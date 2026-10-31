#!/usr/bin/env python
"""Stage 2 - AbLang2-guided candidate generation for the HER2 scFv challenge.

Produces a large pool of substitution-only scFv variants, hard-filters them
against every organizer rule, and ranks them with an antibody language model.

Design rationale
----------------
The parent is a sub-picomolar binder (0.82 pM BLI per the organizer slide), so
the search is deliberately conservative: fixed length 242, 5-8 substitutions,
frozen linker, frozen native cysteines, and **frozen tight-contact anchors**.

Anchors are derived from measured geometry rather than guessed: any scFv residue
whose minimum heavy-atom distance to HER2 in 1N8Z is below ``--anchor-cutoff``
(default 3.0 A) is almost certainly making a hydrogen bond or salt bridge, and
mutating it is the fastest way to destroy a sub-pM interaction. For this parent
that freezes R50, G103, N165, H226, Y227, T229.

Four independent branches are sampled so the portfolio spans distinct
mechanistic hypotheses instead of 50 neighbours of one motif:

==========  =====  ====================================================
Branch      Slots  Hypothesis
==========  =====  ====================================================
A_h3         20    Focused CDR-H3 affinity maturation (strongest
                   published evidence: AlphaBind 2025, AbOptimizer 2026)
B_interface  12    Non-H3 paratope / contact-adjacent optimisation
C_mixed      10    A few paratope edits plus compatible framework support
D_framework   8    Framework-biased control that retains all anchors
==========  =====  ====================================================

Scoring
-------
Two AbLang2 signals, both cheap because the expensive part is done once:

``ablang2_additive``
    One masked forward pass per mutable position gives a per-site
    ``logP(mut) - logP(wt)`` table. A candidate's score is the sum of its
    sites' deltas. Cost: ~223 forward passes total, independent of pool size.
``ablang2_contextual``
    Mean log-probability of the mutated positions evaluated in the *mutant*
    context (one forward pass per candidate). Applied only to the shortlist,
    because it does not factor across candidates.

Neither is a binding predictor. AbLang2 never sees HER2; these scores only ask
whether a sequence still looks like a plausible antibody.

Run:
    python stage2_generate_candidates.py --pool-size 6000 --shortlist 600
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import her2_common as hc

MASK = "*"
# Branch quotas for the internal 50-proposal pool.
BRANCH_SLOTS = {"A_h3": 20, "B_interface": 12, "C_mixed": 10, "D_framework": 8}


# --------------------------------------------------------------------------- #
# Position pools
# --------------------------------------------------------------------------- #

def load_residue_map(path: Path) -> list[dict]:
    with open(path) as fh:
        return list(csv.DictReader(fh))


def build_pools(rows: list[dict], anchor_cutoff: float) -> dict:
    """Partition mutable scFv positions into mechanistic pools.

    Returns a dict with ``anchors`` plus the four candidate position pools.
    A position is mutable only if it is outside the linker and is not a native
    cysteine (both enforced again by the validator).
    """
    spans = hc.cdr_spans()
    h3_lo, h3_hi = spans["CDR-H3"]

    anchors, h3, paratope, other_cdr, framework = set(), [], [], [], []
    for r in rows:
        pos = int(r["scfv_pos_1based"])
        if r["is_linker"] == "True" or r["is_native_cys"] == "True":
            continue
        dist = float(r["min_target_distance_A"]) if r["min_target_distance_A"] else None
        if dist is not None and dist < anchor_cutoff:
            anchors.add(pos)
            continue
        in_h3 = h3_lo <= pos <= h3_hi
        contact = r["contact_class"] in ("direct", "near")
        if in_h3:
            h3.append(pos)
        elif contact:
            paratope.append(pos)
        elif r["cdr_name"] != "framework":
            other_cdr.append(pos)
        else:
            framework.append(pos)
    return {"anchors": sorted(anchors), "h3": h3, "paratope": paratope,
            "other_cdr": other_cdr, "framework": framework}


# --------------------------------------------------------------------------- #
# AbLang2 single-site masked scan
# --------------------------------------------------------------------------- #

def ablang2_row_index(pos: int) -> int:
    """Map a 1-based scFv position to its row in AbLang2's paired logits.

    The paired tokenisation is ``<VH>|<VL>`` = 232 tokens for this parent:
    index 0 ``<``, 1..120 V_H, 121 ``>``, 122 ``|``, 123 ``<``, 124..230 V_L,
    231 ``>``. Verified empirically against the tokenizer, not assumed.
    """
    dom = hc.domain_of(pos)
    if dom == "VH":
        return pos
    if dom == "VL":
        return 123 + (pos - hc.VL_RANGE[0] + 1)
    raise ValueError(f"position {pos} is in the frozen linker")


def masked_site_scan(model, positions: list[int], parent: str, batch_size: int = 48):
    """Return ``{pos: {aa: delta_logp}}`` from one masked pass per position."""
    tok = model.tokenizer
    aa_ids = {a: tok.aa_to_token[a] for a in sorted(hc.CANONICAL_AA)}
    vh_lo, vh_hi = hc.VH_RANGE
    vl_lo = hc.VL_RANGE[0]

    def split_pair(seq: str) -> list[str]:
        return [seq[vh_lo - 1 : vh_hi], seq[vl_lo - 1 :]]

    pairs, order = [], []
    for p in positions:
        mutated = parent[: p - 1] + MASK + parent[p:]
        pairs.append(split_pair(mutated))
        order.append(p)

    deltas: dict[int, dict[str, float]] = {}
    for i in range(0, len(pairs), batch_size):
        chunk, chunk_pos = pairs[i : i + batch_size], order[i : i + batch_size]
        logits = model(chunk, mode="likelihood")
        for lg, p in zip(logits, chunk_pos):
            row = np.asarray(lg)[ablang2_row_index(p)].astype(np.float64)
            sub = np.array([row[aa_ids[a]] for a in sorted(hc.CANONICAL_AA)])
            sub = sub - np.log(np.exp(sub - sub.max()).sum()) - sub.max()  # log-softmax over 20 AA
            lp = dict(zip(sorted(hc.CANONICAL_AA), sub))
            wt = parent[p - 1]
            deltas[p] = {a: float(lp[a] - lp[wt]) for a in lp if a != wt}
    return deltas


def contextual_scores(model, seqs: list[str], mut_positions: list[list[int]],
                      batch_size: int = 32) -> list[float]:
    """Mean log-probability of each candidate's mutated positions in its own context."""
    tok = model.tokenizer
    aa_ids = {a: tok.aa_to_token[a] for a in sorted(hc.CANONICAL_AA)}
    vh_lo, vh_hi = hc.VH_RANGE
    vl_lo = hc.VL_RANGE[0]
    pairs = [[s[vh_lo - 1 : vh_hi], s[vl_lo - 1 :]] for s in seqs]

    out: list[float] = []
    for i in range(0, len(pairs), batch_size):
        logits = model(pairs[i : i + batch_size], mode="likelihood")
        for lg, seq, muts in zip(logits, seqs[i : i + batch_size], mut_positions[i : i + batch_size]):
            arr = np.asarray(lg).astype(np.float64)
            vals = []
            for p in muts:
                row = arr[ablang2_row_index(p)]
                sub = np.array([row[aa_ids[a]] for a in sorted(hc.CANONICAL_AA)])
                sub = sub - sub.max()
                sub = sub - np.log(np.exp(sub).sum())
                vals.append(float(sub[sorted(hc.CANONICAL_AA).index(seq[p - 1])]))
            out.append(float(np.mean(vals)) if vals else float("nan"))
    return out


# --------------------------------------------------------------------------- #
# Sampling
# --------------------------------------------------------------------------- #

BRANCH_RECIPES = {
    # branch -> (pool name, n_from_pool) list; counts are sampled per design
    "A_h3":        [("h3", (3, 5)), ("paratope", (0, 2)), ("other_cdr", (0, 2)), ("framework", (0, 2))],
    "B_interface": [("paratope", (2, 4)), ("other_cdr", (1, 3)), ("framework", (0, 2)), ("h3", (0, 1))],
    "C_mixed":     [("paratope", (1, 2)), ("h3", (0, 1)), ("framework", (3, 5)), ("other_cdr", (0, 1))],
    "D_framework": [("framework", (5, 7)), ("other_cdr", (0, 1))],
}


def sample_design(rng: random.Random, branch: str, pools: dict, deltas: dict,
                  top_k: int, min_mut: int, max_mut: int) -> str | None:
    """Sample one candidate sequence for ``branch``; returns None if infeasible."""
    chosen: dict[int, str] = {}
    for pool_name, (lo, hi) in BRANCH_RECIPES[branch]:
        pool = [p for p in pools[pool_name] if p in deltas and p not in chosen]
        if not pool:
            continue
        n = rng.randint(lo, min(hi, len(pool)))
        for p in rng.sample(pool, n):
            opts = sorted(deltas[p].items(), key=lambda kv: -kv[1])
            # Never introduce a cysteine; keep the top-k most plausible substitutions.
            opts = [(a, d) for a, d in opts if a != "C"][:top_k]
            if not opts:
                continue
            weights = np.exp(np.array([d for _, d in opts], dtype=float) -
                             max(d for _, d in opts))
            chosen[p] = opts[int(rng.choices(range(len(opts)), weights=weights.tolist())[0])][0]

    # Trim or pad to the allowed mutation band.
    if len(chosen) > max_mut:
        keep = rng.sample(sorted(chosen), max_mut)
        chosen = {p: chosen[p] for p in keep}
    if len(chosen) < min_mut:
        spare = [p for name in ("framework", "other_cdr", "paratope", "h3")
                 for p in pools[name] if p in deltas and p not in chosen]
        rng.shuffle(spare)
        for p in spare:
            if len(chosen) >= min_mut:
                break
            opts = [(a, d) for a, d in sorted(deltas[p].items(), key=lambda kv: -kv[1]) if a != "C"][:top_k]
            if opts:
                chosen[p] = opts[0][0]
    if len(chosen) < min_mut:
        return None

    out = list(hc.PARENT_SEQ)
    for p, a in chosen.items():
        out[p - 1] = a
    return "".join(out)


def greedy_diverse(items: list[dict], k: int, key="mutation_positions",
                   pool_cap: int | None = None) -> list[dict]:
    """Farthest-point selection on Jaccard distance between mutation-position sets.

    Picks the best-scoring item first, then repeatedly the item whose mutated
    position set is furthest from everything already chosen. This is what stops
    the portfolio collapsing into 50 variants of one motif.

    Implemented incrementally: each candidate caches its minimum distance to the
    chosen set, and a new pick only has to be compared against that cache. That
    is O(k * n) rather than the O(k^2 * n) of recomputing the min over all
    selected items on every step - the difference between seconds and tens of
    minutes at n=10,000.

    ``items`` must already be sorted best-first; only the top ``pool_cap``
    entries are considered so cost stays bounded on very large pools.
    """
    if len(items) <= k:
        return items
    cap = pool_cap if pool_cap is not None else max(8 * k, 400)
    items = items[:cap]
    sets = [set(it[key]) for it in items]

    def jaccard_dist(a: set, b: set) -> float:
        return 1.0 - len(a & b) / max(1, len(a | b))

    chosen = [0]
    # best[i] = min Jaccard distance from item i to anything already chosen.
    # -1 marks an item that has been consumed.
    best = [jaccard_dist(sets[i], sets[0]) for i in range(len(items))]
    best[0] = -1.0
    while len(chosen) < k:
        nxt = max(range(len(items)), key=best.__getitem__)
        if best[nxt] < 0:
            break
        chosen.append(nxt)
        new = sets[nxt]
        best[nxt] = -1.0
        for i in range(len(items)):
            if best[i] < 0:
                continue
            d = jaccard_dist(sets[i], new)
            if d < best[i]:
                best[i] = d
    return [items[i] for i in chosen]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    ap.add_argument("--residue-map", type=Path, default=here.parent / "outputs" / "residue_map.csv")
    ap.add_argument("--outdir", type=Path, default=here.parent / "outputs")
    ap.add_argument("--pool-size", type=int, default=6000, help="raw proposals to sample")
    ap.add_argument("--shortlist", type=int, default=600, help="diverse set handed to ESM2")
    ap.add_argument("--top-k", type=int, default=5, help="substitutions kept per position")
    ap.add_argument("--anchor-cutoff", type=float, default=3.0,
                    help="freeze scFv residues closer than this (A) to HER2")
    ap.add_argument("--min-mut", type=int, default=hc.MIN_MUTATIONS)
    ap.add_argument("--max-mut", type=int, default=hc.MAX_MUTATIONS_POLICY)
    ap.add_argument("--seed", type=int, default=20261031)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    hc.assert_parent_integrity()
    rng = random.Random(args.seed)
    t0 = time.time()

    rows = load_residue_map(args.residue_map)
    pools = build_pools(rows, args.anchor_cutoff)
    print(f"[pools] anchors(frozen)={pools['anchors']}")
    for k in ("h3", "paratope", "other_cdr", "framework"):
        print(f"[pools] {k:11s} n={len(pools[k]):3d}")

    # ---- AbLang2 site scan ------------------------------------------------ #
    import ablang2
    t = time.time()
    model = ablang2.pretrained(model_to_use="ablang2-paired", random_init=False,
                               ncpu=1, device=args.device)
    load_s = time.time() - t
    scan_positions = sorted(set(pools["h3"] + pools["paratope"] + pools["other_cdr"] + pools["framework"]))
    t = time.time()
    deltas = masked_site_scan(model, scan_positions, hc.PARENT_SEQ)
    scan_s = time.time() - t
    print(f"[ablang2] load {load_s:.1f}s | masked scan {len(scan_positions)} positions in {scan_s:.1f}s")

    with open(args.outdir / "mutation_site_prior.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scfv_pos_1based", "parent_aa", "domain", "cdr_name", "pool",
                    "min_target_distance_A", "sub_aa", "ablang2_delta_logp", "rank_at_site"])
        rmap = {int(r["scfv_pos_1based"]): r for r in rows}
        pool_of = {p: name for name in ("h3", "paratope", "other_cdr", "framework") for p in pools[name]}
        for p in scan_positions:
            ranked = sorted(deltas[p].items(), key=lambda kv: -kv[1])
            for i, (aa, d) in enumerate(ranked, 1):
                r = rmap[p]
                w.writerow([p, hc.PARENT_SEQ[p - 1], r["domain"], r["cdr_name"], pool_of.get(p, ""),
                            r["min_target_distance_A"], aa, round(d, 4), i])

    # ---- sample, filter, dedupe ------------------------------------------- #
    branches = list(BRANCH_SLOTS)
    per_branch = max(1, args.pool_size // len(branches))
    seen_seq: set[str] = set()
    seen_sig: set[tuple] = set()
    kept: list[dict] = []
    reject = Counter()
    attempts = 0

    for branch in branches:
        made = 0
        tries = 0
        while made < per_branch and tries < per_branch * 40:
            tries += 1
            attempts += 1
            seq = sample_design(rng, branch, pools, deltas, args.top_k, args.min_mut, args.max_mut)
            if seq is None:
                reject["infeasible_sample"] += 1
                continue
            if seq in seen_seq:
                reject["duplicate_sequence"] += 1
                continue
            v = hc.validate_candidate(seq, min_mut=args.min_mut, max_mut=args.max_mut)
            if not v.ok:
                reject[v.failures[0].split(":")[0][:40]] += 1
                continue
            sig = tuple(sorted(v.mutations))
            if sig in seen_sig:
                reject["duplicate_mutation_signature"] += 1
                continue
            seen_seq.add(seq)
            seen_sig.add(sig)
            positions = [int(m[1:-1]) for m in v.mutations]
            add = sum(deltas[p][seq[p - 1]] for p in positions)
            kept.append({
                "branch": branch, "sequence": seq, "mutations": v.mutations,
                "mutation_positions": positions, "mutation_count": v.mutation_count,
                "ablang2_additive": add,
                "ablang2_additive_mean": add / max(1, v.mutation_count),
                "warnings": ";".join(v.warnings),
            })
            made += 1
        print(f"[sample] {branch:12s} kept={made}")

    print(f"[sample] total kept={len(kept)} from {attempts} attempts; rejects={dict(reject)}")
    if not kept:
        raise SystemExit("no valid candidates generated")

    # ---- shortlist: quality x diversity, per branch ----------------------- #
    kept.sort(key=lambda d: -d["ablang2_additive_mean"])
    short_per_branch = max(1, args.shortlist // len(branches))
    shortlist: list[dict] = []
    for branch in branches:
        pool = [d for d in kept if d["branch"] == branch]
        shortlist += greedy_diverse(pool, short_per_branch)
    print(f"[shortlist] {len(shortlist)} candidates for ESM2 rerank")

    # Contextual AbLang2 rescore, shortlist only.
    t = time.time()
    ctx = contextual_scores(model, [d["sequence"] for d in shortlist],
                            [d["mutation_positions"] for d in shortlist])
    for d, c in zip(shortlist, ctx):
        d["ablang2_contextual"] = c
    print(f"[ablang2] contextual rescore {len(shortlist)} candidates in {time.time()-t:.1f}s")

    # ---- write artifacts -------------------------------------------------- #
    def cid(i: int) -> str:
        return f"HER2_{i:04d}"

    for i, d in enumerate(sorted(kept, key=lambda x: -x["ablang2_additive_mean"]), 1):
        d["candidate_id"] = cid(i)
    short_ids = {d["sequence"] for d in shortlist}

    fields = ["candidate_id", "branch", "mutation_count", "mutations_1based",
              "ablang2_additive", "ablang2_additive_mean", "ablang2_contextual",
              "in_esm_shortlist", "new_liability_flags", "sequence_sha256", "full_scfv_sequence"]

    def row_of(d: dict) -> dict:
        return {
            "candidate_id": d["candidate_id"], "branch": d["branch"],
            "mutation_count": d["mutation_count"], "mutations_1based": ";".join(d["mutations"]),
            "ablang2_additive": round(d["ablang2_additive"], 4),
            "ablang2_additive_mean": round(d["ablang2_additive_mean"], 4),
            "ablang2_contextual": round(d["ablang2_contextual"], 4) if "ablang2_contextual" in d else "",
            "in_esm_shortlist": d["sequence"] in short_ids,
            "new_liability_flags": d["warnings"],
            "sequence_sha256": hc.sha256_seq(d["sequence"]),
            "full_scfv_sequence": d["sequence"],
        }

    with open(args.outdir / "all_candidates.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(row_of(d) for d in kept)

    with open(args.outdir / "esm_shortlist.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(row_of(d) for d in shortlist)
    hc.write_fasta(args.outdir / "esm_shortlist.fasta",
                   {d["candidate_id"]: d["sequence"] for d in shortlist})

    # Provisional internal 50 - a stop-loss artifact written now, so a valid
    # 50-proposal pool exists even if every later stage fails. Stage 3 replaces
    # it with the ESM2-reranked final selection. ipSAE is deliberately absent.
    prov: list[dict] = []
    for branch, slots in BRANCH_SLOTS.items():
        prov += greedy_diverse([d for d in shortlist if d["branch"] == branch], slots)
    with open(args.outdir / "internal_50_candidates_provisional.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields + ["ipsae_min"])
        w.writeheader()
        for d in prov:
            r = row_of(d)
            r["ipsae_min"] = "NOT_EVALUATED"
            w.writerow(r)
    hc.write_fasta(args.outdir / "internal_50_candidates_provisional.fasta",
                   {d["candidate_id"]: d["sequence"] for d in prov})
    print(f"[stop-loss] internal_50_candidates_provisional.* written ({len(prov)} designs, ipSAE NOT_EVALUATED)")

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed, "pool_size_requested": args.pool_size,
        "candidates_kept": len(kept), "shortlist": len(shortlist), "provisional_50": len(prov),
        "attempts": attempts, "rejects": dict(reject),
        "anchor_cutoff_A": args.anchor_cutoff, "frozen_anchors": pools["anchors"],
        "pool_sizes": {k: len(pools[k]) for k in ("h3", "paratope", "other_cdr", "framework")},
        "branch_slots": BRANCH_SLOTS, "top_k_per_site": args.top_k,
        "mutation_band": [args.min_mut, args.max_mut],
        "ablang2_model": "ablang2-paired", "ablang2_load_s": round(load_s, 1),
        "site_scan_s": round(scan_s, 1),
        "branch_counts": dict(Counter(d["branch"] for d in kept)),
        "mutation_count_hist": dict(sorted(Counter(d["mutation_count"] for d in kept).items())),
        "total_runtime_s": round(time.time() - t0, 1),
        "note": "AbLang2 scores are antibody-plausibility priors; the model never sees HER2.",
    }
    (args.outdir / "stage2_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[done] stage 2 in {manifest['total_runtime_s']}s -> {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
