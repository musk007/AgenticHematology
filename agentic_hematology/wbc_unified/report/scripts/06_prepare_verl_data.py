#!/usr/bin/env python3
"""Build verl SFT parquet from report_sft.jsonl."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT_ROOT))
from bootstrap import DEFAULT_CONFIG, PROJECT_ROOT, setup_paths

setup_paths()

from src.config import load_config
from src.verl_parquet import build_sft_parquet


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--jsonl", type=Path, default=None)
    p.add_argument("--val-ratio", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    cfg = load_config(args.config)
    jsonl = args.jsonl or Path(cfg["output"]["sft_dataset"])
    if not jsonl.is_file():
        raise SystemExit(
            f"Missing SFT jsonl: {jsonl}. Run scripts/10_build_grpo_e2e.py --rebuild-sft first."
        )

    artifact = Path(cfg["artifact_root"])
    verl = cfg.get("verl", {})
    sft_dir = Path(verl.get("sft_parquet", artifact / "data/verl/sft"))

    sft_train, sft_val = build_sft_parquet(
        jsonl, sft_dir, val_ratio=args.val_ratio, seed=args.seed
    )
    print(f"SFT  train={sft_train}  val={sft_val}")
    print("For e2e GRPO parquet use: python scripts/10_build_grpo_e2e.py")


if __name__ == "__main__":
    main()
