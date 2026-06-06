#!/usr/bin/env bash
# Export PEFT lora_adapter from an FSDP checkpoint (for GRPO loading)
# Usage: bash verl_scripts/export_lora.sh [global_step] [checkpoint_dir]
set -euo pipefail
# shellcheck source=env.sh
source "$(dirname "$0")/env.sh"

STEP="${1:-50}"
CKPT="${2:-${SFT_SAVE_DIR}/global_step_${STEP}}"
OUT="${CKPT}/lora_adapter"

if [ ! -d "$CKPT" ]; then
  echo "Checkpoint not found: $CKPT"
  exit 1
fi

if [ -f "$OUT/adapter_config.json" ]; then
  echo "LoRA adapter ready: $OUT"
  exit 0
fi

shards=( "$CKPT"/model_world_size_*_rank_0.pt )
if [ ! -e "${shards[0]}" ]; then
  echo "Missing model shards under $CKPT"
  exit 1
fi

WS="$(basename "${shards[0]}" | sed -n 's/model_world_size_\([0-9]*\)_rank_0.pt/\1/p')"
[ -n "$WS" ] || { echo "Cannot parse world_size from shard name"; exit 1; }

if [ ! -f "$CKPT/fsdp_config.json" ]; then
  printf '{"FSDP_version": 2, "world_size": %s}\n' "$WS" > "$CKPT/fsdp_config.json"
fi

if [ ! -f "$CKPT/lora_train_meta.json" ]; then
  python3 - <<PY
import json, os
p = os.path.join("${CKPT}", "lora_train_meta.json")
json.dump({"r": int("${LORA_RANK}"), "lora_alpha": int("${LORA_ALPHA}"), "task_type": "CAUSAL_LM"}, open(p, "w"), indent=2)
PY
fi

HF_META="${CKPT}/huggingface"
if [ ! -f "${HF_META}/config.json" ] && [ -f "${MODEL_PATH}/config.json" ]; then
  mkdir -p "${HF_META}"
  for f in config.json tokenizer.json tokenizer_config.json generation_config.json \
      preprocessor_config.json chat_template.jinja merges.txt vocab.json \
      special_tokens_map.json video_preprocessor_config.json; do
    [ -e "${MODEL_PATH}/${f}" ] && ln -sfn "$(cd "${MODEL_PATH}" && pwd)/${f}" "${HF_META}/${f}"
  done
fi

python3 - <<'PY' "$CKPT"
import sys, torch
from pathlib import Path
ckpt = Path(sys.argv[1])
shards = sorted(ckpt.glob("model_world_size_*_rank_*.pt"))
if not shards:
    sys.exit("No model shards")
for p in shards:
    try:
        torch.load(p, map_location="cpu", weights_only=False)
    except Exception as e:
        print(f"CORRUPT shard: {p}\n  {e}", file=sys.stderr)
        sys.exit(2)
print(f"OK: {len(shards)} shard(s) readable")
PY

echo "Export LoRA from $CKPT ..."
CUDA_VISIBLE_DEVICES="${EXPORT_CUDA_DEVICES:-0}" python -m verl.model_merger merge \
  --backend fsdp \
  --trust-remote-code \
  --local_dir "$CKPT" \
  --target_dir "${CKPT}/_merge_staging"

if [ -f "${CKPT}/_merge_staging/lora_adapter/adapter_config.json" ]; then
  rm -rf "$OUT"
  mv "${CKPT}/_merge_staging/lora_adapter" "$OUT"
  rm -rf "${CKPT}/_merge_staging"
elif [ ! -f "${CKPT}/lora_adapter/adapter_config.json" ]; then
  echo "Export failed: no lora_adapter under $CKPT"
  exit 1
fi

printf '%s\n' "$STEP" > "${SFT_SAVE_DIR}/latest_checkpointed_iteration.txt"
echo "Done: $OUT"
bash "$(dirname "$0")/filter_lora_lm_only.sh" "$OUT"
echo "GRPO: bash verl_scripts/train.sh grpo"
