#!/bin/bash
# Stage-1 only (detect + attributes + infer), single GPU.
#SBATCH --job-name=wbc_s1
#SBATCH --time=72:00:00
#SBATCH --nodes=1
#SBATCH --partition=long
#SBATCH --exclude=gpu-62,gpu-45
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --output=logs/sbatch_stage1_%j.out
#SBATCH --error=logs/sbatch_stage1_%j.err

set -euo pipefail

if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  PROJECT="$SLURM_SUBMIT_DIR"
else
  PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
cd "$PROJECT"
mkdir -p "$PROJECT/logs"

export CONFIRM_FULL_RETRAIN="${CONFIRM_FULL_RETRAIN:-1}"
export DATA_ROOT="${DATA_ROOT:-/nfs-stor/zongyan/datasets/medical/LeukemiaDataset_Organized}"
export STAGE1_NGPUS=1
export SKIP_SFT=1
export SKIP_GRPO=1
export DET_WEIGHTS_LOCAL="${DET_WEIGHTS_LOCAL:-1}"
export PIPELINE_EVAL_DIR="${PIPELINE_EVAL_DIR:-$PROJECT/logs/pipeline_eval_stage1_${SLURM_JOB_ID}}"
export PYTHONUNBUFFERED=1

bash "$PROJECT/pipeline/run.sh"
