#!/usr/bin/env python3
"""Aggregate per-patient summaries from GT attributes (all cases with labels)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT_ROOT))
from bootstrap import DEFAULT_CONFIG, PROJECT_ROOT, setup_paths

setup_paths()

from src.aggregate import aggregate_gt_from_data_root, save_summaries
from src.config import load_config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--data-root", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    data_root = args.data_root or Path(cfg["data_root"])
    out = args.out or Path(cfg["output"]["summaries_gt"])
    agg = cfg.get("aggregation", {})

    print(f"Aggregating GT from {data_root} -> {out}")
    summaries = aggregate_gt_from_data_root(
        data_root,
        splits=("train", "test"),
        blast_classes=agg.get("blast_classes"),
    )
    paths = save_summaries(summaries, out)
    print(f"Saved {len(paths)} patient summaries (GT)")


if __name__ == "__main__":
    main()
