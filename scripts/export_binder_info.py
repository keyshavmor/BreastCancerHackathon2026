#!/usr/bin/env python
"""Export per-design sequence and structural information for the winning binders.

For each selected design this writes a self-contained folder that someone can
hand to a collaborator without needing the pipeline:

    outputs/binders/<candidate_id>/
        sequence.fasta            full 242-aa scFv, with mutations in the header
        design.json               mutations, CDR/domain mapping, all scores, provenance
        complex.cif               the representative Boltz-2 model (scFv + HER2 domain IV)
        interface_contacts.csv    modelled scFv<->HER2 contacts with distances
        mutations.csv             per-substitution context: CDR, contact class, distance

Plus one roll-up table, ``outputs/binder_summary.csv``.

The exported structure is the **representative** seed - the replicate whose ipSAE
is closest to that design's mean - not its best seed. Picking the best would
misrepresent a design whose seeds disagree, which on this system is most of them.

Run:
    python export_binder_info.py --set top_15_scored --gifs
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import her2_common as hc
from stage5_score_ipsae import parse_cif_atoms, TARGET_CHAIN, BINDER_CHAIN

CONTACT_CUTOFF = 4.5


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


def representative_run(raw: list[dict], cid: str) -> dict | None:
    """The replicate whose ipSAE is nearest that design's mean across seeds."""
    runs = [r for r in raw
            if r.get("candidate_id") == cid and r.get("ipsae_status") == "PASSED"
            and fnum(r.get("ipsae_min")) is not None]
    if not runs:
        return None
    vals = [fnum(r["ipsae_min"]) for r in runs]
    mean = float(np.mean(vals))
    return min(runs, key=lambda r: abs(fnum(r["ipsae_min"]) - mean))


def interface_contacts(cif: Path, crop_start: int) -> list[dict]:
    """Modelled scFv-HER2 heavy-atom contacts within CONTACT_CUTOFF."""
    atoms = parse_cif_atoms(cif)
    tgt, bnd = atoms.get(TARGET_CHAIN), atoms.get(BINDER_CHAIN)
    if not tgt or not bnd:
        return []
    out = []
    tgt_ids = sorted(tgt)
    tgt_pts = {k: tgt[k] for k in tgt_ids}
    for bres in sorted(bnd):
        bp = bnd[bres]
        best = None
        for tres, tp in tgt_pts.items():
            d = float(np.linalg.norm(tp[None, :, :] - bp[:, None, :], axis=2).min())
            if d <= CONTACT_CUTOFF and (best is None or d < best[1]):
                best = (tres, d)
        if best:
            tres, d = best
            out.append({
                "scfv_pos": bres,
                "scfv_aa": hc.PARENT_SEQ[bres - 1] if bres <= hc.PARENT_LEN else "?",
                "scfv_domain": hc.domain_of(bres) if bres <= hc.PARENT_LEN else "?",
                "scfv_cdr": hc.cdr_of(bres) if bres <= hc.PARENT_LEN else "?",
                "her2_mature_pos": crop_start + tres - 1,
                "her2_uniprot_pos": crop_start + tres - 1 + hc.MATURE_TO_UNIPROT_OFFSET,
                "min_distance_A": round(d, 2),
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--results", type=Path, default=base / "outputs")
    ap.add_argument("--set", default="top_15_scored",
                    help="which CSV of designs to export (without .csv)")
    ap.add_argument("--outdir", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=0, help="0 = all in the set")
    args = ap.parse_args()
    out_root = args.outdir or (args.results / "binders")
    out_root.mkdir(parents=True, exist_ok=True)
    hc.assert_parent_integrity()

    contract = json.loads((args.results / "contract.json").read_text())
    crop_start = contract["target"]["domain_iv_mature"][0]
    target_seq = contract["target"]["domain_iv_sequence"]
    exp_epitope = set(contract["target"].get("epitope_direct_mature") or [])

    designs = read_csv(args.results / f"{args.set}.csv")
    if args.limit:
        designs = designs[: args.limit]
    raw = read_csv(args.results / "boltz_results_raw.csv")
    resmap = {int(r["scfv_pos_1based"]): r for r in read_csv(args.results / "residue_map.csv")}
    if not designs:
        raise SystemExit(f"no designs found in {args.set}.csv")
    print(f"[export] {len(designs)} designs from {args.set}.csv")

    summary = []
    for d in designs:
        cid = d["candidate_id"]
        seq = d["full_scfv_sequence"]
        v = hc.validate_candidate(seq, cid)
        folder = out_root / cid
        folder.mkdir(parents=True, exist_ok=True)

        muts = v.mutations
        hdr = (f"{cid} len={len(seq)} muts={len(muts)}:{','.join(muts)} "
               f"ipsae_min={d.get('ipsae_min','')} sha256={hc.sha256_seq(seq)}")
        hc.write_fasta(folder / "sequence.fasta", {hdr: seq})

        # Per-mutation structural context, from the experimental residue map.
        mut_rows = []
        for m in muts:
            pos = int(m[1:-1])
            rm = resmap.get(pos, {})
            mut_rows.append({
                "mutation": m, "position": pos,
                "parent_aa": m[0], "mutant_aa": m[-1],
                "domain": hc.domain_of(pos), "cdr": hc.cdr_of(pos),
                "experimental_contact_class": rm.get("contact_class", ""),
                "experimental_min_dist_to_HER2_A": rm.get("min_target_distance_A", ""),
                "pdb_chain": rm.get("pdb_chain", ""), "pdb_resnum": rm.get("pdb_resnum", ""),
            })
        with open(folder / "mutations.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(mut_rows[0]))
            w.writeheader()
            w.writerows(mut_rows)

        rep = representative_run(raw, cid)
        contacts: list[dict] = []
        cif_dest = ""
        if rep:
            src = Path(rep["structure_path"])
            if src.is_file():
                shutil.copy2(src, folder / "complex.cif")
                cif_dest = "complex.cif"
                pae_src = Path(rep.get("pae_path", ""))
                if pae_src.is_file():
                    shutil.copy2(pae_src, folder / "pae.npz")
                try:
                    contacts = interface_contacts(src, crop_start)
                except Exception as exc:                          # noqa: BLE001
                    print(f"  [warn] {cid} contacts: {type(exc).__name__}")
        if contacts:
            with open(folder / "interface_contacts.csv", "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(contacts[0]))
                w.writeheader()
                w.writerows(contacts)

        modelled_epitope = {c["her2_mature_pos"] for c in contacts}
        recovered = sorted(modelled_epitope & exp_epitope)
        mutated_at_interface = [r["mutation"] for r in mut_rows
                                if r["experimental_contact_class"] in ("direct", "near")]

        info = {
            "candidate_id": cid,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "sequence": {
                "full_scfv": seq, "length": len(seq), "sha256": hc.sha256_seq(seq),
                "vh": seq[hc.VH_RANGE[0] - 1 : hc.VH_RANGE[1]],
                "linker": seq[hc.LINKER_RANGE[0] - 1 : hc.LINKER_RANGE[1]],
                "vl": seq[hc.VL_RANGE[0] - 1 :],
                "native_cysteines_preserved": all(seq[c - 1] == "C" for c in hc.NATIVE_CYS),
            },
            "design": {
                "branch": d.get("branch", ""), "mutation_count": v.mutation_count,
                "mutations": muts,
                "mutated_cdrs": sorted({r["cdr"] for r in mut_rows}),
                "mutations_at_experimental_interface": mutated_at_interface,
                "reconstructible_from_parent":
                    hc.apply_mutations(muts, hc.PARENT_SEQ) == seq,
            },
            "scores": {k: d.get(k) for k in (
                "rank", "ipsae_min", "ipsae_min_sd", "ipsae_max", "ipsae_delta_vs_parent",
                "ipsae_interpretation", "interface_status", "n_seeds", "seeds",
                "iptm", "pDockQ", "LIS", "epitope_recovery",
                "ablang2_contextual", "esm2_contextual", "sequence_consensus_score",
                "rank_score", "max_rank_shift_under_reweighting") if k in d},
            "structure": {
                "representative_run": rep["name"] if rep else None,
                "representative_seed": rep.get("seed") if rep else None,
                "selection_rule": "replicate whose ipSAE is closest to the design mean",
                "cif": cif_dest,
                "target": {
                    "description": "HER2 domain IV crop from 1N8Z chain C",
                    "mature_range": contract["target"]["domain_iv_mature"],
                    "uniprot_range": contract["target"]["domain_iv_uniprot"],
                    "sequence": target_seq,
                },
                "modelled_interface": {
                    "n_contacts": len(contacts),
                    "her2_residues_contacted_mature": sorted(modelled_epitope),
                    "experimental_epitope_recovered": recovered,
                    "experimental_epitope_total": len(exp_epitope),
                    "recovery_fraction": (round(len(recovered) / len(exp_epitope), 4)
                                          if exp_epitope else None),
                },
            },
            "claim_boundary": "Scores are computational ranking signals for experimental "
                              "triage. No K_D is predicted or implied.",
        }
        (folder / "design.json").write_text(json.dumps(info, indent=2))

        summary.append({
            "candidate_id": cid, "branch": d.get("branch", ""),
            "rank": d.get("rank", ""), "mutation_count": v.mutation_count,
            "mutations": ";".join(muts),
            "mutated_cdrs": ";".join(sorted({r["cdr"] for r in mut_rows})),
            "interface_mutations": ";".join(mutated_at_interface),
            "ipsae_min": d.get("ipsae_min", ""), "ipsae_min_sd": d.get("ipsae_min_sd", ""),
            "ipsae_interpretation": d.get("ipsae_interpretation", ""),
            "interface_status": d.get("interface_status", ""),
            "n_seeds": d.get("n_seeds", ""), "iptm": d.get("iptm", ""),
            "epitope_recovery": d.get("epitope_recovery", ""),
            "modelled_contacts": len(contacts),
            "sequence_sha256": hc.sha256_seq(seq),
            "folder": str(folder.relative_to(args.results)),
            "full_scfv_sequence": seq,
        })
        print(f"  {cid}: {v.mutation_count} muts, {len(contacts)} modelled contacts"
              f"{'' if cif_dest else '  [no structure copied]'}")

    with open(args.results / "binder_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    hc.write_fasta(args.results / "binder_sequences.fasta",
                   {s["candidate_id"]: s["full_scfv_sequence"] for s in summary})
    print(f"[export] {len(summary)} binder folders -> {out_root}")
    print(f"[export] binder_summary.csv and binder_sequences.fasta -> {args.results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
