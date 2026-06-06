#!/usr/bin/env python3
"""Print human-readable metrics from metrics_llm_pred.json."""
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
from src.report_metrics import format_metrics_table


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--metrics", type=Path, default=None)
    ap.add_argument("--sort-by", default="report_reward_score", help="per_case field to sort")
    ap.add_argument("--top", type=int, default=0, help="Show top-N per_case rows (0=all)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    path = args.metrics or Path(cfg["output"]["eval"]) / "metrics_llm_pred.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    agg = data.get("aggregate") or {}
    print(format_metrics_table(agg))

    per = data.get("per_case") or {}
    if not per:
        return
    key = args.sort_by
    rows = sorted(
        per.items(),
        key=lambda x: float(x[1].get(key) or -1),
        reverse=True,
    )
    if args.top > 0:
        rows = rows[: args.top]
    print(f"\n--- per_case (sorted by {key}) ---")
    cols = (
        "patient_id",
        "disease_label_file",
        "report_reward_score",
        "report_mae_pct",
        "report_class_recall",
        "report_imp_score",
        "summary_mae_pct",
        "e2e_score",
    )
    print("\t".join(cols))
    for pid, r in rows:
        print("\t".join(str(r.get(c, "")) for c in cols))


if __name__ == "__main__":
    main()
