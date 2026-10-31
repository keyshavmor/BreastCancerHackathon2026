#!/usr/bin/env python
"""Build a balanced cofold queue for a controlled experiment, not a ranked screen.

Two uses:

``--mode sweep``
    Equal numbers of designs in every (mutation_count x branch) cell. This is a
    *designed experiment*: mutation count was the strongest predictor of
    interface quality we found (Spearman -0.50 against ipSAE on single-seed
    values, roughly -0.74 after correcting for measurement attenuation), but it
    was measured on an unbalanced, score-ranked sample. A balanced sweep with
    replicate seeds measures that curve properly instead of inferring it.

``--mode breadth``
    A large stratified sample for pool expansion, still spread across cells so
    the result is not dominated by whichever cell the sequence scores happened to
    favour. Deliberately **not** ranked by sequence plausibility, because those
    scores anti-correlate with interface quality for this affinity-matured parent.

Both modes select within a cell by farthest-point diversity on mutated-position
sets, so a cell is not filled with near-duplicates.

Input is any CSV carrying ``candidate_id``, ``full_scfv_sequence``, ``branch`` and
``mutation_count`` - e.g. a stage 2 shortlist or a stage 3 ``model_scores.csv``.

Run:
    python build_sweep_queue.py --mode sweep   --per-cell 15 --out ../outputs/queue_sweep.csv
    python build_sweep_queue.py --mode breadth --total 600   --out ../outputs/queue_breadth.csv
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

QUEUE_FIELDS = ["queue_order", "priority_tier", "candidate_id", "branch",
                "mutation_count", "mutations_1based", "sequence_sha256",
                "full_scfv_sequence"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--source", type=Path,
                    default=base / "outputs" / "round2" / "esm_shortlist.csv")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mode", choices=["sweep", "breadth"], default="sweep")
    ap.add_argument("--per-cell", type=int, default=15,
                    help="sweep mode: designs per (mutation_count x branch) cell")
    ap.add_argument("--total", type=int, default=600, help="breadth mode: total designs")
    ap.add_argument("--exclude", type=Path, nargs="*", default=[],
                    help="CSVs whose candidate_ids/sequences must not be reused")
    ap.add_argument("--tier", default="extended")
    args = ap.parse_args()
    hc.assert_parent_integrity()

    with open(args.source) as fh:
        rows = list(csv.DictReader(fh))
    print(f"[load] {len(rows)} candidates from {args.source.name}")

    # Never re-cofold something an earlier queue already covers.
    seen_ids: set[str] = set()
    seen_seqs: set[str] = set()
    for p in args.exclude:
        if not Path(p).is_file():
            continue
        with open(p) as fh:
            for r in csv.DictReader(fh):
                seen_ids.add(r.get("candidate_id", ""))
                seen_seqs.add(r.get("full_scfv_sequence", ""))
    if seen_ids:
        before = len(rows)
        rows = [r for r in rows
                if r["candidate_id"] not in seen_ids
                and r["full_scfv_sequence"] not in seen_seqs]
        print(f"[exclude] dropped {before - len(rows)} already-queued designs")

    # Revalidate: a queue handed to a GPU campaign is a trust boundary.
    cells: dict[tuple[int, str], list[dict]] = {}
    bad = 0
    for r in rows:
        v = hc.validate_candidate(r["full_scfv_sequence"], r["candidate_id"])
        if not v.ok:
            bad += 1
            continue
        r["mutation_count"] = v.mutation_count
        r["mutations_1based"] = ";".join(v.mutations)
        r["sequence_sha256"] = hc.sha256_seq(r["full_scfv_sequence"])
        r["mutation_positions"] = [int(m[1:-1]) for m in v.mutations]
        cells.setdefault((v.mutation_count, r.get("branch", "")), []).append(r)
    if bad:
        print(f"[validate] dropped {bad} invalid designs")

    counts = {f"{m}:{b}": len(v) for (m, b), v in sorted(cells.items())}
    print(f"[cells] {len(cells)} non-empty cells; availability={counts}")

    selected: list[dict] = []
    if args.mode == "sweep":
        short = {}
        for key in sorted(cells):
            pool = cells[key]
            take = greedy_diverse(pool, min(args.per_cell, len(pool)))
            selected += take
            if len(take) < args.per_cell:
                short[f"{key[0]}:{key[1]}"] = args.per_cell - len(take)
        if short:
            print(f"[sweep] cells short of --per-cell: {short}")
    else:
        per = max(1, args.total // max(1, len(cells)))
        for key in sorted(cells):
            selected += greedy_diverse(cells[key], min(per, len(cells[key])))
        # Top up round-robin so the total is hit without skewing one cell.
        if len(selected) < args.total:
            have = {r["candidate_id"] for r in selected}
            pools = {k: [r for r in v if r["candidate_id"] not in have] for k, v in cells.items()}
            keys = sorted(pools)
            i = 0
            while len(selected) < args.total and any(pools.values()):
                k = keys[i % len(keys)]
                if pools[k]:
                    selected.append(pools[k].pop(0))
                i += 1
        selected = selected[: args.total]

    mix_m = dict(sorted(Counter(r["mutation_count"] for r in selected).items()))
    mix_b = dict(sorted(Counter(r.get("branch", "") for r in selected).items()))
    print(f"[select] {len(selected)} designs | mutation mix={mix_m} | branch mix={mix_b}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=QUEUE_FIELDS, extrasaction="ignore")
        w.writeheader()
        for i, r in enumerate(selected, 1):
            r = dict(r)
            r["queue_order"] = i
            r["priority_tier"] = args.tier
            w.writerow(r)

    (args.out.with_suffix(".manifest.json")).write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode, "source": str(args.source),
        "per_cell": args.per_cell if args.mode == "sweep" else None,
        "total": len(selected),
        "mutation_mix": mix_m, "branch_mix": mix_b,
        "cell_availability": counts,
        "excluded_sources": [str(p) for p in args.exclude],
        "rationale": ("balanced designed experiment to measure the mutation-count curve "
                      if args.mode == "sweep" else
                      "stratified breadth sample, deliberately not ranked by sequence "
                      "plausibility because those scores anti-correlate with interface "
                      "quality for this affinity-matured parent"),
    }, indent=2))
    print(f"[done] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
