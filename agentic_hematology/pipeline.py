"""Composable pipeline nodes used by the orchestrator."""
from __future__ import annotations

from .aggregator import aggregate
from .agent_controller import (
    AgentAction,
    ReflectionAgent,
    build_case_state,
)
from .detection_agent import BaseDetectionAgent
from .leukemia_classifier import HybridClassifier
from .report_generator import BaseReportGenerator
from .schemas import PipelineState


def detect_node(state: PipelineState, detector: BaseDetectionAgent) -> PipelineState:
    if not state.image_paths:
        state.errors.append("Detection requested but no image paths were supplied")
        return state
    state.detection_result = detector.detect(state.case_id, state.image_paths)
    return state


def aggregate_node(state: PipelineState) -> PipelineState:
    if state.detection_result is None:
        state.errors.append("Aggregation requested before detection")
        return state
    # Honour the (possibly agent-adjusted) confidence threshold.
    state.findings = aggregate(state.detection_result, conf_threshold=state.conf_threshold)
    return state


def classify_node(state: PipelineState, classifier: HybridClassifier) -> PipelineState:
    if state.findings is None:
        state.errors.append("Classification requested before aggregation")
        return state
    state.classification = classifier.classify(state.findings)
    return state


def reflect_node(
    state: PipelineState,
    *,
    agent: ReflectionAgent | None = None,
    classifier: HybridClassifier | None = None,
    max_iterations: int = 2,
) -> PipelineState:
    """
    Agentic reflection loop.

    The reflection agent (Qwen3) inspects the intermediate findings +
    classification and decides the next PROCESS action at runtime:

      - proceed          → exit the loop, evidence is sufficient
      - re_aggregate     → re-run aggregation at a stricter confidence
                           threshold, re-classify, and reflect again
      - flag_for_review  → mark the case for mandatory human review, exit

    This is the component that makes the pipeline agentic: a model makes a
    control-flow decision based on intermediate results, the loop can
    iterate, and the stopping condition is model-influenced. The agent
    never changes the diagnosis — the deterministic classifier stays
    authoritative.

    If no agent is supplied the node is a safe no-op (preserves the old
    automated behaviour), so the pipeline still runs without an LLM.
    """
    if agent is None or state.findings is None:
        return state

    re_aggregate_used = False

    for iteration in range(1, max_iterations + 1):
        state.n_reflect_iterations = iteration
        case_state = build_case_state(state.findings, state.classification)
        decision = agent.decide(
            case_state,
            re_aggregate_used=re_aggregate_used,
            current_conf_threshold=state.conf_threshold,
            iteration=iteration,
        )
        state.agent_actions.append({"iteration": iteration, **decision.to_dict()})

        if decision.action == AgentAction.PROCEED:
            break

        if decision.action == AgentAction.FLAG_FOR_REVIEW:
            state.flagged_for_review = True
            state.review_reasons.append(decision.reason)
            break

        if decision.action == AgentAction.RE_AGGREGATE:
            # Apply the agent's chosen threshold, re-aggregate, re-classify,
            # then loop to reflect again on the sharpened evidence.
            state.conf_threshold = decision.conf_threshold or state.conf_threshold
            re_aggregate_used = True
            state = aggregate_node(state)
            if classifier is not None:
                state = classify_node(state, classifier)
            continue

    else:
        # Loop exhausted without an explicit proceed → escalate, don't silently ship.
        state.flagged_for_review = True
        state.review_reasons.append(
            f"reflection loop hit max_iterations={max_iterations} without converging"
        )

    return state


def report_node(state: PipelineState, report_generator: BaseReportGenerator) -> PipelineState:
    if state.findings is None:
        state.errors.append("Report requested before aggregation")
        return state
    state.report = report_generator.generate(
        state.findings,
        state.classification,
        instruction=state.text_input,
    )
    # Surface the agent's review decision in the report markdown so it is
    # never lost downstream.
    if state.flagged_for_review and state.report is not None:
        reasons = "; ".join(state.review_reasons) or "agent flagged for review"
        banner = (
            "\n\n> **⚠ Flagged for mandatory human review by the reflection "
            f"agent.** Reason(s): {reasons}\n"
        )
        state.report.markdown = state.report.markdown.rstrip() + banner
    return state


def validate_node(
    state: PipelineState,
    *,
    consistency_validator,
    llm_output_validator,
    failure_policy: str = "strip",
    report_generator: BaseReportGenerator | None = None,
) -> PipelineState:
    if state.report is None:
        state.errors.append("Validation requested before report generation")
        return state
    state.consistency_passed = consistency_validator.validate(state).passed
    state.llm_output_passed = llm_output_validator.validate(state.report.markdown).passed
    return state


class LeukemiaPipeline:
    """Small convenience wrapper for direct full-flow execution."""

    def __init__(
        self,
        detector: BaseDetectionAgent,
        classifier: HybridClassifier,
        report_generator: BaseReportGenerator,
        reflection_agent: ReflectionAgent | None = None,
    ):
        self.detector = detector
        self.classifier = classifier
        self.report_generator = report_generator
        self.reflection_agent = reflection_agent

    def run(self, case_id: str, image_paths: list[str], instruction: str | None = None) -> PipelineState:
        state = PipelineState(case_id=case_id, image_paths=image_paths, text_input=instruction)
        state = detect_node(state, self.detector)
        state = aggregate_node(state)
        state = classify_node(state, self.classifier)
        state = reflect_node(
            state, agent=self.reflection_agent, classifier=self.classifier
        )
        state = report_node(state, self.report_generator)
        return state