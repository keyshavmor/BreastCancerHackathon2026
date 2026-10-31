#!/usr/bin/env bash
# =============================================================================
# HER2 scFv optimisation pipeline - top-level orchestrator
#
# Runs the six stages end to end, each in the correct conda environment, with
# measured-throughput defaults for a single 24 GB GPU.
#
#   stage 1  target prep      1N8Z + P04626 -> residue map, HER2 domain IV crop
#   stage 2  generation       AbLang2-guided pool -> shortlist (+ stop-loss 50)
#   stage 3  rerank           ESM2-3B -> internal 50 + cofold queue
#   stage 4  cofold           Boltz-2 on HER2 domain IV, cached MSAs
#   stage 5  ipSAE            external DunbrackLab/IPSAE + epitope QC
#   stage 6  select & audit   submission_scored.*, top_15_scored.*, audit
#
# NOTE: deliberately no `set -u` - Anaconda's qt-main activate.d hook references
# QT_XCB_GL_INTEGRATION unguarded and would abort the script.
#
# Usage:
#   bash scripts/run_her2_pipeline.sh                 # full production run
#   POOL=40000 QUEUE=150 bash scripts/run_her2_pipeline.sh
#   SMOKE=1 bash scripts/run_her2_pipeline.sh         # tiny end-to-end check
#   FROM=4 bash scripts/run_her2_pipeline.sh          # resume from stage 4
#
# Every stage is idempotent; stage 4 skips predictions that already have both a
# structure and a PAE file, so an interrupted run resumes cheaply.
# =============================================================================
set -o pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE"

# ---- tunables ---------------------------------------------------------------
SEQ_ENV="${SEQ_ENV:-her2_seq}"
BOLTZ_ENV="${BOLTZ_ENV:-her2_boltz2}"
CONDA_ROOT="${CONDA_ROOT:-$HOME/anaconda3}"

POOL="${POOL:-1000000}"        # raw AbLang2 proposals sampled (~200 s; measured to
                               # beat 40k by +49% on the top-500 band)
SHORTLIST="${SHORTLIST:-50000}" # handed to ESM2-3B (~37 min at batch 16)
QUEUE="${QUEUE:-150}"          # total cofold queue length
INTERNAL="${INTERNAL:-50}"     # curated internal proposal pool (deliverable)
TOPN="${TOPN:-15}"             # lab nominations
SEEDS="${SEEDS:-42,7,13}"      # first seed = main pass; others = replicates
REPLICATE_TOP="${REPLICATE_TOP:-20}"
BATCH="${BATCH:-25}"           # YAMLs per boltz invocation (amortises model load)
MSA_MODE="${MSA_MODE:-retarget}"
TIME_BUDGET_MIN="${TIME_BUDGET_MIN:-80}"
RUN_DIR="${RUN_DIR:-$BASE/pipeline_runs/her2_cofold}"
OUTDIR="${OUTDIR:-$BASE/outputs}"
FROM="${FROM:-1}"

if [ "${SMOKE:-0}" = "1" ]; then
  POOL=2000; SHORTLIST=100; QUEUE=4; INTERNAL=50; TOPN=3
  SEEDS=42; REPLICATE_TOP=0; BATCH=4; TIME_BUDGET_MIN=20
  RUN_DIR="$BASE/pipeline_runs/her2_smoke"
  echo "### SMOKE MODE: tiny counts, single seed ###"
fi

SEQ_PY="$CONDA_ROOT/envs/$SEQ_ENV/bin/python"
BOLTZ_PY="$CONDA_ROOT/envs/$BOLTZ_ENV/bin/python"
for p in "$SEQ_PY" "$BOLTZ_PY"; do
  [ -x "$p" ] || { echo "FATAL: missing interpreter $p - see envs/README.md"; exit 1; }
done

mkdir -p "$OUTDIR" "$RUN_DIR" logs
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG="logs/pipeline_${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1

banner () { echo; echo "=============== $* ($(date -Is)) ==============="; }
t_stage () { local s=$1; shift; local t0=$(date +%s); "$@"; local rc=$?
             echo "--- stage $s finished rc=$rc in $(( $(date +%s)-t0 ))s ---"
             [ $rc -eq 0 ] || { echo "FATAL: stage $s failed"; exit $rc; }; }

banner "HER2 pipeline start | pool=$POOL shortlist=$SHORTLIST queue=$QUEUE seeds=$SEEDS"
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader || true

# ---- stage 0: invariants ----------------------------------------------------
banner "stage 0: parent invariants"
t_stage 0 "$SEQ_PY" scripts/her2_common.py

# ---- stage 1: target prep ---------------------------------------------------
if [ "$FROM" -le 1 ]; then
  banner "stage 1: target preparation (1N8Z + P04626 -> HER2 domain IV)"
  t_stage 1 "$SEQ_PY" scripts/stage1_target_prep.py --outdir "$OUTDIR"
fi

# ---- stage 2: generation ----------------------------------------------------
if [ "$FROM" -le 2 ]; then
  banner "stage 2: AbLang2-guided candidate generation"
  t_stage 2 "$SEQ_PY" scripts/stage2_generate_candidates.py \
    --pool-size "$POOL" --shortlist "$SHORTLIST" \
    --id-prefix "${ID_PREFIX:-HER2_}" --outdir "$OUTDIR"
fi

# ---- stage 3: ESM2 rerank ---------------------------------------------------
if [ "$FROM" -le 3 ]; then
  banner "stage 3: ESM2-3B rerank and portfolio freeze"
  t_stage 3 "$SEQ_PY" scripts/stage3_esm_rerank.py \
    --max-candidates "$SHORTLIST" --queue-size "$QUEUE" \
    --internal-pool "$INTERNAL" --priority "$TOPN" --outdir "$OUTDIR"
fi

# ---- stage 4: Boltz-2 cofold ------------------------------------------------
# One MSA-server call must already have populated outputs/msa_cache/. If it has
# not, bootstrap it from the parent before the budgeted candidate run.
if [ "$FROM" -le 4 ]; then
  if [ ! -f "$OUTDIR/msa_cache/scfv_parent.csv" ]; then
    banner "stage 4a: bootstrap MSA cache (single --use_msa_server parent run)"
    t_stage 4a "$BOLTZ_PY" scripts/bootstrap_msa_cache.py --outdir "$OUTDIR"
  fi
  banner "stage 4: Boltz-2 cofold (HER2 domain IV only, cached MSAs)"
  t_stage 4 "$BOLTZ_PY" scripts/stage4_boltz_cofold.py \
    --limit "$QUEUE" --batch-size "$BATCH" --seeds "$SEEDS" \
    --replicate-top "$REPLICATE_TOP" --msa-mode "$MSA_MODE" \
    --run-dir "$RUN_DIR" --time-budget-min "$TIME_BUDGET_MIN"
fi

# ---- stage 5: ipSAE ---------------------------------------------------------
if [ "$FROM" -le 5 ]; then
  banner "stage 5: external ipSAE scoring + epitope recovery QC"
  t_stage 5 "$BOLTZ_PY" scripts/stage5_score_ipsae.py \
    --run-dir "$RUN_DIR" --outdir "$OUTDIR"
fi

# ---- stage 6: select and audit ---------------------------------------------
if [ "$FROM" -le 6 ]; then
  banner "stage 6: multi-objective selection, compliance audit, packaging"
  t_stage 6 "$SEQ_PY" scripts/stage6_select_audit.py --top-n "$TOPN" --outdir "$OUTDIR"
fi

banner "pipeline complete"
echo "Deliverables in $OUTDIR:"
for f in contract.yaml residue_map.csv her2_domain_iv.fasta \
         internal_50_candidates.csv internal_50_candidates.fasta \
         submission_scored.csv submission_scored.fasta \
         top_15_scored.csv top_15_scored.fasta \
         ipSAE_provenance.csv compliance_audit.json run_manifest.json; do
  [ -f "$OUTDIR/$f" ] && printf '  %-36s %s\n' "$f" "$(wc -l < "$OUTDIR/$f") lines" \
                      || printf '  %-36s MISSING\n' "$f"
done
echo
python3 - "$OUTDIR/compliance_audit.json" <<'PY' 2>/dev/null || true
import json,sys
d=json.load(open(sys.argv[1]))
print(f"AUDIT: {d['overall']} ({d['failed_checks']} failed) | "
      f"{d['submitted_scored_count']} scored designs | top {d['top_n']} nominees")
print(f"ipSAE seed noise sd={d['seed_noise_ipsae_sd']} | "
      f"above parent beyond noise: {d['designs_above_parent_beyond_noise']}")
PY
echo "Full log: $LOG"
