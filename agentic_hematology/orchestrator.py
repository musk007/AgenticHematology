"""
orchestrator.py
===============
The agentic orchestrator. This is the component the user (or an upstream
service) talks to. It:

1. Receives a request containing images and/or a free-text instruction.
2. Parses the instruction to decide WHAT the user wants (intent routing).
3. Dispatches to the appropriate pipeline stages in the right order.
4. Collects outputs and returns a structured response.

Design notes
------------
The orchestrator is deliberately a thin *router*, not a monolith. It owns
no clinical logic; it only decides which agents to call and in what order,
then threads the shared `PipelineState` through them. The heavy lifting
stays in the specialised agents (detection, aggregation, classification,
reporting, validation).

Intent routing has two modes:
- `RuleBasedRouter` (default): keyword/heuristic routing over the text
  instruction. Deterministic, no API cost.
- `LLMRouter` (optional): uses an LLM to classify the instruction into one
  of the known intents when phrasing is ambiguous. Falls back to the rule
  router if the LLM is unavailable or returns something unrecognised.

Supported intents:
- FULL_REPORT       : detect → aggregate → classify → report → validate
- DETECT_ONLY       : detect → aggregate (return structured findings only)
- CLASSIFY_ONLY     : detect → aggregate → classify (no narrative report)
- REPORT_FROM_JSON  : skip detection; caller supplies precomputed findings
- EXPLAIN           : answer a free-text question about an existing result

The orchestrator returns an `OrchestratorResponse` describing what was run,
the resulting state, and any routing rationale (for auditability).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .aggregator import aggregate
from .detection_agent import BaseDetectionAgent
from .leukemia_classifier import HybridClassifier
from .pipeline import (
    aggregate_node,
    classify_node,
    detect_node,
    reflect_node,
    report_node,
    validate_node,
)
from .report_generator import BaseReportGenerator, TemplateReportGenerator
from .schemas import AggregatedFindings, DetectionResult, PipelineState
from .validators import LLMOutputValidator, ReportConsistencyValidator


# ---------------------------------------------------------------------------
# Intents
# ---------------------------------------------------------------------------

class Intent(str, Enum):
    FULL_REPORT = "FULL_REPORT"
    DETECT_ONLY = "DETECT_ONLY"
    CLASSIFY_ONLY = "CLASSIFY_ONLY"
    REPORT_FROM_JSON = "REPORT_FROM_JSON"
    EXPLAIN = "EXPLAIN"


@dataclass
class OrchestratorRequest:
    """What the orchestrator receives."""
    case_id: str
    image_paths: list[str] = field(default_factory=list)
    instruction: str | None = None          # free-text from the user
    precomputed_findings: dict | None = None  # for REPORT_FROM_JSON
    forced_intent: Intent | None = None      # bypass routing if set


@dataclass
class OrchestratorResponse:
    """What the orchestrator returns."""
    case_id: str
    intent: Intent
    routing_rationale: str
    state: PipelineState
    answer: str | None = None                # for EXPLAIN intent

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "intent": self.intent.value,
            "routing_rationale": self.routing_rationale,
            "report_markdown": (self.state.report.markdown if self.state.report else None),
            "leukemia_class": (
                self.state.classification.predicted_class
                if self.state.classification else None
            ),
            "consistency_passed": self.state.consistency_passed,
            "llm_output_passed": self.state.llm_output_passed,
            "agent_actions": self.state.agent_actions,
            "n_reflect_iterations": self.state.n_reflect_iterations,
            "flagged_for_review": self.state.flagged_for_review,
            "review_reasons": self.state.review_reasons,
            "answer": self.answer,
            "errors": self.state.errors,
        }


# ---------------------------------------------------------------------------
# Intent routers
# ---------------------------------------------------------------------------

class BaseRouter(ABC := type("ABC", (), {})):  # lightweight ABC
    def route(self, request: OrchestratorRequest) -> tuple[Intent, str]:
        raise NotImplementedError


class RuleBasedRouter:
    """Keyword-driven intent routing. Deterministic, no API cost."""

    # Keyword → intent. Checked in order; first match wins.
    _PATTERNS: list[tuple[re.Pattern, Intent]] = [
        # CLASSIFY_ONLY — "only classify", "just tell me the subtype", etc.
        # Checked before DETECT_ONLY so "classify" wins over a stray "cells".
        (re.compile(r"\b(only|just)\b.*\b(classif|diagnos|subtype|leukemia type|which leukemia)\w*", re.I), Intent.CLASSIFY_ONLY),
        (re.compile(r"\b(classif|diagnos|subtype)\w*\b.*\b(only|just)\b", re.I), Intent.CLASSIFY_ONLY),
        # DETECT_ONLY — "only detect", "just count the cells", etc.
        (re.compile(r"\b(only|just)\b.*\b(detect|count|localiz|localis|find cells?)\w*", re.I), Intent.DETECT_ONLY),
        (re.compile(r"\b(detect|count|localiz|localis)\w*\b.*\b(only|just)\b", re.I), Intent.DETECT_ONLY),
        # EXPLAIN — questions / justification requests.
        (re.compile(r"\b(explain|why|how come|justify|rationale)\b", re.I), Intent.EXPLAIN),
        (re.compile(r"\bwhat does\b.*\bmean\b", re.I), Intent.EXPLAIN),
        # FULL_REPORT — anything mentioning a report.
        (re.compile(r"\breport\b", re.I), Intent.FULL_REPORT),
    ]

    def route(self, request: OrchestratorRequest) -> tuple[Intent, str]:
        if request.forced_intent:
            return request.forced_intent, "forced by caller"

        if request.precomputed_findings is not None and not request.image_paths:
            return Intent.REPORT_FROM_JSON, "precomputed findings supplied, no images"

        text = (request.instruction or "").strip()
        if not text:
            # No instruction → default to a full report if we have images.
            if request.image_paths:
                return Intent.FULL_REPORT, "no instruction; images present → full report"
            return Intent.EXPLAIN, "no instruction and no images"

        for pattern, intent in self._PATTERNS:
            if pattern.search(text):
                return intent, f"matched rule {pattern.pattern!r}"

        # Default.
        return Intent.FULL_REPORT, "no specific rule matched; defaulting to full report"


class LLMRouter:
    """
    LLM-backed intent classifier for ambiguous instructions. Falls back to
    the rule router if the LLM is unavailable or returns garbage.
    """

    def __init__(self, llm_complete, fallback: RuleBasedRouter | None = None):
        """
        :param llm_complete: a callable (system:str, user:str) -> str.
        """
        self.llm_complete = llm_complete
        self.fallback = fallback or RuleBasedRouter()

    _SYSTEM = (
        "You are an intent classifier for a hematology pipeline. "
        "Classify the user's instruction into exactly one of: "
        "FULL_REPORT, DETECT_ONLY, CLASSIFY_ONLY, REPORT_FROM_JSON, EXPLAIN. "
        "Reply with ONLY the label, nothing else."
    )

    def route(self, request: OrchestratorRequest) -> tuple[Intent, str]:
        if request.forced_intent:
            return request.forced_intent, "forced by caller"
        text = (request.instruction or "").strip()
        if not text:
            return self.fallback.route(request)

        try:
            raw = self.llm_complete(self._SYSTEM, text).strip().upper()
            for intent in Intent:
                if intent.value in raw:
                    return intent, f"LLM router → {intent.value}"
        except Exception:
            pass
        return self.fallback.route(request)


# ---------------------------------------------------------------------------
# The orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Receives requests, routes by intent, dispatches to pipeline stages.

    Wire it up with the agents you want:
        orch = Orchestrator(
            detector=TwoStageDetectionAgent(...),
            classifier=HybridClassifier(...),
            report_generator=TemplateReportGenerator(),  # or Claude/OpenAI
            router=RuleBasedRouter(),
        )
        resp = orch.handle(OrchestratorRequest(
            case_id="12",
            image_paths=[...],
            instruction="Generate a full diagnostic report",
        ))
    """

    def __init__(
        self,
        detector: BaseDetectionAgent,
        classifier: HybridClassifier | None = None,
        report_generator: BaseReportGenerator | None = None,
        router: Any | None = None,
        enable_reflect: bool = True,
        enable_validate: bool = True,
        validate_failure_policy: str = "strip",
        llm_explain=None,  # optional callable (system, user) -> str for EXPLAIN
        reflection_agent=None,           # ReflectionAgent | None — enables agency
        max_reflect_iterations: int = 2,
    ):
        self.detector = detector
        self.classifier = classifier or HybridClassifier()
        self.report_generator = report_generator or TemplateReportGenerator()
        self.router = router or RuleBasedRouter()
        self.enable_reflect = enable_reflect
        self.enable_validate = enable_validate
        self.validate_failure_policy = validate_failure_policy
        self.llm_explain = llm_explain
        self.reflection_agent = reflection_agent
        self.max_reflect_iterations = max_reflect_iterations
        self._consistency = ReportConsistencyValidator()
        self._llm_guard = LLMOutputValidator()

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def handle(self, request: OrchestratorRequest) -> OrchestratorResponse:
        intent, rationale = self.router.route(request)
        state = PipelineState(
            case_id=request.case_id,
            image_paths=request.image_paths,
            text_input=request.instruction,
        )

        # If caller supplied precomputed findings, inject them.
        if request.precomputed_findings is not None:
            state.findings = self._findings_from_dict(
                request.case_id, request.precomputed_findings
            )

        answer = None
        if intent == Intent.DETECT_ONLY:
            state = self._run_detect_aggregate(state)
        elif intent == Intent.CLASSIFY_ONLY:
            state = self._run_detect_aggregate(state)
            state = classify_node(state, self.classifier)
        elif intent == Intent.REPORT_FROM_JSON:
            state = self._run_report_from_findings(state)
        elif intent == Intent.EXPLAIN:
            answer = self._run_explain(state, request)
        else:  # FULL_REPORT
            state = self._run_full(state)

        return OrchestratorResponse(
            case_id=request.case_id,
            intent=intent,
            routing_rationale=rationale,
            state=state,
            answer=answer,
        )

    # ------------------------------------------------------------------
    # Intent handlers
    # ------------------------------------------------------------------

    def _run_detect_aggregate(self, state: PipelineState) -> PipelineState:
        state = detect_node(state, self.detector)
        state = aggregate_node(state)
        return state

    def _run_full(self, state: PipelineState) -> PipelineState:
        state = detect_node(state, self.detector)
        state = aggregate_node(state)
        state = classify_node(state, self.classifier)
        if self.enable_reflect:
            state = reflect_node(
                state,
                agent=self.reflection_agent,
                classifier=self.classifier,
                max_iterations=self.max_reflect_iterations,
            )
        state = report_node(state, self.report_generator)
        if self.enable_validate:
            state = validate_node(
                state,
                consistency_validator=self._consistency,
                llm_output_validator=self._llm_guard,
                failure_policy=self.validate_failure_policy,
                report_generator=self.report_generator,
            )
        return state

    def _run_report_from_findings(self, state: PipelineState) -> PipelineState:
        if state.findings is None:
            state.errors.append("REPORT_FROM_JSON: no findings supplied")
            return state
        state = classify_node(state, self.classifier)
        if self.enable_reflect:
            state = reflect_node(
                state,
                agent=self.reflection_agent,
                classifier=self.classifier,
                max_iterations=self.max_reflect_iterations,
            )
        state = report_node(state, self.report_generator)
        if self.enable_validate:
            state = validate_node(
                state,
                consistency_validator=self._consistency,
                llm_output_validator=self._llm_guard,
                failure_policy=self.validate_failure_policy,
                report_generator=self.report_generator,
            )
        return state

    def _run_explain(
        self, state: PipelineState, request: OrchestratorRequest
    ) -> str | None:
        """
        Answer a free-text question. If findings are available, run the full
        pipeline first so the LLM has grounded context; then answer.
        """
        if state.findings is None and state.image_paths:
            state = self._run_full(state)

        if self.llm_explain is None:
            return (
                "EXPLAIN intent requires an LLM. Provide `llm_explain` to the "
                "Orchestrator. Structured findings are available in the state."
            )

        context = ""
        if state.findings is not None:
            context = json.dumps(state.findings.report_ready, indent=2)
        if state.report is not None:
            context += "\n\nREPORT:\n" + state.report.markdown

        system = (
            "You are a hematopathology assistant. Answer the user's question "
            "using ONLY the structured findings and report provided. Do not "
            "invent numbers or findings."
        )
        user = f"QUESTION: {request.instruction}\n\nCONTEXT:\n{context}"
        try:
            return self.llm_explain(system, user)
        except Exception as e:
            return f"EXPLAIN failed: {e}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _findings_from_dict(case_id: str, payload: dict) -> AggregatedFindings:
        """Build an AggregatedFindings from a precomputed JSON payload."""
        return AggregatedFindings(
            case_id=case_id,
            n_images=payload.get("n_images", 0),
            n_cells_total=payload.get("n_cells_total", 0),
            n_cells_identified_wbc=payload.get("n_cells_identified_wbc", 0),
            cell_counts=payload.get("cell_counts", {}),
            cell_percentages_all=payload.get("cell_percentages_all", {}),
            cell_percentages_clinical=payload.get("cell_percentages_clinical", {}),
            attributes=payload.get("attributes", {}),
            report_ready=payload["report_ready"],
            grounding_index=payload.get("grounding_index", {}),
        )