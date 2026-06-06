#!/usr/bin/env python3
"""Aggregate per-patient summaries from CV infer JSON."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT_ROOT))
from bootstrap import DEFAULT_CONFIG, PROJECT_ROOT, setup_paths

setup_paths()

from src.aggregate import aggregate_predictions, save_summaries
from src.config import load_config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--predictions", nargs="*", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--conf", type=float, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    pred_paths = args.predictions or [Path(p) for p in cfg["predictions"]]
    out = args.out or Path(cfg["output"]["summaries_pred"])
    agg = cfg.get("aggregation", {})
    conf = args.conf if args.conf is not None else float(agg.get("conf_threshold", 0.25))

    for p in pred_paths:
        if not p.is_file():
            raise SystemExit(f"Missing predictions file: {p}")

    print(f"Aggregating {len(pred_paths)} prediction file(s) -> {out}")
    summaries = aggregate_predictions(
        pred_paths,
        conf_threshold=conf,
        blast_classes=agg.get("blast_classes"),
    )
    paths = save_summaries(summaries, out)
    print(f"Saved {len(paths)} patient summaries (predictions)")


if __name__ == "__main__":
    main()
