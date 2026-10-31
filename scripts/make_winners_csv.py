#!/usr/bin/env python
"""Produce the submission-ready ranked winners table.

Writes ``outputs/ranked_winners.csv`` (and ``.fasta``): one row per design, in
final rank order, carrying every metric a reviewer or a wet-lab scientist needs
without having to join three other files.

Columns are grouped so the table reads left to right as: identity -> sequence
and mutations -> the required ipSAE evidence with its uncertainty -> supporting
structural metrics -> sequence-model priors -> selection provenance.

The statistics are the point of this file. Each design carries its replicate
mean, standard deviation, seed count, a 95% confidence interval, the Welch t
against the parent and the **Benjamini-Hochberg q-value** across all tested
designs. A design is called better than the parent only at q < 0.05; testing
~250 designs at an uncorrected alpha of 0.05 would otherwise manufacture a dozen
"winners" from noise.

Run:
    python make_winners_csv.py --top 50
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics as st
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import her2_common as hc

COLUMNS = [
    # identity / rank
    "rank", "candidate_id", "branch", "selected_top15", "priority_tier",
    # sequence and edits
    "mutation_count", "mutations_1based", "mutated_domains", "mutated_CDRs",
    "mutations_at_experimental_interface", "new_cysteine_count", "new_liability_flags",
    # the required deliverable metric, with uncertainty
    "ipsae_min_mean", "ipsae_min_sd", "ipsae_n_seeds", "ipsae_ci95_low", "ipsae_ci95_high",
    "ipsae_min_best", "ipsae_max_mean",
    "parent_ipsae_mean", "parent_ipsae_sd", "parent_n_seeds",
    "delta_vs_parent", "welch_t", "q_value_BH", "verdict_vs_parent",
    # supporting structural evidence
    "epitope_recovery", "epitope_contacts_recovered", "modelled_interface_contacts",
    "iptm", "pDockQ", "LIS", "interface_status",
    # sequence-model priors (never affinity)
    "ablang2_contextual", "esm2_contextual", "sequence_consensus_score", "model_disagreement",
    # selection provenance
    "rank_score", "max_rank_shift_under_reweighting", "compute_source",
    # identity / reproducibility
    "sequence_sha256", "full_scfv_sequence",
]


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--results", type=Path, default=base / "outputs")
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    o = args.results
    out_csv = args.out or (o / "ranked_winners.csv")
    hc.assert_parent_integrity()

    scored = read_csv(o / "submission_scored.csv")
    if not scored:
        raise SystemExit("submission_scored.csv is empty; run stage 6 first")
    top15 = {r["candidate_id"] for r in read_csv(o / "top_15_scored.csv")}
    raw = [r for r in read_csv(o / "boltz_results_raw.csv") if r.get("ipsae_status") == "PASSED"]
    diag = json.loads((o / "score_diagnostics.json").read_text()) \
        if (o / "score_diagnostics.json").is_file() else {}
    pc = ((diag.get("reliability") or {}).get("parent_comparison") or {})
    tests = {t["candidate_id"]: t for t in pc.get("tests", [])}
    contract = json.loads((o / "contract.json").read_text())
    epitope_total = len(contract["target"].get("epitope_direct_mature") or [])

    # Where each design's structures were computed, and its replicate values.
    per_vals: dict[str, list[float]] = defaultdict(list)
    per_src: dict[str, set[str]] = defaultdict(set)
    for r in raw:
        v = fnum(r.get("ipsae_min"))
        if v is None:
            continue
        per_vals[r["candidate_id"]].append(v)
        per_src[r["candidate_id"]].add(
            "Modal" if "modal_cofold" in (r.get("structure_path") or "") else "Local")

    binders = {b["candidate_id"]: b for b in read_csv(o / "binder_summary.csv")}

    rows_out: list[dict] = []
    for r in scored[: args.top]:
        cid = r["candidate_id"]
        seq = r["full_scfv_sequence"]
        v = hc.validate_candidate(seq, cid)
        vals = per_vals.get(cid, [])
        n = len(vals)
        mean = st.fmean(vals) if vals else None
        sd = st.stdev(vals) if n > 1 else 0.0
        # Normal-approximation interval on the mean; with n>=2 it is the honest
        # way to show that most designs overlap the parent.
        half = 1.96 * sd / math.sqrt(n) if n > 1 else None
        t = tests.get(cid, {})
        interface_muts = (binders.get(cid, {}) or {}).get("interface_mutations", "")

        rows_out.append({
            "rank": r.get("rank", ""),
            "candidate_id": cid,
            "branch": r.get("branch", ""),
            "selected_top15": cid in top15,
            "priority_tier": r.get("priority_tier", ""),
            "mutation_count": v.mutation_count,
            "mutations_1based": ";".join(v.mutations),
            "mutated_domains": ";".join(sorted({hc.domain_of(int(m[1:-1])) for m in v.mutations})),
            "mutated_CDRs": ";".join(sorted({hc.cdr_of(int(m[1:-1])) for m in v.mutations})),
            "mutations_at_experimental_interface": interface_muts,
            "new_cysteine_count": 0,
            "new_liability_flags": r.get("new_liability_flags", ""),
            "ipsae_min_mean": round(mean, 4) if mean is not None else "",
            "ipsae_min_sd": round(sd, 4),
            "ipsae_n_seeds": n,
            "ipsae_ci95_low": round(mean - half, 4) if half is not None else "",
            "ipsae_ci95_high": round(mean + half, 4) if half is not None else "",
            "ipsae_min_best": round(max(vals), 4) if vals else "",
            "ipsae_max_mean": r.get("ipsae_max", ""),
            "parent_ipsae_mean": pc.get("parent_mean", ""),
            "parent_ipsae_sd": pc.get("parent_sd", ""),
            "parent_n_seeds": pc.get("parent_n_seeds", ""),
            "delta_vs_parent": t.get("delta_vs_parent", r.get("ipsae_delta_vs_parent", "")),
            "welch_t": t.get("t", ""),
            "q_value_BH": t.get("q_value_BH", ""),
            "verdict_vs_parent": t.get("verdict_fdr",
                                       r.get("ipsae_interpretation", "SINGLE_SEED_UNRELIABLE")),
            "epitope_recovery": r.get("epitope_recovery", ""),
            "epitope_contacts_recovered":
                (round(float(r["epitope_recovery"]) * epitope_total)
                 if fnum(r.get("epitope_recovery")) is not None else ""),
            "modelled_interface_contacts": (binders.get(cid, {}) or {}).get("modelled_contacts", ""),
            "iptm": r.get("iptm", ""),
            "pDockQ": r.get("pDockQ", ""),
            "LIS": r.get("LIS", ""),
            "interface_status": r.get("interface_status", ""),
            "ablang2_contextual": r.get("ablang2_contextual", ""),
            "esm2_contextual": r.get("esm2_contextual", ""),
            "sequence_consensus_score": r.get("sequence_consensus_score", ""),
            "model_disagreement": r.get("model_disagreement", ""),
            "rank_score": r.get("rank_score", ""),
            "max_rank_shift_under_reweighting": r.get("max_rank_shift_under_reweighting", ""),
            "compute_source": "+".join(sorted(per_src.get(cid, {"Local"}))),
            "sequence_sha256": hc.sha256_seq(seq),
            "full_scfv_sequence": seq,
        })

    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_out)
    hc.write_fasta(out_csv.with_suffix(".fasta"),
                   {f"{r['candidate_id']} rank={r['rank']} muts={r['mutation_count']} "
                    f"ipSAE={r['ipsae_min_mean']}+/-{r['ipsae_min_sd']} n={r['ipsae_n_seeds']} "
                    f"q={r['q_value_BH']}": r["full_scfv_sequence"] for r in rows_out})

    # A short README so the CSV is self-explanatory to someone who did not run it.
    (o / "ranked_winners_README.md").write_text(f"""# ranked_winners.csv

Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} - {len(rows_out)} designs in final rank order.

Every row is a compliant scFv variant of the trastuzumab parent with a genuine,
externally computed ipSAE. Columns read left to right as identity, sequence and
mutations, the ipSAE evidence with its uncertainty, supporting structural
metrics, sequence-model priors, and selection provenance.

## Reading the statistics

| Column | Meaning |
| --- | --- |
| `ipsae_min_mean` | mean of `min(asym B->T, asym T->B)` across replicate seeds |
| `ipsae_n_seeds` | how many independent Boltz-2 seeds back that mean |
| `ipsae_ci95_low/high` | 95% interval on the mean (normal approximation) |
| `delta_vs_parent` | mean minus the parent's mean, same protocol throughout |
| `welch_t` | Welch t-statistic against the parent's own replicates |
| `q_value_BH` | Benjamini-Hochberg q across all tested designs |
| `verdict_vs_parent` | `ABOVE_PARENT_FDR` only when q < 0.05 |

**Why the q-value matters.** Roughly 250 designs were tested. At an uncorrected
alpha of 0.05 about a dozen would clear `|t| > 2` by chance alone, so an
uncorrected "above parent" count is not evidence. Only `ABOVE_PARENT_FDR`
survives correction.

**Claim boundary.** ipSAE is interface confidence from a structure predictor, not
a binding affinity. A higher ipSAE is not a demonstrated improvement in K_D, and
no K_D is predicted anywhere in this work. The parent is ~0.82 pM; the wet-lab
assay decides.

## Hard constraints, verified for every row

- exactly 242 aa, substitution-only, >= 5 substitutions vs the parent
- `(GGGGS)x3` linker intact at 121-135
- native cysteines preserved at 22/96/158/223, no new cysteines
- no newly introduced N-X-S/T glycosylation sequons
- reconstructible by applying `mutations_1based` to the frozen parent
""")
    # ---- XLSX with the same content, formatted for reading ---------------- #
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = "ranked_winners"
        hdr_fill = PatternFill("solid", fgColor="1C5CAB")
        hdr_font = Font(color="FFFFFF", bold=True, size=10)
        win_fill = PatternFill("solid", fgColor="D8EFE2")   # FDR-significant rows
        bad_fill = PatternFill("solid", fgColor="F7DDD9")   # collapsed interface
        ws.append(COLUMNS)
        for c in range(1, len(COLUMNS) + 1):
            cell = ws.cell(row=1, column=c)
            cell.fill, cell.font = hdr_fill, hdr_font
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        for r in rows_out:
            ws.append([r.get(k, "") for k in COLUMNS])
            rowi = ws.max_row
            if r.get("verdict_vs_parent") == "ABOVE_PARENT_FDR":
                fill = win_fill
            elif r.get("interface_status") == "COLLAPSED":
                fill = bad_fill
            else:
                fill = None
            if fill:
                for c in range(1, len(COLUMNS) + 1):
                    ws.cell(row=rowi, column=c).fill = fill
        # The sequence column is 242 characters; everything else is narrow.
        widths = {"mutations_1based": 42, "full_scfv_sequence": 60,
                  "sequence_sha256": 20, "mutations_at_experimental_interface": 26,
                  "candidate_id": 14, "branch": 14, "verdict_vs_parent": 26,
                  "new_liability_flags": 26, "mutated_CDRs": 20, "mutated_domains": 16}
        for i, name in enumerate(COLUMNS, 1):
            ws.column_dimensions[get_column_letter(i)].width = widths.get(name, 13)
        ws.freeze_panes = "C2"          # keep rank + id visible while scrolling
        ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{ws.max_row}"

        # Legend sheet, so the file explains itself away from this repo.
        ws2 = wb.create_sheet("legend")
        legend = [
            ("Column", "Meaning"),
            ("ipsae_min_mean", "mean of min(asym B->T, asym T->B) across replicate seeds"),
            ("ipsae_n_seeds", "independent Boltz-2 seeds behind that mean"),
            ("ipsae_ci95_low/high", "95% interval on the mean (normal approximation)"),
            ("delta_vs_parent", "mean minus the parent mean, identical protocol throughout"),
            ("welch_t", "Welch t against the parent's own replicates"),
            ("q_value_BH", "Benjamini-Hochberg q across all tested designs"),
            ("verdict_vs_parent", "ABOVE_PARENT_FDR only when q < 0.05"),
            ("epitope_recovery", "fraction of the experimentally observed 1N8Z contacts reproduced"),
            ("interface_status", "COLLAPSED = interface lost; barred from lab nomination"),
            ("", ""),
            ("Why q-values", "~250 designs were tested. At an uncorrected alpha of 0.05 about a "
                             "dozen would clear |t|>2 by chance, so an uncorrected count is not "
                             "evidence. Only ABOVE_PARENT_FDR survives correction."),
            ("Claim boundary", "ipSAE is interface confidence from a structure predictor, NOT a "
                               "binding affinity. No K_D is predicted. The parent is ~0.82 pM; "
                               "the wet-lab assay decides."),
            ("Shading", "green = FDR-significant above parent; red = collapsed interface"),
            ("", ""),
            ("Verified for every row", "242 aa, substitution-only, >=5 substitutions; (GGGGS)x3 "
                                       "linker intact at 121-135; cysteines 22/96/158/223 "
                                       "preserved with no new ones; no new N-X-S/T sequons; "
                                       "reconstructible from mutations_1based."),
        ]
        for row in legend:
            ws2.append(list(row))
        ws2.cell(row=1, column=1).font = Font(bold=True)
        ws2.cell(row=1, column=2).font = Font(bold=True)
        ws2.column_dimensions["A"].width = 26
        ws2.column_dimensions["B"].width = 110
        for r_ in range(1, ws2.max_row + 1):
            ws2.cell(row=r_, column=2).alignment = Alignment(wrap_text=True, vertical="top")
        xlsx = out_csv.with_suffix(".xlsx")
        wb.save(xlsx)
        print(f"[winners] {xlsx}")
    except Exception as exc:                                     # noqa: BLE001
        print(f"[winners] XLSX skipped: {type(exc).__name__}: {exc}")

    nseeds = [r["ipsae_n_seeds"] for r in rows_out]
    above = sum(1 for r in rows_out if r["verdict_vs_parent"] == "ABOVE_PARENT_FDR")
    print(f"[winners] {out_csv} : {len(rows_out)} designs")
    print(f"[winners] seeds per design min={min(nseeds)} median={sorted(nseeds)[len(nseeds)//2]} "
          f"max={max(nseeds)}")
    print(f"[winners] parent {pc.get('parent_mean')} +/- {pc.get('parent_sd')} "
          f"(n={pc.get('parent_n_seeds')}); FDR-significant above parent: {above}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
