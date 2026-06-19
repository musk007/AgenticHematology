"""Patient-level leukemia classification from aggregated WBC findings (LLD)."""
from __future__ import annotations

import json
import pickle
from pathlib import Path

from .schemas import AggregatedFindings, DetectionResult, LeukemiaClassification

DEFAULT_CLASSES = ("ALL", "AML", "APML", "CLL", "CML")


class LearnedClassifier:
    """Wrapper for a pickled Random Forest / LightGBM / XGBoost classifier."""

    def __init__(self, model_path: str | Path, meta_path: str | Path | None = None):
        model_path = Path(model_path)
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)

        meta_path = Path(meta_path) if meta_path else model_path.with_name(f"{model_path.stem}_meta.json")
        self.feature_keys: list[str] | None = None
        self.backend: str | None = None
        self.classes: list[str] = list(DEFAULT_CLASSES)
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            keys = meta.get("feature_keys") or meta.get("feature_names")
            if isinstance(keys, list) and keys:
                self.feature_keys = [str(k) for k in keys]
            self.backend = meta.get("classifier_backend")
            meta_classes = meta.get("classes")
            if isinstance(meta_classes, list) and meta_classes:
                self.classes = [str(c) for c in meta_classes]

    def _decode_label(self, raw_pred) -> str:
        if isinstance(raw_pred, (str, bytes)) and not str(raw_pred).isdigit():
            return str(raw_pred)
        try:
            idx = int(raw_pred)
        except (TypeError, ValueError):
            return str(raw_pred)
        if 0 <= idx < len(self.classes):
            return self.classes[idx]
        return str(raw_pred)

    def predict(self, features: dict[str, float]) -> LeukemiaClassification | None:
        if not hasattr(self.model, "predict"):
            return None
        keys = self.feature_keys if self.feature_keys else sorted(features)
        row = {k: float(features.get(k, 0.0)) for k in keys}
        try:
            import pandas as pd

            x = pd.DataFrame([row], columns=keys)
        except Exception:
            x = [[row[k] for k in keys]]
        pred = self._decode_label(self.model.predict(x)[0])
        confidence = 0.0
        scores: dict[str, float] = {}
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(x)[0]
            model_classes = getattr(self.model, "classes_", None)
            if self.backend == "xgboost" and model_classes is not None:
                label_names = [
                    self.classes[int(c)] if int(c) < len(self.classes) else str(c)
                    for c in model_classes
                ]
            elif model_classes is not None:
                label_names = [self._decode_label(c) for c in model_classes]
            else:
                label_names = list(self.classes)
            scores = {name: float(p) for name, p in zip(label_names, probs)}
            confidence = max(scores.values()) if scores else 0.0
        return LeukemiaClassification(
            predicted_class=pred,
            confidence=confidence,
            rationale="learned classifier prediction from detection-derived features",
            scores=scores,
        )


class HybridClassifier:
    """Rule-first classifier with optional learned model override."""

    def __init__(self, learned: LearnedClassifier | None = None):
        self.learned = learned

    def classify(
        self,
        findings: AggregatedFindings,
        detection_result: DetectionResult | None = None,
    ) -> LeukemiaClassification:
        from .leukemia_features import build_feature_row_from_findings

        feature_names = self.learned.feature_keys if self.learned and self.learned.feature_keys else None
        features = build_feature_row_from_findings(
            findings,
            feature_names=feature_names,
            detection_result=detection_result,
        )
        if self.learned is not None:
            learned = self.learned.predict(features)
            if learned is not None:
                return learned

        diff = findings.cell_percentages_clinical
        counts = findings.cell_counts
        blast_pct = float(findings.report_ready.get("blast_pct", 0.0))

        if diff.get("Abnormal promyelocyte", 0.0) >= 10.0:
            return self._result("APML", 0.82, "abnormal promyelocytes are enriched")
        if diff.get("Lymphoblast", 0.0) >= 20.0:
            return self._result("ALL", 0.8, "lymphoblast burden meets acute leukemia pattern")
        if diff.get("Myeloblast", 0.0) + diff.get("Monoblast", 0.0) >= 20.0:
            return self._result("AML", 0.8, "myeloid/monocytic blast burden meets acute leukemia pattern")
        if counts.get("Myelocyte", 0) + counts.get("Metamyelocyte", 0) > counts.get("Lymphocyte", 0):
            return self._result("CML", 0.65, "granulocytic precursors dominate the differential")
        if diff.get("Lymphocyte", 0.0) >= 50.0 and blast_pct < 20.0:
            return self._result("CLL", 0.65, "mature lymphocytes dominate without blast threshold")
        if blast_pct >= 20.0:
            return self._result("Acute leukemia, subtype indeterminate", 0.55, "blast threshold is met")
        return self._result("Indeterminate", 0.35, "no subtype-defining differential pattern detected")

    @staticmethod
    def _result(pred: str, confidence: float, rationale: str) -> LeukemiaClassification:
        return LeukemiaClassification(
            predicted_class=pred,
            confidence=confidence,
            rationale=rationale,
            scores={pred: confidence},
        )
