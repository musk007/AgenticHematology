#!/usr/bin/env bash
# Record per-stage eval artifact paths; write pipeline_summary.json at the end.

PIPELINE_EVAL_PATHS=()

pipeline_eval_init() {
  PIPELINE_EVAL_DIR="${1}"
  mkdir -p "$PIPELINE_EVAL_DIR"
  PIPELINE_SUMMARY_JSON="${PIPELINE_EVAL_DIR}/pipeline_summary.json"
  export PIPELINE_EVAL_DIR PIPELINE_SUMMARY_JSON
}

pipeline_eval_record() {
  local stage="$1"
  local key="$2"
  local path="$3"
  PIPELINE_EVAL_PATHS+=("${stage}|${key}|${path}")
}

pipeline_eval_write_summary() {
  export PIPELINE_EVAL_ENTRIES
  PIPELINE_EVAL_ENTRIES="$(printf '%s\n' "${PIPELINE_EVAL_PATHS[@]}")"
  export PIPELINE_SUMMARY_NOTES="${1:-}"
  python3 - <<'PY'
import json
import os
from datetime import datetime, timezone

stages = {}
for line in os.environ.get("PIPELINE_EVAL_ENTRIES", "").splitlines():
    line = line.strip()
    if not line:
        continue
    stage, key, path = line.split("|", 2)
    stages.setdefault(stage, {})[key] = path

out = {
    "written_at": datetime.now(timezone.utc).isoformat(),
    "pipeline_eval_dir": os.environ["PIPELINE_EVAL_DIR"],
    "notes": os.environ.get("PIPELINE_SUMMARY_NOTES", ""),
    "stages": stages,
}
path = os.environ["PIPELINE_SUMMARY_JSON"]
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("")
print("======== Pipeline eval summary ========")
print(f"SUMMARY_JSON={path}")
for stage, files in stages.items():
    print(f"[{stage}]")
    for k, p in files.items():
        print(f"  {k}: {p}")
PY
}
