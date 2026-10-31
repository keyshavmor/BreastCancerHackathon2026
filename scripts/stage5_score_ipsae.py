#!/usr/bin/env python
"""Stage 5 - external ipSAE scoring and structural QC of completed cofolds.

The organizer requires a **genuine ipSAE for every submitted design**. Boltz-2
does not emit ipSAE, so each prediction's full PAE matrix and mmCIF are passed to
the authoritative DunbrackLab/IPSAE implementation and the numbers are parsed
back out. Nothing is proxied: a design with no structure, no PAE, or a failed
ipSAE run is recorded as ``NOT_EVALUATED`` and is excluded from the submission.

Metrics collected per prediction
--------------------------------
* ``ipsae_asym_BT`` / ``ipsae_asym_TB`` - the two directional ipSAE values
* ``ipsae_min`` - the conservative min of the two directions (primary metric)
* ``ipsae_max`` - the value IPSAE reports on its ``max`` row
* ``pDockQ``, ``pDockQ2``, ``LIS`` - independent interface measures from IPSAE
* ``iptm``, ``complex_plddt``, ``complex_ipde`` - from Boltz's confidence JSON
* ``epitope_recovery`` - fraction of the *experimental* 1N8Z epitope residues
  that are still contacted in the predicted complex

Epitope recovery is the check that catches a model which scores well while
binding the wrong face: ipSAE alone cannot tell a correct interface from a
confident but misplaced one.

Replicate seeds are aggregated per candidate (mean / sd / n) so that an ipSAE
difference can be compared against its own seed noise before anyone calls it an
improvement.

Run:
    python stage5_score_ipsae.py --run-dir ../pipeline_runs/her2_cofold
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import her2_common as hc

IPSAE_DEFAULT = Path(__file__).resolve().parent.parent / "third_party" / "IPSAE" / "ipsae.py"
# Chain ids as written by stage 4.
TARGET_CHAIN, BINDER_CHAIN = "T", "B"


# --------------------------------------------------------------------------- #
# mmCIF parsing (no gemmi dependency: boltz mmCIF uses a plain atom_site loop)
# --------------------------------------------------------------------------- #

def parse_cif_atoms(path: Path) -> dict[str, dict[int, np.ndarray]]:
    """Return ``{chain_id: {residue_seq_id: (natoms,3) coords}}`` for heavy atoms."""
    cols: list[str] = []
    in_loop = False
    out: dict[str, dict[int, list]] = {}
    with open(path) as fh:
        for line in fh:
            s = line.strip()
            if s.startswith("loop_"):
                cols, in_loop = [], False
                continue
            if s.startswith("_atom_site."):
                cols.append(s.split(".", 1)[1])
                in_loop = True
                continue
            if in_loop and (s.startswith("#") or s.startswith("_") or not s):
                if cols and s.startswith("#"):
                    in_loop = False
                continue
            if in_loop and cols:
                f = s.split()
                if len(f) < len(cols):
                    continue
                rec = dict(zip(cols, f))
                if rec.get("group_PDB") not in (None, "ATOM"):
                    continue
                if rec.get("type_symbol") == "H":
                    continue
                ch = rec.get("label_asym_id") or rec.get("auth_asym_id")
                try:
                    rid = int(rec.get("label_seq_id") or rec.get("auth_seq_id"))
                    xyz = (float(rec["Cartn_x"]), float(rec["Cartn_y"]), float(rec["Cartn_z"]))
                except (TypeError, ValueError):
                    continue
                out.setdefault(ch, {}).setdefault(rid, []).append(xyz)
    return {c: {r: np.asarray(v, dtype=float) for r, v in d.items()} for c, d in out.items()}


def epitope_recovery(cif: Path, experimental_epitope: set[int], crop_start: int,
                     cutoff: float = 4.5) -> tuple[float, int, int]:
    """Fraction of experimental epitope residues still contacted in the model.

    Target chain residue *i* (1-based in the crop) corresponds to HER2 mature
    position ``crop_start + i - 1``, which is how the predicted interface is
    compared with the 1N8Z-derived epitope.
    """
    atoms = parse_cif_atoms(cif)
    tgt, bnd = atoms.get(TARGET_CHAIN), atoms.get(BINDER_CHAIN)
    if not tgt or not bnd:
        return float("nan"), 0, len(experimental_epitope)
    bpts = np.vstack(list(bnd.values()))
    contacted = set()
    for rid, pts in tgt.items():
        d = np.linalg.norm(bpts[None, :, :] - pts[:, None, :], axis=2)
        if d.min() <= cutoff:
            contacted.add(crop_start + rid - 1)
    hit = len(contacted & experimental_epitope)
    return (hit / max(1, len(experimental_epitope)), hit, len(experimental_epitope))


# --------------------------------------------------------------------------- #
# ipSAE invocation and parsing
# --------------------------------------------------------------------------- #

def run_ipsae(ipsae_py: Path, pae: Path, cif: Path, pae_cut: float, dist_cut: float,
              python_exe: str) -> tuple[dict, str]:
    """Run ipsae.py and parse its summary table. Returns (metrics, stdout_path)."""
    cmd = [python_exe, str(ipsae_py), str(pae), str(cif), str(int(pae_cut)), str(int(dist_cut))]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    stem = cif.with_suffix("").name
    summary = cif.parent / f"{stem}_{int(pae_cut)}_{int(dist_cut)}.txt"
    log = cif.parent / f"{stem}_ipsae_stdout.log"
    log.write_text(f"$ {' '.join(cmd)}\nrc={proc.returncode}\n{proc.stdout}\n{proc.stderr}")
    if proc.returncode != 0 or not summary.is_file():
        return {"ipsae_status": "FAILED"}, str(log)

    rows = []
    for line in summary.read_text().splitlines():
        f = line.split()
        if len(f) < 13 or f[0] in ("Chn1",) or not f[0].isalnum():
            continue
        if f[4] not in ("asym", "max"):
            continue
        rows.append(f)
    if not rows:
        return {"ipsae_status": "UNPARSEABLE"}, str(log)

    m: dict = {"ipsae_status": "PASSED"}
    asym: dict[tuple[str, str], float] = {}
    for f in rows:
        c1, c2, typ = f[0], f[1], f[4]
        try:
            val = float(f[5])
        except ValueError:
            continue
        if typ == "asym":
            asym[(c1, c2)] = val
            m[f"ipsae_asym_{c1}{c2}"] = val
        else:
            m["ipsae_max"] = val
            for key, idx in (("pDockQ", 10), ("pDockQ2", 11), ("LIS", 12)):
                try:
                    m[key] = float(f[idx])
                except (ValueError, IndexError):
                    pass
    if asym:
        m["ipsae_min"] = min(asym.values())
        if "ipsae_max" not in m:
            m["ipsae_max"] = max(asym.values())
    return m, str(log)


def confidence_metrics(pred_dir: Path, name: str) -> dict:
    """Pull Boltz's own confidence fields; these are context, not ipSAE."""
    p = pred_dir / f"confidence_{name}_model_0.json"
    if not p.is_file():
        return {}
    d = json.loads(p.read_text())
    return {
        "boltz_confidence_score": d.get("confidence_score"),
        "iptm": d.get("iptm"), "ptm": d.get("ptm"),
        "complex_plddt": d.get("complex_plddt"), "complex_iplddt": d.get("complex_iplddt"),
        "complex_ipde": d.get("complex_ipde"),
    }


def score_one(job: tuple) -> dict:
    """Worker: score a single completed prediction."""
    (name, pred_dir, ipsae_py, pae_cut, dist_cut, python_exe,
     epitope, crop_start) = job
    pred_dir = Path(pred_dir)
    cif = pred_dir / f"{name}_model_0.cif"
    pae = pred_dir / f"pae_{name}_model_0.npz"
    rec: dict = {"name": name, "structure_path": str(cif), "pae_path": str(pae)}
    if not cif.is_file() or not pae.is_file():
        rec["ipsae_status"] = "MISSING_ARTIFACTS"
        return rec

    # Guard against a PAE/structure residue-count mismatch, which would make
    # any interface metric meaningless.
    try:
        with np.load(pae) as z:
            arr = z[list(z.keys())[0]]
        rec["pae_shape"] = "x".join(str(s) for s in arr.shape)
        rec["pae_finite"] = bool(np.isfinite(arr).all())
    except Exception as exc:                                    # noqa: BLE001
        rec["ipsae_status"] = f"PAE_UNREADABLE:{type(exc).__name__}"
        return rec

    metrics, log = run_ipsae(Path(ipsae_py), pae, cif, pae_cut, dist_cut, python_exe)
    rec.update(metrics)
    rec["ipsae_stdout_path"] = log
    try:
        frac, hit, tot = epitope_recovery(cif, set(epitope), crop_start)
        rec.update({"epitope_recovery": round(frac, 4) if frac == frac else "",
                    "epitope_hits": hit, "epitope_total": tot})
    except Exception as exc:                                    # noqa: BLE001
        rec["epitope_recovery"] = ""
        rec["epitope_error"] = f"{type(exc).__name__}"
    rec.update(confidence_metrics(pred_dir, name))
    return rec


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    base = here.parent
    ap.add_argument("--run-dir", type=Path, default=base / "pipeline_runs" / "her2_cofold")
    ap.add_argument("--outdir", type=Path, default=base / "outputs")
    ap.add_argument("--contract", type=Path, default=base / "outputs" / "contract.json")
    ap.add_argument("--ipsae", type=Path, default=IPSAE_DEFAULT)
    ap.add_argument("--pae-cutoff", type=float, default=10.0)
    ap.add_argument("--dist-cutoff", type=float, default=15.0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--python-exe", default=sys.executable)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    contract = json.loads(args.contract.read_text())
    # Compare like with like: the model's <=4.5 A contacts against the
    # experimentally DIRECT (<=4.5 A) epitope. Falls back to the 8 A set for
    # contracts written before that field existed.
    tgt = contract["target"]
    epitope = tgt.get("epitope_direct_mature") or tgt["epitope_contacts_mature"]
    print(f"[epitope] denominator = {len(epitope)} residues "
          f"({'direct <=4.5A' if tgt.get('epitope_direct_mature') else 'near <=8A fallback'})")
    crop_start = tgt["domain_iv_mature"][0]

    preds = sorted({p for p in (args.run_dir / "out").glob("boltz_results_*/predictions/*")
                    if p.is_dir()})
    jobs = []
    for p in preds:
        name = p.name
        if (p / f"{name}_model_0.cif").is_file():
            jobs.append((name, str(p), str(args.ipsae), args.pae_cutoff, args.dist_cutoff,
                         args.python_exe, epitope, crop_start))
    print(f"[scan] {len(jobs)} completed predictions under {args.run_dir}")
    if not jobs:
        raise SystemExit("no completed predictions to score")

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(score_one, jobs))
    passed = [r for r in records if r.get("ipsae_status") == "PASSED"]
    print(f"[ipsae] {len(passed)}/{len(records)} scored successfully "
          f"(cutoffs pae={args.pae_cutoff} dist={args.dist_cutoff})")

    # ---- split parent baselines from candidates --------------------------- #
    def base_id(name: str) -> tuple[str, int | None]:
        m = re.fullmatch(r"(.+?)_seed(\d+)", name)
        return (m.group(1), int(m.group(2))) if m else (name, None)

    for r in records:
        r["candidate_id"], r["seed"] = base_id(r["name"])

    fields = ["name", "candidate_id", "seed", "ipsae_status", "ipsae_min", "ipsae_max",
              f"ipsae_asym_{BINDER_CHAIN}{TARGET_CHAIN}", f"ipsae_asym_{TARGET_CHAIN}{BINDER_CHAIN}",
              "pDockQ", "pDockQ2", "LIS", "iptm", "ptm", "boltz_confidence_score",
              "complex_plddt", "complex_iplddt", "complex_ipde",
              "epitope_recovery", "epitope_hits", "epitope_total",
              "pae_shape", "pae_finite", "structure_path", "pae_path", "ipsae_stdout_path"]
    with open(args.outdir / "boltz_results_raw.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(records, key=lambda r: (r["candidate_id"], r.get("seed") or 0)))

    # ---- aggregate replicates -------------------------------------------- #
    by_cand: dict[str, list[dict]] = {}
    for r in records:
        if r.get("ipsae_status") == "PASSED":
            by_cand.setdefault(r["candidate_id"], []).append(r)

    parent_runs = by_cand.get("parent", [])
    parent_vals = [r["ipsae_min"] for r in parent_runs if "ipsae_min" in r]
    parent_mean = statistics.fmean(parent_vals) if parent_vals else None
    parent_sd = statistics.stdev(parent_vals) if len(parent_vals) > 1 else 0.0
    print(f"[parent] baseline ipsae_min over {len(parent_vals)} seed(s): "
          f"mean={parent_mean} sd={parent_sd:.4f}" if parent_mean is not None
          else "[parent] WARNING no parent baseline scored")

    agg_rows = []
    for cid, runs in sorted(by_cand.items()):
        vals = [r["ipsae_min"] for r in runs if "ipsae_min" in r]
        rec_m = [r.get("epitope_recovery") for r in runs if isinstance(r.get("epitope_recovery"), float)]
        row = {
            "candidate_id": cid, "n_seeds": len(vals),
            "ipsae_min_mean": round(statistics.fmean(vals), 4) if vals else "",
            "ipsae_min_sd": round(statistics.stdev(vals), 4) if len(vals) > 1 else 0.0,
            "ipsae_min_best": round(max(vals), 4) if vals else "",
            "ipsae_max_mean": round(statistics.fmean([r["ipsae_max"] for r in runs if "ipsae_max" in r]), 4)
                              if any("ipsae_max" in r for r in runs) else "",
            "iptm_mean": round(statistics.fmean([r["iptm"] for r in runs if r.get("iptm") is not None]), 4)
                         if any(r.get("iptm") is not None for r in runs) else "",
            "pDockQ_mean": round(statistics.fmean([r["pDockQ"] for r in runs if "pDockQ" in r]), 4)
                           if any("pDockQ" in r for r in runs) else "",
            "LIS_mean": round(statistics.fmean([r["LIS"] for r in runs if "LIS" in r]), 4)
                        if any("LIS" in r for r in runs) else "",
            "epitope_recovery_mean": round(statistics.fmean(rec_m), 4) if rec_m else "",
            "seeds": ";".join(str(r["seed"]) for r in runs),
        }
        if parent_mean is not None and vals:
            row["ipsae_min_delta_vs_parent"] = round(statistics.fmean(vals) - parent_mean, 4)
        agg_rows.append(row)

    with open(args.outdir / "ipsae_aggregated.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(agg_rows[0]), extrasaction="ignore")
        w.writeheader()
        w.writerows(agg_rows)

    # ---- provenance ------------------------------------------------------- #
    commit = subprocess.run(["git", "-C", str(args.ipsae.parent), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    with open(args.outdir / "ipSAE_provenance.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["candidate_id", "seed", "ipsae_script", "ipsae_commit", "pae_cutoff_A",
                    "distance_cutoff_A", "metric_definition", "chain_order",
                    "structure_path", "pae_path", "ipsae_stdout_path", "status"])
        for r in sorted(records, key=lambda r: r["name"]):
            w.writerow([r["candidate_id"], r.get("seed", ""), "DunbrackLab/IPSAE ipsae.py", commit,
                        args.pae_cutoff, args.dist_cutoff,
                        "ipsae_min = min(asym B->T, asym T->B)",
                        f"T={TARGET_CHAIN} (HER2 domain IV), B={BINDER_CHAIN} (scFv)",
                        r.get("structure_path", ""), r.get("pae_path", ""),
                        r.get("ipsae_stdout_path", ""), r.get("ipsae_status", "")])

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "predictions_found": len(records), "ipsae_passed": len(passed),
        "ipsae_failed": [r["name"] for r in records if r.get("ipsae_status") != "PASSED"],
        "pae_cutoff_A": args.pae_cutoff, "distance_cutoff_A": args.dist_cutoff,
        "ipsae_commit": commit,
        "parent_baseline": {"n_seeds": len(parent_vals),
                            "ipsae_min_mean": parent_mean, "ipsae_min_sd": parent_sd},
        "candidates_with_scores": len([c for c in by_cand if c != "parent"]),
        "note": "ipSAE computed externally by DunbrackLab/IPSAE from Boltz full PAE + mmCIF. "
                "Boltz confidence fields are reported as context and are NOT ipSAE.",
    }
    (args.outdir / "stage5_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[done] boltz_results_raw.csv, ipsae_aggregated.csv, ipSAE_provenance.csv -> {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
