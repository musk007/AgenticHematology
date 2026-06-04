"""
enrich_report_with_llm.py

Standalone post-processor that adds an LLM-generated "Morphologic
interpretation" paragraph to an already-generated template report. The
original report is not modified — the new section is inserted in-memory
and the enriched report is written to a separate output path.

Reads:
- The case JSON (the same payload your template generator consumes).
- The existing markdown report for that case.

Writes:
- An enriched markdown report with one extra section inserted between
  the "Cohort morphology" paragraph and the "Diagnostic flags" line.

LLM hallucination guard:
- After generation, every numeric token in the LLM output is checked
  against the union of numbers present in the case JSON and the source
  report. Novel numbers trigger one retry with feedback; a second
  failure causes the section to be dropped entirely.

Usage
-----
    export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY

    python enrich_report_with_llm.py \\
        --case-json cases.json \\
        --case-id 1 \\
        --report-in  template_reports/case_1_report.md \\
        --report-out enriched_reports/case_1_report.md \\
        --backend claude        # or openai

    # Batch mode — process every report in a directory:
    python enrich_report_with_llm.py \\
        --case-json cases.json \\
        --reports-in  template_reports/ \\
        --reports-out enriched_reports/ \\
        --backend claude
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Hardcoded API keys and models
# ---------------------------------------------------------------------------
# WARNING: do not commit this file to a public git repo with real keys.


<<<<<<< HEAD
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
=======
>>>>>>> 98009b8 (mended the API report generation code)


OPENAI_MODEL    = "gpt-5.5"


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a hematopathologist assistant. You will receive TWO inputs for one case:
1. STRUCTURED FINDINGS JSON — the full output of an automated cell-detection pipeline
2. TEMPLATE REPORT — a deterministically-generated markdown report derived from that JSON

Produce a SHORT complementary "Morphologic interpretation" section that adds clinical reasoning the rule-based template cannot express. The template prints only the dominant value per attribute; you have access to the full distribution and may reference subordinate values where they are clinically meaningful.

# What to produce

Output exactly one section titled "**Morphologic interpretation:**" containing 3 to 5 sentences of running prose. Nothing else — no headers, no bullets, no preamble, no closing remarks, no recommended workup, no restated impression, no QC commentary.

# What the section should do

1. If the observed morphology clearly supports a FAB subtype, state which subtype is favored and why.
2. If morphology is mixed or insufficient for a specific FAB assignment, explicitly state that no specific FAB subtype is favored.
3. If features span multiple FAB categories, describe the mixed pattern rather than forcing a single assignment.
4. Surface clinically relevant subordinate findings from the JSON that the template's dominant-only prose hides:
   - Size heterogeneity (a substantial minority of small or large cells alongside the dominant population)
   - Nuclear shape sub-categories (cleaved or folded nuclei, prominent irregular minority alongside a regular dominant)
   - Substantial minorities of prominent nucleoli, scanty cytoplasm, or basophilic cytoplasm that would shift sub-entity favouring
5. Flag borderline attribute dominances. A dominance_pct < 65% indicates that the cohort is not strongly one-sided and the dominant descriptor should be qualified accordingly.
6. Discuss differential considerations only when specific morphologic findings directly support or argue against them.
7. If morphology does not provide clear evidence for a differential consideration, do not discuss it.
5. If the cohort morphology is internally inconsistent with the impression, say so plainly.

# Hard constraints (violations invalidate the output)

- Numbers: do not introduce any numeric value not literally present in either input. You may quote percentages from `cell_percentages_clinical`, `blast_morphology`, or the report verbatim.
- Source of truth for cohort morphology: use ONLY the `report_ready.blast_morphology` block, which is computed over the blast cohort. The top-level `attributes` block is computed over all annotated objects (including artefacts) and must not be cited as cohort statistics, though you may reference its subordinate percentages when discussing the broader smear.
- Do not interpret `code_2`, `code_3`, or any `code_N` placeholder as a morphology value — these represent non-informative cells. Treat them as missing data and do not mention them.
- Do not use `metadata_filename_diagnosis` as a confirmed diagnosis — it is dataset training metadata. Reason from morphology only.
- Do not invent clinical data absent from the inputs: no age, sex, CBC indices, symptoms, history, immunophenotype, cytogenetics, or molecular results.
- Do not invent morphologic findings: no Auer rods, smudge cells, faggot cells, hand-mirror cells, granules, vacuoles, or features beyond what the JSON describes.
- Do not recommend any test, follow-up, treatment, or workup.
- Do not restate the impression, the differential table, the QC line, or the diagnostic flags.
- Do not hedge with empty qualifiers. Use direct clinical voice: "favours", "is consistent with", "argues against", "is borderline for".
- If the JSON lacks a `report_ready.blast_morphology` block or `n_cells_in_cohort` is zero, output exactly the string: SKIP
- Treat all morphology as cohort-level observations derived from automated image analysis.
- Do not express greater diagnostic certainty than the observed morphology supports.
- Avoid definitive subtype assignment when morphologic support is limited or mixed.

# Style

- Clinical, terse, declarative.
- Running prose. No numbered or bulleted lists.
- Reference attributes by morphologic name: "nuclear chromatin" not "nuclear_chromatio".
- Use "the cohort", "the blast population", or "the lymphoblast cohort" — not "the cells in this report".
"""


USER_TEMPLATE = """---JSON---
{json_blob}

---REPORT---
{report_md}
"""


# ---------------------------------------------------------------------------
# Numeric containment guard
# ---------------------------------------------------------------------------

NUMERIC_TOKEN_RE = re.compile(r"(?<![A-Za-z_])(\d+(?:\.\d+)?)")

DEFAULT_WHITELIST: set[str] = {
    "20",                    # WHO/ICC blast threshold
    "10",                    # accelerated phase CML threshold
    "5",                     # lymphocytosis threshold
    "2",                     # basophilia threshold
    "1", "3", "4", "6", "7", # FAB indices
    "2022",                  # WHO 5th ed.
}


def _flatten_numbers(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _flatten_numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _flatten_numbers(v, out)
    elif isinstance(obj, (int, float)):
        out.add(str(obj))
        if isinstance(obj, float):
            out.add(f"{obj:.1f}")
            out.add(f"{round(obj, 1)}")
    elif isinstance(obj, str):
        out.update(NUMERIC_TOKEN_RE.findall(obj))


def extract_allowed_numbers(case_json: dict, report_md: str) -> set[str]:
    allowed: set[str] = set(DEFAULT_WHITELIST)
    _flatten_numbers(case_json, allowed)
    allowed.update(NUMERIC_TOKEN_RE.findall(report_md))
    return allowed


def find_novel_numbers(text: str, allowed: set[str]) -> list[str]:
    novel: list[str] = []
    seen: set[str] = set()
    for tok in NUMERIC_TOKEN_RE.findall(text):
        if tok not in allowed and tok not in seen:
            novel.append(tok)
            seen.add(tok)
    return novel


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------

class BaseBackend(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        ...



class OpenAIBackend(BaseBackend):
    def __init__(self, model: str = OPENAI_MODEL, max_completion_tokens: int = 1000):
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise ImportError("pip install openai") from e
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = model
        self.max_tokens = max_completion_tokens

    def complete(self, system: str, user: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            max_completion_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()


def build_backend(name: str) -> BaseBackend:
    if name == "openai":
        return OpenAIBackend()
    raise ValueError(f"Unknown backend: {name!r}")


# ---------------------------------------------------------------------------
# Section generation with retry-on-hallucination
# ---------------------------------------------------------------------------

def generate_morphologic_interpretation(
    backend: BaseBackend,
    case_json: dict,
    report_md: str,
    max_retries: int = 1,
) -> tuple[str | None, list[str]]:
    """
    Returns (section_text, issues). section_text is None if the LLM
    decided to skip or all retries failed validation. `issues` lists any
    novel-number violations seen across attempts.
    """
    # Cheap up-front check: if there's no blast cohort, skip without calling.
    rr = case_json.get("report_ready", {})
    cohort_n = rr.get("qc", {}).get("n_cells_in_cohort", 0)
    if cohort_n == 0 or "blast_morphology" not in rr:
        return None, ["no blast cohort to interpret"]

    user_msg = USER_TEMPLATE.format(
        json_blob=json.dumps(case_json, indent=2),
        report_md=report_md,
    )
    allowed = extract_allowed_numbers(case_json, report_md)
    issues: list[str] = []

    for attempt in range(max_retries + 1):
        output = backend.complete(SYSTEM_PROMPT, user_msg)
        if output.strip().upper().startswith("SKIP"):
            return None, []

        novel = find_novel_numbers(output, allowed)
        if not novel:
            return output, []

        issues.append(
            f"attempt {attempt + 1}: novel numbers {novel}"
        )
        # Append retry feedback for the next attempt.
        user_msg = (
            USER_TEMPLATE.format(
                json_blob=json.dumps(case_json, indent=2),
                report_md=report_md,
            )
            + "\n\n---RETRY FEEDBACK---\n"
            f"Your previous output contained numeric value(s) not present in "
            f"the inputs: {', '.join(novel)}. Regenerate using ONLY numbers "
            f"that appear verbatim in the JSON or the report. Do not perform "
            f"any new calculation."
        )

    return None, issues


# ---------------------------------------------------------------------------
# Insertion — place the new section before "**Diagnostic flags:**"
# ---------------------------------------------------------------------------

def insert_section(report_md: str, section: str) -> str:
    """
    Insert `section` immediately before the "**Diagnostic flags:**" line.
    Falls back to inserting before "**Impression:**" if flags are absent,
    and finally to appending at the end.
    """
    section = section.rstrip() + "\n"
    for anchor in ("**Diagnostic flags:**", "**Impression:**"):
        idx = report_md.find(anchor)
        if idx != -1:
            # Find the start of the line containing the anchor.
            line_start = report_md.rfind("\n", 0, idx) + 1
            return (
                report_md[:line_start]
                + section
                + "\n"
                + report_md[line_start:]
            )
    # Append if neither anchor is present.
    return report_md.rstrip() + "\n\n" + section


# ---------------------------------------------------------------------------
# Case-id resolution from filename
# ---------------------------------------------------------------------------

CASE_ID_RE = re.compile(r"case_([^_]+(?:_[^_]+)*?)_report")


def case_id_from_filename(path: Path) -> str | None:
    m = CASE_ID_RE.search(path.stem)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _process_one(
    case_id: str,
    case_json: dict,
    report_in: Path,
    report_out: Path,
    backend: BaseBackend,
) -> bool:
    report_md = report_in.read_text()
    section, issues = generate_morphologic_interpretation(
        backend, case_json, report_md
    )

    if section is None:
        msg = "no LLM section added"
        if issues:
            msg += f" (issues: {issues})"
        print(f"  [{case_id}] {msg}")
        # Still write the report unchanged so the output dir mirrors the input.
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(report_md)
        return False

    enriched = insert_section(report_md, section)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(enriched)
    print(f"  [{case_id}] enriched -> {report_out}")
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--case-json", required=True, help="Path to the cases JSON.")
    p.add_argument("--backend", choices=["openai"], default="openai")
    p.add_argument("--case-id", help="Single case id (with --report-in/--report-out).")
    p.add_argument("--report-in", help="Single input report path.")
    p.add_argument("--report-out", help="Single output report path.")
    p.add_argument("--reports-in", help="Directory of input *.md reports.")
    p.add_argument("--reports-out", help="Directory for enriched reports.")
    args = p.parse_args()

    cases = json.loads(Path(args.case_json).read_text())
    backend = build_backend(args.backend)

    # Single-case mode.
    if args.case_id and args.report_in and args.report_out:
        if args.case_id not in cases:
            print(f"ERROR: case {args.case_id!r} not in JSON", file=sys.stderr)
            return 2
        _process_one(
            args.case_id,
            cases[args.case_id],
            Path(args.report_in),
            Path(args.report_out),
            backend,
        )
        return 0

    # Batch mode.
    if args.reports_in and args.reports_out:
        n_done = n_skip = 0
        for path in sorted(Path(args.reports_in).glob("*.md")):
            cid = case_id_from_filename(path)
            if cid is None:
                print(f"  [skip] cannot parse case id from {path.name}")
                n_skip += 1
                continue
            if cid not in cases:
                print(f"  [skip] case {cid!r} not in JSON")
                n_skip += 1
                continue
            out_path = Path(args.reports_out) / path.name
            ok = _process_one(cid, cases[cid], path, out_path, backend)
            n_done += int(ok)
        print(f"\nDone. Enriched: {n_done}; skipped/unchanged: {n_skip}")
        return 0

    print(
        "ERROR: provide either --case-id + --report-in + --report-out (single), "
        "or --reports-in + --reports-out (batch).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
