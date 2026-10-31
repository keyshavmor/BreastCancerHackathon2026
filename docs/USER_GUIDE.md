# User guide

Stage-by-stage reference for the HER2 scFv optimisation pipeline. For setup see
[../envs/README.md](../envs/README.md); for the scientific rationale see
[../README.md](../README.md).

## Before you start

```bash
source ~/anaconda3/bin/activate
conda env create -f envs/her2_seq.yml
conda env create -f envs/her2_boltz2.yml

# vendored ipSAE implementation (not committed)
git clone --depth 1 https://github.com/DunbrackLab/IPSAE.git third_party/IPSAE
```

Confirm the GPU is free. Boltz-2 peaks at ~19 GiB on a 361-residue complex, so
on a 24 GB card nothing else substantial can be resident:

```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
```

## One-command run

```bash
bash scripts/run_her2_pipeline.sh
```

Environment-variable overrides (all optional):

| Variable | Default | Meaning |
| --- | --- | --- |
| `POOL` | 40000 | raw AbLang2 proposals sampled |
| `SHORTLIST` | 4000 | candidates handed to ESM2-3B |
| `QUEUE` | 150 | total cofold queue length |
| `INTERNAL` | 50 | curated internal proposal pool |
| `TOPN` | 15 | lab nominations |
| `SEEDS` | 42,7,13 | first is the main pass; the rest are replicates |
| `REPLICATE_TOP` | 20 | how many top designs get replicate seeds |
| `BATCH` | 25 | YAMLs per `boltz predict` call |
| `MSA_MODE` | retarget | `retarget` \| `share` \| `empty` |
| `TIME_BUDGET_MIN` | 80 | stop launching new Boltz batches after this |
| `FROM` | 1 | resume from this stage |
| `SMOKE` | 0 | `1` runs a tiny end-to-end check |

```bash
SMOKE=1 bash scripts/run_her2_pipeline.sh            # ~5 min sanity check
QUEUE=50 REPLICATE_TOP=0 bash scripts/run_her2_pipeline.sh
FROM=5 bash scripts/run_her2_pipeline.sh             # rescore existing structures
```

All stages are idempotent. Stage 4 treats any prediction that already has both a
structure and a PAE file as complete, so an interrupted campaign resumes without
repeating finished work.

## Stage reference

### Stage 0 - invariants

```bash
conda run -n her2_seq python scripts/her2_common.py
```

Prints the parent's length, SHA-256, cysteine positions, CDR spans and native
liability counts. Every other stage calls `assert_parent_integrity()` on import,
so a corrupted parent aborts the run rather than silently producing designs
against the wrong scaffold.

### Stage 1 - target preparation

```bash
conda run -n her2_seq python scripts/stage1_target_prep.py --outdir outputs
```

Downloads nothing itself — place `1N8Z.pdb`, `1N8Z.cif` and `P04626.fasta` in
`reference_data/` first:

```bash
cd reference_data
curl -O https://files.rcsb.org/download/1N8Z.pdb
curl -O https://files.rcsb.org/download/1N8Z.cif
curl -o P04626.fasta "https://rest.uniprot.org/uniprotkb/P04626.fasta"
```

Key options: `--domain-iv-start` / `--domain-iv-end` (mature numbering, default
489-607), `--pdb`, `--uniprot`.

**Outputs:** `residue_map.csv`, `her2_domain_iv.fasta`, `contract.yaml`,
`contract.json`, `target_prep_report.md`.

The stage **refuses to write a target** if the crop would split a disulfide or
exclude a Fab-contacting residue, or if the PDB SEQRES and UniProt disagree.
Those are hard exits, not warnings.

### Stage 2 - candidate generation

```bash
conda run -n her2_seq python scripts/stage2_generate_candidates.py \
  --pool-size 40000 --shortlist 4000
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--pool-size` | 6000 | raw proposals sampled across four branches |
| `--shortlist` | 600 | diverse subset for ESM2 |
| `--top-k` | 5 | substitutions kept per position |
| `--anchor-cutoff` | 3.0 | freeze residues closer than this (Å) to HER2 |
| `--min-mut` / `--max-mut` | 5 / 8 | substitution band |
| `--seed` | 20261031 | reproducible sampling |

**Outputs:** `mutation_site_prior.csv`, `all_candidates.csv`,
`esm_shortlist.{csv,fasta}`, `internal_50_candidates_provisional.*`,
`stage2_manifest.json`.

The provisional 50 is a **stop-loss artifact**: a valid 50-proposal pool exists
from this point on even if every later stage fails. Its ipSAE column is
deliberately `NOT_EVALUATED`.

Raising `--pool-size` is nearly free (the AbLang2 scan is one-time), but note
that under an additive objective a larger pool buys diversity coverage, not
better top-ranked scores.

### Stage 3 - ESM2-3B rerank

```bash
conda run -n her2_seq python scripts/stage3_esm_rerank.py \
  --max-candidates 4000 --queue-size 150 --batch-size 8
```

Run `--benchmark-only` first on unfamiliar hardware; it times 10 sequences,
reports projected cost and peak VRAM, then exits.

| Option | Default | Meaning |
| --- | --- | --- |
| `--max-candidates` | 5000 | cap on candidates scored |
| `--queue-size` | 150 | total cofold queue length |
| `--internal-pool` | 50 | curated proposal pool size |
| `--priority` | 15 | priority tier (must complete) |
| `--batch-size` | 8 | sequences per forward pass |
| `--fp32` | off | disable bf16 (slower, ~2x memory) |
| `--control-fp32-subset` | 12 | candidates rescored in fp32 to check bf16 numerics |

**Outputs:** `esm2_site_prior.csv`, `model_scores.csv`,
`internal_50_candidates.{csv,fasta}`, `priority_cofold_queue.csv`,
`stage3_manifest.json`.

The bf16/fp32 control is reported in `stage3_manifest.json`. Observed here:
max |Δ| ≈ 0.13-0.19, mean ≈ 0.04-0.05 log-prob units, no NaNs — acceptable for
*ranking*. If you need absolute scores, use `--fp32`.

`priority_cofold_queue.csv` is tiered so Boltz can be stopped at any point:
`priority_15` → `internal_50` → `extended`.

### Stage 4 - Boltz-2 cofolding

```bash
# once per machine: the single MSA-server call
conda run -n her2_boltz2 python scripts/bootstrap_msa_cache.py --outdir outputs

conda run -n her2_boltz2 python scripts/stage4_boltz_cofold.py \
  --limit 150 --batch-size 25 --seeds 42,7,13 --replicate-top 20
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--limit` | 50 | candidates to cofold, in queue order |
| `--batch-size` | 10 | YAMLs per boltz call (amortises ~25 s model load) |
| `--seeds` | 42 | comma-separated; first is the main pass |
| `--replicate-top` | 0 | re-run the top N under every extra seed |
| `--msa-mode` | retarget | see below |
| `--sampling-steps` | 200 | 100 is ~15% faster with modest quality loss |
| `--recycling-steps` | 3 | |
| `--diffusion-samples` | 1 | |
| `--time-budget-min` | 0 | stop launching batches after N minutes |
| `--no-kernels` | off | bypass cuEquivariance (slower, no extra dependency) |
| `--skip-parent` | off | omit the parent baseline (not recommended) |

**MSA modes.** `retarget` (default) copies the cached binder alignment per
candidate and rewrites only the query row — exact for substitution-only variants,
costs ~4 MB per design. `share` reuses the parent alignment verbatim with zero
extra storage. `empty` runs single-sequence mode: faster, lower confidence, and
**must** be applied to the parent too so the comparison stays matched.

**Outputs:** `pipeline_runs/<run>/out/boltz_results_*/predictions/<name>/` with
`<name>_model_0.cif`, `pae_<name>_model_0.npz`,
`confidence_<name>_model_0.json`; plus `stage4_manifest.json`, `stage4_runs.csv`.

Housekeeping — the per-candidate MSAs are regenerable:

```bash
rm -rf pipeline_runs/*/msa_per_candidate
```

### Stage 5 - ipSAE scoring

```bash
conda run -n her2_boltz2 python scripts/stage5_score_ipsae.py \
  --run-dir pipeline_runs/her2_cofold --outdir outputs
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--pae-cutoff` | 10.0 | ipSAE PAE cutoff (Å) |
| `--dist-cutoff` | 15.0 | ipSAE distance cutoff (Å) |
| `--workers` | 6 | parallel ipSAE processes |

**Outputs:** `boltz_results_raw.csv` (per prediction),
`ipsae_aggregated.csv` (per candidate, replicates aggregated),
`ipSAE_provenance.csv`, `stage5_manifest.json`.

`ipsae_min = min(asym B→T, asym T→B)` is the primary conservative metric.
`epitope_recovery` is the fraction of experimentally observed 1N8Z epitope
residues still contacted in the model — the check that catches a confident model
binding the wrong face, which ipSAE alone cannot detect.

Any prediction with a missing or unreadable PAE, a failed ipSAE run, or a
PAE/structure mismatch is recorded with a non-`PASSED` status and excluded
downstream. Nothing is proxied.

### Stage 6 - selection and audit

```bash
conda run -n her2_seq python scripts/stage6_select_audit.py --top-n 15
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--top-n` | 15 | lab nominations |
| `--min-epitope-recovery` | 0.30 | below this, interface scores are not trusted |

**Outputs:** `submission_scored.{csv,fasta}`, `top_15_scored.{csv,fasta}`,
`excluded_from_submission.csv`, `compliance_audit.json`, `run_manifest.json`.

Read `compliance_audit.json` first. `overall` is `PASS` only if every check
passes; each entry is `PASS` / `FAIL` / `NOT_EVALUATED` computed from real files.

Columns worth reading before nominating anything:

- `ipsae_interpretation` — `ABOVE_PARENT`, `BELOW_PARENT`, or
  `WITHIN_SEED_NOISE`. Treat the last as "no detected difference".
- `max_rank_shift_under_reweighting` — how far the design moves under three
  alternative weightings. A large shift means its rank depends on one metric.
- `model_disagreement` — AbLang2 and ESM2 disagreeing. Not a penalty; a flag
  that this design needs structural evidence to adjudicate.
- `epitope_recovery` — compare against the parent's value, not an absolute bar.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `ModuleNotFoundError: cuequivariance_torch` | Boltz-2 does not declare it. Install the matching `cuequivariance-ops-torch-cuXX`, or pass `--no-kernels`. |
| `QT_XCB_GL_INTEGRATION: unbound variable` | A `set -u` script sourcing conda's activate hook. Drop `-u`. |
| `import esm` gives ESM3 classes, or AbLang2 breaks | `fair-esm` and the ESM3 SDK both own the `esm` package. Separate environments. |
| Boltz CUDA OOM | Something else is on the GPU, or two Boltz jobs are running. 19 GiB peak leaves no room on a 24 GB card. |
| MSA server `PENDING` for a long time | Rate limiting. The bootstrap is the only call; if it fails, use `--msa-mode empty` for parent *and* candidates. |
| Stage 4 reports `complete=0/N` with `rc=0` | Output-path mismatch. Boltz names results after the *input directory*; `is_complete()` globs `boltz_results_*/predictions/<name>`. |
| Stage 6: "no ipSAE-complete candidates" | Stage 5 found no `PASSED` predictions. Check `boltz_results_raw.csv` statuses and the ipSAE stdout logs. |
| Generation very slow | Diversity selection is bounded by `pool_cap`; confirm you are on a build that includes the incremental farthest-point selection. |

## Extending the pipeline

**A third sequence prior (ESM-C / ESM3).** Keep the EvolutionaryScale SDK in its
own environment (`her2_esm3`) and add its percentile rank as a fourth axis in
`stage6_select_audit.py`'s `axes` dict, adjusting `PRIMARY_WEIGHTS`. Treat it as
another plausibility prior: like AbLang2 and ESM2 it never sees HER2.

**More replicate seeds.** Raising `--seeds` and `--replicate-top` tightens the
seed-noise estimate, which is what decides whether an ipSAE delta is real.
At ~15 s per structure this is usually the best marginal use of GPU time.

**Changing the mutation policy.** Edit the constants in `her2_common.py`
(`MAX_MUTATIONS_POLICY`, liability patterns) and the branch recipes in
`stage2_generate_candidates.py`. Do not relax the organizer rules: the validator
is intentionally fail-closed, and stage 6 re-checks every submitted sequence
independently of the stage that generated it.
