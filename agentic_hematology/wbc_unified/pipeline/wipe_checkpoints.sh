#!/usr/bin/env bash
# Remove training checkpoints (does not delete datasets or parquet data).
#
#   export CONFIRM_WIPE=1
#   export WIPE_STAGE1=1
#   export WIPE_LLM=1
#   bash pipeline/wipe_checkpoints.sh

set -euo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CV="$PROJECT/cv"
ARTIFACT="${REPORT_LLM_ARTIFACT_ROOT:-/nfs-stor/zongyan/wbc_medical/rao.anwer/report_llm}"

WIPE_STAGE1="${WIPE_STAGE1:-1}"
WIPE_LLM="${WIPE_LLM:-1}"

DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

TARGETS=()
if [[ "$WIPE_STAGE1" == "1" ]]; then
  TARGETS+=(
    "$CV/runs/detector"
    "$CV/runs/attribute"
    "$CV/runs/predict"
  )
fi
if [[ "$WIPE_LLM" == "1" ]]; then
  TARGETS+=(
    "$ARTIFACT/runs/verl/sft_qwen3_5_2b_lora"
    "$ARTIFACT/runs/verl/grpo_qwen3_5_2b_lora"
    "$ARTIFACT/outputs/sft"
  )
fi

declare -A SEEN
UNIQUE=()
for t in "${TARGETS[@]}"; do
  real="$(readlink -f "$t" 2>/dev/null || echo "$t")"
  if [[ -z "${SEEN[$real]:-}" ]]; then
    SEEN[$real]=1
    UNIQUE+=("$t")
  fi
done

echo "======== Checkpoint paths to remove (WIPE_STAGE1=$WIPE_STAGE1 WIPE_LLM=$WIPE_LLM) ========"
for t in "${UNIQUE[@]}"; do
  if [[ -e "$t" ]]; then
    du -sh "$t" 2>/dev/null || echo "  $t (exists)"
    echo "  $t"
  else
    echo "  (skip, not found) $t"
  fi
done

if [[ "$DRY" == "1" ]]; then
  echo "Dry-run only. To delete: CONFIRM_WIPE=1 bash pipeline/wipe_checkpoints.sh"
  exit 0
fi

if [[ "${CONFIRM_WIPE:-0}" != "1" ]]; then
  echo "ERROR: Set CONFIRM_WIPE=1 to delete checkpoints." >&2
  exit 2
fi

for t in "${UNIQUE[@]}"; do
  [[ -e "$t" ]] || continue
  echo "rm -rf $t"
  rm -rf "$t"
  mkdir -p "$(dirname "$t")"
done

echo "Done. Datasets and parquet data were not removed."
