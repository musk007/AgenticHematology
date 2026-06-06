#!/usr/bin/env bash
# Re-run CV infer only -> cv/runs/predict/infer/test_predictions.json
set -euo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CV="$PROJECT/cv"

DET_WEIGHTS="${DET_WEIGHTS:-$CV/runs/detector/train/weights/best.pt}"
ATTR_WEIGHTS="${ATTR_WEIGHTS:-$CV/runs/attribute/train/best_attr.pt}"
SPLIT="${STAGE1_SPLIT:-test}"
OUT_JSON="${PREDICTIONS_JSON:-$CV/runs/predict/infer/test_predictions.json}"

for w in "$DET_WEIGHTS" "$ATTR_WEIGHTS"; do
  [ -f "$w" ] || { echo "Missing weights: $w" >&2; exit 1; }
done

mkdir -p "$(dirname "$OUT_JSON")"
cd "$CV"
python infer.py \
  --det-weights "$DET_WEIGHTS" \
  --attr-weights "$ATTR_WEIGHTS" \
  --split "$SPLIT" \
  --conf "${STAGE1_CONF:-0.25}" \
  --device "${STAGE1_DEVICE:-0}" \
  --save-json \
  --out runs/predict \
  --name infer

BUILT="$CV/runs/predict/infer/${SPLIT}_predictions.json"
if [ -f "$BUILT" ] && [ "$BUILT" != "$OUT_JSON" ]; then
  cp -f "$BUILT" "$OUT_JSON"
fi
[ -f "$OUT_JSON" ] || { echo "Missing $OUT_JSON"; exit 1; }
echo "OK: $OUT_JSON"
