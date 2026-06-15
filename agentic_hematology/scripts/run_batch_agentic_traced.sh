#!/bin/bash
# Re-run the 13-patient agentic batch with the per-case agent_actions trace
# persisted (case_<id>_agent_trace.json), to recover the proceed /
# re_aggregate / flag_for_review distribution.

#SBATCH --job-name=wbc_agent_traced
#SBATCH --time=2:00:00
#SBATCH --nodes=1
#SBATCH --partition=cscc-gpu-p
#SBATCH --qos=cscc-gpu-qos
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --output=/home/roba.majzoub/agentic_hematology/logs/batch_traced_%j.out
#SBATCH --error=/home/roba.majzoub/agentic_hematology/logs/batch_traced_%j.err

set -euo pipefail

REPO_ROOT=/home/roba.majzoub
PROJECT="${REPO_ROOT}/agentic_hematology"
mkdir -p "${PROJECT}/logs"

cd "${PROJECT}"

export PYTHONUNBUFFERED=1
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

/home/roba.majzoub/envs/agentic/bin/python run_orchestrator.py \
  --patients-dir wbc_unified/cv/generated/patients \
  --yolo-weights wbc_unified/cv/runs/detector/train/weights/best.pt \
  --effnet-weights wbc_unified/cv/runs/attribute/train/best_attr.pt \
  --llm-model /home/roba.majzoub/agentic_hematology/models/Qwen3-VL-4B-Instruct \
  --lora-adapter /home/roba.majzoub/agentic_hematology/models/wbc_qwen3_4b_sft_lora \
  --out outputs/batch_traced/ \
  --instruction "diagnose this case"
