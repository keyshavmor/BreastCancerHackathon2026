# Method walkthrough: HER2 scFv optimisation

Generated 2026-10-31T15:08:26.992340+00:00 from this run's own artifacts.

> **Claim boundary.** Every value below is a computational ranking signal for experimental triage. No affinity is measured or predicted. ipSAE is not K_D, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. The parent is already a sub-picomolar binder, so the prior that any 5-8 substitution variant improves on it is low by construction.

## What was produced

| Deliverable | Count |
| --- | --- |
| Valid internal proposals (`internal_50_candidates.*`) | 50 |
| Designs with a real, externally computed ipSAE (`submission_scored.*`) | 249 |
| Ranked lab nominations (`top_15_scored.*`) | 15 |
| Designs excluded, with recorded reasons | 1 |
| Boltz-2 structures computed | 193 |

Compliance audit: **PASS** (0 failed checks).

## 1. Immutable parent, verified not assumed

Every stage re-verifies the parent on import and aborts on mismatch, so no design can be built against the wrong scaffold.

| Property | Value |
| --- | --- |
| Length | 242 |
| SHA-256 | `0b9248c76a2b399791c47dbfa0d252b18284265f1dbca9ae8e66c0dd018c9f64` |
| V_H / linker / V_L | 1-120 / 121-135 `(GGGGS)x3` / 136-242 |
| Native cysteines | 22, 96, 158, 223 |

CDRs are located by exact motif match rather than hard-coded indices:

| CDR | Span | Sequence |
| --- | --- | --- |
| CDR-H1 | 31-35 | `DTYIH` |
| CDR-H2 | 50-66 | `RIYPTNGYTRYADSVKG` |
| CDR-H3 | 99-109 | `WGGDGFYAMDY` |
| CDR-L1 | 159-169 | `RASQDVNTAVA` |
| CDR-L2 | 185-191 | `SASFLYS` |
| CDR-L3 | 224-232 | `QQHYTTPPT` |

## 2. Target: HER2 domain IV, derived from primary data

Built from RCSB `1N8Z` and UniProt `P04626` only. 1N8Z chain A is the Fab light chain, B the heavy chain, C the HER2 ectodomain; chain C is numbered in HER2 **mature** numbering (`uniprot = mature + 22`).

| Property | Value |
| --- | --- |
| Crop (mature) | 489-607 |
| Crop (UniProt) | 511-629 |
| Crop length | 119 aa |
| Intact disulfides in crop | 8 (0 split) |
| Fab-contacting HER2 residues retained | 37 |
| Boltz complex size | 361 residues |

The crop is validated three ways before anything is cofolded: it must not split a disulfide (checked against `SSBOND` records), it must retain every observed Fab-contacting residue, and its sequence must match UniProt exactly. Any failure is a hard exit. **The full ~630-residue ectodomain is never cofolded**, per the organizer's restriction, and the same crop is used for the parent and every candidate so all comparisons are matched by construction.

Caveats recorded: cropping removes receptor context and creates artificial termini, and crystallographic glycans are not modelled.

## 3. Candidate generation (AbLang2-guided)

| Parameter | Value |
| --- | --- |
| Raw proposals sampled | 40000 |
| Valid unique candidates kept | 40000 |
| Shortlist to ESM2 | 4000 |
| Mutation band | [5, 8] substitutions |
| Frozen tight-contact anchors | [50, 103, 165, 226, 227, 229] |
| Anchor cutoff | 3.0 A |
| Substitutions kept per site | 5 |
| Random seed | 20261031 |
| Runtime | 41.6 s |

Hard-filter rejections (the validator is fail-closed):

- `introduces 1 new N-X-S/T sequon(s)`: 2815
- `introduces 2 new N-X-S/T sequon(s)`: 64

Mutation-count distribution: {'5': 8369, '6': 10678, '7': 10965, '8': 9988}

**Mutation policy.** Fixed length 242, substitution-only, 5-8 substitutions (organizer minimum is 5; the upper bound is our own conservative choice). The linker and native cysteines are frozen, no new cysteines or N-X-S/T sequons are allowed, and residues within 3.0 A of HER2 in 1N8Z are frozen as probable hydrogen-bond or salt-bridge anchors carrying the sub-pM binding energy.

**Why four branches.** Fifty neighbours of one motif are not fifty hypotheses, so candidates are sampled from four independent mechanistic pools:

| Branch | Slots | Hypothesis |
| --- | --- | --- |
| `A_h3` | 20 | focused CDR-H3 maturation (strongest published evidence) |
| `B_interface` | 12 | non-H3 paratope and contact-adjacent positions |
| `C_mixed` | 10 | a few paratope edits plus compatible framework support |
| `D_framework` | 8 | framework-biased control retaining all anchors |

Selection within a branch uses farthest-point selection on Jaccard distance between mutated-position sets, which is what prevents the portfolio collapsing onto one motif.

## 4. Sequence screening with two orthogonal priors

AbLang2 asks whether a sequence still looks like a plausible *antibody*; ESM2-3B asks whether it still looks like a plausible *protein*. The models have different training distributions and different failure modes, which is the reason for running both. **Neither model sees HER2, so neither predicts binding.**

| Parameter | Value |
| --- | --- |
| Model | `esm2_t36_3B_UR50D` (bf16) |
| Candidates scored | 4000 |
| Mutable positions scanned | 223 |
| Cost per candidate | 61.7 ms |
| Peak GPU memory | 10.91 GiB |

**Numerical control.** 12 candidates were rescored in fp32: max |diff| 0.1330, mean |diff| 0.0433, NaNs present: False. This is immaterial for ranking; use `--fp32` if absolute scores are needed.

**Scoring design.** Each model is run once over the mutable positions to build a `position x amino-acid` delta-log-probability table; a candidate's additive score is then a table lookup. A second pass scores each candidate's mutated positions in its own context, which is the term that can see interaction between co-occurring substitutions. Making the expensive part pool-size independent is what allows a 40,000-candidate pool at negligible cost.

Ranking across models uses **rank aggregation of percentile ranks**, not a weighted sum of raw scores: AbLang2 and ESM2 log-probabilities are in incomparable units, and absolute thresholds borrowed from one model do not transfer to another.

## 5. Boltz-2 cofolding against HER2 domain IV

| Parameter | Value |
| --- | --- |
| Structures completed | 193 of 193 planned |
| Mean cost per structure | 16.1 s |
| Total GPU time | 51.7 min |
| Diffusion samples / recycling / sampling steps | 1 / 3 / 200 |
| Seeds | [42, 7, 13] |
| MSA mode | `retarget` |
| Failures | 0 |

**MSA policy, and why it matters.** The ColabFold MSA server costs roughly 100 s per target and is rate-limited. It is called **once**, for the parent; both resulting alignments are cached and reused for every candidate, with only the query row rewritten to the candidate's own sequence. This is exact for substitution-only variants at fixed length, because every alignment column stays in register. Over a 150-design campaign this converts about six hours of mostly idle waiting into under an hour of GPU work, and it has a scientific benefit: every design is predicted under a byte-identical MSA condition, so parent-relative comparison is matched rather than assumed.

Identical crop, MSA condition, seed protocol, recycling and sampling settings are applied to the parent and to every candidate. Boltz-2's small-molecule affinity head is **not** used; it is not a calibrated antibody-HER2 K_D estimator.

## 6. ipSAE: computed externally, never proxied

Boltz-2 does not emit ipSAE. Each prediction's full PAE matrix and mmCIF are passed to the authoritative DunbrackLab/IPSAE implementation and the values parsed back.

| Parameter | Value |
| --- | --- |
| Predictions scored | 1583 of 1583 |
| PAE cutoff | 10.0 A |
| Distance cutoff | 15.0 A |
| IPSAE commit | `6174cf9e71cb` |

Primary metric is `ipsae_min = min(asym B->T, asym T->B)`, the conservative of the two directional values. Chain order is `T` = HER2 domain IV, `B` = scFv. `ipSAE_provenance.csv` records the script commit, both cutoffs, the metric definition, the chain mapping and the artifact paths for every design.

A prediction with a missing or unreadable PAE, a PAE/structure residue mismatch, or a failed ipSAE run is recorded with a non-`PASSED` status and **excluded**. No ipSAE value is ever estimated, interpolated or carried over from another design.

**Parent baseline** (matched settings): ipsae_min 0.7127 +/- 0.0445 over ? seed(s); epitope recovery 0.9662.

**Epitope recovery** is reported alongside ipSAE: the fraction of experimentally observed 1N8Z epitope residues still contacted in the predicted complex. ipSAE cannot distinguish a correct interface from a confident but misplaced one, so a model recovering less than 30% of the known epitope is rejected regardless of its ipSAE.

## 6b. Do the sequence scores predict the structure? (measured each run)

Spearman rank correlation between each sequence-stage predictor and each structural outcome, over n=249 ipSAE-complete designs.

| Predictor | ipsae_min | epitope_recovery | iptm |
| --- | ---: | ---: | ---: |
| `ablang2_contextual` | +0.060 | -0.168 | +0.022 |
| `esm2_contextual` | -0.217 | -0.122 | -0.223 |
| `ablang2_additive_mean` | -0.412 | -0.459 | -0.451 |
| `esm2_additive_mean` | -0.402 | -0.295 | -0.425 |
| `sequence_consensus_score` | -0.010 | +0.065 | -0.033 |
| `mutation_count` | +0.033 | +0.158 | +0.023 |

**Interpretation.** Negative rho means a HIGHER sequence-plausibility score goes with a WORSE modelled interface. Trastuzumab's CDRs are affinity-matured, so an antibody language model tends to propose reverting them toward germline consensus - precisely the residues contacting HER2. The mutation_count effect is partly confounded by MSA reuse.

This is the single most consequential empirical result of the run: it means selecting candidates by maximising sequence plausibility optimises a proxy that points **away** from interface quality. Later rounds therefore use sequence consensus as a floor (reject the implausible tail) rather than as a maximand, and stratify the structural budget by mutation count and branch instead (`requeue_structure_informed.py`).

### By mutation count

| Mutations | n | ipSAE_min | ipTM | Epitope recovery |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 121 | 0.5741 +/- 0.152 | 0.840 | 0.869 |
| 6 | 32 | 0.5869 +/- 0.146 | 0.845 | 0.902 |
| 7 | 31 | 0.6577 +/- 0.060 | 0.881 | 0.936 |
| 8 | 65 | 0.5668 +/- 0.128 | 0.839 | 0.892 |
| *parent* | - | *0.7127* | - | *0.966* |

### How much of the ipSAE ranking is real?

A variance decomposition over the designs that were run under multiple seeds. This is the number that governs every other claim in this document.

| Quantity | Value |
| --- | ---: |
| Designs with replicates | 250 |
| Mean seeds per design | 6.33 |
| sd within design (seed noise) | 0.1179 |
| sd between designs (observed) | 0.1388 |
| sd between designs (true, est.) | 0.1306 |
| **Reliability of a single seed** | **0.551** |
| Reliability of the current mean | 0.886 |
| Seeds needed for reliability 0.8 | 4 |
| Seeds needed for reliability 0.9 | 8 |

Reliability is the fraction of ranking variance that is real signal rather than seed noise. A value near 0.5 means a single-seed ranking is close to a coin flip between designs of similar quality, so **a single-seed ipSAE table must not be read as an ordering of design quality.**

Because the measurements are noisy, the correlations in the table above are *attenuated* toward zero. Dividing by sqrt(reliability) (x1.35) estimates the underlying relationships with ipSAE:

- `ablang2_contextual`: 0.0803
- `esm2_contextual`: -0.2929
- `ablang2_additive_mean`: -0.5550
- `esm2_additive_mean`: -0.5416
- `sequence_consensus_score`: -0.0132
- `mutation_count`: 0.0439

So the true effects are **stronger** than measured, not weaker - including the negative ones.

### Replicated designs tested against the parent

Parent baseline 0.7127 +/- 0.0445 over 14 seeds. Welch-style comparison, significance threshold |t| > 2.

**Above parent: 5 | below: 138 | indistinguishable: 106** (uncorrected, |t| > 2)

**Multiple-comparison correction.** 249 designs were tested, so at an uncorrected alpha of 0.05 roughly **12.5** of them would clear |t| > 2 by chance alone. Applying Benjamini-Hochberg FDR at q<0.05 over all tested designs, the number of designs significantly above the parent is **3**. An uncorrected count of 5 is therefore not evidence of improvement, and the table below reports q-values so this cannot be misread.

| Design | seeds | ipSAE mean | sd | delta | t | q (BH) | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `HER2_14514` | 11 | 0.7560 | 0.0168 | +0.0433 | +3.35 | 0.008 | ABOVE_PARENT_FDR |
| `HER2_17641` | 10 | 0.7528 | 0.0416 | +0.0402 | +2.27 | 0.067 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2696` | 2 | 0.7507 | 0.0166 | +0.0381 | +2.28 | 0.075 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13625` | 11 | 0.7500 | 0.0207 | +0.0373 | +2.78 | 0.025 | ABOVE_PARENT_FDR |
| `HER2B_0955` | 2 | 0.7452 | 0.0048 | +0.0326 | +2.63 | 0.044 | ABOVE_PARENT_FDR |
| `HER2B_10177` | 2 | 0.7330 | 0.0324 | +0.0203 | +0.79 | 0.513 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1238` | 14 | 0.7322 | 0.0283 | +0.0195 | +1.38 | 0.243 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1488` | 2 | 0.7315 | 0.0262 | +0.0189 | +0.86 | 0.478 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0949` | 2 | 0.7307 | 0.0181 | +0.0181 | +1.04 | 0.399 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17118` | 11 | 0.7304 | 0.0361 | +0.0177 | +1.10 | 0.369 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17465` | 11 | 0.7290 | 0.0510 | +0.0164 | +0.84 | 0.481 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0096` | 2 | 0.7286 | 0.0687 | +0.0159 | +0.32 | 0.795 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18461` | 10 | 0.7276 | 0.0379 | +0.0150 | +0.89 | 0.464 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_27115` | 2 | 0.7275 | 0.0354 | +0.0149 | +0.54 | 0.664 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17254` | 8 | 0.7269 | 0.0382 | +0.0142 | +0.79 | 0.511 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14954` | 14 | 0.7262 | 0.0280 | +0.0136 | +0.97 | 0.425 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23723` | 11 | 0.7246 | 0.0519 | +0.0119 | +0.61 | 0.620 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21202` | 11 | 0.7221 | 0.0197 | +0.0095 | +0.71 | 0.556 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0930` | 2 | 0.7220 | 0.0363 | +0.0093 | +0.33 | 0.791 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18216` | 10 | 0.7220 | 0.0338 | +0.0093 | +0.58 | 0.637 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15056` | 10 | 0.7213 | 0.0510 | +0.0087 | +0.43 | 0.730 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_28172` | 10 | 0.7203 | 0.0321 | +0.0076 | +0.49 | 0.690 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1375` | 2 | 0.7192 | 0.0201 | +0.0065 | +0.35 | 0.778 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_13932` | 2 | 0.7179 | 0.1019 | +0.0052 | +0.07 | 0.949 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0302` | 2 | 0.7174 | 0.0045 | +0.0047 | +0.38 | 0.765 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_6999` | 8 | 0.7154 | 0.0415 | +0.0028 | +0.15 | 0.912 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1330` | 2 | 0.7153 | 0.0103 | +0.0027 | +0.19 | 0.888 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_19503` | 10 | 0.7142 | 0.0328 | +0.0015 | +0.10 | 0.936 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2110` | 2 | 0.7138 | 0.0045 | +0.0011 | +0.09 | 0.941 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15988` | 10 | 0.7133 | 0.0245 | +0.0007 | +0.05 | 0.961 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_5693` | 12 | 0.7111 | 0.0387 | -0.0016 | -0.10 | 0.936 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1251` | 2 | 0.7107 | 0.0313 | -0.0019 | -0.08 | 0.945 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1612` | 2 | 0.7103 | 0.0266 | -0.0024 | -0.11 | 0.936 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_22350` | 8 | 0.7097 | 0.0326 | -0.0029 | -0.18 | 0.891 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13103` | 8 | 0.7081 | 0.0828 | -0.0045 | -0.14 | 0.916 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_2720` | 10 | 0.7068 | 0.0383 | -0.0059 | -0.35 | 0.778 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15259` | 8 | 0.7066 | 0.0604 | -0.0060 | -0.25 | 0.846 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_22721` | 8 | 0.7064 | 0.0708 | -0.0062 | -0.23 | 0.858 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3536` | 10 | 0.7060 | 0.0342 | -0.0066 | -0.41 | 0.742 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_9557` | 12 | 0.7023 | 0.0640 | -0.0104 | -0.47 | 0.702 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_19004` | 10 | 0.7016 | 0.0328 | -0.0110 | -0.70 | 0.561 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14939` | 10 | 0.7008 | 0.0575 | -0.0119 | -0.55 | 0.656 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_24248` | 8 | 0.6982 | 0.0243 | -0.0144 | -0.99 | 0.418 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23455` | 8 | 0.6979 | 0.0362 | -0.0148 | -0.85 | 0.478 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_15832` | 2 | 0.6975 | 0.0366 | -0.0152 | -0.53 | 0.669 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_34846` | 10 | 0.6948 | 0.0296 | -0.0179 | -1.18 | 0.330 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11519` | 15 | 0.6946 | 0.0658 | -0.0181 | -0.87 | 0.471 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11572` | 8 | 0.6944 | 0.0472 | -0.0182 | -0.89 | 0.464 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15708` | 11 | 0.6939 | 0.0464 | -0.0187 | -1.02 | 0.400 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1130` | 2 | 0.6936 | 0.0727 | -0.0191 | -0.36 | 0.777 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_19389` | 2 | 0.6933 | 0.0046 | -0.0193 | -1.57 | 0.196 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8022` | 11 | 0.6933 | 0.0864 | -0.0194 | -0.68 | 0.572 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_24532` | 10 | 0.6932 | 0.0663 | -0.0195 | -0.81 | 0.499 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21848` | 8 | 0.6928 | 0.0390 | -0.0199 | -1.09 | 0.372 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1025` | 2 | 0.6923 | 0.0463 | -0.0204 | -0.59 | 0.636 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0538` | 2 | 0.6911 | 0.0123 | -0.0215 | -1.46 | 0.229 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_10014` | 8 | 0.6908 | 0.0562 | -0.0218 | -0.94 | 0.444 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_12026` | 8 | 0.6892 | 0.0524 | -0.0235 | -1.07 | 0.382 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8386` | 11 | 0.6875 | 0.0345 | -0.0251 | -1.59 | 0.182 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13086` | 11 | 0.6875 | 0.0441 | -0.0252 | -1.41 | 0.234 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0719` | 2 | 0.6865 | 0.0074 | -0.0261 | -2.01 | 0.110 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_18668` | 2 | 0.6847 | 0.0047 | -0.0280 | -2.26 | 0.076 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_16732` | 2 | 0.6841 | 0.0155 | -0.0285 | -1.77 | 0.150 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17485` | 10 | 0.6838 | 0.0718 | -0.0289 | -1.13 | 0.355 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11912` | 8 | 0.6834 | 0.0429 | -0.0293 | -1.52 | 0.203 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_7827` | 10 | 0.6833 | 0.0422 | -0.0293 | -1.64 | 0.171 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21342` | 10 | 0.6831 | 0.0469 | -0.0295 | -1.55 | 0.193 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15323` | 8 | 0.6820 | 0.0332 | -0.0307 | -1.84 | 0.130 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13727` | 8 | 0.6798 | 0.1010 | -0.0328 | -0.87 | 0.472 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_22339` | 8 | 0.6794 | 0.0359 | -0.0333 | -1.91 | 0.118 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2747` | 2 | 0.6793 | 0.0035 | -0.0334 | -2.75 | 0.037 | BELOW_PARENT_FDR |
| `HER2B_0888` | 2 | 0.6787 | 0.0589 | -0.0340 | -0.78 | 0.517 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_10318` | 2 | 0.6787 | 0.0948 | -0.0340 | -0.50 | 0.688 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3091` | 10 | 0.6785 | 0.0536 | -0.0342 | -1.65 | 0.169 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21408` | 10 | 0.6768 | 0.0430 | -0.0359 | -1.99 | 0.104 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_26656` | 11 | 0.6759 | 0.0619 | -0.0367 | -1.66 | 0.166 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0104` | 2 | 0.6754 | 0.0075 | -0.0372 | -2.86 | 0.030 | BELOW_PARENT_FDR |
| `HER2_21152` | 8 | 0.6752 | 0.0449 | -0.0374 | -1.89 | 0.121 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_10808` | 11 | 0.6751 | 0.0530 | -0.0376 | -1.89 | 0.119 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1834` | 2 | 0.6719 | 0.0494 | -0.0408 | -1.11 | 0.371 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_3098` | 2 | 0.6712 | 0.0226 | -0.0415 | -2.08 | 0.100 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_20989` | 10 | 0.6673 | 0.0831 | -0.0454 | -1.57 | 0.188 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0070` | 12 | 0.6651 | 0.0407 | -0.0475 | -2.85 | 0.022 | BELOW_PARENT_FDR |
| `HER2_18401` | 8 | 0.6647 | 0.0548 | -0.0479 | -2.11 | 0.088 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_9279` | 2 | 0.6637 | 0.0112 | -0.0490 | -3.43 | 0.012 | BELOW_PARENT_FDR |
| `HER2_20055` | 8 | 0.6625 | 0.1536 | -0.0501 | -0.90 | 0.462 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_24204` | 2 | 0.6618 | 0.0032 | -0.0509 | -4.20 | 0.004 | BELOW_PARENT_FDR |
| `HER2_10341` | 8 | 0.6587 | 0.0881 | -0.0540 | -1.62 | 0.177 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0077` | 12 | 0.6584 | 0.0791 | -0.0543 | -2.11 | 0.084 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15853` | 8 | 0.6581 | 0.0536 | -0.0546 | -2.44 | 0.052 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8798` | 10 | 0.6580 | 0.0555 | -0.0547 | -2.58 | 0.039 | BELOW_PARENT_FDR |
| `HER2_2407` | 8 | 0.6578 | 0.0495 | -0.0548 | -2.59 | 0.040 | BELOW_PARENT_FDR |
| `HER2B_0412` | 2 | 0.6578 | 0.0332 | -0.0549 | -2.09 | 0.099 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_16400` | 2 | 0.6563 | 0.0146 | -0.0564 | -3.58 | 0.009 | BELOW_PARENT_FDR |
| `HER2_15523` | 8 | 0.6550 | 0.0602 | -0.0577 | -2.37 | 0.058 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_22359` | 8 | 0.6548 | 0.0785 | -0.0579 | -1.92 | 0.117 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11456` | 13 | 0.6537 | 0.0797 | -0.0589 | -2.35 | 0.056 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_23444` | 3 | 0.6534 | 0.0029 | -0.0593 | -4.94 | 0.001 | BELOW_PARENT_FDR |
| `HER2_19487` | 8 | 0.6527 | 0.0821 | -0.0599 | -1.91 | 0.118 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8533` | 11 | 0.6527 | 0.0511 | -0.0600 | -3.08 | 0.015 | BELOW_PARENT_FDR |
| `HER2B_3742` | 2 | 0.6526 | 0.0779 | -0.0601 | -1.07 | 0.387 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14799` | 10 | 0.6524 | 0.0325 | -0.0603 | -3.84 | 0.004 | BELOW_PARENT_FDR |
| `HER2_2788` | 8 | 0.6519 | 0.0571 | -0.0608 | -2.60 | 0.039 | BELOW_PARENT_FDR |
| `HER2_14172` | 8 | 0.6502 | 0.0806 | -0.0625 | -2.02 | 0.101 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_31150` | 8 | 0.6498 | 0.0629 | -0.0629 | -2.49 | 0.048 | BELOW_PARENT_FDR |
| `HER2_23198` | 11 | 0.6491 | 0.1259 | -0.0635 | -1.60 | 0.179 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_7401` | 10 | 0.6486 | 0.0529 | -0.0641 | -3.12 | 0.014 | BELOW_PARENT_FDR |
| `HER2_11678` | 11 | 0.6481 | 0.0830 | -0.0646 | -2.33 | 0.059 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23267` | 10 | 0.6469 | 0.0564 | -0.0658 | -3.07 | 0.015 | BELOW_PARENT_FDR |
| `HER2B_1971` | 2 | 0.6412 | 0.0465 | -0.0714 | -2.05 | 0.104 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0417` | 2 | 0.6399 | 0.0811 | -0.0728 | -1.24 | 0.312 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_12122` | 8 | 0.6394 | 0.0861 | -0.0733 | -2.24 | 0.071 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18746` | 8 | 0.6379 | 0.0253 | -0.0748 | -5.03 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0478` | 2 | 0.6350 | 0.0225 | -0.0776 | -3.91 | 0.006 | BELOW_PARENT_FDR |
| `HER2_18778` | 8 | 0.6347 | 0.0849 | -0.0780 | -2.42 | 0.054 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1456` | 2 | 0.6342 | 0.0422 | -0.0785 | -2.45 | 0.058 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_6796` | 8 | 0.6339 | 0.0453 | -0.0787 | -3.95 | 0.003 | BELOW_PARENT_FDR |
| `HER2B_1116` | 2 | 0.6323 | 0.0612 | -0.0803 | -1.79 | 0.147 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_22714` | 8 | 0.6322 | 0.1044 | -0.0805 | -2.08 | 0.093 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14143` | 8 | 0.6318 | 0.0666 | -0.0808 | -3.06 | 0.017 | BELOW_PARENT_FDR |
| `HER2_8859` | 8 | 0.6291 | 0.0735 | -0.0835 | -2.92 | 0.021 | BELOW_PARENT_FDR |
| `HER2B_1058` | 2 | 0.6279 | 0.0358 | -0.0847 | -3.03 | 0.022 | BELOW_PARENT_FDR |
| `HER2B_0290` | 2 | 0.6266 | 0.0623 | -0.0861 | -1.89 | 0.129 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17233` | 10 | 0.6243 | 0.0736 | -0.0883 | -3.38 | 0.008 | BELOW_PARENT_FDR |
| `HER2B_15746` | 3 | 0.6241 | 0.0836 | -0.0886 | -1.78 | 0.147 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8404` | 8 | 0.6230 | 0.0442 | -0.0897 | -4.56 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_0309` | 2 | 0.6207 | 0.0278 | -0.0920 | -4.01 | 0.005 | BELOW_PARENT_FDR |
| `HER2B_1050` | 2 | 0.6206 | 0.0005 | -0.0920 | -7.74 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1204` | 3 | 0.6195 | 0.0668 | -0.0932 | -2.31 | 0.070 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1401` | 11 | 0.6192 | 0.0765 | -0.0935 | -3.60 | 0.005 | BELOW_PARENT_FDR |
| `HER2_20561` | 8 | 0.6180 | 0.1408 | -0.0947 | -1.85 | 0.129 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1306` | 2 | 0.6166 | 0.1273 | -0.0960 | -1.06 | 0.390 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1038` | 2 | 0.6136 | 0.0048 | -0.0991 | -8.02 | 0.000 | BELOW_PARENT_FDR |
| `HER2_7739` | 8 | 0.6117 | 0.0585 | -0.1009 | -4.23 | 0.002 | BELOW_PARENT_FDR |
| `HER2_11611` | 8 | 0.6116 | 0.0715 | -0.1011 | -3.62 | 0.006 | BELOW_PARENT_FDR |
| `HER2_12194` | 8 | 0.6098 | 0.1283 | -0.1029 | -2.20 | 0.076 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15879` | 8 | 0.6097 | 0.1121 | -0.1030 | -2.49 | 0.048 | BELOW_PARENT_FDR |
| `HER2B_32745` | 2 | 0.6087 | 0.0805 | -0.1039 | -1.79 | 0.147 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_9311` | 8 | 0.6077 | 0.0697 | -0.1049 | -3.84 | 0.004 | BELOW_PARENT_FDR |
| `HER2_1936` | 10 | 0.6068 | 0.0622 | -0.1058 | -4.60 | 0.001 | BELOW_PARENT_FDR |
| `HER2_14063` | 8 | 0.6066 | 0.0406 | -0.1061 | -5.70 | 0.000 | BELOW_PARENT_FDR |
| `HER2_14212` | 8 | 0.6064 | 0.1185 | -0.1062 | -2.44 | 0.052 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_12122` | 2 | 0.6039 | 0.0451 | -0.1087 | -3.19 | 0.017 | BELOW_PARENT_FDR |
| `HER2B_6691` | 3 | 0.6029 | 0.1383 | -0.1098 | -1.36 | 0.260 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_4384` | 2 | 0.6027 | 0.0855 | -0.1100 | -1.79 | 0.147 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_14367` | 2 | 0.6006 | 0.0739 | -0.1121 | -2.09 | 0.099 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_10933` | 8 | 0.5995 | 0.0780 | -0.1132 | -3.77 | 0.005 | BELOW_PARENT_FDR |
| `HER2_0737` | 10 | 0.5988 | 0.1168 | -0.1139 | -2.94 | 0.019 | BELOW_PARENT_FDR |
| `HER2B_1769` | 2 | 0.5972 | 0.0961 | -0.1154 | -1.67 | 0.173 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21798` | 8 | 0.5967 | 0.2445 | -0.1159 | -1.33 | 0.264 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17437` | 10 | 0.5958 | 0.0536 | -0.1168 | -5.64 | 0.000 | BELOW_PARENT_FDR |
| `HER2_19316` | 10 | 0.5956 | 0.0832 | -0.1170 | -4.05 | 0.002 | BELOW_PARENT_FDR |
| `HER2_27820` | 8 | 0.5944 | 0.0540 | -0.1183 | -5.26 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_9348` | 2 | 0.5934 | 0.1818 | -0.1193 | -0.92 | 0.458 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_27314` | 8 | 0.5919 | 0.0863 | -0.1208 | -3.69 | 0.005 | BELOW_PARENT_FDR |
| `HER2_5265` | 10 | 0.5910 | 0.0503 | -0.1216 | -6.13 | 0.000 | BELOW_PARENT_FDR |
| `HER2_4977` | 11 | 0.5908 | 0.1297 | -0.1219 | -2.98 | 0.018 | BELOW_PARENT_FDR |
| `HER2_24489` | 8 | 0.5887 | 0.0780 | -0.1240 | -4.13 | 0.002 | BELOW_PARENT_FDR |
| `HER2B_0881` | 2 | 0.5884 | 0.0421 | -0.1242 | -3.88 | 0.006 | BELOW_PARENT_FDR |
| `HER2_4189` | 8 | 0.5838 | 0.0715 | -0.1288 | -4.61 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_0054` | 2 | 0.5818 | 0.0476 | -0.1308 | -3.66 | 0.008 | BELOW_PARENT_FDR |
| `HER2_10485` | 8 | 0.5782 | 0.1715 | -0.1345 | -2.18 | 0.077 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_12757` | 8 | 0.5778 | 0.0992 | -0.1348 | -3.64 | 0.006 | BELOW_PARENT_FDR |
| `HER2_11449` | 10 | 0.5774 | 0.2162 | -0.1353 | -1.95 | 0.110 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_4906` | 8 | 0.5731 | 0.0910 | -0.1396 | -4.07 | 0.003 | BELOW_PARENT_FDR |
| `HER2_18279` | 8 | 0.5723 | 0.0645 | -0.1403 | -5.46 | 0.000 | BELOW_PARENT_FDR |
| `HER2_1582` | 10 | 0.5677 | 0.0951 | -0.1450 | -4.48 | 0.001 | BELOW_PARENT_FDR |
| `HER2_3494` | 8 | 0.5675 | 0.1114 | -0.1452 | -3.53 | 0.007 | BELOW_PARENT_FDR |
| `HER2_8252` | 8 | 0.5672 | 0.1325 | -0.1454 | -3.01 | 0.018 | BELOW_PARENT_FDR |
| `HER2_23768` | 8 | 0.5661 | 0.0982 | -0.1465 | -3.99 | 0.003 | BELOW_PARENT_FDR |
| `HER2_13381` | 8 | 0.5613 | 0.1482 | -0.1513 | -2.82 | 0.025 | BELOW_PARENT_FDR |
| `HER2B_2120` | 2 | 0.5601 | 0.0363 | -0.1525 | -5.39 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_1703` | 2 | 0.5575 | 0.0858 | -0.1551 | -2.51 | 0.054 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0100` | 2 | 0.5569 | 0.1215 | -0.1557 | -1.80 | 0.147 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23717` | 8 | 0.5511 | 0.1148 | -0.1615 | -3.82 | 0.004 | BELOW_PARENT_FDR |
| `HER2_4432` | 8 | 0.5496 | 0.0979 | -0.1631 | -4.46 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_0849` | 2 | 0.5487 | 0.0750 | -0.1640 | -3.02 | 0.022 | BELOW_PARENT_FDR |
| `HER2B_0692` | 2 | 0.5453 | 0.0874 | -0.1674 | -2.66 | 0.042 | BELOW_PARENT_FDR |
| `HER2_25740` | 8 | 0.5382 | 0.1113 | -0.1745 | -4.24 | 0.002 | BELOW_PARENT_FDR |
| `HER2B_1114` | 2 | 0.5380 | 0.1147 | -0.1747 | -2.13 | 0.093 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2228` | 2 | 0.5364 | 0.1813 | -0.1762 | -1.37 | 0.259 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0136` | 8 | 0.5338 | 0.1013 | -0.1789 | -4.74 | 0.001 | BELOW_PARENT_FDR |
| `HER2_9340` | 8 | 0.5308 | 0.1127 | -0.1819 | -4.38 | 0.001 | BELOW_PARENT_FDR |
| `HER2_4786` | 10 | 0.5259 | 0.1576 | -0.1867 | -3.64 | 0.005 | BELOW_PARENT_FDR |
| `HER2_1036` | 10 | 0.5153 | 0.1354 | -0.1973 | -4.44 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_1315` | 2 | 0.5115 | 0.0018 | -0.2012 | -16.82 | 0.000 | BELOW_PARENT_FDR |
| `HER2_2566` | 8 | 0.5073 | 0.0717 | -0.2054 | -7.34 | 0.000 | BELOW_PARENT_FDR |
| `HER2_17087` | 8 | 0.5067 | 0.0518 | -0.2060 | -9.43 | 0.000 | BELOW_PARENT_FDR |
| `HER2_11522` | 8 | 0.4938 | 0.1196 | -0.2189 | -4.98 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_0209` | 2 | 0.4917 | 0.0061 | -0.2210 | -17.47 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0371` | 2 | 0.4873 | 0.0950 | -0.2254 | -3.30 | 0.015 | BELOW_PARENT_FDR |
| `HER2B_0470` | 2 | 0.4846 | 0.1613 | -0.2281 | -1.99 | 0.113 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_16818` | 3 | 0.4817 | 0.1708 | -0.2310 | -2.33 | 0.068 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1749` | 2 | 0.4806 | 0.1306 | -0.2320 | -2.49 | 0.055 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0111` | 2 | 0.4802 | 0.3802 | -0.2325 | -0.86 | 0.478 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0021` | 2 | 0.4756 | 0.1364 | -0.2370 | -2.44 | 0.058 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_15697` | 2 | 0.4718 | 0.0211 | -0.2409 | -12.61 | 0.000 | BELOW_PARENT_FDR |
| `HER2_17896` | 8 | 0.4682 | 0.1414 | -0.2445 | -4.76 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_1801` | 2 | 0.4680 | 0.1062 | -0.2446 | -3.22 | 0.017 | BELOW_PARENT_FDR |
| `HER2B_24898` | 2 | 0.4676 | 0.1527 | -0.2450 | -2.26 | 0.076 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_12233` | 8 | 0.4654 | 0.2005 | -0.2473 | -3.44 | 0.008 | BELOW_PARENT_FDR |
| `HER2_9009` | 8 | 0.4648 | 0.1391 | -0.2479 | -4.90 | 0.001 | BELOW_PARENT_FDR |
| `HER2_13869` | 8 | 0.4610 | 0.0618 | -0.2517 | -10.12 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1203` | 2 | 0.4601 | 0.2410 | -0.2525 | -1.48 | 0.224 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0902` | 2 | 0.4553 | 0.1082 | -0.2574 | -3.32 | 0.014 | BELOW_PARENT_FDR |
| `HER2_4995` | 8 | 0.4552 | 0.1344 | -0.2575 | -5.25 | 0.000 | BELOW_PARENT_FDR |
| `HER2_3990` | 10 | 0.4538 | 0.0922 | -0.2589 | -8.22 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1644` | 2 | 0.4476 | 0.2021 | -0.2651 | -1.85 | 0.137 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0038` | 8 | 0.4465 | 0.2296 | -0.2662 | -3.24 | 0.012 | BELOW_PARENT_FDR |
| `HER2_4714` | 8 | 0.4460 | 0.2077 | -0.2666 | -3.58 | 0.006 | BELOW_PARENT_FDR |
| `HER2B_31611` | 2 | 0.4446 | 0.2146 | -0.2681 | -1.76 | 0.151 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_4269` | 2 | 0.4438 | 0.2586 | -0.2688 | -1.47 | 0.226 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_2943` | 8 | 0.4421 | 0.2162 | -0.2705 | -3.50 | 0.007 | BELOW_PARENT_FDR |
| `HER2B_0180` | 2 | 0.4412 | 0.0614 | -0.2715 | -6.03 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0261` | 2 | 0.4412 | 0.1072 | -0.2715 | -3.54 | 0.010 | BELOW_PARENT_FDR |
| `HER2_6704` | 10 | 0.4340 | 0.1698 | -0.2787 | -5.07 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0936` | 3 | 0.4314 | 0.1339 | -0.2813 | -3.60 | 0.008 | BELOW_PARENT_FDR |
| `HER2B_10599` | 3 | 0.4314 | 0.2749 | -0.2813 | -1.77 | 0.149 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1793` | 2 | 0.4310 | 0.1266 | -0.2817 | -3.12 | 0.019 | BELOW_PARENT_FDR |
| `HER2_11770` | 8 | 0.4295 | 0.2015 | -0.2832 | -3.92 | 0.003 | BELOW_PARENT_FDR |
| `HER2B_1000` | 2 | 0.4267 | 0.2671 | -0.2860 | -1.51 | 0.214 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_2418` | 8 | 0.4248 | 0.1553 | -0.2879 | -5.12 | 0.000 | BELOW_PARENT_FDR |
| `HER2_3843` | 10 | 0.4192 | 0.1479 | -0.2934 | -6.08 | 0.000 | BELOW_PARENT_FDR |
| `HER2_3133` | 8 | 0.4074 | 0.1031 | -0.3053 | -7.96 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_4716` | 2 | 0.3958 | 0.0422 | -0.3169 | -9.88 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_2739` | 3 | 0.3954 | 0.3443 | -0.3173 | -1.59 | 0.190 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2319` | 2 | 0.3910 | 0.2577 | -0.3216 | -1.76 | 0.151 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_6901` | 8 | 0.3861 | 0.2224 | -0.3266 | -4.11 | 0.002 | BELOW_PARENT_FDR |
| `HER2_10423` | 8 | 0.3859 | 0.1625 | -0.3268 | -5.57 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_11515` | 2 | 0.3766 | 0.0952 | -0.3360 | -4.91 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_1893` | 2 | 0.3687 | 0.5214 | -0.3440 | -0.93 | 0.454 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0610` | 3 | 0.3645 | 0.3186 | -0.3481 | -1.89 | 0.128 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1340` | 10 | 0.3618 | 0.2340 | -0.3508 | -4.68 | 0.001 | BELOW_PARENT_FDR |
| `HER2_10007` | 8 | 0.3617 | 0.1692 | -0.3509 | -5.75 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_2117` | 2 | 0.3511 | 0.2172 | -0.3615 | -2.35 | 0.068 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_10031` | 8 | 0.3462 | 0.2583 | -0.3665 | -3.98 | 0.003 | BELOW_PARENT_FDR |
| `HER2_9367` | 8 | 0.3429 | 0.1530 | -0.3698 | -6.68 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1903` | 2 | 0.3405 | 0.0904 | -0.3722 | -5.72 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_2383` | 2 | 0.3078 | 0.0572 | -0.4048 | -9.61 | 0.000 | BELOW_PARENT_FDR |
| `HER2_1981` | 8 | 0.3008 | 0.2806 | -0.4119 | -4.12 | 0.002 | BELOW_PARENT_FDR |
| `HER2B_1580` | 2 | 0.2911 | 0.4117 | -0.4215 | -1.45 | 0.231 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0419` | 8 | 0.2764 | 0.2423 | -0.4362 | -5.04 | 0.000 | BELOW_PARENT_FDR |
| `HER2_1425` | 8 | 0.2329 | 0.2831 | -0.4798 | -4.76 | 0.001 | BELOW_PARENT_FDR |
| `HER2_1850` | 8 | 0.1903 | 0.2043 | -0.5223 | -7.14 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_20445` | 2 | 0.1041 | 0.0416 | -0.6085 | -19.16 | 0.000 | BELOW_PARENT_FDR |
| `HER2_0888` | 10 | 0.0959 | 0.0799 | -0.6168 | -22.08 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0801` | 2 | 0.0542 | 0.0766 | -0.6585 | -11.87 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0750` | 2 | 0.0000 | 0.0000 | -0.7127 | -59.94 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1174` | 2 | 0.0000 | 0.0000 | -0.7127 | -59.94 | 0.000 | BELOW_PARENT_FDR |

### By branch

| Branch | n | ipSAE_min | ipTM | Epitope recovery |
| --- | ---: | ---: | ---: | ---: |
| `A_h3` | 28 | 0.4772 | 0.796 | 0.847 |
| `B_interface` | 127 | 0.5706 | 0.838 | 0.859 |
| `C_mixed` | 67 | 0.6152 | 0.862 | 0.928 |
| `D_framework` | 27 | 0.6823 | 0.892 | 0.965 |

Note this **contradicts the premise** that CDR-H3 maturation is the strongest branch: the published evidence for H3-focused editing came from a different parent and a different assay. Here framework-biased edits best preserve the modelled interface. We report the discrepancy rather than suppressing it, and keep all four branches represented in the submission.

## 7. Selection: multi-objective and diversity-aware

Ranking is deliberately **not** 'sort by ipSAE'. Four reasons: ipSAE is not calibrated to K_D; a small ipSAE gap can be smaller than seed noise; a confident model can bind the wrong face; and near-identical neighbours are not independent hypotheses.

| Axis | Weight |
| --- | --- |
| sequence_consensus | 0.3 |
| ipsae | 0.25 |
| epitope_recovery | 0.2 |
| structural_confidence | 0.15 |
| developability | 0.1 |

**Seed-noise gate.** Pooled ipSAE standard deviation across replicated candidates: **0.0893**. A design whose advantage over the parent is smaller than this is labelled `WITHIN_SEED_NOISE` rather than presented as an improvement. Designs exceeding the parent beyond that noise: **0** of 249.

**Sensitivity analysis.** Because the weights are a stated hypothesis and not a fitted model, the whole set is re-ranked under three alternative weightings (ipSAE-heavy, sequence-heavy, equal). Each design carries `max_rank_shift_under_reweighting`, so a nominee whose position depends on a single metric is visible as such.

## 8. Lab nominations (top 15)

| Rank | ID | Branch | Muts | ipSAE_min | Δ vs parent | Interpretation | Epitope rec. | ipTM | Rank shift |
| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 4 | `HER2_13625` | C_mixed | 8 | 0.7500 | 0.0373 | WITHIN_SEED_NOISE | 0.947 | 0.913 | 5 |
| 33 | `HER2_14514` | C_mixed | 6 | 0.7560 | 0.0433 | WITHIN_SEED_NOISE | 0.923 | 0.914 | 40 |
| 65 | `HER2B_0955` | B_interface | 5 | 0.7452 | 0.0325 | WITHIN_SEED_NOISE | 0.895 | 0.904 | 61 |
| 1 | `HER2_11519` | C_mixed | 5 | 0.6946 | -0.0181 | WITHIN_SEED_NOISE | 0.983 | 0.894 | 8 |
| 2 | `HER2_1238` | B_interface | 5 | 0.7322 | 0.0195 | WITHIN_SEED_NOISE | 0.917 | 0.906 | 3 |
| 5 | `HER2_5693` | D_framework | 6 | 0.7111 | -0.0016 | WITHIN_SEED_NOISE | 0.974 | 0.896 | 7 |
| 6 | `HER2_15708` | D_framework | 6 | 0.6939 | -0.0188 | WITHIN_SEED_NOISE | 0.976 | 0.899 | 11 |
| 8 | `HER2_8022` | B_interface | 8 | 0.6933 | -0.0194 | WITHIN_SEED_NOISE | 0.957 | 0.895 | 17 |
| 9 | `HER2_9557` | A_h3 | 8 | 0.7023 | -0.0104 | WITHIN_SEED_NOISE | 0.969 | 0.902 | 12 |
| 21 | `HER2_18461` | C_mixed | 5 | 0.7276 | 0.0149 | WITHIN_SEED_NOISE | 0.937 | 0.908 | 9 |
| 23 | `HER2_15988` | B_interface | 8 | 0.7133 | 0.0006 | WITHIN_SEED_NOISE | 0.958 | 0.899 | 23 |
| 52 | `HER2_13103` | B_interface | 6 | 0.7081 | -0.0046 | WITHIN_SEED_NOISE | 0.822 | 0.901 | 5 |
| 83 | `HER2_11611` | A_h3 | 5 | 0.6116 | -0.1011 | BELOW_PARENT | 0.954 | 0.873 | 36 |
| 94 | `HER2_4995` | A_h3 | 8 | 0.4552 | -0.2575 | BELOW_PARENT | 0.987 | 0.799 | 66 |
| 123 | `HER2_1582` | A_h3 | 8 | 0.5677 | -0.1450 | BELOW_PARENT | 0.900 | 0.850 | 69 |

Mutation lists for each nominee are in `top_15_scored.csv` (`mutations_1based`), and each sequence is independently reconstructible by re-applying that list to the frozen parent - a check the audit performs.

## 9. Independent compliance audit

Computed from the real output files, after and independently of the stages that produced them.

| Check | Result | Detail |
| --- | --- | --- |
| parent_integrity | **PASS** | len=242 sha256=0b9248c76a2b399791c47dbfa0d252b18284265f1dbca9ae8e66c0dd018c9f64 |
| internal_pool_exists | **PASS** | 50 internal candidates |
| all_submitted_length_242 | **PASS** | violations=[] |
| all_submitted_min_5_mutations | **PASS** | violations=[] |
| linker_intact | **PASS** | violations=[] |
| native_cysteines_preserved_no_new | **PASS** | violations=[] |
| submitted_sequences_unique | **PASS** | 249 rows, 249 unique |
| mutation_signatures_unique | **PASS** | 249 unique signatures |
| reconstructible_from_mutation_list | **PASS** | violations=[] |
| every_submitted_has_finite_ipsae | **PASS** | violations=[] |
| structure_and_pae_present_for_submitted | **PASS** | violations=[] |
| parent_baseline_scored | **PASS** | parent ipsae_min=0.7127 over 14 seed(s) |
| no_stale_EGFR_cetuximab_inputs | **PASS** | files_with_stale_refs=[] |
| top15_size | **PASS** | 15/15 nominees |
| top15_branch_diversity | **PASS** | branches=['A_h3', 'B_interface', 'C_mixed', 'D_framework'] |
| top15_distinct_mutation_sets | **PASS** | each nominee has a distinct mutation signature |

## 10. Limitations

- **No affinity is predicted.** ipSAE, ipTM, pLDDT, pDockQ and LIS are model confidence and interface-geometry measures. None is a K_D, and none is calibrated against sub-picomolar antibody binding.
- **The parent is very strong.** At 0.82 pM, assay floor and rebinding effects make improvement hard to demonstrate even experimentally.
- **Cropping changes the system.** Domain IV alone lacks receptor context, has artificial termini, and omits glycans. It is required by the organizer and applied identically everywhere, but it is still an approximation.
- **The MSA query-row reuse is an approximation**, exact in alignment terms for substitution-only variants but not a re-derived alignment per mutant.
- **Language-model priors are blind to the target.** AbLang2, ESM2 and ESM-C never see HER2; they can only reject implausible sequences, not identify better binders.
- **Selection weights are unvalidated.** They are a reasoned hypothesis; the sensitivity analysis quantifies how much the answer depends on them.
- **Single structure per seed.** One diffusion sample per seed; replicates quantify seed variance but not full conformational uncertainty.
- **No experimental feedback.** Without in-campaign assay data this is not Bayesian optimisation; it is one-shot constrained screening over model priors.

## Reproducibility

- repository commit: `51e7bc75e86ba585bb296744d2e662152045a46c` (working tree dirty)
- parent SHA-256: `0b9248c76a2b399791c47dbfa0d252b18284265f1dbca9ae8e66c0dd018c9f64`
- `bash scripts/run_her2_pipeline.sh` reruns the whole pipeline; stages are idempotent and resumable.
- per-stage manifests (`stage*_manifest.json`) record models, precisions, seeds, timings and peak memory.

