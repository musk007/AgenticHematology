"""Build patient-level feature matrices from patient_WBC_stats JSON."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# 13 informative WBC types (exclude "none")
CLINICAL_CELL_TYPES: tuple[str, ...] = (
    "myeloblast",
    "lymphoblast",
    "neutrophil",
    "atypical lymphocyte",
    "promonocyte",
    "monoblast",
    "lymphocyte",
    "myelocyte",
    "abnormal promyelocyte",
    "monocyte",
    "metamyelocyte",
    "eosinophil",
    "basophil",
)

ATTRIBUTE_KEYS: tuple[str, ...] = (
    "cell_size",
    "nuclear_chromatio",
    "nuclear_shape",
    "nucleolus",
    "cytoplasm",
    "cytoplasmic_basophilia",
    "cytoplasmic_vacuoles",
)

CLINICAL_GROUPS: dict[str, tuple[str, ...]] = {
    "blasts": ("myeloblast", "lymphoblast", "monoblast", "abnormal promyelocyte"),
    "intermediate_myeloid": ("promonocyte", "myelocyte", "metamyelocyte"),
    "mature_granulocytes": ("neutrophil", "eosinophil", "basophil"),
    "lymphoid": ("lymphocyte", "atypical lymphocyte"),
    "monocytic": ("monocyte",),
}

FEATURES_EXCLUDED = {"qc__global_canvas_stitching_active"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).strip().lower()).strip("_")


def load_patient_stats(path: Path | str) -> dict[str, dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected dict patient_id -> record in {path}")
    return payload


def discover_lld_split_from_cv(cv_root: Path) -> dict[str, list[str]]:
    """Read-only split from wbc_unified det_dataset label filenames."""
    split: dict[str, set[str]] = {"train": set(), "test": set()}
    for part in ("train", "test"):
        label_dir = cv_root / "generated" / "det_dataset" / "labels" / part
        if not label_dir.is_dir():
            continue
        for label_path in label_dir.glob("*.txt"):
            split[part].add(label_path.name.split("_")[0])
    # If a patient appears in both, keep them in test only.
    overlap = split["train"] & split["test"]
    split["train"] -= overlap
    return {k: sorted(v, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x)) for k, v in split.items()}


def load_or_create_split(
    stats: dict[str, dict[str, Any]],
    *,
    split_path: Path | None,
    cv_root: Path | None,
) -> dict[str, list[str]]:
    if split_path and split_path.is_file():
        payload = json.loads(split_path.read_text(encoding="utf-8"))
        return {
            "train": [str(x) for x in payload.get("train", [])],
            "test": [str(x) for x in payload.get("test", [])],
        }
    if cv_root is None:
        raise ValueError("Provide --split-json or --cv-root to derive train/test patient IDs.")
    derived = discover_lld_split_from_cv(cv_root)
    stats_ids = set(stats.keys())
    derived["train"] = [pid for pid in derived["train"] if pid in stats_ids]
    derived["test"] = [pid for pid in derived["test"] if pid in stats_ids]
    return derived


def _attribute_state_columns(stats: dict[str, dict[str, Any]]) -> list[str]:
    states: dict[str, set[str]] = {k: set() for k in ATTRIBUTE_KEYS}
    for rec in stats.values():
        attrs = rec.get("attributes") or {}
        for attr_key in ATTRIBUTE_KEYS:
            percentages = (attrs.get(attr_key) or {}).get("percentages") or {}
            for state in percentages:
                if str(state).lower() in {"n_a", "na"}:
                    continue
                states[attr_key].add(_slug(state))
    columns: list[str] = []
    for attr_key in ATTRIBUTE_KEYS:
        for state in sorted(states[attr_key]):
            columns.append(f"attr_{_slug(attr_key)}__{_slug(state)}__pct")
    return columns


def build_feature_matrix(
    stats: dict[str, dict[str, Any]],
    *,
    include_qc_features: bool = True,
    exclude_low_cell_count: bool = False,
) -> tuple[pd.DataFrame, pd.Series, list[str], dict[str, bool]]:
    attr_cols = _attribute_state_columns(stats)
    feature_names: list[str] = []
    for cell_type in CLINICAL_CELL_TYPES:
        feature_names.append(f"pct_{_slug(cell_type)}")
    feature_names.append("blast_pool_percentage_of_wbc")
    feature_names.extend(attr_cols)
    for group in CLINICAL_GROUPS:
        feature_names.append(f"group_{group}_pct")
    if include_qc_features:
        feature_names.append("n_cells_identified_wbc")

    rows: list[dict[str, float]] = []
    labels: list[str] = []
    patient_ids: list[str] = []
    flags: dict[str, bool] = {}

    for patient_id, rec in sorted(stats.items(), key=lambda kv: kv[0]):
        qc = (rec.get("report_ready") or {}).get("qc") or {}
        low_cell = bool(qc.get("low_cell_count_warning", False))
        flags[patient_id] = low_cell
        if exclude_low_cell_count and low_cell:
            continue

        pct_clinical = rec.get("cell_percentages_clinical") or {}
        row = {name: 0.0 for name in feature_names}
        for cell_type in CLINICAL_CELL_TYPES:
            row[f"pct_{_slug(cell_type)}"] = float(pct_clinical.get(cell_type, 0.0))

        report_ready = rec.get("report_ready") or {}
        row["blast_pool_percentage_of_wbc"] = float(
            report_ready.get("blast_pool_percentage_of_wbc", 0.0)
        )

        attrs = rec.get("attributes") or {}
        for attr_key in ATTRIBUTE_KEYS:
            percentages = (attrs.get(attr_key) or {}).get("percentages") or {}
            for state, value in percentages.items():
                if str(state).lower() in {"n_a", "na"}:
                    continue
                col = f"attr_{_slug(attr_key)}__{_slug(state)}__pct"
                if col in row:
                    row[col] = float(value)

        group_den = float(rec.get("n_cells_identified_wbc") or 0.0)
        counts = rec.get("cell_counts") or {}
        if group_den <= 0:
            group_den = float(sum(v for k, v in counts.items() if k != "none") or 1.0)
        for group, members in CLINICAL_GROUPS.items():
            group_count = sum(float(counts.get(ct, 0)) for ct in members)
            row[f"group_{group}_pct"] = round(100.0 * group_count / group_den, 4)

        if include_qc_features:
            row["n_cells_identified_wbc"] = float(rec.get("n_cells_identified_wbc") or group_den)

        rows.append(row)
        labels.append(str(rec.get("metadata_filename_diagnosis", "Unknown")))
        patient_ids.append(str(patient_id))

    X = pd.DataFrame(rows, columns=feature_names).fillna(0.0)
    X.index = patient_ids
    y = pd.Series(labels, index=patient_ids, name="metadata_filename_diagnosis")
    kept_names = [c for c in feature_names if c not in FEATURES_EXCLUDED]
    return X[kept_names], y, kept_names, flags


def humanize_feature_name(name: str) -> str:
    if name.startswith("pct_"):
        return f"{name.removeprefix('pct_').replace('_', ' ')} differential %"
    if name.startswith("group_") and name.endswith("_pct"):
        group = name.removeprefix("group_").removesuffix("_pct").replace("_", " ")
        return f"{group} lineage group %"
    if name.startswith("attr_") and name.endswith("__pct"):
        body = name.removeprefix("attr_").removesuffix("__pct")
        attr, state = body.split("__", 1)
        return f"{state.replace('_', ' ')} {attr.replace('_', ' ')} attribute %"
    if name == "blast_pool_percentage_of_wbc":
        return "blast pool % of WBC"
    if name == "n_cells_identified_wbc":
        return "identified WBC cell count"
    return name.replace("_", " ")


def build_simple_features_from_infer_json(
    pred_json: Path | str,
) -> tuple[list[dict[str, float]], list[str], list[str]]:
    """Legacy simple pct_* features from wbc_unified infer JSON (infer feature source)."""
    import json
    from pathlib import Path as _Path

    from agentic_hematology.aggregator import aggregate
    from agentic_hematology.leukemia_classifier import HybridClassifier
    from agentic_hematology.schemas import Detection, DetectionResult

    pred_json = _Path(pred_json)
    payload = json.loads(pred_json.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "predictions" in payload:
        payload = payload["predictions"]

    patients: dict[str, dict] = {}
    for img_rec in payload:
        image_path = _Path(str(img_rec.get("image", "")))
        stem_parts = image_path.stem.split("_")
        if len(stem_parts) < 5:
            continue
        pid = stem_parts[0]
        gt_label = stem_parts[-1].strip()
        if not gt_label:
            continue
        rec = patients.setdefault(pid, {"patient_id": pid, "label": gt_label, "images": []})
        rec["images"].append(img_rec)

    X: list[dict[str, float]] = []
    y: list[str] = []
    patient_ids: list[str] = []
    for patient in patients.values():
        pid = str(patient.get("patient_id", "unknown"))
        gt_label = str(patient.get("label", "")).strip()
        detections = []
        for img_idx, img_rec in enumerate(patient.get("images", [])):
            image_id = _Path(str(img_rec.get("image", ""))).name
            for cell_idx, cell in enumerate(img_rec.get("cells", [])):
                attrs = dict(cell.get("attributes", {}))
                attrs["class_id"] = cell.get("class_id")
                detections.append(
                    Detection(
                        cell_id=f"img{img_idx:03d}_c{cell_idx:03d}",
                        image_id=image_id,
                        bbox_xyxy=tuple(float(v) for v in cell.get("xyxy", [0, 0, 1, 1])),
                        cell_type=str(cell.get("class_name", "Unknown")),
                        objectness=float(cell.get("conf", 0.0)),
                        attributes=attrs,
                        attribute_probs={},
                    )
                )
        if not detections:
            continue
        findings = aggregate(
            DetectionResult(
                case_id=pid,
                n_images=len(patient.get("images", [])),
                detections=detections,
            )
        )
        X.append(HybridClassifier._features(findings))
        y.append(gt_label)
        patient_ids.append(pid)
    return X, y, patient_ids


def build_feature_row_from_stats(
    stats: dict[str, dict[str, Any]],
    patient_id: str,
    feature_names: list[str],
) -> dict[str, float]:
    """Single patient feature row aligned with build_feature_matrix columns."""
    X, _, names, _ = build_feature_matrix(stats, include_qc_features=True)
    if str(patient_id) not in X.index:
        return {name: 0.0 for name in feature_names}
    row = X.loc[str(patient_id)]
    return {name: float(row.get(name, 0.0)) for name in feature_names}
