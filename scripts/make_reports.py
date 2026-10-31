#!/usr/bin/env python
"""Assemble the campaign reports from whatever results exist right now.

Writes three documents into ``outputs/reports/``:

``local_run_report.md``    everything computed on the local RTX 3090
``modal_run_report.md``    everything computed on Modal, plus cost/throughput
``final_designs_report.md`` the ranked submission set and the lab nominations

Every number is read back out of the pipeline's own tables, so the reports can be
regenerated at any time and will simply describe more data. Sections whose inputs
do not exist yet say so rather than guessing, which makes this safe to run on a
timer while a campaign is still in flight.

Run:
    python make_reports.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics as st
from collections import Counter, defaultdict
from datetime import datetime, timezone
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


def load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except Exception:                                            # noqa: BLE001
        return {}


def fmt(v, nd=4, dash="n/a"):
    f = fnum(v)
    return dash if f is None else f"{f:.{nd}f}"


def source_of(r: dict) -> str:
    return "Modal" if "modal_cofold" in (r.get("structure_path") or "") else "Local"


def per_design(raw: list[dict], source: str | None = None) -> dict[str, list[float]]:
    out: dict[str, list[float]] = defaultdict(list)
    for r in raw:
        if r.get("ipsae_status") != "PASSED":
            continue
        if source and source_of(r) != source:
            continue
        v = fnum(r.get("ipsae_min"))
        if v is not None:
            out[r["candidate_id"]].append(v)
    return out


def welch(a: list[float], b: list[float]) -> float | None:
    """t statistic for mean(a) - mean(b); None when it cannot be computed."""
    if len(a) < 2 or len(b) < 2:
        return None
    sa, sb = st.stdev(a), st.stdev(b)
    se = math.sqrt(sa ** 2 / len(a) + sb ** 2 / len(b))
    return (st.fmean(a) - st.fmean(b)) / se if se > 0 else None


def stats_block(vals: list[float]) -> str:
    if not vals:
        return "no data"
    return (f"n={len(vals)}  min={min(vals):.4f}  median={st.median(vals):.4f}  "
            f"mean={st.fmean(vals):.4f}  max={max(vals):.4f}")


HEADER_NOTE = (
    "> **Claim boundary.** Every value here is a computational ranking signal for "
    "experimental triage. ipSAE is not a binding affinity, ipTM is not ipSAE, and a "
    "higher score is not a demonstrated improvement. No K_D is predicted.\n")


def throughput_section(log_dir: Path) -> list[str]:
    """Parse the Modal campaign logs for progress, cost and failures."""
    L = ["## Throughput and cost", ""]
    phases = {"A": "error bars on all submitted designs (7 seeds)",
              "B": "balanced mutation-count sweep (5 seeds)",
              "C": "stratified breadth with replicates (5 seeds)",
              "D": "deep replication of nominees (20 seeds)"}
    any_phase = False
    L += ["| Phase | Purpose | Structures | Elapsed | Est. cost | State |",
          "| --- | --- | ---: | ---: | ---: | --- |"]
    total = 0
    for p, label in phases.items():
        f = log_dir / f"modal_phase_{p}.log"
        if not f.is_file():
            L.append(f"| {p} | {label} | - | - | - | not started |")
            continue
        any_phase = True
        txt = f.read_text(errors="replace")
        prog = [l for l in txt.splitlines() if l.startswith("[progress]")]
        done = elapsed = cost = "-"
        if prog:
            last = prog[-1].split()
            try:
                done = last[1]
                total += int(last[1].split("/")[0])
                elapsed = next(x.split("=")[1] for x in last if x.startswith("elapsed="))
                cost = next(x.split("=")[1] for x in last if x.startswith("cost="))
            except Exception:                                    # noqa: BLE001
                pass
        state = "complete" if "[modal] batches" in txt else "running"
        L.append(f"| {p} | {label} | {done} | {elapsed} | {cost} | {state} |")
    if not any_phase:
        L = ["## Throughput and cost", "", "_No Modal phase has started yet._", ""]
        return L
    L += ["", f"Structures completed on Modal so far: **{total}**.", ""]
    camp = log_dir / "modal_campaign.log"
    if camp.is_file():
        spend = [l for l in camp.read_text(errors="replace").splitlines()
                 if "campaign spend estimate" in l]
        if spend:
            L += [spend[-1].strip().lstrip("> "), ""]
    L += ["Cost is estimated at ~$0.0046 per structure (~15 s on an A10G at ~$1.10/GPU-hour); "
          "the authoritative figure is the Modal usage dashboard.", ""]
    return L


def common_sections(d: dict) -> list[str]:
    """Reliability + parent comparison, shared by the local and Modal reports."""
    L: list[str] = []
    diag = d["diag"]
    rel = (diag.get("reliability") or {})
    if rel.get("reliability_single_seed") is not None:
        L += ["## Measurement reliability", "",
              "| Quantity | Value |", "| --- | ---: |",
              f"| Designs with replicates | {rel.get('n_replicated')} |",
              f"| sd within design (seed noise) | {fmt(rel.get('sd_within_seed'))} |",
              f"| sd between designs (true, est.) | {fmt(rel.get('sd_between_designs_true_est'))} |",
              f"| Reliability of a single seed | **{fmt(rel.get('reliability_single_seed'),3)}** |",
              f"| Reliability of the current mean | {fmt(rel.get('reliability_current_mean'),3)} |",
              f"| Seeds for reliability 0.8 / 0.9 | "
              f"{rel.get('seeds_for_reliability_0.8')} / {rel.get('seeds_for_reliability_0.9')} |",
              "",
              "Reliability is the share of ranking variance that is real signal rather than "
              "seed noise. This governs every comparison below: a single-seed ipSAE table is "
              "not an ordering of design quality.", ""]
        pc = rel.get("parent_comparison") or {}
        if pc.get("tests"):
            L += ["### Designs tested against the parent", "",
                  f"Parent {fmt(pc.get('parent_mean'))} +/- {fmt(pc.get('parent_sd'))} over "
                  f"{pc.get('parent_n_seeds')} seeds; threshold {pc.get('threshold')}.", "",
                  f"- above parent: **{pc.get('n_above')}**",
                  f"- below parent: {pc.get('n_below')}",
                  f"- indistinguishable: {pc.get('n_indistinguishable')}", ""]
            if pc.get("n_above", 0) == 0:
                L += ["**No design is statistically distinguishable as better than the parent.** "
                      "That is the honest result, and the expected one: the parent is a "
                      "sub-picomolar, heavily optimised therapeutic antibody.", ""]
    sp = diag.get("spearman") or {}
    if sp:
        L += ["## Do sequence scores predict structure?", "",
              "| Predictor | vs ipSAE | vs epitope recovery | vs ipTM |",
              "| --- | ---: | ---: | ---: |"]
        for pn, tv in sp.items():
            cells = [fmt(tv.get(t, {}).get("rho"), 3) for t in
                     ("ipsae_min", "epitope_recovery", "iptm")]
            L.append(f"| `{pn}` | " + " | ".join(cells) + " |")
        L += ["", "Negative means a higher sequence-plausibility score goes with a **worse** "
                  "modelled interface. The parent is affinity-matured, so antibody language "
                  "models push its CDRs back toward germline consensus - away from the "
                  "residues that contact HER2.", ""]
    for key, title in (("by_mutation_count", "By substitution count"), ("by_branch", "By branch")):
        grp = diag.get(key) or {}
        if not grp:
            continue
        L += [f"### {title}", "",
              "| Group | n | ipSAE mean | sd | ipTM | epitope recovery |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for k, v in grp.items():
            L.append(f"| {k} | {v['n']} | {fmt(v['ipsae_min_mean'])} | {fmt(v.get('ipsae_min_sd'),3)} "
                     f"| {fmt(v.get('iptm_mean'),3)} | {fmt(v.get('epitope_recovery_mean'),3)} |")
        L.append("")
    return L


FIGS = [
    ("01_ipsae_distribution.png", "ipSAE distribution of designed variants"),
    ("02_ipsae_by_mutation_count.png", "Interface quality vs substitution count"),
    ("03_ipsae_by_branch.png", "Interface quality by design branch"),
    ("04_replicate_spread.png", "Seed noise against between-design differences"),
    ("05_reliability.png", "How much of the ipSAE ranking is real"),
    ("06_score_correlations.png", "Sequence scores vs structural outcomes"),
    ("07_epitope_vs_ipsae.png", "Epitope recovery against interface confidence"),
    ("08_top_designs.png", "Nominated designs with replicate error bars"),
    ("09_throughput.png", "Structures scored, by compute source"),
]


def figure_block(figdir: Path, rel_prefix: str, only: list[str] | None = None) -> list[str]:
    L = ["## Figures", ""]
    n = 0
    for fn, cap in FIGS:
        if only and fn not in only:
            continue
        if (figdir / fn).is_file():
            L += [f"**{cap}**", "", f"![{cap}]({rel_prefix}{fn})", ""]
            n += 1
    return L if n else ["## Figures", "", "_Not generated yet._", ""]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--results", type=Path, default=base / "outputs")
    ap.add_argument("--logs", type=Path, default=base / "logs")
    ap.add_argument("--outdir", type=Path, default=base / "outputs" / "reports")
    args = ap.parse_args()
    o, rep = args.results, args.outdir
    rep.mkdir(parents=True, exist_ok=True)
    hc.assert_parent_integrity()

    d = {
        "raw": read_csv(o / "boltz_results_raw.csv"),
        "scored": read_csv(o / "submission_scored.csv"),
        "top15": read_csv(o / "top_15_scored.csv"),
        "top50": read_csv(o / "top_50_scored.csv"),
        "diag": load_json(o / "score_diagnostics.json"),
        "audit": load_json(o / "compliance_audit.json"),
        "contract": load_json(o / "contract.json"),
        "binders": read_csv(o / "binder_summary.csv"),
    }
    passed = [r for r in d["raw"] if r.get("ipsae_status") == "PASSED"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    figrel = "../figures/"

    by_src = Counter(source_of(r) for r in passed)
    parent_all = per_design(passed).get("parent", [])

    # ---------------------------------------------------------------- local
    for label, src in (("local", "Local"), ("modal", "Modal")):
        sub = [r for r in passed if source_of(r) == src]
        pd_ = per_design(sub)
        cand = {k: v for k, v in pd_.items() if k != "parent"}
        vals = [st.fmean(v) for v in cand.values()]
        L = [f"# {src} run report - HER2 scFv optimisation", "",
             f"Generated {now}. Regenerated automatically as results arrive.", "",
             HEADER_NOTE, "## Summary", "",
             "| Quantity | Value |", "| --- | ---: |",
             f"| Structures scored on {src} | {len(sub)} |",
             f"| Distinct designs | {len(cand)} |",
             f"| Parent replicates | {len(pd_.get('parent', []))} |",
             f"| Mean seeds per design | "
             f"{(st.fmean([len(v) for v in cand.values()]) if cand else 0):.2f} |", ""]
        if vals:
            L += [f"Per-design mean ipSAE: {stats_block(vals)}", ""]
        if src == "Local":
            L += ["Hardware: one NVIDIA RTX 3090 (24 GB). Measured ~15.5 s per 361-residue "
                  "complex with cached MSAs, ~19 GiB peak, so only one Boltz job fits at a "
                  "time.", ""]
        else:
            L += throughput_section(args.logs)
        L += common_sections(d)
        L += figure_block(o / "figures", figrel)
        (rep / f"{label}_run_report.md").write_text("\n".join(L) + "\n")

    # ------------------------------------------------------- final designs
    scored = d["scored"]
    top50 = d["top50"] or scored[:50]
    top15 = d["top15"]
    pdall = per_design(passed)
    L = ["# Final designs report - HER2 scFv optimisation", "",
         f"Generated {now}.", "", HEADER_NOTE,
         "## Headline", "",
         "| Quantity | Value |", "| --- | ---: |",
         f"| Designs with a genuine external ipSAE | **{len(scored)}** |",
         f"| Structures behind them | {len(passed)} |",
         f"| Local / Modal structures | {by_src.get('Local',0)} / {by_src.get('Modal',0)} |",
         f"| Ranked submission set | {len(top50)} |",
         f"| Lab nominations | {len(top15)} |",
         f"| Parent replicates | {len(parent_all)} |",
         f"| Compliance audit | **{d['audit'].get('overall','NOT_EVALUATED')}** "
         f"({d['audit'].get('failed_checks','?')} failed) |", ""]
    if parent_all:
        L += [f"Parent baseline: **{st.fmean(parent_all):.4f}** "
              f"+/- {(st.stdev(parent_all) if len(parent_all)>1 else 0):.4f} "
              f"over {len(parent_all)} seeds.", ""]
    ic = d["audit"].get("interpretation_counts")
    if ic:
        L += ["### How each design compares with the parent", "",
              "| Verdict | Designs |", "| --- | ---: |"]
        L += [f"| {k} | {v} |" for k, v in ic.items()]
        L += ["", "`SINGLE_SEED_UNRELIABLE` means the design has one replicate, which at the "
                  "measured reliability cannot support a directional claim either way.", ""]

    L += ["## Top 50 ranked designs", "",
          "Ranked by the multi-objective score (sequence consensus, ipSAE, epitope recovery, "
          "structural confidence, developability), **not** by ipSAE alone.", "",
          "| # | design | branch | muts | ipSAE | sd | n | delta vs parent | epitope | ipTM | "
          "interface | verdict |",
          "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
    for i, r in enumerate(top50[:50], 1):
        cid = r["candidate_id"]
        vals = pdall.get(cid, [])
        t = welch(vals, parent_all)
        verdict = ("above" if t and t > 2 else "below" if t and t < -2
                   else "indistinguishable" if t is not None else "1 seed")
        L.append(f"| {i} | `{cid}` | {r.get('branch','')} | {r.get('mutation_count','')} "
                 f"| {fmt(r.get('ipsae_min'))} | {fmt(r.get('ipsae_min_sd'),3)} "
                 f"| {len(vals)} | {fmt(r.get('ipsae_delta_vs_parent'))} "
                 f"| {fmt(r.get('epitope_recovery'),3)} | {fmt(r.get('iptm'),3)} "
                 f"| {r.get('interface_status','')} | {verdict} |")
    L.append("")

    if top15:
        L += ["## Lab nominations", "",
              "| # | design | branch | substitutions | ipSAE | epitope | rank shift |",
              "| ---: | --- | --- | --- | ---: | ---: | ---: |"]
        for i, r in enumerate(top15, 1):
            L.append(f"| {i} | `{r['candidate_id']}` | {r.get('branch','')} "
                     f"| `{r.get('mutations_1based','')}` | {fmt(r.get('ipsae_min'))} "
                     f"| {fmt(r.get('epitope_recovery'),3)} "
                     f"| {r.get('max_rank_shift_under_reweighting','')} |")
        L += ["", "`rank shift` is how far a design moves under three alternative weightings; a "
                  "large value means its position depends on one metric.", ""]

    if d["binders"]:
        L += ["## Exported binder packages", "",
              f"{len(d['binders'])} designs exported to `outputs/binders/<id>/` with "
              "`sequence.fasta`, `design.json`, `complex.cif`, `pae.npz`, "
              "`interface_contacts.csv` and `mutations.csv`. Rotating 3D animations are in "
              "`outputs/gifs/`.", "",
              "| design | muts | modelled contacts | epitope recovery | folder |",
              "| --- | ---: | ---: | ---: | --- |"]
        for b in d["binders"]:
            L.append(f"| `{b['candidate_id']}` | {b['mutation_count']} "
                     f"| {b.get('modelled_contacts','')} | {fmt(b.get('epitope_recovery'),3)} "
                     f"| `{b.get('folder','')}` |")
        L.append("")

    L += figure_block(o / "figures", figrel)
    L += ["## Limitations", "",
          "- ipSAE, ipTM, pDockQ and LIS are model-confidence measures, not affinities.",
          "- The parent is ~0.82 pM; assay floor effects make improvement hard to show even "
          "experimentally.",
          "- The domain IV crop removes receptor context and glycans; it is required by the "
          "organizer and applied identically to parent and candidates.",
          "- MSA reuse keeps the parent's homolog block, which slightly favours designs closer "
          "to the parent. A fresh-MSA control was attempted but did not complete.",
          "- AbLang2, ESM2 and ESM-C never see HER2; they reject implausible sequences, they do "
          "not identify better binders.",
          "- Selection weights are a reasoned hypothesis, quantified by the sensitivity analysis.",
          ""]
    (rep / "final_designs_report.md").write_text("\n".join(L) + "\n")

    print(f"[reports] local_run_report.md, modal_run_report.md, final_designs_report.md -> {rep}")
    print(f"[reports] {len(passed)} structures "
          f"(Local {by_src.get('Local',0)} / Modal {by_src.get('Modal',0)}), "
          f"{len(scored)} designs, audit {d['audit'].get('overall','?')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
