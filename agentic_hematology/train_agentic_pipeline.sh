#!/bin/bash
# sbatch_train_pipeline.sh
# Fits the sklearn HybridClassifier using existing detector + attribute weights.
# Detector and attribute models are NOT retrained.
#
# Default run:
#   sbatch pipeline/sbatch_train_pipeline.sh
#
# Custom weights:
#   DET_WEIGHTS=/path/to/best.pt ATTR_WEIGHTS=/path/to/best_attr.pt \
#     sbatch pipeline/sbatch_train_pipeline.sh
#
# To also retrain detector and/or attributes (rare):
#   RUN_DETECTOR=1 RUN_ATTRIBUTES=1 sbatch pipeline/sbatch_train_pipeline.sh
#
#SBATCH --job-name=wbc_clf_fit
#SBATCH --time=2:00:00
#SBATCH --nodes=1
#SBATCH --partition=cscc-gpu-p    
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=logs/sbatch_train_%j.out
#SBATCH --error=logs/sbatch_train_%j.err

set -euo pipefail

if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  PROJECT="$SLURM_SUBMIT_DIR"
else
  PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
cd "$PROJECT"
mkdir -p "$PROJECT/logs"

# ---- env ----
export DATA_ROOT="${DATA_ROOT:-/nfs-stor/roba.majzoub/LeukemiaDataset_Organized}"
export STAGE1_DEVICE="${STAGE1_DEVICE:-0}"
export DET_WEIGHTS="/home/roba.majzoub/agentic_hematology/wbc_unified/cv/runs/detector/train/weights/best.pt"
export ATTR_WEIGHTS="/home/roba.majzoub/agentic_hematology/wbc_unified/cv/runs/attribute/train/best_attr.pt"
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export PYTHONUNBUFFERED=1

# ---- activate conda env ----
source /apps/local/anaconda3.10/bin/activate
module load nvidia/cuda/11.8 2>/dev/null || true
conda activate /home/roba.majzoub/envs/agentic

# ---- build CLI args ----
EXTRA_ARGS=""
[[ -n "${DET_WEIGHTS:-}"   ]] && EXTRA_ARGS="$EXTRA_ARGS --det-weights $DET_WEIGHTS"
[[ -n "${ATTR_WEIGHTS:-}"  ]] && EXTRA_ARGS="$EXTRA_ARGS --attr-weights $ATTR_WEIGHTS"
[[ "${RUN_DATA_PREP:-0}"  == "1" ]] && EXTRA_ARGS="$EXTRA_ARGS --run-data-prep"
[[ "${RUN_DETECTOR:-0}"   == "1" ]] && EXTRA_ARGS="$EXTRA_ARGS --run-detector"
[[ "${RUN_ATTRIBUTES:-0}" == "1" ]] && EXTRA_ARGS="$EXTRA_ARGS --run-attributes"

echo "======== wbc classifier fit ========"
echo "  SLURM_JOB_ID : ${SLURM_JOB_ID:-local}"
echo "  DET_WEIGHTS  : ${DET_WEIGHTS:-<default>}"
echo "  ATTR_WEIGHTS : ${ATTR_WEIGHTS:-<default>}"
echo ""

python "$PROJECT/Train_pipeline.py" \
  --data-root "$DATA_ROOT" \
  --device    "$STAGE1_DEVICE" \
  $EXTRA_ARGS