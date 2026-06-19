#!/usr/bin/env python3
"""
Deprecated: patient_WBC_stats JSON training removed.

Use ``train_leukemia_from_dinobloom.py`` instead — it trains RF/XGBoost/LightGBM on
features extracted from the live YOLO + DinoBloom + MLP detection pipeline.
Labels come from LLD image filenames (``{patient}_*_{DIAGNOSIS}.png``).
"""
from __future__ import annotations

import sys


def main() -> None:
    raise SystemExit(
        "train_leukemia_from_stats.py no longer uses patient_WBC_stats JSON.\n\n"
        "Train leukemia classifiers from detection pipeline features instead:\n"
        "  python train_leukemia_from_dinobloom.py --backend all --device 0\n\n"
        "Run reports from live detection + aggregation:\n"
        "  python run_orchestrator.py --lld-split test --backend dinobloom \\\n"
        "    --classifier-model outputs/ablations/classifier/dinobloom/random_forest/leukemia_random_forest.pkl \\\n"
        "    --dinobloom-attr-weights wbc_unified/cv/runs/attribute_dinobloom/train/best_attr_dinobloom.pt \\\n"
        "    --device 0 --out outputs/reports\n"
    )


if __name__ == "__main__":
    main()
