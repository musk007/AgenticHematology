#!/usr/bin/env python3
"""Helmholtz data prep: metadata JSON and classifier training JSON."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from mll_helmholtz import (  # noqa: E402
    resolve_helmholtz_classifier_predictions_json,
    resolve_helmholtz_metadata_json,
    resolve_helmholtz_xlsx,
    write_helmholtz_classifier_predictions,
)

LEGACY_BUILDER = Path.home() / "AgenticHematology" / "data_preprocessing" / "patients_helmholtz.py"


def build_metadata_json(metadata_xlsx: Path, out_json: Path) -> None:
    if not LEGACY_BUILDER.is_file():
        sys.exit(f"Builder script not found: {LEGACY_BUILDER}")
    if not metadata_xlsx.is_file():
        sys.exit(f"Metadata xlsx not found: {metadata_xlsx}")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(LEGACY_BUILDER),
            "--metadata",
            str(metadata_xlsx),
            "--out-json",
            str(out_json),
        ],
        check=True,
    )
    print(f"Metadata JSON ready: {out_json}")


def build_classifier_json(metadata_json: Path, out_json: Path) -> None:
    if not metadata_json.is_file():
        sys.exit(f"Helmholtz metadata not found: {metadata_json}")
    payload = write_helmholtz_classifier_predictions(out_json, metadata_json)
    print(
        json.dumps(
            {
                "out": str(out_json),
                "metadata_json": str(metadata_json),
                "n_patients": payload["n_patients"],
                "patient_label_counts": payload["patient_label_counts"],
                "genetic_label_counts": payload["genetic_label_counts"],
            },
            indent=2,
        )
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Build Helmholtz metadata and classifier training JSON.")
    ap.add_argument(
        "--classifier-only",
        action="store_true",
        help="Build infer-compatible helmholtz_predictions.json for RF training (default step before Train_pipeline)",
    )
    ap.add_argument("--metadata", type=Path, default=None, help="Path to AML-Cytomorphology_MLL_Helmholtz.xlsx")
    ap.add_argument(
        "--metadata-json",
        type=Path,
        default=None,
        help="Existing patients_helmholtz.json (classifier-only mode)",
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Output patients_helmholtz.json (metadata mode) or helmholtz_predictions.json (classifier mode)",
    )
    args = ap.parse_args()

    if args.classifier_only:
        metadata_json = args.metadata_json or resolve_helmholtz_metadata_json()
        out_json = args.out_json or resolve_helmholtz_classifier_predictions_json()
        build_classifier_json(metadata_json, out_json)
        return

    xlsx = args.metadata or resolve_helmholtz_xlsx()
    out_json = args.out_json or resolve_helmholtz_metadata_json()
    build_metadata_json(xlsx, out_json)


if __name__ == "__main__":
    main()
