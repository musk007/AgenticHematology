"""Per-attribute binary classification metrics (GT crops + e2e)."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None


def _binarize_preds(y_pred: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    return (y_pred >= threshold).astype(np.int32)


def _attr_metrics_one(y_true: np.ndarray, y_pred_bin: np.ndarray) -> dict:
    if len(y_true) == 0:
        return {}
    return {
        "accuracy": float(accuracy_score(y_true, y_pred_bin)),
        "precision": float(precision_score(y_true, y_pred_bin, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred_bin, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred_bin, zero_division=0)),
    }


def attribute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    attr_names: list[str],
    *,
    threshold: float = 0.5,
) -> dict:
    """Multi-label metrics; y_true == -1 masks that attribute for the sample."""
    y_pred_bin = _binarize_preds(y_pred, threshold)
    out: dict = {}
    for j, name in enumerate(attr_names):
        mask = y_true[:, j] >= 0
        if not mask.any():
            continue
        yt = y_true[mask, j].astype(np.int32)
        yp = y_pred_bin[mask, j]
        stats = _attr_metrics_one(yt, yp)
        if stats:
            out[name] = stats
    return out


def attribute_metrics_legacy(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    attr_names: list[str],
    *,
    threshold: float = 0.5,
) -> tuple[dict, list]:
    """Legacy val.py alignment: all six attrs labeled 0/1, preds thresholded at 0.5."""
    y_pred_bin = _binarize_preds(y_pred, threshold)
    metrics: dict = {}
    table_rows: list = []
    for j, name in enumerate(attr_names):
        yt = y_true[:, j].astype(np.int32)
        yp = y_pred_bin[:, j]
        stats = _attr_metrics_one(yt, yp)
        metrics[name] = stats
        table_rows.append([name, stats["accuracy"], stats["precision"], stats["recall"], stats["f1"]])
    return metrics, table_rows


def print_legacy_attribute_table(rows: list) -> None:
    headers = ["Attribute", "Accuracy", "Precision", "Recall", "F1"]
    if tabulate is not None:
        print(tabulate(rows, headers=headers, floatfmt=".4f"))
    else:
        print("\t".join(headers))
        for row in rows:
            print("\t".join(str(x) for x in row))
