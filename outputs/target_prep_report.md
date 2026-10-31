# Stage 1 - HER2 target preparation report

Generated 2026-10-31T13:02:28.015804+00:00

## Parent

- 242 aa, SHA-256 `0b9248c76a2b399791c47dbfa0d252b18284265f1dbca9ae8e66c0dd018c9f64` (verified, not copied)
- V_H 1-120, linker 121-135 `(GGGGS)x3`, V_L 136-242
- native cysteines [22, 96, 158, 223]; parent carries 0 N-glyc sequons
- V_H vs 1N8Z chain B: 0 mismatches; V_L vs chain A: 0 mismatches

## CDRs (Kabat, located by motif match)

| CDR | span | sequence |
| --- | --- | --- |
| CDR-H1 | 31-35 | `DTYIH` |
| CDR-H2 | 50-66 | `RIYPTNGYTRYADSVKG` |
| CDR-H3 | 99-109 | `WGGDGFYAMDY` |
| CDR-L1 | 159-169 | `RASQDVNTAVA` |
| CDR-L2 | 185-191 | `SASFLYS` |
| CDR-L3 | 224-232 | `QQHYTTPPT` |

## HER2 domain IV crop

- mature **489-607** = UniProt 511-629 (119 aa)
- 8 disulfides fully inside, **0 split** (checked against SSBOND records)
- all 37 Fab-contacting HER2 residues (mature 532-607) retained
- Boltz complex size: 242 + 119 = **361 residues** (vs ~849 for the full ectodomain)

```
CHQLCARGHCWGPGPTQCVNCSQFLRGQECVEECRVLQGLPREYVNARHCLPCHPECQPQNGSVTCFGPEADQCVACAHYKDPPFCVARCPSGVKPDLSYMPIWKFPDEEGACQPCPIN
```

## Paratope (scFv residues near HER2)

- direct (<= 4.5 A): 20 residues
- near (4.5-8.0 A): 21 residues

| scFv pos | aa | domain | CDR | min dist (A) |
| --- | --- | --- | --- | --- |
| 33 | Y | VH | CDR-H1 | 3.42 |
| 50 | R | VH | CDR-H2 | 2.6 |
| 52 | Y | VH | CDR-H2 | 4.39 |
| 57 | Y | VH | CDR-H2 | 3.51 |
| 58 | T | VH | CDR-H2 | 4.11 |
| 59 | R | VH | CDR-H2 | 3.43 |
| 99 | W | VH | CDR-H3 | 4.05 |
| 103 | G | VH | CDR-H3 | 2.42 |
| 104 | F | VH | CDR-H3 | 4.27 |
| 105 | Y | VH | CDR-H3 | 3.32 |
| 163 | D | VL | CDR-L1 | 4.5 |
| 165 | N | VL | CDR-L1 | 2.99 |
| 166 | T | VL | CDR-L1 | 3.05 |
| 167 | A | VL | CDR-L1 | 3.69 |
| 185 | S | VL | CDR-L2 | 3.61 |
| 188 | F | VL | CDR-L2 | 3.56 |
| 226 | H | VL | CDR-L3 | 2.89 |
| 227 | Y | VL | CDR-L3 | 2.96 |
| 228 | T | VL | CDR-L3 | 4.05 |
| 229 | T | VL | CDR-L3 | 2.82 |

## Caveats

- Cropping removes receptor context and creates artificial termini; the **same crop**
  is used for the parent and every candidate so comparisons stay matched.
- Glycans present in the crystal are not modelled in the cofold.
- Distance bins are geometric, not calibrated affinity predictors.
