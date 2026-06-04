"""
llm_output.py
=============
Hallucination guard for LLM-generated complementary content (e.g. the
morphologic interpretation paragraph).

The core idea: every number that appears in the LLM's output must already
exist in the input the LLM was given. If it doesn't, the LLM either
fabricated it or recomputed something — both unsafe in a pathology report.

This is a fast, dependency-free guard. It is *necessary but not sufficient*:
it catches hallucinated numbers, not hallucinated qualitative findings
("Auer rods present"). Pair with a forbidden-phrase blocklist for the
latter (e.g. "Auer rod", "smudge cell") if those are not in the inputs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


# Matches integers, decimals, and percentages. Captures the bare numeric
# token (without trailing % or units) so we can do set membership.
NUMERIC_TOKEN_RE = re.compile(r"(?<![A-Za-z_])(\d+(?:\.\d+)?)")


# Numbers that are universally allowed even if not in the source — these are
# clinical thresholds and reference points clinicians cite from memory.
# Keep this list short and explicit.
DEFAULT_WHITELIST: set[str] = {
    "20",      # WHO/ICC blast threshold for acute leukemia
    "10",      # ICC accelerated-phase CML blast threshold
    "5",       # lymphocytosis / atypical lymphocyte threshold
    "2",       # basophilia threshold (%)
    "1", "2", "3", "4",  # FAB subtype indices (M1-M7, L1-L3)
    "5", "6", "7",
    "2022",    # WHO 5th edition / ICC publication year
}


@dataclass
class NumericContainmentResult:
    """Outcome of a single numeric-containment check."""
    passed: bool
    novel_numbers: list[str] = field(default_factory=list)
    novel_numbers_in_context: list[str] = field(default_factory=list)

    @property
    def reason(self) -> str:
        if self.passed:
            return "ok"
        return (
            f"LLM output contained {len(self.novel_numbers)} numeric token(s) "
            f"not present in the source inputs: "
            f"{', '.join(self.novel_numbers[:5])}"
            + (" ..." if len(self.novel_numbers) > 5 else "")
        )


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

def extract_numeric_tokens(text: str) -> list[str]:
    """Return every numeric token found in `text` (with duplicates)."""
    return NUMERIC_TOKEN_RE.findall(text)


def _flatten_json_numbers(obj: Any, out: set[str]) -> None:
    """Recursively collect every number found in a JSON-like object."""
    if isinstance(obj, dict):
        for v in obj.values():
            _flatten_json_numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _flatten_json_numbers(v, out)
    elif isinstance(obj, (int, float)):
        out.add(str(obj))
        # Also add the rounded-to-one-decimal-place form, since the report
        # renders percentages that way. e.g. 92.857 → "92.9".
        if isinstance(obj, float):
            out.add(f"{obj:.1f}")
            out.add(f"{round(obj, 1)}")
    elif isinstance(obj, str):
        # Pull any numeric tokens embedded in string values too.
        out.update(extract_numeric_tokens(obj))


def collect_allowed_numbers(
    *sources: str | dict | Any,
    extra_whitelist: set[str] | None = None,
) -> set[str]:
    """
    Build the union of every numeric token allowed in LLM output, from any
    mix of:
    - JSON-like dicts (recursively flattened)
    - markdown / plain text strings (regex-scanned)
    - the static clinical whitelist
    - an optional case-specific extra whitelist
    """
    allowed: set[str] = set(DEFAULT_WHITELIST)
    if extra_whitelist:
        allowed |= extra_whitelist

    for src in sources:
        if isinstance(src, str):
            allowed.update(extract_numeric_tokens(src))
        elif isinstance(src, (dict, list)):
            _flatten_json_numbers(src, allowed)
        # Silently ignore None / unsupported types.

    return allowed


# ---------------------------------------------------------------------------
# The validator
# ---------------------------------------------------------------------------

class LLMOutputValidator:
    """
    Checks that every numeric token in LLM output is also in the inputs.

    Usage:
        v = LLMOutputValidator()
        result = v.validate(
            llm_output_text,
            source_json=case_json,
            source_text=template_report_md,
        )
        if not result.passed:
            print(result.reason)
            print(result.novel_numbers_in_context)
    """

    def __init__(
        self,
        whitelist: set[str] | None = None,
        context_window: int = 25,
    ):
        """
        :param whitelist: additional numeric tokens to always allow.
        :param context_window: characters of context to capture around each
            novel-number occurrence (helps debugging the LLM's mistake).
        """
        self.extra_whitelist = whitelist
        self.context_window = context_window

    def validate(
        self,
        llm_output: str,
        *,
        source_json: dict | None = None,
        source_text: str | None = None,
        extra_whitelist: set[str] | None = None,
    ) -> NumericContainmentResult:
        sources: list[Any] = []
        if source_json is not None:
            sources.append(source_json)
        if source_text is not None:
            sources.append(source_text)

        allowed = collect_allowed_numbers(
            *sources,
            extra_whitelist=(extra_whitelist or self.extra_whitelist),
        )

        output_tokens = extract_numeric_tokens(llm_output)
        novel = [t for t in output_tokens if t not in allowed]

        # De-duplicate while preserving order of first occurrence.
        seen: set[str] = set()
        novel_unique: list[str] = []
        for t in novel:
            if t not in seen:
                seen.add(t)
                novel_unique.append(t)

        # Capture context for each novel number for easier debugging.
        contexts: list[str] = []
        for token in novel_unique:
            for m in re.finditer(rf"(?<![A-Za-z_]){re.escape(token)}", llm_output):
                start = max(0, m.start() - self.context_window)
                end = min(len(llm_output), m.end() + self.context_window)
                snippet = llm_output[start:end].replace("\n", " ").strip()
                contexts.append(f"{token!r}: '...{snippet}...'")
                break  # one example per token is enough

        return NumericContainmentResult(
            passed=(len(novel_unique) == 0),
            novel_numbers=novel_unique,
            novel_numbers_in_context=contexts,
        )

    def build_retry_feedback(self, result: NumericContainmentResult) -> str:
        """
        Build a short instruction the orchestrator can append to the
        original prompt for a single retry. Stays under ~80 tokens.
        """
        if result.passed:
            return ""
        return (
            "Your previous output contained numeric value(s) not present in "
            "the inputs: "
            + ", ".join(result.novel_numbers)
            + ". Regenerate the section using ONLY numbers that appear "
            "verbatim in the JSON or the report. Do not perform any new "
            "calculation."
        )
