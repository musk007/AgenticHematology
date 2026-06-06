#!/usr/bin/env bash
# Wrapper — prefer: bash pipeline/run_stage1_infer.sh (from wbc_unified root)
set -euo pipefail
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec bash "$PROJECT/pipeline/run_stage1_infer.sh" "$@"
