#!/usr/bin/env python3
"""Evaluate LLM reports (pred-input) vs GT with layered metrics."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT_ROOT))
from bootstrap import DEFAULT_CONFIG, PROJECT_ROOT, setup_paths

setup_paths()

from src.config import load_config
from src.report_metrics import (
    aggregate_case_metrics,
    evaluate_case,
    format_metrics_table,
    load_summary_dir,
)
from verl_scripts.reward_report import compute_score  # noqa: E402


def eval_pred_reports(
    generated_dir: Path,
    reports_gt_dir: Path,
    summaries_pred_dir: Path | None = None,
    summaries_gt_dir: Path | None = None,
) -> dict:
    pred_summaries = load_summary_dir(summaries_pred_dir)
    gt_summaries = load_summary_dir(summaries_gt_dir)

    per_case: dict[str, dict] = {}
    for gen_path in sorted(generated_dir.glob("case_*_report.md")):
        pid = gen_path.stem.replace("case_", "").replace("_report", "")
        gt_path = reports_gt_dir / gen_path.name
        if not gt_path.is_file():
            continue
        gen_text = gen_path.read_text(encoding="utf-8")
        gt_text = gt_path.read_text(encoding="utf-8")
        pred_sum = pred_summaries.get(pid)
        gt_sum = gt_summaries.get(pid)
        extra = {
            "patient_id": pid,
            "disease_label_file": pred_sum.get("disease_label_file") if pred_sum else None,
        }
        reward = compute_score("leukemia_report", gen_text, gt_text, extra)
        per_case[pid] = evaluate_case(
            pid,
            gen_text,
            gt_text,
            reward,
            pred_summary=pred_sum,
            gt_summary=gt_sum,
            disease_label=extra.get("disease_label_file"),
        )

    aggregate = aggregate_case_metrics(per_case)
    return {
        "schema_version": 1,
        "input_summaries": "predictions",
        "n_cases": len(per_case),
        "per_case": per_case,
        "aggregate": aggregate,
        # legacy keys for backward compatibility
        "mean_reward_score": (aggregate.get("report_reward_score") or {}).get("mean"),
        "mean_mae_differential_pct": (aggregate.get("report_mae_pct") or {}).get("mean"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--generated", type=Path, default=None)
    ap.add_argument("--reports-gt", type=Path, default=None)
    ap.add_argument("--summaries-pred", type=Path, default=None)
    ap.add_argument("--summaries-gt", type=Path, default=None, help="GT summaries for Layer-A metrics")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-print", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    generated = args.generated or Path(cfg["output"]["reports_llm_pred"])
    reports_gt = args.reports_gt or Path(cfg["reports_gt_dir"])
    summaries_pred = args.summaries_pred or Path(cfg["output"]["summaries_pred"])
    summaries_gt = args.summaries_gt or Path(cfg["output"]["summaries_gt"])
    out = args.out or Path(cfg["output"]["eval"]) / "metrics_llm_pred.json"

    result = eval_pred_reports(generated, reports_gt, summaries_pred, summaries_gt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if not args.no_print:
        print(format_metrics_table(result.get("aggregate", {})))
        print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
