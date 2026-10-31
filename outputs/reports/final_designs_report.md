# Final designs report - HER2 scFv optimisation

Generated 2026-10-31T15:24:52+00:00.

> **Claim boundary.** Every value here is a computational ranking signal for experimental triage. ipSAE is not a binding affinity, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. No K_D is predicted.

## Headline

| Quantity | Value |
| --- | ---: |
| Designs with a genuine external ipSAE | **248** |
| Structures behind them | 1964 |
| Local / Modal structures | 596 / 1368 |
| Ranked submission set | 50 |
| Lab nominations | 15 |
| Parent replicates | 30 |
| Compliance audit | **PASS** (0 failed) |

Parent baseline: **0.6949** +/- 0.0597 over 30 seeds.

### How each design compares with the parent

| Verdict | Designs |
| --- | ---: |
| ABOVE_PARENT | 0 |
| BELOW_PARENT | 107 |
| WITHIN_SEED_NOISE | 141 |
| SINGLE_SEED_UNRELIABLE | 0 |
| NO_PARENT_BASELINE | 0 |

`SINGLE_SEED_UNRELIABLE` means the design has one replicate, which at the measured reliability cannot support a directional claim either way.

## Top 50 ranked designs

Ranked by the multi-objective score (sequence consensus, ipSAE, epitope recovery, structural confidence, developability), **not** by ipSAE alone.

| # | design | branch | muts | ipSAE | sd | n | delta vs parent | epitope | ipTM | interface | verdict |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `HER2_11519` | C_mixed | 5 | 0.7059 | 0.039 | 30 | 0.0110 | 0.977 | 0.897 | OK | indistinguishable |
| 2 | `HER2_1238` | B_interface | 5 | 0.7372 | 0.036 | 29 | 0.0423 | 0.916 | 0.908 | OK | above |
| 3 | `HER2_5693` | D_framework | 6 | 0.7173 | 0.039 | 27 | 0.0224 | 0.977 | 0.897 | OK | indistinguishable |
| 4 | `HER2_15056` | B_interface | 7 | 0.7206 | 0.053 | 12 | 0.0257 | 0.965 | 0.906 | OK | indistinguishable |
| 5 | `HER2_13625` | C_mixed | 8 | 0.7498 | 0.023 | 28 | 0.0549 | 0.942 | 0.913 | OK | above |
| 6 | `HER2_17465` | D_framework | 8 | 0.7343 | 0.049 | 13 | 0.0394 | 0.972 | 0.908 | OK | above |
| 7 | `HER2_15708` | D_framework | 6 | 0.6922 | 0.047 | 13 | -0.0027 | 0.976 | 0.898 | OK | indistinguishable |
| 8 | `HER2_9557` | A_h3 | 8 | 0.7067 | 0.052 | 27 | 0.0118 | 0.971 | 0.904 | OK | indistinguishable |
| 9 | `HER2_18216` | D_framework | 7 | 0.7266 | 0.033 | 12 | 0.0317 | 0.943 | 0.904 | OK | above |
| 10 | `HER2_17118` | C_mixed | 6 | 0.7326 | 0.034 | 13 | 0.0377 | 0.964 | 0.905 | OK | above |
| 11 | `HER2_14954` | D_framework | 6 | 0.7221 | 0.043 | 28 | 0.0272 | 0.970 | 0.903 | OK | indistinguishable |
| 12 | `HER2_23723` | C_mixed | 5 | 0.7250 | 0.049 | 13 | 0.0301 | 0.984 | 0.907 | OK | indistinguishable |
| 13 | `HER2_8022` | B_interface | 8 | 0.6874 | 0.070 | 26 | -0.0075 | 0.951 | 0.893 | OK | indistinguishable |
| 14 | `HER2_19503` | D_framework | 6 | 0.7081 | 0.033 | 12 | 0.0132 | 0.987 | 0.896 | OK | indistinguishable |
| 15 | `HER2_21202` | C_mixed | 6 | 0.7218 | 0.024 | 13 | 0.0269 | 0.972 | 0.903 | OK | above |
| 16 | `HER2_17254` | D_framework | 7 | 0.7269 | 0.038 | 8 | 0.0320 | 0.941 | 0.905 | OK | indistinguishable |
| 17 | `HER2_13086` | C_mixed | 7 | 0.6804 | 0.044 | 14 | -0.0145 | 0.962 | 0.894 | OK | indistinguishable |
| 18 | `HER2_0077` | B_interface | 5 | 0.6515 | 0.089 | 14 | -0.0434 | 0.947 | 0.880 | OK | indistinguishable |
| 19 | `HER2_8533` | D_framework | 7 | 0.6527 | 0.051 | 11 | -0.0422 | 1.000 | 0.887 | OK | below |
| 20 | `HER2_18461` | C_mixed | 5 | 0.7212 | 0.040 | 12 | 0.0263 | 0.930 | 0.906 | OK | indistinguishable |
| 21 | `HER2_22350` | C_mixed | 8 | 0.7097 | 0.033 | 8 | 0.0148 | 0.993 | 0.898 | OK | indistinguishable |
| 22 | `HER2_21848` | B_interface | 5 | 0.6928 | 0.039 | 8 | -0.0021 | 0.954 | 0.892 | OK | indistinguishable |
| 23 | `HER2_7401` | B_interface | 6 | 0.6576 | 0.096 | 25 | -0.0373 | 0.971 | 0.877 | OK | indistinguishable |
| 24 | `HER2_15853` | D_framework | 7 | 0.6581 | 0.054 | 8 | -0.0368 | 0.974 | 0.885 | OK | indistinguishable |
| 25 | `HER2_15988` | B_interface | 8 | 0.7154 | 0.024 | 12 | 0.0205 | 0.952 | 0.900 | OK | indistinguishable |
| 26 | `HER2_24532` | D_framework | 7 | 0.6932 | 0.066 | 10 | -0.0017 | 0.968 | 0.895 | OK | indistinguishable |
| 27 | `HER2_8386` | C_mixed | 5 | 0.6875 | 0.035 | 11 | -0.0074 | 0.952 | 0.888 | OK | indistinguishable |
| 28 | `HER2_13727` | C_mixed | 8 | 0.6798 | 0.101 | 8 | -0.0151 | 0.980 | 0.888 | OK | indistinguishable |
| 29 | `HER2_15259` | D_framework | 8 | 0.7066 | 0.060 | 8 | 0.0117 | 0.947 | 0.899 | OK | indistinguishable |
| 30 | `HER2_26656` | C_mixed | 5 | 0.6759 | 0.062 | 11 | -0.0190 | 0.976 | 0.892 | OK | indistinguishable |
| 31 | `HER2_0070` | B_interface | 5 | 0.6656 | 0.037 | 15 | -0.0293 | 0.902 | 0.878 | OK | below |
| 32 | `HER2_15323` | B_interface | 5 | 0.6820 | 0.033 | 8 | -0.0129 | 0.934 | 0.894 | OK | indistinguishable |
| 33 | `HER2_12026` | C_mixed | 7 | 0.6892 | 0.052 | 8 | -0.0057 | 0.928 | 0.893 | OK | indistinguishable |
| 34 | `HER2_10808` | B_interface | 8 | 0.6724 | 0.047 | 14 | -0.0225 | 0.944 | 0.888 | OK | indistinguishable |
| 35 | `HER2_2407` | D_framework | 6 | 0.6578 | 0.050 | 8 | -0.0371 | 0.987 | 0.886 | OK | indistinguishable |
| 36 | `HER2_17641` | C_mixed | 8 | 0.7569 | 0.039 | 12 | 0.0620 | 0.873 | 0.913 | OK | above |
| 37 | `HER2B_0949` | B_interface | 5 | 0.7170 | 0.034 | 5 | 0.0221 | 0.958 | 0.899 | OK | indistinguishable |
| 38 | `HER2_14514` | C_mixed | 6 | 0.7534 | 0.017 | 13 | 0.0585 | 0.919 | 0.913 | OK | above |
| 39 | `HER2_28172` | D_framework | 7 | 0.7203 | 0.032 | 10 | 0.0254 | 0.947 | 0.907 | OK | indistinguishable |
| 40 | `HER2_10341` | C_mixed | 8 | 0.6587 | 0.088 | 8 | -0.0362 | 0.980 | 0.877 | OK | indistinguishable |
| 41 | `HER2_24248` | D_framework | 8 | 0.6982 | 0.024 | 8 | 0.0033 | 0.974 | 0.896 | OK | indistinguishable |
| 42 | `HER2B_0719` | B_interface | 5 | 0.6769 | 0.051 | 5 | -0.0180 | 0.979 | 0.894 | OK | indistinguishable |
| 43 | `HER2B_1130` | B_interface | 5 | 0.6906 | 0.042 | 5 | -0.0043 | 0.979 | 0.900 | OK | indistinguishable |
| 44 | `HER2_7827` | C_mixed | 8 | 0.6833 | 0.042 | 10 | -0.0116 | 0.921 | 0.889 | OK | indistinguishable |
| 45 | `HER2_22721` | C_mixed | 5 | 0.7064 | 0.071 | 8 | 0.0115 | 0.961 | 0.896 | OK | indistinguishable |
| 46 | `HER2B_10177` | C_mixed | 5 | 0.7009 | 0.033 | 6 | 0.0060 | 0.956 | 0.898 | OK | indistinguishable |
| 47 | `HER2_13103` | B_interface | 6 | 0.7081 | 0.083 | 8 | 0.0132 | 0.822 | 0.901 | OK | indistinguishable |
| 48 | `HER2_6796` | C_mixed | 6 | 0.6339 | 0.045 | 8 | -0.0610 | 0.954 | 0.869 | OK | below |
| 49 | `HER2_2720` | C_mixed | 7 | 0.7068 | 0.038 | 10 | 0.0119 | 0.900 | 0.894 | OK | indistinguishable |
| 50 | `HER2_20989` | D_framework | 7 | 0.6673 | 0.083 | 10 | -0.0276 | 0.974 | 0.885 | OK | indistinguishable |

## Lab nominations

| # | design | branch | substitutions | ipSAE | epitope | rank shift |
| ---: | --- | --- | --- | ---: | ---: | ---: |
| 1 | `HER2_1238` | B_interface | `T32Y;N55G;A79L;A186T;T232A` | 0.7372 | 0.916 | 1 |
| 2 | `HER2_13625` | C_mixed | `Q13R;N28T;Y52T;P53S;T69S;I70V;D73E;A169N` | 0.7498 | 0.942 | 4 |
| 3 | `HER2_17118` | C_mixed | `L86P;S97A;A169N;Q173H;A186E;K238N` | 0.7326 | 0.964 | 10 |
| 4 | `HER2_17641` | C_mixed | `A24V;Y52S;D62E;A79L;E89D;S185V;S195L;S212N` | 0.7569 | 0.873 | 17 |
| 5 | `HER2_14514` | C_mixed | `T32Y;I51V;N55E;Q82E;S119P;Q173H` | 0.7534 | 0.919 | 37 |
| 6 | `HER2B_2696` | B_interface | `T32Y;A61G;A72R;T166N;T228S` | 0.7448 | 0.965 | 95 |
| 7 | `HER2_11519` | C_mixed | `I29F;L181F;R201G;I210V;S212G` | 0.7059 | 0.977 | 5 |
| 8 | `HER2_5693` | D_framework | `A79V;S97A;T157A;A169N;V193A;T209I` | 0.7173 | 0.977 | 3 |
| 9 | `HER2_15708` | D_framework | `S7T;A72R;M83L;E89D;L115T;Y171F` | 0.6922 | 0.976 | 10 |
| 10 | `HER2_9557` | A_h3 | `T32Y;W47Y;E89D;G101T;Y105N;Y109F;S185A;S191I` | 0.7067 | 0.971 | 6 |
| 11 | `HER2_8022` | B_interface | `T54G;R59Y;I70T;T155S;A160T;T166N;Y184H;R201G` | 0.6874 | 0.951 | 15 |
| 12 | `HER2_18461` | C_mixed | `I51V;S75A;E89D;I137V;Y184F` | 0.7212 | 0.930 | 15 |
| 13 | `HER2_7401` | B_interface | `L20V;D62E;V64L;F104N;D163G;V164I` | 0.6576 | 0.971 | 37 |
| 14 | `HER2B_0302` | B_interface | `G66D;V168L;A169N;F188S;Y190E` | 0.7068 | 0.877 | 46 |
| 15 | `HER2_9311` | A_h3 | `A92S;W99D;D102G;D108G;V168L;K177E;T228S;T232A` | 0.6204 | 0.927 | 38 |

`rank shift` is how far a design moves under three alternative weightings; a large value means its position depends on one metric.

## Exported binder packages

15 designs exported to `outputs/binders/<id>/` with `sequence.fasta`, `design.json`, `complex.cif`, `pae.npz`, `interface_contacts.csv` and `mutations.csv`. Rotating 3D animations are in `outputs/gifs/`.

| design | muts | modelled contacts | epitope recovery | folder |
| --- | ---: | ---: | ---: | --- |
| `HER2_1238` | 5 | 30 | 0.918 | `binders/HER2_1238` |
| `HER2_13625` | 8 | 30 | 0.943 | `binders/HER2_13625` |
| `HER2B_0949` | 5 | 31 | 0.947 | `binders/HER2B_0949` |
| `HER2_14514` | 6 | 31 | 0.923 | `binders/HER2_14514` |
| `HER2_17641` | 8 | 28 | 0.868 | `binders/HER2_17641` |
| `HER2B_2696` | 5 | 32 | 0.965 | `binders/HER2B_2696` |
| `HER2_11519` | 5 | 32 | 0.979 | `binders/HER2_11519` |
| `HER2_5693` | 6 | 31 | 0.977 | `binders/HER2_5693` |
| `HER2_15708` | 6 | 29 | 0.976 | `binders/HER2_15708` |
| `HER2_9557` | 8 | 30 | 0.971 | `binders/HER2_9557` |
| `HER2_8022` | 8 | 27 | 0.951 | `binders/HER2_8022` |
| `HER2_18461` | 5 | 30 | 0.937 | `binders/HER2_18461` |
| `HER2_15988` | 8 | 31 | 0.958 | `binders/HER2_15988` |
| `HER2_13103` | 6 | 27 | 0.822 | `binders/HER2_13103` |
| `HER2_9311` | 8 | 30 | 0.927 | `binders/HER2_9311` |

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

