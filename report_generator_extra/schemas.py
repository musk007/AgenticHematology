"""
schemas.py
==========
Strict dataclasses for everything that flows between agents.

A single source of truth for the data shape lets each agent be developed and
tested in isolation. These mirror the JSON schema your data-creation pipeline
already produces (the `report_ready` block).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Detector outputs
# ---------------------------------------------------------------------------

@dataclass
class Detection:
    """A single detected cell with its bounding box, class, and attributes."""
    cell_id: str                           # stable id across the case, e.g. "img03_c12"
    image_id: str                          # which field of view it came from
    bbox_xyxy: tuple[float, float, float, float]   # x1, y1, x2, y2 in pixels
    cell_type: str                         # one of the 14 LLD classes
    objectness: float                      # detector confidence
    cell_type_prob: float                  # classification head probability
    attributes: dict[str, str] = field(default_factory=dict)
    attribute_probs: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "image_id": self.image_id,
            "bbox_xyxy": list(self.bbox_xyxy),
            "cell_type": self.cell_type,
            "objectness": self.objectness,
            "cell_type_prob": self.cell_type_prob,
            "attributes": self.attributes,
            "attribute_probs": self.attribute_probs,
        }


@dataclass
class DetectionResult:
    """All detections for a single case (one patient, possibly many FoVs)."""
    case_id: str
    n_images: int
    detections: list[Detection]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "n_images": self.n_images,
            "detections": [d.to_dict() for d in self.detections],
        }


# ---------------------------------------------------------------------------
# Aggregator outputs — mirror your existing `report_ready` schema
# ---------------------------------------------------------------------------

@dataclass
class AggregatedFindings:
    """
    Structured per-case findings ready to be consumed by the leukemia
    classifier and the report generator. Shape matches the JSON schema you've
    been producing (so this is interoperable with your existing data).
    """
    case_id: str
    n_images: int
    n_cells_total: int
    n_cells_identified_wbc: int
    cell_counts: dict[str, int]
    cell_percentages_all: dict[str, float]
    cell_percentages_clinical: dict[str, float]
    attributes: dict[str, dict[str, Any]]
    report_ready: dict[str, Any]
    # Auditing trail: which cell_ids contributed to each finding.
    grounding_index: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "n_images": self.n_images,
            "n_cells_total": self.n_cells_total,
            "n_cells_identified_wbc": self.n_cells_identified_wbc,
            "cell_counts": self.cell_counts,
            "cell_percentages_all": self.cell_percentages_all,
            "cell_percentages_clinical": self.cell_percentages_clinical,
            "attributes": self.attributes,
            "report_ready": self.report_ready,
            "grounding_index": self.grounding_index,
        }


# ---------------------------------------------------------------------------
# Leukemia classifier outputs
# ---------------------------------------------------------------------------

@dataclass
class LeukemiaClassification:
    """
    Patient-level leukemia type prediction from the differential.

    `predicted_class` is one of:
        "ALL", "AML", "APML", "CML", "CLL", or "UNCLASSIFIED"
    """
    predicted_class: str
    confidence: float                      # in [0, 1]
    class_probabilities: dict[str, float]  # full softmax over supported classes
    rule_based_route: str                  # the deterministic backup route
    routing_rationale: str                 # one-line explanation
    low_confidence: bool                   # triggers human review if True

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicted_class": self.predicted_class,
            "confidence": self.confidence,
            "class_probabilities": self.class_probabilities,
            "rule_based_route": self.rule_based_route,
            "routing_rationale": self.routing_rationale,
            "low_confidence": self.low_confidence,
        }


# ---------------------------------------------------------------------------
# Final grounded report
# ---------------------------------------------------------------------------

@dataclass
class GroundedReport:
    """Markdown report plus the cell-id citations that ground each claim."""
    case_id: str
    leukemia_class: str
    confidence: float
    markdown: str
    # Maps a claim id (e.g. "C1") to the list of cell_ids that support it.
    citations: dict[str, list[str]] = field(default_factory=dict)
    flagged_for_review: bool = False
    review_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "leukemia_class": self.leukemia_class,
            "confidence": self.confidence,
            "markdown": self.markdown,
            "citations": self.citations,
            "flagged_for_review": self.flagged_for_review,
            "review_reasons": self.review_reasons,
        }


# ---------------------------------------------------------------------------
# Orchestrator state — the LangGraph-style state object that flows through
# every node. Each node fills in one more field.
# ---------------------------------------------------------------------------

@dataclass
class PipelineState:
    case_id: str
    image_paths: list[str]
    text_input: str | None = None             # optional clinical context from the user
    detections: DetectionResult | None = None
    findings: AggregatedFindings | None = None
    classification: LeukemiaClassification | None = None
    report: GroundedReport | None = None
    # Validation results — populated by validate_node.
    consistency_passed: bool | None = None
    consistency_issues: list[str] = field(default_factory=list)
    llm_output_passed: bool | None = None
    llm_output_issues: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
