#!/bin/bash
# Run one patient/case through the agentic hematology orchestrator.
#
# Example:
#   cd /home/roba.majzoub
#   sbatch \
#     --export=ALL,CONDA_ENV_PATH=/path/to/env,CASE_ID=PATIENT_001,IMAGES_GLOB='/path/to/patient_001/*.png',YOLO_WEIGHTS=/path/to/yolo/best.pt,EFFNET_WEIGHTS=/path/to/best_attr.pt \
#     agentic_hematology/sbatch_orchestrator.sh
#
# IMPORTANT: IMAGES_GLOB must resolve to ONE patient's image tiles per run.
# The aggregator reconstructs the global canvas from filenames like
# patient_<x>_<y>.png; mixing tiles from multiple patients will merge their
# cells into a single (wrong) differential.
#
# Optional:
#   USE_AGENT=1|0                  enable the agentic LLM router + reflection loop (default 1)
#   AGENT_LLM_MODEL=/path/to/Qwen  model used by the router + reflection agent
#   MAX_REFLECT_ITERS=2            max reflection-agent iterations before forced escalation
#   REPORT_BACKEND=template|local-llm
#   LLM_MODEL=/nfs-stor/zongyan/pretrained_models/Qwen3.5-2B   (report backend model)
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

# --- Agentic controls -------------------------------------------------------
# The LLM router + reflection loop are what make this pipeline agentic. They
# need a Qwen3 model to load EVEN WHEN the report backend is "template",
# because routing and reflection are separate from report generation.
USE_AGENT="${USE_AGENT:-1}"
AGENT_LLM_MODEL="${AGENT_LLM_MODEL:-/nfs-stor/zongyan/pretrained_models/Qwen3.5-2B}"
MAX_REFLECT_ITERS="${MAX_REFLECT_ITERS:-2}"

# IMAGES_GLOB MUST point at a single patient's tiles.
IMAGES_GLOB="${IMAGES_GLOB:-}"
YOLO_WEIGHTS="${YOLO_WEIGHTS:-${PROJECT}/wbc_unified/cv/runs/detector/train/weights/best.pt}"
EFFNET_WEIGHTS="${EFFNET_WEIGHTS:-${PROJECT}/wbc_unified/cv/runs/attribute/train/best_attr.pt}"

if [[ -z "${IMAGES_GLOB}" ]]; then
  echo "ERROR: set IMAGES_GLOB to a SINGLE patient's image path/glob, e.g. /data/patient_001/*.png" >&2
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

if [[ "${USE_AGENT}" == "1" && ! -e "${AGENT_LLM_MODEL}" ]]; then
  echo "ERROR: USE_AGENT=1 but AGENT_LLM_MODEL not found: ${AGENT_LLM_MODEL}" >&2
  echo "       Set AGENT_LLM_MODEL to your Qwen3 path, or set USE_AGENT=0 to run" >&2
  echo "       the deterministic (non-agentic) pipeline." >&2
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

if [[ "${NO_HALF}" == "1" ]]; then
  CMD+=(--no-half)
fi

# --- Agentic vs deterministic ----------------------------------------------
if [[ "${USE_AGENT}" == "1" ]]; then
  CMD+=(--max-reflect-iterations "${MAX_REFLECT_ITERS}")
  # The agent (router + reflection) needs a model even when the report itself
  # is templated. If the report backend is local-llm, --llm-model is supplied
  # below and reused by the agent, so only add it here for non-llm backends.
  if [[ "${REPORT_BACKEND}" != "local-llm" ]]; then
    CMD+=(--llm-model "${AGENT_LLM_MODEL}")
  fi
else
  CMD+=(--no-agent)
fi

# --- Report backend model ---------------------------------------------------
if [[ "${REPORT_BACKEND}" == "local-llm" ]]; then
  CMD+=(--llm-model "${LLM_MODEL:-${AGENT_LLM_MODEL}}")
  if [[ -n "${LORA_ADAPTER:-}" ]]; then
    CMD+=(--lora-adapter "${LORA_ADAPTER}")
  fi
  CMD+=(--max-new-tokens "${MAX_NEW_TOKENS:-768}")
  CMD+=(--temperature "${TEMPERATURE:-0.0}")
fi

echo "Running orchestrator (USE_AGENT=${USE_AGENT}, REPORT_BACKEND=${REPORT_BACKEND}):"
printf ' %q' "${CMD[@]}"
echo

"${CMD[@]}"