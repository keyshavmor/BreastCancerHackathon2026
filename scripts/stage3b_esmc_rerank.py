#!/usr/bin/env python
"""Stage 3b (optional) - ESM-C third sequence prior, orthogonal to AbLang2/ESM2.

Why a third prior at all: AbLang2 asks "is this still a plausible antibody" and
ESM2-3B asks "is this still a plausible protein". ESM-C is a newer
EvolutionaryScale encoder trained on a different corpus with a different
objective, so where it *disagrees* with ESM2 is informative - it marks designs
whose plausibility is model-dependent rather than robust.

Like the other two, **ESM-C never sees HER2**. It cannot predict binding. This
stage only adds a plausibility axis; the core result does not depend on it,
which is why it is optional and runs in its own environment.

Environment: ESM-C needs EvolutionaryScale's ``esm`` SDK, which collides with
``fair-esm`` (both own the top-level ``esm`` package). Run this with the
``esm3-sequence-embeddings`` / ``her2_esm3`` interpreter, never ``her2_seq``.

Scoring mirrors stages 2 and 3 so the costs stay comparable:
  ``esmc_additive``   - one masked pass per mutable position, then table lookup
  ``esmc_contextual`` - mean log-prob of mutated positions in the mutant context

Numerical caveat: without transformer-engine / xformers / flash-attn installed,
the SDK falls back to pure-PyTorch kernels. Differences are a few ULP after the
final LayerNorm and perplexity stays within rounding noise, which is immaterial
for *ranking* but is recorded in the manifest.

Run (note the interpreter):
    ~/anaconda3/envs/esm3-sequence-embeddings/bin/python stage3b_esmc_rerank.py \
        --queue ../outputs/priority_cofold_queue.csv --outdir ../outputs
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

import her2_common as hc

MODEL_NAME = "esmc_600m"


# --------------------------------------------------------------------------- #
# Model / tokenizer plumbing
# --------------------------------------------------------------------------- #

def load_esmc(model_name: str, device: str):
    """Load ESM-C and its sequence tokenizer."""
    from esm.models.esmc import ESMC

    model = ESMC.from_pretrained(model_name, device=torch.device(device), use_flash_attn=False)
    model = model.eval()
    tok = getattr(model, "tokenizer", None)
    if tok is None:
        from esm.tokenization.sequence_tokenizer import EsmSequenceTokenizer
        tok = EsmSequenceTokenizer()
    return model, tok


def encode_batch(tok, seqs: list[str], device: str) -> torch.Tensor:
    """Tokenise a batch of equal-length sequences to (B, L+2) ids."""
    ids = [tok.encode(s) for s in seqs]
    width = max(len(i) for i in ids)
    pad = getattr(tok, "pad_token_id", 1)
    out = torch.full((len(ids), width), pad, dtype=torch.long)
    for r, i in enumerate(ids):
        out[r, : len(i)] = torch.tensor(i, dtype=torch.long)
    return out.to(device)


@torch.inference_mode()
def seq_logits(model, toks: torch.Tensor) -> torch.Tensor:
    """Return (B, L, vocab) sequence logits, tolerating SDK output shapes."""
    out = model(sequence_tokens=toks)
    lg = getattr(out, "sequence_logits", None)
    if lg is None:
        lg = getattr(getattr(out, "logits", None), "sequence", None)
    if lg is None:
        raise RuntimeError("could not locate sequence logits on ESM-C output")
    return lg.float()


def aa_token_ids(tok) -> dict[str, int]:
    return {a: tok.encode(a, add_special_tokens=False)[0] for a in sorted(hc.CANONICAL_AA)}


def mask_id(tok) -> int:
    mid = getattr(tok, "mask_token_id", None)
    if mid is None:
        raise RuntimeError("tokenizer exposes no mask_token_id")
    return int(mid)


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #

@torch.inference_mode()
def masked_site_scan(model, tok, positions: list[int], parent: str,
                     device: str, batch_size: int) -> dict[int, dict[str, float]]:
    """``{pos: {aa: logP(aa) - logP(wt)}}``; one masked forward pass per position."""
    aa_ids, mid = aa_token_ids(tok), mask_id(tok)
    deltas: dict[int, dict[str, float]] = {}
    for i in range(0, len(positions), batch_size):
        chunk = positions[i : i + batch_size]
        toks = encode_batch(tok, [parent] * len(chunk), device)
        for r, p in enumerate(chunk):
            toks[r, p] = mid                     # +1 offset: index 0 is BOS
        lp = torch.log_softmax(seq_logits(model, toks), dim=-1)
        for r, p in enumerate(chunk):
            row = lp[r, p]
            wt = parent[p - 1]
            base = row[aa_ids[wt]].item()
            deltas[p] = {a: row[aa_ids[a]].item() - base for a in aa_ids if a != wt}
    return deltas


@torch.inference_mode()
def contextual_scores(model, tok, seqs: list[str], mut_positions: list[list[int]],
                      device: str, batch_size: int) -> list[float]:
    """Mean log-probability of each candidate's mutated positions in its own context."""
    aa_ids = aa_token_ids(tok)
    out: list[float] = []
    for i in range(0, len(seqs), batch_size):
        chunk, muts = seqs[i : i + batch_size], mut_positions[i : i + batch_size]
        lp = torch.log_softmax(seq_logits(model, encode_batch(tok, chunk, device)), dim=-1)
        for r, (seq, mp) in enumerate(zip(chunk, muts)):
            vals = [lp[r, p, aa_ids[seq[p - 1]]].item() for p in mp]
            out.append(float(np.mean(vals)) if vals else float("nan"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    base = here.parent
    ap.add_argument("--queue", type=Path, default=base / "outputs" / "priority_cofold_queue.csv")
    ap.add_argument("--residue-map", type=Path, default=base / "outputs" / "residue_map.csv")
    ap.add_argument("--outdir", type=Path, default=base / "outputs")
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-candidates", type=int, default=0, help="0 = all")
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    hc.assert_parent_integrity()

    with open(args.queue) as fh:
        cands = list(csv.DictReader(fh))
    if args.max_candidates:
        cands = cands[: args.max_candidates]
    print(f"[load] {len(cands)} candidates from {args.queue.name}")

    t0 = time.time()
    model, tok = load_esmc(args.model, args.device)
    load_s = time.time() - t0
    peak = lambda: (torch.cuda.max_memory_allocated() / 2**30
                    if args.device.startswith("cuda") else 0.0)
    print(f"[esmc] {args.model} loaded in {load_s:.1f}s, peak {peak():.2f} GiB")

    with open(args.residue_map) as fh:
        mutable = [int(r["scfv_pos_1based"]) for r in csv.DictReader(fh) if r["mutable"] == "True"]
    t = time.time()
    deltas = masked_site_scan(model, tok, mutable, hc.PARENT_SEQ, args.device, args.batch_size)
    scan_s = time.time() - t
    print(f"[esmc] masked site scan {len(mutable)} positions in {scan_s:.1f}s")

    seqs = [c["full_scfv_sequence"] for c in cands]
    muts = [[int(m[1:-1]) for m in c["mutations_1based"].split(";")] for c in cands]
    t = time.time()
    ctx = contextual_scores(model, tok, seqs, muts, args.device, args.batch_size)
    ctx_s = time.time() - t
    print(f"[esmc] contextual scored {len(cands)} candidates in {ctx_s:.1f}s "
          f"({ctx_s/max(1,len(cands))*1000:.0f} ms/seq); peak {peak():.2f} GiB")

    rows = []
    for c, seq, mp, cv in zip(cands, seqs, muts, ctx):
        add = sum(deltas[p][seq[p - 1]] for p in mp if p in deltas and seq[p - 1] in deltas[p])
        rows.append({
            "candidate_id": c["candidate_id"],
            "esmc_additive": round(add, 4),
            "esmc_additive_mean": round(add / max(1, len(mp)), 4),
            "esmc_contextual": round(cv, 4),
        })
    with open(args.outdir / "esmc_scores.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    with open(args.outdir / "esmc_site_prior.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scfv_pos_1based", "parent_aa", "sub_aa", "esmc_delta_logp", "rank_at_site"])
        for p in mutable:
            for i, (aa, d) in enumerate(sorted(deltas[p].items(), key=lambda kv: -kv[1]), 1):
                w.writerow([p, hc.PARENT_SEQ[p - 1], aa, round(d, 4), i])

    # Agreement with ESM2, if stage 3 has run: this is the whole point of the stage.
    corr = None
    ms = args.outdir / "model_scores.csv"
    if ms.is_file():
        with open(ms) as fh:
            e2 = {r["candidate_id"]: r for r in csv.DictReader(fh)}
        pairs = [(float(e2[r["candidate_id"]]["esm2_contextual"]), r["esmc_contextual"])
                 for r in rows
                 if r["candidate_id"] in e2 and e2[r["candidate_id"]].get("esm2_contextual")]
        if len(pairs) > 2:
            a = np.array([p[0] for p in pairs]); b = np.array([p[1] for p in pairs])
            corr = {
                "n": len(pairs),
                "pearson": round(float(np.corrcoef(a, b)[0, 1]), 4),
                "spearman": round(float(np.corrcoef(a.argsort().argsort(),
                                                    b.argsort().argsort())[0, 1]), 4),
            }
            print(f"[agreement] ESM-C vs ESM2-3B contextual: n={corr['n']} "
                  f"pearson={corr['pearson']} spearman={corr['spearman']}")

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model, "candidates_scored": len(rows),
        "load_s": round(load_s, 1), "site_scan_s": round(scan_s, 1),
        "contextual_s": round(ctx_s, 1),
        "ms_per_seq": round(ctx_s / max(1, len(cands)) * 1000, 1),
        "peak_gpu_gib": round(peak(), 2),
        "esm2_agreement": corr,
        "kernel_fallback_note": "transformer-engine/xformers/flash-attn absent; pure-PyTorch "
                                "kernels. Immaterial for ranking.",
        "caveat": "ESM-C never sees HER2. Plausibility prior only, not an affinity predictor.",
    }
    (args.outdir / "stage3b_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[done] esmc_scores.csv ({len(rows)} candidates) -> {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
