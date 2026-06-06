"""Generate markdown reports from patient summaries."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .template_report import generate_template_report


def generate_report(summary: dict[str, Any], cfg: dict[str, Any]) -> str:
    return generate_template_report(summary, cfg)


def generate_all_from_dir(summaries_dir: Path, out_dir: Path, cfg: dict[str, Any]) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for path in sorted(summaries_dir.glob("patient_*.json")):
        summary = json.loads(path.read_text())
        pid = summary["patient_id"]
        report = generate_report(summary, cfg)
        out_path = out_dir / f"case_{pid}_report.md"
        out_path.write_text(report, encoding="utf-8")
        written.append(out_path)
    return written
