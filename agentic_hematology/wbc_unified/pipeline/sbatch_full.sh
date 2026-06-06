#!/bin/bash
#SBATCH --job-name=wbc_full
#SBATCH --time=72:00:00
#SBATCH --nodes=1
#SBATCH --partition=long
#SBATCH --exclude=gpu-62,gpu-45
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=64
#SBATCH --mem=230G
#SBATCH --output=logs/sbatch_full_%j.out
#SBATCH --error=logs/sbatch_full_%j.err

set -euo pipefail

# Slurm copies the script to spool — BASH_SOURCE is unreliable; use submit cwd.
# Run from wbc_unified/:  cd wbc_unified && sbatch pipeline/sbatch_full.sh
if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  PROJECT="$SLURM_SUBMIT_DIR"
else
  PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
cd "$PROJECT"
mkdir -p "$PROJECT/logs"

export CONFIRM_FULL_RETRAIN="${CONFIRM_FULL_RETRAIN:-1}"
export DATA_ROOT="${DATA_ROOT:-/nfs-stor/zongyan/datasets/medical/LeukemiaDataset_Organized}"
export STAGE1_NGPUS="${STAGE1_NGPUS:-1}"
export LLM_NGPUS="${LLM_NGPUS:-4}"
export DET_WEIGHTS_LOCAL="${DET_WEIGHTS_LOCAL:-1}"
export RAY_CPUS="${RAY_CPUS:-16}"
export FORCE_GRPO_FRESH="${FORCE_GRPO_FRESH:-1}"
export PIPELINE_EVAL_DIR="${PIPELINE_EVAL_DIR:-$PROJECT/logs/pipeline_eval_${SLURM_JOB_ID}}"
export PYTHONUNBUFFERED=1

bash "$PROJECT/pipeline/run.sh"
