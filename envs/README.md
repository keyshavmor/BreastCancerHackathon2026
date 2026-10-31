# Environment setup

Two conda environments run the pipeline. They are split because of a hard
package conflict, not for tidiness.

| Env | Stages | Key packages | Peak VRAM |
| --- | --- | --- | --- |
| `her2_seq` | 1, 2, 3 | `ablang2`, `fair-esm`, `torch` | ~10.7 GiB (ESM2-3B bf16) |
| `her2_boltz2` | 4, 5 | `boltz==2.2.1`, `cuequivariance-*` | ~19 GiB (361-res complex) |

Optional third env for orthogonal ESM3/ESM-C scoring: see
[ESM3 / ESM-C](#esm3--esm-c-optional-orthogonal-scoring) below.

## Quick start

```bash
source ~/anaconda3/bin/activate

conda env create -f envs/her2_seq.yml
conda env create -f envs/her2_boltz2.yml

# verify
conda run -n her2_seq python -c "import torch,esm,ablang2; print(torch.__version__, torch.cuda.is_available())"
conda run -n her2_boltz2 boltz --help
conda run -n her2_boltz2 python -c "import cuequivariance_torch; print('kernels ok')"
```

`envs/her2_seq_full.yml` and `envs/her2_boltz2_full.yml` are exact
`conda env export` snapshots of the validated machine. Use them to reproduce
bit-for-bit; use the curated YAMLs above on different hardware, because the full
exports pin CUDA wheels that will not resolve against a different driver.

## Three gotchas that cost real time

### 1. `fair-esm` and `esm` (ESM3 SDK) collide

Both install a top-level package named `esm`. Installing one over the other
silently breaks imports. Keep them in separate environments. If you cloned an
existing ESM3 env to build `her2_seq`, uninstall the ESM3 SDK first:

```bash
conda create -y --clone <esm3_env> -n her2_seq   # hardlinks torch, ~0 extra disk
conda run -n her2_seq pip uninstall -y esm
conda run -n her2_seq pip install fair-esm==2.0.0 ablang2==0.2.1
```

This is how `her2_seq` was built here, and it avoids re-downloading ~3 GB of
torch + CUDA wheels.

### 2. Boltz-2 needs cuEquivariance but does not declare it

`pip install boltz==2.2.1` succeeds, then prediction fails with:

```
ModuleNotFoundError: No module named 'cuequivariance_torch'
```

Install wheels whose CUDA major version matches your torch build
(`cuequivariance-ops-torch-cu13` for torch `cu13x`, `-cu12` for `cu12x`):

```bash
conda run -n her2_boltz2 pip install \
  cuequivariance==0.13.0 cuequivariance-torch==0.13.0 cuequivariance-ops-torch-cu13==0.13.0
```

Or bypass the kernels entirely with `--no-kernels` on `stage4_boltz_cofold.py`
(slower, but no extra dependency).

### 3. `set -u` breaks `conda activate`

Anaconda's `etc/conda/activate.d/qt-main_activate.sh` references
`QT_XCB_GL_INTEGRATION` unguarded. Any setup script using `set -euo pipefail`
will abort on `source ~/anaconda3/bin/activate`. Drop `-u`.

## Model weights and caches

Nothing is committed to git. Expect these downloads on a fresh machine:

| Artifact | Size | Location | Trigger |
| --- | --- | --- | --- |
| ESM2-3B (`esm2_t36_3B_UR50D`) | 5.3 GB | `$TORCH_HOME/hub/checkpoints` | first stage 3 run |
| AbLang2 paired weights | ~80 MB | `~/.ablang2` | first stage 2 run |
| Boltz-2 weights + CCD cache | ~3.0 GB | `$BOLTZ_CACHE` or `~/.boltz` | first stage 4 run |
| HER2/scFv MSAs | ~5 MB | `outputs/msa_cache/` | one `--use_msa_server` run |

Total ~8.5 GB. Set `BOLTZ_CACHE` to relocate the largest item.

### Storage housekeeping

Stage 4 writes one retargeted MSA per candidate (~4 MB each, ~600 MB for 150
designs) under `pipeline_runs/<run>/msa_per_candidate/`. These are regenerable
and safe to delete after scoring:

```bash
rm -rf pipeline_runs/*/msa_per_candidate
```

Use `--msa-mode share` to skip writing them at all, at the cost of the query row
not matching each mutant exactly.

## ESM3 / ESM-C (optional, orthogonal scoring)

The pipeline's two required priors are AbLang2 and ESM2-3B. ESM-C can be added
as a third, independent sequence prior via `scripts/stage3b_esmc_rerank.py`.
It needs the EvolutionaryScale SDK, which **must not** be installed into
`her2_seq` (see gotcha 1):

```bash
conda create -y -n her2_esm3 python=3.12
conda run -n her2_esm3 pip install torch esm
```

ESM3-open weights are license-gated on Hugging Face; accept the terms and
authenticate (`huggingface-cli login`) before first use. ESM-C 600M downloads
~2.4 GB. On this machine ESM3-sm-open-v1 was already cached, so only the SDK was
needed.
