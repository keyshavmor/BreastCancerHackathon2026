#!/usr/bin/env python
"""Stage 1 - target preparation and residue mapping for the HER2 scFv challenge.

Derives, from primary data only (RCSB 1N8Z + UniProt P04626), everything the
later stages need to decide *where* it is sensible to mutate:

1. verify the frozen organizer parent (length, SHA-256, linker, cysteines);
2. align parent V_H/V_L to 1N8Z chains B/A and prove the mapping residue-by-residue;
3. measure every scFv residue's minimum heavy-atom distance to HER2 chain C;
4. crop HER2 to **domain IV only**, choosing a boundary that splits no disulfide;
5. emit ``residue_map.csv``, ``her2_domain_iv.fasta``, ``contract.yaml`` and a report.

Why domain IV only: the organizer forbids cofolding the ~630-residue ectodomain.
Trastuzumab's epitope lies entirely in domain IV, so the crop loses no contact
while cutting the complex from ~850 to ~361 residues - the single largest
throughput lever in the whole pipeline.

Run:
    python stage1_target_prep.py --outdir ../outputs
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import her2_common as hc

AA3 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q", "GLU": "E",
    "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F",
    "PRO": "P", "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}

# Interface geometry bins. These are exploratory distance classes for choosing
# mutation sites, NOT learned affinity thresholds - see the report's caveat.
DIRECT_CUTOFF_A = 4.5
NEAR_CUTOFF_A = 8.0


# --------------------------------------------------------------------------- #
# PDB parsing
# --------------------------------------------------------------------------- #

def parse_pdb(path: Path):
    """Parse ATOM/SEQRES/SSBOND. Returns (atoms, seqres, ssbonds).

    ``atoms``  : chain -> {(resnum, icode): {"resn": str, "xyz": (N,3) array}}
    ``seqres`` : chain -> one-letter sequence string
    ``ssbonds``: list of (chain1, res1, chain2, res2)
    """
    raw: dict[str, dict[tuple[int, str], dict]] = {}
    seqres: dict[str, list[str]] = {}
    ssbonds: list[tuple[str, int, str, int]] = []

    with open(path) as fh:
        for line in fh:
            rec = line[:6]
            if rec == "SEQRES":
                seqres.setdefault(line[11], []).extend(line[19:].split())
            elif rec == "SSBOND":
                ssbonds.append((line[15], int(line[17:21]), line[29], int(line[31:35])))
            elif rec == "ATOM  ":
                element = (line[76:78].strip() or line[12:16].strip()[:1])
                if element == "H":          # ignore hydrogens for distance work
                    continue
                ch, rn, ic = line[21], int(line[22:26]), line[26]
                key = (rn, ic)
                slot = raw.setdefault(ch, {}).setdefault(key, {"resn": line[17:20].strip(), "xyz": []})
                slot["xyz"].append((float(line[30:38]), float(line[38:46]), float(line[46:54])))

    atoms = {
        ch: {k: {"resn": v["resn"], "xyz": np.asarray(v["xyz"], dtype=float)} for k, v in res.items()}
        for ch, res in raw.items()
    }
    seqs = {ch: "".join(AA3.get(r, "X") for r in lst) for ch, lst in seqres.items()}
    return atoms, seqs, ssbonds


def min_distance_matrix(chain_res: dict, target_pts: np.ndarray) -> dict:
    """Minimum heavy-atom distance from each residue of a chain to a point cloud."""
    out = {}
    for key, rec in chain_res.items():
        d = np.linalg.norm(target_pts[None, :, :] - rec["xyz"][:, None, :], axis=2)
        out[key] = float(d.min())
    return out


def contact_class(dist: float) -> str:
    if dist <= DIRECT_CUTOFF_A:
        return "direct"
    if dist <= NEAR_CUTOFF_A:
        return "near"
    return "distal"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    ap.add_argument("--pdb", type=Path, default=here.parent / "reference_data" / "1N8Z.pdb")
    ap.add_argument("--uniprot", type=Path, default=here.parent / "reference_data" / "P04626.fasta")
    ap.add_argument("--outdir", type=Path, default=here.parent / "outputs")
    ap.add_argument("--domain-iv-start", type=int, default=hc.HER2_DOMAIN_IV_MATURE[0],
                    help="HER2 mature-numbering start of the domain IV crop")
    ap.add_argument("--domain-iv-end", type=int, default=hc.HER2_DOMAIN_IV_MATURE[1])
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    # -- 1. parent integrity ------------------------------------------------ #
    hc.assert_parent_integrity()
    spans = hc.cdr_spans()
    print(f"[ok] parent verified: 242 aa, sha256={hc.PARENT_SHA256[:16]}..., cys={hc.NATIVE_CYS}")

    # -- 2. structure + chain mapping --------------------------------------- #
    atoms, seqres, ssbonds = parse_pdb(args.pdb)
    for ch in "ABC":
        if ch not in atoms:
            raise SystemExit(f"chain {ch} missing from {args.pdb}")

    # 1N8Z chains A/B are numbered 1..N with no insertion codes and no gaps,
    # so the scFv variable domains map by direct index. Assert rather than assume.
    for ch in "AB":
        keys = sorted(atoms[ch])
        assert all(ic == " " for _, ic in keys), f"chain {ch} has insertion codes"
        assert [rn for rn, _ in keys] == list(range(1, len(keys) + 1)), f"chain {ch} not 1..N contiguous"

    vh_parent = hc.PARENT_SEQ[hc.VH_RANGE[0] - 1 : hc.VH_RANGE[1]]
    vl_parent = hc.PARENT_SEQ[hc.VL_RANGE[0] - 1 : hc.VL_RANGE[1]]
    vh_pdb = seqres["B"][: len(vh_parent)]
    vl_pdb = seqres["A"][: len(vl_parent)]
    vh_mismatch = [(i + 1, a, b) for i, (a, b) in enumerate(zip(vh_parent, vh_pdb)) if a != b]
    vl_mismatch = [(i + 1, a, b) for i, (a, b) in enumerate(zip(vl_parent, vl_pdb)) if a != b]
    print(f"[ok] V_H vs 1N8Z:B[1-120] mismatches={len(vh_mismatch)} {vh_mismatch}")
    print(f"[ok] V_L vs 1N8Z:A[1-107] mismatches={len(vl_mismatch)} {vl_mismatch}")

    # -- 3. distances to HER2 ----------------------------------------------- #
    her2_pts = np.vstack([r["xyz"] for r in atoms["C"].values()])
    dist_b = min_distance_matrix(atoms["B"], her2_pts)
    dist_a = min_distance_matrix(atoms["A"], her2_pts)

    rows = []
    for pos in range(1, hc.PARENT_LEN + 1):
        dom = hc.domain_of(pos)
        if dom == "VH":
            chain, resnum, dom_pos = "B", pos, pos
        elif dom == "VL":
            chain, resnum, dom_pos = "A", pos - hc.VL_RANGE[0] + 1, pos - hc.VL_RANGE[0] + 1
        else:
            chain, resnum, dom_pos = "", None, pos - hc.LINKER_RANGE[0] + 1

        dist, pdb_aa, resolved = "", "", False
        if chain:
            key = (resnum, " ")
            dmap = dist_b if chain == "B" else dist_a
            if key in dmap:
                dist = round(dmap[key], 2)
                pdb_aa = AA3.get(atoms[chain][key]["resn"], "X")
                resolved = True

        rows.append({
            "scfv_pos_1based": pos,
            "parent_aa": hc.PARENT_SEQ[pos - 1],
            "domain": dom,
            "domain_pos": dom_pos,
            "cdr_name": hc.cdr_of(pos, spans),
            "pdb_chain": chain,
            "pdb_resnum": resnum if resnum is not None else "",
            "pdb_aa": pdb_aa,
            "resolved_in_pdb": resolved,
            "min_target_distance_A": dist,
            "contact_class": contact_class(dist) if dist != "" else "unmapped",
            "is_native_cys": pos in hc.NATIVE_CYS,
            "is_linker": dom == "linker",
            "mutable": dom != "linker" and pos not in hc.NATIVE_CYS,
        })

    map_path = args.outdir / "residue_map.csv"
    with open(map_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n_direct = sum(1 for r in rows if r["contact_class"] == "direct")
    n_near = sum(1 for r in rows if r["contact_class"] == "near")
    print(f"[ok] residue_map.csv: {len(rows)} rows, direct={n_direct} near={n_near}")

    # -- 4. HER2 domain IV crop --------------------------------------------- #
    lo, hi = args.domain_iv_start, args.domain_iv_end
    her2_mature = seqres["C"]                       # mature numbering: index i -> residue i+1
    crop_seq = her2_mature[lo - 1 : hi]

    # A crop that breaks a disulfide would fold into something unphysical.
    c_bonds = [(r1, r2) for c1, r1, c2, r2 in ssbonds if c1 == "C" and c2 == "C"]
    split = [(a, b) for a, b in c_bonds if (lo <= a <= hi) != (lo <= b <= hi)]
    inside = [(a, b) for a, b in c_bonds if lo <= a <= hi and lo <= b <= hi]
    if split:
        raise SystemExit(f"crop {lo}-{hi} splits disulfide(s) {split}; refusing to write a broken target")
    print(f"[ok] domain IV crop mature {lo}-{hi} ({len(crop_seq)} aa), "
          f"{len(inside)} intact disulfides, 0 split")

    # Every observed contact must survive the crop, else the epitope is clipped.
    contact_res = sorted(k[0] for k, d in min_distance_matrix(
        atoms["C"], np.vstack([r["xyz"] for ch in "AB" for r in atoms[ch].values()])).items()
        if d <= NEAR_CUTOFF_A)
    outside = [r for r in contact_res if not lo <= r <= hi]
    if outside:
        raise SystemExit(f"crop excludes contact residues {outside}")
    print(f"[ok] all {len(contact_res)} contact residues (mature {contact_res[0]}-{contact_res[-1]}) inside crop")

    hc.write_fasta(args.outdir / "her2_domain_iv.fasta", {
        f"HER2_domainIV_1N8Z_C_mature{lo}-{hi}_uniprot"
        f"{lo+hc.MATURE_TO_UNIPROT_OFFSET}-{hi+hc.MATURE_TO_UNIPROT_OFFSET}": crop_seq})

    # Cross-check the crop against UniProt so a bad PDB SEQRES cannot slip through.
    up = "".join(l.strip() for l in open(args.uniprot) if not l.startswith(">"))
    up_crop = up[lo + hc.MATURE_TO_UNIPROT_OFFSET - 1 : hi + hc.MATURE_TO_UNIPROT_OFFSET]
    print(f"[{'ok' if up_crop == crop_seq else 'FAIL'}] crop matches UniProt P04626 "
          f"{lo+hc.MATURE_TO_UNIPROT_OFFSET}-{hi+hc.MATURE_TO_UNIPROT_OFFSET}")
    if up_crop != crop_seq:
        raise SystemExit("PDB SEQRES and UniProt disagree over the domain IV crop")

    # -- 5. contract -------------------------------------------------------- #
    contract = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "parent": {
            "sequence": hc.PARENT_SEQ, "length": hc.PARENT_LEN, "sha256": hc.PARENT_SHA256,
            "vh_range": list(hc.VH_RANGE), "linker_range": list(hc.LINKER_RANGE),
            "vl_range": list(hc.VL_RANGE), "native_cysteines": list(hc.NATIVE_CYS),
        },
        "organizer_rules": {
            "min_mutations_vs_parent": hc.MIN_MUTATIONS, "max_length": hc.MAX_LEN,
            "topology": "VH-(GGGGS)3-VL", "forbidden_tools": ["RFdiffusion", "BindCraft", "BoltzGen"],
            "cofold_target": "HER2 domain IV only - never the full ectodomain",
            "required_deliverables": ["designed sequences", "actual ipSAE per submitted design",
                                      "method walkthrough"],
        },
        "self_imposed_policy": {
            "fixed_length": 242, "mutation_band": [hc.MIN_MUTATIONS, hc.MAX_MUTATIONS_POLICY],
            "edit_linker": False, "edit_native_cysteines": False, "introduce_cysteines": False,
            "introduce_nglyc_sequons": False,
        },
        "target": {
            "source_pdb": "1N8Z", "uniprot": "P04626",
            "chain_map": {"A": "Fab light", "B": "Fab heavy", "C": "HER2 ectodomain"},
            "mature_to_uniprot_offset": hc.MATURE_TO_UNIPROT_OFFSET,
            "domain_iv_mature": [lo, hi],
            "domain_iv_uniprot": [lo + hc.MATURE_TO_UNIPROT_OFFSET, hi + hc.MATURE_TO_UNIPROT_OFFSET],
            "domain_iv_length": len(crop_seq),
            "domain_iv_sequence": crop_seq,
            "intact_disulfides_in_crop": [list(b) for b in inside],
            "epitope_contacts_mature": contact_res,
            "complex_residues_for_boltz": hc.PARENT_LEN + len(crop_seq),
        },
        "geometry_bins": {"direct_A": DIRECT_CUTOFF_A, "near_A": NEAR_CUTOFF_A,
                          "note": "exploratory distance classes, not affinity thresholds"},
        "cdr_spans_kabat": {k: list(v) for k, v in spans.items()},
    }
    (args.outdir / "contract.yaml").write_text(_to_yaml(contract))
    (args.outdir / "contract.json").write_text(json.dumps(contract, indent=2))

    # -- 6. human-readable report ------------------------------------------- #
    direct_rows = [r for r in rows if r["contact_class"] == "direct"]
    near_rows = [r for r in rows if r["contact_class"] == "near"]
    lines = [
        "# Stage 1 - HER2 target preparation report", "",
        f"Generated {contract['generated_utc']}", "",
        "## Parent", "",
        f"- 242 aa, SHA-256 `{hc.PARENT_SHA256}` (verified, not copied)",
        f"- V_H 1-120, linker 121-135 `(GGGGS)x3`, V_L 136-242",
        f"- native cysteines {list(hc.NATIVE_CYS)}; parent carries 0 N-glyc sequons",
        f"- V_H vs 1N8Z chain B: {len(vh_mismatch)} mismatches; "
        f"V_L vs chain A: {len(vl_mismatch)} mismatches", "",
        "## CDRs (Kabat, located by motif match)", "",
        "| CDR | span | sequence |", "| --- | --- | --- |",
    ]
    lines += [f"| {k} | {v[0]}-{v[1]} | `{hc.PARENT_SEQ[v[0]-1:v[1]]}` |" for k, v in sorted(spans.items())]
    lines += [
        "", "## HER2 domain IV crop", "",
        f"- mature **{lo}-{hi}** = UniProt {lo+hc.MATURE_TO_UNIPROT_OFFSET}-{hi+hc.MATURE_TO_UNIPROT_OFFSET}"
        f" ({len(crop_seq)} aa)",
        f"- {len(inside)} disulfides fully inside, **0 split** (checked against SSBOND records)",
        f"- all {len(contact_res)} Fab-contacting HER2 residues (mature "
        f"{contact_res[0]}-{contact_res[-1]}) retained",
        f"- Boltz complex size: 242 + {len(crop_seq)} = **{hc.PARENT_LEN + len(crop_seq)} residues** "
        f"(vs ~849 for the full ectodomain)",
        "", f"```\n{crop_seq}\n```", "",
        "## Paratope (scFv residues near HER2)", "",
        f"- direct (<= {DIRECT_CUTOFF_A} A): {len(direct_rows)} residues",
        f"- near ({DIRECT_CUTOFF_A}-{NEAR_CUTOFF_A} A): {len(near_rows)} residues", "",
        "| scFv pos | aa | domain | CDR | min dist (A) |", "| --- | --- | --- | --- | --- |",
    ]
    lines += [f"| {r['scfv_pos_1based']} | {r['parent_aa']} | {r['domain']} | {r['cdr_name']} "
              f"| {r['min_target_distance_A']} |" for r in direct_rows]
    lines += ["", "## Caveats", "",
              "- Cropping removes receptor context and creates artificial termini; the **same crop**",
              "  is used for the parent and every candidate so comparisons stay matched.",
              "- Glycans present in the crystal are not modelled in the cofold.",
              "- Distance bins are geometric, not calibrated affinity predictors."]
    (args.outdir / "target_prep_report.md").write_text("\n".join(lines) + "\n")

    print(f"[ok] wrote contract.yaml, contract.json, her2_domain_iv.fasta, target_prep_report.md "
          f"-> {args.outdir}")
    return 0


def _to_yaml(obj, indent: int = 0) -> str:
    """Tiny YAML emitter - avoids a PyYAML dependency in this stage."""
    pad = "  " * indent
    if isinstance(obj, dict):
        out = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                out.append(f"{pad}{k}:\n{_to_yaml(v, indent + 1)}")
            else:
                out.append(f"{pad}{k}: {_scalar(v)}")
        return "\n".join(out)
    if isinstance(obj, list):
        if all(not isinstance(i, (dict, list)) for i in obj):
            return f"{pad}[{', '.join(_scalar(i) for i in obj)}]"
        return "\n".join(f"{pad}-\n{_to_yaml(i, indent + 1)}" if isinstance(i, (dict, list))
                         else f"{pad}- {_scalar(i)}" for i in obj)
    return f"{pad}{_scalar(obj)}"


def _scalar(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, str) and (len(v) > 60 or any(c in v for c in ":#{}[],&*?|<>=!%@`")):
        return f'"{v}"'
    return str(v)


if __name__ == "__main__":
    raise SystemExit(main())
