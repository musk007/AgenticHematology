#!/usr/bin/env python3
"""Extract DinoBloom cell-type + attribute predictions from all Helmholtz pre-cropped cells.

Runs the LLD-trained DinoBloom cell classifier on every 144×144 crop across all genetic
cohorts (control, NPM1, CBFB_MYH11, RUNX1_RUNX1T1, PML_RARA). Output JSON is compatible
with ``Train_pipeline.py --include-healthy-class``.

Replaces metadata-synthetic cell types from ``build_helmholtz_metadata.py --classifier-only``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dinobloom_infer import (  # noqa: E402
    DEFAULT_DINOBLOOM_CELL_WEIGHTS,
    build_dinobloom_cell_classifier,
    resolve_dinobloom_cell_weights,
)
from mll_helmholtz import (  # noqa: E402
    HELMHOLTZ_GENETIC_COHORTS,
    genetic_label_to_diagnosis,
    iter_helmholtz_cohort_patients,
    load_helmholtz_metadata,
    resolve_helmholtz_data_root,
    verify_mapping_excludes_unmapped,
)
from utils.labels import ATTR_NAMES  # noqa: E402

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def _list_patient_images(patient_dir: Path) -> list[Path]:
    images: list[Path] = []
    for img in sorted(patient_dir.iterdir()):
        if img.is_file() and img.suffix.lower() in IMAGE_SUFFIXES and not img.name.startswith("._"):
            images.append(img)
    return images


def extract_helmholtz_patients(
    data_root: Path,
    metadata_path: Path | None,
    device: str,
    batch: int,
    out_json: Path,
    cell_weights: Path,
    attr_weights: Path | None,
    dinobloom_weights: str,
    dinobloom_variant: str,
    dinobloom_hub_dir: str | None,
    cohorts: tuple[str, ...] = HELMHOLTZ_GENETIC_COHORTS,
    patient_ids: set[str] | None = None,
) -> dict:
    audit = verify_mapping_excludes_unmapped()
    print(f"Mapping audit: {json.dumps(audit, indent=2)}")

    metadata = load_helmholtz_metadata(metadata_path)
    cohort_rows = iter_helmholtz_cohort_patients(data_root, cohorts=cohorts)
    if not cohort_rows:
        raise SystemExit(f"No Helmholtz patient folders found under {data_root}")

    classifier = build_dinobloom_cell_classifier(
        device=device,
        cell_weights=cell_weights,
        attr_weights=attr_weights,
        dinobloom_weights=dinobloom_weights,
        variant=dinobloom_variant,
        hub_dir=dinobloom_hub_dir,
        fallback_to_yolo_type=False,
    )
    print(f"DinoBloom cell classifier: {cell_weights}")

    all_results: list[dict] = []
    patient_labels: dict[str, str] = {}
    n_patients = 0

    for pid, genetic, patient_dir in tqdm(cohort_rows, desc="Helmholtz patients"):
        if patient_ids is not None and pid not in patient_ids:
            continue
        images = _list_patient_images(patient_dir)
        if not images:
            continue

        meta_case = metadata.get(pid, {})
        patient_labels[pid] = (
            meta_case.get("metadata_filename_diagnosis")
            or genetic_label_to_diagnosis(genetic)
        )
        n_patients += 1

        for start in range(0, len(images), batch):
            chunk_paths = images[start : start + batch]
            pil_images = [Image.open(p).convert("RGB") for p in chunk_paths]
            results = classifier.classify_crops(pil_images)

            for idx, (img_path, (attrs, attr_probs, cell_type, cell_conf)) in enumerate(
                zip(chunk_paths, results)
            ):
                w, h = pil_images[idx].size
                attr_dict = {name: float(attrs.get(name, 0.0)) for name in ATTR_NAMES}
                attr_bin = {k: int(v >= 0.5) for k, v in attr_dict.items()}
                all_results.append(
                    {
                        "image": str(img_path),
                        "patient_id": pid,
                        "patient_label": patient_labels[pid],
                        "genetic_label": genetic,
                        "cells": [
                            {
                                "xyxy": [0.0, 0.0, float(w), float(h)],
                                "conf": float(cell_conf or 1.0),
                                "class_id": None,
                                "class_name": str(cell_type or "Unclassified"),
                                "attributes": attr_dict,
                                "attributes_bin": attr_bin,
                            }
                        ],
                    }
                )

    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "mll_helmholtz_cell_classifier",
        "cell_model": "dinobloom_cell_linear",
        "attribute_model": "dinobloom_mlp",
        "cell_weights": str(cell_weights),
        "data_root": str(data_root),
        "n_patients": n_patients,
        "n_images": len(all_results),
        "patient_labels": patient_labels,
        "mapping_audit": audit,
        "predictions": all_results,
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved {out_json} ({len(all_results)} images, {n_patients} patients)")
    return payload


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract DinoBloom cell + attribute predictions for all Helmholtz cohorts."
    )
    ap.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Helmholtz image root (default: ~/helmholtz/data)",
    )
    ap.add_argument(
        "--cell-weights",
        type=Path,
        default=DEFAULT_DINOBLOOM_CELL_WEIGHTS,
        help="Trained DinoBloom cell classifier (.pt)",
    )
    ap.add_argument("--attr-weights", type=Path, default=None, help="Optional attribute MLP override")
    ap.add_argument("--dinobloom-weights", default="auto")
    ap.add_argument("--dinobloom-variant", choices=["s", "b", "l", "g"], default="l")
    ap.add_argument("--dinobloom-hub-dir", default=None)
    ap.add_argument("--metadata-json", type=Path, default=None)
    ap.add_argument(
        "--split-json",
        type=Path,
        default=None,
        help="Optional helmholtz_split.json — restrict to listed train+test patients",
    )
    ap.add_argument("--device", default="0")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "runs" / "predict" / "mll_helmholtz" / "helmholtz_cell_predictions.json",
    )
    args = ap.parse_args()

    cell_weights = resolve_dinobloom_cell_weights(args.cell_weights)
    if not cell_weights.is_file():
        sys.exit(
            f"DinoBloom cell classifier not found: {cell_weights}\n"
            "Train with: python wbc_unified/cv/train_dinobloom_cell_classifier.py"
        )

    data_root = args.data_root or resolve_helmholtz_data_root()
    if not data_root.is_dir():
        sys.exit(f"Data root not found: {data_root}")

    patient_ids: set[str] | None = None
    if args.split_json and args.split_json.is_file():
        from mll_helmholtz import load_helmholtz_split  # noqa: E402

        split_payload = load_helmholtz_split(args.split_json)
        train_ids = split_payload.get("train_patient_ids") or []
        test_ids = split_payload.get("test_patient_ids") or []
        patient_ids = {str(pid) for pid in train_ids + test_ids}
        if not patient_ids:
            patients = split_payload.get("patients") or {}
            patient_ids = set(patients.keys())
        print(f"Restricting to {len(patient_ids)} patients from {args.split_json}")

    extract_helmholtz_patients(
        data_root=data_root,
        metadata_path=args.metadata_json,
        device=args.device,
        batch=args.batch,
        out_json=args.out,
        cell_weights=cell_weights,
        attr_weights=args.attr_weights,
        dinobloom_weights=args.dinobloom_weights,
        dinobloom_variant=args.dinobloom_variant,
        dinobloom_hub_dir=args.dinobloom_hub_dir,
        patient_ids=patient_ids,
    )


if __name__ == "__main__":
    main()
