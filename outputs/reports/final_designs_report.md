# Final designs report - HER2 scFv optimisation

Generated 2026-10-31T15:08:28+00:00.

> **Claim boundary.** Every value here is a computational ranking signal for experimental triage. ipSAE is not a binding affinity, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. No K_D is predicted.

## Headline

| Quantity | Value |
| --- | ---: |
| Designs with a genuine external ipSAE | **249** |
| Structures behind them | 1583 |
| Local / Modal structures | 519 / 1064 |
| Ranked submission set | 50 |
| Lab nominations | 15 |
| Parent replicates | 14 |
| Compliance audit | **PASS** (0 failed) |

Parent baseline: **0.7127** +/- 0.0445 over 14 seeds.

### How each design compares with the parent

| Verdict | Designs |
| --- | ---: |
| ABOVE_PARENT | 0 |
| BELOW_PARENT | 124 |
| WITHIN_SEED_NOISE | 125 |
| SINGLE_SEED_UNRELIABLE | 0 |
| NO_PARENT_BASELINE | 0 |

`SINGLE_SEED_UNRELIABLE` means the design has one replicate, which at the measured reliability cannot support a directional claim either way.

## Top 50 ranked designs

Ranked by the multi-objective score (sequence consensus, ipSAE, epitope recovery, structural confidence, developability), **not** by ipSAE alone.

| # | design | branch | muts | ipSAE | sd | n | delta vs parent | epitope | ipTM | interface | verdict |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `HER2_11519` | C_mixed | 5 | 0.6946 | 0.066 | 15 | -0.0181 | 0.983 | 0.894 | OK | indistinguishable |
| 2 | `HER2_1238` | B_interface | 5 | 0.7322 | 0.028 | 14 | 0.0195 | 0.917 | 0.906 | OK | indistinguishable |
| 3 | `HER2_15056` | B_interface | 7 | 0.7213 | 0.051 | 10 | 0.0086 | 0.968 | 0.906 | OK | indistinguishable |
| 4 | `HER2_13625` | C_mixed | 8 | 0.7500 | 0.021 | 11 | 0.0373 | 0.947 | 0.913 | OK | above |
| 5 | `HER2_5693` | D_framework | 6 | 0.7111 | 0.039 | 12 | -0.0016 | 0.974 | 0.896 | OK | indistinguishable |
| 6 | `HER2_15708` | D_framework | 6 | 0.6939 | 0.046 | 11 | -0.0188 | 0.976 | 0.899 | OK | indistinguishable |
| 7 | `HER2_17465` | D_framework | 8 | 0.7290 | 0.051 | 11 | 0.0163 | 0.967 | 0.907 | OK | indistinguishable |
| 8 | `HER2_8022` | B_interface | 8 | 0.6933 | 0.086 | 11 | -0.0194 | 0.957 | 0.895 | OK | indistinguishable |
| 9 | `HER2_9557` | A_h3 | 8 | 0.7023 | 0.064 | 12 | -0.0104 | 0.969 | 0.902 | OK | indistinguishable |
| 10 | `HER2_17118` | C_mixed | 6 | 0.7304 | 0.036 | 11 | 0.0177 | 0.967 | 0.904 | OK | indistinguishable |
| 11 | `HER2_18216` | D_framework | 7 | 0.7220 | 0.034 | 10 | 0.0093 | 0.947 | 0.904 | OK | indistinguishable |
| 12 | `HER2_19503` | D_framework | 6 | 0.7142 | 0.033 | 10 | 0.0015 | 0.990 | 0.897 | OK | indistinguishable |
| 13 | `HER2_14954` | D_framework | 6 | 0.7262 | 0.028 | 14 | 0.0135 | 0.966 | 0.905 | OK | indistinguishable |
| 14 | `HER2B_10177` | C_mixed | 5 | 0.7330 | 0.032 | 2 | 0.0203 | 1.000 | 0.912 | OK | indistinguishable |
| 15 | `HER2_23723` | C_mixed | 5 | 0.7246 | 0.052 | 11 | 0.0119 | 0.986 | 0.906 | OK | indistinguishable |
| 16 | `HER2_21202` | C_mixed | 6 | 0.7221 | 0.020 | 11 | 0.0094 | 0.971 | 0.903 | OK | indistinguishable |
| 17 | `HER2_17254` | D_framework | 7 | 0.7269 | 0.038 | 8 | 0.0142 | 0.941 | 0.905 | OK | indistinguishable |
| 18 | `HER2_0077` | B_interface | 5 | 0.6584 | 0.079 | 12 | -0.0543 | 0.947 | 0.882 | OK | below |
| 19 | `HER2B_0949` | B_interface | 5 | 0.7307 | 0.018 | 2 | 0.0180 | 0.974 | 0.905 | OK | indistinguishable |
| 20 | `HER2_13086` | C_mixed | 7 | 0.6875 | 0.044 | 11 | -0.0252 | 0.957 | 0.895 | OK | indistinguishable |
| 21 | `HER2_18461` | C_mixed | 5 | 0.7276 | 0.038 | 10 | 0.0149 | 0.937 | 0.908 | OK | indistinguishable |
| 22 | `HER2_8533` | D_framework | 7 | 0.6527 | 0.051 | 11 | -0.0600 | 1.000 | 0.887 | OK | below |
| 23 | `HER2_15988` | B_interface | 8 | 0.7133 | 0.025 | 10 | 0.0006 | 0.958 | 0.899 | OK | indistinguishable |
| 24 | `HER2_22350` | C_mixed | 8 | 0.7097 | 0.033 | 8 | -0.0030 | 0.993 | 0.898 | OK | indistinguishable |
| 25 | `HER2_21848` | B_interface | 5 | 0.6928 | 0.039 | 8 | -0.0199 | 0.954 | 0.892 | OK | indistinguishable |
| 26 | `HER2_26656` | C_mixed | 5 | 0.6759 | 0.062 | 11 | -0.0368 | 0.976 | 0.892 | OK | indistinguishable |
| 27 | `HER2_15853` | D_framework | 7 | 0.6581 | 0.054 | 8 | -0.0546 | 0.974 | 0.885 | OK | below |
| 28 | `HER2_15259` | D_framework | 8 | 0.7066 | 0.060 | 8 | -0.0061 | 0.947 | 0.899 | OK | indistinguishable |
| 29 | `HER2_13727` | C_mixed | 8 | 0.6798 | 0.101 | 8 | -0.0329 | 0.980 | 0.888 | OK | indistinguishable |
| 30 | `HER2_24532` | D_framework | 7 | 0.6932 | 0.066 | 10 | -0.0195 | 0.968 | 0.895 | OK | indistinguishable |
| 31 | `HER2_8386` | C_mixed | 5 | 0.6875 | 0.035 | 11 | -0.0252 | 0.952 | 0.888 | OK | indistinguishable |
| 32 | `HER2_12026` | C_mixed | 7 | 0.6892 | 0.052 | 8 | -0.0235 | 0.928 | 0.893 | OK | indistinguishable |
| 33 | `HER2_14514` | C_mixed | 6 | 0.7560 | 0.017 | 11 | 0.0433 | 0.923 | 0.914 | OK | above |
| 34 | `HER2_10808` | B_interface | 8 | 0.6751 | 0.053 | 11 | -0.0376 | 0.943 | 0.889 | OK | indistinguishable |
| 35 | `HER2_0070` | B_interface | 5 | 0.6651 | 0.041 | 12 | -0.0476 | 0.895 | 0.878 | OK | below |
| 36 | `HER2_15323` | B_interface | 5 | 0.6820 | 0.033 | 8 | -0.0307 | 0.934 | 0.894 | OK | indistinguishable |
| 37 | `HER2_7401` | B_interface | 6 | 0.6486 | 0.053 | 10 | -0.0641 | 0.968 | 0.875 | OK | below |
| 38 | `HER2_2407` | D_framework | 6 | 0.6578 | 0.050 | 8 | -0.0549 | 0.987 | 0.886 | OK | below |
| 39 | `HER2_17641` | C_mixed | 8 | 0.7528 | 0.042 | 10 | 0.0401 | 0.868 | 0.911 | OK | above |
| 40 | `HER2B_0719` | B_interface | 5 | 0.6865 | 0.007 | 2 | -0.0262 | 0.974 | 0.895 | OK | below |
| 41 | `HER2B_0930` | B_interface | 5 | 0.7220 | 0.036 | 2 | 0.0093 | 0.947 | 0.898 | OK | indistinguishable |
| 42 | `HER2B_0096` | B_interface | 5 | 0.7286 | 0.069 | 2 | 0.0159 | 0.895 | 0.910 | OK | indistinguishable |
| 43 | `HER2_28172` | D_framework | 7 | 0.7203 | 0.032 | 10 | 0.0076 | 0.947 | 0.907 | OK | indistinguishable |
| 44 | `HER2_10341` | C_mixed | 8 | 0.6587 | 0.088 | 8 | -0.0540 | 0.980 | 0.877 | OK | indistinguishable |
| 45 | `HER2_3536` | C_mixed | 5 | 0.7060 | 0.034 | 10 | -0.0067 | 0.889 | 0.892 | OK | indistinguishable |
| 46 | `HER2B_1130` | B_interface | 5 | 0.6936 | 0.073 | 2 | -0.0191 | 0.974 | 0.900 | OK | indistinguishable |
| 47 | `HER2_24248` | D_framework | 8 | 0.6982 | 0.024 | 8 | -0.0145 | 0.974 | 0.896 | OK | indistinguishable |
| 48 | `HER2B_1025` | B_interface | 5 | 0.6923 | 0.046 | 2 | -0.0204 | 1.000 | 0.887 | OK | indistinguishable |
| 49 | `HER2_19004` | C_mixed | 7 | 0.7016 | 0.033 | 10 | -0.0111 | 0.921 | 0.896 | OK | indistinguishable |
| 50 | `HER2_22721` | C_mixed | 5 | 0.7064 | 0.071 | 8 | -0.0063 | 0.961 | 0.896 | OK | indistinguishable |

## Lab nominations

| # | design | branch | substitutions | ipSAE | epitope | rank shift |
| ---: | --- | --- | --- | ---: | ---: | ---: |
| 1 | `HER2_13625` | C_mixed | `Q13R;N28T;Y52T;P53S;T69S;I70V;D73E;A169N` | 0.7500 | 0.947 | 5 |
| 2 | `HER2_14514` | C_mixed | `T32Y;I51V;N55E;Q82E;S119P;Q173H` | 0.7560 | 0.923 | 40 |
| 3 | `HER2B_0955` | B_interface | `T32Y;Y33W;T54D;V164I;V168L` | 0.7452 | 0.895 | 61 |
| 4 | `HER2_11519` | C_mixed | `I29F;L181F;R201G;I210V;S212G` | 0.6946 | 0.983 | 8 |
| 5 | `HER2_1238` | B_interface | `T32Y;N55G;A79L;A186T;T232A` | 0.7322 | 0.917 | 3 |
| 6 | `HER2_5693` | D_framework | `A79V;S97A;T157A;A169N;V193A;T209I` | 0.7111 | 0.974 | 7 |
| 7 | `HER2_15708` | D_framework | `S7T;A72R;M83L;E89D;L115T;Y171F` | 0.6939 | 0.976 | 11 |
| 8 | `HER2_8022` | B_interface | `T54G;R59Y;I70T;T155S;A160T;T166N;Y184H;R201G` | 0.6933 | 0.957 | 17 |
| 9 | `HER2_9557` | A_h3 | `T32Y;W47Y;E89D;G101T;Y105N;Y109F;S185A;S191I` | 0.7023 | 0.969 | 12 |
| 10 | `HER2_18461` | C_mixed | `I51V;S75A;E89D;I137V;Y184F` | 0.7276 | 0.937 | 9 |
| 11 | `HER2_15988` | B_interface | `I34M;G56S;T58A;S85G;R159Q;Q162L;D163G;I241V` | 0.7133 | 0.958 | 23 |
| 12 | `HER2_13103` | B_interface | `L45P;I51L;D62E;G66D;F188N;T220A` | 0.7081 | 0.822 | 5 |
| 13 | `HER2_11611` | A_h3 | `G100D;A106Y;Y109S;I210V;I241V` | 0.6116 | 0.954 | 36 |
| 14 | `HER2_4995` | A_h3 | `D102S;F104S;M107F;D108A;A167Y;Y171F;S187T;Q224L` | 0.4552 | 0.987 | 66 |
| 15 | `HER2_1582` | A_h3 | `T54N;T74D;G101S;A106S;D163G;A167Y;A169N;K238R` | 0.5677 | 0.900 | 69 |

`rank shift` is how far a design moves under three alternative weightings; a large value means its position depends on one metric.

## Exported binder packages

15 designs exported to `outputs/binders/<id>/` with `sequence.fasta`, `design.json`, `complex.cif`, `pae.npz`, `interface_contacts.csv` and `mutations.csv`. Rotating 3D animations are in `outputs/gifs/`.

| design | muts | modelled contacts | epitope recovery | folder |
| --- | ---: | ---: | ---: | --- |
| `HER2_11519` | 5 | 30 | 1.000 | `binders/HER2_11519` |
| `HER2_1238` | 5 | 31 | 0.921 | `binders/HER2_1238` |
| `HER2_8022` | 8 | 32 | 0.974 | `binders/HER2_8022` |
| `HER2_5693` | 6 | 32 | 0.979 | `binders/HER2_5693` |
| `HER2_13625` | 8 | 28 | 0.947 | `binders/HER2_13625` |
| `HER2_9557` | 8 | 31 | 0.968 | `binders/HER2_9557` |
| `HER2_7401` | 6 | 32 | 0.965 | `binders/HER2_7401` |
| `HER2_14954` | 6 | 32 | 0.974 | `binders/HER2_14954` |
| `HER2_3536` | 5 | 29 | 0.860 | `binders/HER2_3536` |
| `HER2_11456` | 7 | 28 | 0.947 | `binders/HER2_11456` |
| `HER2_2788` | 8 | 29 | 0.947 | `binders/HER2_2788` |
| `HER2_9311` | 8 | 34 | 0.947 | `binders/HER2_9311` |
| `HER2_8404` | 7 | 31 | 0.947 | `binders/HER2_8404` |
| `HER2_1582` | 8 | 29 | 0.842 | `binders/HER2_1582` |
| `HER2_8252` | 8 | 24 | 0.789 | `binders/HER2_8252` |

## Figures

**ipSAE distribution of designed variants**

![ipSAE distribution of designed variants](../figures/01_ipsae_distribution.png)

**Interface quality vs substitution count**

![Interface quality vs substitution count](../figures/02_ipsae_by_mutation_count.png)

**Interface quality by design branch**

![Interface quality by design branch](../figures/03_ipsae_by_branch.png)

**Seed noise against between-design differences**

![Seed noise against between-design differences](../figures/04_replicate_spread.png)

**How much of the ipSAE ranking is real**

![How much of the ipSAE ranking is real](../figures/05_reliability.png)

**Sequence scores vs structural outcomes**

![Sequence scores vs structural outcomes](../figures/06_score_correlations.png)

**Epitope recovery against interface confidence**

![Epitope recovery against interface confidence](../figures/07_epitope_vs_ipsae.png)

**Nominated designs with replicate error bars**

![Nominated designs with replicate error bars](../figures/08_top_designs.png)

**Structures scored, by compute source**

![Structures scored, by compute source](../figures/09_throughput.png)

## Limitations

- ipSAE, ipTM, pDockQ and LIS are model-confidence measures, not affinities.
- The parent is ~0.82 pM; assay floor effects make improvement hard to show even experimentally.
- The domain IV crop removes receptor context and glycans; it is required by the organizer and applied identically to parent and candidates.
- MSA reuse keeps the parent's homolog block, which slightly favours designs closer to the parent. A fresh-MSA control was attempted but did not complete.
- AbLang2, ESM2 and ESM-C never see HER2; they reject implausible sequences, they do not identify better binders.
- Selection weights are a reasoned hypothesis, quantified by the sensitivity analysis.

