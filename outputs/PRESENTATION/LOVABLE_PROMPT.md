# Lovable prompt — HER2 scFv deck (4 slides)

Build a **4-slide** presentation web app, 16:9, keyboard-navigable. Short and
visual: a judge should get the whole story in three minutes. All numbers below
are real measured results — do not invent or round them away.

## Files in this folder

- `pipeline_diagram.svg` — the funnel diagram; embed as-is, it is already styled
- `gifs/parent.gif` — rotating 3D model of the original antibody bound to HER2
- winner GIFs (rotating 3D models of our designs):
  - `gifs/parent.gif`
  - `gifs/HER2_1238.gif`
  - `gifs/HER2_13625.gif`
  - `gifs/HER2_17118.gif`
  - `gifs/HER2_14514.gif`
  - `gifs/HER2_11519.gif`
  - `gifs/HER2_5693.gif`
  - `gifs/HER2_9557.gif`
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
  (119 amino acids), not the full 630-residue protein.
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
   19 make direct contact; the six closest were **frozen**
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
**0.504** reliable, so roughly half of a one-run
ranking is noise. So we folded everything repeatedly — the original antibody
**42 times**, each design a median of
**8 times** — and report error bars.
Use `figures/05_reliability.png`.

**Right — testing many designs invents winners.** With
**249** designs tested, about
**12.5** would look like winners from
chance alone. We applied **Benjamini-Hochberg correction**, and several
apparent winners disappeared. We report the corrected number.
Use `figures/08_top_designs.png`.

Footer, quiet but explicit: *"ipSAE measures how confident the structure model
is about the interface. It is not binding strength, and we predict no K_D."*

---

### Slide 4 — Results

**Headline:** 7 designs score above the original —
and survive correction.

- Original antibody: **0.7003 ± 0.0546**
  over 42 folds.
- **7 designs significantly above it** after correction.
- **135 significantly below** — the screen discriminates
  rather than flattering everything.
- Built from **2,432 structures**
  (629 on one 1x RTX 3090 24 GB,
  1803 on Modal for about $8.29).

Render `top10_table.md`, highlighting rows with a bold q-value in green.

Beside the table, a small row of looping GIF cards for the standouts:
  - **HER2_1238** — 5 substitutions, ipSAE 0.737 ± 0.0386 over 39 runs, 0.0367 vs parent, q=0.00242
  - **HER2_13625** — 8 substitutions, ipSAE 0.7487 ± 0.0231 over 38 runs, 0.0484 vs parent, q=0.0
  - **HER2_17118** — 6 substitutions, ipSAE 0.7291 ± 0.0325 over 23 runs, 0.0288 vs parent, q=0.02152
  - **HER2_18216** — 7 substitutions, ipSAE 0.7269 ± 0.0274 over 22 runs, 0.0266 vs parent, q=0.0247

Closing line, full width: *"ipSAE is interface confidence from a structure predictor, not a binding affinity. No K_D is predicted. The 15 lab slots decide
what no model here can."*

---

## Interaction

Arrow keys and swipe to navigate, a slide counter in the corner. GIFs pause when
off-screen. Must be legible projected: nothing below 20 px, high contrast.
