#!/usr/bin/env bash
# =============================================================================
# Modal campaign: ~5,550 Boltz-2 structures for ~$25 in roughly 50-70 minutes.
#
# Every phase buys something the local run could not afford, and the ordering is
# by scientific value per dollar, so stopping early still leaves a coherent
# result.
#
#   A  error bars on EVERY submitted design   1,050 structures  ~$4.8
#   B  balanced mutation-count sweep          1,200 structures  ~$5.5
#   C  stratified breadth, WITH replicates    3,000 structures  ~$13.8
#   D  deep replication of the lab nominees     300 structures  ~$1.4
#
# Why this and not simply "more designs": measured single-seed ipSAE reliability
# on this system is 0.461, so a one-seed ranking is about half noise. Every phase
# therefore carries >=5 seeds. Phase A alone upgrades the deliverable from "149
# designs with one noisy number each" to "149 designs with a mean and an error
# bar".
#
# PREREQUISITE - concurrency. Wall-clock is total_structures * 15 s / containers:
#     10 containers -> ~2.3 h   (does NOT fit 90 min)
#     20 containers -> ~69 min
#     30 containers -> ~46 min
#     50 containers -> ~28 min
# Check your workspace limit at modal.com/settings and request a raise if it is
# below ~20, otherwise run PHASES="A B D" for a ~$12 / 40 min subset.
#
# Usage:
#   bash modal/run_campaign.sh --dry            # print plan and cost, run nothing
#   bash modal/run_campaign.sh                  # all phases
#   PHASES="A B" bash modal/run_campaign.sh     # subset
#   GPU=L4 bash modal/run_campaign.sh           # cheaper per structure than A10G
# =============================================================================
set -o pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE"

GPU="${GPU:-A10G}"
PHASES="${PHASES:-A B C D}"
BATCH="${BATCH:-10}"
DRY=0
[ "${1:-}" = "--dry" ] && DRY=1

APP=modal/her2_modal_app.py
# Cost per structure, derived from ~15 s/structure at ~$1.10/GPU-hour (A10G).
RATE_PER_STRUCT=0.0046

# Seeds are disjoint from the local run (42,7,13,101,202) so local and Modal
# results COMBINE into a larger replicate set rather than duplicating it.
A_SEEDS="1001,1002,1003,1004,1005,1006,1007"
B_SEEDS="2001,2002,2003,2004,2005"
C_SEEDS="3001,3002,3003,3004,3005"
D_SEEDS="4001,4002,4003,4004,4005,4006,4007,4008,4009,4010,4011,4012,4013,4014,4015,4016,4017,4018,4019,4020"

declare -A QUEUE SEEDS LIMIT LABEL
QUEUE[A]="outputs/submission_scored.csv";  SEEDS[A]="$A_SEEDS"; LIMIT[A]=149
LABEL[A]="error bars on every submitted design (7 seeds)"
QUEUE[B]="outputs/queue_sweep.csv";        SEEDS[B]="$B_SEEDS"; LIMIT[B]=240
LABEL[B]="balanced mutation-count x branch sweep (5 seeds)"
QUEUE[C]="outputs/queue_breadth.csv";      SEEDS[C]="$C_SEEDS"; LIMIT[C]=600
LABEL[C]="stratified breadth with replicates (5 seeds)"
QUEUE[D]="outputs/top_15_scored.csv";      SEEDS[D]="$D_SEEDS"; LIMIT[D]=15
LABEL[D]="deep replication of the lab nominees (20 seeds)"

nseeds () { awk -F, '{print NF}' <<<"$1"; }

echo "=============================================================="
echo " Modal campaign plan   GPU=$GPU  batch=$BATCH  phases='$PHASES'"
echo "=============================================================="
total=0
for p in $PHASES; do
  q="${QUEUE[$p]}"
  if [ ! -f "$q" ]; then echo "  [$p] MISSING QUEUE $q - skipping"; continue; fi
  rows=$(( $(wc -l < "$q") - 1 ))
  lim=${LIMIT[$p]}; [ "$rows" -lt "$lim" ] && lim=$rows
  s=$(nseeds "${SEEDS[$p]}")
  n=$(( (lim + 1) * s ))         # +1 for the parent baseline per seed
  total=$(( total + n ))
  printf "  [%s] %-52s %5d designs x %2d seeds = %5d structures\n" "$p" "${LABEL[$p]}" "$lim" "$s" "$n"
done
cost=$(awk -v n="$total" -v r="$RATE_PER_STRUCT" 'BEGIN{printf "%.2f", n*r}')
echo "--------------------------------------------------------------"
printf "  TOTAL %d structures   est. cost \$%s\n" "$total" "$cost"
for c in 10 20 30 50; do
  printf "  wall-clock @ %2d containers: %5.1f min\n" "$c" \
    "$(awk -v n="$total" -v c="$c" 'BEGIN{print n*15/c/60}')"
done
echo "=============================================================="

if [ "$DRY" = "1" ]; then echo "(--dry: nothing launched)"; exit 0; fi

if [ ! -f "$HOME/.modal.toml" ]; then
  echo "FATAL: not authenticated. Run:  modal token new"
  exit 1
fi

mkdir -p logs
echo ">>> ensuring Boltz weights are in the Modal Volume (one-time)"
modal run "$APP::populate_cache" 2>&1 | tee "logs/modal_populate.log" | tail -5

echo
echo ">>> smoke test (3 structures) before committing real money"
modal run "$APP" --queue "outputs/top_15_scored.csv" --limit 2 --batch-size 2 \
  --seeds 9001 2>&1 | tee "logs/modal_smoke.log" | tail -12
if ! grep -qE "ipsae_min=" "logs/modal_smoke.log"; then
  echo
  echo "FATAL: smoke test produced no ipSAE values. Inspect logs/modal_smoke.log"
  echo "       before spending the budget. Nothing further launched."
  exit 1
fi
echo ">>> smoke test OK"

for p in $PHASES; do
  q="${QUEUE[$p]}"
  [ -f "$q" ] || { echo ">>> phase $p: queue missing, skipped"; continue; }
  echo
  echo "=============================================================="
  echo ">>> PHASE $p  ${LABEL[$p]}   $(date -Is)"
  echo "=============================================================="
  HER2_MODAL_GPU="$GPU" modal run "$APP" \
    --queue "$q" --limit "${LIMIT[$p]}" --batch-size "$BATCH" \
    --seeds "${SEEDS[$p]}" 2>&1 | tee "logs/modal_phase_${p}.log" | tail -25
  echo ">>> phase $p finished rc=$? $(date -Is)"
done

echo
echo ">>> pulling artifacts back for local scoring"
modal volume get her2-boltz-out / ./pipeline_runs/modal_cofold 2>&1 | tail -3

cat <<'NEXT'

>>> score the Modal results with the normal local stages:

    python scripts/stage5_score_ipsae.py --run-dir pipeline_runs/modal_cofold
    python scripts/stage6_select_audit.py --top-n 15
    python scripts/stage7_method_walkthrough.py

    # to combine local + Modal replicates into one reliability estimate,
    # point stage 5 at both run directories in turn and re-run stage 6.
NEXT
