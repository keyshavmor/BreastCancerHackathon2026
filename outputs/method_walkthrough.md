# Method walkthrough: HER2 scFv optimisation

Generated 2026-10-31T15:11:45.538310+00:00 from this run's own artifacts.

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
| Predictions scored | 553 of 553 |
| PAE cutoff | 10.0 A |
| Distance cutoff | 15.0 A |
| IPSAE commit | `6174cf9e71cb` |

Primary metric is `ipsae_min = min(asym B->T, asym T->B)`, the conservative of the two directional values. Chain order is `T` = HER2 domain IV, `B` = scFv. `ipSAE_provenance.csv` records the script commit, both cutoffs, the metric definition, the chain mapping and the artifact paths for every design.

A prediction with a missing or unreadable PAE, a PAE/structure residue mismatch, or a failed ipSAE run is recorded with a non-`PASSED` status and **excluded**. No ipSAE value is ever estimated, interpolated or carried over from another design.

**Parent baseline** (matched settings): ipsae_min 0.6855 +/- 0.0595 over ? seed(s); epitope recovery 0.9699.

**Epitope recovery** is reported alongside ipSAE: the fraction of experimentally observed 1N8Z epitope residues still contacted in the predicted complex. ipSAE cannot distinguish a correct interface from a confident but misplaced one, so a model recovering less than 30% of the known epitope is rejected regardless of its ipSAE.

## 6b. Do the sequence scores predict the structure? (measured each run)

Spearman rank correlation between each sequence-stage predictor and each structural outcome, over n=248 ipSAE-complete designs.

| Predictor | ipsae_min | epitope_recovery | iptm |
| --- | ---: | ---: | ---: |
| `ablang2_contextual` | +0.103 | -0.103 | +0.076 |
| `esm2_contextual` | -0.218 | -0.057 | -0.217 |
| `ablang2_additive_mean` | -0.300 | -0.355 | -0.330 |
| `esm2_additive_mean` | -0.320 | -0.233 | -0.348 |
| `sequence_consensus_score` | +0.019 | +0.152 | +0.000 |
| `mutation_count` | +0.048 | +0.229 | +0.038 |

**Interpretation.** Negative rho means a HIGHER sequence-plausibility score goes with a WORSE modelled interface. Trastuzumab's CDRs are affinity-matured, so an antibody language model tends to propose reverting them toward germline consensus - precisely the residues contacting HER2. The mutation_count effect is partly confounded by MSA reuse.

This is the single most consequential empirical result of the run: it means selecting candidates by maximising sequence plausibility optimises a proxy that points **away** from interface quality. Later rounds therefore use sequence consensus as a floor (reject the implausible tail) rather than as a maximand, and stratify the structural budget by mutation count and branch instead (`requeue_structure_informed.py`).

### By mutation count

| Mutations | n | ipSAE_min | ipTM | Epitope recovery |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 120 | 0.5731 +/- 0.148 | 0.842 | 0.874 |
| 6 | 32 | 0.5614 +/- 0.206 | 0.821 | 0.897 |
| 7 | 31 | 0.6427 +/- 0.073 | 0.876 | 0.945 |
| 8 | 65 | 0.5685 +/- 0.131 | 0.844 | 0.914 |
| *parent* | - | *0.6855* | - | *0.970* |

### How much of the ipSAE ranking is real?

A variance decomposition over the designs that were run under multiple seeds. This is the number that governs every other claim in this document.

| Quantity | Value |
| --- | ---: |
| Designs with replicates | 164 |
| Mean seeds per design | 2.84 |
| sd within design (seed noise) | 0.1109 |
| sd between designs (observed) | 0.1466 |
| sd between designs (true, est.) | 0.1310 |
| **Reliability of a single seed** | **0.583** |
| Reliability of the current mean | 0.799 |
| Seeds needed for reliability 0.8 | 3 |
| Seeds needed for reliability 0.9 | 7 |

Reliability is the fraction of ranking variance that is real signal rather than seed noise. A value near 0.5 means a single-seed ranking is close to a coin flip between designs of similar quality, so **a single-seed ipSAE table must not be read as an ordering of design quality.**

Because the measurements are noisy, the correlations in the table above are *attenuated* toward zero. Dividing by sqrt(reliability) (x1.31) estimates the underlying relationships with ipSAE:

- `ablang2_contextual`: 0.1353
- `esm2_contextual`: -0.2855
- `ablang2_additive_mean`: -0.3929
- `esm2_additive_mean`: -0.4194
- `sequence_consensus_score`: 0.0248
- `mutation_count`: 0.0622

So the true effects are **stronger** than measured, not weaker - including the negative ones.

### Replicated designs tested against the parent

Parent baseline 0.6855 +/- 0.0595 over 7 seeds. Welch-style comparison, significance threshold |t| > 2.

**Above parent: 7 | below: 46 | indistinguishable: 110** (uncorrected, |t| > 2)

**Multiple-comparison correction.** 163 designs were tested, so at an uncorrected alpha of 0.05 roughly **8.2** of them would clear |t| > 2 by chance alone. Applying Benjamini-Hochberg FDR at q<0.05 over all tested designs, the number of designs significantly above the parent is **0**. An uncorrected count of 7 is therefore not evidence of improvement, and the table below reports q-values so this cannot be misread.

| Design | seeds | ipSAE mean | sd | delta | t | q (BH) | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `HER2_17641` | 3 | 0.7595 | 0.0294 | +0.0740 | +2.63 | 0.156 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17118` | 4 | 0.7513 | 0.0354 | +0.0657 | +2.30 | 0.199 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17465` | 4 | 0.7496 | 0.0383 | +0.0641 | +2.17 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14514` | 4 | 0.7486 | 0.0128 | +0.0631 | +2.70 | 0.153 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13625` | 4 | 0.7451 | 0.0124 | +0.0596 | +2.56 | 0.156 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2696` | 3 | 0.7448 | 0.0156 | +0.0593 | +2.45 | 0.184 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1238` | 4 | 0.7417 | 0.0215 | +0.0562 | +2.26 | 0.200 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23723` | 4 | 0.7349 | 0.0467 | +0.0494 | +1.52 | 0.353 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_10177` | 2 | 0.7330 | 0.0324 | +0.0474 | +1.48 | 0.367 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0955` | 3 | 0.7323 | 0.0227 | +0.0467 | +1.80 | 0.307 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1488` | 2 | 0.7315 | 0.0262 | +0.0460 | +1.58 | 0.353 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21202` | 4 | 0.7306 | 0.0099 | +0.0451 | +1.96 | 0.246 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_2720` | 3 | 0.7292 | 0.0391 | +0.0437 | +1.37 | 0.385 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0949` | 3 | 0.7282 | 0.0135 | +0.0426 | +1.79 | 0.307 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_27115` | 2 | 0.7275 | 0.0354 | +0.0420 | +1.25 | 0.423 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_13932` | 3 | 0.7273 | 0.0739 | +0.0418 | +0.87 | 0.571 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8022` | 4 | 0.7267 | 0.0267 | +0.0412 | +1.57 | 0.351 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18461` | 3 | 0.7262 | 0.0084 | +0.0407 | +1.77 | 0.312 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_5693` | 5 | 0.7258 | 0.0226 | +0.0403 | +1.63 | 0.336 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14939` | 3 | 0.7249 | 0.0086 | +0.0394 | +1.71 | 0.320 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14954` | 4 | 0.7226 | 0.0346 | +0.0370 | +1.31 | 0.394 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17485` | 3 | 0.7217 | 0.0658 | +0.0362 | +0.82 | 0.587 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_18216` | 3 | 0.7209 | 0.0465 | +0.0354 | +1.01 | 0.516 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1375` | 2 | 0.7192 | 0.0201 | +0.0336 | +1.27 | 0.423 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0302` | 2 | 0.7174 | 0.0045 | +0.0319 | +1.40 | 0.384 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_28172` | 3 | 0.7162 | 0.0428 | +0.0307 | +0.92 | 0.555 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_34846` | 3 | 0.7161 | 0.0214 | +0.0306 | +1.19 | 0.442 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1330` | 2 | 0.7153 | 0.0103 | +0.0298 | +1.26 | 0.423 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2110` | 2 | 0.7138 | 0.0045 | +0.0283 | +1.25 | 0.423 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_9557` | 5 | 0.7133 | 0.0414 | +0.0278 | +0.96 | 0.523 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11519` | 4 | 0.7131 | 0.0346 | +0.0275 | +0.97 | 0.523 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15988` | 3 | 0.7129 | 0.0226 | +0.0274 | +1.05 | 0.499 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1251` | 2 | 0.7107 | 0.0313 | +0.0252 | +0.80 | 0.596 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1612` | 2 | 0.7103 | 0.0266 | +0.0247 | +0.84 | 0.582 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8386` | 4 | 0.7054 | 0.0372 | +0.0198 | +0.68 | 0.649 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_19503` | 3 | 0.7011 | 0.0336 | +0.0156 | +0.53 | 0.737 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3536` | 3 | 0.7012 | 0.0599 | +0.0156 | +0.38 | 0.825 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_15832` | 2 | 0.6975 | 0.0366 | +0.0119 | +0.35 | 0.839 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0719` | 3 | 0.6971 | 0.0189 | +0.0115 | +0.46 | 0.783 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_13086` | 4 | 0.6961 | 0.0468 | +0.0106 | +0.33 | 0.839 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21342` | 3 | 0.6950 | 0.0872 | +0.0095 | +0.17 | 0.926 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0930` | 3 | 0.6948 | 0.0537 | +0.0093 | +0.24 | 0.899 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1130` | 2 | 0.6936 | 0.0727 | +0.0080 | +0.14 | 0.945 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_19389` | 2 | 0.6933 | 0.0046 | +0.0078 | +0.34 | 0.839 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0538` | 2 | 0.6911 | 0.0123 | +0.0056 | +0.23 | 0.902 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8798` | 3 | 0.6887 | 0.0564 | +0.0031 | +0.08 | 0.974 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_7827` | 3 | 0.6882 | 0.0817 | +0.0027 | +0.05 | 0.981 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_10318` | 3 | 0.6872 | 0.0687 | +0.0017 | +0.04 | 0.981 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0070` | 5 | 0.6856 | 0.0242 | +0.0001 | +0.00 | 1.000 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_10808` | 4 | 0.6850 | 0.0391 | -0.0005 | -0.02 | 0.991 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_18668` | 2 | 0.6847 | 0.0047 | -0.0008 | -0.04 | 0.981 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_16732` | 2 | 0.6841 | 0.0155 | -0.0014 | -0.06 | 0.981 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_19004` | 3 | 0.6828 | 0.0501 | -0.0028 | -0.08 | 0.974 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11449` | 3 | 0.6807 | 0.0241 | -0.0048 | -0.18 | 0.924 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2747` | 2 | 0.6793 | 0.0035 | -0.0063 | -0.28 | 0.873 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1025` | 3 | 0.6791 | 0.0398 | -0.0064 | -0.20 | 0.920 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3091` | 3 | 0.6780 | 0.0893 | -0.0075 | -0.13 | 0.946 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11456` | 3 | 0.6777 | 0.0602 | -0.0079 | -0.19 | 0.922 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_3098` | 3 | 0.6764 | 0.0184 | -0.0091 | -0.37 | 0.828 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0104` | 2 | 0.6754 | 0.0075 | -0.0101 | -0.44 | 0.789 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1834` | 2 | 0.6719 | 0.0494 | -0.0137 | -0.33 | 0.839 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17233` | 3 | 0.6693 | 0.0312 | -0.0162 | -0.56 | 0.729 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_21408` | 3 | 0.6686 | 0.0170 | -0.0170 | -0.69 | 0.649 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15708` | 4 | 0.6682 | 0.0671 | -0.0173 | -0.43 | 0.789 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_24204` | 3 | 0.6656 | 0.0070 | -0.0199 | -0.87 | 0.571 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_7401` | 3 | 0.6648 | 0.0380 | -0.0208 | -0.66 | 0.657 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_9279` | 2 | 0.6637 | 0.0112 | -0.0219 | -0.92 | 0.555 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_26656` | 4 | 0.6632 | 0.0809 | -0.0224 | -0.48 | 0.770 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_15056` | 3 | 0.6596 | 0.0400 | -0.0259 | -0.80 | 0.596 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0412` | 2 | 0.6578 | 0.0332 | -0.0278 | -0.85 | 0.582 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_16400` | 2 | 0.6563 | 0.0146 | -0.0293 | -1.18 | 0.446 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0417` | 3 | 0.6544 | 0.0626 | -0.0312 | -0.73 | 0.634 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_23444` | 3 | 0.6534 | 0.0029 | -0.0321 | -1.43 | 0.370 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_3742` | 2 | 0.6526 | 0.0779 | -0.0330 | -0.55 | 0.729 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_20989` | 3 | 0.6495 | 0.1365 | -0.0361 | -0.44 | 0.789 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_8533` | 4 | 0.6488 | 0.0759 | -0.0367 | -0.83 | 0.582 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0077` | 5 | 0.6484 | 0.0818 | -0.0372 | -0.87 | 0.571 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_17437` | 3 | 0.6442 | 0.0056 | -0.0414 | -1.82 | 0.307 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1971` | 2 | 0.6412 | 0.0465 | -0.0443 | -1.11 | 0.476 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1038` | 3 | 0.6374 | 0.0414 | -0.0481 | -1.46 | 0.367 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_11678` | 4 | 0.6370 | 0.1380 | -0.0486 | -0.67 | 0.652 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1936` | 3 | 0.6363 | 0.0114 | -0.0493 | -2.10 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0478` | 2 | 0.6350 | 0.0225 | -0.0505 | -1.83 | 0.307 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1456` | 2 | 0.6342 | 0.0422 | -0.0514 | -1.38 | 0.385 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1401` | 4 | 0.6332 | 0.0217 | -0.0523 | -2.10 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1116` | 2 | 0.6323 | 0.0612 | -0.0532 | -1.09 | 0.484 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_24532` | 3 | 0.6312 | 0.0832 | -0.0543 | -1.02 | 0.514 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_5265` | 3 | 0.6294 | 0.0139 | -0.0561 | -2.35 | 0.199 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0290` | 2 | 0.6266 | 0.0623 | -0.0589 | -1.19 | 0.445 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0096` | 3 | 0.6251 | 0.1857 | -0.0604 | -0.55 | 0.729 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_15746` | 3 | 0.6241 | 0.0836 | -0.0614 | -1.15 | 0.453 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_14799` | 3 | 0.6216 | 0.0348 | -0.0639 | -2.12 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0309` | 2 | 0.6207 | 0.0278 | -0.0649 | -2.17 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1050` | 2 | 0.6206 | 0.0005 | -0.0649 | -2.89 | 0.153 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1204` | 3 | 0.6195 | 0.0668 | -0.0660 | -1.48 | 0.367 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23198` | 4 | 0.6190 | 0.1853 | -0.0665 | -0.70 | 0.644 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1306` | 2 | 0.6166 | 0.1273 | -0.0689 | -0.74 | 0.634 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_12122` | 3 | 0.6142 | 0.0365 | -0.0713 | -2.32 | 0.199 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_19316` | 3 | 0.6138 | 0.0714 | -0.0717 | -1.53 | 0.353 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0888` | 3 | 0.6126 | 0.1218 | -0.0729 | -0.99 | 0.520 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_23267` | 3 | 0.6104 | 0.0766 | -0.0751 | -1.51 | 0.359 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0054` | 3 | 0.6053 | 0.0527 | -0.0803 | -2.12 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_6691` | 3 | 0.6029 | 0.1383 | -0.0827 | -1.00 | 0.518 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_14367` | 2 | 0.6006 | 0.0739 | -0.0849 | -1.49 | 0.367 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1769` | 2 | 0.5972 | 0.0961 | -0.0883 | -1.23 | 0.430 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1582` | 3 | 0.5937 | 0.1084 | -0.0919 | -1.38 | 0.384 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_9348` | 2 | 0.5934 | 0.1818 | -0.0921 | -0.71 | 0.644 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_4384` | 3 | 0.5915 | 0.0635 | -0.0940 | -2.19 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_32745` | 3 | 0.5859 | 0.0693 | -0.0997 | -2.17 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0881` | 3 | 0.5720 | 0.0412 | -0.1135 | -3.47 | 0.078 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1058` | 3 | 0.5619 | 0.1172 | -0.1237 | -1.73 | 0.320 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2120` | 2 | 0.5601 | 0.0363 | -0.1254 | -3.68 | 0.078 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0737` | 3 | 0.5596 | 0.0775 | -0.1259 | -2.51 | 0.180 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_4977` | 4 | 0.5581 | 0.1798 | -0.1274 | -1.37 | 0.384 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_4786` | 3 | 0.5579 | 0.0594 | -0.1276 | -3.11 | 0.118 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1703` | 2 | 0.5575 | 0.0858 | -0.1280 | -1.98 | 0.261 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0100` | 2 | 0.5569 | 0.1215 | -0.1286 | -1.45 | 0.370 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0849` | 2 | 0.5487 | 0.0750 | -0.1369 | -2.38 | 0.199 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_24898` | 3 | 0.5473 | 0.1752 | -0.1383 | -1.33 | 0.394 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1114` | 2 | 0.5380 | 0.1147 | -0.1476 | -1.75 | 0.320 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0692` | 3 | 0.5365 | 0.0637 | -0.1491 | -3.46 | 0.078 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2228` | 2 | 0.5364 | 0.1813 | -0.1491 | -1.15 | 0.456 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0209` | 3 | 0.5294 | 0.0655 | -0.1561 | -3.55 | 0.078 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0021` | 3 | 0.5123 | 0.1155 | -0.1732 | -2.46 | 0.184 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1315` | 2 | 0.5115 | 0.0018 | -0.1740 | -7.73 | 0.002 | BELOW_PARENT_FDR |
| `HER2B_0261` | 3 | 0.4938 | 0.1186 | -0.1917 | -2.66 | 0.156 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0371` | 2 | 0.4873 | 0.0950 | -0.1983 | -2.80 | 0.156 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0470` | 3 | 0.4851 | 0.1141 | -0.2004 | -2.88 | 0.152 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_16818` | 3 | 0.4817 | 0.1708 | -0.2038 | -2.02 | 0.240 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1749` | 2 | 0.4806 | 0.1306 | -0.2049 | -2.16 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1801` | 2 | 0.4680 | 0.1062 | -0.2175 | -2.77 | 0.156 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1203` | 2 | 0.4601 | 0.2410 | -0.2254 | -1.31 | 0.406 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0902` | 2 | 0.4553 | 0.1082 | -0.2302 | -2.89 | 0.153 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1644` | 2 | 0.4476 | 0.2021 | -0.2379 | -1.64 | 0.351 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_6704` | 3 | 0.4469 | 0.0290 | -0.2386 | -8.51 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_31611` | 2 | 0.4446 | 0.2146 | -0.2410 | -1.57 | 0.353 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0180` | 2 | 0.4412 | 0.0614 | -0.2443 | -5.00 | 0.023 | BELOW_PARENT_FDR |
| `HER2B_1000` | 3 | 0.4394 | 0.1902 | -0.2461 | -2.20 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3843` | 3 | 0.4345 | 0.0697 | -0.2510 | -5.44 | 0.011 | BELOW_PARENT_FDR |
| `HER2B_0936` | 3 | 0.4314 | 0.1339 | -0.2541 | -3.16 | 0.115 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_10599` | 3 | 0.4314 | 0.2749 | -0.2542 | -1.59 | 0.351 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1793` | 2 | 0.4310 | 0.1266 | -0.2546 | -2.76 | 0.156 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_3990` | 3 | 0.4293 | 0.1551 | -0.2562 | -2.78 | 0.153 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_0111` | 3 | 0.4204 | 0.2881 | -0.2651 | -1.58 | 0.351 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_1036` | 3 | 0.4160 | 0.1549 | -0.2696 | -2.92 | 0.150 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_4269` | 3 | 0.4076 | 0.1933 | -0.2779 | -2.44 | 0.184 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2739` | 3 | 0.3954 | 0.3443 | -0.2901 | -1.45 | 0.368 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2319` | 2 | 0.3910 | 0.2577 | -0.2945 | -1.60 | 0.351 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_15697` | 3 | 0.3908 | 0.1411 | -0.2947 | -3.49 | 0.078 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_11515` | 2 | 0.3766 | 0.0952 | -0.3089 | -4.35 | 0.045 | BELOW_PARENT_FDR |
| `HER2_1340` | 3 | 0.3748 | 0.3265 | -0.3107 | -1.64 | 0.345 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_4716` | 3 | 0.3692 | 0.0549 | -0.3164 | -8.14 | 0.001 | BELOW_PARENT_FDR |
| `HER2B_0610` | 3 | 0.3645 | 0.3186 | -0.3210 | -1.73 | 0.320 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_2117` | 2 | 0.3511 | 0.2172 | -0.3344 | -2.15 | 0.216 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1893` | 3 | 0.3481 | 0.3704 | -0.3374 | -1.57 | 0.351 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_1903` | 2 | 0.3405 | 0.0904 | -0.3450 | -5.09 | 0.023 | BELOW_PARENT_FDR |
| `HER2B_2383` | 2 | 0.3078 | 0.0572 | -0.3777 | -8.17 | 0.002 | BELOW_PARENT_FDR |
| `HER2B_1580` | 2 | 0.2911 | 0.4117 | -0.3944 | -1.35 | 0.394 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2B_20445` | 3 | 0.2252 | 0.2117 | -0.4604 | -3.71 | 0.075 | NOT_SIGNIFICANT_AFTER_CORRECTION |
| `HER2_0888` | 3 | 0.1017 | 0.0607 | -0.5839 | -14.03 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0801` | 2 | 0.0542 | 0.0766 | -0.6313 | -10.76 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_0750` | 2 | 0.0000 | 0.0000 | -0.6855 | -30.51 | 0.000 | BELOW_PARENT_FDR |
| `HER2B_1174` | 2 | 0.0000 | 0.0000 | -0.6855 | -30.51 | 0.000 | BELOW_PARENT_FDR |

**No design is statistically distinguishable as better than the parent.** This is the honest headline result. It is also the expected one: the parent is a sub-picomolar, heavily optimised therapeutic antibody, and a pipeline reporting that most of its 5-8 substitution variants improved on it would be evidence of a broken scoring function rather than a successful campaign. Designs are submitted as compliant, structurally intact candidates with genuine ipSAE values - not as predicted improvements.

### By branch

| Branch | n | ipSAE_min | ipTM | Epitope recovery |
| --- | ---: | ---: | ---: | ---: |
| `A_h3` | 28 | 0.4813 | 0.796 | 0.863 |
| `B_interface` | 126 | 0.5734 | 0.841 | 0.866 |
| `C_mixed` | 67 | 0.6047 | 0.855 | 0.936 |
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

**Seed-noise gate.** Pooled ipSAE standard deviation across replicated candidates: **0.0791**. A design whose advantage over the parent is smaller than this is labelled `WITHIN_SEED_NOISE` rather than presented as an improvement. Designs exceeding the parent beyond that noise: **0** of 248.

**Sensitivity analysis.** Because the weights are a stated hypothesis and not a fitted model, the whole set is re-ranked under three alternative weightings (ipSAE-heavy, sequence-heavy, equal). Each design carries `max_rank_shift_under_reweighting`, so a nominee whose position depends on a single metric is visible as such.

## 8. Lab nominations (top 15)

| Rank | ID | Branch | Muts | ipSAE_min | Δ vs parent | Interpretation | Epitope rec. | ipTM | Rank shift |
| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 1 | `HER2_11519` | C_mixed | 5 | 0.7131 | 0.0276 | WITHIN_SEED_NOISE | 1.000 | 0.899 | 2 |
| 2 | `HER2_8022` | B_interface | 8 | 0.7267 | 0.0412 | WITHIN_SEED_NOISE | 0.974 | 0.903 | 4 |
| 3 | `HER2_1238` | B_interface | 5 | 0.7417 | 0.0562 | WITHIN_SEED_NOISE | 0.921 | 0.908 | 2 |
| 4 | `HER2_5693` | D_framework | 6 | 0.7258 | 0.0403 | WITHIN_SEED_NOISE | 0.979 | 0.900 | 3 |
| 5 | `HER2_13625` | C_mixed | 8 | 0.7451 | 0.0596 | WITHIN_SEED_NOISE | 0.947 | 0.911 | 2 |
| 7 | `HER2_9557` | A_h3 | 8 | 0.7133 | 0.0278 | WITHIN_SEED_NOISE | 0.968 | 0.904 | 7 |
| 9 | `HER2_14954` | D_framework | 6 | 0.7226 | 0.0371 | WITHIN_SEED_NOISE | 0.974 | 0.904 | 18 |
| 13 | `HER2_14514` | C_mixed | 6 | 0.7486 | 0.0631 | WITHIN_SEED_NOISE | 0.961 | 0.912 | 45 |
| 21 | `HER2_7401` | B_interface | 6 | 0.6648 | -0.0207 | WITHIN_SEED_NOISE | 0.965 | 0.882 | 28 |
| 39 | `HER2_11456` | B_interface | 7 | 0.6777 | -0.0078 | WITHIN_SEED_NOISE | 0.947 | 0.880 | 34 |
| 72 | `HER2_2788` | A_h3 | 8 | 0.6099 | -0.0756 | SINGLE_SEED_UNRELIABLE | 0.947 | 0.876 | 47 |
| 84 | `HER2_8404` | A_h3 | 7 | 0.6442 | -0.0413 | SINGLE_SEED_UNRELIABLE | 0.947 | 0.866 | 29 |
| 87 | `HER2_9311` | A_h3 | 8 | 0.6299 | -0.0556 | SINGLE_SEED_UNRELIABLE | 0.947 | 0.860 | 42 |
| 129 | `HER2_1582` | A_h3 | 8 | 0.5937 | -0.0918 | BELOW_PARENT | 0.842 | 0.862 | 61 |
| 167 | `HER2_8252` | A_h3 | 8 | 0.5933 | -0.0922 | SINGLE_SEED_UNRELIABLE | 0.789 | 0.854 | 57 |

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
| parent_baseline_scored | **PASS** | parent ipsae_min=0.6855 over 7 seed(s) |
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

- repository commit: `7e45390fc919646bd0e1fb6042ea93b76a8aa800` (working tree dirty)
- parent SHA-256: `0b9248c76a2b399791c47dbfa0d252b18284265f1dbca9ae8e66c0dd018c9f64`
- `bash scripts/run_her2_pipeline.sh` reruns the whole pipeline; stages are idempotent and resumable.
- per-stage manifests (`stage*_manifest.json`) record models, precisions, seeds, timings and peak memory.

