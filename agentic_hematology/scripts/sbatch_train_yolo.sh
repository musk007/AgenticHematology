#!/bin/bash
# Train YOLO11 WBC detector on LLD (single GPU).
#
# Dataset: wbc_unified/cv/generated/det_dataset (built from LeukemiaDataset_Organized)
#
# Submit:
#   cd /home/roba.majzoub/agentic_hematology
#   sbatch scripts/sbatch_train_yolo.sh
#
# Optional overrides:
#   REGENERATE_DATA=1 sbatch scripts/sbatch_train_yolo.sh
#   EPOCHS=100 BATCH=16 RESUME=1 sbatch scripts/sbatch_train_yolo.sh
#   DET_MODEL=yolo11m.pt sbatch scripts/sbatch_train_yolo.sh
#
# Output:
#   wbc_unified/cv/runs/detector/train/weights/best.pt

#SBATCH --job-name=yolo_lld
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --partition=cscc-gpu-p
#SBATCH --qos=cscc-gpu-qos
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=/home/roba.majzoub/agentic_hematology/logs/sbatch_train_yolo_%j.out
#SBATCH --error=/home/roba.majzoub/agentic_hematology/logs/sbatch_train_yolo_%j.err

set -euo pipefail

if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  PROJECT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
else
  PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

CV="${PROJECT}/wbc_unified/cv"
mkdir -p "${PROJECT}/logs"
cd "${CV}"

# ---- defaults (1 GPU) ----
export DATA_ROOT="${DATA_ROOT:-/nfs-stor/roba.majzoub/LeukemiaDataset_Organized}"
export REGENERATE_DATA="${REGENERATE_DATA:-0}"
export DET_MODEL="${DET_MODEL:-yolo11m.pt}"
export EPOCHS="${EPOCHS:-100}"
export BATCH="${BATCH:-16}"
export IMGSZ="${IMGSZ:-640}"
export DEVICE="${DEVICE:-0}"
export WORKERS="${WORKERS:-0}"
export DET_VAL="${DET_VAL:-0}"
export DET_PLOTS="${DET_PLOTS:-0}"
export DET_SAVE_PERIOD="${DET_SAVE_PERIOD:-5}"
export PATIENCE="${PATIENCE:-30}"
export RESUME="${RESUME:-0}"
export RUN_NAME="${RUN_NAME:-train}"
export PROJECT_DIR="${PROJECT_DIR:-${CV}/runs/detector}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT}:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
# Disable optional Ultralytics integrations that fail on Slurm (wandb paths, raytune API drift).
export WANDB_DISABLED="${WANDB_DISABLED:-true}"
export WANDB_MODE="${WANDB_MODE:-disabled}"
export RAY_DISABLE_IMPORT_WARNING="${RAY_DISABLE_IMPORT_WARNING:-1}"

activate_conda_env() {
  if command -v module >/dev/null 2>&1; then
    module load nvidia/cuda/11.8 2>/dev/null || module load cuda/11.8 2>/dev/null || true
  fi

  local conda_sh=""
  local d
  for d in "${CONDA_ROOT:-}" "$HOME/miniconda3" "$HOME/anaconda3" /apps/local/anaconda3 /apps/local/anaconda3.10; do
    [[ -n "${d}" ]] || continue
    if [[ -f "${d}/etc/profile.d/conda.sh" ]]; then
      conda_sh="${d}/etc/profile.d/conda.sh"
      break
    fi
  done
  if [[ -z "${conda_sh}" ]]; then
    echo "ERROR: conda.sh not found. Set CONDA_ROOT." >&2
    exit 2
  fi
  # shellcheck source=/dev/null
  source "${conda_sh}"

  if [[ -n "${CONDA_ENV_PATH:-}" ]]; then
    conda activate "${CONDA_ENV_PATH}"
  else
    conda activate "${CONDA_ENV:-/home/roba.majzoub/envs/agentic}"
  fi

  export LD_LIBRARY_PATH="${CONDA_PREFIX}/lib:${LD_LIBRARY_PATH:-}"
}

verify_gpu_runtime() {
  echo "  SLURM_JOB_ID            : ${SLURM_JOB_ID:-local}"
  echo "  SLURM_JOB_NODELIST      : ${SLURM_JOB_NODELIST:-unknown}"
  echo "  SLURM_GPUS_ON_NODE      : ${SLURM_GPUS_ON_NODE:-unknown}"
  echo "  CUDA_VISIBLE_DEVICES    : ${CUDA_VISIBLE_DEVICES:-unset}"

  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi -L || true
  else
    echo "WARNING: nvidia-smi not found in PATH" >&2
  fi

  python - <<'PY'
import sys
import torch
print(f"  torch.__version__       : {torch.__version__}")
print(f"  torch.cuda.is_available : {torch.cuda.is_available()}")
print(f"  torch.cuda.device_count : {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"  torch.cuda.get_device_name(0): {torch.cuda.get_device_name(0)}")
else:
    sys.exit("PyTorch cannot see a CUDA GPU on this node.")
PY
}

if [[ ! -d "${DATA_ROOT}/images/train" ]]; then
  echo "ERROR: LLD train images not found: ${DATA_ROOT}/images/train" >&2
  exit 2
fi

if [[ "${REGENERATE_DATA}" == "1" ]]; then
  echo "Regenerating det_dataset + attr_manifest from ${DATA_ROOT} ..."
  python "${CV}/data/prepare_dataset.py" \
    --data-root "${DATA_ROOT}" \
    --out "${CV}/generated" \
    --image-mode hardlink
fi

TRAIN_IMG_DIR="${CV}/generated/det_dataset/images/train"
if [[ ! -d "${TRAIN_IMG_DIR}" ]] || [[ -z "$(ls -A "${TRAIN_IMG_DIR}" 2>/dev/null || true)" ]]; then
  echo "ERROR: no YOLO train images under ${TRAIN_IMG_DIR}" >&2
  echo "Submit with REGENERATE_DATA=1 or run prepare_dataset.py first." >&2
  exit 2
fi

activate_conda_env

# Under Slurm, always use logical GPU 0 (maps to the allocated GPU).
if [[ -n "${CUDA_VISIBLE_DEVICES:-}" ]]; then
  DEVICE=0
fi
export DEVICE

RESUME_ARGS=()
if [[ "${RESUME}" == "1" ]]; then
  RESUME_ARGS=(--resume)
fi

VAL_ARGS=()
if [[ "${DET_VAL}" == "1" ]]; then
  VAL_ARGS=(--val)
fi

PLOTS_ARGS=()
if [[ "${DET_PLOTS}" == "1" ]]; then
  PLOTS_ARGS=(--plots)
fi

echo "======== YOLO LLD detector training (1 GPU) ========"
verify_gpu_runtime
echo "  DATA_ROOT       : ${DATA_ROOT}"
echo "  DET_MODEL       : ${DET_MODEL}"
echo "  TRAIN_IMAGES    : ${TRAIN_IMG_DIR}"
echo "  PROJECT_DIR     : ${PROJECT_DIR}/${RUN_NAME}"
echo "  EPOCHS          : ${EPOCHS}"
echo "  BATCH           : ${BATCH}"
echo "  IMGSZ           : ${IMGSZ}"
echo "  DEVICE          : ${DEVICE}"
echo "  WORKERS         : ${WORKERS}"
echo "  DET_VAL         : ${DET_VAL}"
echo "  RESUME          : ${RESUME}"
echo ""

python "${CV}/train_detector.py" \
  --config "${CV}/configs/dataset.yaml" \
  --model "${DET_MODEL}" \
  --epochs "${EPOCHS}" \
  --imgsz "${IMGSZ}" \
  --batch "${BATCH}" \
  --device "${DEVICE}" \
  --ngpus 1 \
  --workers "${WORKERS}" \
  --project "${PROJECT_DIR}" \
  --name "${RUN_NAME}" \
  --save-period "${DET_SAVE_PERIOD}" \
  --patience "${PATIENCE}" \
  "${VAL_ARGS[@]}" \
  "${PLOTS_ARGS[@]}" \
  "${RESUME_ARGS[@]}"

OUT="${PROJECT_DIR}/${RUN_NAME}/weights/best.pt"
echo ""
echo "Training complete."
echo "  Best weights: ${OUT}"
echo ""
echo "Next steps:"
echo "  # Regenerate infer JSON + retrain patient classifier"
echo "  cd ${PROJECT}"
echo "  YOLO=${OUT}"
echo "  EFFNET=wbc_unified/cv/runs/attribute/train/best_attr.pt"
echo "  python wbc_unified/cv/infer.py --det-weights \"\${YOLO}\" --attr-weights \"\${EFFNET}\" \\"
echo "    --split train --save-json --device 0 --out wbc_unified/cv/runs/predict --name classifier_fit_infer"
echo "  python train_leukemia_from_stats.py --backend random_forest"
