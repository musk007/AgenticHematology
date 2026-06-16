#!/bin/bash
# Agentic batch on the LLD test split (13 patients): reflection, re_aggregate,
# flag_for_review traces saved as case_<id>_agent_trace.json per patient.

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

source /apps/local/anaconda3.10/bin/activate /home/roba.majzoub/envs/agentic/
cd "${PROJECT}"

export PYTHONUNBUFFERED=1
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

CLASSIFIER="${CLASSIFIER:-${PROJECT}/runs/classifier/random_forest/leukemia_random_forest.pkl}"
STATS_JSON="${STATS_JSON:-/home/roba.majzoub/AgenticHematology/data_preprocessing/patient_WBC_stats_NoOveralp.json}"
AGENT_LLM="${AGENT_LLM:-${PROJECT}/models/Qwen3-VL-4B-Instruct}"
OUT_DIR="${OUT_DIR:-${PROJECT}/outputs/batch_traced}"

python run_orchestrator.py \
  --lld-split test \
  --yolo-weights wbc_unified/cv/runs/detector/train/weights/best.pt \
  --effnet-weights wbc_unified/cv/runs/attribute/train/best_attr.pt \
  --classifier-model "${CLASSIFIER}" \
  --stats-json "${STATS_JSON}" \
  --llm-model "${AGENT_LLM}" \
  --max-reflect-iterations 2 \
  --report-backend template \
  --instruction "diagnose this case" \
  --device 0 \
  --out "${OUT_DIR}"

echo "Analyze traces: python analyze_agent_trace.py --agentic-dir ${OUT_DIR}"
