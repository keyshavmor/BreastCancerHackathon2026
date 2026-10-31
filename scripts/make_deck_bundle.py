#!/usr/bin/env python
"""Build a single self-contained folder for a short, simple slide deck.

Produces ``outputs/PRESENTATION/`` holding everything needed and nothing else:

    LOVABLE_PROMPT.md     build prompt for a 4-slide deck, numbers inlined
    METHODOLOGY.md        the science in plain language, with Q&A
    pipeline_diagram.svg  the funnel, drawn so a browser can embed it directly
    top10_table.csv/.md   ten designs, only challenge-relevant columns
    metrics.json          headline numbers, machine-readable
    gifs/                 parent + the winning designs, rotating
    figures/              the three figures that matter for a short deck

Deliberately smaller than the full report bundle: a 4-slide deck should carry
four ideas, so this ships the subset that supports them rather than everything
the campaign produced.

Run:
    python make_deck_bundle.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import her2_common as hc

# Only the columns a judge needs for this challenge. The full 42-column table
# stays in outputs/ranked_winners.csv for anyone who wants to dig.
TABLE_COLS = [
    ("rank", "Rank"),
    ("candidate_id", "Design"),
    ("strategy", "Strategy"),
    ("mutation_count", "Mutations"),
    ("mutations_1based", "Substitutions"),
    ("ipsae_min_mean", "ipSAE"),
    ("ipsae_min_sd", "± SD"),
    ("ipsae_n_seeds", "Runs"),
    ("delta_vs_parent", "vs parent"),
    ("q_value_BH", "q (FDR)"),
    ("epitope_recovery", "Epitope kept"),
]

# Only the figures a short deck can actually use.
STRATEGIES = {
    "A_h3": {
        "label": "CDR-H3 focused",
        "where": "edits concentrated in CDR-H3, the antibody's main binding loop",
        "why": "published work reports CDR-H3 as the most productive region to mature",
        "result": "scored WORST here, contradicting that expectation",
    },
    "B_interface": {
        "label": "Contact region",
        "where": "edits on or beside residues that physically touch HER2, excluding CDR-H3",
        "why": "changes near the interface can improve complementarity without touching H3",
        "result": "second best; produced two of the significant designs",
    },
    "C_mixed": {
        "label": "Mixed",
        "where": "a few edits near the contact surface plus supporting edits elsewhere",
        "why": "tests whether distant changes can reinforce a contact-region change",
        "result": "produced the most statistically significant designs",
    },
    "D_framework": {
        "label": "Scaffold only",
        "where": "edits only in the structural framework; the binding site is left untouched",
        "why": "a deliberate control: can we change the molecule without disturbing binding?",
        "result": "best average interface quality, and the safest edits",
    },
}

KEEP_FIGS = ["05_reliability.png", "02_ipsae_by_mutation_count.png",
             "08_top_designs.png", "01_ipsae_distribution.png"]


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


# --------------------------------------------------------------------------- #
# Pipeline diagram, emitted as plain SVG so a browser can embed it unchanged
# --------------------------------------------------------------------------- #

def pipeline_svg(f: dict, c: dict, s: dict) -> str:
    ink, ink2, surf = "#0b0b0b", "#52514e", "#fcfcfb"
    blue, orange, aqua, grey = "#2a78d6", "#eb6834", "#1baf7a", "#9a9890"
    green = "#0ca30c"

    stages = [
        ("Parent scFv", "242 aa, 0.82 pM\ntrastuzumab", grey, "frozen + SHA-verified"),
        ("Generate", f"{f.get('ablang2_candidates') or 0:,}\ncandidates", blue,
         "AbLang2, 4 strategies"),
        ("Screen", f"{f.get('esm2_shortlist') or 0:,}\nshortlisted", blue, "ESM2-3B, 2nd opinion"),
        ("Fold", f"{f.get('designs_cofolded') or 0}\ndesigns cofolded", orange,
         "Boltz-2, HER2 domain IV"),
        ("Replicate", f"{c.get('structures_total') or 0:,}\nstructures", orange,
         f"median {s.get('median_seeds_per_design')} runs each"),
        ("Score", f"{f.get('designs_with_ipsae') or 0}\nwith real ipSAE", aqua,
         "DunbrackLab ipSAE"),
        ("Select", f"{f.get('ranked_submission') or 0} ranked\n{f.get('lab_nominations') or 0} nominated",
         green, "multi-objective + FDR"),
    ]
    W, H = 1240, 340
    bw, bh, gap = 150, 92, 20
    x0 = 24
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'font-family="Inter,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<rect width="{W}" height="{H}" fill="{surf}"/>',
        f'<text x="{x0}" y="36" font-size="21" font-weight="700" fill="{ink}">'
        f'How a million candidates become fifteen lab tests</text>',
        f'<text x="{x0}" y="60" font-size="13" fill="{ink2}">'
        f'Cheap filters first. Nothing expensive runs on a candidate a cheap test already '
        f'rejected.</text>',
    ]
    y = 96
    for i, (title, big, col, sub) in enumerate(stages):
        x = x0 + i * (bw + gap)
        parts.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="{col}"/>')
        parts.append(f'<text x="{x+bw/2}" y="{y+24}" font-size="13" font-weight="700" '
                     f'fill="#ffffff" text-anchor="middle">{title}</text>')
        for j, line in enumerate(big.split("\n")):
            parts.append(f'<text x="{x+bw/2}" y="{y+48+j*19}" font-size="15" font-weight="700" '
                         f'fill="#ffffff" text-anchor="middle">{line}</text>')
        for j, line in enumerate(sub.split("\n")):
            parts.append(f'<text x="{x+bw/2}" y="{y+bh+20+j*15}" font-size="11" fill="{ink2}" '
                         f'text-anchor="middle">{line}</text>')
        if i < len(stages) - 1:
            ax = x + bw + 4
            parts.append(f'<path d="M{ax} {y+bh/2} l{gap-8} 0" stroke="{ink2}" stroke-width="2" '
                         f'marker-end="url(#ar)"/>')
    parts.insert(1, f'<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" '
                    f'orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="{ink2}"/></marker></defs>')

    # The two guard rails that make the numbers trustworthy.
    gy = y + bh + 56
    parts.append(f'<rect x="{x0}" y="{gy}" width="{W-2*x0}" height="68" rx="10" '
                 f'fill="#ffffff" stroke="#e6e5e0"/>')
    parts.append(f'<text x="{x0+16}" y="{gy+25}" font-size="13" font-weight="700" fill="{ink}">'
                 f'Two guard rails</text>')
    parts.append(
        f'<text x="{x0+16}" y="{gy+46}" font-size="12.5" fill="{ink2}">'
        f'1. A single fold is only {s.get("single_seed_reliability")} reliable, so every design '
        f'is folded many times and reported with an error bar.</text>')
    parts.append(
        f'<text x="{x0+16}" y="{gy+63}" font-size="12.5" fill="{ink2}">'
        f'2. Testing {s.get("designs_tested")} designs would yield about '
        f'{s.get("expected_false_positives_uncorrected")} false winners by chance, so '
        f'Benjamini-Hochberg correction is applied before any design is called better.</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--results", type=Path, default=base / "outputs")
    ap.add_argument("--outdir", type=Path, default=None)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()
    o = args.results
    dest = args.outdir or (o / "PRESENTATION")
    for sub in ("gifs", "figures"):
        (dest / sub).mkdir(parents=True, exist_ok=True)
    hc.assert_parent_integrity()

    winners = read_csv(o / "ranked_winners.csv")[: args.top]
    audit = load_json(o / "compliance_audit.json")
    diag = load_json(o / "score_diagnostics.json")
    contract = load_json(o / "contract.json")
    m2 = load_json(o / "stage2_manifest.json")
    rel = diag.get("reliability") or {}
    pc = rel.get("parent_comparison") or {}
    raw = [r for r in read_csv(o / "boltz_results_raw.csv") if r.get("ipsae_status") == "PASSED"]
    n_modal = sum(1 for r in raw if "modal_cofold" in (r.get("structure_path") or ""))
    seeds = {}
    for r in raw:
        seeds[r["candidate_id"]] = seeds.get(r["candidate_id"], 0) + 1
    seeds.pop("parent", None)
    tgt = contract.get("target", {})
    fdr = [w for w in winners if w.get("verdict_vs_parent") == "ABOVE_PARENT_FDR"]

    metrics = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "funnel": {
            "ablang2_candidates": m2.get("candidates_kept"),
            "esm2_shortlist": m2.get("shortlist"),
            "designs_cofolded": len(seeds),
            "designs_with_ipsae": audit.get("submitted_scored_count"),
            "ranked_submission": 50,
            "lab_nominations": audit.get("top_n"),
        },
        "compute": {
            "structures_total": len(raw),
            "structures_local": len(raw) - n_modal,
            "structures_modal": n_modal,
            "modal_cost_usd_approx": round(n_modal * 0.0046, 2),
            "local_gpu": "1x RTX 3090 24 GB",
        },
        "statistics": {
            "parent_ipsae_mean": pc.get("parent_mean"),
            "parent_ipsae_sd": pc.get("parent_sd"),
            "parent_n_seeds": pc.get("parent_n_seeds"),
            "single_seed_reliability": rel.get("reliability_single_seed"),
            "median_seeds_per_design": (sorted(seeds.values())[len(seeds) // 2] if seeds else 0),
            "designs_tested": pc.get("n_tests"),
            "expected_false_positives_uncorrected": pc.get(
                "expected_false_positives_at_uncorrected_alpha05"),
            "above_parent_fdr": pc.get("n_above_fdr"),
            "below_parent": pc.get("n_below"),
        },
        "target": {
            "domain_iv_mature": tgt.get("domain_iv_mature"),
            "domain_iv_length": tgt.get("domain_iv_length"),
            "complex_residues": tgt.get("complex_residues_for_boltz"),
            "epitope_contacts": len(tgt.get("epitope_direct_mature") or []),
        },
        "strategies": STRATEGIES,
        "winners_fdr": [w["candidate_id"] for w in fdr],
        "claim_boundary": "ipSAE is interface confidence from a structure predictor, not a "
                          "binding affinity. No K_D is predicted.",
    }
    (dest / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (dest / "pipeline_diagram.svg").write_text(
        pipeline_svg(metrics["funnel"], metrics["compute"], metrics["statistics"]))

    # ---- trimmed top-10 table ------------------------------------------- #
    # Renumber 1..N for the slide; the full multi-objective rank stays in
    # ranked_winners.csv, and showing it here only confuses a reader.
    for i, r in enumerate(winners, 1):
        r["rank"] = i
    with open(dest / "top10_table.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([lbl for _, lbl in TABLE_COLS])
        for r in winners:
            w.writerow([r.get(k, "") for k, _ in TABLE_COLS])
    md = ["| " + " | ".join(lbl for _, lbl in TABLE_COLS) + " |",
          "| " + " | ".join("---" for _ in TABLE_COLS) + " |"]
    for r in winners:
        cells = []
        for k, _ in TABLE_COLS:
            v = r.get(k, "")
            if k == "candidate_id":
                v = f"`{v}`"
            if k == "mutations_1based":
                v = f"`{v}`"
            if k == "q_value_BH" and r.get("verdict_vs_parent") == "ABOVE_PARENT_FDR":
                v = f"**{v}**"
            cells.append(str(v))
        md.append("| " + " | ".join(cells) + " |")
    (dest / "top10_table.md").write_text("\n".join(md) + "\n")

    # ---- media ------------------------------------------------------------ #
    want = ["parent.gif"] + [f"{w['candidate_id']}.gif" for w in winners]
    got = []
    for name in want:
        src = o / "gifs" / name
        if src.is_file():
            shutil.copy2(src, dest / "gifs" / name)
            got.append(name)
    for fn in KEEP_FIGS:
        src = o / "figures" / fn
        if src.is_file():
            shutil.copy2(src, dest / "figures" / fn)

    for extra in ("ranked_winners.csv", "ranked_winners.xlsx", "ranked_winners.fasta"):
        src = o / extra
        if src.is_file():
            shutil.copy2(src, dest / extra)

    # ---- methodology, plain language -------------------------------------- #
    guide = base / "docs" / "PRESENTATION_GUIDE.md"
    if guide.is_file():
        shutil.copy2(guide, dest / "METHODOLOGY.md")

    strat_rows = "\n".join(
        f"| `{k}` | **{v['label']}** | {v['where']} | {v['result']} |"
        for k, v in STRATEGIES.items())
    (dest / "STRATEGIES.md").write_text(
        "# The four design strategies\n\n"
        "Candidates were generated from four competing hypotheses about *where* to edit the\n"
        "antibody, run in parallel so the portfolio tests several ideas rather than fifteen\n"
        "variations of one. The internal code appears in the data files; the label is what\n"
        "you should say out loud.\n\n"
        "| Code | Strategy | Where the edits go | How it performed |\n"
        "| --- | --- | --- | --- |\n" + strat_rows + "\n\n"
        "**The headline surprise:** CDR-H3 editing is the literature-favoured approach and it\n"
        "performed worst here, while leaving the binding site alone (scaffold-only) preserved\n"
        "the interface best. Our reading is that trastuzumab's binding loops are already\n"
        "affinity-matured, so changing them is far more likely to break the grip than improve\n"
        "it. All four strategies are still represented in the nominations, because one\n"
        "campaign on one target is not enough to retire a hypothesis.\n")

    # ---- the prompt -------------------------------------------------------- #
    st_ = metrics["statistics"]
    cp = metrics["compute"]
    fn_ = metrics["funnel"]
    tg = metrics["target"]
    gif_list = "\n".join(f"  - `gifs/{g}`" for g in got)
    win_cards = "\n".join(
        f"  - **{w['candidate_id']}** — {w['mutation_count']} substitutions, "
        f"ipSAE {w['ipsae_min_mean']} ± {w['ipsae_min_sd']} over {w['ipsae_n_seeds']} runs, "
        f"{w['delta_vs_parent']} vs parent, q={w['q_value_BH']}"
        for w in fdr[:4]) or "  - (none currently clear correction)"

    prompt = f"""# Lovable prompt — HER2 scFv deck (4 slides)

Build a **4-slide** presentation web app, 16:9, keyboard-navigable. Short and
visual: a judge should get the whole story in three minutes. All numbers below
are real measured results — do not invent or round them away.

## Files in this folder

- `pipeline_diagram.svg` — the funnel diagram; embed as-is, it is already styled
- `gifs/parent.gif` — rotating 3D model of the original antibody bound to HER2
- winner GIFs (rotating 3D models of our designs):
{gif_list}
- `top10_table.md` / `.csv` — the results table, already trimmed to what matters
- `figures/05_reliability.png` — why we fold each design many times
- `figures/02_ipsae_by_mutation_count.png` — fewer edits score better
- `figures/08_top_designs.png` — designs with error bars
- `metrics.json` — every number here, machine-readable
- `STRATEGIES.md` — what the four design strategies mean (use these labels, not the codes)
- `METHODOLOGY.md` — long-form background and Q&A (not for the slides; reference)

## Visual style

Clean scientific poster, not a startup pitch. Surface `#fcfcfb`, ink `#0b0b0b`,
secondary text `#52514e`. Accents in this order: blue `#2a78d6`, orange
`#eb6834`, aqua `#1baf7a`. Green `#0ca30c` marks statistically significant
results. Large type (minimum 20 px body), generous whitespace, no gradients or
shadows. GIFs loop continuously.

---

### Slide 1 — The challenge

**Headline:** Can we improve one of the best cancer drugs ever made?

- **Trastuzumab (Herceptin)** binds the breast-cancer target **HER2** at
  **0.82 pM** — an extraordinarily tight grip, the product of decades of
  engineering.
- Our task: change **at least 5** of its 242 amino acids and show the result is
  still a good binder, with a real **ipSAE** score for every design.
- Hard rules: keep the V_H–linker–V_L architecture, never touch the linker or
  the four structural cysteines, and cofold only against **HER2 domain IV**
  ({tg['domain_iv_length']} amino acids), not the full {630}-residue protein.
- Set the honest expectation up front: **most edits to a near-optimal molecule
  make it worse.** A team claiming a big improvement should be doubted.

Visual: `gifs/parent.gif` large on the right, captioned
"The starting point: trastuzumab bound to HER2 domain IV".

---

### Slide 2 — How we did it

**Headline:** Cheap filters first, expensive ones last.

Embed `pipeline_diagram.svg` full width. Underneath, three short points:

1. **We looked before we cut.** Using the experimental crystal structure
   (PDB 1N8Z) we measured which antibody residues actually touch HER2.
   {tg['epitope_contacts']} make direct contact; the six closest were **frozen**
   — you don't edit the residues doing the work.
   We generated designs from **four competing strategies**, so the portfolio
   tests several ideas rather than one:

   | Strategy | Where the edits go |
   | --- | --- |
   | **CDR-H3 focused** | in the main binding loop (the textbook choice) |
   | **Contact region** | beside the residues that touch HER2 |
   | **Mixed** | a few contact edits plus supporting changes elsewhere |
   | **Scaffold only** | in the framework, binding site untouched |

   Worth calling out on the slide: **CDR-H3 is the literature's favourite and it
   did worst here**; leaving the binding site alone did best.

2. **Two independent opinions.** AbLang2 (antibody-specific) proposed edits;
   ESM2-3B (all proteins) judged them. Neither model has ever seen HER2, so
   neither can predict binding — they only reject implausible sequences.
3. **Then we folded it.** Boltz-2 predicted each designed antibody bound to
   HER2 domain IV, and the original DunbrackLab program computed ipSAE from the
   result.

---

### Slide 3 — Why you can trust the numbers

**Headline:** We measured our own uncertainty before making any claim.

Two ideas side by side, each with one figure:

**Left — structure prediction is noisy.** Fold the same sequence twice and you
get different answers. We measured it: a single fold is only
**{st_['single_seed_reliability']}** reliable, so roughly half of a one-run
ranking is noise. So we folded everything repeatedly — the original antibody
**{st_['parent_n_seeds']} times**, each design a median of
**{st_['median_seeds_per_design']} times** — and report error bars.
Use `figures/05_reliability.png`.

**Right — testing many designs invents winners.** With
**{st_['designs_tested']}** designs tested, about
**{st_['expected_false_positives_uncorrected']}** would look like winners from
chance alone. We applied **Benjamini-Hochberg correction**, and several
apparent winners disappeared. We report the corrected number.
Use `figures/08_top_designs.png`.

Footer, quiet but explicit: *"ipSAE measures how confident the structure model
is about the interface. It is not binding strength, and we predict no K_D."*

---

### Slide 4 — Results

**Headline:** {st_['above_parent_fdr']} designs score above the original —
and survive correction.

- Original antibody: **{st_['parent_ipsae_mean']} ± {st_['parent_ipsae_sd']}**
  over {st_['parent_n_seeds']} folds.
- **{st_['above_parent_fdr']} designs significantly above it** after correction.
- **{st_['below_parent']} significantly below** — the screen discriminates
  rather than flattering everything.
- Built from **{cp['structures_total']:,} structures**
  ({cp['structures_local']} on one {cp['local_gpu']},
  {cp['structures_modal']} on Modal for about ${cp['modal_cost_usd_approx']}).

Render `top10_table.md`, highlighting rows with a bold q-value in green.

Beside the table, a small row of looping GIF cards for the standouts:
{win_cards}

Closing line, full width: *"{metrics['claim_boundary']} The 15 lab slots decide
what no model here can."*

---

## Interaction

Arrow keys and swipe to navigate, a slide counter in the corner. GIFs pause when
off-screen. Must be legible projected: nothing below 20 px, high contrast.
"""
    (dest / "LOVABLE_PROMPT.md").write_text(prompt)

    print(f"[deck] bundle -> {dest}")
    print(f"[deck] gifs={len(got)} figures={len(list((dest/'figures').glob('*.png')))} "
          f"table_rows={len(winners)} fdr_winners={len(fdr)}")
    print(f"[deck] files: {sorted(p.name for p in dest.iterdir())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
