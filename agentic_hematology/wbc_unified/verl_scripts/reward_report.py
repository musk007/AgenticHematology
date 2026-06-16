"""Custom verl GRPO reward: format + differential table vs GT report."""
from __future__ import annotations

import re
import sys
from pathlib import Path

_PROJECT = Path(__file__).resolve().parents[1]
_REPORT = _PROJECT / "report"
for _p in (_REPORT, _PROJECT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from src.eval_report import eval_pair, extract_report_markdown, strip_model_artifacts  # noqa: E402

DATA_SOURCE = "leukemia_report"


def _coerce_data_source(data_source: str) -> str:
    if hasattr(data_source, "item"):
        return str(data_source.item())
    return str(data_source)


def _coerce_extra_info(extra_info: dict | None) -> dict:
    if extra_info is None:
        return {}
    if hasattr(extra_info, "item"):
        extra_info = extra_info.item()
    return dict(extra_info) if isinstance(extra_info, dict) else {}


def _format_score_partial(text: str) -> float:
    """Graduated structure reward (title / table / impression)."""
    t = extract_report_markdown(text).lower()
    score = 0.0
    if re.search(r"#\s*hematology\s+report", t):
        score += 0.35
    if "| cell type |" in t or (
        "|" in t and "cell" in t and ("%" in t or "percent" in t or "wbc" in t)
    ):
        score += 0.40
    if "**impression:**" in t or re.search(r"\*\*impression\s*:", t):
        score += 0.25
    return min(1.0, score)


def _shaping_bonus(text: str) -> float:
    """Small dense rewards so GRPO gets signal before full report quality."""
    t = strip_model_artifacts(text).lower()
    bonus = 0.0
    if re.search(r"#\s*hematology\s+report", t):
        bonus += 0.08
    elif re.search(r"#\s+\w", t):
        bonus += 0.03
    if re.search(r"\|[^|\n]+\|[^|\n]+\|", t):
        bonus += 0.07
    if "differential" in t or "**specimen:**" in t:
        bonus += 0.04
    if "impression" in t:
        bonus += 0.03
    return min(0.15, bonus)


def _impression_mentions_disease(text: str, disease: str | None) -> float:
    if not disease:
        return 0.0
    body = extract_report_markdown(text)
    imp = re.search(r"\*\*impression:\*\*\s*(.+)", body, re.I | re.S)
    if not imp:
        return 0.0
    block = imp.group(1).split("\n\n")[0].lower()
    d = disease.lower()
    aliases = {
        "all": ["lymphoblastic", "all", "acute lymphoblastic"],
        "aml": ["myeloid", "aml", "acute myeloid"],
        "cml": ["myeloid", "cml", "chronic myeloid", "chronic myelogenous"],
        "cll": ["lymphocytic", "cll", "chronic lymphocytic"],
        "apml": ["promyelocytic", "apml", "acute promyelocytic"],
    }
    keys = aliases.get(d, [d])
    return 1.0 if any(k in block for k in keys) else 0.0


def _degeneration_penalty(text: str, has_table: bool) -> float:
    if has_table:
        return 0.0
    raw = strip_model_artifacts(text)
    if len(raw) < 1200:
        return 0.0
    words = raw.split()
    if len(words) >= 80:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.15:
            return 0.25
    if len(raw) > 5000:
        return 0.15
    return 0.08


def compute_score(
    data_source: str,
    solution_str: str,
    ground_truth: str,
    extra_info: dict | None = None,
) -> float | dict:
    """
    verl custom_reward_function entry (name=compute_score).

    Returns dict with key ``score`` (and ``acc``). All values are numeric for verl metrics.
    """
    if _coerce_data_source(data_source) != DATA_SOURCE:
        return 0.0

    extra_info = _coerce_extra_info(extra_info)
    solution = extract_report_markdown(solution_str or "")

    metrics = eval_pair(solution, ground_truth)
    mae = metrics.get("mae_pct")
    n_gt = metrics.get("n_classes_gt") or 0
    matched = metrics.get("matched_classes") or 0
    gen_diff = metrics.get("gen_diff") or {}
    has_table = bool(gen_diff)

    if mae is None or n_gt == 0:
        diff_score = 0.0
    else:
        diff_score = max(0.0, 1.0 - mae / 15.0)

    coverage = matched / n_gt if n_gt else 0.0
    fmt_score = _format_score_partial(solution)
    disease = extra_info.get("disease_label_file")
    imp_score = _impression_mentions_disease(solution, disease)
    shaping = _shaping_bonus(solution_str or "")
    penalty = _degeneration_penalty(solution_str or "", has_table)

    # diff 0.45 + coverage 0.25 + format 0.20 + impression 0.05 + shaping 0.05
    total = (
        0.45 * diff_score
        + 0.25 * coverage
        + 0.20 * fmt_score
        + 0.05 * imp_score
        + 0.05 * shaping
        - penalty
    )
    score = round(max(0.0, min(1.0, total)), 4)

    return {
        "score": score,
        "acc": score,
        "diff_score": round(diff_score, 4),
        "coverage": round(coverage, 4),
        "fmt_score": round(fmt_score, 4),
        "imp_score": round(imp_score, 4),
        "shaping": round(shaping, 4),
        "penalty": round(penalty, 4),
        "mae_pct": float(mae) if mae is not None else -1.0,
        "n_classes_gt": float(n_gt),
        "matched_classes": float(matched),
        "has_table": 1.0 if has_table else 0.0,
    }
