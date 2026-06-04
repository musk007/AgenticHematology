"""
pipeline.py
===========
The agentic orchestrator that wires the four agents together.

Design
------
The pipeline is structured as a state machine over `PipelineState`. Each
node consumes the state, performs its work, and returns an updated state.
Nodes are independent functions so they can be:

- Swapped (real YOLO ↔ stub) without changing the orchestrator.
- Reordered or run in parallel where the graph allows.
- Migrated to a real LangGraph `StateGraph` later — the function
  signatures already match.

Default node order:

    detect → aggregate → classify → reflect → report → validate

`reflect` is an optional integrity check that catches obvious failure
modes (no detections, all artefacts, classification mismatch) and sets
the `flagged_for_review` bit so a human is brought in.

`validate` runs two guards after the report is generated:
1. `ReportConsistencyValidator` — every number in the rendered markdown
   matches the source JSON (catches template / aggregator drift).
2. `LLMOutputValidator` — every number in any LLM-generated section was
   already present in the inputs (catches numeric hallucination).

Failure policies (configurable):
- "flag"   : append the violations to review_reasons; emit the report anyway.
- "strip"  : if the LLM-generated section failed, drop it; keep the
             deterministic template body. (Default — safest.)
- "retry"  : ask the LLM to regenerate with the violations appended to the
             prompt, then on second failure fall back to "strip".

Two execution modes:
- `PIPELINE.run(state)` — single-case synchronous run.
- `PIPELINE.run_batch(states)` — convenience batch runner.

To migrate to LangGraph proper, the nodes below already conform to the
`(state) -> partial_state` signature; you'd register each as a node and
add edges in the order shown.
"""

from __future__ import annotations

from typing import Any, Callable, Literal

from .aggregator import aggregate
from .detection_agent import BaseDetectionAgent
from .leukemia_classifier import HybridClassifier
from .report_generator import BaseReportGenerator, TemplateReportGenerator
from .schemas import (
    AggregatedFindings,
    DetectionResult,
    GroundedReport,
    LeukemiaClassification,
    PipelineState,
)
from .validators import (
    LLMOutputValidator,
    ReportConsistencyValidator,
)


# ---------------------------------------------------------------------------
# Individual node functions
# ---------------------------------------------------------------------------

def detect_node(
    state: PipelineState, detector: BaseDetectionAgent
) -> PipelineState:
    try:
        state.detections = detector.detect(state.case_id, state.image_paths)
    except Exception as e:
        state.errors.append(f"detect_node: {e}")
    return state


def aggregate_node(state: PipelineState) -> PipelineState:
    if state.detections is None:
        state.errors.append("aggregate_node: no detections in state")
        return state
    try:
        state.findings = aggregate(state.detections)
    except Exception as e:
        state.errors.append(f"aggregate_node: {e}")
    return state


def classify_node(
    state: PipelineState, classifier: HybridClassifier
) -> PipelineState:
    if state.findings is None:
        state.errors.append("classify_node: no findings in state")
        return state
    try:
        state.classification = classifier.classify(state.findings)
    except Exception as e:
        state.errors.append(f"classify_node: {e}")
    return state


def reflect_node(state: PipelineState) -> PipelineState:
    """
    Lightweight integrity check before the LLM is invoked. Sets
    classification.low_confidence and adds rationale notes when something
    looks off.

    Catches:
    - empty detections
    - all-artefact cases
    - extremely sparse cell counts (< 50 WBCs)
    - very high artefact fraction (> 50%)
    - rule/learned disagreement (handled inside classifier but echoed here)
    """
    if state.findings is None or state.classification is None:
        return state

    f = state.findings
    cls = state.classification
    notes: list[str] = []

    if f.n_cells_identified_wbc == 0:
        notes.append("No informative WBCs detected; downstream classification unreliable.")
    elif f.n_cells_identified_wbc < 50:
        notes.append(
            f"Very low informative WBC count ({f.n_cells_identified_wbc}); "
            f"differential statistics may not be representative."
        )

    if f.n_cells_total > 0:
        artefact_frac = (f.n_cells_total - f.n_cells_identified_wbc) / f.n_cells_total
        if artefact_frac > 0.5:
            notes.append(
                f"High artefact fraction ({artefact_frac:.0%}); slide quality is poor."
            )

    if cls.predicted_class == "UNCLASSIFIED":
        notes.append("Findings do not match a specific WHO/ICC entity on morphology alone.")

    if notes:
        cls.low_confidence = True
        cls.routing_rationale = (
            cls.routing_rationale + " | Reflect: " + "; ".join(notes)
        )

    return state


def report_node(
    state: PipelineState, report_generator: BaseReportGenerator
) -> PipelineState:
    if state.findings is None or state.classification is None or state.detections is None:
        state.errors.append("report_node: missing prerequisite state")
        return state
    try:
        state.report = report_generator.generate(
            findings=state.findings,
            classification=state.classification,
            detection_result=state.detections,
            clinical_context=state.text_input,
        )
    except Exception as e:
        state.errors.append(f"report_node: {e}")
    return state


def validate_node(
    state: PipelineState,
    consistency_validator: ReportConsistencyValidator,
    llm_output_validator: LLMOutputValidator,
    failure_policy: Literal["flag", "strip", "retry"] = "strip",
    report_generator: BaseReportGenerator | None = None,
    llm_section_marker: str = "**Morphologic interpretation:**",
) -> PipelineState:
    """
    Run both validators on the produced report and apply the failure policy.

    Guard 1 — Report ↔ JSON consistency:
      catches template / aggregator drift. ALWAYS runs.

    Guard 2 — LLM numeric containment:
      only runs if the report contains an LLM-generated section, detected
      by the presence of `llm_section_marker` in the markdown. The numeric
      tokens of that section alone are checked against the union of the
      structured findings JSON and the rest of the report.
    """
    if state.report is None or state.findings is None:
        state.errors.append("validate_node: no report to validate")
        return state

    # --- Guard 1: consistency ------------------------------------------------
    # Build the legacy JSON shape the consistency validator expects.
    # `metadata_filename_diagnosis` is populated from the classification so
    # the alias matcher in the consistency validator has something to bind to.
    findings_dict = state.findings.to_dict()
    findings_dict.setdefault(
        "metadata_filename_diagnosis", state.classification.predicted_class
        if state.classification else None,
    )
    consistency = consistency_validator.validate(
        state.report.markdown, findings_dict
    )
    state.consistency_passed = consistency.passed
    state.consistency_issues = consistency.issues + consistency.parse_errors

    # --- Guard 2: LLM numeric containment ------------------------------------
    state.llm_output_passed = True  # default: no LLM content present
    llm_section, body_without_llm = _split_llm_section(
        state.report.markdown, llm_section_marker
    )
    if llm_section is not None:
        result = llm_output_validator.validate(
            llm_section,
            source_json=findings_dict,
            source_text=body_without_llm,
        )
        state.llm_output_passed = result.passed
        if not result.passed:
            state.llm_output_issues = [result.reason] + result.novel_numbers_in_context

            # Apply failure policy.
            if failure_policy == "retry" and report_generator is not None:
                # Retry once: re-run the report generator. The downstream
                # report generator's prompt builder is responsible for
                # picking up `result.novel_numbers` via the feedback hook
                # if implemented; otherwise this is a plain re-run.
                feedback = llm_output_validator.build_retry_feedback(result)
                augmented_context = (state.text_input or "") + "\n\n" + feedback
                try:
                    retry_report = report_generator.generate(
                        findings=state.findings,
                        classification=state.classification,
                        detection_result=state.detections,
                        clinical_context=augmented_context.strip(),
                    )
                    # Re-check after retry.
                    retry_section, retry_body = _split_llm_section(
                        retry_report.markdown, llm_section_marker
                    )
                    retry_check = llm_output_validator.validate(
                        retry_section or "",
                        source_json=findings_dict,
                        source_text=retry_body,
                    )
                    if retry_check.passed:
                        state.report = retry_report
                        state.llm_output_passed = True
                        state.llm_output_issues = []
                    else:
                        # Retry also failed → fall through to strip.
                        state.report.markdown = body_without_llm
                        state.report.flagged_for_review = True
                        state.report.review_reasons.append(
                            "llm_section_stripped_after_failed_retry"
                        )
                except Exception as e:
                    state.errors.append(f"validate_node retry: {e}")
                    state.report.markdown = body_without_llm
                    state.report.flagged_for_review = True

            elif failure_policy == "strip":
                state.report.markdown = body_without_llm
                state.report.flagged_for_review = True
                state.report.review_reasons.append("llm_section_stripped")

            elif failure_policy == "flag":
                state.report.flagged_for_review = True
                state.report.review_reasons.append("llm_section_failed_validation")

    if not consistency.passed:
        # Consistency failures are template-side bugs, not LLM hallucination.
        # Always flag — fixing the template is the right response.
        state.report.flagged_for_review = True
        state.report.review_reasons.append("consistency_validation_failed")

    return state


def _split_llm_section(
    markdown: str, marker: str
) -> tuple[str | None, str]:
    """
    Split a report into (llm_section, rest).

    The LLM-generated section is detected by the literal marker string
    (e.g. "**Morphologic interpretation:**") and is assumed to end at the
    next blank line followed by another bold-prefixed line, OR end of
    document.

    Returns (None, full_markdown) if the marker is not present.
    """
    idx = markdown.find(marker)
    if idx == -1:
        return None, markdown

    # Find the end: next "\n\n**" pattern, or end of doc.
    rest_start = idx + len(marker)
    next_section = markdown.find("\n\n**", rest_start)
    if next_section == -1:
        # Trailing section.
        llm_section = markdown[idx:].strip()
        body_without_llm = markdown[:idx].rstrip()
    else:
        llm_section = markdown[idx:next_section].strip()
        body_without_llm = (
            markdown[:idx].rstrip() + "\n\n" + markdown[next_section:].lstrip()
        )

    return llm_section, body_without_llm


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class LeukemiaPipeline:
    """Sequential orchestrator. Drop-in upgrade path to LangGraph."""

    def __init__(
        self,
        detector: BaseDetectionAgent,
        classifier: HybridClassifier | None = None,
        report_generator: BaseReportGenerator | None = None,
        enable_reflect: bool = True,
        enable_validate: bool = True,
        validate_failure_policy: Literal["flag", "strip", "retry"] = "strip",
        consistency_pct_tolerance: float = 0.11,
        llm_numeric_whitelist: set[str] | None = None,
    ):
        self.detector = detector
        self.classifier = classifier or HybridClassifier()
        self.report_generator = report_generator or TemplateReportGenerator()
        self.enable_reflect = enable_reflect
        self.enable_validate = enable_validate
        self.validate_failure_policy = validate_failure_policy
        self.consistency_validator = ReportConsistencyValidator(
            pct_tolerance=consistency_pct_tolerance,
        )
        self.llm_output_validator = LLMOutputValidator(
            whitelist=llm_numeric_whitelist,
        )

    def run(self, state: PipelineState) -> PipelineState:
        state = detect_node(state, self.detector)
        state = aggregate_node(state)
        state = classify_node(state, self.classifier)
        if self.enable_reflect:
            state = reflect_node(state)
        state = report_node(state, self.report_generator)
        if self.enable_validate:
            state = validate_node(
                state,
                consistency_validator=self.consistency_validator,
                llm_output_validator=self.llm_output_validator,
                failure_policy=self.validate_failure_policy,
                report_generator=self.report_generator,
            )
        return state

    def run_batch(self, states: list[PipelineState]) -> list[PipelineState]:
        return [self.run(s) for s in states]

    # -------------------------------------------------------------------
    # Optional: build a real LangGraph graph if the dependency is present.
    # -------------------------------------------------------------------

    def as_langgraph(self):
        """
        Build a LangGraph `StateGraph` from the same nodes. Useful when you
        want streaming, checkpointing, parallel branches, or distributed
        execution. Falls back gracefully if LangGraph is not installed.
        """
        try:
            from langgraph.graph import StateGraph, END  # type: ignore
        except ImportError as e:
            raise ImportError(
                "Install LangGraph to use as_langgraph(): `pip install langgraph`"
            ) from e

        graph = StateGraph(PipelineState)
        graph.add_node("detect", lambda s: detect_node(s, self.detector))
        graph.add_node("aggregate", aggregate_node)
        graph.add_node("classify", lambda s: classify_node(s, self.classifier))
        if self.enable_reflect:
            graph.add_node("reflect", reflect_node)
        graph.add_node("report", lambda s: report_node(s, self.report_generator))
        if self.enable_validate:
            graph.add_node("validate", lambda s: validate_node(
                s,
                consistency_validator=self.consistency_validator,
                llm_output_validator=self.llm_output_validator,
                failure_policy=self.validate_failure_policy,
                report_generator=self.report_generator,
            ))

        graph.set_entry_point("detect")
        graph.add_edge("detect", "aggregate")
        graph.add_edge("aggregate", "classify")
        if self.enable_reflect:
            graph.add_edge("classify", "reflect")
            graph.add_edge("reflect", "report")
        else:
            graph.add_edge("classify", "report")
        if self.enable_validate:
            graph.add_edge("report", "validate")
            graph.add_edge("validate", END)
        else:
            graph.add_edge("report", END)

        return graph.compile()
