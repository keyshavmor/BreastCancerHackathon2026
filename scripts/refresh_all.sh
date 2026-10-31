#!/usr/bin/env bash
# =============================================================================
# One pass of: pull Modal results -> rescore everything -> regenerate every
# report, plot, binder package and animation.
#
#   bash scripts/refresh_all.sh            # one pass
#   LOOP=600 bash scripts/refresh_all.sh   # repeat every 600 s until stopped
#
# Safe to run while campaigns are still going: each stage is idempotent, scores
# whatever structures exist at that moment, and pools local + Modal replicates of
# the same design into one estimate. Nothing is deleted, so a pass that races a
# half-written file simply picks it up next time.
# =============================================================================
set -o pipefail
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE"

SEQ="$HOME/anaconda3/envs/her2_seq/bin/python"
BOLTZ="$HOME/anaconda3/envs/her2_boltz2/bin/python"
MODALBIN="$HOME/anaconda3/envs/her2_modal/bin/modal"
TOPN="${TOPN:-15}"
GIFS="${GIFS:-6}"
PULL_MODAL="${PULL_MODAL:-1}"
mkdir -p logs outputs/reports

RUN_DIRS=()
for d in pipeline_runs/her2_cofold pipeline_runs/her2_exploit \
         pipeline_runs/her2_msa_control pipeline_runs/modal_cofold; do
  [ -d "$d/out" ] && RUN_DIRS+=("$d")
done

one_pass () {
  local t0 stamp
  t0=$(date +%s); stamp=$(date '+%Y-%m-%d %H:%M:%S')
  echo "=============================================================="
  echo " refresh pass  $stamp"
  echo "=============================================================="

  # 1. Pull whatever Modal has finished so far. The volume is append-only from
  #    our side, so an in-flight campaign just means fewer files this pass.
  if [ "$PULL_MODAL" = "1" ] && [ -x "$MODALBIN" ] && [ -f "$HOME/.modal.toml" ]; then
    echo ">>> pulling Modal artifacts"
    "$MODALBIN" volume get --force her2-boltz-out / ./pipeline_runs/modal_cofold \
      > logs/modal_pull.log 2>&1 && echo "    ok" || echo "    (nothing new or pull failed)"
    [ -d pipeline_runs/modal_cofold/out ] && {
      case " ${RUN_DIRS[*]} " in *" pipeline_runs/modal_cofold "*) ;;
        *) RUN_DIRS+=("pipeline_runs/modal_cofold");; esac; }
  fi

  echo ">>> run dirs: ${RUN_DIRS[*]}"
  echo ">>> structures on disk: $(find pipeline_runs -name '*_model_0.cif' 2>/dev/null | wc -l)"

  # 2. Score every structure, pooling local + Modal replicates per design.
  echo ">>> stage 5: ipSAE"
  "$BOLTZ" scripts/stage5_score_ipsae.py --run-dir "${RUN_DIRS[@]}" --workers 6 \
    2>&1 | tail -4

  # 3. Re-select and re-audit against the larger replicate set.
  echo ">>> stage 6: selection + audit"
  "$SEQ" scripts/stage6_select_audit.py --top-n "$TOPN" 2>&1 | tail -7

  # 4. Documents and figures.
  echo ">>> stage 7: method walkthrough"
  "$SEQ" scripts/stage7_method_walkthrough.py 2>&1 | tail -2
  echo ">>> plots"
  "$SEQ" scripts/make_plots.py 2>&1 | grep -v findfont | tail -3
  echo ">>> reports"
  "$SEQ" scripts/make_reports.py 2>&1 | tail -3
  echo ">>> organizer compliance"
  "$SEQ" scripts/verify_compliance.py 2>&1 | head -3

  # 5. Binder packages and animations for the current nominees.
  echo ">>> binder packages"
  "$SEQ" scripts/export_binder_info.py --set top_15_scored 2>&1 | tail -2
  if [ "$GIFS" -gt 0 ]; then
    echo ">>> animations (top $GIFS)"
    "$SEQ" scripts/make_3d_gifs.py --set top_15_scored --limit "$GIFS" \
      --frames 24 --size 640 2>&1 | grep -v findfont | tail -2
  fi

  # 6. A single machine-readable status line for the watcher/dashboard.
  "$SEQ" - <<'PY' >> logs/refresh_status.log
import json, pathlib, datetime
o = pathlib.Path("outputs")
def j(p):
    try: return json.loads((o / p).read_text())
    except Exception: return {}
a = j("compliance_audit.json"); dg = j("score_diagnostics.json")
rel = (dg.get("reliability") or {}); pc = rel.get("parent_comparison") or {}
print(json.dumps({
    "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "scored_designs": a.get("submitted_scored_count"),
    "top_n": a.get("top_n"),
    "audit": a.get("overall"),
    "failed_checks": a.get("failed_checks"),
    "single_seed_reliability": rel.get("reliability_single_seed"),
    "n_replicated": rel.get("n_replicated"),
    "above_parent": pc.get("n_above"),
    "below_parent": pc.get("n_below"),
    "indistinguishable": pc.get("n_indistinguishable"),
}))
PY
  echo ">>> pass complete in $(( $(date +%s) - t0 ))s"
  tail -1 logs/refresh_status.log
  echo
}

if [ -n "${LOOP:-}" ]; then
  echo "looping every ${LOOP}s - Ctrl-C or kill to stop"
  while true; do one_pass; sleep "$LOOP"; done
else
  one_pass
fi
