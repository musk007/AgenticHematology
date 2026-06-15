#!/usr/bin/env python3
"""Stratified 70:30 train/test split for Helmholtz patients (per diagnosis class)."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from mll_helmholtz import (  # noqa: E402
    genetic_label_to_diagnosis,
    load_helmholtz_metadata,
    resolve_helmholtz_metadata_json,
)


def stratified_patient_split(
    metadata: dict[str, dict],
    test_fraction: float = 0.3,
    seed: int = 42,
) -> tuple[list[str], list[str], dict[str, str]]:
    from sklearn.model_selection import train_test_split

    patient_ids: list[str] = []
    labels: list[str] = []
    for pid, rec in sorted(metadata.items()):
        genetic = str(rec.get("metadata_genetic_label") or "control")
        label = str(
            rec.get("metadata_filename_diagnosis") or genetic_label_to_diagnosis(genetic)
        ).strip()
        patient_ids.append(pid)
        labels.append(label)

    train_ids, test_ids = train_test_split(
        patient_ids,
        test_size=test_fraction,
        random_state=seed,
        stratify=labels,
    )
    split_map = {pid: "train" for pid in train_ids}
    split_map.update({pid: "test" for pid in test_ids})
    return train_ids, test_ids, split_map


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Split Helmholtz patients 70:30 with stratification per diagnosis class."
    )
    ap.add_argument(
        "--metadata-json",
        type=Path,
        default=None,
        help="patients_helmholtz.json (default: resolve via mll_helmholtz)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "generated" / "helmholtz_split.json",
        help="Output split manifest JSON",
    )
    ap.add_argument("--test-fraction", type=float, default=0.3, help="Test set fraction (default 0.3)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    metadata_path = args.metadata_json or resolve_helmholtz_metadata_json()
    metadata = load_helmholtz_metadata(metadata_path)
    if not metadata:
        sys.exit(f"No Helmholtz metadata found: {metadata_path}")

    train_ids, test_ids, split_map = stratified_patient_split(
        metadata, test_fraction=args.test_fraction, seed=args.seed
    )

    train_labels = Counter(
        metadata[pid].get("metadata_filename_diagnosis")
        or genetic_label_to_diagnosis(metadata[pid].get("metadata_genetic_label", "control"))
        for pid in train_ids
    )
    test_labels = Counter(
        metadata[pid].get("metadata_filename_diagnosis")
        or genetic_label_to_diagnosis(metadata[pid].get("metadata_genetic_label", "control"))
        for pid in test_ids
    )

    payload = {
        "metadata_json": str(metadata_path),
        "seed": args.seed,
        "test_fraction": args.test_fraction,
        "train_fraction": round(1.0 - args.test_fraction, 4),
        "n_patients": len(metadata),
        "n_train": len(train_ids),
        "n_test": len(test_ids),
        "train_label_counts": dict(sorted(train_labels.items())),
        "test_label_counts": dict(sorted(test_labels.items())),
        "train_patient_ids": sorted(train_ids),
        "test_patient_ids": sorted(test_ids),
        "patients": {
            pid: {
                "split": split_map[pid],
                "label": metadata[pid].get("metadata_filename_diagnosis")
                or genetic_label_to_diagnosis(metadata[pid].get("metadata_genetic_label", "control")),
                "genetic_label": metadata[pid].get("metadata_genetic_label"),
            }
            for pid in sorted(metadata)
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote {args.out}")
    print(f"  train: {len(train_ids)}  {dict(train_labels)}")
    print(f"  test:  {len(test_ids)}  {dict(test_labels)}")


if __name__ == "__main__":
    main()
