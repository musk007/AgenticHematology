"""Shared prompts: detection summary -> chat messages (SFT / inference)."""
from __future__ import annotations

import json
from typing import Any

DEFAULT_SYSTEM_PROMPT = (
    "You are a hematopathology assistant. Write a structured peripheral blood smear "
    "report in Markdown from the detection summary JSON only."
)


def summary_to_user_content(summary: dict[str, Any]) -> str:
    return (
        "Write the hematology report for this case.\n\n"
        f"<detection_summary>\n{json.dumps(summary, indent=2)}\n</detection_summary>"
    )


def build_messages(
    summary: dict[str, Any],
    *,
    system_prompt: str | None = None,
    assistant_content: str | None = None,
) -> list[dict[str, str]]:
    """SFT triple or inference pair (no assistant if assistant_content is None)."""
    msgs: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": summary_to_user_content(summary)},
    ]
    if assistant_content is not None:
        msgs.append({"role": "assistant", "content": assistant_content})
    return msgs


def messages_for_inference(summary: dict[str, Any], system_prompt: str | None = None) -> list[dict[str, str]]:
    """Chat layout aligned with verl SFT/GRPO (system merged into first user)."""
    from .verl_parquet import normalize_messages_for_verl

    return normalize_messages_for_verl(build_messages(summary, system_prompt=system_prompt))
