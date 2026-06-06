"""Build SFT JSONL: detection summary -> GT report markdown."""
from __future__ import annotations

import json
from pathlib import Path

from .prompt import build_messages


def build_sft_jsonl(
    summaries_dir: Path,
    reports_gt_dir: Path,
    out_path: Path,
    system_prompt: str | None = None,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as fout:
        for sum_path in sorted(summaries_dir.glob("patient_*.json")):
            summary = json.loads(sum_path.read_text())
            pid = summary["patient_id"]
            gt_path = reports_gt_dir / f"case_{pid}_report.md"
            if not gt_path.is_file():
                continue
            record = {
                "patient_id": pid,
                "messages": build_messages(
                    summary,
                    system_prompt=system_prompt,
                    assistant_content=gt_path.read_text(encoding="utf-8"),
                ),
            }
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            n += 1
    return n
