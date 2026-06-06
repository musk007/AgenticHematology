"""Patient-level aggregation for detector and attribute outputs."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from .schemas import Detection
from .schemas import AggregatedFindings, DetectionResult


BLAST_CLASSES = {"Myeloblast", "Lymphoblast", "Monoblast", "Abnormal promyelocyte"}
EXCLUDED_CLASSES = {"None", "Unknown"}
DEFAULT_IMAGE_WH = (640, 640)
OVERLAP_PERCENTAGE = 0.20
GLOBAL_STRIDE_PX = int(DEFAULT_IMAGE_WH[0] * (1.0 - OVERLAP_PERCENTAGE))
IOU_MATCH_THRESHOLD = 0.2


def aggregate(result: DetectionResult, conf_threshold: float = 0.25) -> AggregatedFindings:
    raw_cells = [d for d in result.detections if d.objectness >= conf_threshold]
    cells = _deduplicate_canvas_cells(raw_cells)
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
        "n_cells_raw_before_overlap_dedup": len(raw_cells),
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
            "global_canvas_stitching_active": True,
            "overlap_percentage": OVERLAP_PERCENTAGE,
            "iou_match_threshold": IOU_MATCH_THRESHOLD,
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


@dataclass
class _GlobalDetection:
    detection: Detection
    global_x1: float
    global_y1: float
    global_x2: float
    global_y2: float

    @property
    def global_area(self) -> float:
        return max(0.0, self.global_x2 - self.global_x1) * max(0.0, self.global_y2 - self.global_y1)

    def iou(self, other: "_GlobalDetection") -> float:
        inter_x1 = max(self.global_x1, other.global_x1)
        inter_y1 = max(self.global_y1, other.global_y1)
        inter_x2 = min(self.global_x2, other.global_x2)
        inter_y2 = min(self.global_y2, other.global_y2)
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        union_area = self.global_area + other.global_area - inter_area
        return inter_area / union_area if union_area > 0 else 0.0


def _deduplicate_canvas_cells(cells: list[Detection]) -> list[Detection]:
    """Remove duplicate cells caused by the 20% tile overlap in LLD fields."""
    global_cells = [_to_global_detection(cell) for cell in cells]
    sorted_cells = sorted(
        global_cells,
        key=lambda g: (g.detection.objectness, g.global_area),
        reverse=True,
    )
    retained: list[_GlobalDetection] = []

    while sorted_cells:
        current = sorted_cells.pop(0)
        retained.append(current)
        # Class-agnostic suppression catches overlap duplicates even when the
        # detector assigns a different lineage to the same physical cell.
        sorted_cells = [
            candidate
            for candidate in sorted_cells
            if current.iou(candidate) < IOU_MATCH_THRESHOLD
        ]
    return [g.detection for g in retained]


def _to_global_detection(cell: Detection) -> _GlobalDetection:
    grid_x, grid_y = _parse_filename_grid(cell.image_id)
    x1, y1, x2, y2 = cell.bbox_xyxy
    return _GlobalDetection(
        detection=cell,
        global_x1=(grid_x * GLOBAL_STRIDE_PX) + float(x1),
        global_y1=(grid_y * GLOBAL_STRIDE_PX) + float(y1),
        global_x2=(grid_x * GLOBAL_STRIDE_PX) + float(x2),
        global_y2=(grid_y * GLOBAL_STRIDE_PX) + float(y2),
    )


def _parse_filename_grid(image_id: str) -> tuple[int, int]:
    stem = image_id.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    parts = stem.split("_")
    if len(parts) < 3:
        return 0, 0
    clean_grid_x = "".join(filter(str.isdigit, parts[1]))
    clean_grid_y = "".join(filter(str.isdigit, parts[2]))
    if not clean_grid_x or not clean_grid_y:
        return 0, 0
    return int(clean_grid_x), int(clean_grid_y)


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
