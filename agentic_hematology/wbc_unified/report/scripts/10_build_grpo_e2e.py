#!/usr/bin/env python3
"""Build GRPO parquet with pred-summary prompts + CV det/attr scores in extra_info."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT_ROOT))
from bootstrap import DEFAULT_CONFIG, PROJECT_ROOT, setup_paths

setup_paths()

from src.config import load_config
from src.grpo_e2e_data import build_grpo_e2e_parquet, rebuild_sft_from_new_gt


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--val-ratio", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--rebuild-sft", action="store_true", help="Also rebuild report_sft.jsonl from new GT reports")
    args = p.parse_args()

    cfg = load_config(args.config)
    artifact = Path(cfg["artifact_root"])
    verl = cfg.get("verl", {})
    grpo_dir = Path(verl.get("grpo_e2e_parquet", artifact / "data/verl/grpo_e2e"))
    pred_paths = [Path(x) for x in cfg["predictions"]]
    agg = cfg.get("aggregation", {})

    train_p, val_p = build_grpo_e2e_parquet(
        reports_gt_dir=Path(cfg["reports_gt_dir"]),
        data_root=Path(cfg["data_root"]),
        predictions_paths=pred_paths,
        summaries_pred_dir=Path(cfg["output"]["summaries_pred"]),
        summaries_gt_dir=Path(cfg["output"]["summaries_gt"]),
        out_dir=grpo_dir,
        val_ratio=args.val_ratio,
        seed=args.seed,
        conf_threshold=float(agg.get("conf_threshold", 0.25)),
    )
    print(f"GRPO e2e train={train_p}")
    print(f"GRPO e2e val={val_p}")

    if args.rebuild_sft:
        n = rebuild_sft_from_new_gt(
            Path(cfg["output"]["summaries_gt"]),
            Path(cfg["reports_gt_dir"]),
            Path(cfg["output"]["sft_dataset"]),
        )
        print(f"Rebuilt SFT jsonl: {n} rows -> {cfg['output']['sft_dataset']}")


if __name__ == "__main__":
    main()
