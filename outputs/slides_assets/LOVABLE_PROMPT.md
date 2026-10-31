# Lovable build prompt — HER2 scFv optimisation deck

Build a presentation web app (single page, keyboard-navigable slides, 16:9) for a
computational antibody-engineering result. Everything below is real measured
data from the run; do not invent numbers.

## Assets (in this folder)

- `figures/*.png` — nine campaign figures, already styled; display as-is
- `gifs/parent.gif` — rotating 3D model of the unmodified parent complex
- `gifs/<DESIGN_ID>.gif` — rotating 3D models of the winning designs
- `ranking_table.csv` / `ranking_table.md` — the ranked results table
- `metrics.json` — every number below, machine-readable

## Design direction

Scientific-poster clarity, not startup-pitch gloss. Light surface `#fcfcfb`,
ink `#0b0b0b`, secondary `#52514e`. Accent palette, used in this fixed order:
blue `#2a78d6`, orange `#eb6834`, aqua `#1baf7a`. Green `#0ca30c` for
statistically significant results, red `#d03b3b` for failures. Generous
whitespace, one idea per slide, large readable type, no gradients or drop
shadows. Every slide that shows a number shows its uncertainty.

## Slides

**1 — Title.** "Optimising a trastuzumab scFv against HER2 domain IV".
Subtitle: 248 designs, 2178 structures,
every design carrying a genuine ipSAE. Background: `gifs/parent.gif`, subtle.

**2 — The problem.** The parent is Herceptin at **0.82 pM** — one of the most
optimised therapeutic antibodies ever made. Improving it is the hard case.
Constraints: ≥5 substitutions, ≤260 aa, fixed V_H-(GGGGS)x3-V_L topology,
linker and the four native cysteines untouchable.

**3 — Target preparation.** Derived from PDB 1N8Z and UniProt P04626, not
assumed. Crop HER2 to **domain IV only**: mature [489, 607],
119 aa, versus 630 aa for
the full ectodomain. 8 disulfides intact, zero
split. V_H/V_L match the crystal chains with **0
mismatches**. Use `figures/07_epitope_vs_ipsae.png`.

**4 — The funnel.** 40,000 AbLang2 candidates →
4,000 ESM2-3B screened → 250 cofolded →
248 with ipSAE → 50 ranked →
15 nominated. Emphasise: sequence models explore, Boltz-2
only confirms.

**5 — Throughput.** 2178 Boltz-2 structures
(611 local on a single 1x RTX 3090 24 GB,
1567 on Modal for about
$7.21). Key engineering: **one** MSA-server call total,
cached and reused, instead of ~100 s per design. Use
`figures/09_throughput.png`.

**6 — The measurement problem (the pivotal slide).** A single Boltz-2 seed
carries reliability **0.5** — about half of a
one-seed ranking is noise. 5 seeds are needed for
0.8. We replicated instead of broadening: median
**8 seeds per design**, parent at
**35 seeds**. Use `figures/05_reliability.png` and
`figures/04_replicate_spread.png`.

**7 — Guarding against false positives.** 249 designs were
tested. At an uncorrected α=0.05 about
**12.5** would clear |t|>2 by chance.
Uncorrected count: 10. After Benjamini-Hochberg:
**8**. State plainly that reporting the uncorrected number
would have been wrong.

**8 — Results.** Parent **0.6973 ± 0.0583**
over 35 seeds. Designs significantly above after correction:
**8**. Significantly below: 126 — the
screen discriminates. Render `ranking_table.md`, highlighting FDR-significant
rows in green.

**9 — The winners.** One card per design, each with its rotating GIF:

- **HER2_1238** — 5 substitutions, ipSAE 0.7368 ± 0.0367 over 33 seeds, Δ 0.0394 vs parent, q=0.00469, epitope recovery 0.9171
- **HER2_13625** — 8 substitutions, ipSAE 0.7478 ± 0.0222 over 32 seeds, Δ 0.0505 vs parent, q=0.0001, epitope recovery 0.9359
- **HER2_17118** — 6 substitutions, ipSAE 0.7308 ± 0.0314 over 16 seeds, Δ 0.0335 vs parent, q=0.02428, epitope recovery 0.9704
- **HER2_18216** — 7 substitutions, ipSAE 0.7267 ± 0.0301 over 15 seeds, Δ 0.0294 vs parent, q=0.04755, epitope recovery 0.9333
- **HER2_17641** — 8 substitutions, ipSAE 0.7587 ± 0.0356 over 15 seeds, Δ 0.0614 vs parent, q=0.00028, epitope recovery 0.8702
- **HER2_14514** — 6 substitutions, ipSAE 0.7546 ± 0.0175 over 17 seeds, Δ 0.0573 vs parent, q=0.0, epitope recovery 0.9164

**10 — What the data overturned.** Three findings that contradicted our
starting assumptions:
- A 1,000,000-candidate pool beat 40,000 by +49% on the top-500 band; the saturation we expected did not occur.
- Sequence-plausibility scores ANTI-correlate with interface quality (AbLang2 vs epitope recovery, rho ~ -0.47): the parent is affinity-matured, so language models push its CDRs back toward germline.
- CDR-H3 editing scored worst, not best, contradicting the starting hypothesis; framework-biased edits preserved the interface best.
Use `figures/06_score_correlations.png` and `figures/03_ipsae_by_branch.png`.

**11 — Claim boundary.** Full-width, sober, no decoration:
"ipSAE is interface confidence from a structure predictor, not a binding affinity. No K_D is predicted. The wet-lab assay decides."

**12 — Compliance and reproducibility.** Audit **PASS**,
0 failed checks. Every submitted design:
≥5 substitutions, linker intact, cysteines preserved, reconstructible from its
recorded mutation list. Domain IV only, no de novo tools, never ranked by ipSAE
alone.

## Interaction

Arrow-key and swipe navigation, a slide counter, and a key that toggles a
speaker-notes overlay. GIFs loop and pause when off-screen. Must read correctly
on a projector: minimum 20 px body text, high contrast throughout.
