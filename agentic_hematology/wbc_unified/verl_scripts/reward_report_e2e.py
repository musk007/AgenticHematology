"""GRPO reward: stage-1 det/attr (frozen CV) + report quality vs GT report."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_PROJECT = Path(__file__).resolve().parents[1]
_REPORT = _PROJECT / "report"
for _p in (_REPORT, _PROJECT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from verl_scripts.reward_report import compute_score as _report_score  # noqa: E402

DATA_SOURCE = "leukemia_report"

W_REPORT = float(os.environ.get("REWARD_W_REPORT", "0.50"))
W_DET = float(os.environ.get("REWARD_W_DET", "0.25"))
W_ATTR = float(os.environ.get("REWARD_W_ATTR", "0.25"))


def _coerce_extra(extra_info) -> dict:
    if extra_info is None:
        return {}
    if hasattr(extra_info, "item"):
        extra_info = extra_info.item()
    return dict(extra_info) if isinstance(extra_info, dict) else {}


def compute_score(
    data_source: str,
    solution_str: str,
    ground_truth: str,
    extra_info: dict | None = None,
) -> float | dict:
    extra = _coerce_extra(extra_info)
    ds = str(data_source.item() if hasattr(data_source, "item") else data_source)
    if ds not in (DATA_SOURCE, "leukemia_report_e2e"):
        return 0.0

    report_out = _report_score(DATA_SOURCE, solution_str, ground_truth, extra)
    if not isinstance(report_out, dict):
        report_out = {"score": float(report_out)}

    det = float(extra.get("cv_det_score", extra.get("cv_cell_det", 0.0)) or 0.0)
    attr = float(extra.get("cv_attr_score", extra.get("cv_cell_attr", 0.0)) or 0.0)
    report_score = float(report_out.get("score", 0.0))

    total = W_REPORT * report_score + W_DET * det + W_ATTR * attr
    total = round(max(0.0, min(1.0, total)), 4)

    return {
        "score": total,
        "acc": total,
        "report_score": report_score,
        "det_score": round(det, 4),
        "attr_score": round(attr, 4),
        "report_diff_score": report_out.get("diff_score"),
        "report_fmt_score": report_out.get("fmt_score"),
        "report_imp_score": report_out.get("imp_score"),
        "report_coverage": report_out.get("coverage"),
        "report_mae_pct": report_out.get("mae_pct"),
        "reward_w_report": W_REPORT,
        "reward_w_det": W_DET,
        "reward_w_attr": W_ATTR,
    }
