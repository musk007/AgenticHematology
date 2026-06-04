"""
report_consistency.py
=====================
Validates that a deterministically-generated markdown report is internally
consistent with the source JSON it was produced from.

This is a *template drift* / *aggregator drift* guard. It catches:
- A schema change in the JSON that the markdown renderer didn't track.
- A rounding-policy mismatch between aggregator and renderer.
- A regex bug in the renderer that swaps two numbers.
- A cell-type label change between detector and reporter.

It does NOT catch hallucinations introduced by an LLM — for that, see
`llm_output.py`.

Refactored from the original standalone script: paths are no longer module
constants, `parse_report` collects all issues instead of failing on the
first, and the cell-type map covers the full 14-class LLD schema.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Markdown percentages are rendered to one decimal place; rounding can
# introduce up to ~0.05 of drift per operand. We allow a touch more for safety.
DEFAULT_PCT_TOLERANCE = 0.11


# Maps the markdown display label (plural, capitalized) to the JSON key
# (singular, lowercase). Covers the full 14-class LLD schema, including
# previously missing entries: Myeloblasts, Atypical lymphocytes, Promonocytes,
# Monoblasts, Abnormal promyelocytes.
CELL_TYPE_MAP: dict[str, str] = {
    "Lymphoblasts": "lymphoblast",
    "Myeloblasts": "myeloblast",
    "Monoblasts": "monoblast",
    "Promonocytes": "promonocyte",
    "Abnormal promyelocytes": "abnormal promyelocyte",
    "Atypical lymphocytes": "atypical lymphocyte",
    "Lymphocytes": "lymphocyte",
    "Monocytes": "monocyte",
    "Neutrophils": "neutrophil",
    "Eosinophils": "eosinophil",
    "Basophils": "basophil",
    "Promyelocytes": "promyelocyte",
    "Myelocytes": "myelocyte",
    "Metamyelocytes": "metamyelocyte",
    "Band neutrophils": "band_neutrophil",
}


DIAGNOSIS_ALIASES: dict[str, list[str]] = {
    "APML": ["APML", "APL", "Acute Promyelocytic Leukemia"],
    "APL":  ["APL", "APML", "Acute Promyelocytic Leukemia"],
    "AML":  ["AML", "Acute Myeloid Leukemia"],
    "ALL":  ["ALL", "Acute Lymphoblastic Leukemia"],
    "CML":  ["CML", "Chronic Myeloid Leukemia"],
    "CLL":  ["CLL", "Chronic Lymphocytic Leukemia", "Small Lymphocytic Lymphoma"],
}


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ConsistencyResult:
    """Outcome of a single report-vs-JSON validation."""
    case_id: str | None
    passed: bool
    issues: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    @property
    def n_issues(self) -> int:
        return len(self.issues) + len(self.parse_errors)


# ---------------------------------------------------------------------------
# Parsing — same regex contract as the original, but never raises.
# ---------------------------------------------------------------------------

def parse_report(report_text: str) -> tuple[dict[str, Any], list[str]]:
    """
    Parse a markdown report back into a structured dict.

    Unlike the original script, this never raises: any parsing failure is
    appended to the returned `errors` list and the function continues with
    whatever it could extract. This lets compare_case see ALL issues in one
    pass rather than aborting on the first.
    """
    parsed: dict[str, Any] = {}
    errors: list[str] = []

    # Case ID
    case_match = re.search(r"#\s+Hematology Report\s+—\s+Case\s+(\S+)", report_text)
    if case_match:
        parsed["case_id"] = case_match.group(1)
    else:
        parsed["case_id"] = None
        errors.append("parse: could not locate case ID in report title")

    # Specimen line
    specimen_re = re.search(
        r"\*\*Specimen:\*\*\s*Peripheral blood smear,\s*(\d+)\s*fields of view,\s*"
        r"(\d+)\s*of\s*(\d+)\s*annotated objects classified as informative WBCs\s*"
        r"\((\d+)\s*artefacts excluded\)\.",
        report_text,
    )
    if specimen_re:
        parsed["n_images"] = int(specimen_re.group(1))
        parsed["n_identified_wbc"] = int(specimen_re.group(2))
        parsed["n_annotated"] = int(specimen_re.group(3))
        parsed["n_artifacts"] = int(specimen_re.group(4))
    else:
        errors.append("parse: could not locate specimen line")

    # Differential table
    parsed["differential"] = {}
    for label, pct in re.findall(r"\|\s*([A-Za-z\s\-]+?)\s*\|\s*([\d.]+)%\s*\|", report_text):
        clean = label.strip()
        if clean == "Cell type":
            continue
        key = CELL_TYPE_MAP.get(clean)
        if key:
            parsed["differential"][key] = float(pct)
        else:
            errors.append(f"parse: unrecognised cell type in differential: {clean!r}")

    # Impression
    impression_match = re.search(r"\*\*Impression:\*\*\s*(.+?)\.", report_text)
    parsed["impression"] = (
        impression_match.group(1).strip() if impression_match else None
    )

    # Blast pool percentage — try the lymphoblast wording, then a generic fallback.
    blast_match = re.search(
        r"(?:Lymphoblasts|Myeloblasts|Monoblasts|Abnormal promyelocytes|Blasts)\s+"
        r"comprise\s*([\d.]+)%\s*of WBCs",
        report_text,
    )
    parsed["blast_pool_percentage_of_wbc"] = (
        float(blast_match.group(1)) if blast_match else None
    )

    # QC line
    qc_re = re.search(
        r"\*\*QC:\*\*\s*(\d+)\s*FOVs;\s*(\d+)/(\d+)\s*cells classifiable\s*"
        r"\(([\d.]+)%\s*artefact\);\s*cohort cell count\s*=\s*(\d+);",
        report_text,
    )
    if qc_re:
        parsed["qc_n_fields_of_view"] = int(qc_re.group(1))
        parsed["qc_n_identified_wbc"] = int(qc_re.group(2))
        parsed["qc_n_annotated"] = int(qc_re.group(3))
        parsed["qc_artefact_pct"] = float(qc_re.group(4))
        parsed["qc_n_cells_in_cohort"] = int(qc_re.group(5))
    else:
        errors.append("parse: could not locate QC line")

    return parsed, errors


# ---------------------------------------------------------------------------
# Comparison — same logic as the original, returns a list of human-readable
# issues. Pure function over parsed report + expected JSON.
# ---------------------------------------------------------------------------

def compare_case(
    parsed_report: dict[str, Any],
    expected_case: dict[str, Any],
    pct_tolerance: float = DEFAULT_PCT_TOLERANCE,
) -> list[str]:
    """Return a list of human-readable mismatches; empty list means OK."""
    issues: list[str] = []
    rr = expected_case["report_ready"]

    # Scalar integers
    expected_scalars = {
        "n_images": expected_case["n_images"],
        "n_identified_wbc": expected_case["n_cells_identified_wbc"],
        "n_annotated": expected_case["n_cells_total"],
        "n_artifacts": rr["qc"]["n_artifacts"],
        "qc_n_fields_of_view": rr["qc"]["n_fields_of_view"],
        "qc_n_identified_wbc": rr["qc"]["n_identified_wbc"],
        "qc_n_annotated": rr["qc"]["n_annotated_cells"],
        "qc_n_cells_in_cohort": rr["qc"]["n_cells_in_cohort"],
    }
    for key, expected in expected_scalars.items():
        got = parsed_report.get(key)
        if got is None:
            continue  # parse error was already recorded
        if got != expected:
            issues.append(f"{key}: report={got}, json={expected}")

    # Artefact percentage (rendered)
    if "qc_artefact_pct" in parsed_report and rr["qc"]["n_annotated_cells"]:
        expected_artefact_pct = round(
            (rr["qc"]["n_artifacts"] / rr["qc"]["n_annotated_cells"]) * 100, 1
        )
        if abs(parsed_report["qc_artefact_pct"] - expected_artefact_pct) > pct_tolerance:
            issues.append(
                f"qc_artefact_pct: report={parsed_report['qc_artefact_pct']}, "
                f"json={expected_artefact_pct}"
            )

    # Blast pool percentage
    if parsed_report.get("blast_pool_percentage_of_wbc") is not None:
        expected_blast_pct = round(rr["blast_pool_percentage_of_wbc"], 1)
        if abs(parsed_report["blast_pool_percentage_of_wbc"] - expected_blast_pct) > pct_tolerance:
            issues.append(
                "blast_pool_percentage_of_wbc: "
                f"report={parsed_report['blast_pool_percentage_of_wbc']}, "
                f"json={expected_blast_pct}"
            )

    # Impression vs metadata diagnosis (with alias support)
    diagnosis_json = expected_case.get("metadata_filename_diagnosis")
    impression_text = parsed_report.get("impression") or ""
    if diagnosis_json and impression_text:
        aliases = DIAGNOSIS_ALIASES.get(diagnosis_json, [diagnosis_json])
        impression_lower = impression_text.lower()
        if not any(alias.lower() in impression_lower for alias in aliases):
            if "unclassified" in impression_lower:
                issues.append(
                    "impression diagnosis mismatch (likely threshold fallback): "
                    f"report='{impression_text}', json='{diagnosis_json}'"
                )
            else:
                issues.append(
                    f"impression diagnosis mismatch: "
                    f"report='{impression_text}', json='{diagnosis_json}'"
                )

    # Differential percentages
    clinical_raw = expected_case.get("cell_percentages_clinical", {})
    # Case-insensitive lookup: handle both lowercase ("lymphoblast") and
    # canonical LLD case ("Lymphoblast") sources.
    clinical = {k.lower(): v for k, v in clinical_raw.items()}
    for cell_type, report_pct in parsed_report.get("differential", {}).items():
        key = cell_type.lower()
        if key not in clinical:
            issues.append(
                f"differential '{cell_type}' missing in json clinical percentages"
            )
            continue
        expected_pct = round(float(clinical[key]), 1)
        if abs(report_pct - expected_pct) > pct_tolerance:
            issues.append(
                f"differential {cell_type}: report={report_pct}, json={expected_pct}"
            )

    return issues


# ---------------------------------------------------------------------------
# Class wrapper — what the orchestrator imports.
# ---------------------------------------------------------------------------

class ReportConsistencyValidator:
    """
    Validates a rendered markdown report against its source JSON.

    Usage:
        validator = ReportConsistencyValidator(pct_tolerance=0.11)
        result = validator.validate(report_md, source_json_dict)
        if not result.passed:
            for issue in result.issues + result.parse_errors:
                print(issue)
    """

    def __init__(self, pct_tolerance: float = DEFAULT_PCT_TOLERANCE):
        self.pct_tolerance = pct_tolerance

    def validate(
        self, report_markdown: str, source_json: dict[str, Any]
    ) -> ConsistencyResult:
        parsed, parse_errors = parse_report(report_markdown)
        issues = compare_case(parsed, source_json, self.pct_tolerance)
        return ConsistencyResult(
            case_id=parsed.get("case_id"),
            passed=(not issues and not parse_errors),
            issues=issues,
            parse_errors=parse_errors,
        )

    def validate_batch(
        self,
        reports_dir: str | Path,
        stats_json_path: str | Path,
    ) -> list[ConsistencyResult]:
        """Reproduces the original script's batch behaviour."""
        reports_dir = Path(reports_dir)
        stats_json_path = Path(stats_json_path)

        stats = json.loads(stats_json_path.read_text())
        report_paths = sorted(reports_dir.glob("*.md"))

        results: list[ConsistencyResult] = []
        for path in report_paths:
            text = path.read_text()
            parsed, parse_errors = parse_report(text)
            case_id = parsed.get("case_id")
            if case_id is None:
                results.append(ConsistencyResult(
                    case_id=None, passed=False,
                    parse_errors=parse_errors + [f"file: {path.name}"],
                ))
                continue
            if case_id not in stats:
                results.append(ConsistencyResult(
                    case_id=case_id, passed=False,
                    issues=[f"case '{case_id}' not present in stats JSON"],
                    parse_errors=parse_errors,
                ))
                continue
            issues = compare_case(parsed, stats[case_id], self.pct_tolerance)
            results.append(ConsistencyResult(
                case_id=case_id,
                passed=(not issues and not parse_errors),
                issues=issues,
                parse_errors=parse_errors,
            ))
        return results


# ---------------------------------------------------------------------------
# CLI for batch use — same behaviour as the original script.
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse
    p = argparse.ArgumentParser(
        description="Validate rendered markdown reports against the source JSON."
    )
    p.add_argument("reports_dir", help="Directory containing *.md reports.")
    p.add_argument("stats_json", help="Path to the cases stats JSON.")
    p.add_argument("--tolerance", type=float, default=DEFAULT_PCT_TOLERANCE)
    args = p.parse_args()

    validator = ReportConsistencyValidator(pct_tolerance=args.tolerance)
    results = validator.validate_batch(args.reports_dir, args.stats_json)

    total_issues = 0
    for r in results:
        tag = "PASS" if r.passed else "FAIL"
        print(f"[{tag}] case {r.case_id}")
        for issue in r.parse_errors + r.issues:
            print(f"  - {issue}")
        total_issues += r.n_issues
    print(f"\nValidation complete. Total mismatches: {total_issues}")


if __name__ == "__main__":
    _cli()
