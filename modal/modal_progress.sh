#!/usr/bin/env bash
# =============================================================================
# Live dashboard for a running Modal campaign.
#
#   bash modal/modal_progress.sh          # one snapshot
#   bash modal/modal_progress.sh -w       # refresh every 15 s
#   bash modal/modal_progress.sh -w 30    # refresh every 30 s
#
# Reads the tee'd campaign logs (logs/modal_campaign.log, logs/modal_phase_*.log)
# rather than querying Modal, so it is instant and costs nothing. The app emits
# fixed-format flushed `[progress]` and `[batch]` lines specifically so this can
# parse them.
# =============================================================================
set -o pipefail
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE"
LOGDIR="$BASE/logs"
CAMPAIGN="$LOGDIR/modal_campaign.log"

# Planned totals per phase, kept in step with modal/run_campaign.sh.
declare -A PLAN=( [A]=1050 [B]=1205 [C]=3005 [D]=320 )
declare -A PLABEL=( [A]="error bars, all submitted designs (7 seeds)"
                    [B]="balanced mutation-count sweep (5 seeds)"
                    [C]="stratified breadth w/ replicates (5 seeds)"
                    [D]="deep replication of nominees (20 seeds)" )
GRAND=5580
COST_PER=0.0046

bar () {  # bar <done> <total> <width>
  local d=$1 t=$2 w=${3:-28}
  [ "$t" -le 0 ] && t=1
  local f=$(( d * w / t )); [ "$f" -gt "$w" ] && f=$w
  printf "["
  for ((i=0;i<f;i++)); do printf "#"; done
  for ((i=f;i<w;i++)); do printf "."; done
  printf "]"
}

snapshot () {
  echo "=================================================================="
  echo " Modal campaign           $(date '+%Y-%m-%d %H:%M:%S')"
  echo "=================================================================="

  # ---- auth / workspace ----
  if [ -f "$HOME/.modal.toml" ]; then
    local ws
    ws=$(grep -m1 -oP '^\[\K[^\]]+' "$HOME/.modal.toml" 2>/dev/null)
    echo "  workspace: ${ws:-unknown}   (authenticated)"
  else
    echo "  NOT AUTHENTICATED - run: modal token new"
  fi

  # ---- is a run alive? ----
  if pgrep -f "modal run" >/dev/null; then
    local pid el
    pid=$(pgrep -f "modal run" | head -1)
    el=$(ps -o etime= -p "$pid" | tr -d ' ')
    echo "  state    : RUNNING (pid $pid, elapsed $el)"
  else
    echo "  state    : no 'modal run' process active"
  fi

  # ---- per-phase progress ----
  echo
  echo "  phase  progress                        structures      cost     status"
  local grand_done=0
  for p in A B C D; do
    local log="$LOGDIR/modal_phase_${p}.log"
    local plan=${PLAN[$p]} done=0 last="" st="pending"
    if [ -f "$log" ]; then
      last=$(grep -a "^\[progress\]" "$log" | tail -1)
      if [ -n "$last" ]; then
        done=$(sed -nE 's/^\[progress\] ([0-9]+)\/.*/\1/p' <<<"$last")
        [ -z "$done" ] && done=0
      fi
      if grep -qa "^\[modal\] batches" "$log"; then st="done"; else st="running"; fi
    fi
    grand_done=$(( grand_done + done ))
    printf "   %s     %s %5d/%-5d  \$%6.2f   %s\n" \
      "$p" "$(bar "$done" "$plan" 24)" "$done" "$plan" \
      "$(awk -v d="$done" -v c="$COST_PER" 'BEGIN{printf "%.2f", d*c}')" "$st"
  done
  echo "  ----------------------------------------------------------------"
  printf "   TOTAL   %s %5d/%-5d  \$%6.2f\n" \
    "$(bar "$grand_done" "$GRAND" 24)" "$grand_done" "$GRAND" \
    "$(awk -v d="$grand_done" -v c="$COST_PER" 'BEGIN{printf "%.2f", d*c}')"

  # ---- latest live metrics from whichever phase is active ----
  local active
  active=$(ls -t "$LOGDIR"/modal_phase_*.log 2>/dev/null | head -1)
  if [ -n "$active" ]; then
    echo
    echo "  latest  ($(basename "$active"))"
    grep -a "^\[progress\]" "$active" | tail -1 | sed 's/^/    /'
    echo "  recent batches:"
    grep -a "^\[batch\]" "$active" | tail -4 | sed 's/^/    /'
    local nf
    nf=$(grep -ac "^\[fail\]" "$active" 2>/dev/null || echo 0)
    if [ "${nf:-0}" -gt 0 ]; then
      echo "  FAILURES: $nf"
      grep -a "^\[fail\]" "$active" | tail -2 | cut -c1-160 | sed 's/^/    /'
    fi
  fi

  # ---- top ipSAE reported by the remote scorer, if any ----
  local tops
  tops=$(grep -ah "ipsae_min=" "$LOGDIR"/modal_phase_*.log "$LOGDIR"/modal_smoke.log 2>/dev/null | tail -6)
  if [ -n "$tops" ]; then
    echo
    echo "  remote ipSAE (top reported):"
    echo "$tops" | sed 's/^/    /'
  fi

  # ---- weights volume / setup ----
  if [ -f "$LOGDIR/modal_populate.log" ]; then
    echo
    echo "  weights volume: $(grep -ao "'status': '[a-zA-Z_]*'" "$LOGDIR/modal_populate.log" | tail -1)"
  fi

  # ---- local track, for context ----
  echo
  local lc
  lc=$(find "$BASE/pipeline_runs/her2_cofold/out" -name "*_model_0.cif" 2>/dev/null | wc -l)
  echo "  local structures: $lc    (Modal results land in pipeline_runs/modal_cofold)"
  if [ -f "$BASE/outputs/compliance_audit.json" ]; then
    python3 - "$BASE/outputs/compliance_audit.json" <<'PY' 2>/dev/null | sed 's/^/  /'
import json,sys
d=json.load(open(sys.argv[1]))
print(f"local audit: {d['overall']} | scored={d['submitted_scored_count']} "
      f"| top={d['top_n']}")
PY
  fi
  echo
  echo "  full log: $CAMPAIGN"
}

if [ "${1:-}" = "-w" ] || [ "${1:-}" = "--watch" ]; then
  INT="${2:-15}"
  while true; do clear; snapshot; echo "  (refresh ${INT}s - Ctrl-C to stop)"; sleep "$INT"; done
else
  snapshot
fi
