#!/bin/bash
#SBATCH --job-name=wbc_validate
#SBATCH --time=4:00:00
#SBATCH --nodes=1
#SBATCH --partition=long
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=logs/sbatch_validate_%j.out
#SBATCH --error=logs/sbatch_validate_%j.err

set -euo pipefail

if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  PROJECT="$SLURM_SUBMIT_DIR"
else
  PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
cd "$PROJECT"
mkdir -p "$PROJECT/logs"

# shellcheck source=/dev/null
source "$PROJECT/verl_scripts/env.sh"
export PYTHONUNBUFFERED=1

bash "$PROJECT/pipeline/run_validate_pred.sh"
