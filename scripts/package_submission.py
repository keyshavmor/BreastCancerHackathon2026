#!/usr/bin/env python
"""Assemble the exact artifact layout the execution brief asks for.

The brief specifies `outputs/boltz_parent/` and `outputs/boltz_candidates/`
alongside the CSV/FASTA deliverables. The pipeline writes structures into
timestamped run directories instead, which is better for resumability but does
not match the requested tree, so this collects the relevant structures into the
expected locations.

For each design one **representative** replicate is copied: the seed whose ipSAE
is closest to that design's mean. Copying the best seed would flatter designs
whose replicates disagree, which is most of them.

Each directory gets a MANIFEST.csv mapping file to design, seed and ipSAE, so a
reviewer can tie any structure back to a row of the submission table.

Run:
    python package_submission.py --set top_50_scored
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import statistics as st
from collections import defaultdict
from pathlib import Path

import her2_common as hc


def fnum(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def read_csv(p: Path) -> list[dict]:
    if not p.is_file():
        return []
    with open(p) as fh:
        return list(csv.DictReader(fh))


def copy_set(runs: dict[str, list[dict]], ids: list[str], dest: Path,
             label: str) -> list[dict]:
    """Copy one representative structure + PAE per design into ``dest``."""
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    for cid in ids:
        reps = runs.get(cid, [])
        if not reps:
            continue
        vals = [fnum(r["ipsae_min"]) for r in reps]
        vals = [v for v in vals if v is not None]
        if not vals:
            continue
        mean = st.fmean(vals)
        rep = min(reps, key=lambda r: abs(fnum(r["ipsae_min"]) - mean))
        cif, pae = Path(rep["structure_path"]), Path(rep.get("pae_path", ""))
        if not cif.is_file():
            continue
        shutil.copy2(cif, dest / f"{cid}.cif")
        if pae.is_file():
            shutil.copy2(pae, dest / f"{cid}_pae.npz")
        rows.append({
            "candidate_id": cid,
            "structure_file": f"{cid}.cif",
            "pae_file": f"{cid}_pae.npz" if pae.is_file() else "",
            "representative_seed": rep.get("seed", ""),
            "ipsae_min_this_seed": round(fnum(rep["ipsae_min"]), 4),
            "ipsae_min_mean_all_seeds": round(mean, 4),
            "ipsae_min_sd_all_seeds": round(st.stdev(vals), 4) if len(vals) > 1 else 0.0,
            "n_seeds": len(vals),
            "selection_rule": "seed closest to the design mean",
        })
    if rows:
        with open(dest / "MANIFEST.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"[package] {label}: {len(rows)} structures -> {dest}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--results", type=Path, default=base / "outputs")
    ap.add_argument("--set", default="top_50_scored")
    args = ap.parse_args()
    o = args.results
    hc.assert_parent_integrity()

    raw = [r for r in read_csv(o / "boltz_results_raw.csv")
           if r.get("ipsae_status") == "PASSED"]
    runs: dict[str, list[dict]] = defaultdict(list)
    for r in raw:
        runs[r["candidate_id"]].append(r)

    copy_set(runs, ["parent"], o / "boltz_parent", "parent baseline")
    ids = [r["candidate_id"] for r in read_csv(o / f"{args.set}.csv")]
    cand_rows = copy_set(runs, ids, o / "boltz_candidates", f"{args.set} candidates")

    # A top-level index so the required tree is navigable without this script.
    required = {
        "inputs/organizer_parent_scfv.fasta": "frozen organizer parent, SHA-256 verified",
        "outputs/contract.yaml": "rules, parent, target definition and checksums",
        "outputs/residue_map.csv": "per-residue scFv <-> 1N8Z mapping with contact classes",
        "outputs/internal_50_candidates.csv": "curated 50-proposal pool",
        "outputs/submission_scored.csv": "every design with a genuine external ipSAE",
        "outputs/ranked_winners.csv": "ranked 50 with full statistics (also .xlsx/.fasta)",
        "outputs/top_15_scored.csv": "lab nominations",
        "outputs/boltz_parent/": "parent structure + PAE, representative seed",
        "outputs/boltz_candidates/": "one structure + PAE per submitted design",
        "outputs/ipSAE_provenance.csv": "ipSAE script commit, cutoffs, chain order, paths",
        "outputs/method_walkthrough.md": "the design-method deliverable",
        "outputs/compliance_audit.json": "PASS/FAIL checks computed from real files",
        "outputs/organizer_compliance.json": "the organizer's recap, verified point by point",
        "outputs/run_manifest.json": "commit, weights, counts, claim boundary",
        "outputs/figures/": "nine campaign figures",
        "outputs/gifs/": "rotating 3D animations, parent and winners",
        "outputs/binders/": "per-design package: sequence, structure, PAE, contacts",
        "outputs/reports/": "local, Modal and final-designs reports",
        "outputs/slides_assets/": "presentation bundle incl. the Lovable prompt",
    }
    present = {k: (base / k).exists() for k in required}
    lines = ["# Submission index", "",
             "Everything the execution brief asks for, and where it is.", "",
             "| Artifact | Present | What it is |", "| --- | :-: | --- |"]
    lines += [f"| `{k}` | {'yes' if present[k] else 'MISSING'} | {v} |"
              for k, v in required.items()]
    lines += ["", f"Parent structure: `outputs/boltz_parent/parent.cif` "
                  f"(+ `parent_pae.npz`), representative of its replicate seeds.",
              f"Candidate structures: {len(cand_rows)} in `outputs/boltz_candidates/`, "
              f"one per submitted design, each with its PAE and a MANIFEST.csv row.", "",
              "**Claim boundary.** ipSAE is interface confidence from a structure "
              "predictor, not a binding affinity. No K_D is predicted anywhere in this "
              "submission."]
    (o / "SUBMISSION_INDEX.md").write_text("\n".join(lines) + "\n")
    missing = [k for k, v in present.items() if not v]
    print(f"[package] SUBMISSION_INDEX.md written; missing artifacts: {missing or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
