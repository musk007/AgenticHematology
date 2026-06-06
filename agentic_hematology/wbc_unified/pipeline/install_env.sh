#!/usr/bin/env bash
# SLA_Det environment setup for wbc_unified (CV + LLM).
#
#   cd wbc_unified
#   bash pipeline/install_env.sh              # all
#   bash pipeline/install_env.sh stage1       # cv only
#   bash pipeline/install_env.sh llm          # verl + vLLM
#   bash pipeline/install_env.sh verify

set -euo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CV_REQ="$PROJECT/cv/requirements.txt"
LLM_INSTALL="$PROJECT/verl_scripts/install.sh"

CONDA_ENV="${CONDA_ENV:-SLA_Det}"
CREATE_ENV="${CREATE_ENV:-0}"
MODE="${1:-all}"

_run_pip() {
  if [ "${DRY_RUN:-0}" = "1" ]; then echo "[dry-run] pip $*"; return 0; fi
  pip "$@"
}

_init_conda() {
  local d
  for d in "${CONDA_ROOT:-}" "$HOME/anaconda3" "$HOME/miniconda3" /apps/local/anaconda3; do
    [ -n "$d" ] || continue
    if [ -f "$d/etc/profile.d/conda.sh" ]; then
      # shellcheck source=/dev/null
      source "$d/etc/profile.d/conda.sh"
      return 0
    fi
  done
  echo "ERROR: conda not found" >&2
  exit 1
}

_activate_conda_env() {
  _init_conda
  if conda env list | awk '{print $1}' | grep -qx "$CONDA_ENV"; then
    conda activate "$CONDA_ENV"
    return 0
  fi
  if [ "$CREATE_ENV" = "1" ]; then
    conda create -y -n "$CONDA_ENV" python=3.10
    conda activate "$CONDA_ENV"
    return 0
  fi
  echo "ERROR: env '$CONDA_ENV' not found. Use CREATE_ENV=1" >&2
  exit 1
}

install_stage1() {
  echo "========== Stage-1: cv =========="
  _run_pip install --upgrade pip
  _run_pip install -r "$CV_REQ"
}

install_llm() {
  echo "========== LLM: verl + vLLM =========="
  bash "$LLM_INSTALL" all
}

verify_env() {
  echo "========== verify =========="
  python3 -c "import sys; print('python', sys.version.split()[0])"
  python3 - <<PY
import importlib
checks = [
    'torch','torchvision','ultralytics','numpy','yaml','tqdm','PIL','sklearn',
    'pandas','transformers','ray','vllm','verl',
]
for mod in checks:
    m = {'yaml':'yaml','PIL':'PIL','sklearn':'sklearn'}.get(mod, mod)
    try:
        importlib.import_module(m)
        print(f'  OK {mod}')
    except Exception as e:
        print(f'  MISS {mod}: {e}')
PY
}

case "$MODE" in
  stage1) _activate_conda_env; install_stage1 ;;
  llm) _activate_conda_env; install_llm ;;
  verify) _activate_conda_env; verify_env ;;
  all|"") _activate_conda_env; install_stage1; install_llm; verify_env ;;
  *) echo "Usage: $0 [all|stage1|llm|verify]"; exit 1 ;;
esac
