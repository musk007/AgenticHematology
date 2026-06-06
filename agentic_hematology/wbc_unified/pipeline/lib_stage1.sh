#!/usr/bin/env bash
# Stage-1 CV: single-GPU training, eval after each step, infer -> test_predictions.json

stage1_train_and_infer() {
  local CV="$1"
  local EVAL_DIR="$2"
  cd "$CV"
  mkdir -p "$EVAL_DIR"

  export DATA_ROOT="${DATA_ROOT:-/nfs-stor/zongyan/datasets/medical/LeukemiaDataset_Organized}"
  export STAGE1_NGPUS="${STAGE1_NGPUS:-1}"
  export NGPUS="$STAGE1_NGPUS"
  export DEVICE="${STAGE1_DEVICE:-0}"
  export MASTER_PORT="${MASTER_PORT:-$((29500 + RANDOM % 1000))}"

  if (( STAGE1_NGPUS == 1 )); then
    export DET_BATCH="${DET_BATCH:-64}"
    export ATTR_BATCH="${ATTR_BATCH:-64}"
  else
    export DET_BATCH="${DET_BATCH:-64}"
    export ATTR_BATCH="${ATTR_BATCH:-256}"
  fi
  export DET_WORKERS="${DET_WORKERS:-0}"
  export ATTR_WORKERS="${ATTR_WORKERS:-2}"
  export DET_IMAGE_MODE="${DET_IMAGE_MODE:-auto}"
  export DET_VAL="${DET_VAL:-0}"
  export DET_SAVE_PERIOD="${DET_SAVE_PERIOD:-5}"
  export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
  export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
  export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

  if (( STAGE1_NGPUS > 1 )); then
    export NCCL_ASYNC_ERROR_HANDLING="${NCCL_ASYNC_ERROR_HANDLING:-1}"
    if (( DET_BATCH % STAGE1_NGPUS != 0 )) || (( ATTR_BATCH % STAGE1_NGPUS != 0 )); then
      echo "ERROR: DET_BATCH/ATTR_BATCH must be divisible by STAGE1_NGPUS=$STAGE1_NGPUS" >&2
      return 1
    fi
  fi

  local MET_DET="${EVAL_DIR}/metrics_detector_test.json"
  local MET_ATTR="${EVAL_DIR}/metrics_attribute_test.json"
  local MET_JOINT="${EVAL_DIR}/metrics_stage1_joint_test.json"
  local PRED_JSON="${CV}/runs/predict/infer/test_predictions.json"
  local DET_REPO_DIR="$CV/runs/detector"
  local DET_PROJECT="$CV/runs/detector"
  local DET_NAME="train"
  local DET_SCRATCH=""

  if [[ "${DET_WEIGHTS_LOCAL:-1}" == "1" && -n "${SLURM_TMPDIR:-}" ]]; then
    DET_SCRATCH="${SLURM_TMPDIR}/detector_${SLURM_JOB_ID:-$$}"
    mkdir -p "$DET_SCRATCH"
    DET_PROJECT="$DET_SCRATCH"
    echo "Detector checkpoints: local scratch $DET_SCRATCH -> $DET_REPO_DIR/train/weights/"
  fi

  echo "======== Stage-1 CV (STAGE1_NGPUS=$STAGE1_NGPUS DEVICE=$DEVICE) ========"

  python - <<PY
import os
from pathlib import Path
root = Path(os.environ["DATA_ROOT"])
for sp in ("train", "test"):
    d = root / "images" / sp
    n = len(list(d.glob("*.png"))) if d.is_dir() else 0
    print(f"preflight {sp}: png={n}")
    if n == 0:
        raise SystemExit(f"No PNG in {d}")
PY

  # Pretrained detector weights (avoid corrupt auto-download on compute nodes)
  local DET_MODEL_DEFAULT="/nfs-stor/zongyan/wbc_medical/rao.anwer/home_archive/LLD_nextgen_wbc_pipeline/yolo11m.pt"
  export DET_MODEL="${DET_MODEL:-$DET_MODEL_DEFAULT}"
  if [[ ! -f "$DET_MODEL" ]]; then
    echo "ERROR: missing detector pretrained weights: $DET_MODEL" >&2
    return 1
  fi
  python3 - "$DET_MODEL" <<'PY'
import zipfile, sys
p = sys.argv[1]
try:
    zipfile.ZipFile(p)
except Exception as e:
    raise SystemExit(f"Corrupt YOLO weights {p}: {e}")
print(f"detector weights OK: {p}")
PY

  echo "======== Stage-1a: train detector ========"
  python data/prepare_dataset.py --data-root "$DATA_ROOT" --image-mode "$DET_IMAGE_MODE"

  python train_detector.py \
    --device "$DEVICE" \
    --ngpus "$STAGE1_NGPUS" \
    --epochs "${DET_EPOCHS:-100}" \
    --model "$DET_MODEL" \
    --batch "$DET_BATCH" \
    --imgsz "${DET_IMGSZ:-640}" \
    --workers "$DET_WORKERS" \
    --project "$DET_PROJECT" \
    --name "$DET_NAME"

  if [[ -n "$DET_SCRATCH" ]]; then
    mkdir -p "$DET_REPO_DIR/train/weights"
    cp -f "$DET_SCRATCH/$DET_NAME/weights/"*.pt "$DET_REPO_DIR/train/weights/" 2>/dev/null || true
  fi

  DET_BEST="$DET_REPO_DIR/train/weights/best.pt"
  [[ -f "$DET_BEST" ]] || DET_BEST="$DET_REPO_DIR/train/weights/last.pt"
  [[ -f "$DET_BEST" ]] || DET_BEST="$DET_PROJECT/$DET_NAME/weights/best.pt"
  [[ -f "$DET_BEST" ]] || DET_BEST="$DET_PROJECT/$DET_NAME/weights/last.pt"
  [[ -f "$DET_BEST" ]] || { echo "Missing detector weights"; return 1; }

  echo "======== Stage-1a eval: detector ========"
  python scripts/pipeline_eval.py detector \
    --weights "$DET_BEST" \
    --split test \
    --json-out "$MET_DET"
  pipeline_eval_record "detector" "metrics" "$MET_DET"
  pipeline_eval_record "detector" "weights" "$DET_BEST"

  echo "======== Stage-1b: train attribute head ========"
  if (( STAGE1_NGPUS > 1 )); then
    python -m torch.distributed.run \
      --nproc_per_node="$STAGE1_NGPUS" \
      --master_port="$MASTER_PORT" \
      train_attributes.py \
      --epochs "${ATTR_EPOCHS:-40}" \
      --batch "$ATTR_BATCH" \
      --backbone "${ATTR_BACKBONE:-efficientnet_b0}" \
      --workers "$ATTR_WORKERS"
  else
    python train_attributes.py \
      --epochs "${ATTR_EPOCHS:-40}" \
      --batch "$ATTR_BATCH" \
      --backbone "${ATTR_BACKBONE:-efficientnet_b0}" \
      --device "$DEVICE" \
      --workers "$ATTR_WORKERS"
  fi

  ATTR_BEST="$CV/runs/attribute/train/best_attr.pt"
  [[ -f "$ATTR_BEST" ]] || { echo "Missing $ATTR_BEST"; return 1; }

  echo "======== Stage-1b eval: attribute (GT crops) ========"
  python scripts/pipeline_eval.py attribute \
    --weights "$ATTR_BEST" \
    --split test \
    --json-out "$MET_ATTR"
  pipeline_eval_record "attribute" "metrics" "$MET_ATTR"
  pipeline_eval_record "attribute" "weights" "$ATTR_BEST"

  echo "======== Stage-1c eval: joint det+attr e2e ========"
  python scripts/pipeline_eval.py joint \
    --det-weights "$DET_BEST" \
    --attr-weights "$ATTR_BEST" \
    --split test \
    --json-out "$MET_JOINT"
  pipeline_eval_record "stage1_joint" "metrics" "$MET_JOINT"

  echo "======== Stage-1d: infer test JSON ========"
  mkdir -p "$(dirname "$PRED_JSON")"
  python infer.py \
    --det-weights "$DET_BEST" \
    --attr-weights "$ATTR_BEST" \
    --split "${STAGE1_SPLIT:-test}" \
    --conf "${STAGE1_CONF:-0.25}" \
    --save-json \
    --device "$DEVICE" \
    --out runs/predict \
    --name infer
  BUILT="$CV/runs/predict/infer/${STAGE1_SPLIT:-test}_predictions.json"
  if [[ -f "$BUILT" && "$BUILT" != "$PRED_JSON" ]]; then
    cp -f "$BUILT" "$PRED_JSON"
  fi
  [[ -f "$PRED_JSON" ]] || { echo "Missing $PRED_JSON"; return 1; }
  pipeline_eval_record "stage1_infer" "predictions_json" "$PRED_JSON"

  export DET_WEIGHTS="$DET_BEST" ATTR_WEIGHTS="$ATTR_BEST"
}
