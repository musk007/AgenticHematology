#!/usr/bin/env bash
# Export LM-only LoRA adapter for vLLM language_model_only rollout
# Usage: bash verl_scripts/filter_lora_lm_only.sh [adapter_dir]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=env.sh
source "$ROOT/verl_scripts/env.sh"

if [ -n "${1:-}" ]; then
  SRC="$1"
else
  SRC="${SFT_SAVE_DIR}/global_step_50/lora_adapter"
  [ -d "$SRC" ] || SRC="${SFT_LORA_ADAPTER%_lm}"
fi
DST="${SRC%/}_lm"

python3 "$ROOT/verl_scripts/filter_lora_lm_only.py" "$SRC" --dst "$DST"
echo "For GRPO set: export SFT_LORA_ADAPTER=$DST"
