"""Lightweight validation for generated reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .report_validation import (
    classification_to_dict,
    compare_report_to_findings_json,
    evaluate_numerical_hallucination,
    findings_to_det_agg,
)


@dataclass
class ValidationResult:
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class ReportConsistencyValidator:
    def validate(self, state) -> ValidationResult:
        if state.report is None:
            return ValidationResult(False, "missing report")
        if state.classification and state.classification.predicted_class not in state.report.markdown:
            return ValidationResult(
                False,
                "predicted class is not mentioned in report markdown",
            )
        return ValidationResult(True, "ok")


class LLMOutputValidator:
    _BANNED = ("as an ai language model", "i cannot diagnose")

    def validate(self, markdown: str) -> ValidationResult:
        text = markdown.strip()
        if not text:
            return ValidationResult(False, "empty report")
        lowered = text.lower()
        if any(term in lowered for term in self._BANNED):
            return ValidationResult(False, "contains generic refusal text")
        return ValidationResult(True, "ok")


class TemplateJsonConsistencyValidator:
    """Verify report numbers match findings.report_ready / aggregation JSON."""

    def validate(self, state) -> ValidationResult:
        if state.report is None:
            return ValidationResult(False, "missing report")
        if state.findings is None:
            return ValidationResult(False, "missing findings for JSON cross-check")

        result = compare_report_to_findings_json(
            state.report.markdown,
            state.findings,
        )
        if result["passed"]:
            return ValidationResult(True, "ok", details=result)
        msg = "; ".join(result["mismatches"][:4])
        if len(result["mismatches"]) > 4:
            msg += f" (+{len(result['mismatches']) - 4} more)"
        return ValidationResult(False, msg, details=result)


class NumericalHallucinationValidator:
    """Screen numeric claims in the report body against pipeline JSON evidence."""

    def validate(self, state) -> ValidationResult:
        if state.report is None:
            return ValidationResult(False, "missing report")
        if state.findings is None:
            return ValidationResult(False, "missing findings for evidence pool")

        det_agg = findings_to_det_agg(state.findings)
        clf = classification_to_dict(state.classification)
        hall = evaluate_numerical_hallucination(
            state.report.markdown,
            det_agg,
            clf,
        )
        if hall["n_untraceable"] == 0:
            return ValidationResult(True, "ok", details=hall)

        examples = hall.get("untraceable_examples") or []
        msg = (
            f"{hall['n_untraceable']}/{hall['n_claims']} numeric claims untraceable "
            f"(rate={hall['hallucination_rate']})"
        )
        if examples:
            msg += f"; e.g. {examples[0]}"
        return ValidationResult(False, msg, details=hall)
