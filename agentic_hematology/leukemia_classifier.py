"""Simple patient-level leukemia classification from aggregated WBC findings."""
from __future__ import annotations

import json
import pickle
from pathlib import Path

from .domain_feature_norm import DomainFeatureNormalizer
from .schemas import AggregatedFindings, LeukemiaClassification

# Mature WBC types expected on healthy peripheral smears (Matek NGS/NGB/EOS/BAS/LYT/MON/MYB/PMO).
HEALTHY_MATURE_CELL_TYPES = frozenset(
    {
        "Neutrophil",
        "Lymphocyte",
        "Eosinophil",
        "Basophil",
        "Monocyte",
        "Myelocyte",
        "Metamyelocyte",
        "Promonocyte",
    }
)

DEFAULT_CLASSES_5 = ("ALL", "AML", "APML", "CLL", "CML")
DEFAULT_CLASSES_6 = DEFAULT_CLASSES_5 + ("Healthy",)


class LearnedClassifier:
    """Optional wrapper for a pickled sklearn-like classifier."""

    def __init__(self, model_path: str | Path, meta_path: str | Path | None = None):
        model_path = Path(model_path)
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)

        meta_path = Path(meta_path) if meta_path else model_path.with_name(f"{model_path.stem}_meta.json")
        self.feature_keys: list[str] | None = None
        self.domain_normalize = False
        self.normalizer: DomainFeatureNormalizer | None = None
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            keys = meta.get("feature_keys")
            if isinstance(keys, list) and keys:
                self.feature_keys = [str(k) for k in keys]
            self.domain_normalize = bool(meta.get("domain_normalize", False))
            norm_stats_path = meta.get("domain_norm_stats_json")
            if self.domain_normalize and norm_stats_path and Path(norm_stats_path).is_file():
                self.normalizer = DomainFeatureNormalizer.load(norm_stats_path)
            elif self.domain_normalize and meta.get("domain_norm_stats"):
                self.normalizer = DomainFeatureNormalizer.from_dict(meta["domain_norm_stats"])

    def _prepare_features(
        self,
        features: dict[str, float],
        dataset_source: str | int | None = None,
    ) -> dict[str, float]:
        if self.domain_normalize:
            if self.normalizer is None:
                raise ValueError("domain_normalize enabled but normalization stats are missing")
            if dataset_source is None:
                raise ValueError("dataset_source is required for domain-normalized classifier")
            return self.normalizer.transform_dict(features, dataset_source)
        return dict(features)

    def predict(
        self,
        features: dict[str, float],
        dataset_source: str | int | None = None,
    ) -> LeukemiaClassification | None:
        if not hasattr(self.model, "predict"):
            return None
        prepared = self._prepare_features(features, dataset_source)
        keys = self.feature_keys if self.feature_keys else sorted(prepared)
        x = [[float(prepared.get(k, 0.0)) for k in keys]]
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

    def __init__(
        self,
        learned: LearnedClassifier | None = None,
        healthy_cell_pct_threshold: float = 65.0,
        include_healthy_class: bool = False,
    ):
        self.learned = learned
        self.healthy_cell_pct_threshold = float(healthy_cell_pct_threshold)
        self.include_healthy_class = include_healthy_class

    def classify(
        self,
        findings: AggregatedFindings,
        dataset_source: str = "lld",
    ) -> LeukemiaClassification:
        features = self._features(findings)
        if self.learned is not None:
            learned = self.learned.predict(features, dataset_source=dataset_source)
            if learned is not None:
                return learned

        diff = findings.cell_percentages_clinical
        counts = findings.cell_counts
        blast_pct = float(findings.report_ready.get("blast_pct", 0.0))
        healthy_mature_pct = sum(diff.get(t, 0.0) for t in HEALTHY_MATURE_CELL_TYPES)

        if self.include_healthy_class:
            # Priority 0 — dominant mature WBC pattern without blast burden.
            # Threshold 65%: healthy PB typically >60% segmented neutrophils + lymphocytes;
            # 65% is conservative to avoid calling leukemic smears Healthy when mature
            # cells still dominate (e.g. CML left-shift).
            if (
                healthy_mature_pct >= self.healthy_cell_pct_threshold
                and blast_pct < 20.0
                and diff.get("Lymphoblast", 0.0) < 10.0
                and diff.get("Myeloblast", 0.0) + diff.get("Monoblast", 0.0) < 10.0
                and diff.get("Abnormal promyelocyte", 0.0) < 5.0
            ):
                return self._result(
                    "Healthy",
                    min(0.95, 0.55 + healthy_mature_pct / 200.0),
                    f"mature WBC fraction {healthy_mature_pct:.1f}% exceeds "
                    f"threshold {self.healthy_cell_pct_threshold:.0f}% without blast burden",
                )

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
