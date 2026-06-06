#!/bin/bash
# Run one patient/case through the agentic hematology orchestrator.
#
# Example:
#   cd /home/roba.majzoub
#   sbatch \
#     --export=ALL,CONDA_ENV_PATH=/path/to/env,CASE_ID=PATIENT_001,IMAGES_GLOB='/path/to/images/*.png',YOLO_WEIGHTS=/path/to/yolo/best.pt,EFFNET_WEIGHTS=/path/to/best_attr.pt \
#     agentic_hematology/sbatch_orchestrator.sh
#
# Optional:
#   REPORT_BACKEND=template|local-llm
#   LLM_MODEL=/nfs-stor/zongyan/pretrained_models/Qwen3.5-2B
#   LORA_ADAPTER=/path/to/lora_adapter

#SBATCH --job-name=wbc_agent
#SBATCH --time=4:00:00
#SBATCH --nodes=1
#SBATCH --partition=cscc-gpu-p
#SBATCH --qos=cscc-gpu-qos
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --output=/home/roba.majzoub/agentic_hematology/logs/sbatch_orchestrator_%j.out
#SBATCH --error=/home/roba.majzoub/agentic_hematology/logs/sbatch_orchestrator_%j.err

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/roba.majzoub}"
PROJECT="${PROJECT:-${REPO_ROOT}/agentic_hematology}"
mkdir -p "${PROJECT}/logs"
# project_out="/nfs-stor/roba.majzoub"

CASE_ID="${CASE_ID:-PATIENT_001}"
INSTRUCTION="${INSTRUCTION:-diagnose this case}"
REPORT_BACKEND="${REPORT_BACKEND:-template}"
OUT_DIR="${OUT_DIR:-${PROJECT}/outputs/${CASE_ID}}"
DEVICE="${DEVICE:-0}"
CONF_THRESHOLD="${CONF_THRESHOLD:-0.25}"
IOU_THRESHOLD="${IOU_THRESHOLD:-0.5}"
DET_IMGSZ="${DET_IMGSZ:-512}"
DET_BATCH="${DET_BATCH:-1}"
NO_HALF="${NO_HALF:-0}"

AGENT_LLM_MODEL="${AGENT_LLM_MODEL:-/nfs-stor/zongyan/pretrained_models/Qwen3.5-2B}"
USE_AGENT="${USE_AGENT:-1}"
MAX_REFLECT_ITERS="${MAX_REFLECT_ITERS:-2}"

IMAGES_GLOB="${IMAGES_GLOB:-/home/roba.majzoub/agentic_hematology/wbc_unified/cv/generated/det_dataset/images/test}"
YOLO_WEIGHTS="${YOLO_WEIGHTS:-${PROJECT}/wbc_unified/cv/runs/detector/train/weights/best.pt}"
EFFNET_WEIGHTS="${EFFNET_WEIGHTS:-${PROJECT}/wbc_unified/cv/runs/attribute/train/best_attr.pt}"

if [[ -z "${IMAGES_GLOB}" ]]; then
  echo "ERROR: set IMAGES_GLOB to the patient image path/glob, e.g. /data/patient/*.png" >&2
  exit 2
fi

if [[ ! -f "${YOLO_WEIGHTS}" ]]; then
  echo "ERROR: YOLO_WEIGHTS not found: ${YOLO_WEIGHTS}" >&2
  exit 2
fi

if [[ ! -f "${EFFNET_WEIGHTS}" ]]; then
  echo "ERROR: EFFNET_WEIGHTS not found: ${EFFNET_WEIGHTS}" >&2
  exit 2
fi

activate_conda_env() {
  if [[ -n "${CONDA_ENV_PATH:-}" ]]; then
    local d
    for d in "${CONDA_ROOT:-}" "$HOME/miniconda3" "$HOME/anaconda3" /apps/local/anaconda3; do
      [[ -n "${d}" ]] || continue
      if [[ -f "${d}/etc/profile.d/conda.sh" ]]; then
        # shellcheck source=/dev/null
        source "${d}/etc/profile.d/conda.sh"
        conda activate "${CONDA_ENV_PATH}"
        return 0
      fi
    done
    echo "ERROR: CONDA_ENV_PATH was set, but conda.sh was not found. Set CONDA_ROOT." >&2
    exit 2
  fi

  if [[ -n "${CONDA_ENV:-}" ]]; then
    local d
    for d in "${CONDA_ROOT:-}" "$HOME/miniconda3" "$HOME/anaconda3" /apps/local/anaconda3; do
      [[ -n "${d}" ]] || continue
      if [[ -f "${d}/etc/profile.d/conda.sh" ]]; then
        # shellcheck source=/dev/null
        source "${d}/etc/profile.d/conda.sh"
        conda activate "${CONDA_ENV}"
        return 0
      fi
    done
  fi
}

activate_conda_env

export PYTHONUNBUFFERED=1
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

mkdir -p "${OUT_DIR}"
cd "${REPO_ROOT}"

CMD=(
  python3 agentic_hematology/run_orchestrator.py
  --case-id "${CASE_ID}"
  --backend wbc-unified
  --images "${IMAGES_GLOB}"
  --yolo-weights "${YOLO_WEIGHTS}"
  --effnet-weights "${EFFNET_WEIGHTS}"
  --instruction "${INSTRUCTION}"
  --report-backend "${REPORT_BACKEND}"
  --device "${DEVICE}"
  --conf-threshold "${CONF_THRESHOLD}"
  --iou-threshold "${IOU_THRESHOLD}"
  --det-imgsz "${DET_IMGSZ}"
  --det-batch "${DET_BATCH}"
  --out "${OUT_DIR}"
)

if [[ "${USE_AGENT}" == "1" ]]; then
  CMD+=(--max-reflect-iterations "${MAX_REFLECT_ITERS}")
  # agent needs a model for routing + reflection even when the report is templated
  if [[ "${REPORT_BACKEND}" != "local-llm" ]]; then
    CMD+=(--llm-model "${AGENT_LLM_MODEL}")
  fi
else
  CMD+=(--no-agent)
fi

if [[ "${NO_HALF}" == "1" ]]; then
  CMD+=(--no-half)
fi

if [[ "${REPORT_BACKEND}" == "local-llm" ]]; then
  CMD+=(--llm-model "${LLM_MODEL:-/nfs-stor/zongyan/pretrained_models/Qwen3.5-2B}")
  if [[ -n "${LORA_ADAPTER:-}" ]]; then
    CMD+=(--lora-adapter "${LORA_ADAPTER}")
  fi
  CMD+=(--max-new-tokens "${MAX_NEW_TOKENS:-768}")
  CMD+=(--temperature "${TEMPERATURE:-0.0}")
fi

echo "Running orchestrator:"
printf ' %q' "${CMD[@]}"
echo

"${CMD[@]}"
