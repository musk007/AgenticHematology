#!/usr/bin/env python3
"""Validate 6-class HybridClassifier on held-out LLD test + Helmholtz test patients."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CV = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(CV))

from Train_pipeline import _build_features_labels  # noqa: E402
from agentic_hematology.leukemia_classifier import LearnedClassifier  # noqa: E402
from mll_helmholtz import (  # noqa: E402
    helmholtz_patient_ids_for_split,
    load_helmholtz_split,
    resolve_helmholtz_classifier_predictions_json,
    resolve_helmholtz_split_json,
)


def _predict_all(
    learned: LearnedClassifier,
    X_dicts: list[dict],
    sources: list[str],
) -> list[str]:
    y_pred = []
    for feats, src in zip(X_dicts, sources):
        pred = learned.predict(feats, dataset_source=src)
        y_pred.append(pred.predicted_class if pred else "Indeterminate")
    return y_pred


def _subset_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

    if not y_true:
        return {"n_patients": 0, "accuracy": None}
    labels = sorted(set(y_true) | set(y_pred))
    acc = accuracy_score(y_true, y_pred)
    return {
        "n_patients": len(y_true),
        "accuracy": acc,
        "classes": sorted(set(y_true)),
        "confusion_matrix_labels": labels,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "classification_report": classification_report(
            y_true, y_pred, labels=labels, zero_division=0
        ),
    }


def _class_recall(y_true: list[str], y_pred: list[str], label: str) -> float | None:
    idx = [i for i, y in enumerate(y_true) if y == label]
    if not idx:
        return None
    correct = sum(1 for i in idx if y_pred[i] == label)
    return correct / len(idx)


def _pick(indices: list[int], values: list) -> list:
    return [values[i] for i in indices]


def _resolve_meta_path(model_path: Path) -> Path:
    return model_path.with_name(f"{model_path.stem}_meta.json")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Validate 6-class classifier on LLD test and/or Helmholtz test splits."
    )
    ap.add_argument("--lld-json", type=Path, required=True, help="LLD infer JSON (test split)")
    ap.add_argument(
        "--mll-json",
        type=Path,
        default=None,
        help="Helmholtz predictions JSON (default: helmholtz_predictions.json when using split)",
    )
    ap.add_argument(
        "--helmholtz-split-json",
        type=Path,
        default=None,
        help="Filter Helmholtz eval to test patients (default: cv/generated/helmholtz_split.json)",
    )
    ap.add_argument(
        "--classifier-model",
        type=Path,
        default=CV / "runs" / "classifier" / "leukemia_rf_6class.pkl",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Summary JSON (default: validate_6class_summary.json or _domainnorm.json)",
    )
    ap.add_argument(
        "--combined-only",
        action="store_true",
        help="Skip per-dataset (LLD / Helmholtz) metric breakdown",
    )
    args = ap.parse_args()

    if not args.classifier_model.is_file():
        sys.exit(f"6-class model not found: {args.classifier_model}. Train with --include-healthy-class first.")

    meta_path = _resolve_meta_path(args.classifier_model)
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    domain_normalize = bool(meta.get("domain_normalize", False))
    if args.out is None:
        args.out = (
            CV / "runs" / "classifier" / "validate_6class_summary_domainnorm.json"
            if domain_normalize
            else CV / "runs" / "classifier" / "validate_6class_summary.json"
        )

    mll_json = args.mll_json
    helmholtz_test_ids: set[str] | None = None
    split_path = args.helmholtz_split_json or resolve_helmholtz_split_json()
    if split_path.is_file():
        split_payload = load_helmholtz_split(split_path)
        helmholtz_test_ids = helmholtz_patient_ids_for_split(split_payload, "test")
        if mll_json is None:
            mll_json = resolve_helmholtz_classifier_predictions_json()
        print(f"  Helmholtz test split: {len(helmholtz_test_ids)} patients from {split_path}")

    X_dicts, y_true, sources = _build_features_labels(
        args.lld_json, mll_json, helmholtz_test_ids, return_sources=True
    )
    learned = LearnedClassifier(args.classifier_model, meta_path if meta_path.is_file() else None)
    y_pred = _predict_all(learned, X_dicts, sources)

    combined = _subset_metrics(y_true, y_pred)
    summary = {
        **combined,
        "domain_normalize": domain_normalize,
        "lld_json": str(args.lld_json),
        "mll_json": str(mll_json) if mll_json else None,
        "helmholtz_split_json": str(split_path) if split_path.is_file() else None,
        "model": str(args.classifier_model),
    }
    hz_idx = [i for i, src in enumerate(sources) if src == "helmholtz"]
    lld_idx = [i for i, src in enumerate(sources) if src == "lld"]
    summary["helmholtz_aml_recall"] = _class_recall(
        _pick(hz_idx, y_true),
        _pick(hz_idx, y_pred),
        "AML",
    )
    summary["lld_accuracy"] = _subset_metrics(_pick(lld_idx, y_true), _pick(lld_idx, y_pred)).get("accuracy")

    if not args.combined_only:
        by_dataset: dict[str, dict] = {}
        for name in ("lld", "helmholtz"):
            idx = [i for i, src in enumerate(sources) if src == name]
            metrics = _subset_metrics(_pick(idx, y_true), _pick(idx, y_pred))
            by_dataset[name] = metrics
            if metrics["n_patients"]:
                acc = metrics["accuracy"]
                print(f"\n[{name.upper()}] n={metrics['n_patients']}  accuracy={acc:.1%}")
                print(metrics["classification_report"])
                if name == "helmholtz":
                    aml_recall = _class_recall(_pick(idx, y_true), _pick(idx, y_pred), "AML")
                    if aml_recall is not None:
                        print(f"  Helmholtz AML recall: {aml_recall:.1%}")
        summary["by_dataset"] = by_dataset

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n[COMBINED] n={combined['n_patients']}  accuracy={combined['accuracy']:.1%}")
    print(combined["classification_report"])
    if summary.get("lld_accuracy") is not None:
        print(f"LLD accuracy: {summary['lld_accuracy']:.1%}  (baseline target >= 84.6%)")
    if summary.get("helmholtz_aml_recall") is not None:
        print(f"Helmholtz AML recall: {summary['helmholtz_aml_recall']:.1%}")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
