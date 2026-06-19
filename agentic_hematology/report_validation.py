"""Shared report validation helpers (pipeline + batch evaluation)."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
WBC_UNIFIED = ROOT / "wbc_unified"

PCT_TOLERANCE = 1.5
COUNT_TOLERANCE = 2
BLAST_PCT_TOLERANCE = 2.0
WHITELIST_PCT = {20.0}


def _eval_report_helpers():
    if str(WBC_UNIFIED) not in sys.path:
        sys.path.insert(0, str(WBC_UNIFIED))
    from report.src.eval_report import (  # noqa: WPS433
        _normalize_name,
        _parse_differential_table,
        extract_report_markdown,
    )

    return _normalize_name, _parse_differential_table, extract_report_markdown


def extract_blast_pct_from_report(md: str) -> float | None:
    m = re.search(r"blast-equivalent burden is (\d+\.?\d*)\s*%", md, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"blast_pct[\"']?\s*[:=]\s*(\d+\.?\d*)", md, re.I)
    return float(m.group(1)) if m else None


def extract_percentages(text: str) -> list[float]:
    return [float(m.group(1)) for m in re.finditer(r"(\d+\.?\d*)\s*%", text)]


def extract_integer_claims(md: str) -> list[int]:
    body = md.split("## Quantitative Cell Summary")[0]
    claims: list[int] = []
    for pattern in (
        r"(\d+)\s+fields of view",
        r"(\d+)\s+of\s+(\d+)\s+detected objects",
        r"(\d+)\s+artefacts excluded",
        r"(\d+)/(\d+)\s+cells classifiable",
        r"\(n\s*=\s*(\d+)",
    ):
        for match in re.finditer(pattern, body, re.I):
            claims.extend(int(g) for g in match.groups() if g is not None)
    return claims


def report_body_before_appendix(md: str) -> str:
    for marker in ("## Quantitative Cell Summary", "## Agentic Diagnosis"):
        if marker in md:
            return md.split(marker)[0]
    return md


def findings_to_det_agg(findings) -> dict[str, Any]:
    rr = findings.report_ready or {}
    qc = rr.get("qc") or {}
    return {
        "blast_pct": float(rr.get("blast_pct", 0.0)),
        "pct_class_none": float(qc.get("pct_class_none", 0.0)),
        "mean_det_conf": float(qc.get("mean_det_conf", 0.0)),
        "cell_percentages_clinical": dict(findings.cell_percentages_clinical or {}),
        "n_cells_total": int(rr.get("n_cells_total", findings.n_cells_total)),
        "n_cells_informative": int(
            rr.get("n_cells_informative", findings.n_cells_identified_wbc)
        ),
        "n_cells_artifact": int(rr.get("n_cells_artifact", 0)),
        "n_images": int(rr.get("n_images", findings.n_images)),
        "morphology_cohort": dict(rr.get("morphology_cohort") or findings.attributes or {}),
    }


def classification_to_dict(classification) -> dict[str, Any] | None:
    if classification is None:
        return None
    return {
        "predicted_class": classification.predicted_class,
        "confidence": float(classification.confidence),
    }


def build_pipeline_json_evidence(
    det_agg: dict[str, Any],
    clf: dict | None,
    report_md: str,
) -> tuple[set[float], set[int]]:
    pct_pool: set[float] = set(WHITELIST_PCT)
    int_pool: set[int] = set()

    pct_pool.add(float(det_agg.get("blast_pct", 0.0)))
    pct_pool.add(float(det_agg.get("pct_class_none", 0.0)))
    pct_pool.add(round(float(det_agg.get("mean_det_conf", 0.0)) * 100.0, 2))
    pct_pool.add(round(float(det_agg.get("mean_det_conf", 0.0)) * 100.0, 1))
    for value in (det_agg.get("cell_percentages_clinical") or {}).values():
        pct_pool.add(float(value))
    for cls_stats in (det_agg.get("morphology_cohort") or {}).values():
        for rate in (cls_stats.get("attr_pos_rate") or {}).values():
            pct_pool.add(round(float(rate) * 100.0, 1))
            pct_pool.add(round(float(rate) * 100.0, 2))

    int_pool.update(
        {
            int(det_agg.get("n_cells_total", 0)),
            int(det_agg.get("n_cells_informative", 0)),
            int(det_agg.get("n_cells_artifact", 0)),
            int(det_agg.get("n_images", 0)),
        }
    )
    if clf:
        int_pool.add(int(round(float(clf.get("confidence", 0.0)) * 100)))

    if report_md:
        quant = (
            report_md.split("## Quantitative Cell Summary")[-1]
            if "## Quantitative Cell Summary" in report_md
            else ""
        )
        for value in extract_percentages(quant):
            pct_pool.add(value)
        for value in extract_integer_claims(report_md):
            int_pool.add(value)

    return pct_pool, int_pool


def _is_traceable(value: float, pool: set[float], *, is_pct: bool) -> bool:
    tol = PCT_TOLERANCE if is_pct else float(COUNT_TOLERANCE)
    return any(abs(value - candidate) <= tol for candidate in pool)


def evaluate_numerical_hallucination(
    generated_md: str,
    det_agg: dict[str, Any],
    clf: dict | None,
    *,
    approved_md: str | None = None,
) -> dict[str, Any]:
    body = report_body_before_appendix(generated_md)
    pct_claims = [v for v in extract_percentages(body) if v not in WHITELIST_PCT]
    int_claims = extract_integer_claims(body)

    json_pct, json_int = build_pipeline_json_evidence(det_agg, clf, generated_md)
    approved_pct: set[float] = set()
    approved_int: set[int] = set()
    if approved_md:
        approved_body = report_body_before_appendix(approved_md)
        approved_pct = set(WHITELIST_PCT) | set(extract_percentages(approved_body))
        approved_int = set(extract_integer_claims(approved_body))

    untraceable: list[dict[str, Any]] = []
    for value in pct_claims:
        ok = _is_traceable(value, json_pct, is_pct=True) or _is_traceable(
            value, approved_pct, is_pct=True
        )
        if not ok:
            untraceable.append({"kind": "percent", "value": value})
    for value in int_claims:
        ok = _is_traceable(float(value), {float(v) for v in json_int}, is_pct=False) or _is_traceable(
            float(value), {float(v) for v in approved_int}, is_pct=False
        )
        if not ok:
            untraceable.append({"kind": "count", "value": value})

    total = len(pct_claims) + len(int_claims)
    rate = round(len(untraceable) / total, 4) if total else 0.0
    return {
        "n_claims": total,
        "n_untraceable": len(untraceable),
        "hallucination_rate": rate,
        "untraceable_examples": untraceable[:8],
    }


def _display_class(name: str, class_display: dict[str, str]) -> str:
    return class_display.get(name, name + "s" if not name.endswith("s") else name)


def compare_report_to_findings_json(
    markdown: str,
    findings,
    *,
    class_display: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Check numeric claims in the report body against findings.report_ready."""
    class_display = class_display or {}
    rr = findings.report_ready or {}
    body = report_body_before_appendix(markdown)
    _normalize_name, _parse_differential_table, extract_report_markdown = _eval_report_helpers()

    mismatches: list[str] = []
    parsed_diff = _parse_differential_table(extract_report_markdown(body))
    expected_diff = dict(findings.cell_percentages_clinical or {})

    for cls, expected_pct in expected_diff.items():
        display = _display_class(cls, class_display)
        matched_val: float | None = None
        for name, val in parsed_diff.items():
            if _normalize_name(name) in (
                _normalize_name(display),
                _normalize_name(cls),
            ):
                matched_val = val
                break
        if matched_val is None:
            mismatches.append(f"missing differential row for {cls}")
        elif abs(matched_val - float(expected_pct)) > PCT_TOLERANCE:
            mismatches.append(
                f"{cls}: report {matched_val}% vs JSON {expected_pct}% "
                f"(tol {PCT_TOLERANCE} pp)"
            )

    report_blast = extract_blast_pct_from_report(body)
    expected_blast = float(rr.get("blast_pct", 0.0))
    if report_blast is not None and abs(report_blast - expected_blast) > BLAST_PCT_TOLERANCE:
        mismatches.append(
            f"blast_pct: report {report_blast}% vs JSON {expected_blast}% "
            f"(tol {BLAST_PCT_TOLERANCE} pp)"
        )

    expected_counts = {
        "fields of view": int(rr.get("n_images", findings.n_images)),
        "informative WBCs": int(rr.get("n_cells_informative", findings.n_cells_identified_wbc)),
        "detected objects total": int(rr.get("n_cells_total", findings.n_cells_total)),
        "artefacts excluded": int(rr.get("n_cells_artifact", 0)),
    }
    int_claims = extract_integer_claims(body)
    for label, expected in expected_counts.items():
        if expected == 0:
            continue
        if not any(abs(claim - expected) <= COUNT_TOLERANCE for claim in int_claims):
            mismatches.append(
                f"{label}: expected {expected} in report narrative (±{COUNT_TOLERANCE})"
            )

    return {
        "passed": not mismatches,
        "mismatches": mismatches,
        "parsed_differential": parsed_diff,
        "expected_differential": expected_diff,
    }
