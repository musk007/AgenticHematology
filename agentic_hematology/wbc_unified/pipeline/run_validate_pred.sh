#!/usr/bin/env bash
# Deploy validation: CV predictions -> patient summary -> LoRA report -> compare to GT
#
#   cd wbc_unified
#   source verl_scripts/env.sh
#   bash pipeline/run_validate_pred.sh

set -euo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="$PROJECT/report"
cd "$REPORT"
# shellcheck source=/dev/null
source "$PROJECT/verl_scripts/env.sh"

export DATA_ROOT="${DATA_ROOT:-/nfs-stor/zongyan/datasets/medical/LeukemiaDataset_Organized}"

maybe_export_grpo_lora() {
  local ckpt="${GRPO_SAVE_DIR}/global_step_${GRPO_LORA_STEP}/actor"
  local lm="${ckpt}/lora_adapter_lm"
  if [ -f "${lm}/adapter_config.json" ]; then
    return 0
  fi
  if compgen -G "${ckpt}/model_world_size_*_rank_0.pt" > /dev/null; then
    echo "Exporting GRPO LoRA from ${ckpt} ..."
    bash "$PROJECT/verl_scripts/export_lora.sh" "${GRPO_LORA_STEP}" "${ckpt}"
  fi
}

resolve_adapter() {
  maybe_export_grpo_lora
  if [ -n "${LORA_ADAPTER:-}" ] && [ -f "${LORA_ADAPTER}/adapter_config.json" ]; then
    echo "$LORA_ADAPTER"
    return
  fi
  local grpo_lm="${GRPO_SAVE_DIR}/global_step_${GRPO_LORA_STEP}/actor/lora_adapter_lm"
  if [ -f "${grpo_lm}/adapter_config.json" ]; then
    echo "$grpo_lm"
    return
  fi
  if [ -f "${SFT_LORA_ADAPTER}/adapter_config.json" ]; then
    echo "$SFT_LORA_ADAPTER"
    return
  fi
  echo "ERROR: no LoRA adapter found." >&2
  exit 1
}

ADAPTER="$(resolve_adapter)"
ART="${REPORT_LLM_ARTIFACT_ROOT}"
SUMMARIES_PRED="${ART}/data/patient_summaries/pred"
REPORTS_LLM="${ART}/data/reports_llm_pred"
EVAL_JSON="${ART}/data/eval/metrics_llm_pred.json"

echo "======== Deploy validate (pred -> LLM report) ========"
echo "LoRA: $ADAPTER"

if [ "${SKIP_AGGREGATE:-0}" != "1" ]; then
  if [ -n "${PREDICTIONS_JSON:-}" ]; then
    python scripts/02_aggregate_pred.py --predictions "$PREDICTIONS_JSON" --out "$SUMMARIES_PRED"
  else
    python scripts/02_aggregate_pred.py --out "$SUMMARIES_PRED"
  fi
fi

if [ "${GENERATE_TEMPLATE:-0}" = "1" ]; then
  python scripts/04_generate_reports.py \
    --summaries "$SUMMARIES_PRED" \
    --out "${ART}/data/reports_template_pred"
fi

export REPORT_LLM_ARTIFACT_ROOT="$ART"
python scripts/07_generate_reports_llm.py \
  --summaries "$SUMMARIES_PRED" \
  --out "$REPORTS_LLM" \
  --adapter "$ADAPTER" \
  ${MAX_NEW_TOKENS:+--max-new-tokens "$MAX_NEW_TOKENS"} \
  ${TEMPERATURE:+--temperature "$TEMPERATURE"}

SUMMARIES_GT="${ART}/data/patient_summaries/gt"
if [ ! -d "$SUMMARIES_GT" ] || [ -z "$(ls -A "$SUMMARIES_GT"/*.json 2>/dev/null)" ]; then
  python scripts/01_aggregate_gt.py --out "$SUMMARIES_GT"
fi

python scripts/08_eval_llm_reports.py \
  --generated "$REPORTS_LLM" \
  --summaries-pred "$SUMMARIES_PRED" \
  --summaries-gt "$SUMMARIES_GT" \
  --out "$EVAL_JSON"

echo "Done. Metrics: $EVAL_JSON"
