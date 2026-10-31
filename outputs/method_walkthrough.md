# Method walkthrough: HER2 scFv optimisation

Generated 2026-10-31T15:33:20.795556+00:00 from this run's own artifacts.

> **Claim boundary.** Every value below is a computational ranking signal for experimental triage. No affinity is measured or predicted. ipSAE is not K_D, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. The parent is already a sub-picomolar binder, so the prior that any 5-8 substitution variant improves on it is low by construction.

## What was produced

| Deliverable | Count |
| --- | --- |
| Valid internal proposals (`internal_50_candidates.*`) | 50 |
| Designs with a real, externally computed ipSAE (`submission_scored.*`) | 248 |
| Ranked lab nominations (`top_15_scored.*`) | 15 |
| Designs excluded, with recorded reasons | 2 |
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
| Predictions scored | 2178 of 2178 |
| PAE cutoff | 10.0 A |
| Distance cutoff | 15.0 A |
| IPSAE commit | `6174cf9e71cb` |

Primary metric is `ipsae_min = min(asym B->T, asym T->B)`, the conservative of the two directional values. Chain order is `T` = HER2 domain IV, `B` = scFv. `ipSAE_provenance.csv` records the script commit, both cutoffs, the metric definition, the chain mapping and the artifact paths for every design.

A prediction with a missing or unreadable PAE, a PAE/structure residue mismatch, or a failed ipSAE run is recorded with a non-`PASSED` status and **excluded**. No ipSAE value is ever estimated, interpolated or carried over from another design.

**Parent baseline** (matched settings): ipsae_min 0.6973 +/- 0.0583 over ? seed(s); epitope recovery 0.9669.

**Epitope recovery** is reported alongside ipSAE: the fraction of experimentally observed 1N8Z epitope residues still contacted in the predicted complex. ipSAE cannot distinguish a correct interface from a confident but misplaced one, so a model recovering less than 30% of the known epitope is rejected regardless of its ipSAE.

## 6b. Do the sequence scores predict the structure? (measured each run)

Spearman rank correlation between each sequence-stage predictor and each structural outcome, over n=248 ipSAE-complete designs.

| Predictor | ipsae_min | epitope_recovery | iptm |
| --- | ---: | ---: | ---: |
| `ablang2_contextual` | +0.049 | -0.174 | +0.009 |
| `esm2_contextual` | -0.223 | -0.148 | -0.230 |
| `ablang2_additive_mean` | -0.432 | -0.457 | -0.468 |
| `esm2_additive_mean` | -0.408 | -0.310 | -0.432 |
| `sequence_consensus_score` | +0.051 | +0.065 | +0.025 |
| `mutation_count` | +0.103 | +0.151 | +0.089 |

**Interpretation.** Negative rho means a HIGHER sequence-plausibility score goes with a WORSE modelled interface. Trastuzumab's CDRs are affinity-matured, so an antibody language model tends to propose reverting them toward germline consensus - precisely the residues contacting HER2. The mutation_count effect is partly confounded by MSA reuse.

This is the single most consequential empirical result of the run: it means selecting candidates by maximising sequence plausibility optimises a proxy that points **away** from interface quality. Later rounds therefore use sequence consensus as a floor (reject the implausible tail) rather than as a maximand, and stratify the structural budget by mutation count and branch instead (`requeue_structure_informed.py`).

### By mutation count

| Mutations | n | ipSAE_min | ipTM | Epitope recovery |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 120 | 0.5654 +/- 0.143 | 0.836 | 0.863 |
| 6 | 32 | 0.5858 +/- 0.146 | 0.844 | 0.902 |
| 7 | 31 | 0.6530 +/- 0.060 | 0.879 | 0.932 |
| 8 | 65 | 0.5664 +/- 0.127 | 0.838 | 0.891 |
| *parent* | - | *0.6973* | - | *0.967* |

### How much of the ipSAE ranking is real?

A variance decomposition over the designs that were run under multiple seeds. This is the number that governs every other claim in this document.

| Quantity | Value |
| --- | ---: |
| Designs with replicates | 250 |
| Mean seeds per design | 8.71 |
| sd within design (seed noise) | 0.1278 |
| sd between designs (observed) | 0.1348 |
| sd between designs (true, est.) | 0.1277 |
| **Reliability of a single seed** | **0.500** |
| Reliability of the current mean | 0.897 |
| Seeds needed for reliability 0.8 | 5 |
| Seeds needed for reliability 0.9 | 10 |

Reliability is the fraction of ranking variance that is real signal rather than seed noise. A value near 0.5 means a single-seed ranking is close to a coin flip between designs of similar quality, so **a single-seed ipSAE table must not be read as an ordering of design quality.**

Because the measurements are noisy, the correlations in the table above are *attenuated* toward zero. Dividing by sqrt(reliability) (x1.42) estimates the underlying relationships with ipSAE:

- `ablang2_contextual`: 0.0696
- `esm2_contextual`: -0.3160
- `ablang2_additive_mean`: -0.6107
- `esm2_additive_mean`: -0.5770
- `sequence_consensus_score`: 0.0724
- `mutation_count`: 0.1457

So the true effects are **stronger** than measured, not weaker - including the negative ones.

### Replicated designs tested against the parent

Parent baseline 0.6973 +/- 0.0583 over 35 seeds. Welch-style comparison, significance threshold |t| > 2.

**Above parent: 10 | below: 126 | indistinguishable: 113** (uncorrected, |t| > 2)

**Multiple-comparison correction.** 249 designs were tested, so at an uncorrected alpha of 0.05 roughly **12.5** of them would clear |t| > 2 by chance alone. Applying Benjamini-Hochberg FDR at q<0.05 over all tested designs, the number of designs significantly above the parent is **8**. An uncorrected count of 10 is therefore not evidence of improvement, and the table below reports q-values so this cannot be misread.

| Design | seeds | ipSAE mean | sd | delta | t | q (BH) | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `HER2_17641` | 15 | 0.7587 | 0.0356 | +0.0614 | +4.55 | 0.000 | ABOVE_PARENT_FDR |
| `HER2_14514` | 17 | 0.7546 | 0.0175 | +0.0573 | +5.33 | 0.000 | ABOVE_PARENT_FDR |
| `HER2_13625` | 32 | 0.7478 | 0.0222 | +0.0505 | +4.75 | 0.000 | ABOVE_PARENT_FDR |
| `HER2B_2696` | 3 | 0.7448 | 0.0156 | +0.0475 | +3.55 | 0.004 | ABOVE_PARENT_FDR |
| `HER2B_1488` | 3 | 0.7428 | 0.0269 | +0.0455 | +2.47 | 0.038 | ABOVE_PARENT_FDR |
| `HER2_1238` | 33 | 0.7368 | 0.0367 | +0.0394 | +3.36 | 0.005 | ABOVE_PARENT_FDR |
| `HER2_17118` | 16 | 0.7308 | 0.0314 | +0.0335 | +2.66 | 0.024 | ABOVE_PARENT_FDR |
| `HER2_17465` | 16 | 0.7293 | 0.0564 | +0.0320 | +1.86 | 0.117 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_13932` | 3 | 0.7273 | 0.0739 | +0.0300 | +0.69 | 0.560 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17254` | 8 | 0.7269 | 0.0382 | +0.0296 | +1.77 | 0.136 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18216` | 15 | 0.7267 | 0.0301 | +0.0294 | +2.34 | 0.048 | ABOVE_PARENT_FDR |
| `HER2_14954` | 31 | 0.7227 | 0.0436 | +0.0254 | +2.02 | 0.088 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23723` | 16 | 0.7226 | 0.0441 | +0.0253 | +1.71 | 0.149 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_27115` | 3 | 0.7209 | 0.0275 | +0.0236 | +1.26 | 0.286 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21202` | 16 | 0.7207 | 0.0224 | +0.0234 | +2.07 | 0.081 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2110` | 3 | 0.7201 | 0.0114 | +0.0228 | +1.93 | 0.107 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_5693` | 32 | 0.7193 | 0.0368 | +0.0220 | +1.86 | 0.116 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18461` | 15 | 0.7192 | 0.0404 | +0.0219 | +1.53 | 0.192 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0949` | 9 | 0.7190 | 0.0254 | +0.0217 | +1.67 | 0.158 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15988` | 15 | 0.7160 | 0.0257 | +0.0187 | +1.57 | 0.182 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_6999` | 8 | 0.7154 | 0.0415 | +0.0181 | +1.02 | 0.383 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_28172` | 15 | 0.7131 | 0.0324 | +0.0158 | +1.22 | 0.299 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_19503` | 15 | 0.7110 | 0.0307 | +0.0137 | +1.08 | 0.352 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_9557` | 32 | 0.7101 | 0.0509 | +0.0128 | +0.96 | 0.412 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13103` | 8 | 0.7081 | 0.0828 | +0.0108 | +0.35 | 0.768 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15056` | 15 | 0.7080 | 0.0594 | +0.0107 | +0.58 | 0.622 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_19389` | 3 | 0.7078 | 0.0253 | +0.0105 | +0.59 | 0.618 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11519` | 33 | 0.7076 | 0.0385 | +0.0103 | +0.86 | 0.459 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0302` | 3 | 0.7068 | 0.0186 | +0.0095 | +0.65 | 0.583 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15259` | 8 | 0.7066 | 0.0604 | +0.0093 | +0.40 | 0.742 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_22721` | 8 | 0.7064 | 0.0708 | +0.0091 | +0.34 | 0.773 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1330` | 3 | 0.7063 | 0.0173 | +0.0090 | +0.64 | 0.588 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1375` | 3 | 0.7045 | 0.0291 | +0.0072 | +0.37 | 0.756 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_22350` | 13 | 0.7035 | 0.0270 | +0.0062 | +0.50 | 0.679 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_18668` | 3 | 0.7012 | 0.0288 | +0.0039 | +0.20 | 0.871 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_24248` | 8 | 0.6982 | 0.0243 | +0.0009 | +0.07 | 0.956 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1130` | 9 | 0.6980 | 0.0419 | +0.0007 | +0.04 | 0.972 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23455` | 8 | 0.6979 | 0.0362 | +0.0006 | +0.04 | 0.972 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_10014` | 14 | 0.6974 | 0.0455 | +0.0001 | +0.00 | 1.000 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14939` | 15 | 0.6949 | 0.0594 | -0.0024 | -0.13 | 0.915 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0930` | 3 | 0.6948 | 0.0537 | -0.0025 | -0.08 | 0.952 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11572` | 8 | 0.6944 | 0.0472 | -0.0029 | -0.15 | 0.903 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8386` | 16 | 0.6939 | 0.0314 | -0.0034 | -0.27 | 0.822 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_24532` | 10 | 0.6932 | 0.0663 | -0.0041 | -0.18 | 0.883 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_34846` | 15 | 0.6929 | 0.0259 | -0.0044 | -0.37 | 0.756 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21848` | 8 | 0.6928 | 0.0390 | -0.0045 | -0.27 | 0.822 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0538` | 3 | 0.6920 | 0.0088 | -0.0053 | -0.48 | 0.690 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8022` | 31 | 0.6901 | 0.0659 | -0.0072 | -0.47 | 0.691 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_12026` | 8 | 0.6892 | 0.0524 | -0.0081 | -0.39 | 0.747 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_2720` | 15 | 0.6887 | 0.0575 | -0.0086 | -0.48 | 0.690 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_10318` | 3 | 0.6872 | 0.0687 | -0.0101 | -0.25 | 0.834 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21342` | 15 | 0.6870 | 0.0426 | -0.0103 | -0.70 | 0.554 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11912` | 8 | 0.6834 | 0.0429 | -0.0139 | -0.77 | 0.511 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15323` | 8 | 0.6820 | 0.0332 | -0.0153 | -1.00 | 0.393 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0719` | 9 | 0.6810 | 0.0425 | -0.0163 | -0.95 | 0.416 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17485` | 15 | 0.6801 | 0.0655 | -0.0172 | -0.88 | 0.450 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13727` | 8 | 0.6798 | 0.1010 | -0.0175 | -0.47 | 0.691 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_10177` | 9 | 0.6794 | 0.0494 | -0.0179 | -0.93 | 0.422 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_22339` | 8 | 0.6794 | 0.0359 | -0.0179 | -1.11 | 0.342 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15708` | 16 | 0.6789 | 0.0550 | -0.0184 | -1.09 | 0.350 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3091` | 10 | 0.6785 | 0.0536 | -0.0188 | -0.96 | 0.412 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1834` | 3 | 0.6784 | 0.0367 | -0.0189 | -0.81 | 0.490 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2747` | 3 | 0.6773 | 0.0041 | -0.0200 | -1.97 | 0.101 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3536` | 30 | 0.6771 | 0.0872 | -0.0202 | -1.08 | 0.352 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21408` | 10 | 0.6768 | 0.0430 | -0.0205 | -1.22 | 0.299 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_3098` | 3 | 0.6764 | 0.0184 | -0.0209 | -1.44 | 0.219 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_15832` | 3 | 0.6763 | 0.0449 | -0.0210 | -0.76 | 0.516 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21152` | 8 | 0.6752 | 0.0449 | -0.0221 | -1.18 | 0.314 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_7827` | 15 | 0.6735 | 0.0443 | -0.0238 | -1.58 | 0.181 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_10808` | 17 | 0.6728 | 0.0432 | -0.0245 | -1.70 | 0.151 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_16732` | 3 | 0.6724 | 0.0230 | -0.0249 | -1.50 | 0.203 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1025` | 9 | 0.6716 | 0.0505 | -0.0257 | -1.32 | 0.261 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_19004` | 16 | 0.6715 | 0.0626 | -0.0258 | -1.40 | 0.231 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_20989` | 10 | 0.6673 | 0.0831 | -0.0300 | -1.07 | 0.356 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8798` | 15 | 0.6670 | 0.0522 | -0.0303 | -1.81 | 0.128 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13086` | 17 | 0.6663 | 0.0847 | -0.0310 | -1.36 | 0.243 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11456` | 31 | 0.6661 | 0.0881 | -0.0312 | -1.68 | 0.153 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_24204` | 3 | 0.6656 | 0.0070 | -0.0317 | -2.97 | 0.014 | BELOW_PARENT_FDR |
| `HER2_18401` | 8 | 0.6647 | 0.0548 | -0.0326 | -1.50 | 0.202 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0070` | 18 | 0.6638 | 0.0342 | -0.0335 | -2.63 | 0.026 | BELOW_PARENT_FDR |
| `HER2_26656` | 16 | 0.6627 | 0.0975 | -0.0346 | -1.31 | 0.263 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_20055` | 8 | 0.6625 | 0.1536 | -0.0348 | -0.63 | 0.592 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_16400` | 3 | 0.6598 | 0.0120 | -0.0375 | -3.11 | 0.010 | BELOW_PARENT_FDR |
| `HER2_10341` | 8 | 0.6587 | 0.0881 | -0.0386 | -1.18 | 0.314 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15853` | 8 | 0.6581 | 0.0536 | -0.0392 | -1.84 | 0.123 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_7401` | 30 | 0.6580 | 0.0888 | -0.0393 | -2.07 | 0.080 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_9279` | 3 | 0.6574 | 0.0135 | -0.0399 | -3.18 | 0.008 | BELOW_PARENT_FDR |
| `HER2B_0412` | 3 | 0.6552 | 0.0239 | -0.0421 | -2.48 | 0.038 | BELOW_PARENT_FDR |
| `HER2_15523` | 8 | 0.6550 | 0.0602 | -0.0423 | -1.81 | 0.128 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_22359` | 8 | 0.6548 | 0.0785 | -0.0425 | -1.44 | 0.219 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0417` | 3 | 0.6544 | 0.0626 | -0.0429 | -1.15 | 0.324 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_23444` | 3 | 0.6534 | 0.0029 | -0.0439 | -4.39 | 0.001 | BELOW_PARENT_FDR |
| `HER2_19487` | 8 | 0.6527 | 0.0821 | -0.0446 | -1.45 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14799` | 10 | 0.6524 | 0.0325 | -0.0449 | -3.16 | 0.008 | BELOW_PARENT_FDR |
| `HER2_14172` | 8 | 0.6502 | 0.0806 | -0.0471 | -1.56 | 0.185 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1456` | 3 | 0.6499 | 0.0404 | -0.0474 | -1.87 | 0.118 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_31150` | 8 | 0.6498 | 0.0629 | -0.0475 | -1.95 | 0.102 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23198` | 11 | 0.6491 | 0.1259 | -0.0482 | -1.23 | 0.297 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23267` | 10 | 0.6469 | 0.0564 | -0.0504 | -2.48 | 0.036 | BELOW_PARENT_FDR |
| `HER2_8533` | 16 | 0.6408 | 0.0546 | -0.0565 | -3.36 | 0.005 | BELOW_PARENT_FDR |
| `HER2_0077` | 18 | 0.6400 | 0.0933 | -0.0573 | -2.38 | 0.043 | BELOW_PARENT_FDR |
| `HER2B_0104` | 3 | 0.6397 | 0.0622 | -0.0576 | -1.55 | 0.189 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_12122` | 8 | 0.6394 | 0.0861 | -0.0579 | -1.81 | 0.128 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18746` | 8 | 0.6379 | 0.0253 | -0.0594 | -4.46 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1038` | 3 | 0.6374 | 0.0414 | -0.0599 | -2.31 | 0.053 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18778` | 8 | 0.6347 | 0.0849 | -0.0626 | -1.98 | 0.099 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11678` | 17 | 0.6343 | 0.1027 | -0.0630 | -2.35 | 0.046 | BELOW_PARENT_FDR |
| `HER2_6796` | 8 | 0.6339 | 0.0453 | -0.0634 | -3.37 | 0.005 | BELOW_PARENT_FDR |
| `HER2_22714` | 8 | 0.6322 | 0.1044 | -0.0651 | -1.70 | 0.152 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1306` | 3 | 0.6321 | 0.0939 | -0.0652 | -1.18 | 0.314 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_9348` | 3 | 0.6318 | 0.1448 | -0.0655 | -0.78 | 0.508 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14143` | 8 | 0.6318 | 0.0666 | -0.0655 | -2.56 | 0.031 | BELOW_PARENT_FDR |
| `HER2B_0955` | 9 | 0.6313 | 0.2373 | -0.0660 | -0.83 | 0.478 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_2407` | 13 | 0.6292 | 0.1021 | -0.0681 | -2.27 | 0.055 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8859` | 8 | 0.6291 | 0.0735 | -0.0682 | -2.45 | 0.039 | BELOW_PARENT_FDR |
| `HER2B_0096` | 3 | 0.6251 | 0.1857 | -0.0722 | -0.67 | 0.571 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_3742` | 3 | 0.6248 | 0.0730 | -0.0725 | -1.67 | 0.158 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17233` | 10 | 0.6243 | 0.0736 | -0.0730 | -2.89 | 0.015 | BELOW_PARENT_FDR |
| `HER2B_15746` | 3 | 0.6241 | 0.0836 | -0.0732 | -1.49 | 0.205 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0290` | 3 | 0.6212 | 0.0450 | -0.0761 | -2.74 | 0.023 | BELOW_PARENT_FDR |
| `HER2_1401` | 16 | 0.6212 | 0.0650 | -0.0761 | -4.00 | 0.001 | BELOW_PARENT_FDR |
| `HER2_9311` | 23 | 0.6204 | 0.0559 | -0.0769 | -5.04 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1204` | 3 | 0.6195 | 0.0668 | -0.0778 | -1.96 | 0.102 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_20561` | 8 | 0.6180 | 0.1408 | -0.0793 | -1.56 | 0.185 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1769` | 3 | 0.6170 | 0.0761 | -0.0803 | -1.78 | 0.136 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_12122` | 3 | 0.6142 | 0.0365 | -0.0831 | -3.58 | 0.004 | BELOW_PARENT_FDR |
| `HER2B_0888` | 3 | 0.6126 | 0.1218 | -0.0847 | -1.19 | 0.314 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_7739` | 8 | 0.6117 | 0.0585 | -0.0856 | -3.74 | 0.002 | BELOW_PARENT_FDR |
| `HER2_11611` | 8 | 0.6116 | 0.0715 | -0.0857 | -3.16 | 0.008 | BELOW_PARENT_FDR |
| `HER2_12194` | 8 | 0.6098 | 0.1283 | -0.0876 | -1.89 | 0.114 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15879` | 8 | 0.6097 | 0.1121 | -0.0876 | -2.15 | 0.072 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_14367` | 3 | 0.6085 | 0.0540 | -0.0888 | -2.72 | 0.024 | BELOW_PARENT_FDR |
| `HER2_1936` | 10 | 0.6068 | 0.0622 | -0.0905 | -4.11 | 0.001 | BELOW_PARENT_FDR |
| `HER2_14063` | 8 | 0.6066 | 0.0406 | -0.0907 | -5.21 | 0.000 | BELOW_PARENT_FDR |
| `HER2_14212` | 8 | 0.6064 | 0.1185 | -0.0909 | -2.11 | 0.077 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0054` | 3 | 0.6053 | 0.0527 | -0.0920 | -2.88 | 0.017 | BELOW_PARENT_FDR |
| `HER2B_6691` | 3 | 0.6029 | 0.1383 | -0.0944 | -1.17 | 0.317 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_10933` | 8 | 0.5995 | 0.0780 | -0.0978 | -3.34 | 0.006 | BELOW_PARENT_FDR |
| `HER2_0737` | 10 | 0.5988 | 0.1168 | -0.0985 | -2.58 | 0.030 | BELOW_PARENT_FDR |
| `HER2_21798` | 8 | 0.5967 | 0.2445 | -0.1006 | -1.16 | 0.319 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17437` | 10 | 0.5958 | 0.0536 | -0.1015 | -5.17 | 0.000 | BELOW_PARENT_FDR |
| `HER2_19316` | 10 | 0.5956 | 0.0832 | -0.1017 | -3.62 | 0.003 | BELOW_PARENT_FDR |
| `HER2_27820` | 8 | 0.5944 | 0.0540 | -0.1029 | -4.79 | 0.000 | BELOW_PARENT_FDR |
| `HER2_27314` | 8 | 0.5919 | 0.0863 | -0.1054 | -3.29 | 0.006 | BELOW_PARENT_FDR |
| `HER2B_4384` | 3 | 0.5915 | 0.0635 | -0.1058 | -2.79 | 0.021 | BELOW_PARENT_FDR |
| `HER2B_1050` | 3 | 0.5913 | 0.0509 | -0.1060 | -3.42 | 0.005 | BELOW_PARENT_FDR |
| `HER2_5265` | 10 | 0.5910 | 0.0503 | -0.1063 | -5.68 | 0.000 | BELOW_PARENT_FDR |
| `HER2_4977` | 11 | 0.5908 | 0.1297 | -0.1065 | -2.64 | 0.026 | BELOW_PARENT_FDR |
| `HER2_24489` | 8 | 0.5887 | 0.0780 | -0.1086 | -3.71 | 0.003 | BELOW_PARENT_FDR |
| `HER2_8252` | 23 | 0.5879 | 0.1404 | -0.1094 | -3.54 | 0.003 | BELOW_PARENT_FDR |
| `HER2_1582` | 25 | 0.5876 | 0.0702 | -0.1097 | -6.39 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_32745` | 3 | 0.5859 | 0.0693 | -0.1114 | -2.70 | 0.024 | BELOW_PARENT_FDR |
| `HER2_4189` | 8 | 0.5838 | 0.0715 | -0.1135 | -4.18 | 0.001 | BELOW_PARENT_FDR |
| `HER2_10485` | 8 | 0.5782 | 0.1715 | -0.1191 | -1.94 | 0.104 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11449` | 16 | 0.5782 | 0.1696 | -0.1191 | -2.74 | 0.021 | BELOW_PARENT_FDR |
| `HER2_12757` | 8 | 0.5778 | 0.0992 | -0.1195 | -3.28 | 0.006 | BELOW_PARENT_FDR |
| `HER2B_0100` | 3 | 0.5773 | 0.0929 | -0.1200 | -2.20 | 0.067 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8404` | 23 | 0.5753 | 0.1113 | -0.1220 | -4.84 | 0.000 | BELOW_PARENT_FDR |
| `HER2_4906` | 8 | 0.5731 | 0.0910 | -0.1242 | -3.69 | 0.003 | BELOW_PARENT_FDR |
| `HER2_18279` | 8 | 0.5723 | 0.0645 | -0.1250 | -5.03 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0881` | 3 | 0.5720 | 0.0412 | -0.1253 | -4.87 | 0.000 | BELOW_PARENT_FDR |
| `HER2_3494` | 8 | 0.5675 | 0.1114 | -0.1298 | -3.20 | 0.008 | BELOW_PARENT_FDR |
| `HER2_2788` | 23 | 0.5665 | 0.1860 | -0.1308 | -3.27 | 0.006 | BELOW_PARENT_FDR |
| `HER2_23768` | 8 | 0.5661 | 0.0982 | -0.1312 | -3.64 | 0.003 | BELOW_PARENT_FDR |
| `HER2B_2228` | 3 | 0.5640 | 0.1368 | -0.1333 | -1.67 | 0.158 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1058` | 3 | 0.5619 | 0.1172 | -0.1354 | -1.98 | 0.100 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13381` | 8 | 0.5613 | 0.1482 | -0.1360 | -2.55 | 0.032 | BELOW_PARENT_FDR |
| `HER2B_0478` | 3 | 0.5547 | 0.1400 | -0.1426 | -1.75 | 0.142 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23717` | 8 | 0.5511 | 0.1148 | -0.1462 | -3.50 | 0.004 | BELOW_PARENT_FDR |
| `HER2_4432` | 8 | 0.5496 | 0.0979 | -0.1477 | -4.10 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_24898` | 3 | 0.5473 | 0.1752 | -0.1500 | -1.48 | 0.208 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1114` | 3 | 0.5395 | 0.0812 | -0.1578 | -3.30 | 0.007 | BELOW_PARENT_FDR |
| `HER2_25740` | 8 | 0.5382 | 0.1113 | -0.1591 | -3.92 | 0.002 | BELOW_PARENT_FDR |
| `HER2B_0692` | 3 | 0.5365 | 0.0637 | -0.1608 | -4.23 | 0.001 | BELOW_PARENT_FDR |
| `HER2_0136` | 8 | 0.5338 | 0.1013 | -0.1635 | -4.40 | 0.001 | BELOW_PARENT_FDR |
| `HER2_9340` | 8 | 0.5308 | 0.1127 | -0.1665 | -4.06 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_1203` | 3 | 0.5296 | 0.2086 | -0.1677 | -1.39 | 0.237 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0209` | 3 | 0.5294 | 0.0655 | -0.1679 | -4.30 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_1116` | 3 | 0.5288 | 0.1844 | -0.1685 | -1.58 | 0.182 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1315` | 3 | 0.5287 | 0.0298 | -0.1686 | -8.50 | 0.000 | BELOW_PARENT_FDR |
| `HER2_4786` | 10 | 0.5259 | 0.1576 | -0.1714 | -3.37 | 0.005 | BELOW_PARENT_FDR |
| `HER2_1036` | 10 | 0.5153 | 0.1354 | -0.1820 | -4.14 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_0021` | 3 | 0.5123 | 0.1155 | -0.1850 | -2.74 | 0.023 | BELOW_PARENT_FDR |
| `HER2B_0371` | 3 | 0.5123 | 0.0800 | -0.1850 | -3.92 | 0.002 | BELOW_PARENT_FDR |
| `HER2_2566` | 8 | 0.5073 | 0.0717 | -0.1900 | -6.99 | 0.000 | BELOW_PARENT_FDR |
| `HER2_17087` | 8 | 0.5067 | 0.0518 | -0.1906 | -9.16 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1801` | 3 | 0.5026 | 0.0960 | -0.1947 | -3.46 | 0.005 | BELOW_PARENT_FDR |
| `HER2B_2120` | 3 | 0.5024 | 0.1033 | -0.1949 | -3.22 | 0.008 | BELOW_PARENT_FDR |
| `HER2B_0261` | 3 | 0.4938 | 0.1186 | -0.2035 | -2.94 | 0.015 | BELOW_PARENT_FDR |
| `HER2_11522` | 8 | 0.4938 | 0.1196 | -0.2035 | -4.69 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0470` | 3 | 0.4851 | 0.1141 | -0.2122 | -3.19 | 0.008 | BELOW_PARENT_FDR |
| `HER2B_0902` | 3 | 0.4841 | 0.0914 | -0.2132 | -3.97 | 0.002 | BELOW_PARENT_FDR |
| `HER2B_16818` | 3 | 0.4817 | 0.1708 | -0.2156 | -2.18 | 0.069 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1793` | 3 | 0.4764 | 0.1192 | -0.2209 | -3.18 | 0.008 | BELOW_PARENT_FDR |
| `HER2B_1251` | 3 | 0.4738 | 0.4109 | -0.2235 | -0.94 | 0.419 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1612` | 3 | 0.4735 | 0.4105 | -0.2238 | -0.94 | 0.419 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1749` | 3 | 0.4726 | 0.0934 | -0.2247 | -4.10 | 0.001 | BELOW_PARENT_FDR |
| `HER2_17896` | 8 | 0.4682 | 0.1414 | -0.2291 | -4.50 | 0.000 | BELOW_PARENT_FDR |
| `HER2_12233` | 8 | 0.4654 | 0.2005 | -0.2319 | -3.24 | 0.007 | BELOW_PARENT_FDR |
| `HER2_9009` | 8 | 0.4648 | 0.1391 | -0.2325 | -4.63 | 0.000 | BELOW_PARENT_FDR |
| `HER2_13869` | 8 | 0.4610 | 0.0618 | -0.2363 | -9.86 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1644` | 3 | 0.4573 | 0.1439 | -0.2400 | -2.87 | 0.017 | BELOW_PARENT_FDR |
| `HER2_4995` | 8 | 0.4552 | 0.1344 | -0.2421 | -4.99 | 0.000 | BELOW_PARENT_FDR |
| `HER2_3990` | 10 | 0.4538 | 0.0922 | -0.2435 | -7.91 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_2319` | 3 | 0.4519 | 0.2106 | -0.2454 | -2.01 | 0.095 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0038` | 8 | 0.4465 | 0.2296 | -0.2508 | -3.07 | 0.010 | BELOW_PARENT_FDR |
| `HER2_4714` | 8 | 0.4460 | 0.2077 | -0.2513 | -3.39 | 0.005 | BELOW_PARENT_FDR |
| `HER2B_1703` | 3 | 0.4453 | 0.2036 | -0.2520 | -2.14 | 0.075 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_2943` | 8 | 0.4421 | 0.2162 | -0.2552 | -3.31 | 0.006 | BELOW_PARENT_FDR |
| `HER2B_11515` | 3 | 0.4416 | 0.1311 | -0.2557 | -3.35 | 0.006 | BELOW_PARENT_FDR |
| `HER2B_1000` | 3 | 0.4394 | 0.1902 | -0.2579 | -2.34 | 0.050 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1903` | 3 | 0.4367 | 0.1784 | -0.2606 | -2.52 | 0.035 | BELOW_PARENT_FDR |
| `HER2B_31611` | 3 | 0.4357 | 0.1525 | -0.2616 | -2.95 | 0.015 | BELOW_PARENT_FDR |
| `HER2_6704` | 10 | 0.4340 | 0.1698 | -0.2634 | -4.83 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0849` | 3 | 0.4330 | 0.2073 | -0.2643 | -2.20 | 0.067 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0936` | 3 | 0.4314 | 0.1339 | -0.2659 | -3.41 | 0.005 | BELOW_PARENT_FDR |
| `HER2B_10599` | 3 | 0.4314 | 0.2749 | -0.2659 | -1.67 | 0.158 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11770` | 8 | 0.4295 | 0.2015 | -0.2678 | -3.72 | 0.003 | BELOW_PARENT_FDR |
| `HER2B_1971` | 3 | 0.4275 | 0.3717 | -0.2698 | -1.26 | 0.286 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_2418` | 8 | 0.4248 | 0.1553 | -0.2725 | -4.88 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0111` | 3 | 0.4204 | 0.2881 | -0.2769 | -1.66 | 0.160 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3843` | 10 | 0.4192 | 0.1479 | -0.2781 | -5.82 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0309` | 3 | 0.4138 | 0.3589 | -0.2835 | -1.37 | 0.243 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0180` | 3 | 0.4121 | 0.0665 | -0.2852 | -7.19 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_4269` | 3 | 0.4076 | 0.1933 | -0.2897 | -2.59 | 0.030 | BELOW_PARENT_FDR |
| `HER2_3133` | 8 | 0.4074 | 0.1031 | -0.2899 | -7.68 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_2117` | 3 | 0.4024 | 0.1774 | -0.2949 | -2.87 | 0.017 | BELOW_PARENT_FDR |
| `HER2B_2739` | 3 | 0.3954 | 0.3443 | -0.3019 | -1.52 | 0.198 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_15697` | 3 | 0.3908 | 0.1411 | -0.3065 | -3.73 | 0.003 | BELOW_PARENT_FDR |
| `HER2_6901` | 8 | 0.3861 | 0.2224 | -0.3112 | -3.93 | 0.002 | BELOW_PARENT_FDR |
| `HER2_10423` | 8 | 0.3859 | 0.1625 | -0.3114 | -5.34 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_4716` | 3 | 0.3692 | 0.0549 | -0.3281 | -9.89 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0610` | 3 | 0.3645 | 0.3186 | -0.3328 | -1.81 | 0.129 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1340` | 10 | 0.3618 | 0.2340 | -0.3355 | -4.49 | 0.000 | BELOW_PARENT_FDR |
| `HER2_10007` | 8 | 0.3617 | 0.1692 | -0.3356 | -5.54 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1893` | 3 | 0.3481 | 0.3704 | -0.3492 | -1.63 | 0.169 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_10031` | 8 | 0.3462 | 0.2583 | -0.3511 | -3.82 | 0.002 | BELOW_PARENT_FDR |
| `HER2_9367` | 8 | 0.3429 | 0.1530 | -0.3544 | -6.44 | 0.000 | BELOW_PARENT_FDR |
| `HER2_1981` | 8 | 0.3008 | 0.2806 | -0.3965 | -3.98 | 0.001 | BELOW_PARENT_FDR |
| `HER2_0419` | 8 | 0.2764 | 0.2423 | -0.4209 | -4.88 | 0.000 | BELOW_PARENT_FDR |
| `HER2_1425` | 8 | 0.2329 | 0.2831 | -0.4644 | -4.62 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0801` | 3 | 0.2254 | 0.3014 | -0.4719 | -2.71 | 0.024 | BELOW_PARENT_FDR |
| `HER2B_20445` | 3 | 0.2252 | 0.2117 | -0.4721 | -3.85 | 0.002 | BELOW_PARENT_FDR |
| `HER2B_2383` | 3 | 0.2090 | 0.1759 | -0.4883 | -4.79 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1580` | 3 | 0.1941 | 0.3362 | -0.5032 | -2.59 | 0.030 | BELOW_PARENT_FDR |
| `HER2_1850` | 8 | 0.1903 | 0.2043 | -0.5070 | -6.95 | 0.000 | BELOW_PARENT_FDR |
| `HER2_0888` | 10 | 0.0959 | 0.0799 | -0.6014 | -22.16 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0750` | 3 | 0.0000 | 0.0000 | -0.6973 | -70.71 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1174` | 3 | 0.0000 | 0.0000 | -0.6973 | -70.71 | 0.000 | BELOW_PARENT_FDR |

### By branch

| Branch | n | ipSAE_min | ipTM | Epitope recovery |
| --- | ---: | ---: | ---: | ---: |
| `A_h3` | 28 | 0.4747 | 0.795 | 0.846 |
| `B_interface` | 126 | 0.5627 | 0.834 | 0.853 |
| `C_mixed` | 67 | 0.6133 | 0.861 | 0.926 |
| `D_framework` | 27 | 0.6803 | 0.891 | 0.963 |

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

**Seed-noise gate.** Pooled ipSAE standard deviation across replicated candidates: **0.1003**. A design whose advantage over the parent is smaller than this is labelled `WITHIN_SEED_NOISE` rather than presented as an improvement. Designs exceeding the parent beyond that noise: **0** of 248.

**Sensitivity analysis.** Because the weights are a stated hypothesis and not a fitted model, the whole set is re-ranked under three alternative weightings (ipSAE-heavy, sequence-heavy, equal). Each design carries `max_rank_shift_under_reweighting`, so a nominee whose position depends on a single metric is visible as such.

## 8. Lab nominations (top 15)

| Rank | ID | Branch | Muts | ipSAE_min | Δ vs parent | Interpretation | Epitope rec. | ipTM | Rank shift |
| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 2 | `HER2_1238` | B_interface | 5 | 0.7368 | 0.0395 | WITHIN_SEED_NOISE | 0.917 | 0.907 | 1 |
| 7 | `HER2_13625` | C_mixed | 8 | 0.7478 | 0.0505 | WITHIN_SEED_NOISE | 0.936 | 0.913 | 3 |
| 8 | `HER2_17118` | C_mixed | 6 | 0.7308 | 0.0335 | WITHIN_SEED_NOISE | 0.970 | 0.904 | 11 |
| 11 | `HER2_18216` | D_framework | 7 | 0.7267 | 0.0294 | WITHIN_SEED_NOISE | 0.933 | 0.905 | 3 |
| 32 | `HER2_17641` | C_mixed | 8 | 0.7587 | 0.0614 | WITHIN_SEED_NOISE | 0.870 | 0.914 | 19 |
| 37 | `HER2_14514` | C_mixed | 6 | 0.7546 | 0.0573 | WITHIN_SEED_NOISE | 0.916 | 0.913 | 39 |
| 56 | `HER2B_2696` | B_interface | 5 | 0.7448 | 0.0475 | WITHIN_SEED_NOISE | 0.965 | 0.910 | 92 |
| 83 | `HER2B_1488` | B_interface | 5 | 0.7428 | 0.0455 | WITHIN_SEED_NOISE | 0.895 | 0.904 | 66 |
| 1 | `HER2_11519` | C_mixed | 5 | 0.7076 | 0.0103 | WITHIN_SEED_NOISE | 0.976 | 0.898 | 1 |
| 3 | `HER2_5693` | D_framework | 6 | 0.7193 | 0.0220 | WITHIN_SEED_NOISE | 0.975 | 0.898 | 2 |
| 6 | `HER2_9557` | A_h3 | 8 | 0.7101 | 0.0128 | WITHIN_SEED_NOISE | 0.970 | 0.905 | 6 |
| 9 | `HER2_15708` | D_framework | 6 | 0.6789 | -0.0184 | WITHIN_SEED_NOISE | 0.980 | 0.894 | 12 |
| 15 | `HER2_8022` | B_interface | 8 | 0.6901 | -0.0072 | WITHIN_SEED_NOISE | 0.946 | 0.894 | 11 |
| 19 | `HER2_18461` | C_mixed | 5 | 0.7192 | 0.0219 | WITHIN_SEED_NOISE | 0.933 | 0.904 | 15 |
| 22 | `HER2_7401` | B_interface | 6 | 0.6580 | -0.0393 | WITHIN_SEED_NOISE | 0.970 | 0.877 | 35 |

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
| submitted_sequences_unique | **PASS** | 248 rows, 248 unique |
| mutation_signatures_unique | **PASS** | 248 unique signatures |
| reconstructible_from_mutation_list | **PASS** | violations=[] |
| every_submitted_has_finite_ipsae | **PASS** | violations=[] |
| structure_and_pae_present_for_submitted | **PASS** | violations=[] |
| parent_baseline_scored | **PASS** | parent ipsae_min=0.6973 over 35 seed(s) |
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

- repository commit: `e194529171f8698d1e8cf3916b80859e25987b22` (working tree dirty)
- parent SHA-256: `0b9248c76a2b399791c47dbfa0d252b18284265f1dbca9ae8e66c0dd018c9f64`
- `bash scripts/run_her2_pipeline.sh` reruns the whole pipeline; stages are idempotent and resumable.
- per-stage manifests (`stage*_manifest.json`) record models, precisions, seeds, timings and peak memory.

