"""Patient-level aggregation for detector and attribute outputs."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .schemas import AggregatedFindings, DetectionResult


BLAST_CLASSES = {"Myeloblast", "Lymphoblast", "Monoblast", "Abnormal promyelocyte"}
EXCLUDED_CLASSES = {"None", "Unknown"}


def aggregate(result: DetectionResult, conf_threshold: float = 0.25) -> AggregatedFindings:
    cells = [d for d in result.detections if d.objectness >= conf_threshold]
    informative = [d for d in cells if d.cell_type not in EXCLUDED_CLASSES]
    counts = Counter(d.cell_type for d in informative)
    total_inf = sum(counts.values())
    total_all = len(cells)

    clinical_pct = {
        name: round(100.0 * count / total_inf, 1) for name, count in counts.most_common()
    } if total_inf else {}
    all_pct = {
        name: round(100.0 * count / max(total_all, 1), 1) for name, count in counts.most_common()
    }

    morphology = _morphology_cohort(informative)
    blast_n = sum(counts.get(name, 0) for name in BLAST_CLASSES)
    blast_pct = round(100.0 * blast_n / total_inf, 1) if total_inf else 0.0
    grounding_index = _grounding_index(informative)

    report_ready: dict[str, Any] = {
        "patient_id": result.case_id,
        "source": "agentic_orchestrator",
        "n_images": result.n_images,
        "image_stems": sorted({d.image_id.rsplit(".", 1)[0] for d in result.detections}),
        "n_cells_total": total_all,
        "n_cells_informative": total_inf,
        "n_cells_artifact": max(0, total_all - total_inf),
        "class_counts": dict(counts),
        "differential_pct": clinical_pct,
        "blast_pct": blast_pct,
        "flags": {
            "blasts_present": blast_n > 0,
            "blast_threshold_met": blast_pct >= 20.0,
        },
        "morphology_cohort": morphology,
        "grounding_index": grounding_index,
        "qc": {
            "mean_det_conf": round(
                sum(float(d.objectness) for d in informative) / total_inf, 3
            ) if total_inf else 0.0,
            "pct_class_none": round(
                100.0 * (total_all - total_inf) / max(total_all, 1), 1
            ),
        },
    }

    return AggregatedFindings(
        case_id=result.case_id,
        n_images=result.n_images,
        n_cells_total=total_all,
        n_cells_identified_wbc=total_inf,
        cell_counts=dict(counts),
        cell_percentages_all=all_pct,
        cell_percentages_clinical=clinical_pct,
        attributes=morphology,
        report_ready=report_ready,
        grounding_index=grounding_index,
    )


def _morphology_cohort(cells) -> dict[str, dict[str, Any]]:
    by_class: dict[str, list] = defaultdict(list)
    for cell in cells:
        by_class[cell.cell_type].append(cell)

    out: dict[str, dict[str, Any]] = {}
    for cell_type, group in by_class.items():
        attr_values: dict[str, list[float]] = defaultdict(list)
        for cell in group:
            for name, value in cell.attributes.items():
                if name == "class_id" or not isinstance(value, (int, float)):
                    continue
                attr_values[name].append(float(value))
        out[cell_type] = {
            "n": len(group),
            "attr_pos_rate": {
                name: round(sum(values) / len(values), 4)
                for name, values in sorted(attr_values.items())
                if values
            },
        }
    return out


def _grounding_index(cells) -> dict[str, Any]:
    return {
        cell.cell_id: {
            "image_id": cell.image_id,
            "bbox_xyxy": [round(float(v), 2) for v in cell.bbox_xyxy],
            "cell_type": cell.cell_type,
            "confidence": round(float(cell.objectness), 4),
            "attributes": {
                k: v for k, v in cell.attributes.items() if k != "class_id"
            },
        }
        for cell in cells
    }
