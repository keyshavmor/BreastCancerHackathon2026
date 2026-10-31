# HER2 scFv Optimisation Pipeline

Trastuzumab-derived scFv optimisation against HER2 for the Adaptyv / Bioincubate
breast-cancer hackathon (Zurich, 2026). The pipeline proposes substitution-only
variants of an immutable 242-residue parent scFv, screens them with two
orthogonal protein language models, cofolds the survivors against **HER2 domain
IV only** with Boltz-2, and scores every submitted design with the external
DunbrackLab ipSAE implementation.

Built for a single **24 GB GPU** (validated on an RTX 3090) under a hard
four-hour wall-clock budget.

> **Claim boundary.** Every number this pipeline produces is a *ranking signal
> for experimental triage*. Nothing here measures affinity. ipSAE is not K_D,
> ipTM is not ipSAE, and a higher score is not a demonstrated improvement. The
> parent is a sub-picomolar binder (0.82 pM BLI per the organizer slide), so the
> prior that a random 5-8 substitution variant beats it is low by construction.

## Pipeline

```text
stage 1  target prep     1N8Z + UniProt P04626  ->  residue map, HER2 domain IV crop
stage 2  generation      AbLang2-guided sampling ->  40,000 valid candidates -> 4,000 shortlist
stage 3  rerank          ESM2-3B                 ->  internal 50 + 150-entry cofold queue
stage 4  cofold          Boltz-2, cached MSAs    ->  structures + full PAE
stage 5  ipSAE           DunbrackLab/IPSAE       ->  real ipSAE + epitope-recovery QC
stage 6  select & audit  multi-objective ranking ->  submission_scored.*, top_15_scored.*
```

Run everything:

```bash
bash scripts/run_her2_pipeline.sh          # production
SMOKE=1 bash scripts/run_her2_pipeline.sh  # tiny end-to-end check
FROM=4 bash scripts/run_her2_pipeline.sh   # resume from cofolding
```

See [envs/README.md](envs/README.md) for environment setup and
[docs/USER_GUIDE.md](docs/USER_GUIDE.md) for stage-by-stage options.

## Measured throughput on one RTX 3090

All figures measured on this machine, not estimated.

| Stage | Cost | Peak VRAM | Notes |
| --- | --- | --- | --- |
| AbLang2 masked site scan | **0.7 s** / 217 positions | ~1 GB | one-time, pool-size independent |
| AbLang2 generation | **42 s** / 40,000 candidates | ~1 GB | CPU-bound filtering |
| ESM2-3B load | 24-32 s | 10.7 GiB (bf16) | weights cached locally |
| ESM2-3B masked scan | **6.8 s** / 223 positions | 10.7 GiB | one-time |
| ESM2-3B contextual | **62 ms** / candidate | 10.7 GiB | 4,000 in ~2 min |
| MSA server (one-shot) | **103 s** total | - | once, then cached forever |
| Boltz-2 cofold | **~14.8 s** / structure | ~19 GiB | 361-res complex, cached MSA |
| ipSAE | ~1-2 s / structure | CPU | 6 workers in parallel |

### Why this is fast

1. **Domain IV only.** 242 + 119 = **361 residues** instead of ~849 for the full
   ectodomain. Also an organizer requirement, not just an optimisation.
2. **One MSA, reused.** The ColabFold server costs ~103 s per target and is
   rate-limited. We call it **once** for the parent and reuse both alignments for
   every candidate, rewriting only the query row. Over 150 designs that is
   ~50 minutes of GPU work instead of **~6.3 hours** of mostly idle waiting - and
   it makes every design's MSA condition byte-identical, so parent-relative
   comparisons are matched by construction.
3. **Masked site scans instead of per-candidate model calls.** Both language
   models are run once over the mutable positions to build a
   `position x amino-acid` Δlog-P table; scoring a candidate is then a table
   lookup. This is what makes a 40,000-candidate pool essentially free, and it
   is why the Catalyst-style "1M sequences" funnel is not the right shape here:
   under an additive objective a huge pool buys *diversity coverage*, not better
   scores.
4. **Batched Boltz invocation.** One `boltz predict` over a directory of 25 YAMLs
   pays the ~25 s model load once rather than per structure.
5. **One GPU model at a time.** ESM2-3B (10.7 GiB) and Boltz-2 (19 GiB) are never
   co-resident; 19 GiB peak also means **do not** run two Boltz jobs on a 24 GB card.

## The immutable parent

```text
EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYIHWVRQAPGKGLEWVARIYPTNGYTRYADSVKGRFTISADTSKNTAYLQMNSLRAEDTAVYYCSRWGGDGFYAMDYWGQGTLVTVSSGGGGSGGGGSGGGGSDIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSRSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK
```

Verified programmatically at the start of every stage, never trusted from a
document:

| Property | Value |
| --- | --- |
| Length | 242 |
| SHA-256 | `0b9248c76a2b399791c47dbfa0d252b18284265f1dbca9ae8e66c0dd018c9f64` |
| V_H / linker / V_L | 1-120 / 121-135 `(GGGGS)x3` / 136-242 |
| Native cysteines | 22, 96, 158, 223 |
| N-glyc sequons | 0 (so any new sequon is a clean rejection) |

CDRs are located by **motif match**, not hard-coded indices, so a changed parent
can never leave the CDR table silently pointing at the wrong residues:

| CDR | Span | Sequence |
| --- | --- | --- |
| CDR-H1 | 31-35 | `DTYIH` |
| CDR-H2 | 50-66 | `RIYPTNGYTRYADSVKG` |
| CDR-H3 | 99-109 | `WGGDGFYAMDY` |
| CDR-L1 | 159-169 | `RASQDVNTAVA` |
| CDR-L2 | 185-191 | `SASFLYS` |
| CDR-L3 | 224-232 | `QQHYTTPPT` |

## Target: HER2 domain IV, derived not assumed

`stage1_target_prep.py` works from primary data (RCSB `1N8Z`, UniProt `P04626`)
and refuses to proceed if any invariant fails.

- 1N8Z chain **A** = Fab light, **B** = Fab heavy, **C** = HER2 ectodomain.
- Chain C uses HER2 **mature** numbering: `uniprot = mature + 22`.
- **V_H and V_L match 1N8Z chains B/A with zero mismatches**, so the organizer
  parent is residue-for-residue identical to the crystallographic variable
  domains and the structural priors transfer directly.
- Crop: **mature 489-607** (UniProt 511-629), **119 aa**, cross-checked against
  P04626. All **8** domain-IV disulfides are fully inside and **none is split**
  (validated against `SSBOND` records). All **37** Fab-contacting HER2 residues
  (mature 532-607) are retained.
- Paratope: **20 direct** (≤4.5 Å) and **21 near** (4.5-8 Å) scFv residues,
  spread across all six CDRs.

### Mutation policy

Conservative by design, because the parent is already sub-picomolar.

- Fixed length 242, substitution-only, **5-8** substitutions (organizer minimum
  is 5; the upper bound is our own choice).
- Linker and native cysteines frozen; **no new cysteines**; **no new N-X-S/T**
  sequons.
- **Tight-contact anchors frozen**, derived from geometry rather than guessed:
  any residue within 3.0 Å of HER2 - here `R50, G103, N165, H226, Y227, T229`.
  These most plausibly carry the sub-pM binding energy.

Four branches sample distinct mechanistic hypotheses rather than 50 neighbours
of one motif:

| Branch | Slots | Hypothesis |
| --- | --- | --- |
| `A_h3` | 20 | focused CDR-H3 maturation (strongest published evidence) |
| `B_interface` | 12 | non-H3 paratope / contact-adjacent |
| `C_mixed` | 10 | a few paratope edits plus framework support |
| `D_framework` | 8 | framework-biased control retaining all anchors |

## Scoring and selection

Four signals, deliberately orthogonal:

| Signal | What it knows | What it cannot do |
| --- | --- | --- |
| AbLang2-paired | antibody sequence plausibility | never sees HER2 |
| ESM2-3B | general protein plausibility | never sees HER2 |
| Boltz-2 + ipSAE | modelled interface confidence | not calibrated to K_D |
| Epitope recovery | did it bind the *experimental* face | geometric, not energetic |

Selection is **not** "sort by ipSAE". Ranking aggregates *percentile ranks*
across five axes (sequence consensus 0.30, ipSAE 0.25, epitope recovery 0.20,
structural confidence 0.15, developability 0.10), then allocates the top 15 under
branch quotas with farthest-point diversity selection.

Because those weights are a hypothesis and not a fitted model, stage 6 re-ranks
under three alternative weightings and reports each design's
`max_rank_shift_under_reweighting`, so a nominee that depends on one metric is
visible as such.

**Seed noise gate.** Replicate seeds give a pooled ipSAE standard deviation; any
design whose ipSAE advantage over the parent is smaller than that noise is
labelled `WITHIN_SEED_NOISE` rather than reported as an improvement.

**Epitope gate.** A model recovering <30% of the experimental epitope is binding
the wrong surface, and its interface scores are not trusted regardless of ipSAE.

## Deliverables

Written to `outputs/`. The distinction is strict and non-negotiable:

| File | Contents |
| --- | --- |
| `internal_50_candidates.*` | 50 curated proposals; ipSAE may be `NOT_EVALUATED` |
| `submission_scored.*` | **only** designs with real structure + full PAE + real ipSAE |
| `top_15_scored.*` | diverse, ranked lab nominations drawn from the scored set |
| `ipSAE_provenance.csv` | script commit, cutoffs, chain order, artifact paths per design |
| `compliance_audit.json` | PASS/FAIL/NOT_EVALUATED from real files |
| `run_manifest.json` | commit, weights, counts, claim boundary |
| `contract.yaml` / `residue_map.csv` | frozen rules; per-residue mapping and geometry |
| `target_prep_report.md` | derivation of the domain IV crop with caveats |

A design never appears in `submission_scored.*` without a finite, externally
computed ipSAE backed by saved artifacts. No value is estimated or carried over.

## Repository layout

```text
scripts/
  her2_common.py              frozen parent, validator, mutation utilities
  stage1_target_prep.py       1N8Z/P04626 -> residue map + domain IV crop
  stage2_generate_candidates.py  AbLang2 generation
  stage3_esm_rerank.py        ESM2-3B rerank + portfolio freeze
  stage4_boltz_cofold.py      Boltz-2 cofolding with MSA reuse
  stage5_score_ipsae.py       external ipSAE + epitope QC
  stage6_select_audit.py      selection, audit, packaging
  bootstrap_msa_cache.py      the single MSA-server call
  run_her2_pipeline.sh        orchestrator
envs/                         conda specs + setup gotchas
inputs/organizer_parent_scfv.fasta
reference_data/               1N8Z.pdb/.cif, P04626 (downloaded, checksummed)
third_party/IPSAE/            DunbrackLab ipSAE (vendored, pinned commit)
outputs/                      deliverables
pipeline_runs/                Boltz run directories (git-ignored)
docs/                         user guide, method walkthrough
```

## Verified parent baseline (Gate B)

The parent cofold against the domain IV crop, used as the matched reference for
every candidate:

| Metric | Value |
| --- | --- |
| Boltz confidence | 0.927 |
| ipTM | 0.895 |
| complex pLDDT | 0.935 |
| ipSAE (B→T) | 0.684 |
| ipSAE (T→B) | 0.832 |
| pDockQ / pDockQ2 / LIS | 0.492 / 0.717 / 0.651 |

ipSAE cutoffs: `pae_cutoff=10`, `dist_cutoff=15`;
`ipsae_min = min(asym B→T, asym T→B)`.

## Scope compliance

- Boltz-2 is used **only** to predict the structure of an already-edited
  antibody sequence, after sequence screening.
- **No** de novo binder generation: no RFdiffusion, BindCraft, BoltzGen or Mosaic.
- **Never** cofolds the full ~630-residue HER2 ectodomain.
- No linker or native-cysteine edits; every design ≥5 substitutions, ≤260 aa.
- Boltz-2's small-molecule affinity head is **not** used; it is not a calibrated
  antibody-HER2 K_D estimator.

## Acknowledgements

- Boltz-2 (MIT) - structure prediction
- [DunbrackLab/IPSAE](https://github.com/DunbrackLab/IPSAE) - ipSAE, pDockQ, LIS
- AbLang2 (Olsen et al.) - antibody language model
- ESM2 (Lin et al., Meta AI) - general protein language model
- ColabFold / MMseqs2 MSA server
- RCSB PDB `1N8Z` (Cho et al., 2003) and UniProt `P04626`
