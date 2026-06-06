"""Parse LLD Organized image filenames."""
from __future__ import annotations

from pathlib import Path


def parse_image_stem(stem: str) -> dict[str, str | int]:
    """
    {patient_id}_{row}_{col}_{magnification}_{disease}.png
    e.g. 15_10_12_400_AML
    """
    parts = stem.split("_")
    if len(parts) < 5:
        raise ValueError(f"Expected >=5 underscore fields, got: {stem}")
    return {
        "patient_id": parts[0],
        "row": int(parts[1]),
        "col": int(parts[2]),
        "magnification": parts[3],
        "disease_label": parts[4],
    }


def patient_id_from_path(image_path: str | Path) -> str:
    return parse_image_stem(Path(image_path).stem)["patient_id"]
