"""Patient-level tabular classifiers (Random Forest / LightGBM / XGBoost) for LLD features."""
from __future__ import annotations

from collections import Counter
from typing import Any, Literal

import numpy as np
from sklearn.preprocessing import LabelEncoder

Backend = Literal["random_forest", "lightgbm", "xgboost"]


def compute_balanced_sample_weights(y: list[int] | np.ndarray) -> np.ndarray:
    """Inverse-frequency sample weights (multiclass analogue of balanced class weights)."""
    y_arr = np.asarray(y, dtype=np.int64)
    counts = np.bincount(y_arr)
    counts = np.maximum(counts, 1)
    n_samples = len(y_arr)
    n_classes = len(counts)
    class_weights = n_samples / (n_classes * counts.astype(np.float64))
    return class_weights[y_arr]


def build_tabular_classifier(
    backend: Backend = "lightgbm",
    *,
    random_state: int = 42,
) -> Any:
    if backend == "random_forest":
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier(
            n_estimators=500,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        )

    if backend == "lightgbm":
        try:
            import lightgbm as lgb
        except ImportError as exc:
            raise ImportError(
                "lightgbm is required for --classifier-backend lightgbm. "
                "Install with: pip install lightgbm"
            ) from exc
        return lgb.LGBMClassifier(
            objective="multiclass",
            n_estimators=300,
            learning_rate=0.05,
            max_depth=5,
            num_leaves=31,
            min_child_samples=2,
            subsample=0.9,
            colsample_bytree=0.9,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
            verbose=-1,
        )

    if backend == "xgboost":
        try:
            import xgboost as xgb
        except ImportError as exc:
            raise ImportError(
                "xgboost is required for --classifier-backend xgboost. "
                "Install with: pip install xgboost"
            ) from exc
        return xgb.XGBClassifier(
            objective="multi:softprob",
            n_estimators=300,
            learning_rate=0.05,
            max_depth=5,
            min_child_weight=1,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            random_state=random_state,
            n_jobs=-1,
            verbosity=0,
        )

    raise ValueError(f"Unknown backend: {backend}")


def fit_tabular_classifier(
    clf: Any,
    X,
    y_labels: list[str],
    *,
    backend: Backend,
) -> tuple[Any, LabelEncoder]:
    le = LabelEncoder()
    y_enc = le.fit_transform(y_labels)
    sample_weight = compute_balanced_sample_weights(y_enc)
    if backend == "xgboost":
        clf.fit(X, y_enc, sample_weight=sample_weight)
    else:
        clf.fit(X, y_labels, sample_weight=sample_weight)
    return clf, le


def native_feature_importances(
    clf: Any,
    feature_keys: list[str],
) -> dict[str, float]:
    importances = getattr(clf, "feature_importances_", None)
    if importances is None:
        return {}
    total = float(np.sum(importances)) or 1.0
    ranked = sorted(
        zip(feature_keys, importances.tolist()),
        key=lambda item: item[1],
        reverse=True,
    )
    return {name: float(score / total) for name, score in ranked}


def _normalize_importance_dict(
    feature_keys: list[str],
    mean_abs: np.ndarray,
) -> dict[str, float]:
    mean_abs = np.asarray(mean_abs, dtype=np.float64).reshape(-1)
    if len(mean_abs) != len(feature_keys):
        return {}
    total = float(np.sum(mean_abs)) or 1.0
    ranked = sorted(
        zip(feature_keys, mean_abs.tolist()),
        key=lambda item: item[1],
        reverse=True,
    )
    return {name: float(score / total) for name, score in ranked}


def compute_xgboost_shap_importances(
    clf: Any,
    X,
    feature_keys: list[str],
    *,
    max_samples: int = 128,
) -> dict[str, float]:
    """Mean |SHAP| from XGBoost native pred_contribs (multiclass-safe with XGBoost 3.x)."""
    try:
        import xgboost as xgb
    except ImportError:
        return {}

    n = min(len(X), max_samples)
    if n == 0:
        return {}
    x_sample = X.iloc[:n] if hasattr(X, "iloc") else np.asarray(X[:n], dtype=np.float64)
    try:
        contribs = clf.get_booster().predict(xgb.DMatrix(x_sample), pred_contribs=True)
    except Exception:
        return {}

    arr = np.abs(np.asarray(contribs, dtype=np.float64))
    if arr.ndim == 2:
        mean_abs = arr[:, :-1].mean(axis=0)
    elif arr.ndim == 3:
        mean_abs = arr[:, :, :-1].mean(axis=(0, 1))
    else:
        return {}
    return _normalize_importance_dict(feature_keys, mean_abs)


def compute_shap_importances(
    clf: Any,
    X,
    feature_keys: list[str],
    *,
    backend: Backend | None = None,
    max_samples: int = 128,
) -> dict[str, float]:
    """Mean |SHAP| per feature (averaged across classes for multiclass)."""
    if backend == "xgboost" or type(clf).__module__.startswith("xgboost"):
        return compute_xgboost_shap_importances(clf, X, feature_keys, max_samples=max_samples)

    try:
        import shap
    except ImportError:
        return {}

    n = min(len(X), max_samples)
    if n == 0:
        return {}
    x_sample = X.iloc[:n] if hasattr(X, "iloc") else np.asarray(X[:n], dtype=np.float64)
    try:
        shap_values = shap.TreeExplainer(clf).shap_values(x_sample)
    except Exception:
        return {}

    if isinstance(shap_values, list):
        stacked = np.stack([np.abs(np.asarray(v)) for v in shap_values], axis=0)
        mean_abs = stacked.mean(axis=(0, 1))
    else:
        arr = np.abs(np.asarray(shap_values))
        mean_abs = arr.mean(axis=0)
        if mean_abs.ndim > 1:
            mean_abs = mean_abs.mean(axis=tuple(range(1, mean_abs.ndim)))

    return _normalize_importance_dict(feature_keys, mean_abs)


def summarize_label_counts(y_raw: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(y_raw).items()))
