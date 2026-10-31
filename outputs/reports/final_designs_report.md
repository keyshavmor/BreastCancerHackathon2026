# Final designs report - HER2 scFv optimisation

Generated 2026-10-31T15:47:14+00:00.

> **Claim boundary.** Every value here is a computational ranking signal for experimental triage. ipSAE is not a binding affinity, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. No K_D is predicted.

## Headline

| Quantity | Value |
| --- | ---: |
| Designs with a genuine external ipSAE | **248** |
| Structures behind them | 2432 |
| Local / Modal structures | 629 / 1803 |
| Ranked submission set | 50 |
| Lab nominations | 15 |
| Parent replicates | 42 |
| Compliance audit | **PASS** (0 failed) |

Parent baseline: **0.7003** +/- 0.0546 over 42 seeds.

### How each design compares with the parent

| Verdict | Designs |
| --- | ---: |
| ABOVE_PARENT | 0 |
| BELOW_PARENT | 111 |
| WITHIN_SEED_NOISE | 137 |
| SINGLE_SEED_UNRELIABLE | 0 |
| NO_PARENT_BASELINE | 0 |

`SINGLE_SEED_UNRELIABLE` means the design has one replicate, which at the measured reliability cannot support a directional claim either way.

## Top 50 ranked designs

Ranked by the multi-objective score (sequence consensus, ipSAE, epitope recovery, structural confidence, developability), **not** by ipSAE alone.

| # | design | branch | muts | ipSAE | sd | n | delta vs parent | epitope | ipTM | interface | verdict |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `HER2_11519` | C_mixed | 5 | 0.7088 | 0.037 | 37 | 0.0085 | 0.974 | 0.898 | OK | indistinguishable |
| 2 | `HER2_5693` | D_framework | 6 | 0.7232 | 0.036 | 37 | 0.0229 | 0.976 | 0.898 | OK | above |
| 3 | `HER2_1238` | B_interface | 5 | 0.7370 | 0.039 | 39 | 0.0367 | 0.918 | 0.908 | OK | above |
| 4 | `HER2_9557` | A_h3 | 8 | 0.7149 | 0.050 | 37 | 0.0146 | 0.969 | 0.906 | OK | indistinguishable |
| 5 | `HER2_15056` | B_interface | 7 | 0.6960 | 0.058 | 20 | -0.0043 | 0.979 | 0.899 | OK | indistinguishable |
| 6 | `HER2_17465` | D_framework | 8 | 0.7322 | 0.051 | 21 | 0.0319 | 0.970 | 0.907 | OK | above |
| 7 | `HER2_13625` | C_mixed | 8 | 0.7487 | 0.023 | 38 | 0.0484 | 0.936 | 0.913 | OK | above |
| 8 | `HER2_15708` | D_framework | 6 | 0.6837 | 0.059 | 21 | -0.0166 | 0.978 | 0.896 | OK | indistinguishable |
| 9 | `HER2_21202` | C_mixed | 6 | 0.7216 | 0.022 | 21 | 0.0213 | 0.975 | 0.903 | OK | above |
| 10 | `HER2_19503` | D_framework | 6 | 0.7184 | 0.032 | 20 | 0.0181 | 0.979 | 0.900 | OK | indistinguishable |
| 11 | `HER2_14954` | D_framework | 6 | 0.7214 | 0.045 | 36 | 0.0211 | 0.966 | 0.903 | OK | indistinguishable |
| 12 | `HER2_8022` | B_interface | 8 | 0.6908 | 0.064 | 36 | -0.0095 | 0.946 | 0.894 | OK | indistinguishable |
| 13 | `HER2_17118` | C_mixed | 6 | 0.7291 | 0.033 | 23 | 0.0288 | 0.950 | 0.904 | OK | above |
| 14 | `HER2_23723` | C_mixed | 5 | 0.7253 | 0.039 | 21 | 0.0250 | 0.980 | 0.908 | OK | above |
| 15 | `HER2_17254` | D_framework | 7 | 0.7269 | 0.038 | 8 | 0.0266 | 0.941 | 0.905 | OK | indistinguishable |
| 16 | `HER2_18216` | D_framework | 7 | 0.7269 | 0.027 | 22 | 0.0266 | 0.919 | 0.904 | OK | above |
| 17 | `HER2_8386` | C_mixed | 5 | 0.7001 | 0.030 | 21 | -0.0002 | 0.962 | 0.892 | OK | indistinguishable |
| 18 | `HER2_18461` | C_mixed | 5 | 0.7178 | 0.039 | 20 | 0.0175 | 0.934 | 0.904 | OK | indistinguishable |
| 19 | `HER2_7401` | B_interface | 6 | 0.6565 | 0.097 | 35 | -0.0438 | 0.973 | 0.878 | OK | below |
| 20 | `HER2_21848` | B_interface | 5 | 0.6928 | 0.039 | 8 | -0.0075 | 0.954 | 0.892 | OK | indistinguishable |
| 21 | `HER2_13086` | C_mixed | 7 | 0.6686 | 0.077 | 21 | -0.0317 | 0.962 | 0.889 | OK | indistinguishable |
| 22 | `HER2_15853` | D_framework | 7 | 0.6581 | 0.054 | 8 | -0.0422 | 0.974 | 0.885 | OK | below |
| 23 | `HER2_15259` | D_framework | 8 | 0.7066 | 0.060 | 8 | 0.0063 | 0.947 | 0.899 | OK | indistinguishable |
| 24 | `HER2_0070` | B_interface | 5 | 0.6708 | 0.035 | 22 | -0.0295 | 0.897 | 0.880 | OK | below |
| 25 | `HER2_24532` | D_framework | 7 | 0.6932 | 0.066 | 10 | -0.0071 | 0.968 | 0.895 | OK | indistinguishable |
| 26 | `HER2_8533` | D_framework | 7 | 0.6431 | 0.055 | 21 | -0.0572 | 0.985 | 0.884 | OK | below |
| 27 | `HER2_13727` | C_mixed | 8 | 0.6798 | 0.101 | 8 | -0.0205 | 0.980 | 0.888 | OK | indistinguishable |
| 28 | `HER2_10808` | B_interface | 8 | 0.6734 | 0.040 | 21 | -0.0269 | 0.947 | 0.888 | OK | below |
| 29 | `HER2_0077` | B_interface | 5 | 0.6247 | 0.131 | 22 | -0.0756 | 0.952 | 0.869 | OK | below |
| 30 | `HER2_12026` | C_mixed | 7 | 0.6892 | 0.052 | 8 | -0.0111 | 0.928 | 0.893 | OK | indistinguishable |
| 31 | `HER2_15323` | B_interface | 5 | 0.6820 | 0.033 | 8 | -0.0183 | 0.934 | 0.894 | OK | indistinguishable |
| 32 | `HER2_7827` | C_mixed | 8 | 0.6802 | 0.043 | 20 | -0.0201 | 0.932 | 0.887 | OK | indistinguishable |
| 33 | `HER2_15988` | B_interface | 8 | 0.7150 | 0.026 | 20 | 0.0147 | 0.937 | 0.900 | OK | indistinguishable |
| 34 | `HER2_10341` | C_mixed | 8 | 0.6587 | 0.088 | 8 | -0.0416 | 0.980 | 0.877 | OK | indistinguishable |
| 35 | `HER2_17641` | C_mixed | 8 | 0.7500 | 0.041 | 22 | 0.0497 | 0.859 | 0.911 | OK | above |
| 36 | `HER2_24248` | D_framework | 8 | 0.6982 | 0.024 | 8 | -0.0021 | 0.974 | 0.896 | OK | indistinguishable |
| 37 | `HER2_26656` | C_mixed | 5 | 0.6672 | 0.085 | 21 | -0.0331 | 0.967 | 0.887 | OK | indistinguishable |
| 38 | `HER2_14514` | C_mixed | 6 | 0.7568 | 0.016 | 23 | 0.0565 | 0.913 | 0.914 | OK | above |
| 39 | `HER2_22350` | C_mixed | 8 | 0.7121 | 0.029 | 18 | 0.0118 | 0.959 | 0.898 | OK | indistinguishable |
| 40 | `HER2B_0719` | B_interface | 5 | 0.6858 | 0.039 | 13 | -0.0145 | 0.964 | 0.897 | OK | indistinguishable |
| 41 | `HER2_28172` | D_framework | 7 | 0.7098 | 0.041 | 20 | 0.0095 | 0.945 | 0.903 | OK | indistinguishable |
| 42 | `HER2_2407` | D_framework | 6 | 0.6509 | 0.094 | 18 | -0.0494 | 0.983 | 0.882 | OK | below |
| 43 | `HER2_22721` | C_mixed | 5 | 0.7064 | 0.071 | 8 | 0.0061 | 0.961 | 0.896 | OK | indistinguishable |
| 44 | `HER2_13103` | B_interface | 6 | 0.7081 | 0.083 | 8 | 0.0078 | 0.822 | 0.901 | OK | indistinguishable |
| 45 | `HER2B_1025` | B_interface | 5 | 0.6843 | 0.048 | 13 | -0.0160 | 0.988 | 0.882 | OK | indistinguishable |
| 46 | `HER2_6796` | C_mixed | 6 | 0.6339 | 0.045 | 8 | -0.0664 | 0.954 | 0.869 | OK | below |
| 47 | `HER2B_1130` | B_interface | 5 | 0.6809 | 0.057 | 13 | -0.0194 | 0.976 | 0.897 | OK | indistinguishable |
| 48 | `HER2B_2696` | B_interface | 5 | 0.7525 | 0.018 | 5 | 0.0522 | 0.968 | 0.913 | OK | above |
| 49 | `HER2_20989` | D_framework | 7 | 0.6673 | 0.083 | 10 | -0.0330 | 0.974 | 0.885 | OK | indistinguishable |
| 50 | `HER2_23267` | D_framework | 7 | 0.6469 | 0.056 | 10 | -0.0534 | 0.979 | 0.884 | OK | below |

## Lab nominations

| # | design | branch | substitutions | ipSAE | epitope | rank shift |
| ---: | --- | --- | --- | ---: | ---: | ---: |
| 1 | `HER2_1238` | B_interface | `T32Y;N55G;A79L;A186T;T232A` | 0.7370 | 0.918 | 2 |
| 2 | `HER2_13625` | C_mixed | `Q13R;N28T;Y52T;P53S;T69S;I70V;D73E;A169N` | 0.7487 | 0.936 | 3 |
| 3 | `HER2_17118` | C_mixed | `L86P;S97A;A169N;Q173H;A186E;K238N` | 0.7291 | 0.950 | 16 |
| 4 | `HER2_18216` | D_framework | `D31T;A49S;Q82E;L86V;T207S;Q235G;K238R` | 0.7269 | 0.919 | 3 |
| 5 | `HER2_17641` | C_mixed | `A24V;Y52S;D62E;A79L;E89D;S185V;S195L;S212N` | 0.7500 | 0.859 | 22 |
| 6 | `HER2_14514` | C_mixed | `T32Y;I51V;N55E;Q82E;S119P;Q173H` | 0.7568 | 0.913 | 39 |
| 7 | `HER2B_2696` | B_interface | `T32Y;A61G;A72R;T166N;T228S` | 0.7525 | 0.968 | 99 |
| 8 | `HER2_11519` | C_mixed | `I29F;L181F;R201G;I210V;S212G` | 0.7088 | 0.974 | 1 |
| 9 | `HER2_5693` | D_framework | `A79V;S97A;T157A;A169N;V193A;T209I` | 0.7232 | 0.976 | 1 |
| 10 | `HER2_9557` | A_h3 | `T32Y;W47Y;E89D;G101T;Y105N;Y109F;S185A;S191I` | 0.7149 | 0.969 | 5 |
| 11 | `HER2_15708` | D_framework | `S7T;A72R;M83L;E89D;L115T;Y171F` | 0.6837 | 0.978 | 10 |
| 12 | `HER2_8022` | B_interface | `T54G;R59Y;I70T;T155S;A160T;T166N;Y184H;R201G` | 0.6908 | 0.946 | 13 |
| 13 | `HER2_18461` | C_mixed | `I51V;S75A;E89D;I137V;Y184F` | 0.7178 | 0.934 | 16 |
| 14 | `HER2_7401` | B_interface | `L20V;D62E;V64L;F104N;D163G;V164I` | 0.6565 | 0.973 | 39 |
| 15 | `HER2B_0302` | B_interface | `G66D;V168L;A169N;F188S;Y190E` | 0.7068 | 0.877 | 46 |

`rank shift` is how far a design moves under three alternative weightings; a large value means its position depends on one metric.

## Exported binder packages

12 designs exported to `outputs/binders/<id>/` with `sequence.fasta`, `design.json`, `complex.cif`, `pae.npz`, `interface_contacts.csv` and `mutations.csv`. Rotating 3D animations are in `outputs/gifs/`.

| design | muts | modelled contacts | epitope recovery | folder |
| --- | ---: | ---: | ---: | --- |
| `HER2_11519` | 5 | 30 | 0.976 | `binders/HER2_11519` |
| `HER2_1238` | 5 | 30 | 0.917 | `binders/HER2_1238` |
| `HER2_5693` | 6 | 31 | 0.975 | `binders/HER2_5693` |
| `HER2_15056` | 7 | 31 | 0.972 | `binders/HER2_15056` |
| `HER2_17465` | 8 | 29 | 0.974 | `binders/HER2_17465` |
| `HER2_9557` | 8 | 31 | 0.970 | `binders/HER2_9557` |
| `HER2_13625` | 8 | 31 | 0.936 | `binders/HER2_13625` |
| `HER2_17118` | 6 | 30 | 0.970 | `binders/HER2_17118` |
| `HER2_15708` | 6 | 27 | 0.980 | `binders/HER2_15708` |
| `HER2_14954` | 6 | 31 | 0.969 | `binders/HER2_14954` |
| `HER2_18216` | 7 | 29 | 0.933 | `binders/HER2_18216` |
| `HER2_19503` | 6 | 31 | 0.986 | `binders/HER2_19503` |

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

