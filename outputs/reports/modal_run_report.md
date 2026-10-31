# Modal run report - HER2 scFv optimisation

Generated 2026-10-31T15:47:14+00:00. Regenerated automatically as results arrive.

> **Claim boundary.** Every value here is a computational ranking signal for experimental triage. ipSAE is not a binding affinity, ipTM is not ipSAE, and a higher score is not a demonstrated improvement. No K_D is predicted.

## Summary

| Quantity | Value |
| --- | ---: |
| Structures scored on Modal | 1803 |
| Distinct designs | 155 |
| Parent replicates | 33 |
| Mean seeds per design | 11.42 |

Per-design mean ipSAE: n=155  min=0.0934  median=0.6418  mean=0.6055  max=0.7580

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
| sd within design (seed noise) | 0.1275 |
| sd between designs (true, est.) | 0.1286 |
| Reliability of a single seed | **0.504** |
| Reliability of the current mean | 0.908 |
| Seeds for reliability 0.8 / 0.9 | 4 / 9 |

Reliability is the share of ranking variance that is real signal rather than seed noise. This governs every comparison below: a single-seed ipSAE table is not an ordering of design quality.

### Designs tested against the parent

Parent 0.7003 +/- 0.0546 over 42 seeds; threshold |t| > 2.

- above parent: **11**
- below parent: 135
- indistinguishable: 103

## Do sequence scores predict structure?

| Predictor | vs ipSAE | vs epitope recovery | vs ipTM |
| --- | ---: | ---: | ---: |
| `ablang2_contextual` | 0.050 | -0.173 | 0.012 |
| `esm2_contextual` | -0.224 | -0.130 | -0.232 |
| `ablang2_additive_mean` | -0.427 | -0.449 | -0.465 |
| `esm2_additive_mean` | -0.410 | -0.300 | -0.432 |
| `sequence_consensus_score` | 0.051 | 0.072 | 0.025 |
| `mutation_count` | 0.102 | 0.153 | 0.086 |

Negative means a higher sequence-plausibility score goes with a **worse** modelled interface. The parent is affinity-matured, so antibody language models push its CDRs back toward germline consensus - away from the residues that contact HER2.

### By substitution count

| Group | n | ipSAE mean | sd | ipTM | epitope recovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5 | 120 | 0.5654 | 0.143 | 0.836 | 0.863 |
| 6 | 32 | 0.5869 | 0.146 | 0.844 | 0.901 |
| 7 | 31 | 0.6531 | 0.060 | 0.879 | 0.933 |
| 8 | 65 | 0.5664 | 0.127 | 0.838 | 0.890 |

### By branch

| Group | n | ipSAE mean | sd | ipTM | epitope recovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| A_h3 | 28 | 0.4748 | 0.137 | 0.795 | 0.846 |
| B_interface | 126 | 0.5624 | 0.142 | 0.834 | 0.853 |
| C_mixed | 67 | 0.6139 | 0.104 | 0.861 | 0.925 |
| D_framework | 27 | 0.6818 | 0.034 | 0.892 | 0.963 |

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

