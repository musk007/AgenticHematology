#!/usr/bin/env python3
"""Layer-A metrics: pred patient summaries vs GT summaries."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT_ROOT))
from bootstrap import DEFAULT_CONFIG, PROJECT_ROOT, setup_paths

setup_paths()

from src.config import load_config
from src.report_metrics import compare_summaries


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--pred", type=Path, default=None)
    ap.add_argument("--gt", type=Path, default=None)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    cfg = load_config(args.config)
    pred_dir = args.pred or Path(cfg["output"]["summaries_pred"])
    gt_dir = args.gt or Path(cfg["output"]["summaries_gt"])

    per_case = {}
    maes = []
    for gt_path in sorted(gt_dir.glob("patient_*.json")):
        pid = gt_path.stem.replace("patient_", "")
        pred_path = pred_dir / gt_path.name
        if not pred_path.is_file():
            continue
        pred = json.loads(pred_path.read_text(encoding="utf-8"))
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        m = compare_summaries(pred, gt)
        per_case[pid] = m
        if m.get("summary_mae_pct") is not None:
            maes.append(float(m["summary_mae_pct"]))

    payload = {
        "stage": "stage1_pred_summaries",
        "pred_dir": str(pred_dir.resolve()),
        "gt_dir": str(gt_dir.resolve()),
        "n_cases": len(per_case),
        "mean_summary_mae_pct": round(sum(maes) / len(maes), 4) if maes else None,
        "per_case": per_case,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}  mean_summary_mae_pct={payload['mean_summary_mae_pct']}")


if __name__ == "__main__":
    main()
