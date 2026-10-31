#!/usr/bin/env python
"""Re-prioritise a cofold queue using structural results from an earlier round.

Motivation (measured, not assumed)
----------------------------------
Round 1 cofolded 150 designs and scored them with external ipSAE. Rank
correlations over the 66 ipSAE-complete designs available at the time were:

    predictor                 ipsae_min   epitope_recovery   iptm
    ablang2_additive_mean       -0.284        -0.466        -0.297
    sequence_consensus          -0.231        -0.389        -0.256
    esm2_additive_mean          -0.197        -0.287        -0.222
    mutation_count              -0.499        -0.134        -0.520

Every sequence-plausibility score is **negatively** correlated with interface
quality. The mechanism is plausible: trastuzumab's CDRs are affinity-matured and
therefore deliberately atypical, so an antibody language model tends to propose
reverting them toward germline consensus - and those are exactly the residues
contacting HER2 domain IV. Per-branch means agreed: framework-biased designs
scored best (ipSAE 0.639, epitope recovery 0.976) and CDR-H3-focused designs
worst (0.519, 0.900).

So ranking a second round by sequence consensus would optimise a proxy that
points the wrong way. This script instead:

1. uses sequence consensus only as a **floor** (reject the implausible tail)
   rather than as a maximand;
2. allocates the budget across **mutation-count strata**, favouring the
   organizer minimum of 5, since mutation count was the strongest single
   predictor and its sign is negative;
3. weights **branch quotas** by round-1 observed interface quality while keeping
   every branch represented, so the portfolio stays mechanistically diverse;
4. selects within each stratum by farthest-point diversity on mutated-position
   sets.

Honest caveats
--------------
* This is **not** Bayesian optimisation and must not be described as such: there
  is no experimental feedback in the loop. It is one-shot reprioritisation
  against our own structural proxy.
* ipSAE and epitope recovery are model confidence measures, not affinity. A
  design selected here is not predicted to bind better.
* The mutation-count effect is **partly confounded** by our MSA reuse: the
  retargeted alignment keeps the parent's homolog block, so a design further
  from the parent has weaker profile support at more columns. `--msa-control`
  in stage 4 can be used to test this separately. Treat the mutation-count
  prior as suggestive, which is why every stratum keeps a nonzero quota.

Run:
    python requeue_structure_informed.py \
        --scores ../outputs/round2/model_scores.csv \
        --out ../outputs/round2/priority_cofold_queue.csv --limit 240
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import her2_common as hc
from stage2_generate_candidates import greedy_diverse

# Relative appetite per mutation count. Derived from round-1 means
# (5: 0.678, 6: 0.554, 7: 0.599, 8: 0.556) but deliberately flattened: the
# signal is noisy and partly confounded, so no stratum is starved.
DEFAULT_MUT_WEIGHTS = {5: 0.45, 6: 0.15, 7: 0.25, 8: 0.15}

# Relative appetite per branch, from round-1 observed interface quality
# (D 0.639, B 0.626, C 0.597, A 0.519). Every branch keeps representation so the
# submission still spans four mechanistic hypotheses.
DEFAULT_BRANCH_WEIGHTS = {"D_framework": 0.32, "B_interface": 0.28,
                          "C_mixed": 0.22, "A_h3": 0.18}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--scores", type=Path, default=base / "outputs" / "round2" / "model_scores.csv")
    ap.add_argument("--out", type=Path, default=base / "outputs" / "round2" / "priority_cofold_queue.csv")
    ap.add_argument("--limit", type=int, default=240)
    ap.add_argument("--consensus-floor-pct", type=float, default=20.0,
                    help="drop the worst N%% by sequence consensus before selecting")
    ap.add_argument("--priority", type=int, default=0,
                    help="rows to tag priority (0: round 1 already holds the priority tier)")
    ap.add_argument("--tier", default="extended")
    args = ap.parse_args()
    hc.assert_parent_integrity()

    with open(args.scores) as fh:
        reader = csv.DictReader(fh)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    print(f"[load] {len(rows)} ESM-scored candidates from {args.scores}")

    # --- floor on plausibility (not a maximand) --------------------------- #
    def consensus(r: dict) -> float:
        try:
            return float(r.get("sequence_consensus_score") or 0.0)
        except ValueError:
            return 0.0

    rows.sort(key=consensus)
    cut = int(len(rows) * args.consensus_floor_pct / 100.0)
    kept = rows[cut:]
    print(f"[floor] dropped worst {args.consensus_floor_pct}% by sequence consensus "
          f"({cut} rows); {len(kept)} remain")

    # --- revalidate: a requeue is a trust boundary ------------------------ #
    valid = []
    bad = 0
    for r in kept:
        v = hc.validate_candidate(r["full_scfv_sequence"], r["candidate_id"])
        if v.ok:
            r["_muts"] = v.mutation_count
            r["mutation_positions"] = [int(m[1:-1]) for m in v.mutations]
            valid.append(r)
        else:
            bad += 1
    if bad:
        print(f"[validate] dropped {bad} invalid candidates")
    print(f"[validate] {len(valid)} valid; mutation-count mix="
          f"{dict(sorted(Counter(r['_muts'] for r in valid).items()))}")

    # --- stratified allocation -------------------------------------------- #
    quota: dict[tuple[int, str], int] = {}
    for m, mw in DEFAULT_MUT_WEIGHTS.items():
        for b, bw in DEFAULT_BRANCH_WEIGHTS.items():
            quota[(m, b)] = max(1, round(args.limit * mw * bw))

    buckets: dict[tuple[int, str], list[dict]] = {}
    for r in valid:
        buckets.setdefault((r["_muts"], r.get("branch", "")), []).append(r)
    # Within a bucket, order by consensus descending so the floor still informs
    # which members of an equally-diverse set we take.
    for k in buckets:
        buckets[k].sort(key=consensus, reverse=True)

    selected: list[dict] = []
    shortfall: dict[str, int] = {}
    for k, n in sorted(quota.items()):
        pool = buckets.get(k, [])
        take = greedy_diverse(pool, min(n, len(pool))) if pool else []
        selected += take
        if len(take) < n:
            shortfall[f"{k[0]}:{k[1]}"] = n - len(take)

    # Top up from the best remaining if strata could not fill the budget.
    if len(selected) < args.limit:
        have = {r["candidate_id"] for r in selected}
        spare = [r for r in valid if r["candidate_id"] not in have]
        spare.sort(key=lambda r: (r["_muts"], -consensus(r)))
        selected += spare[: args.limit - len(selected)]
    selected = selected[: args.limit]

    print(f"[select] {len(selected)} designs")
    print(f"[select] mutation mix={dict(sorted(Counter(r['_muts'] for r in selected).items()))}")
    print(f"[select] branch  mix={dict(sorted(Counter(r.get('branch','') for r in selected).items()))}")
    if shortfall:
        print(f"[select] strata that could not fill quota: {shortfall}")

    out_fields = ["queue_order", "priority_tier"] + [f for f in fields if f != "queue_order"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=out_fields, extrasaction="ignore")
        w.writeheader()
        for i, r in enumerate(selected, 1):
            r = dict(r)
            r["queue_order"] = i
            r["priority_tier"] = "priority" if i <= args.priority else args.tier
            w.writerow(r)

    (args.out.parent / "requeue_manifest.json").write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_scores": str(args.scores), "candidates_available": len(rows),
        "consensus_floor_pct": args.consensus_floor_pct, "validated": len(valid),
        "selected": len(selected),
        "mutation_weights": DEFAULT_MUT_WEIGHTS, "branch_weights": DEFAULT_BRANCH_WEIGHTS,
        "mutation_mix": dict(sorted(Counter(r["_muts"] for r in selected).items())),
        "branch_mix": dict(sorted(Counter(r.get("branch", "") for r in selected).items())),
        "strata_shortfall": shortfall,
        "rationale": "Round-1 ipSAE correlations were negative for every sequence-plausibility "
                     "score (ablang2_additive -0.284 vs ipsae_min, -0.466 vs epitope recovery) "
                     "and strongest-negative for mutation_count (-0.499). Sequence consensus is "
                     "therefore used as a floor, not a maximand, and the budget is stratified "
                     "toward few-mutation and framework-biased designs.",
        "caveats": [
            "Not Bayesian optimisation: no experimental feedback is in the loop.",
            "ipSAE and epitope recovery are confidence measures, not affinity.",
            "The mutation-count prior is partly confounded by MSA reuse (a design further "
            "from the parent has weaker homolog support at more columns).",
        ],
    }, indent=2))
    print(f"[done] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
