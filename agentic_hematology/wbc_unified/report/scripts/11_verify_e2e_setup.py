#!/usr/bin/env python3
"""Smoke-test GRPO e2e parquet + reward (no GPU)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT_ROOT))
from bootstrap import DEFAULT_CONFIG, PROJECT_ROOT, setup_paths

setup_paths()

from src.config import load_config
from verl_scripts.reward_report_e2e import compute_score


def main() -> None:
    cfg = load_config(DEFAULT_CONFIG)
    artifact = Path(cfg["artifact_root"])
    train_p = artifact / "data/verl/grpo_e2e/train.parquet"
    if not train_p.is_file():
        raise SystemExit(f"Missing {train_p} — run: python scripts/10_build_grpo_e2e.py")

    try:
        import pyarrow.parquet as pq

        row = pq.read_table(train_p).slice(0, 1).to_pylist()[0]
        n_rows = pq.read_metadata(train_p).num_rows
    except ImportError:
        import pandas as pd

        df = pd.read_parquet(train_p)
        row = df.iloc[0].to_dict()
        n_rows = len(df)
    extra = row.get("extra_info") or {}
    if hasattr(extra, "item"):
        extra = extra.item()
    gt = row["reward_model"]["ground_truth"]
    sample_report = "# Hematology Report\n\n| Cell Type | % WBC |\n|---|---|\n| Neutrophils | 40 |\n\n**Impression:** Test."
    out = compute_score(row["data_source"], sample_report, gt, extra)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"OK: {n_rows} train rows; patient_id={extra.get('patient_id')}")


if __name__ == "__main__":
    main()
