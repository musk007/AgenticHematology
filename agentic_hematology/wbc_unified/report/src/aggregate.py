"""Build per-patient detection summaries from infer JSON or GT attributes."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .filename import parse_image_stem, patient_id_from_path

ATTR_NAMES = [
    "Nuclear_Chromatin",
    "Nuclear_Shape",
    "Nucleus",
    "Cytoplasm",
    "Cytoplasmic_Basophilia",
    "Cytoplasmic_Vacuoles",
]

CLASS_NAMES = [
    "None",
    "Myeloblast",
    "Lymphoblast",
    "Neutrophil",
    "Atypical lymphocyte",
    "Promonocyte",
    "Monoblast",
    "Lymphocyte",
    "Myelocyte",
    "Abnormal promyelocyte",
    "Monocyte",
    "Metamyelocyte",
    "Eosinophil",
    "Basophil",
]


def _morphology_stats(cells: list[dict]) -> dict[str, dict[str, float]]:
    by_class: dict[str, list[dict]] = defaultdict(list)
    for c in cells:
        by_class[c["class_name"]].append(c)
    out = {}
    for cls, group in by_class.items():
        if cls == "None" or len(group) < 1:
            continue
        rates = {}
        for attr in ATTR_NAMES:
            vals = [c["attributes_bin"].get(attr, 0) for c in group if attr in c.get("attributes_bin", {})]
            if vals:
                rates[attr] = round(sum(vals) / len(vals), 4)
        out[cls] = {"n": len(group), "attr_pos_rate": rates}
    return out


def _cell_from_prediction(det: dict, conf_threshold: float) -> dict | None:
    name = det.get("class_name", "None")
    conf = float(det.get("conf", 0))
    if name == "None" or conf < conf_threshold:
        return None
    return {
        "class_name": name,
        "class_id": int(det.get("class_id", 0)),
        "conf": conf,
        "attributes_bin": det.get("attributes_bin", {}),
    }


def aggregate_predictions(
    predictions_paths: list[str | Path],
    conf_threshold: float = 0.25,
    blast_classes: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Group infer JSON by patient_id."""
    blast_classes = blast_classes or [
        "Myeloblast",
        "Lymphoblast",
        "Monoblast",
        "Abnormal promyelocyte",
    ]
    by_patient: dict[str, dict[str, Any]] = {}

    for ppath in predictions_paths:
        data = json.loads(Path(ppath).read_text())
        for item in data:
            meta = parse_image_stem(Path(item["image"]).stem)
            pid = str(meta["patient_id"])
            if pid not in by_patient:
                by_patient[pid] = {
                    "patient_id": pid,
                    "disease_label_file": meta["disease_label"],
                    "source": "predictions",
                    "n_images": 0,
                    "image_stems": [],
                    "cells_all": [],
                    "cells_informative": [],
                }
            rec = by_patient[pid]
            rec["n_images"] += 1
            rec["image_stems"].append(Path(item["image"]).stem)
            for det in item.get("cells", []):
                cell = _cell_from_prediction(det, conf_threshold)
                rec["cells_all"].append(det)
                if cell:
                    rec["cells_informative"].append(cell)

    for pid, rec in by_patient.items():
        _finalize_summary(rec, blast_classes)
    return by_patient


def aggregate_gt_from_data_root(
    data_root: str | Path,
    splits: tuple[str, ...] = ("train", "test"),
    blast_classes: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Aggregate from attributes/*.txt (ground truth), grouped by patient."""
    data_root = Path(data_root)
    blast_classes = blast_classes or [
        "Myeloblast",
        "Lymphoblast",
        "Monoblast",
        "Abnormal promyelocyte",
    ]
    by_patient: dict[str, dict[str, Any]] = {}

    for split in splits:
        attr_dir = data_root / "attributes" / split
        if not attr_dir.is_dir():
            continue
        for lb_path in sorted(attr_dir.glob("*.txt")):
            if lb_path.name.startswith("._") or lb_path.name.startswith("."):
                continue
            try:
                meta = parse_image_stem(lb_path.stem)
            except ValueError:
                continue
            pid = str(meta["patient_id"])
            if pid not in by_patient:
                by_patient[pid] = {
                    "patient_id": pid,
                    "disease_label_file": meta["disease_label"],
                    "source": "ground_truth",
                    "n_images": 0,
                    "image_stems": [],
                    "cells_all": [],
                    "cells_informative": [],
                }
            rec = by_patient[pid]
            rec["n_images"] += 1
            rec["image_stems"].append(lb_path.stem)

            lines = lb_path.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
            for line in lines:
                parts = line.split()
                if len(parts) < 5:
                    continue
                try:
                    cls_id = int(float(parts[0]))
                except ValueError:
                    continue
                class_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else str(cls_id)
                attrs_bin = {}
                if len(parts) >= 11:
                    for j, name in enumerate(ATTR_NAMES):
                        v = int(float(parts[5 + j]))
                        if v != 2:
                            attrs_bin[name] = v
                det = {
                    "class_name": class_name,
                    "class_id": cls_id,
                    "conf": 1.0,
                    "attributes_bin": attrs_bin,
                }
                rec["cells_all"].append(det)
                if class_name != "None" and attrs_bin:
                    rec["cells_informative"].append(
                        {
                            "class_name": class_name,
                            "class_id": cls_id,
                            "conf": 1.0,
                            "attributes_bin": attrs_bin,
                        }
                    )

    for rec in by_patient.values():
        _finalize_summary(rec, blast_classes)
    return by_patient


def _finalize_summary(rec: dict[str, Any], blast_classes: list[str]) -> None:
    informative = rec["cells_informative"]
    n_inf = len(informative)
    n_all = len(rec["cells_all"])
    counts = Counter(c["class_name"] for c in informative)
    total = sum(counts.values()) or 1
    differential = {
        k: round(100.0 * v / total, 1) for k, v in sorted(counts.items(), key=lambda x: -x[1])
    }
    blast_n = sum(counts.get(c, 0) for c in blast_classes)
    blast_pct = round(100.0 * blast_n / total, 1) if total else 0.0
    rec["n_cells_total"] = n_all
    rec["n_cells_informative"] = n_inf
    rec["n_cells_artifact"] = max(0, n_all - n_inf)
    rec["class_counts"] = dict(counts)
    rec["differential_pct"] = differential
    rec["blast_pct"] = blast_pct
    rec["flags"] = {
        "blasts_present": blast_n > 0,
        "blast_threshold_met": blast_pct >= 20.0,
    }
    rec["morphology_cohort"] = _morphology_stats(informative)
    confs = [float(c.get("conf", 1.0)) for c in informative]
    rec["qc"] = {
        "mean_det_conf": round(sum(confs) / len(confs), 3) if confs else 0.0,
        "pct_class_none": round(100.0 * (n_all - n_inf) / max(n_all, 1), 1),
    }
    # drop bulky raw lists in saved JSON
    del rec["cells_all"]
    del rec["cells_informative"]


def save_summaries(summaries: dict[str, dict], out_dir: str | Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for pid, summary in sorted(summaries.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
        path = out_dir / f"patient_{pid}.json"
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        paths.append(path)
    return paths


def load_manifest_cells(data_root: Path, manifest_csv: Path | None = None) -> None:
    """Unused helper for future manifest-based GT aggregate."""
    pass
