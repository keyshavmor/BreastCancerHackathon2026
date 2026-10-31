#!/usr/bin/env bash
# =============================================================================
# Live progress dashboard for a running HER2 pipeline.
#
#   bash scripts/progress.sh            # one snapshot
#   bash scripts/progress.sh -w         # refresh every 10 s
#   bash scripts/progress.sh -w 30      # refresh every 30 s
#
# Why this exists: Python buffers stdout when redirected to a file, so a
# `nohup python stage4... > x.log` wrapper log can look empty for minutes. The
# authoritative live signals are the on-disk artifact counts and Boltz's own
# per-batch log, both of which this script reads directly.
# =============================================================================
set -o pipefail
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="${RUN_DIR:-$BASE/pipeline_runs/her2_cofold}"

snapshot () {
  echo "=========================================================="
  echo " HER2 pipeline progress            $(date '+%Y-%m-%d %H:%M:%S')"
  echo "=========================================================="

  # ---- running stages ----
  echo "-- processes --"
  local any=0
  for s in bootstrap_msa_cache stage2_generate stage3_esm stage3b_esmc \
           stage4_boltz stage5_score stage6_select; do
    local pid
    pid=$(pgrep -f "$s" | head -1)
    if [ -n "$pid" ]; then
      any=1
      printf "   %-22s pid=%-8s elapsed=%s cpu=%s%%\n" "$s" "$pid" \
        "$(ps -o etime= -p "$pid" | tr -d ' ')" "$(ps -o pcpu= -p "$pid" | tr -d ' ')"
    fi
  done
  [ "$any" = "0" ] && echo "   (no pipeline stage currently running)"

  # ---- GPU ----
  echo "-- gpu --"
  nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu \
    --format=csv,noheader 2>/dev/null | sed 's/^/   /' || echo "   nvidia-smi unavailable"

  # ---- Boltz structures ----
  echo "-- boltz structures --"
  local cif pae planned
  cif=$(find "$RUN/out" -name "*_model_0.cif" 2>/dev/null | wc -l)
  pae=$(find "$RUN/out" -name "pae_*_model_0.npz" 2>/dev/null | wc -l)
  planned=$(python3 -c "import json;print(json.load(open('$RUN/stage4_manifest.json'))['runs_planned'])" 2>/dev/null)
  if [ -z "$planned" ]; then
    planned=$(grep -ahoE "^\[plan\] [0-9]+" "$RUN"/../../logs/*.log 2>/dev/null | tail -1 | awk '{print $2}')
  fi
  printf "   structures=%s  pae=%s  planned=%s\n" "$cif" "$pae" "${planned:-?}"
  if [ -n "$planned" ] && [ "$cif" -gt 0 ] 2>/dev/null; then
    printf "   %.1f%% complete\n" "$(echo "$cif $planned" | awk '{print $1*100/$2}')"
  fi
  # throughput from file mtimes of the last 10 structures
  if [ "$cif" -ge 2 ]; then
    find "$RUN/out" -name "*_model_0.cif" -printf '%T@\n' 2>/dev/null | sort -n | tail -10 \
      | awk 'NR==1{f=$1} {l=$1; n++} END{if(n>1) printf "   recent rate: %.1f s/structure (last %d)\n",(l-f)/(n-1),n}'
  fi

  # ---- latest boltz batch activity ----
  echo "-- latest boltz batch log --"
  local blog
  blog=$(ls -t "$RUN/out"/boltz_batch_seed*.log 2>/dev/null | head -1)
  if [ -n "$blog" ]; then
    echo "   $blog"
    tr '\r' '\n' < "$blog" | grep -aE "Predicting|failed examples|Error" | tail -3 | sed 's/^/   /'
  else
    echo "   (none yet)"
  fi

  # ---- deliverables ----
  echo "-- deliverables in outputs/ --"
  for f in residue_map.csv internal_50_candidates.csv priority_cofold_queue.csv \
           boltz_results_raw.csv ipsae_aggregated.csv submission_scored.csv \
           top_15_scored.csv compliance_audit.json method_walkthrough.md; do
    if [ -f "$BASE/outputs/$f" ]; then
      printf "   %-30s %6s lines  %s\n" "$f" "$(wc -l < "$BASE/outputs/$f")" \
        "$(date -r "$BASE/outputs/$f" '+%H:%M:%S')"
    else
      printf "   %-30s %s\n" "$f" "pending"
    fi
  done

  # ---- audit verdict if present ----
  if [ -f "$BASE/outputs/compliance_audit.json" ]; then
    echo "-- audit --"
    python3 - "$BASE/outputs/compliance_audit.json" <<'PY' 2>/dev/null | sed 's/^/   /'
import json,sys
d=json.load(open(sys.argv[1]))
print(f"{d['overall']} ({d['failed_checks']} failed) | scored={d['submitted_scored_count']} "
      f"| top={d['top_n']} | seed_noise={d['seed_noise_ipsae_sd']} "
      f"| above_parent={d['designs_above_parent_beyond_noise']}")
PY
  fi
  echo
}

if [ "${1:-}" = "-w" ] || [ "${1:-}" = "--watch" ]; then
  INT="${2:-10}"
  while true; do clear; snapshot; echo "(refreshing every ${INT}s - Ctrl-C to stop)"; sleep "$INT"; done
else
  snapshot
fi
