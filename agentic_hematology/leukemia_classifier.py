"""Simple patient-level leukemia classification from aggregated WBC findings."""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

from .schemas import AggregatedFindings, LeukemiaClassification


class LearnedClassifier:
    """Optional wrapper for a pickled sklearn-like classifier."""

    def __init__(self, model_path: str | Path):
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)

    def predict(self, features: dict[str, float]) -> LeukemiaClassification | None:
        if not hasattr(self.model, "predict"):
            return None
        keys = sorted(features)
        x = [[features[k] for k in keys]]
        pred = str(self.model.predict(x)[0])
        confidence = 0.0
        scores: dict[str, float] = {}
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(x)[0]
            classes = [str(c) for c in getattr(self.model, "classes_", [])]
            scores = {c: float(p) for c, p in zip(classes, probs)}
            confidence = max(scores.values()) if scores else 0.0
        return LeukemiaClassification(
            predicted_class=pred,
            confidence=confidence,
            rationale="learned classifier prediction from aggregated differential features",
            scores=scores,
        )


class HybridClassifier:
    """Rule-first classifier with optional learned model override."""

    def __init__(self, learned: LearnedClassifier | None = None):
        self.learned = learned

    def classify(self, findings: AggregatedFindings) -> LeukemiaClassification:
        features = self._features(findings)
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
    def _features(findings: AggregatedFindings) -> dict[str, float]:
        features = {f"pct_{k}": float(v) for k, v in findings.cell_percentages_clinical.items()}
        features["blast_pct"] = float(findings.report_ready.get("blast_pct", 0.0))
        features["n_cells_informative"] = float(findings.n_cells_identified_wbc)
        return features

    @staticmethod
    def _result(pred: str, confidence: float, rationale: str) -> LeukemiaClassification:
        return LeukemiaClassification(
            predicted_class=pred,
            confidence=confidence,
            rationale=rationale,
            scores={pred: confidence},
        )
