# Modal deployment — parallel Boltz-2 cofolding

Fan the structural stage out across many GPUs. Generation and ESM reranking stay
local (they are cheap); only cofolding is both expensive and embarrassingly
parallel, so it is the only stage worth renting GPUs for.

## Setup

```bash
conda env create -f envs/her2_modal.yml
conda activate her2_modal
modal token new                 # one-time browser auth

# one-time: put Boltz-2 weights + CCD cache (~3 GB) in a persistent Volume
modal run modal/her2_modal_app.py::populate_cache
```

Prerequisite: `outputs/msa_cache/` and `outputs/her2_domain_iv.fasta` must exist
locally — they are baked into the image. Create them once with:

```bash
python scripts/stage1_target_prep.py
python scripts/bootstrap_msa_cache.py     # the single MSA-server call
```

## Run

```bash
modal run modal/her2_modal_app.py \
  --queue outputs/priority_cofold_queue_merged.csv \
  --limit 1000 --batch-size 50 --seeds 42

# pull artifacts back and score with the normal local stages
modal volume get her2-boltz-out / ./pipeline_runs/modal_cofold
python scripts/stage5_score_ipsae.py --run-dir pipeline_runs/modal_cofold
python scripts/stage6_select_audit.py --top-n 15
```

Output layout matches a local run exactly
(`boltz_results_*/predictions/<name>/`), so stage 5 and 6 need no changes.

Pick the GPU with `HER2_MODAL_GPU` (it is read at import time, so set it in the
same command):

```bash
HER2_MODAL_GPU=L4 modal run modal/her2_modal_app.py --limit 500
```

## Counter-intuitive cost finding: do **not** buy bigger GPUs

Our complex is 242 + 119 = **361 residues** and peaks at **~19 GiB**. That fits a
24 GB card with room to spare, and Boltz-2 at this size is not compute-bound
enough for a bigger card to pay off. Approximate cost per structure, using the
locally measured 15 s on a 24 GB RTX 3090 and scaling conservatively:

| GPU | VRAM | ~$/GPU-hr | est. s/structure | **est. $/1,000 structures** |
| --- | ---: | ---: | ---: | ---: |
| T4 | 16 GB | ~0.59 | — | **does not fit** (19 GiB peak) |
| **L4** | 24 GB | ~0.80 | ~18 | **~$4.00** |
| **A10G** | 24 GB | ~1.10 | ~15 | **~$4.60** |
| L40S | 48 GB | ~1.95 | ~10 | ~$5.40 |
| A100 40 GB | 40 GB | ~2.10 | ~9 | ~$5.25 |
| H100 | 80 GB | ~3.95 | ~6 | ~$6.60 |

Prices are indicative — **check current Modal pricing before a large run.**

The pattern holds regardless of the exact numbers: a bigger GPU cuts latency
sub-linearly while costing linearly more, so **cost per structure rises with GPU
size**. The cheapest 24 GB card that fits is the most structures per dollar.

**What actually buys speed is container count, not GPU size.** Wall-clock is
`total_structures / containers x s_per_structure`, so:

| Containers | 1,000 structures on A10G | Cost |
| ---: | --- | ---: |
| 1 | ~4.2 h | ~$4.60 |
| 10 | ~25 min | ~$4.60 |
| 50 | ~5 min | ~$4.60 |

Cost is essentially flat; only wall-clock changes. Use more containers, not
bigger GPUs. (Modal enforces a per-workspace concurrency limit; request a raise
if you want 50+ in parallel.)

### Your $30 budget

At ~$4.60 per 1,000 on A10G, $30 is roughly **5,000–6,000 structures** after
cold-start overhead — about 30x the 193 we ran locally. Reserve ~20% for retries
and the ipSAE CPU containers (those are a rounding error, a few cents).

## Batch size matters more than it looks

Container cold start is **~1–2 min** (boot plus model load) and is billed per
container, not per structure. At `--batch-size 1` you would pay more for startup
than inference.

| batch-size | startup share of runtime | verdict |
| ---: | ---: | --- |
| 1 | ~85% | wasteful |
| 10 | ~35% | acceptable |
| **50** | **~10%** | **recommended** |
| 200 | ~3% | fine, but coarse retry granularity |

A failed batch re-runs entirely (`retries=1`), so very large batches trade
efficiency for blast radius.

## How to spend the credits well

Based on what the local 193-structure run actually showed, raw breadth is *not*
the best use of GPU time:

1. **Replicate seeds (highest value).** Our best design exceeds the parent by
   +0.069 ipSAE while the same-seed batch-order swing alone was 0.037. Signal is
   only ~2x noise, so error bars decide whether *any* ranking is real. Running
   5 seeds on 200 designs (1,000 structures, ~$4.60) turns anecdotes into
   statistics — worth far more than 1,000 single-seed designs.
2. **The MSA-reuse control.** We reuse the parent's alignment for every mutant,
   which systematically favours the parent (its query row matches the alignment
   perfectly; a mutant has 5–8 mismatched columns). Running a matched subset with
   `--msa-mode fresh` locally, or a `fresh`-equivalent on Modal, settles whether
   the parent's apparent advantage is partly our own artifact. This is cheap and
   affects how every result is interpreted.
3. **Mutation-count stratified sweeps.** Mutation count was the strongest single
   predictor of interface quality (rho = −0.50 vs ipSAE). A clean sweep at
   5/6/7/8 substitutions with many designs per stratum would measure that curve
   properly instead of inferring it from an unbalanced sample.
4. **Breadth last.** Sequence-plausibility scores *anti-correlate* with interface
   quality here (AbLang2 vs epitope recovery: −0.47), so generating thousands
   more candidates ranked by those scores mostly produces more below-parent
   designs. Fix the selection objective before scaling the count.

## Caveats

- **This app has not been executed against live Modal** — it is validated only
  by constructing the app locally (`import her2_modal_app` succeeds against
  modal 1.6.3, so the Image/Volume/GPU API usage is correct). Run
  `populate_cache` and a small `--limit 4 --batch-size 2` job first and confirm
  the artifacts before launching a large batch.
- `cuequivariance-ops-torch-cu12` is pinned to match the Torch that
  `boltz==2.2.1` installs. If a future boltz moves to a cu13 Torch, switch to the
  `-cu13` wheel — the same trap documented in [../envs/README.md](../envs/README.md).
- Workers never contact the MSA server; alignments ship in the image. That is
  deliberate: 1,000 containers hitting ColabFold would be rate-limited and is
  discourteous.
- Scientific claim boundaries are unchanged by running on bigger hardware. More
  structures do not make ipSAE an affinity measurement, and no K_D is computed.
