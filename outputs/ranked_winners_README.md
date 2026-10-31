# ranked_winners.csv

Generated 2026-10-31T15:54:49+00:00 - 50 designs in final rank order.

Every row is a compliant scFv variant of the trastuzumab parent with a genuine,
externally computed ipSAE. Columns read left to right as identity, sequence and
mutations, the ipSAE evidence with its uncertainty, supporting structural
metrics, sequence-model priors, and selection provenance.

## Reading the statistics

| Column | Meaning |
| --- | --- |
| `ipsae_min_mean` | mean of `min(asym B->T, asym T->B)` across replicate seeds |
| `ipsae_n_seeds` | how many independent Boltz-2 seeds back that mean |
| `ipsae_ci95_low/high` | 95% interval on the mean (normal approximation) |
| `delta_vs_parent` | mean minus the parent's mean, same protocol throughout |
| `welch_t` | Welch t-statistic against the parent's own replicates |
| `q_value_BH` | Benjamini-Hochberg q across all tested designs |
| `verdict_vs_parent` | `ABOVE_PARENT_FDR` only when q < 0.05 |

**Why the q-value matters.** Roughly 250 designs were tested. At an uncorrected
alpha of 0.05 about a dozen would clear `|t| > 2` by chance alone, so an
uncorrected "above parent" count is not evidence. Only `ABOVE_PARENT_FDR`
survives correction.

**Claim boundary.** ipSAE is interface confidence from a structure predictor, not
a binding affinity. A higher ipSAE is not a demonstrated improvement in K_D, and
no K_D is predicted anywhere in this work. The parent is ~0.82 pM; the wet-lab
assay decides.

## Hard constraints, verified for every row

- exactly 242 aa, substitution-only, >= 5 substitutions vs the parent
- `(GGGGS)x3` linker intact at 121-135
- native cysteines preserved at 22/96/158/223, no new cysteines
- no newly introduced N-X-S/T glycosylation sequons
- reconstructible by applying `mutations_1based` to the frozen parent
