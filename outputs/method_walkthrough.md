# Method walkthrough: HER2 scFv optimisation

Generated 2026-10-31T14:28:18.128010+00:00 from this run's own artifacts.

> **Claim boundary.** Every value below is a computational ranking signal for experimental triage. No affinity is measured or predicted. ipSAE is not K_D, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. The parent is already a sub-picomolar binder, so the prior that any 5-8 substitution variant improves on it is low by construction.

## What was produced

| Deliverable | Count |
| --- | --- |
| Valid internal proposals (`internal_50_candidates.*`) | 50 |
| Designs with a real, externally computed ipSAE (`submission_scored.*`) | 149 |
| Ranked lab nominations (`top_15_scored.*`) | 15 |
| Designs excluded, with recorded reasons | 60 |
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
| Predictions scored | 368 of 368 |
| PAE cutoff | 10.0 A |
| Distance cutoff | 15.0 A |
| IPSAE commit | `6174cf9e71cb` |

Primary metric is `ipsae_min = min(asym B->T, asym T->B)`, the conservative of the two directional values. Chain order is `T` = HER2 domain IV, `B` = scFv. `ipSAE_provenance.csv` records the script commit, both cutoffs, the metric definition, the chain mapping and the artifact paths for every design.

A prediction with a missing or unreadable PAE, a PAE/structure residue mismatch, or a failed ipSAE run is recorded with a non-`PASSED` status and **excluded**. No ipSAE value is ever estimated, interpolated or carried over from another design.

**Parent baseline** (matched settings): ipsae_min 0.6864 +/- 0.0574 over ? seed(s); epitope recovery 0.9684.

**Epitope recovery** is reported alongside ipSAE: the fraction of experimentally observed 1N8Z epitope residues still contacted in the predicted complex. ipSAE cannot distinguish a correct interface from a confident but misplaced one, so a model recovering less than 30% of the known epitope is rejected regardless of its ipSAE.

## 6b. Do the sequence scores predict the structure? (measured each run)

Spearman rank correlation between each sequence-stage predictor and each structural outcome, over n=149 ipSAE-complete designs.

| Predictor | ipsae_min | epitope_recovery | iptm |
| --- | ---: | ---: | ---: |
| `ablang2_contextual` | +0.103 | -0.103 | +0.076 |
| `esm2_contextual` | -0.218 | -0.057 | -0.217 |
| `ablang2_additive_mean` | -0.300 | -0.355 | -0.330 |
| `esm2_additive_mean` | -0.320 | -0.233 | -0.348 |
| `sequence_consensus_score` | -0.254 | -0.261 | -0.283 |
| `mutation_count` | -0.231 | -0.084 | -0.240 |

**Interpretation.** Negative rho means a HIGHER sequence-plausibility score goes with a WORSE modelled interface. Trastuzumab's CDRs are affinity-matured, so an antibody language model tends to propose reverting them toward germline consensus - precisely the residues contacting HER2. The mutation_count effect is partly confounded by MSA reuse.

This is the single most consequential empirical result of the run: it means selecting candidates by maximising sequence plausibility optimises a proxy that points **away** from interface quality. Later rounds therefore use sequence consensus as a floor (reject the implausible tail) rather than as a maximand, and stratify the structural budget by mutation count and branch instead (`requeue_structure_informed.py`).

### By mutation count

| Mutations | n | ipSAE_min | ipTM | Epitope recovery |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 21 | 0.6467 +/- 0.079 | 0.878 | 0.932 |
| 6 | 32 | 0.5614 +/- 0.206 | 0.821 | 0.897 |
| 7 | 31 | 0.6427 +/- 0.073 | 0.876 | 0.945 |
| 8 | 65 | 0.5685 +/- 0.131 | 0.844 | 0.914 |
| *parent* | - | *0.6864* | - | *0.968* |

### How much of the ipSAE ranking is real?

A variance decomposition over the designs that were run under multiple seeds. This is the number that governs every other claim in this document.

| Quantity | Value |
| --- | ---: |
| Designs with replicates | 64 |
| Mean seeds per design | 3.47 |
| sd within design (seed noise) | 0.0797 |
| sd between designs (observed) | 0.1102 |
| sd between designs (true, est.) | 0.1015 |
| **Reliability of a single seed** | **0.619** |
| Reliability of the current mean | 0.849 |
| Seeds needed for reliability 0.8 | 3 |
| Seeds needed for reliability 0.9 | 6 |

Reliability is the fraction of ranking variance that is real signal rather than seed noise. A value near 0.5 means a single-seed ranking is close to a coin flip between designs of similar quality, so **a single-seed ipSAE table must not be read as an ordering of design quality.**

Because the measurements are noisy, the correlations in the table above are *attenuated* toward zero. Dividing by sqrt(reliability) (x1.27) estimates the underlying relationships with ipSAE:

- `ablang2_contextual`: 0.1313
- `esm2_contextual`: -0.2770
- `ablang2_additive_mean`: -0.3812
- `esm2_additive_mean`: -0.4069
- `sequence_consensus_score`: -0.3225
- `mutation_count`: -0.2939

So the true effects are **stronger** than measured, not weaker - including the negative ones.

### Replicated designs tested against the parent

Parent baseline 0.6864 +/- 0.0574 over 5 seeds. Welch-style comparison, significance threshold |t| > 2.

**Above parent: 4 | below: 8 | indistinguishable: 51** (uncorrected, |t| > 2)

**Multiple-comparison correction.** 63 designs were tested, so at an uncorrected alpha of 0.05 roughly **3.2** of them would clear |t| > 2 by chance alone. Applying Benjamini-Hochberg FDR at q<0.05 over all tested designs, the number of designs significantly above the parent is **0**. An uncorrected count of 4 is therefore not evidence of improvement, and the table below reports q-values so this cannot be misread.

| Design | seeds | ipSAE mean | sd | delta | t | q (BH) | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `HER2_17641` | 3 | 0.7595 | 0.0294 | +0.0731 | +2.38 | 0.383 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17118` | 4 | 0.7513 | 0.0354 | +0.0649 | +2.08 | 0.385 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17465` | 4 | 0.7496 | 0.0383 | +0.0632 | +1.97 | 0.385 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14514` | 4 | 0.7486 | 0.0128 | +0.0623 | +2.35 | 0.383 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13625` | 4 | 0.7451 | 0.0124 | +0.0587 | +2.22 | 0.385 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1238` | 4 | 0.7417 | 0.0215 | +0.0553 | +1.99 | 0.385 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23723` | 4 | 0.7349 | 0.0467 | +0.0485 | +1.40 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21202` | 4 | 0.7306 | 0.0099 | +0.0443 | +1.69 | 0.472 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_2720` | 3 | 0.7292 | 0.0391 | +0.0428 | +1.25 | 0.541 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8022` | 4 | 0.7267 | 0.0267 | +0.0403 | +1.39 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18461` | 3 | 0.7262 | 0.0084 | +0.0399 | +1.53 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_5693` | 5 | 0.7258 | 0.0226 | +0.0394 | +1.43 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14939` | 3 | 0.7249 | 0.0086 | +0.0385 | +1.47 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14954` | 4 | 0.7226 | 0.0346 | +0.0362 | +1.17 | 0.570 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17485` | 3 | 0.7217 | 0.0658 | +0.0354 | +0.77 | 0.706 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18216` | 3 | 0.7209 | 0.0465 | +0.0345 | +0.93 | 0.692 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_28172` | 3 | 0.7162 | 0.0428 | +0.0299 | +0.84 | 0.692 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_34846` | 3 | 0.7161 | 0.0214 | +0.0298 | +1.05 | 0.658 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_9557` | 5 | 0.7133 | 0.0414 | +0.0270 | +0.85 | 0.692 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11519` | 4 | 0.7131 | 0.0346 | +0.0267 | +0.86 | 0.692 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15988` | 3 | 0.7129 | 0.0226 | +0.0266 | +0.92 | 0.692 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8386` | 4 | 0.7054 | 0.0372 | +0.0190 | +0.60 | 0.761 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_19503` | 3 | 0.7011 | 0.0336 | +0.0148 | +0.46 | 0.824 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3536` | 3 | 0.7012 | 0.0599 | +0.0148 | +0.34 | 0.886 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13086` | 4 | 0.6961 | 0.0468 | +0.0098 | +0.28 | 0.919 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21342` | 3 | 0.6950 | 0.0872 | +0.0087 | +0.15 | 0.970 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8798` | 3 | 0.6887 | 0.0564 | +0.0023 | +0.06 | 0.977 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_7827` | 3 | 0.6882 | 0.0817 | +0.0019 | +0.03 | 0.977 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0070` | 5 | 0.6856 | 0.0242 | -0.0007 | -0.03 | 0.977 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_10808` | 4 | 0.6850 | 0.0391 | -0.0013 | -0.04 | 0.977 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_19004` | 3 | 0.6828 | 0.0501 | -0.0036 | -0.09 | 0.977 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11449` | 3 | 0.6807 | 0.0241 | -0.0057 | -0.19 | 0.963 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3091` | 3 | 0.6780 | 0.0893 | -0.0083 | -0.14 | 0.970 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11456` | 3 | 0.6777 | 0.0602 | -0.0087 | -0.20 | 0.963 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17233` | 3 | 0.6693 | 0.0312 | -0.0170 | -0.54 | 0.799 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21408` | 3 | 0.6686 | 0.0170 | -0.0178 | -0.65 | 0.748 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15708` | 4 | 0.6682 | 0.0671 | -0.0181 | -0.43 | 0.824 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_7401` | 3 | 0.6648 | 0.0380 | -0.0216 | -0.64 | 0.748 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_26656` | 4 | 0.6632 | 0.0809 | -0.0232 | -0.48 | 0.824 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15056` | 3 | 0.6596 | 0.0400 | -0.0267 | -0.77 | 0.706 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_20989` | 3 | 0.6495 | 0.1365 | -0.0369 | -0.45 | 0.824 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8533` | 4 | 0.6488 | 0.0759 | -0.0375 | -0.82 | 0.692 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0077` | 5 | 0.6484 | 0.0818 | -0.0380 | -0.85 | 0.692 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17437` | 3 | 0.6442 | 0.0056 | -0.0422 | -1.63 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11678` | 4 | 0.6370 | 0.1380 | -0.0494 | -0.67 | 0.748 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1936` | 3 | 0.6363 | 0.0114 | -0.0501 | -1.89 | 0.399 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1401` | 4 | 0.6332 | 0.0217 | -0.0532 | -1.91 | 0.385 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_24532` | 3 | 0.6312 | 0.0832 | -0.0551 | -1.01 | 0.671 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_5265` | 3 | 0.6294 | 0.0139 | -0.0570 | -2.12 | 0.385 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14799` | 3 | 0.6216 | 0.0348 | -0.0648 | -1.99 | 0.385 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23198` | 4 | 0.6190 | 0.1853 | -0.0673 | -0.70 | 0.742 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_19316` | 3 | 0.6138 | 0.0714 | -0.0726 | -1.49 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23267` | 3 | 0.6104 | 0.0766 | -0.0760 | -1.49 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1582` | 3 | 0.5937 | 0.1084 | -0.0927 | -1.37 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0737` | 3 | 0.5596 | 0.0775 | -0.1267 | -2.46 | 0.383 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_4977` | 4 | 0.5581 | 0.1798 | -0.1282 | -1.37 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_4786` | 3 | 0.5579 | 0.0594 | -0.1285 | -3.00 | 0.340 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_6704` | 3 | 0.4469 | 0.0290 | -0.2395 | -7.81 | 0.007 | BELOW_PARENT_FDR |
| `HER2_3843` | 3 | 0.4345 | 0.0697 | -0.2518 | -5.28 | 0.039 | BELOW_PARENT_FDR |
| `HER2_3990` | 3 | 0.4293 | 0.1551 | -0.2570 | -2.76 | 0.345 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1036` | 3 | 0.4160 | 0.1549 | -0.2704 | -2.91 | 0.340 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1340` | 3 | 0.3748 | 0.3265 | -0.3116 | -1.64 | 0.477 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0888` | 3 | 0.1017 | 0.0607 | -0.5847 | -13.46 | 0.001 | BELOW_PARENT_FDR |

**No design is statistically distinguishable as better than the parent.** This is the honest headline result. It is also the expected one: the parent is a sub-picomolar, heavily optimised therapeutic antibody, and a pipeline reporting that most of its 5-8 substitution variants improved on it would be evidence of a broken scoring function rather than a successful campaign. Designs are submitted as compliant, structurally intact candidates with genuine ipSAE values - not as predicted improvements.

### By branch

| Branch | n | ipSAE_min | ipTM | Epitope recovery |
| --- | ---: | ---: | ---: | ---: |
| `A_h3` | 28 | 0.4813 | 0.796 | 0.863 |
| `B_interface` | 33 | 0.6259 | 0.865 | 0.898 |
| `C_mixed` | 61 | 0.6053 | 0.855 | 0.934 |
| `D_framework` | 27 | 0.6434 | 0.879 | 0.971 |

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

**Seed-noise gate.** Pooled ipSAE standard deviation across replicated candidates: **0.0594**. A design whose advantage over the parent is smaller than this is labelled `WITHIN_SEED_NOISE` rather than presented as an improvement. Designs exceeding the parent beyond that noise: **4** of 149.

**Sensitivity analysis.** Because the weights are a stated hypothesis and not a fitted model, the whole set is re-ranked under three alternative weightings (ipSAE-heavy, sequence-heavy, equal). Each design carries `max_rank_shift_under_reweighting`, so a nominee whose position depends on a single metric is visible as such.

## 8. Lab nominations (top 15)

| Rank | ID | Branch | Muts | ipSAE_min | Δ vs parent | Interpretation | Epitope rec. | ipTM | Rank shift |
| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 1 | `HER2_11519` | C_mixed | 5 | 0.7131 | 0.0267 | WITHIN_SEED_NOISE | 1.000 | 0.899 | 1 |
| 2 | `HER2_1238` | B_interface | 5 | 0.7417 | 0.0553 | WITHIN_SEED_NOISE | 0.921 | 0.908 | 1 |
| 3 | `HER2_8022` | B_interface | 8 | 0.7267 | 0.0403 | WITHIN_SEED_NOISE | 0.974 | 0.903 | 2 |
| 4 | `HER2_5693` | D_framework | 6 | 0.7258 | 0.0394 | WITHIN_SEED_NOISE | 0.979 | 0.900 | 2 |
| 5 | `HER2_13625` | C_mixed | 8 | 0.7451 | 0.0587 | WITHIN_SEED_NOISE | 0.947 | 0.911 | 5 |
| 8 | `HER2_9557` | A_h3 | 8 | 0.7133 | 0.0269 | WITHIN_SEED_NOISE | 0.968 | 0.904 | 6 |
| 13 | `HER2_7401` | B_interface | 6 | 0.6648 | -0.0216 | WITHIN_SEED_NOISE | 0.965 | 0.882 | 21 |
| 14 | `HER2_14954` | D_framework | 6 | 0.7226 | 0.0362 | WITHIN_SEED_NOISE | 0.974 | 0.904 | 41 |
| 24 | `HER2_3536` | C_mixed | 5 | 0.7012 | 0.0148 | WITHIN_SEED_NOISE | 0.860 | 0.890 | 39 |
| 25 | `HER2_11456` | B_interface | 7 | 0.6777 | -0.0087 | WITHIN_SEED_NOISE | 0.947 | 0.880 | 18 |
| 55 | `HER2_2788` | A_h3 | 8 | 0.6099 | -0.0765 | SINGLE_SEED_UNRELIABLE | 0.947 | 0.876 | 27 |
| 73 | `HER2_9311` | A_h3 | 8 | 0.6299 | -0.0565 | SINGLE_SEED_UNRELIABLE | 0.947 | 0.860 | 26 |
| 75 | `HER2_8404` | A_h3 | 7 | 0.6442 | -0.0422 | SINGLE_SEED_UNRELIABLE | 0.947 | 0.866 | 18 |
| 90 | `HER2_1582` | A_h3 | 8 | 0.5937 | -0.0927 | BELOW_PARENT | 0.842 | 0.862 | 56 |
| 120 | `HER2_8252` | A_h3 | 8 | 0.5933 | -0.0931 | SINGLE_SEED_UNRELIABLE | 0.789 | 0.854 | 37 |

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
| submitted_sequences_unique | **PASS** | 149 rows, 149 unique |
| mutation_signatures_unique | **PASS** | 149 unique signatures |
| reconstructible_from_mutation_list | **PASS** | violations=[] |
| every_submitted_has_finite_ipsae | **PASS** | violations=[] |
| structure_and_pae_present_for_submitted | **PASS** | violations=[] |
| parent_baseline_scored | **PASS** | parent ipsae_min=0.6864 over 5 seed(s) |
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

- repository commit: `83d7bf64db2d4ec4ae5586f1d9639e62160b9466` (working tree dirty)
- parent SHA-256: `0b9248c76a2b399791c47dbfa0d252b18284265f1dbca9ae8e66c0dd018c9f64`
- `bash scripts/run_her2_pipeline.sh` reruns the whole pipeline; stages are idempotent and resumable.
- per-stage manifests (`stage*_manifest.json`) record models, precisions, seeds, timings and peak memory.

