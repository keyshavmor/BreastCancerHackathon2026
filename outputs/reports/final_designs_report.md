# Final designs report - HER2 scFv optimisation

Generated 2026-10-31T15:11:47+00:00.

> **Claim boundary.** Every value here is a computational ranking signal for experimental triage. ipSAE is not a binding affinity, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. No K_D is predicted.

## Headline

| Quantity | Value |
| --- | ---: |
| Designs with a genuine external ipSAE | **248** |
| Structures behind them | 553 |
| Local / Modal structures | 553 / 0 |
| Ranked submission set | 50 |
| Lab nominations | 15 |
| Parent replicates | 7 |
| Compliance audit | **PASS** (0 failed) |

Parent baseline: **0.6855** +/- 0.0595 over 7 seeds.

### How each design compares with the parent

| Verdict | Designs |
| --- | ---: |
| ABOVE_PARENT | 0 |
| BELOW_PARENT | 61 |
| WITHIN_SEED_NOISE | 101 |
| SINGLE_SEED_UNRELIABLE | 86 |
| NO_PARENT_BASELINE | 0 |

`SINGLE_SEED_UNRELIABLE` means the design has one replicate, which at the measured reliability cannot support a directional claim either way.

## Top 50 ranked designs

Ranked by the multi-objective score (sequence consensus, ipSAE, epitope recovery, structural confidence, developability), **not** by ipSAE alone.

| # | design | branch | muts | ipSAE | sd | n | delta vs parent | epitope | ipTM | interface | verdict |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `HER2_11519` | C_mixed | 5 | 0.7131 | 0.035 | 4 | 0.0276 | 1.000 | 0.899 | OK | indistinguishable |
| 2 | `HER2_8022` | B_interface | 8 | 0.7267 | 0.027 | 4 | 0.0412 | 0.974 | 0.903 | OK | indistinguishable |
| 3 | `HER2_1238` | B_interface | 5 | 0.7417 | 0.021 | 4 | 0.0562 | 0.921 | 0.908 | OK | above |
| 4 | `HER2_5693` | D_framework | 6 | 0.7258 | 0.023 | 5 | 0.0403 | 0.979 | 0.900 | OK | indistinguishable |
| 5 | `HER2_13625` | C_mixed | 8 | 0.7451 | 0.012 | 4 | 0.0596 | 0.947 | 0.911 | OK | above |
| 6 | `HER2_17118` | C_mixed | 6 | 0.7513 | 0.035 | 4 | 0.0658 | 0.987 | 0.910 | OK | above |
| 7 | `HER2_9557` | A_h3 | 8 | 0.7133 | 0.041 | 5 | 0.0278 | 0.968 | 0.904 | OK | indistinguishable |
| 8 | `HER2B_10177` | C_mixed | 5 | 0.7330 | 0.032 | 2 | 0.0475 | 1.000 | 0.912 | OK | indistinguishable |
| 9 | `HER2_14954` | D_framework | 6 | 0.7226 | 0.035 | 4 | 0.0371 | 0.974 | 0.904 | OK | indistinguishable |
| 10 | `HER2_21202` | C_mixed | 6 | 0.7306 | 0.010 | 4 | 0.0451 | 0.974 | 0.906 | OK | indistinguishable |
| 11 | `HER2_17465` | D_framework | 8 | 0.7496 | 0.038 | 4 | 0.0641 | 0.947 | 0.915 | OK | above |
| 12 | `HER2_19503` | D_framework | 6 | 0.7011 | 0.034 | 3 | 0.0156 | 1.000 | 0.894 | OK | indistinguishable |
| 13 | `HER2_14514` | C_mixed | 6 | 0.7486 | 0.013 | 4 | 0.0631 | 0.961 | 0.912 | OK | above |
| 14 | `HER2_23723` | C_mixed | 5 | 0.7349 | 0.047 | 4 | 0.0494 | 0.974 | 0.909 | OK | indistinguishable |
| 15 | `HER2_18216` | D_framework | 7 | 0.7209 | 0.046 | 3 | 0.0354 | 0.930 | 0.903 | OK | indistinguishable |
| 16 | `HER2_8386` | C_mixed | 5 | 0.7054 | 0.037 | 4 | 0.0199 | 0.961 | 0.893 | OK | indistinguishable |
| 17 | `HER2_10808` | B_interface | 8 | 0.6850 | 0.039 | 4 | -0.0005 | 0.947 | 0.893 | OK | indistinguishable |
| 18 | `HER2_13086` | C_mixed | 7 | 0.6961 | 0.047 | 4 | 0.0106 | 0.947 | 0.896 | OK | indistinguishable |
| 19 | `HER2_15708` | D_framework | 6 | 0.6682 | 0.067 | 4 | -0.0173 | 0.961 | 0.890 | OK | indistinguishable |
| 20 | `HER2_28172` | D_framework | 7 | 0.7162 | 0.043 | 3 | 0.0307 | 1.000 | 0.905 | OK | indistinguishable |
| 21 | `HER2_7401` | B_interface | 6 | 0.6648 | 0.038 | 3 | -0.0207 | 0.965 | 0.882 | OK | indistinguishable |
| 22 | `HER2_0070` | B_interface | 5 | 0.6856 | 0.024 | 5 | 0.0001 | 0.863 | 0.884 | OK | indistinguishable |
| 23 | `HER2_2720` | C_mixed | 7 | 0.7292 | 0.039 | 3 | 0.0437 | 0.930 | 0.902 | OK | indistinguishable |
| 24 | `HER2_15056` | B_interface | 7 | 0.6596 | 0.040 | 3 | -0.0259 | 0.965 | 0.888 | OK | indistinguishable |
| 25 | `HER2_8533` | D_framework | 7 | 0.6488 | 0.076 | 4 | -0.0367 | 1.000 | 0.887 | OK | indistinguishable |
| 26 | `HER2_0077` | B_interface | 5 | 0.6484 | 0.082 | 5 | -0.0371 | 0.926 | 0.882 | OK | indistinguishable |
| 27 | `HER2_18461` | C_mixed | 5 | 0.7262 | 0.008 | 3 | 0.0407 | 0.912 | 0.906 | OK | indistinguishable |
| 28 | `HER2B_0949` | B_interface | 5 | 0.7282 | 0.013 | 3 | 0.0427 | 0.947 | 0.904 | OK | indistinguishable |
| 29 | `HER2B_0719` | B_interface | 5 | 0.6971 | 0.019 | 3 | 0.0116 | 0.983 | 0.899 | OK | indistinguishable |
| 30 | `HER2_34846` | D_framework | 7 | 0.7161 | 0.021 | 3 | 0.0306 | 0.983 | 0.906 | OK | indistinguishable |
| 31 | `HER2_26656` | C_mixed | 5 | 0.6632 | 0.081 | 4 | -0.0223 | 0.987 | 0.887 | OK | indistinguishable |
| 32 | `HER2_10014` | C_mixed | 7 | 0.6940 | 0.000 | 1 | 0.0085 | 1.000 | 0.887 | OK | 1 seed |
| 33 | `HER2_2407` | D_framework | 6 | 0.6499 | 0.000 | 1 | -0.0356 | 1.000 | 0.887 | OK | 1 seed |
| 34 | `HER2_17641` | C_mixed | 8 | 0.7595 | 0.029 | 3 | 0.0740 | 0.842 | 0.914 | OK | above |
| 35 | `HER2_14939` | C_mixed | 7 | 0.7249 | 0.009 | 3 | 0.0394 | 0.930 | 0.901 | OK | indistinguishable |
| 36 | `HER2_22350` | C_mixed | 8 | 0.7500 | 0.000 | 1 | 0.0645 | 0.947 | 0.909 | OK | 1 seed |
| 37 | `HER2_17485` | B_interface | 8 | 0.7217 | 0.066 | 3 | 0.0362 | 0.895 | 0.901 | OK | indistinguishable |
| 38 | `HER2_7827` | C_mixed | 8 | 0.6882 | 0.082 | 3 | 0.0027 | 0.912 | 0.890 | OK | indistinguishable |
| 39 | `HER2_11456` | B_interface | 7 | 0.6777 | 0.060 | 3 | -0.0078 | 0.947 | 0.880 | OK | indistinguishable |
| 40 | `HER2_15988` | B_interface | 8 | 0.7129 | 0.023 | 3 | 0.0274 | 0.947 | 0.897 | OK | indistinguishable |
| 41 | `HER2_1401` | B_interface | 8 | 0.6332 | 0.022 | 4 | -0.0523 | 0.974 | 0.859 | OK | below |
| 42 | `HER2_21342` | D_framework | 8 | 0.6950 | 0.087 | 3 | 0.0095 | 1.000 | 0.900 | OK | indistinguishable |
| 43 | `HER2_3536` | C_mixed | 5 | 0.7012 | 0.060 | 3 | 0.0157 | 0.860 | 0.890 | OK | indistinguishable |
| 44 | `HER2_11678` | B_interface | 7 | 0.6370 | 0.138 | 4 | -0.0485 | 0.987 | 0.871 | OK | indistinguishable |
| 45 | `HER2B_1130` | B_interface | 5 | 0.6936 | 0.073 | 2 | 0.0081 | 0.974 | 0.900 | OK | indistinguishable |
| 46 | `HER2_8798` | B_interface | 8 | 0.6887 | 0.056 | 3 | 0.0032 | 0.895 | 0.894 | OK | indistinguishable |
| 47 | `HER2B_0955` | B_interface | 5 | 0.7323 | 0.023 | 3 | 0.0468 | 0.930 | 0.901 | OK | indistinguishable |
| 48 | `HER2_19004` | C_mixed | 7 | 0.6828 | 0.050 | 3 | -0.0027 | 0.947 | 0.886 | OK | indistinguishable |
| 49 | `HER2B_1025` | B_interface | 5 | 0.6791 | 0.040 | 3 | -0.0064 | 1.000 | 0.881 | OK | indistinguishable |
| 50 | `HER2_11449` | B_interface | 5 | 0.6807 | 0.024 | 3 | -0.0048 | 0.860 | 0.884 | OK | indistinguishable |

## Lab nominations

| # | design | branch | substitutions | ipSAE | epitope | rank shift |
| ---: | --- | --- | --- | ---: | ---: | ---: |
| 1 | `HER2_11519` | C_mixed | `I29F;L181F;R201G;I210V;S212G` | 0.7131 | 1.000 | 2 |
| 2 | `HER2_8022` | B_interface | `T54G;R59Y;I70T;T155S;A160T;T166N;Y184H;R201G` | 0.7267 | 0.974 | 4 |
| 3 | `HER2_1238` | B_interface | `T32Y;N55G;A79L;A186T;T232A` | 0.7417 | 0.921 | 2 |
| 4 | `HER2_5693` | D_framework | `A79V;S97A;T157A;A169N;V193A;T209I` | 0.7258 | 0.979 | 3 |
| 5 | `HER2_13625` | C_mixed | `Q13R;N28T;Y52T;P53S;T69S;I70V;D73E;A169N` | 0.7451 | 0.947 | 2 |
| 6 | `HER2_9557` | A_h3 | `T32Y;W47Y;E89D;G101T;Y105N;Y109F;S185A;S191I` | 0.7133 | 0.968 | 7 |
| 7 | `HER2_14954` | D_framework | `F27L;T74N;S75A;G151R;I210V;Q214L` | 0.7226 | 0.974 | 18 |
| 8 | `HER2_14514` | C_mixed | `T32Y;I51V;N55E;Q82E;S119P;Q173H` | 0.7486 | 0.961 | 45 |
| 9 | `HER2_7401` | B_interface | `L20V;D62E;V64L;F104N;D163G;V164I` | 0.6648 | 0.965 | 28 |
| 10 | `HER2_11456` | B_interface | `S63P;D102S;V168L;F206Y;Q214E;T228G;P231Q` | 0.6777 | 0.947 | 34 |
| 11 | `HER2_2788` | A_h3 | `D31N;P53G;Y80S;D102S;F104S;Y105N;A169N;Q214R` | 0.6099 | 0.947 | 47 |
| 12 | `HER2_8404` | A_h3 | `I29L;T58I;Y94F;Y105N;M107L;D108E;Q225H` | 0.6442 | 0.947 | 29 |
| 13 | `HER2_9311` | A_h3 | `A92S;W99D;D102G;D108G;V168L;K177E;T228S;T232A` | 0.6299 | 0.947 | 42 |
| 14 | `HER2_1582` | A_h3 | `T54N;T74D;G101S;A106S;D163G;A167Y;A169N;K238R` | 0.5937 | 0.842 | 61 |
| 15 | `HER2_8252` | A_h3 | `A49S;S63A;V64M;I70V;G100N;D102G;F188N;P231Q` | 0.5933 | 0.789 | 57 |

`rank shift` is how far a design moves under three alternative weightings; a large value means its position depends on one metric.

## Exported binder packages

15 designs exported to `outputs/binders/<id>/` with `sequence.fasta`, `design.json`, `complex.cif`, `pae.npz`, `interface_contacts.csv` and `mutations.csv`. Rotating 3D animations are in `outputs/gifs/`.

| design | muts | modelled contacts | epitope recovery | folder |
| --- | ---: | ---: | ---: | --- |
| `HER2_13625` | 8 | 31 | 0.947 | `binders/HER2_13625` |
| `HER2_14514` | 6 | 31 | 0.923 | `binders/HER2_14514` |
| `HER2B_0955` | 5 | 28 | 0.895 | `binders/HER2B_0955` |
| `HER2_11519` | 5 | 33 | 0.983 | `binders/HER2_11519` |
| `HER2_1238` | 5 | 31 | 0.917 | `binders/HER2_1238` |
| `HER2_5693` | 6 | 29 | 0.974 | `binders/HER2_5693` |
| `HER2_15708` | 6 | 29 | 0.976 | `binders/HER2_15708` |
| `HER2_8022` | 8 | 30 | 0.957 | `binders/HER2_8022` |
| `HER2_9557` | 8 | 31 | 0.969 | `binders/HER2_9557` |
| `HER2_18461` | 5 | 30 | 0.937 | `binders/HER2_18461` |
| `HER2_15988` | 8 | 31 | 0.958 | `binders/HER2_15988` |
| `HER2_13103` | 6 | 27 | 0.822 | `binders/HER2_13103` |
| `HER2_11611` | 5 | 22 | 0.954 | `binders/HER2_11611` |
| `HER2_4995` | 8 | 29 | 0.987 | `binders/HER2_4995` |
| `HER2_1582` | 8 | 27 | 0.900 | `binders/HER2_1582` |

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

