#!/usr/bin/env python3
"""
Train patient-level leukemia classifier from patient_WBC_stats JSON.

Does not modify wbc_unified/. Optionally runs read-only infer via wbc_unified/cv/infer.py
when --run-infer is set (uses existing YOLO + EfficientNet weights).

Default feature source: patient_WBC_stats JSON with rich differential + attribute features.

Training uses the LLD train split only; reported accuracy is on the held-out test split
(same 34/13 split as wbc_unified/cv/generated/det_dataset).
"""
from __future__ import annotations

import argparse
import json
import pickle
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from agentic_hematology.leukemia_features import humanize_feature_name  # noqa: E402

WBC_CV = HERE / "wbc_unified" / "cv"
DEFAULT_STATS_JSON = Path(
    "/home/roba.majzoub/AgenticHematology/data_preprocessing/patient_WBC_stats_NoOveralp.json"
)
DEFAULT_DET_WEIGHTS = WBC_CV / "runs" / "detector" / "train" / "weights" / "best.pt"
DEFAULT_ATTR_WEIGHTS = WBC_CV / "runs" / "attribute" / "train" / "best_attr.pt"
DEFAULT_OUT_DIR = HERE / "runs" / "classifier"


def _run_infer(det_weights: Path, attr_weights: Path, device: str) -> None:
    for split, name in (("train", "classifier_fit_infer"), ("test", "infer")):
        cmd = [
            sys.executable,
            str(WBC_CV / "infer.py"),
            "--det-weights",
            str(det_weights),
            "--attr-weights",
            str(attr_weights),
            "--split",
            split,
            "--save-json",
            "--device",
            device,
            "--out",
            str(WBC_CV / "runs" / "predict"),
            "--name",
            name,
        ]
        print(f"Running infer ({split})...")
        result = subprocess.run(cmd, cwd=str(WBC_CV))
        if result.returncode != 0:
            sys.exit(f"infer.py failed for split={split}")


def _build_from_infer(train_json: Path, test_json: Path | None):
    from agentic_hematology.leukemia_features import (
        build_simple_features_from_infer_json,
        discover_lld_split_from_cv,
    )

    X_dicts, y_train, patient_ids_train = build_simple_features_from_infer_json(train_json)
    patient_ids = list(patient_ids_train)

    if test_json and test_json.is_file():
        X_test, y_test, test_ids = build_simple_features_from_infer_json(test_json)
        X_dicts.extend(X_test)
        y_train = y_train + y_test
        patient_ids.extend(test_ids)

    all_keys = sorted({k for d in X_dicts for k in d})
    X = pd.DataFrame([[d.get(k, 0.0) for k in all_keys] for d in X_dicts], columns=all_keys)
    X.index = patient_ids
    y = pd.Series(y_train, index=patient_ids, name="metadata_filename_diagnosis")
    split = discover_lld_split_from_cv(WBC_CV)
    return X, y, all_keys, split


def _make_model(backend: str, random_state: int):
    from agentic_hematology.tabular_classifier import build_tabular_classifier

    return build_tabular_classifier(backend, random_state=random_state)  # type: ignore[arg-type]


def _fit_model(clf, X: pd.DataFrame, y_enc: np.ndarray, y_labels: list[str], backend: str):
    if backend == "xgboost":
        # XGBoost requires contiguous class ids 0..n-1 per fit (CV folds may omit rare classes).
        le = LabelEncoder()
        y_local = le.fit_transform(y_labels)
        weights = compute_sample_weight(class_weight="balanced", y=y_local)
        clf.fit(X, y_local, sample_weight=weights)
        clf._leukemia_label_encoder = le
        return clf
    weights = compute_sample_weight(class_weight="balanced", y=y_enc)
    clf.fit(X, y_labels, sample_weight=weights)
    return clf


def _predict_labels(clf, X: pd.DataFrame, le: LabelEncoder, backend: str) -> list[str]:
    raw = clf.predict(X)
    if backend == "xgboost":
        fit_le: LabelEncoder = getattr(clf, "_leukemia_label_encoder", le)
        return [str(x) for x in fit_le.inverse_transform(raw)]
    if len(raw) and isinstance(raw[0], str):
        return [str(x) for x in raw]
    return list(le.inverse_transform(raw))


def _align_proba_to_encoder(raw: np.ndarray, fit_le: LabelEncoder, le: LabelEncoder) -> np.ndarray:
    aligned = np.zeros((raw.shape[0], len(le.classes_)), dtype=np.float64)
    for j, cls in enumerate(fit_le.classes_):
        global_j = int(np.where(le.classes_ == cls)[0][0])
        aligned[:, global_j] = raw[:, j]
    return aligned


def _predict_proba(clf, X: pd.DataFrame, le: LabelEncoder) -> np.ndarray:
    if not hasattr(clf, "predict_proba"):
        return np.zeros((len(X), len(le.classes_)))
    raw = clf.predict_proba(X)
    fit_le = getattr(clf, "_leukemia_label_encoder", None)
    if fit_le is not None and (
        len(fit_le.classes_) != len(le.classes_)
        or not np.array_equal(fit_le.classes_, le.classes_)
    ):
        return _align_proba_to_encoder(raw, fit_le, le)
    return raw


def _cv_evaluate(
    X: pd.DataFrame,
    y_labels: list[str],
    *,
    backend: str,
    n_splits: int,
    random_state: int,
) -> dict:
    le = LabelEncoder()
    y_enc = le.fit_transform(y_labels)
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    oof_pred = np.empty(len(y_labels), dtype=object)
    fold_acc: list[float] = []

    for fold, (tr, te) in enumerate(skf.split(X, y_enc), start=1):
        clf = _make_model(backend, random_state=random_state + fold)
        y_tr = [y_labels[i] for i in tr]
        y_tr_enc = y_enc[tr]
        _fit_model(clf, X.iloc[tr], y_tr_enc, y_tr, backend)
        preds = _predict_labels(clf, X.iloc[te], le, backend)
        oof_pred[te] = preds
        fold_acc.append(accuracy_score([y_labels[i] for i in te], preds))

    report = classification_report(y_labels, oof_pred, labels=list(le.classes_), zero_division=0)
    cm = confusion_matrix(y_labels, oof_pred, labels=list(le.classes_)).tolist()
    return {
        "backend": backend,
        "cv_folds": n_splits,
        "cv_accuracy_mean": float(np.mean(fold_acc)),
        "cv_accuracy_std": float(np.std(fold_acc)),
        "cv_fold_accuracies": [float(x) for x in fold_acc],
        "classes": list(le.classes_),
        "confusion_matrix_labels": list(le.classes_),
        "confusion_matrix": cm,
        "classification_report": report,
        "oof_predictions": {str(i): str(p) for i, p in enumerate(oof_pred)},
    }


def _shap_top_features(
    clf,
    X: pd.DataFrame,
    feature_names: list[str],
    *,
    backend: str,
    top_k: int = 5,
) -> dict[str, list[dict]]:
    per_patient: dict[str, list[dict]] = {}
    index_keys = [str(v) for v in X.index.tolist()] if hasattr(X, "index") else [str(i) for i in range(len(X))]

    if backend == "xgboost":
        try:
            import xgboost as xgb
        except ImportError:
            xgb = None
        if xgb is not None:
            contribs = clf.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
            contribs = np.asarray(contribs, dtype=np.float64)
            n_feat = len(feature_names)
            for row_idx in range(len(X)):
                pred_idx = int(np.argmax(clf.predict_proba(X.iloc[[row_idx]])[0]))
                if contribs.ndim == 3:
                    row_shap = contribs[row_idx, pred_idx, :n_feat]
                else:
                    row_shap = contribs[row_idx, :n_feat]
                order = np.argsort(np.abs(row_shap))[::-1][:top_k]
                per_patient[index_keys[row_idx]] = [
                    {
                        "feature": feature_names[feat_idx],
                        "label": humanize_feature_name(feature_names[feat_idx]),
                        "shap_value": round(float(row_shap[feat_idx]), 4),
                        "direction": "supports" if row_shap[feat_idx] >= 0 else "opposes",
                    }
                    for feat_idx in order
                ]
            return per_patient

    try:
        import shap
    except ImportError:
        shap = None

    if shap is None:
        from agentic_hematology.tabular_classifier import compute_shap_importances

        global_importance = compute_shap_importances(clf, X, feature_names, backend=backend)
        top = sorted(global_importance.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        for idx in range(len(X)):
            per_patient[index_keys[idx]] = [
                {
                    "feature": name,
                    "label": humanize_feature_name(name),
                    "shap_value": 0.0,
                    "direction": "supports",
                    "global_importance": round(score, 4),
                }
                for name, score in top
            ]
        return per_patient

    shap_values = shap.TreeExplainer(clf).shap_values(X.values)
    n_feat = len(feature_names)

    def _row_shap_for_prediction(row_idx: int, pred_idx: int) -> np.ndarray:
        if isinstance(shap_values, list):
            return np.asarray(shap_values[pred_idx][row_idx], dtype=np.float64)[:n_feat]
        arr = np.asarray(shap_values, dtype=np.float64)
        if arr.ndim == 3:
            if arr.shape[0] == len(getattr(clf, "classes_", [])):
                return arr[pred_idx, row_idx, :n_feat]
            if arr.shape[-1] == len(getattr(clf, "classes_", [])):
                return arr[row_idx, :n_feat, pred_idx]
        return arr[row_idx, :n_feat]

    for row_idx in range(len(X)):
        pred_idx = int(np.argmax(clf.predict_proba(X.iloc[[row_idx]])[0]))
        row_shap = _row_shap_for_prediction(row_idx, pred_idx)
        order = np.argsort(np.abs(row_shap))[::-1][:top_k]
        per_patient[index_keys[row_idx]] = [
            {
                "feature": feature_names[feat_idx],
                "label": humanize_feature_name(feature_names[feat_idx]),
                "shap_value": round(float(row_shap[feat_idx]), 4),
                "direction": "supports" if row_shap[feat_idx] >= 0 else "opposes",
            }
            for feat_idx in order
        ]
    return per_patient


def main() -> None:
    ap = argparse.ArgumentParser(description="Train leukemia classifier from patient stats JSON.")
    ap.add_argument("--stats-json", type=Path, default=DEFAULT_STATS_JSON)
    ap.add_argument("--feature-source", choices=("stats", "infer"), default="stats")
    ap.add_argument("--run-infer", action="store_true", help="Run wbc_unified/cv/infer.py first (read-only).")
    ap.add_argument("--det-weights", type=Path, default=DEFAULT_DET_WEIGHTS)
    ap.add_argument("--attr-weights", type=Path, default=DEFAULT_ATTR_WEIGHTS)
    ap.add_argument("--device", default="0")
    ap.add_argument("--backend", choices=("random_forest", "xgboost", "lightgbm"), default="random_forest")
    ap.add_argument("--compare-baseline-rf", action="store_true", help="Also report RF CV when backend != rf.")
    ap.add_argument("--cv-folds", type=int, default=5)
    ap.add_argument("--random-state", type=int, default=42)
    ap.add_argument("--exclude-low-cell-count", action="store_true")
    ap.add_argument("--split-json", type=Path, default=None)
    ap.add_argument("--cv-root", type=Path, default=WBC_CV)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--model-name", default=None, help="Output stem (default: leukemia_<backend>)")
    args = ap.parse_args()

    if args.run_infer:
        if not args.det_weights.is_file():
            sys.exit(f"Detector weights not found: {args.det_weights}")
        if not args.attr_weights.is_file():
            sys.exit(f"Attribute weights not found: {args.attr_weights}")
        _run_infer(args.det_weights, args.attr_weights, args.device)

    if args.feature_source == "infer":
        train_json = WBC_CV / "runs" / "predict" / "classifier_fit_infer" / "train_predictions.json"
        test_json = WBC_CV / "runs" / "predict" / "infer" / "test_predictions.json"
        if not train_json.is_file():
            sys.exit(f"Missing {train_json}. Run with --run-infer first.")
        X, y, feature_names, split = _build_from_infer(train_json, test_json)
        patient_ids = list(y.index)
    else:
        if not args.stats_json.is_file():
            sys.exit(f"Stats JSON not found: {args.stats_json}")
        from agentic_hematology.leukemia_features import (
            build_feature_matrix,
            load_or_create_split,
            load_patient_stats,
        )

        stats = load_patient_stats(args.stats_json)
        split = load_or_create_split(stats, split_path=args.split_json, cv_root=args.cv_root)
        X, y, feature_names, flags = build_feature_matrix(
            stats,
            exclude_low_cell_count=args.exclude_low_cell_count,
        )
        patient_ids = list(y.index)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Patients: {len(patient_ids)}  Features: {len(feature_names)}  Backend: {args.backend}")

    test_ids = [pid for pid in split.get("test", []) if pid in patient_ids]
    train_ids = [pid for pid in split.get("train", []) if pid in patient_ids]
    if not train_ids or not test_ids:
        sys.exit(
            "Could not resolve LLD train/test split. "
            "Provide --split-json or ensure wbc_unified/cv/generated/det_dataset/labels exists."
        )

    y_train = [str(y.loc[pid]) for pid in train_ids]
    y_test = [str(y.loc[pid]) for pid in test_ids]

    print(f"Split: train={len(train_ids)}  test={len(test_ids)}")
    print(f"Train labels: {pd.Series(y_train).value_counts().to_dict()}")
    print(f"Test labels:  {pd.Series(y_test).value_counts().to_dict()}")

    cv_summary = None
    if args.cv_folds > 1:
        n_splits = min(args.cv_folds, len(set(y_train)))
        if n_splits >= 2:
            cv_summary = _cv_evaluate(
                X.loc[train_ids],
                y_train,
                backend=args.backend,
                n_splits=n_splits,
                random_state=args.random_state,
            )
            cv_summary["scope"] = "train_only"
            print(
                f"\n[Train CV {args.backend}] mean accuracy = {cv_summary['cv_accuracy_mean']:.1%} "
                f"(±{cv_summary['cv_accuracy_std']:.1%})"
            )
            print(cv_summary["classification_report"])

    if args.compare_baseline_rf and args.backend != "random_forest":
        n_splits = min(args.cv_folds, len(set(y_train)))
        if n_splits >= 2:
            rf_cv = _cv_evaluate(
                X.loc[train_ids],
                y_train,
                backend="random_forest",
                n_splits=n_splits,
                random_state=args.random_state,
            )
            rf_cv["scope"] = "train_only"
            print(f"\n[Train CV random_forest baseline] mean accuracy = {rf_cv['cv_accuracy_mean']:.1%}")
            if cv_summary is not None:
                cv_summary["random_forest_baseline"] = rf_cv

    le = LabelEncoder()
    le.fit(y_train + y_test)
    y_train_enc = le.transform(y_train)
    clf = _make_model(args.backend, random_state=args.random_state)
    _fit_model(clf, X.loc[train_ids], y_train_enc, y_train, args.backend)

    test_preds = _predict_labels(clf, X.loc[test_ids], le, args.backend)
    test_acc = accuracy_score(y_test, test_preds)
    class_names = list(le.classes_)
    test_summary = {
        "n_train": len(train_ids),
        "n_test": len(test_ids),
        "accuracy": float(test_acc),
        "classification_report": classification_report(
            y_test, test_preds, labels=class_names, zero_division=0
        ),
        "confusion_matrix_labels": class_names,
        "confusion_matrix": confusion_matrix(y_test, test_preds, labels=class_names).tolist(),
        "predictions": {pid: pred for pid, pred in zip(test_ids, test_preds)},
    }
    print(f"\n[Test set] n={len(test_ids)} accuracy={test_acc:.1%}")
    print(test_summary["classification_report"])

    model_stem = args.model_name or f"leukemia_{args.backend}"
    model_path = args.out_dir / f"{model_stem}.pkl"
    meta_path = args.out_dir / f"{model_stem}_meta.json"
    with open(model_path, "wb") as f:
        pickle.dump(clf, f)

    shap_by_patient = _shap_top_features(
        clf, X.loc[test_ids], feature_names, backend=args.backend, top_k=5
    )
    probas = _predict_proba(clf, X.loc[test_ids], le)
    predictions: dict[str, dict] = {}
    for idx, patient_id in enumerate(test_ids):
        prob_map = {cls: float(probas[idx, j]) for j, cls in enumerate(class_names)}
        predictions[patient_id] = {
            "patient_id": patient_id,
            "true_label": y.loc[patient_id],
            "predicted_class": test_preds[idx],
            "confidence": float(max(prob_map.values()) if prob_map else 0.0),
            "class_probabilities": prob_map,
            "split": "test",
            "top_features": shap_by_patient.get(patient_id, []),
        }

    meta = {
        "classifier_backend": args.backend,
        "feature_source": args.feature_source,
        "stats_json": str(args.stats_json),
        "feature_names": feature_names,
        "classes": class_names,
        "n_train": len(train_ids),
        "n_test": len(test_ids),
        "train_cv": cv_summary,
        "test_evaluation": test_summary,
        "split": {"train": train_ids, "test": test_ids},
        "det_weights": str(args.det_weights),
        "attr_weights": str(args.attr_weights),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    pred_path = args.out_dir / f"{model_stem}_predictions.json"
    pred_path.write_text(json.dumps(predictions, indent=2), encoding="utf-8")
    if args.backend == "random_forest":
        legacy_pred_path = args.out_dir / "leukemia_classifier_predictions.json"
        legacy_pred_path.write_text(json.dumps(predictions, indent=2), encoding="utf-8")
    if cv_summary is not None:
        cv_path = args.out_dir / f"{model_stem}_cv_summary.json"
        cv_path.write_text(json.dumps(cv_summary, indent=2), encoding="utf-8")

    print(f"\nSaved model       : {model_path}")
    print(f"Saved meta        : {meta_path}")
    print(f"Saved test preds  : {pred_path} ({len(test_ids)} patients)")
    if args.backend == "random_forest":
        print(f"Saved report input: {args.out_dir / 'leukemia_classifier_predictions.json'}")
    if cv_summary is not None:
        print(f"Saved train CV    : {cv_path}")


if __name__ == "__main__":
    main()
