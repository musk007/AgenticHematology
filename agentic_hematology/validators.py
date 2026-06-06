"""Lightweight validation for generated reports."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationResult:
    passed: bool
    message: str = ""


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
