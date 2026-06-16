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
#   BACKEND=wbc-unified|dinobloom
#   ATTRIBUTE_MODEL=effnet|dinobloom
#   CLASSIFIER_MODEL=${PROJECT}/wbc_unified/cv/runs/classifier/leukemia_rf.pkl
#   DINOBLOOM_WEIGHTS=/path/to/DinoBloom-B.pth
#   DINOBLOOM_ATTR_WEIGHTS=${PROJECT}/wbc_unified/cv/runs/attribute_dinobloom/train/best_attr_probes.joblib

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
BACKEND="${BACKEND:-dinobloom}"
ATTRIBUTE_MODEL="${ATTRIBUTE_MODEL:-dinobloom}"
DINOBLOOM_VARIANT="${DINOBLOOM_VARIANT:-l}"
DINOBLOOM_WEIGHTS="${DINOBLOOM_WEIGHTS:-auto}"
DINOBLOOM_ATTR_MODE="${DINOBLOOM_ATTR_MODE:-probes}"
DINOBLOOM_ATTR_WEIGHTS="${DINOBLOOM_ATTR_WEIGHTS:-${PROJECT}/runs/attribute_dinobloom/train/best_attr_dinobloom.pt}"
CLASSIFIER_MODEL="${CLASSIFIER_MODEL:-${PROJECT}/wbc_unified/cv/runs/classifier/leukemia_gbm.pkl}"

AGENT_LLM_MODEL="${AGENT_LLM_MODEL:-/nfs-stor/roba.majzoub/Qwen3.5-4B}"
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

if [[ "${BACKEND}" == "dinobloom" || "${ATTRIBUTE_MODEL}" == "dinobloom" ]]; then
  if [[ -n "${DINOBLOOM_WEIGHTS:-}" && "${DINOBLOOM_WEIGHTS}" != "auto" && ! -f "${DINOBLOOM_WEIGHTS}" ]]; then
    echo "ERROR: DINOBLOOM_WEIGHTS not found: ${DINOBLOOM_WEIGHTS}" >&2
    exit 2
  fi
fi

if [[ "${BACKEND}" != "dinobloom" && "${ATTRIBUTE_MODEL}" != "dinobloom" ]]; then
  if [[ ! -f "${EFFNET_WEIGHTS}" ]]; then
    echo "ERROR: EFFNET_WEIGHTS not found: ${EFFNET_WEIGHTS}" >&2
    exit 2
  fi
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
  --backend "${BACKEND}"
  --attribute-model "${ATTRIBUTE_MODEL}"
  --images "${IMAGES_GLOB}"
  --yolo-weights "${YOLO_WEIGHTS}"
  --classifier-model "${CLASSIFIER_MODEL}"
  --instruction "${INSTRUCTION}"
  --report-backend "${REPORT_BACKEND}"
  --device "${DEVICE}"
  --conf-threshold "${CONF_THRESHOLD}"
  --iou-threshold "${IOU_THRESHOLD}"
  --det-imgsz "${DET_IMGSZ}"
  --det-batch "${DET_BATCH}"
  --out "${OUT_DIR}"
)

if [[ "${BACKEND}" == "dinobloom" || "${ATTRIBUTE_MODEL}" == "dinobloom" ]]; then
  CMD+=(--dinobloom-weights "${DINOBLOOM_WEIGHTS}")
  CMD+=(--dinobloom-variant "${DINOBLOOM_VARIANT}")
  CMD+=(--dinobloom-attr-mode "${DINOBLOOM_ATTR_MODE}")
  if [[ -n "${DINOBLOOM_ATTR_WEIGHTS:-}" && -f "${DINOBLOOM_ATTR_WEIGHTS}" ]]; then
    CMD+=(--dinobloom-attr-weights "${DINOBLOOM_ATTR_WEIGHTS}")
  fi
else
  CMD+=(--effnet-weights "${EFFNET_WEIGHTS}")
fi

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
