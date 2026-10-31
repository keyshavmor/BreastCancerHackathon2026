#!/usr/bin/env python
"""Stage 3 - ESM2-3B rerank, orthogonal to AbLang2, then freeze the portfolio.

AbLang2 asks "is this still a plausible *antibody*". ESM2 asks "is this still a
plausible *protein*". The two models have different training distributions and
different failure modes, which is the whole point of running both: a candidate
that survives only one prior is weaker evidence than one that survives both.

Neither model sees HER2, so neither predicts binding. These are plausibility
priors used to shrink the structural budget, nothing more.

Two scores, mirroring stage 2 so the cost stays sub-linear in pool size:

``esm2_additive``
    A one-time masked scan over all mutable positions yields
    ``logP(mut) - logP(wt)`` per site; a candidate's score is the sum over its
    sites. Cost is ~223 forward passes *total*, independent of candidate count,
    so this scales to any pool size we can generate.
``esm2_contextual``
    Mean log-probability of the candidate's mutated positions evaluated in the
    candidate's own (unmasked) context: one forward pass per candidate. This is
    the term that can see epistasis between co-occurring substitutions.

Ranking is by **rank aggregation**, not a weighted sum of raw scores, because
AbLang2 and ESM2 log-probabilities are in incomparable units (see the report's
caveat about absolute cutoffs borrowed across models).

Outputs the frozen deliverables: ``internal_50_candidates.*`` (ipSAE deliberately
``NOT_EVALUATED``) and ``priority_cofold_queue.csv``, the diversity-aware order
in which Boltz-2 should spend its budget - first 15 rows are the lab-nomination
priority set.

Run:
    python stage3_esm_rerank.py --benchmark-only      # time it first
    python stage3_esm_rerank.py --max-candidates 5000
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

import her2_common as hc
from stage2_generate_candidates import BRANCH_SLOTS, greedy_diverse

MODEL_NAME = "esm2_t36_3B_UR50D"


def load_esm(model_name: str, device: str, fp16: bool):
    """Load a fair-esm model. Weights come from the local torch hub cache."""
    import esm as fair_esm

    model, alphabet = getattr(fair_esm.pretrained, model_name)()
    model = model.eval().to(device)
    if fp16 and device.startswith("cuda"):
        # bf16 keeps the dynamic range of fp32 while halving memory; a 3B model
        # in fp32 would need ~12 GB of weights alone before activations.
        model = model.to(torch.bfloat16)
    return model, alphabet, alphabet.get_batch_converter()


@torch.inference_mode()
def _logits(model, toks: torch.Tensor) -> torch.Tensor:
    return model(toks, repr_layers=[], return_contacts=False)["logits"].float()


@torch.inference_mode()
def masked_site_scan(model, alphabet, batch_converter, positions: list[int],
                     parent: str, device: str, batch_size: int) -> dict[int, dict[str, float]]:
    """``{pos: {aa: logP(aa) - logP(wt)}}`` from one masked pass per position."""
    aa_idx = {a: alphabet.get_idx(a) for a in sorted(hc.CANONICAL_AA)}
    deltas: dict[int, dict[str, float]] = {}

    for i in range(0, len(positions), batch_size):
        chunk = positions[i : i + batch_size]
        data = [(f"m{p}", parent[: p - 1] + "<mask>" + parent[p:]) for p in chunk]
        # fair-esm's batch converter understands the literal "<mask>" token.
        _, _, toks = batch_converter([(n, s) for n, s in data])
        toks = toks.to(device)
        logits = _logits(model, toks)
        logprobs = torch.log_softmax(logits, dim=-1)
        for row, p in enumerate(chunk):
            # +1 for the prepended BOS token.
            lp = logprobs[row, p]
            wt = parent[p - 1]
            base = lp[aa_idx[wt]].item()
            deltas[p] = {a: lp[aa_idx[a]].item() - base for a in aa_idx if a != wt}
    return deltas


@torch.inference_mode()
def contextual_scores(model, alphabet, batch_converter, seqs: list[str],
                      mut_positions: list[list[int]], device: str,
                      batch_size: int) -> list[float]:
    """Mean log-probability of each candidate's mutated positions, in its own context."""
    out: list[float] = []
    for i in range(0, len(seqs), batch_size):
        chunk = seqs[i : i + batch_size]
        chunk_muts = mut_positions[i : i + batch_size]
        _, _, toks = batch_converter([(f"s{j}", s) for j, s in enumerate(chunk)])
        toks = toks.to(device)
        logprobs = torch.log_softmax(_logits(model, toks), dim=-1)
        for row, (seq, muts) in enumerate(zip(chunk, chunk_muts)):
            vals = [logprobs[row, p, alphabet.get_idx(seq[p - 1])].item() for p in muts]
            out.append(float(np.mean(vals)) if vals else float("nan"))
    return out


def rank_of(values: list[float], higher_is_better: bool = True) -> list[float]:
    """Percentile ranks in [0,1]; NaNs get the worst rank."""
    arr = np.asarray(values, dtype=float)
    finite = np.isfinite(arr)
    order = np.full(len(arr), np.nan)
    vals = arr[finite]
    if len(vals) == 0:
        return [0.0] * len(arr)
    sign = -1.0 if higher_is_better else 1.0
    idx = np.argsort(sign * vals, kind="stable")
    r = np.empty(len(vals))
    r[idx] = np.arange(len(vals))
    order[finite] = 1.0 - r / max(1, len(vals) - 1)
    return [0.0 if not np.isfinite(v) else float(v) for v in order]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    ap.add_argument("--shortlist", type=Path, default=here.parent / "outputs" / "esm_shortlist.csv")
    ap.add_argument("--residue-map", type=Path, default=here.parent / "outputs" / "residue_map.csv")
    ap.add_argument("--outdir", type=Path, default=here.parent / "outputs")
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--scan-batch-size", type=int, default=8)
    ap.add_argument("--fp32", action="store_true", help="disable bf16 (slower, more memory)")
    ap.add_argument("--max-candidates", type=int, default=5000)
    ap.add_argument("--internal-pool", type=int, default=50)
    ap.add_argument("--priority", type=int, default=15)
    ap.add_argument("--queue-size", type=int, default=150,
                    help="total cofold queue length, including the internal pool")
    ap.add_argument("--benchmark-only", action="store_true",
                    help="time the model on 10 sequences and exit without scoring the pool")
    ap.add_argument("--control-fp32-subset", type=int, default=12,
                    help="re-score this many candidates in fp32 to verify bf16 numerics")
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    hc.assert_parent_integrity()

    with open(args.shortlist) as fh:
        cands = list(csv.DictReader(fh))
    if args.max_candidates:
        cands = cands[: args.max_candidates]
    print(f"[load] {len(cands)} candidates from {args.shortlist.name}")

    t0 = time.time()
    model, alphabet, bc = load_esm(args.model, args.device, fp16=not args.fp32)
    load_s = time.time() - t0
    peak = lambda: torch.cuda.max_memory_allocated() / 2**30 if args.device.startswith("cuda") else 0.0
    print(f"[esm] {args.model} loaded in {load_s:.1f}s, "
          f"dtype={'fp32' if args.fp32 else 'bf16'}, peak {peak():.2f} GiB")

    # ---- throughput benchmark (always run; it sets the hard stop) --------- #
    probe = [c["full_scfv_sequence"] for c in cands[:10]]
    probe_muts = [[int(m[1:-1]) for m in c["mutations_1based"].split(";")] for c in cands[:10]]
    t = time.time()
    _ = contextual_scores(model, alphabet, bc, probe, probe_muts, args.device, args.batch_size)
    per_seq = (time.time() - t) / max(1, len(probe))
    print(f"[bench] contextual pass {per_seq*1000:.0f} ms/seq -> "
          f"{len(cands)} candidates ~= {per_seq*len(cands)/60:.1f} min; peak {peak():.2f} GiB")
    if args.benchmark_only:
        print("[bench] --benchmark-only set, exiting before full scoring")
        return 0

    # ---- one-time masked site scan --------------------------------------- #
    with open(args.residue_map) as fh:
        rmap_rows = list(csv.DictReader(fh))
    mutable = [int(r["scfv_pos_1based"]) for r in rmap_rows if r["mutable"] == "True"]
    t = time.time()
    deltas = masked_site_scan(model, alphabet, bc, mutable, hc.PARENT_SEQ,
                              args.device, args.scan_batch_size)
    scan_s = time.time() - t
    print(f"[esm] masked site scan {len(mutable)} positions in {scan_s:.1f}s "
          f"({scan_s/len(mutable)*1000:.0f} ms/position)")

    with open(args.outdir / "esm2_site_prior.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scfv_pos_1based", "parent_aa", "sub_aa", "esm2_delta_logp", "rank_at_site"])
        for p in mutable:
            for i, (aa, d) in enumerate(sorted(deltas[p].items(), key=lambda kv: -kv[1]), 1):
                w.writerow([p, hc.PARENT_SEQ[p - 1], aa, round(d, 4), i])

    # ---- score the pool --------------------------------------------------- #
    seqs = [c["full_scfv_sequence"] for c in cands]
    muts = [[int(m[1:-1]) for m in c["mutations_1based"].split(";")] for c in cands]
    for c, seq, mp in zip(cands, seqs, muts):
        add = sum(deltas[p][seq[p - 1]] for p in mp if p in deltas and seq[p - 1] in deltas[p])
        c["esm2_additive"] = add
        c["esm2_additive_mean"] = add / max(1, len(mp))

    t = time.time()
    ctx = contextual_scores(model, alphabet, bc, seqs, muts, args.device, args.batch_size)
    ctx_s = time.time() - t
    for c, v in zip(cands, ctx):
        c["esm2_contextual"] = v
    print(f"[esm] contextual scored {len(cands)} candidates in {ctx_s:.1f}s; peak {peak():.2f} GiB")

    # ---- bf16 numeric control -------------------------------------------- #
    control = {}
    if not args.fp32 and args.control_fp32_subset > 0:
        n = min(args.control_fp32_subset, len(cands))
        del model
        torch.cuda.empty_cache()
        m32, a32, b32 = load_esm(args.model, args.device, fp16=False)
        ref = contextual_scores(m32, a32, b32, seqs[:n], muts[:n], args.device, max(1, args.batch_size // 2))
        diff = np.abs(np.asarray(ref) - np.asarray(ctx[:n]))
        control = {"n": n, "max_abs_diff": float(diff.max()), "mean_abs_diff": float(diff.mean()),
                   "any_nan": bool(np.isnan(np.asarray(ctx)).any())}
        print(f"[control] bf16 vs fp32 on {n} candidates: max|diff|={diff.max():.4f} "
              f"mean|diff|={diff.mean():.4f} nan={control['any_nan']}")
        del m32
        torch.cuda.empty_cache()

    # ---- rank aggregation ------------------------------------------------- #
    r_ab_add = rank_of([float(c["ablang2_additive_mean"]) for c in cands])
    r_ab_ctx = rank_of([float(c["ablang2_contextual"]) if c["ablang2_contextual"] else float("nan")
                        for c in cands])
    r_es_add = rank_of([c["esm2_additive_mean"] for c in cands])
    r_es_ctx = rank_of([c["esm2_contextual"] for c in cands])
    for c, a, b, d, e in zip(cands, r_ab_add, r_ab_ctx, r_es_add, r_es_ctx):
        c["rank_ablang2"] = (a + b) / 2
        c["rank_esm2"] = (d + e) / 2
        # Equal weight: we have no validation data that would justify tuning it.
        c["sequence_consensus_score"] = 0.5 * c["rank_ablang2"] + 0.5 * c["rank_esm2"]
        # Disagreement is reported, not penalised - it flags where the two priors
        # tell different stories and the design needs structural evidence.
        c["model_disagreement"] = abs(c["rank_ablang2"] - c["rank_esm2"])

    cands.sort(key=lambda c: -c["sequence_consensus_score"])

    fields = ["candidate_id", "branch", "mutation_count", "mutations_1based",
              "ablang2_additive_mean", "ablang2_contextual", "esm2_additive_mean",
              "esm2_contextual", "rank_ablang2", "rank_esm2",
              "sequence_consensus_score", "model_disagreement",
              "new_liability_flags", "sequence_sha256", "full_scfv_sequence"]

    def row(c: dict, extra: dict | None = None) -> dict:
        r = {k: c.get(k, "") for k in fields}
        for k in ("ablang2_additive_mean", "esm2_additive_mean", "esm2_contextual",
                  "rank_ablang2", "rank_esm2", "sequence_consensus_score", "model_disagreement"):
            if r[k] != "":
                r[k] = round(float(r[k]), 4)
        r.update(extra or {})
        return r

    with open(args.outdir / "model_scores.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(row(c) for c in cands)

    # ---- freeze the internal 50 (branch-quota + diversity aware) ---------- #
    internal: list[dict] = []
    for branch, slots in BRANCH_SLOTS.items():
        pool = [c for c in cands if c["branch"] == branch]
        internal += greedy_diverse(
            [{**c, "mutation_positions": [int(m[1:-1]) for m in c["mutations_1based"].split(";")]}
             for c in pool], slots)
    # Top up from overall ranking if a branch under-delivered.
    if len(internal) < args.internal_pool:
        have = {c["candidate_id"] for c in internal}
        for c in cands:
            if len(internal) >= args.internal_pool:
                break
            if c["candidate_id"] not in have:
                internal.append({**c, "mutation_positions":
                                 [int(m[1:-1]) for m in c["mutations_1based"].split(";")]})
    internal = internal[: args.internal_pool]
    internal.sort(key=lambda c: -c["sequence_consensus_score"])

    out_fields = fields + ["boltz_evaluated", "ipsae_min"]
    with open(args.outdir / "internal_50_candidates.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=out_fields)
        w.writeheader()
        for c in internal:
            w.writerow(row(c, {"boltz_evaluated": False, "ipsae_min": "NOT_EVALUATED"}))
    hc.write_fasta(args.outdir / "internal_50_candidates.fasta",
                   {c["candidate_id"]: c["full_scfv_sequence"] for c in internal})

    # ---- cofold queue ----------------------------------------------------- #
    # Order matters: Boltz spends its budget top-down and may be stopped at any
    # point, so the queue is built in tiers of decreasing commitment:
    #   priority_15  - diverse lab-nomination set, must complete
    #   internal_50  - the rest of the curated 50-proposal deliverable
    #   extended     - further ESM-ranked designs, scored only if time allows
    # Measured Boltz cost (~14 s/structure amortised) makes the extended tier
    # affordable; every scored design still gets a real ipSAE or none at all.
    prio = greedy_diverse(internal, args.priority)
    prio_ids = {p["candidate_id"] for p in prio}
    rest_internal = [c for c in internal if c["candidate_id"] not in prio_ids]
    internal_ids = {c["candidate_id"] for c in internal}

    extended: list[dict] = []
    if args.queue_size > len(internal):
        pool = [{**c, "mutation_positions": [int(m[1:-1]) for m in c["mutations_1based"].split(";")]}
                for c in cands if c["candidate_id"] not in internal_ids]
        extended = greedy_diverse(pool, args.queue_size - len(internal),
                                  pool_cap=max(4 * args.queue_size, 2000))

    queue = prio + rest_internal + extended
    tier_of = lambda i: ("priority_15" if i <= args.priority
                         else "internal_50" if i <= len(internal) else "extended")
    with open(args.outdir / "priority_cofold_queue.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["queue_order", "priority_tier"] + fields)
        w.writeheader()
        for i, c in enumerate(queue, 1):
            w.writerow({"queue_order": i, "priority_tier": tier_of(i), **row(c)})
    print(f"[queue] {len(queue)} entries: {args.priority} priority / "
          f"{len(rest_internal)} internal / {len(extended)} extended")

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model, "precision": "fp32" if args.fp32 else "bf16",
        "load_s": round(load_s, 1), "site_scan_s": round(scan_s, 1),
        "contextual_s": round(ctx_s, 1), "ms_per_seq_contextual": round(per_seq * 1000, 1),
        "candidates_scored": len(cands), "mutable_positions_scanned": len(mutable),
        "peak_gpu_gib": round(peak(), 2),
        "bf16_fp32_control": control,
        "internal_pool": len(internal), "priority": args.priority,
        "queue_size": args.queue_size,
        "branch_counts_internal": dict(Counter(c["branch"] for c in internal)),
        "ranking": "equal-weight rank aggregation of AbLang2 and ESM2 percentile ranks",
        "caveat": "Neither model sees HER2; these are plausibility priors, not affinity predictions.",
    }
    (args.outdir / "stage3_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[done] internal_50_candidates.* and priority_cofold_queue.csv written "
          f"({len(internal)} designs, {args.priority} priority) -> {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
