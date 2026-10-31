# Modal run report - HER2 scFv optimisation

Generated 2026-10-31T15:33:22+00:00. Regenerated automatically as results arrive.

> **Claim boundary.** Every value here is a computational ranking signal for experimental triage. ipSAE is not a binding affinity, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. No K_D is predicted.

## Summary

| Quantity | Value |
| --- | ---: |
| Structures scored on Modal | 1567 |
| Distinct designs | 155 |
| Parent replicates | 28 |
| Mean seeds per design | 9.93 |

Per-design mean ipSAE: n=155  min=0.0934  median=0.6381  mean=0.6047  max=0.7585

## Throughput and cost

| Phase | Purpose | Structures | Elapsed | Est. cost | State |
| --- | --- | ---: | ---: | ---: | --- |
| A | error bars on all submitted designs (7 seeds) | 1050/1050 | 47.7min | $4.83 | complete |
| B | balanced mutation-count sweep (5 seeds) | - | - | - | not started |
| C | stratified breadth with replicates (5 seeds) | - | - | - | not started |
| D | deep replication of nominees (20 seeds) | 240/240 | 16.8min | $1.10 | complete |

Structures completed on Modal so far: **1290**.

Cost is estimated at ~$0.0046 per structure (~15 s on an A10G at ~$1.10/GPU-hour); the authoritative figure is the Modal usage dashboard.

## Measurement reliability

| Quantity | Value |
| --- | ---: |
| Designs with replicates | 250 |
| sd within design (seed noise) | 0.1278 |
| sd between designs (true, est.) | 0.1277 |
| Reliability of a single seed | **0.500** |
| Reliability of the current mean | 0.897 |
| Seeds for reliability 0.8 / 0.9 | 5 / 10 |

Reliability is the share of ranking variance that is real signal rather than seed noise. This governs every comparison below: a single-seed ipSAE table is not an ordering of design quality.

### Designs tested against the parent

Parent 0.6973 +/- 0.0583 over 35 seeds; threshold |t| > 2.

- above parent: **10**
- below parent: 126
- indistinguishable: 113

## Do sequence scores predict structure?

| Predictor | vs ipSAE | vs epitope recovery | vs ipTM |
| --- | ---: | ---: | ---: |
| `ablang2_contextual` | 0.049 | -0.174 | 0.009 |
| `esm2_contextual` | -0.223 | -0.148 | -0.230 |
| `ablang2_additive_mean` | -0.432 | -0.457 | -0.468 |
| `esm2_additive_mean` | -0.408 | -0.310 | -0.432 |
| `sequence_consensus_score` | 0.051 | 0.065 | 0.025 |
| `mutation_count` | 0.103 | 0.151 | 0.089 |

Negative means a higher sequence-plausibility score goes with a **worse** modelled interface. The parent is affinity-matured, so antibody language models push its CDRs back toward germline consensus - away from the residues that contact HER2.

### By substitution count

| Group | n | ipSAE mean | sd | ipTM | epitope recovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5 | 120 | 0.5654 | 0.143 | 0.836 | 0.863 |
| 6 | 32 | 0.5858 | 0.146 | 0.844 | 0.902 |
| 7 | 31 | 0.6530 | 0.060 | 0.879 | 0.932 |
| 8 | 65 | 0.5664 | 0.127 | 0.838 | 0.891 |

### By branch

| Group | n | ipSAE mean | sd | ipTM | epitope recovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| A_h3 | 28 | 0.4747 | 0.136 | 0.795 | 0.846 |
| B_interface | 126 | 0.5627 | 0.142 | 0.834 | 0.853 |
| C_mixed | 67 | 0.6133 | 0.103 | 0.861 | 0.926 |
| D_framework | 27 | 0.6803 | 0.034 | 0.891 | 0.963 |

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

