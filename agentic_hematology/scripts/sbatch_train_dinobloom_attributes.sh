#!/bin/bash
# Train DinoBloom attribute head on LLD manifest crops (frozen MarrLab backbone).
#
# Images are NOT passed as a CLI folder here. Training reads PBS tile paths from
# attr_manifest.csv (same as EfficientNet train_attributes.py). Each row contains:
#   image path + GT bbox (x,y,w,h) + 6 attribute labels
#
# Default image source (via manifest):
#   DATA_ROOT/images/train/*.png
#   DATA_ROOT/images/test/*.png
#
# Regenerate manifest if needed:
#   DATA_ROOT=/nfs-stor/roba.majzoub/LeukemiaDataset_Organized \
#     python wbc_unified/cv/data/prepare_dataset.py --data-root "$DATA_ROOT"
#
# Default: GPU MLP head training (mirrors train_attributes.py / EfficientNet setup).
# Optional sklearn linear probes: TRAIN_MODE=sklearn sbatch ...
#
# Examples:
#   cd /home/roba.majzoub/agentic_hematology
#   sbatch scripts/sbatch_train_dinobloom_attributes.sh
#
#   EPOCHS=50 BATCH=32 DEVICE=0 sbatch scripts/sbatch_train_dinobloom_attributes.sh
#
#   TRAIN_MODE=sklearn sbatch scripts/sbatch_train_dinobloom_attributes.sh
#
# Output:
#   torch : wbc_unified/cv/runs/attribute_dinobloom/train/best_attr_dinobloom.pt
#   sklearn: wbc_unified/cv/runs/attribute_dinobloom/train/best_attr_probes.joblib

#SBATCH --job-name=dinobloom_attr
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --partition=cscc-gpu-p
#SBATCH --qos=cscc-gpu-qos
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=/home/roba.majzoub/agentic_hematology/logs/sbatch_train_dinobloom_%j.out
#SBATCH --error=/home/roba.majzoub/agentic_hematology/logs/sbatch_train_dinobloom_%j.err

set -euo pipefail

if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  PROJECT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
else
  PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

CV="${PROJECT}/wbc_unified/cv"
mkdir -p "${PROJECT}/logs"
cd "${CV}"

# ---- defaults ----
export DATA_ROOT="${DATA_ROOT:-/nfs-stor/roba.majzoub/LeukemiaDataset_Organized}"
export TRAIN_IMAGES_DIR="${TRAIN_IMAGES_DIR:-${DATA_ROOT}/images/train}"
export TEST_IMAGES_DIR="${TEST_IMAGES_DIR:-${DATA_ROOT}/images/test}"
export DINOBLOOM_WEIGHTS="${DINOBLOOM_WEIGHTS:-auto}"
export DINOBLOOM_VARIANT="${DINOBLOOM_VARIANT:-l}"
export MANIFEST="${MANIFEST:-${CV}/generated/attr_manifest.csv}"
export REGENERATE_MANIFEST="${REGENERATE_MANIFEST:-0}"
export TRAIN_MODE="${TRAIN_MODE:-torch}"   # torch | sklearn
export EPOCHS="${EPOCHS:-40}"
export BATCH="${BATCH:-64}"
export LR="${LR:-1e-3}"
export DEVICE="${DEVICE:-0}"
export WORKERS="${WORKERS:-8}"
export RUN_NAME="${RUN_NAME:-train}"
export PROJECT_DIR="${PROJECT_DIR:-${CV}/runs/attribute_dinobloom}"
export EMBED_BATCH="${EMBED_BATCH:-32}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT}:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

activate_conda_env() {
  # Load CUDA driver libs before activating Python (required on CSCC compute nodes).
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
  echo "  SLURM_GPUS              : ${SLURM_GPUS:-unknown}"
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
print(f"  torch.version.cuda      : {torch.version.cuda}")
print(f"  torch.cuda.is_available : {torch.cuda.is_available()}")
print(f"  torch.cuda.device_count : {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"  torch.cuda.get_device_name(0): {torch.cuda.get_device_name(0)}")
else:
    sys.exit("PyTorch cannot see a CUDA GPU on this node.")
PY
}

if [[ ! -d "${TRAIN_IMAGES_DIR}" ]]; then
  echo "ERROR: train images directory not found: ${TRAIN_IMAGES_DIR}" >&2
  echo "Set DATA_ROOT to your LeukemiaDataset_Organized path." >&2
  exit 2
fi

if [[ "${REGENERATE_MANIFEST}" == "1" ]]; then
  echo "Regenerating attr_manifest.csv from ${DATA_ROOT} ..."
  python "${CV}/data/prepare_dataset.py" \
    --data-root "${DATA_ROOT}" \
    --out "${CV}/generated"
fi

if [[ ! -f "${MANIFEST}" ]]; then
  echo "ERROR: attribute manifest not found: ${MANIFEST}" >&2
  echo "Run with REGENERATE_MANIFEST=1 or:" >&2
  echo "  python ${CV}/data/prepare_dataset.py --data-root ${DATA_ROOT}" >&2
  exit 2
fi

# Sanity-check: manifest rows point at image files under DATA_ROOT.
SAMPLE_IMAGE="$(awk -F, 'NR==2 {print $2; exit}' "${MANIFEST}")"
if [[ -z "${SAMPLE_IMAGE}" || ! -f "${SAMPLE_IMAGE}" ]]; then
  echo "ERROR: manifest image path not readable: ${SAMPLE_IMAGE:-<empty>}" >&2
  echo "Manifest may be stale. Rebuild with REGENERATE_MANIFEST=1." >&2
  exit 2
fi

activate_conda_env

# Under Slurm, use the first (and usually only) GPU Slurm exposes in CUDA_VISIBLE_DEVICES.
if [[ -n "${CUDA_VISIBLE_DEVICES:-}" ]]; then
  DEVICE=0
fi
export DEVICE

echo "======== DinoBloom attribute training ========"
verify_gpu_runtime
echo "  TRAIN_MODE        : ${TRAIN_MODE}"
echo "  DATA_ROOT         : ${DATA_ROOT}"
echo "  TRAIN_IMAGES_DIR  : ${TRAIN_IMAGES_DIR}"
echo "  TEST_IMAGES_DIR   : ${TEST_IMAGES_DIR}"
echo "  MANIFEST          : ${MANIFEST}"
echo "  (manifest rows -> open image + GT crop + attribute labels)"
echo "  DINOBLOOM_WEIGHTS : ${DINOBLOOM_WEIGHTS}"
echo "  DINOBLOOM_VARIANT : ${DINOBLOOM_VARIANT}"
echo "  PROJECT_DIR       : ${PROJECT_DIR}/${RUN_NAME}"
echo "  DEVICE            : ${DEVICE}"
echo ""

if [[ "${TRAIN_MODE}" == "torch" ]]; then
  python "${CV}/train_dinobloom_attributes_torch.py" \
    --manifest "${MANIFEST}" \
    --dinobloom-weights "${DINOBLOOM_WEIGHTS}" \
    --dinobloom-variant "${DINOBLOOM_VARIANT}" \
    --project "${PROJECT_DIR}" \
    --name "${RUN_NAME}" \
    --epochs "${EPOCHS}" \
    --batch "${BATCH}" \
    --lr "${LR}" \
    --device "${DEVICE}" \
    --workers "${WORKERS}"

  OUT="${PROJECT_DIR}/${RUN_NAME}/best_attr_dinobloom.pt"
elif [[ "${TRAIN_MODE}" == "sklearn" ]]; then
  python "${CV}/train_dinobloom_attributes.py" \
    --manifest "${MANIFEST}" \
    --dinobloom-weights "${DINOBLOOM_WEIGHTS}" \
    --dinobloom-variant "${DINOBLOOM_VARIANT}" \
    --project "${PROJECT_DIR}" \
    --name "${RUN_NAME}" \
    --device "${DEVICE}" \
    --embed-batch "${EMBED_BATCH}"

  OUT="${PROJECT_DIR}/${RUN_NAME}/best_attr_probes.joblib"
else
  echo "ERROR: TRAIN_MODE must be 'torch' or 'sklearn', got: ${TRAIN_MODE}" >&2
  exit 2
fi

echo ""
echo "Training complete."
echo "  Weights: ${OUT}"
echo ""
echo "Run inference with:"
echo "  cd ${PROJECT}"
echo "  python run_orchestrator.py \\"
echo "    --patients-dir wbc_unified/cv/generated/patients \\"
echo "    --backend dinobloom \\"
echo "    --dinobloom-weights ${DINOBLOOM_WEIGHTS} \\"
echo "    --dinobloom-attr-mode probes \\"
echo "    --dinobloom-attr-weights ${OUT} \\"
echo "    --no-agent --device ${DEVICE} \\"
echo "    --out outputs/ablation_dinobloom_trained"
