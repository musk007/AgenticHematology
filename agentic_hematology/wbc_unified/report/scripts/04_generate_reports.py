#!/usr/bin/env python3
"""Generate markdown reports from patient summary JSON."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT_ROOT))
from bootstrap import DEFAULT_CONFIG, PROJECT_ROOT, setup_paths

setup_paths()

from src.config import load_config
from src.generate import generate_all_from_dir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument(
        "--summaries",
        type=Path,
        default=None,
        help="Input dir (default: summaries/pred for deployment, or gt for dry-run)",
    )
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)

    summaries = args.summaries or Path(cfg["output"]["summaries_pred"])
    out = args.out or Path(cfg["output"]["reports_generated"])

    print("Generating template reports")
    print(f"  summaries: {summaries}")
    print(f"  output:    {out}")
    paths = generate_all_from_dir(summaries, out, cfg)
    print(f"Wrote {len(paths)} reports")


if __name__ == "__main__":
    main()
