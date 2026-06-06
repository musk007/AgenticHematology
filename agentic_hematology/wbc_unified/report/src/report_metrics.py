"""Metrics for pred-summary -> LLM report vs GT (report + optional summary alignment)."""
from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any

from .eval_report import eval_pair, extract_report_markdown, strip_model_artifacts

# Composite report score weights (aligned with reward_report.py)
W_DIFF = 0.45
W_COV = 0.25
W_FMT = 0.20
W_IMP = 0.05


def _normalize_class(name: str) -> str:
    n = re.sub(r"\s+", " ", name.strip().lower())
    if n.endswith("s") and not n.endswith("ss"):
        n = n[:-1]
    return n


def _pct_dict_mae(pred: dict[str, float], gt: dict[str, float]) -> tuple[float | None, float, int]:
    """MAE over GT classes; returns (mae, matched_count, n_gt_classes)."""
    if not gt:
        return None, 0, 0
    pred_norm = {_normalize_class(k): float(v) for k, v in pred.items()}
    errors: list[float] = []
    matched = 0
    for cls, gt_pct in gt.items():
        key = _normalize_class(cls)
        if key in pred_norm:
            matched += 1
            errors.append(abs(pred_norm[key] - float(gt_pct)))
        else:
            errors.append(float(gt_pct))
    mae = sum(errors) / len(errors) if errors else None
    return mae, matched, len(gt)


def _diff_score_from_mae(mae: float | None) -> float:
    if mae is None:
        return 0.0
    return round(max(0.0, 1.0 - mae / 15.0), 4)


def compare_summaries(pred: dict[str, Any], gt: dict[str, Any]) -> dict[str, Any]:
    """Stage-1 input fidelity: pred detection summary vs GT summary."""
    pred_diff = pred.get("differential_pct") or {}
    gt_diff = gt.get("differential_pct") or {}
    mae, matched, n_gt = _pct_dict_mae(pred_diff, gt_diff)
    pred_classes = {_normalize_class(k) for k in pred_diff}
    gt_classes = {_normalize_class(k) for k in gt_diff}
    extra_in_pred = len(pred_classes - gt_classes)
    return {
        "summary_mae_pct": round(mae, 2) if mae is not None else None,
        "summary_class_recall": round(matched / n_gt, 4) if n_gt else None,
        "summary_n_classes_gt": n_gt,
        "summary_n_classes_pred": len(pred_diff),
        "summary_extra_classes": extra_in_pred,
        "summary_blast_pct_pred": pred.get("blast_pct"),
        "summary_blast_pct_gt": gt.get("blast_pct"),
        "summary_blast_pct_abs_err": (
            round(abs(float(pred.get("blast_pct", 0)) - float(gt.get("blast_pct", 0))), 2)
            if pred.get("blast_pct") is not None and gt.get("blast_pct") is not None
            else None
        ),
        "summary_blast_flag_match": int(
            bool(pred.get("flags", {}).get("blast_threshold_met"))
            == bool(gt.get("flags", {}).get("blast_threshold_met"))
        ),
        "cv_mean_det_conf": pred.get("qc", {}).get("mean_det_conf"),
        "cv_artifact_pct": pred.get("qc", {}).get("pct_class_none"),
        "n_cells_informative_pred": pred.get("n_cells_informative"),
    }


def report_structure_metrics(generated: str) -> dict[str, Any]:
    body = extract_report_markdown(generated)
    raw = strip_model_artifacts(generated)
    has_table = bool(re.search(r"\|[^|\n]+\|[^|\n]+\|", body, re.I))
    has_impression = bool(re.search(r"\*\*impression:\*\*", body, re.I))
    has_title = bool(re.search(r"#\s*hematology\s+report", body, re.I))
    return {
        "report_chars": len(body),
        "report_has_title": int(has_title),
        "report_has_table": int(has_table),
        "report_has_impression": int(has_impression),
        "report_raw_chars": len(raw),
    }


def report_vs_gt_metrics(
    generated: str,
    gt_report: str,
    reward: dict[str, Any],
    table_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Layer B: parsed differential table + reward decomposition."""
    table_row = table_row or eval_pair(generated, gt_report)
    mae = table_row.get("mae_pct")
    n_gt = int(table_row.get("n_classes_gt") or 0)
    matched = int(table_row.get("matched_classes") or 0)
    out = {
        "report_mae_pct": mae,
        "report_class_recall": round(matched / n_gt, 4) if n_gt else None,
        "report_n_classes_gt": n_gt,
        "report_matched_classes": matched,
        "report_diff_score": reward.get("diff_score"),
        "report_coverage": reward.get("coverage"),
        "report_fmt_score": reward.get("fmt_score"),
        "report_imp_score": reward.get("imp_score"),
        "report_reward_score": reward.get("score"),
        "report_penalty": reward.get("penalty"),
        "report_has_table_gen": reward.get("has_table"),
    }
    out["report_diff_score_calc"] = _diff_score_from_mae(mae if mae is not None else None)
    return out


def end_to_end_score(
    report_reward: float | None,
    summary_mae: float | None,
    *,
    w_report: float = 0.7,
    w_summary: float = 0.3,
) -> float | None:
    if report_reward is None:
        return None
    s_in = _diff_score_from_mae(summary_mae) if summary_mae is not None else report_reward
    return round(w_report * float(report_reward) + w_summary * s_in, 4)


def evaluate_case(
    patient_id: str,
    generated: str,
    gt_report: str,
    reward: dict[str, Any],
    pred_summary: dict[str, Any] | None = None,
    gt_summary: dict[str, Any] | None = None,
    disease_label: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "patient_id": patient_id,
        "disease_label_file": disease_label or pred_summary.get("disease_label_file") if pred_summary else None,
    }
    row.update(report_structure_metrics(generated))
    row.update(report_vs_gt_metrics(generated, gt_report, reward))
    if pred_summary and gt_summary:
        row.update(compare_summaries(pred_summary, gt_summary))
    row["e2e_score"] = end_to_end_score(
        row.get("report_reward_score"),
        row.get("summary_mae_pct"),
    )
    return row


def load_summary_dir(directory: Path | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict] = {}
    if not directory or not directory.is_dir():
        return out
    for p in directory.glob("patient_*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        out[str(rec["patient_id"])] = rec
    return out


def _aggregate_values(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None, "std": None, "min": None, "max": None}
    return {
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "std": round(statistics.pstdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def aggregate_case_metrics(per_case: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Macro averages + pass rates over cohort."""
    rows = list(per_case.values())
    if not rows:
        return {}

    def col(key: str) -> list[float]:
        return [float(r[key]) for r in rows if r.get(key) is not None]

    reward_scores = col("report_reward_score")
    report_maes = col("report_mae_pct")
    summary_maes = col("summary_mae_pct")
    e2e = col("e2e_score")

    agg: dict[str, Any] = {
        "n_cases": len(rows),
        "report_reward_score": _aggregate_values(reward_scores),
        "report_mae_pct": _aggregate_values(report_maes),
        "report_class_recall": _aggregate_values(col("report_class_recall")),
        "report_fmt_score": _aggregate_values(col("report_fmt_score")),
        "report_imp_score": _aggregate_values(col("report_imp_score")),
        "summary_mae_pct": _aggregate_values(summary_maes),
        "summary_class_recall": _aggregate_values(col("summary_class_recall")),
        "summary_blast_pct_abs_err": _aggregate_values(col("summary_blast_pct_abs_err")),
        "e2e_score": _aggregate_values(e2e),
        "pass_rate": {},
    }

    if reward_scores:
        agg["pass_rate"]["report_reward_ge_0.70"] = round(
            sum(1 for s in reward_scores if s >= 0.70) / len(reward_scores), 4
        )
        agg["pass_rate"]["report_reward_ge_0.80"] = round(
            sum(1 for s in reward_scores if s >= 0.80) / len(reward_scores), 4
        )
    if report_maes:
        agg["pass_rate"]["report_mae_le_10"] = round(
            sum(1 for m in report_maes if m <= 10.0) / len(report_maes), 4
        )
        agg["pass_rate"]["report_mae_le_5"] = round(
            sum(1 for m in report_maes if m <= 5.0) / len(report_maes), 4
        )

    by_disease: dict[str, list[dict]] = {}
    for r in rows:
        d = r.get("disease_label_file") or "UNKNOWN"
        by_disease.setdefault(str(d), []).append(r)
    agg["by_disease"] = {}
    for disease, drows in sorted(by_disease.items()):
        sub = {str(x["patient_id"]): x for x in drows if x.get("patient_id") is not None}
        if not sub:
            sub = {str(i): drows[i] for i in range(len(drows))}
        agg["by_disease"][disease] = {
            "n_cases": len(drows),
            "mean_report_reward": round(
                statistics.mean(float(x["report_reward_score"]) for x in drows if x.get("report_reward_score") is not None),
                4,
            )
            if any(x.get("report_reward_score") is not None for x in drows)
            else None,
            "mean_report_mae_pct": round(
                statistics.mean(float(x["report_mae_pct"]) for x in drows if x.get("report_mae_pct") is not None),
                2,
            )
            if any(x.get("report_mae_pct") is not None for x in drows)
            else None,
        }

    return agg


def format_metrics_table(aggregate: dict[str, Any]) -> str:
    """Human-readable summary for terminal / logs."""
    lines = [
        "=== Report LLM metrics (pred summary -> report vs GT) ===",
        f"Cases: {aggregate.get('n_cases', 0)}",
        "",
        "Layer B — Generated report vs GT report",
        "  report_reward_score (0-1, GRPO-aligned composite):",
    ]
    rs = aggregate.get("report_reward_score") or {}
    if rs.get("mean") is not None:
        lines.append(f"    mean={rs['mean']}  median={rs['median']}  min={rs['min']}  max={rs['max']}")
    rm = aggregate.get("report_mae_pct") or {}
    if rm.get("mean") is not None:
        lines.append("  report_mae_pct (differential table % error, lower better):")
        lines.append(f"    mean={rm['mean']}  median={rm['median']}  min={rm['min']}  max={rm['max']}")
    pr = aggregate.get("pass_rate") or {}
    if pr:
        lines.append("  pass rates:")
        for k, v in sorted(pr.items()):
            lines.append(f"    {k}: {v:.1%}" if v <= 1 else f"    {k}: {v}")

    sm = aggregate.get("summary_mae_pct") or {}
    if sm.get("mean") is not None:
        lines.extend([
            "",
            "Layer A — CV pred summary vs GT summary (input fidelity)",
            "  summary_mae_pct:",
            f"    mean={sm['mean']}  median={sm['median']}",
        ])
    e2e = aggregate.get("e2e_score") or {}
    if e2e.get("mean") is not None:
        lines.extend([
            "",
            "End-to-end (0.7*report_reward + 0.3*summary fidelity):",
            f"    mean={e2e['mean']}  median={e2e['median']}",
        ])
    by_d = aggregate.get("by_disease") or {}
    if by_d:
        lines.append("\nBy disease:")
        for d, stats in by_d.items():
            lines.append(
                f"  {d}: n={stats['n_cases']}  reward={stats.get('mean_report_reward')}  mae%={stats.get('mean_report_mae_pct')}"
            )
    return "\n".join(lines)
