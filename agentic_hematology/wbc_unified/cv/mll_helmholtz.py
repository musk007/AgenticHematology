"""Shared helpers for MLL Helmholtz / Matek class collapse and feature I/O."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
HOME = Path.home()
DEFAULT_MAPPING_PATH = ROOT / "configs" / "mll_matek_class_mapping.json"

# Canonical Helmholtz assets (user-provided layout under ~/helmholtz/).
DEFAULT_HELMHOLTZ_XLSX = HOME / "helmholtz" / "AML-Cytomorphology_MLL_Helmholtz.xlsx"
DEFAULT_HELMHOLTZ_METADATA_JSON = ROOT / "generated" / "patients_helmholtz.json"
DEFAULT_HELMHOLTZ_REPORTS_DIR = (
    HOME / "AgenticHematology" / "helmholtz_template_reports"
)
_HELMHOLTZ_DATA_CANDIDATES = [
    HOME / "helmholtz" / "data",
    Path("/nfs-stor/roba.majzoub/helmholtz/data"),
]
_HELMHOLTZ_STAINNORM_CANDIDATES = [
    HOME / "helmholtz" / "data_stainnorm",
    Path("/nfs-stor/roba.majzoub/helmholtz/data_stainnorm"),
]


def resolve_helmholtz_data_root() -> Path:
    for candidate in _HELMHOLTZ_DATA_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return _HELMHOLTZ_DATA_CANDIDATES[0]


def resolve_helmholtz_stainnorm_data_root() -> Path:
    for candidate in _HELMHOLTZ_STAINNORM_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return _HELMHOLTZ_STAINNORM_CANDIDATES[0]


def resolve_helmholtz_metadata_json() -> Path:
    legacy = (
        HOME / "AgenticHematology" / "data_preprocessing" / "patients_helmholtz.json"
    )
    for candidate in (legacy, DEFAULT_HELMHOLTZ_METADATA_JSON):
        if candidate.is_file():
            return candidate
    return legacy


def resolve_helmholtz_xlsx() -> Path:
    return DEFAULT_HELMHOLTZ_XLSX


def resolve_helmholtz_reports_dir() -> Path:
    return DEFAULT_HELMHOLTZ_REPORTS_DIR


# Back-compat alias used by extract script.
DEFAULT_HELMHOLTZ_ROOT = resolve_helmholtz_data_root()
DEFAULT_HELMHOLTZ_METADATA = resolve_helmholtz_metadata_json()


def load_class_mapping(path: Path | None = None) -> dict[str, Any]:
    mapping_path = Path(path) if path else DEFAULT_MAPPING_PATH
    return json.loads(mapping_path.read_text(encoding="utf-8"))


def matek_code_to_lld(matek_code: str, mapping: dict[str, Any] | None = None) -> str | None:
    mapping = mapping or load_class_mapping()
    entry = mapping["matek_to_lld"].get(str(matek_code).upper(), {})
    if entry.get("excluded"):
        return None
    return entry.get("lld_cell_type")


def metadata_cell_type_to_lld(name: str, mapping: dict[str, Any] | None = None) -> str | None:
    mapping = mapping or load_class_mapping()
    key = str(name).strip().lower()
    lld = mapping["mll_metadata_to_lld_cell_type"].get(key)
    if lld == "None":
        return None
    return lld


def genetic_label_to_diagnosis(bag_label: str, mapping: dict[str, Any] | None = None) -> str:
    mapping = mapping or load_class_mapping()
    return mapping["mll_genetic_to_diagnosis"].get(str(bag_label), str(bag_label))


def verify_mapping_excludes_unmapped(mapping: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return audit dict: mapped Matek codes, excluded codes, healthy codes."""
    mapping = mapping or load_class_mapping()
    matek = mapping["matek_to_lld"]
    mapped = [k for k, v in matek.items() if v.get("lld_cell_type")]
    excluded = [k for k, v in matek.items() if v.get("excluded")]
    return {
        "n_matek_codes": len(matek),
        "mapped_to_lld": mapped,
        "excluded": excluded,
        "healthy_matek_codes": mapping.get("healthy_matek_codes", []),
        "unmapped_policy": mapping.get("unmapped_policy", "drop"),
        "all_accounted": len(mapped) + len(excluded) == len(matek),
    }


def assign_cell_types_from_metadata(
    cell_counts: dict[str, int | float],
    n_cells: int,
    mapping: dict[str, Any] | None = None,
) -> list[str]:
    """Expand metadata differential counts into per-cell LLD type labels (deterministic)."""
    mapping = mapping or load_class_mapping()
    expanded: list[str] = []
    for raw_name, count in cell_counts.items():
        lld = metadata_cell_type_to_lld(raw_name, mapping)
        if not lld:
            continue
        n = max(0, int(round(float(count))))
        expanded.extend([lld] * n)
    if not expanded:
        expanded = ["Neutrophil"] * n_cells
    if len(expanded) >= n_cells:
        return expanded[:n_cells]
    # Pad with dominant mature type for healthy controls.
    pad_type = max(set(expanded), key=expanded.count)
    expanded.extend([pad_type] * (n_cells - len(expanded)))
    return expanded


def load_helmholtz_metadata(metadata_path: Path | None = None) -> dict[str, dict]:
    path = Path(metadata_path) if metadata_path else resolve_helmholtz_metadata_json()
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


HELMHOLTZ_GENETIC_COHORTS = ("control", "NPM1", "CBFB_MYH11", "RUNX1_RUNX1T1", "PML_RARA")
DEFAULT_HELMHOLTZ_CLASSIFIER_JSON = (
    ROOT / "runs" / "predict" / "mll_helmholtz" / "helmholtz_predictions.json"
)
DEFAULT_HELMHOLTZ_CELL_CLASSIFIER_JSON = (
    ROOT / "runs" / "predict" / "mll_helmholtz" / "helmholtz_cell_predictions.json"
)
DEFAULT_HELMHOLTZ_SPLIT_JSON = ROOT / "generated" / "helmholtz_split.json"


def resolve_helmholtz_classifier_predictions_json() -> Path:
    cell_json = DEFAULT_HELMHOLTZ_CELL_CLASSIFIER_JSON
    if cell_json.is_file():
        return cell_json
    return DEFAULT_HELMHOLTZ_CLASSIFIER_JSON


def resolve_helmholtz_split_json() -> Path:
    return DEFAULT_HELMHOLTZ_SPLIT_JSON


def load_helmholtz_split(split_json: Path | None = None) -> dict[str, Any]:
    path = Path(split_json) if split_json else resolve_helmholtz_split_json()
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def helmholtz_patient_ids_for_split(split_payload: dict[str, Any], split: str) -> set[str]:
    split = str(split).strip().lower()
    if split == "train":
        ids = split_payload.get("train_patient_ids")
    elif split == "test":
        ids = split_payload.get("test_patient_ids")
    else:
        raise ValueError(f"split must be 'train' or 'test', got {split!r}")
    if ids:
        return {str(pid) for pid in ids}
    patients = split_payload.get("patients") or {}
    return {pid for pid, rec in patients.items() if str(rec.get("split")) == split}


def filter_helmholtz_prediction_records(
    records: list[dict[str, Any]],
    patient_ids: set[str] | None,
) -> list[dict[str, Any]]:
    if not patient_ids:
        return records
    return [r for r in records if str(r.get("patient_id", "")) in patient_ids]


def iter_helmholtz_control_images(data_root: Path | None = None) -> list[tuple[str, Path]]:
    root = Path(data_root) if data_root else (resolve_helmholtz_data_root() / "control")
    rows: list[tuple[str, Path]] = []
    if not root.is_dir():
        return rows
    suffixes = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    for patient_dir in sorted(root.iterdir()):
        if not patient_dir.is_dir():
            continue
        pid = patient_dir.name
        for img in sorted(patient_dir.iterdir()):
            if img.suffix.lower() in suffixes and not img.name.startswith("._"):
                rows.append((pid, img))
    return rows


def iter_helmholtz_cohort_patients(
    data_root: Path | None = None,
    cohorts: tuple[str, ...] = HELMHOLTZ_GENETIC_COHORTS,
) -> list[tuple[str, str, Path]]:
    """Return ``(patient_id, genetic_label, patient_dir)`` for all Helmholtz cohorts."""
    root = Path(data_root) if data_root else resolve_helmholtz_data_root()
    rows: list[tuple[str, str, Path]] = []
    for genetic in cohorts:
        cohort_dir = root / genetic
        if not cohort_dir.is_dir():
            continue
        for patient_dir in sorted(cohort_dir.iterdir()):
            if patient_dir.is_dir() and not patient_dir.name.startswith("."):
                rows.append((patient_dir.name, genetic, patient_dir))
    return rows


def build_helmholtz_classifier_records(
    metadata_path: Path | None = None,
    patient_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Build infer-compatible records from Helmholtz metadata differentials (all cohorts).

    Patient-level RF features use aggregated WBC percentages; metadata provides the
    annotated 100-cell differential per case. No GPU inference is required.
    """
    metadata = load_helmholtz_metadata(metadata_path)
    if not metadata:
        return []

    records: list[dict[str, Any]] = []
    for pid, meta_case in sorted(metadata.items()):
        if patient_ids is not None and pid not in patient_ids:
            continue
        genetic = str(meta_case.get("metadata_genetic_label") or "control")
        diagnosis = (
            meta_case.get("metadata_filename_diagnosis")
            or genetic_label_to_diagnosis(genetic)
        )
        counts = meta_case.get("cell_counts") or {}
        n_cells = int(
            meta_case.get("n_cells_identified_wbc")
            or meta_case.get("n_cells_total")
            or sum(int(round(float(v))) for v in counts.values())
            or 100
        )
        cell_types = assign_cell_types_from_metadata(counts, n_cells)
        cells = [
            {
                "xyxy": [0.0, 0.0, 144.0, 144.0],
                "conf": 1.0,
                "class_id": None,
                "class_name": cell_type,
                "attributes": {},
                "attributes_bin": {},
            }
            for cell_type in cell_types
        ]
        if not cells:
            continue
        records.append(
            {
                "image": f"helmholtz://{genetic}/{pid}",
                "patient_id": pid,
                "patient_label": str(diagnosis),
                "metadata_genetic_label": genetic,
                "cells": cells,
            }
        )
    return records


def write_helmholtz_classifier_predictions(
    out_json: Path | None = None,
    metadata_path: Path | None = None,
) -> dict[str, Any]:
    """Write full Helmholtz dataset JSON for 6-class classifier training."""
    out_path = Path(out_json) if out_json else resolve_helmholtz_classifier_predictions_json()
    records = build_helmholtz_classifier_records(metadata_path)
    if not records:
        raise FileNotFoundError(
            "No Helmholtz metadata records found. "
            f"Expected {metadata_path or resolve_helmholtz_metadata_json()}"
        )

    from collections import Counter

    label_counts = Counter(r["patient_label"] for r in records)
    genetic_counts = Counter(r["metadata_genetic_label"] for r in records)
    payload = {
        "source": "mll_helmholtz_full",
        "feature_source": "metadata_differential",
        "metadata_json": str(metadata_path or resolve_helmholtz_metadata_json()),
        "n_patients": len(records),
        "n_images": len(records),
        "patient_label_counts": dict(sorted(label_counts.items())),
        "genetic_label_counts": dict(sorted(genetic_counts.items())),
        "predictions": records,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
