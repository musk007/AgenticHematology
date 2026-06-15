#!/usr/bin/env python3
"""Extract DinoBloom MLP attribute predictions from MLL Helmholtz pre-cropped cells.

Helmholtz control images under ``~/helmholtz/data/control/<patient>/`` (or NFS mirror)
are 144×144 RGB single-cell crops (no YOLO needed). Uses the trained DinoBloom attribute
MLP (``runs/attribute_dinobloom/train/best_attr_dinobloom.pt``), not EfficientNet.

Outputs infer-compatible JSON used by ``Train_pipeline.py`` when ``--include-healthy-class``.

For **6-class classifier training on the full Helmholtz dataset** (189 cases: AML/APML/Healthy),
use ``build_helmholtz_metadata.py --classifier-only`` instead.
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

from dinobloom_infer import DEFAULT_DINOBLOOM_ATTR_WEIGHTS, build_dinobloom_attr_classifier, resolve_dinobloom_attr_weights  # noqa: E402
from mll_helmholtz import (  # noqa: E402
    assign_cell_types_from_metadata,
    genetic_label_to_diagnosis,
    iter_helmholtz_control_images,
    load_helmholtz_metadata,
    resolve_helmholtz_data_root,
    verify_mapping_excludes_unmapped,
)
from utils.labels import ATTR_NAMES  # noqa: E402


def extract_control_patients(
    data_root: Path,
    metadata_path: Path | None,
    device: str,
    batch: int,
    out_json: Path,
    attr_weights: Path,
    dinobloom_weights: str,
    dinobloom_variant: str,
    dinobloom_hub_dir: str | None,
) -> dict:
    audit = verify_mapping_excludes_unmapped()
    print(f"Mapping audit: {json.dumps(audit, indent=2)}")

    metadata = load_helmholtz_metadata(metadata_path)
    rows = iter_helmholtz_control_images(data_root)
    if not rows:
        raise SystemExit(f"No control images found under {data_root}")

    classifier = build_dinobloom_attr_classifier(
        device=device,
        attr_weights=attr_weights,
        dinobloom_weights=dinobloom_weights,
        variant=dinobloom_variant,
        hub_dir=dinobloom_hub_dir,
    )
    print(f"DinoBloom attribute MLP: {attr_weights}")

    by_patient: dict[str, list[Path]] = {}
    for pid, img in rows:
        by_patient.setdefault(pid, []).append(img)

    all_results: list[dict] = []
    patient_labels: dict[str, str] = {}

    for pid, images in tqdm(sorted(by_patient.items()), desc="Helmholtz control patients"):
        meta_case = metadata.get(pid, {})
        patient_labels[pid] = meta_case.get("metadata_filename_diagnosis") or genetic_label_to_diagnosis("control")
        counts = meta_case.get("cell_counts") or {}
        cell_types = assign_cell_types_from_metadata(counts, len(images))

        for start in range(0, len(images), batch):
            chunk_paths = images[start : start + batch]
            pil_images = [Image.open(p).convert("RGB") for p in chunk_paths]
            attr_results = classifier.classify_crops(pil_images)

            for idx, (img_path, (attrs, attr_probs, _, _)) in enumerate(zip(chunk_paths, attr_results)):
                global_idx = start + idx
                w, h = pil_images[idx].size
                attr_dict = {name: float(attrs.get(name, 0.0)) for name in ATTR_NAMES}
                attr_bin = {k: int(v >= 0.5) for k, v in attr_dict.items()}
                cell_type = cell_types[global_idx] if global_idx < len(cell_types) else "Neutrophil"
                all_results.append(
                    {
                        "image": str(img_path),
                        "patient_id": pid,
                        "patient_label": patient_labels[pid],
                        "cells": [
                            {
                                "xyxy": [0.0, 0.0, float(w), float(h)],
                                "conf": 1.0,
                                "class_id": None,
                                "class_name": cell_type,
                                "attributes": attr_dict,
                                "attributes_bin": attr_bin,
                            }
                        ],
                    }
                )

    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "mll_helmholtz_control",
        "attribute_model": "dinobloom_mlp",
        "attr_weights": str(attr_weights),
        "data_root": str(data_root),
        "n_patients": len(by_patient),
        "n_images": len(all_results),
        "patient_labels": patient_labels,
        "mapping_audit": audit,
        "predictions": all_results,
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved {out_json} ({len(all_results)} images, {len(by_patient)} patients)")
    return payload


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract DinoBloom MLP attributes for MLL Helmholtz Healthy cells.")
    ap.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Helmholtz control (Healthy) image root (default: ~/helmholtz/data/control)",
    )
    ap.add_argument(
        "--attr-weights",
        type=Path,
        default=DEFAULT_DINOBLOOM_ATTR_WEIGHTS,
        help="Trained DinoBloom attribute MLP (.pt)",
    )
    ap.add_argument("--dinobloom-weights", default="auto", help="DinoBloom backbone weights or 'auto'")
    ap.add_argument("--dinobloom-variant", choices=["s", "b", "l", "g"], default="l")
    ap.add_argument("--dinobloom-hub-dir", default=None)
    ap.add_argument("--metadata-json", type=Path, default=None)
    ap.add_argument("--device", default="0")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "runs" / "predict" / "mll_helmholtz_control" / "control_predictions.json",
    )
    args = ap.parse_args()

    if not resolve_dinobloom_attr_weights(args.attr_weights).is_file():
        sys.exit(f"DinoBloom attribute MLP not found: {args.attr_weights}")

    data_root = args.data_root or (resolve_helmholtz_data_root() / "control")
    if not data_root.is_dir():
        sys.exit(f"Data root not found: {data_root}")

    extract_control_patients(
        data_root=data_root,
        metadata_path=args.metadata_json,
        device=args.device,
        batch=args.batch,
        out_json=args.out,
        attr_weights=resolve_dinobloom_attr_weights(args.attr_weights),
        dinobloom_weights=args.dinobloom_weights,
        dinobloom_variant=args.dinobloom_variant,
        dinobloom_hub_dir=args.dinobloom_hub_dir,
    )


if __name__ == "__main__":
    main()
