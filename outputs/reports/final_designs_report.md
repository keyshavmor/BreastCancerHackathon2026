# Final designs report - HER2 scFv optimisation

Generated 2026-10-31T14:26:25+00:00.

> **Claim boundary.** Every value here is a computational ranking signal for experimental triage. ipSAE is not a binding affinity, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. No K_D is predicted.

## Headline

| Quantity | Value |
| --- | ---: |
| Designs with a genuine external ipSAE | **149** |
| Structures behind them | 368 |
| Local / Modal structures | 368 / 0 |
| Ranked submission set | 50 |
| Lab nominations | 15 |
| Parent replicates | 5 |
| Compliance audit | **PASS** (0 failed) |

Parent baseline: **0.6864** +/- 0.0574 over 5 seeds.

### How each design compares with the parent

| Verdict | Designs |
| --- | ---: |
| ABOVE_PARENT | 4 |
| BELOW_PARENT | 14 |
| WITHIN_SEED_NOISE | 45 |
| SINGLE_SEED_UNRELIABLE | 86 |
| NO_PARENT_BASELINE | 0 |

`SINGLE_SEED_UNRELIABLE` means the design has one replicate, which at the measured reliability cannot support a directional claim either way.

## Top 50 ranked designs

Ranked by the multi-objective score (sequence consensus, ipSAE, epitope recovery, structural confidence, developability), **not** by ipSAE alone.

| # | design | branch | muts | ipSAE | sd | n | delta vs parent | epitope | ipTM | interface | verdict |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `HER2_11519` | C_mixed | 5 | 0.7131 | 0.035 | 4 | 0.0267 | 1.000 | 0.899 | OK | indistinguishable |
| 2 | `HER2_1238` | B_interface | 5 | 0.7417 | 0.021 | 4 | 0.0553 | 0.921 | 0.908 | OK | indistinguishable |
| 3 | `HER2_8022` | B_interface | 8 | 0.7267 | 0.027 | 4 | 0.0403 | 0.974 | 0.903 | OK | indistinguishable |
| 4 | `HER2_5693` | D_framework | 6 | 0.7258 | 0.023 | 5 | 0.0394 | 0.979 | 0.900 | OK | indistinguishable |
| 5 | `HER2_13625` | C_mixed | 8 | 0.7451 | 0.012 | 4 | 0.0587 | 0.947 | 0.911 | OK | above |
| 6 | `HER2_0070` | B_interface | 5 | 0.6856 | 0.024 | 5 | -0.0008 | 0.863 | 0.884 | OK | indistinguishable |
| 7 | `HER2_17118` | C_mixed | 6 | 0.7513 | 0.035 | 4 | 0.0649 | 0.987 | 0.910 | OK | above |
| 8 | `HER2_9557` | A_h3 | 8 | 0.7133 | 0.041 | 5 | 0.0269 | 0.968 | 0.904 | OK | indistinguishable |
| 9 | `HER2_10808` | B_interface | 8 | 0.6850 | 0.039 | 4 | -0.0014 | 0.947 | 0.893 | OK | indistinguishable |
| 10 | `HER2_0077` | B_interface | 5 | 0.6484 | 0.082 | 5 | -0.0380 | 0.926 | 0.882 | OK | indistinguishable |
| 11 | `HER2_21202` | C_mixed | 6 | 0.7306 | 0.010 | 4 | 0.0442 | 0.974 | 0.906 | OK | indistinguishable |
| 12 | `HER2_17465` | D_framework | 8 | 0.7496 | 0.038 | 4 | 0.0632 | 0.947 | 0.915 | OK | indistinguishable |
| 13 | `HER2_7401` | B_interface | 6 | 0.6648 | 0.038 | 3 | -0.0216 | 0.965 | 0.882 | OK | indistinguishable |
| 14 | `HER2_14954` | D_framework | 6 | 0.7226 | 0.035 | 4 | 0.0362 | 0.974 | 0.904 | OK | indistinguishable |
| 15 | `HER2_13086` | C_mixed | 7 | 0.6961 | 0.047 | 4 | 0.0097 | 0.947 | 0.896 | OK | indistinguishable |
| 16 | `HER2_18216` | D_framework | 7 | 0.7209 | 0.046 | 3 | 0.0345 | 0.930 | 0.903 | OK | indistinguishable |
| 17 | `HER2_15708` | D_framework | 6 | 0.6682 | 0.067 | 4 | -0.0182 | 0.961 | 0.890 | OK | indistinguishable |
| 18 | `HER2_8386` | C_mixed | 5 | 0.7054 | 0.037 | 4 | 0.0190 | 0.961 | 0.893 | OK | indistinguishable |
| 19 | `HER2_15056` | B_interface | 7 | 0.6596 | 0.040 | 3 | -0.0268 | 0.965 | 0.888 | OK | indistinguishable |
| 20 | `HER2_19503` | D_framework | 6 | 0.7011 | 0.034 | 3 | 0.0147 | 1.000 | 0.894 | OK | indistinguishable |
| 21 | `HER2_8533` | D_framework | 7 | 0.6488 | 0.076 | 4 | -0.0376 | 1.000 | 0.887 | OK | indistinguishable |
| 22 | `HER2_1401` | B_interface | 8 | 0.6332 | 0.022 | 4 | -0.0532 | 0.974 | 0.859 | OK | indistinguishable |
| 23 | `HER2_2720` | C_mixed | 7 | 0.7292 | 0.039 | 3 | 0.0428 | 0.930 | 0.902 | OK | indistinguishable |
| 24 | `HER2_3536` | C_mixed | 5 | 0.7012 | 0.060 | 3 | 0.0148 | 0.860 | 0.890 | OK | indistinguishable |
| 25 | `HER2_11456` | B_interface | 7 | 0.6777 | 0.060 | 3 | -0.0087 | 0.947 | 0.880 | OK | indistinguishable |
| 26 | `HER2_14514` | C_mixed | 6 | 0.7486 | 0.013 | 4 | 0.0622 | 0.961 | 0.912 | OK | above |
| 27 | `HER2_23723` | C_mixed | 5 | 0.7349 | 0.047 | 4 | 0.0485 | 0.974 | 0.909 | OK | indistinguishable |
| 28 | `HER2_18461` | C_mixed | 5 | 0.7262 | 0.008 | 3 | 0.0398 | 0.912 | 0.906 | OK | indistinguishable |
| 29 | `HER2_11449` | B_interface | 5 | 0.6807 | 0.024 | 3 | -0.0057 | 0.860 | 0.884 | OK | indistinguishable |
| 30 | `HER2_7827` | C_mixed | 8 | 0.6882 | 0.082 | 3 | 0.0018 | 0.912 | 0.890 | OK | indistinguishable |
| 31 | `HER2_17641` | C_mixed | 8 | 0.7595 | 0.029 | 3 | 0.0731 | 0.842 | 0.914 | OK | above |
| 32 | `HER2_17485` | B_interface | 8 | 0.7217 | 0.066 | 3 | 0.0353 | 0.895 | 0.901 | OK | indistinguishable |
| 33 | `HER2_28172` | D_framework | 7 | 0.7162 | 0.043 | 3 | 0.0298 | 1.000 | 0.905 | OK | indistinguishable |
| 34 | `HER2_8798` | B_interface | 8 | 0.6887 | 0.056 | 3 | 0.0023 | 0.895 | 0.894 | OK | indistinguishable |
| 35 | `HER2_2407` | D_framework | 6 | 0.6499 | 0.000 | 1 | -0.0365 | 1.000 | 0.887 | OK | 1 seed |
| 36 | `HER2_11678` | B_interface | 7 | 0.6370 | 0.138 | 4 | -0.0494 | 0.987 | 0.871 | OK | indistinguishable |
| 37 | `HER2_26656` | C_mixed | 5 | 0.6632 | 0.081 | 4 | -0.0232 | 0.987 | 0.887 | OK | indistinguishable |
| 38 | `HER2_12026` | C_mixed | 7 | 0.6773 | 0.000 | 1 | -0.0091 | 0.895 | 0.885 | OK | 1 seed |
| 39 | `HER2_13103` | B_interface | 6 | 0.7185 | 0.000 | 1 | 0.0321 | 0.789 | 0.898 | OK | 1 seed |
| 40 | `HER2_10014` | C_mixed | 7 | 0.6940 | 0.000 | 1 | 0.0076 | 1.000 | 0.887 | OK | 1 seed |
| 41 | `HER2_12122` | C_mixed | 8 | 0.6385 | 0.000 | 1 | -0.0479 | 0.947 | 0.886 | OK | 1 seed |
| 42 | `HER2_15988` | B_interface | 8 | 0.7129 | 0.023 | 3 | 0.0265 | 0.947 | 0.897 | OK | indistinguishable |
| 43 | `HER2_11522` | A_h3 | 8 | 0.6721 | 0.000 | 1 | -0.0143 | 0.895 | 0.874 | OK | 1 seed |
| 44 | `HER2_11611` | A_h3 | 5 | 0.6471 | 0.000 | 1 | -0.0393 | 0.947 | 0.883 | OK | 1 seed |
| 45 | `HER2_14939` | C_mixed | 7 | 0.7249 | 0.009 | 3 | 0.0385 | 0.930 | 0.901 | OK | indistinguishable |
| 46 | `HER2_19004` | C_mixed | 7 | 0.6828 | 0.050 | 3 | -0.0036 | 0.947 | 0.886 | OK | indistinguishable |
| 47 | `HER2_10485` | C_mixed | 6 | 0.6458 | 0.000 | 1 | -0.0406 | 0.947 | 0.867 | OK | 1 seed |
| 48 | `HER2_3091` | B_interface | 5 | 0.6780 | 0.089 | 3 | -0.0084 | 0.895 | 0.884 | OK | indistinguishable |
| 49 | `HER2_22350` | C_mixed | 8 | 0.7500 | 0.000 | 1 | 0.0636 | 0.947 | 0.909 | OK | 1 seed |
| 50 | `HER2_1981` | A_h3 | 8 | 0.3887 | 0.000 | 1 | -0.2977 | 1.000 | 0.784 | COLLAPSED | 1 seed |

## Lab nominations

| # | design | branch | substitutions | ipSAE | epitope | rank shift |
| ---: | --- | --- | --- | ---: | ---: | ---: |
| 1 | `HER2_11519` | C_mixed | `I29F;L181F;R201G;I210V;S212G` | 0.7131 | 1.000 | 1 |
| 2 | `HER2_1238` | B_interface | `T32Y;N55G;A79L;A186T;T232A` | 0.7417 | 0.921 | 1 |
| 3 | `HER2_8022` | B_interface | `T54G;R59Y;I70T;T155S;A160T;T166N;Y184H;R201G` | 0.7267 | 0.974 | 2 |
| 4 | `HER2_5693` | D_framework | `A79V;S97A;T157A;A169N;V193A;T209I` | 0.7258 | 0.979 | 2 |
| 5 | `HER2_13625` | C_mixed | `Q13R;N28T;Y52T;P53S;T69S;I70V;D73E;A169N` | 0.7451 | 0.947 | 5 |
| 6 | `HER2_9557` | A_h3 | `T32Y;W47Y;E89D;G101T;Y105N;Y109F;S185A;S191I` | 0.7133 | 0.968 | 6 |
| 7 | `HER2_7401` | B_interface | `L20V;D62E;V64L;F104N;D163G;V164I` | 0.6648 | 0.965 | 21 |
| 8 | `HER2_14954` | D_framework | `F27L;T74N;S75A;G151R;I210V;Q214L` | 0.7226 | 0.974 | 41 |
| 9 | `HER2_3536` | C_mixed | `T32Y;T74N;S120P;S211N;P231R` | 0.7012 | 0.860 | 39 |
| 10 | `HER2_11456` | B_interface | `S63P;D102S;V168L;F206Y;Q214E;T228G;P231Q` | 0.6777 | 0.947 | 18 |
| 11 | `HER2_2788` | A_h3 | `D31N;P53G;Y80S;D102S;F104S;Y105N;A169N;Q214R` | 0.6099 | 0.947 | 27 |
| 12 | `HER2_9311` | A_h3 | `A92S;W99D;D102G;D108G;V168L;K177E;T228S;T232A` | 0.6299 | 0.947 | 26 |
| 13 | `HER2_8404` | A_h3 | `I29L;T58I;Y94F;Y105N;M107L;D108E;Q225H` | 0.6442 | 0.947 | 18 |
| 14 | `HER2_1582` | A_h3 | `T54N;T74D;G101S;A106S;D163G;A167Y;A169N;K238R` | 0.5937 | 0.842 | 56 |
| 15 | `HER2_8252` | A_h3 | `A49S;S63A;V64M;I70V;G100N;D102G;F188N;P231Q` | 0.5933 | 0.789 | 37 |

`rank shift` is how far a design moves under three alternative weightings; a large value means its position depends on one metric.

## Exported binder packages

15 designs exported to `outputs/binders/<id>/` with `sequence.fasta`, `design.json`, `complex.cif`, `pae.npz`, `interface_contacts.csv` and `mutations.csv`. Rotating 3D animations are in `outputs/gifs/`.

| design | muts | modelled contacts | epitope recovery | folder |
| --- | ---: | ---: | ---: | --- |
| `HER2_11519` | 5 | 32 | 1.000 | `binders/HER2_11519` |
| `HER2_1238` | 5 | 29 | 0.930 | `binders/HER2_1238` |
| `HER2_8022` | 8 | 29 | 0.983 | `binders/HER2_8022` |
| `HER2_5693` | 6 | 31 | 0.965 | `binders/HER2_5693` |
| `HER2_9557` | 8 | 31 | 0.965 | `binders/HER2_9557` |
| `HER2_13625` | 8 | 36 | 0.930 | `binders/HER2_13625` |
| `HER2_15708` | 6 | 27 | 0.965 | `binders/HER2_15708` |
| `HER2_14514` | 6 | 31 | 0.965 | `binders/HER2_14514` |
| `HER2_11449` | 5 | 27 | 0.868 | `binders/HER2_11449` |
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

