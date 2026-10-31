#!/usr/bin/env python
"""Merge cofold queues from several generation rounds into one ordered queue.

Why this exists: `candidate_id` is assigned by rank within a generation round,
so two rounds would both mint `HER2_0001` for *different* sequences. Stage 4
names its structures after the candidate id, and stage 5/6 join on it, so reusing
an id across rounds would silently bind an already-computed structure to the
wrong sequence. Each round therefore runs with its own `--id-prefix`, and this
script merges the results.

Two invariants are enforced:

1. **No duplicate ids.** A collision means two rounds shared a prefix; that is a
   hard error, not something to paper over.
2. **No duplicate sequences.** If a later round rediscovers a sequence an earlier
   round already queued, the earlier entry wins and the later one is dropped, so
   the same design is never cofolded twice under two names.

Earlier queues keep their relative order and priority tiers, so structures that
already exist stay at the front and stage 4's resume logic skips them.

Run:
    python merge_queues.py --out ../outputs/priority_cofold_queue_merged.csv \
        ../outputs/priority_cofold_queue.csv ../outputs/round2/priority_cofold_queue.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import her2_common as hc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queues", nargs="+", type=Path, help="queue CSVs, earliest round first")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit-per-queue", type=int, nargs="*", default=None,
                    help="optional per-queue cap, same order as the positional queues")
    ap.add_argument("--retier", action="store_true",
                    help="relabel tiers of later rounds as 'extended'")
    args = ap.parse_args()
    hc.assert_parent_integrity()

    merged: list[dict] = []
    seen_ids: dict[str, str] = {}
    seen_seqs: dict[str, str] = {}
    fields: list[str] = []
    stats: list[tuple[str, int, int, int]] = []

    for qi, q in enumerate(args.queues):
        if not q.is_file():
            raise SystemExit(f"missing queue {q}")
        with open(q) as fh:
            rows = list(csv.DictReader(fh))
            if not fields:
                fields = [f for f in (csv.DictReader(open(q)).fieldnames or [])]
        if args.limit_per_queue and qi < len(args.limit_per_queue):
            cap = args.limit_per_queue[qi]
            if cap > 0:
                rows = rows[:cap]

        kept = dup_id = dup_seq = 0
        for r in rows:
            cid, seq = r["candidate_id"], r["full_scfv_sequence"]
            if cid in seen_ids:
                raise SystemExit(
                    f"id collision: {cid} appears in both {seen_ids[cid]} and {q.name}. "
                    f"Re-run one round with a distinct --id-prefix; reusing ids would bind "
                    f"an existing structure to the wrong sequence.")
            if seq in seen_seqs:
                dup_seq += 1
                continue
            # Revalidate here too: a merge is a trust boundary between rounds.
            v = hc.validate_candidate(seq, cid)
            if not v.ok:
                raise SystemExit(f"{cid} from {q.name} fails validation: {v.failures}")
            seen_ids[cid] = q.name
            seen_seqs[seq] = cid
            if args.retier and qi > 0:
                r["priority_tier"] = "extended"
            merged.append(r)
            kept += 1
        stats.append((q.name, len(rows), kept, dup_seq))

    for i, r in enumerate(merged, 1):
        r["queue_order"] = i

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(merged)

    print("[merge] per-queue: name, read, kept, dropped_duplicate_sequence")
    for name, read, kept, dup in stats:
        print(f"  {name:48s} {read:>7} {kept:>7} {dup:>7}")
    tiers: dict[str, int] = {}
    for r in merged:
        tiers[r.get("priority_tier", "")] = tiers.get(r.get("priority_tier", ""), 0) + 1
    print(f"[merge] {len(merged)} unique designs -> {args.out}")
    print(f"[merge] tiers: {tiers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
