# Modal run report - HER2 scFv optimisation

Generated 2026-10-31T15:11:47+00:00. Regenerated automatically as results arrive.

> **Claim boundary.** Every value here is a computational ranking signal for experimental triage. ipSAE is not a binding affinity, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. No K_D is predicted.

## Summary

| Quantity | Value |
| --- | ---: |
| Structures scored on Modal | 0 |
| Distinct designs | 0 |
| Parent replicates | 0 |
| Mean seeds per design | 0.00 |

## Throughput and cost

| Phase | Purpose | Structures | Elapsed | Est. cost | State |
| --- | --- | ---: | ---: | ---: | --- |
| A | error bars on all submitted designs (7 seeds) | 1050/1050 | 47.7min | $4.83 | complete |
| B | balanced mutation-count sweep (5 seeds) | - | - | - | not started |
| C | stratified breadth with replicates (5 seeds) | - | - | - | not started |
| D | deep replication of nominees (20 seeds) | 216/240 | 13.0min | $0.99 | running |

Structures completed on Modal so far: **1266**.

Cost is estimated at ~$0.0046 per structure (~15 s on an A10G at ~$1.10/GPU-hour); the authoritative figure is the Modal usage dashboard.

## Measurement reliability

| Quantity | Value |
| --- | ---: |
| Designs with replicates | 164 |
| sd within design (seed noise) | 0.1109 |
| sd between designs (true, est.) | 0.1310 |
| Reliability of a single seed | **0.583** |
| Reliability of the current mean | 0.799 |
| Seeds for reliability 0.8 / 0.9 | 3 / 7 |

Reliability is the share of ranking variance that is real signal rather than seed noise. This governs every comparison below: a single-seed ipSAE table is not an ordering of design quality.

### Designs tested against the parent

Parent 0.6855 +/- 0.0595 over 7 seeds; threshold |t| > 2.

- above parent: **7**
- below parent: 46
- indistinguishable: 110

## Do sequence scores predict structure?

| Predictor | vs ipSAE | vs epitope recovery | vs ipTM |
| --- | ---: | ---: | ---: |
| `ablang2_contextual` | 0.103 | -0.103 | 0.076 |
| `esm2_contextual` | -0.218 | -0.057 | -0.217 |
| `ablang2_additive_mean` | -0.300 | -0.355 | -0.330 |
| `esm2_additive_mean` | -0.320 | -0.233 | -0.348 |
| `sequence_consensus_score` | 0.019 | 0.152 | 0.000 |
| `mutation_count` | 0.048 | 0.229 | 0.038 |

Negative means a higher sequence-plausibility score goes with a **worse** modelled interface. The parent is affinity-matured, so antibody language models push its CDRs back toward germline consensus - away from the residues that contact HER2.

### By substitution count

| Group | n | ipSAE mean | sd | ipTM | epitope recovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5 | 120 | 0.5731 | 0.148 | 0.842 | 0.874 |
| 6 | 32 | 0.5614 | 0.206 | 0.821 | 0.897 |
| 7 | 31 | 0.6427 | 0.073 | 0.876 | 0.945 |
| 8 | 65 | 0.5685 | 0.131 | 0.844 | 0.914 |

### By branch

| Group | n | ipSAE mean | sd | ipTM | epitope recovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| A_h3 | 28 | 0.4813 | 0.163 | 0.796 | 0.863 |
| B_interface | 126 | 0.5734 | 0.148 | 0.841 | 0.866 |
| C_mixed | 67 | 0.6047 | 0.139 | 0.855 | 0.936 |
| D_framework | 27 | 0.6434 | 0.076 | 0.879 | 0.971 |

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

