"""Rule-based hematology report from patient summary (no LLM weights required)."""
from __future__ import annotations

from typing import Any


def _display_class(name: str, class_display: dict[str, str]) -> str:
    return class_display.get(name, name + "s" if not name.endswith("s") else name)


def _top_morphology_line(summary: dict[str, Any], min_cells: int = 5) -> str | None:
    cohort = summary.get("morphology_cohort", {})
    if not cohort:
        return None
    ranked = sorted(cohort.items(), key=lambda x: -x[1]["n"])
    for cls, stats in ranked:
        if stats["n"] < min_cells:
            continue
        rates = stats.get("attr_pos_rate", {})
        parts = []
        for attr, rate in sorted(rates.items(), key=lambda x: -x[1])[:4]:
            if rate >= 0.5:
                parts.append(f"{attr.replace('_', ' ').lower()} ({rate*100:.1f}%)")
        if parts:
            return (
                f"**Cohort morphology (n = {stats['n']} {_display_class(cls, {})}):** "
                + "; ".join(parts[:6]) + "."
            )
    return None


def generate_template_report(summary: dict[str, Any], cfg: dict[str, Any]) -> str:
    pid = summary["patient_id"]
    n_fov = summary["n_images"]
    n_inf = summary["n_cells_informative"]
    n_art = summary["n_cells_artifact"]
    n_all = summary["n_cells_total"]
    disease = summary.get("disease_label_file", "UNKNOWN")
    class_display = cfg.get("class_display", {})
    disease_impression = cfg.get("disease_impression", {})
    blast_pct = summary.get("blast_pct", 0.0)
    flags = summary.get("flags", {})
    diff = summary.get("differential_pct", {})

    lines = [
        f"# Hematology Report — Case {pid}",
        "",
        f"**Specimen:** Peripheral blood smear, {n_fov} fields of view, "
        f"{n_inf} of {n_all} detected objects classified as informative WBCs "
        f"({n_art} artefacts excluded).",
        "",
        "**Differential (clinical denominator):**",
        "",
        "| Cell type | % of informative WBCs |",
        "|---|---|",
    ]
    for cls, pct in sorted(diff.items(), key=lambda x: -x[1]):
        lines.append(f"| {_display_class(cls, class_display)} | {pct}% |")

    flag_parts = []
    if flags.get("blasts_present"):
        flag_parts.append("blasts present")
    if flags.get("blast_threshold_met"):
        flag_parts.append("blast threshold met")
    lines.extend([
        "",
        f"**Diagnostic flags:** {'; '.join(flag_parts) if flag_parts else 'no blast threshold met'}.",
        "",
        f"**Impression:** {disease_impression.get(disease, f'{disease} — review peripheral smear findings.')}",
        "",
    ])

    if flags.get("blast_threshold_met"):
        lines.append(
            f"Blast-equivalent burden is {blast_pct}% of informative WBCs, "
            f"meeting the {cfg.get('aggregation', {}).get('blast_threshold_pct', 20)}% threshold for acute leukemia consideration."
        )
    else:
        dominant = max(diff.items(), key=lambda x: x[1])[0] if diff else "unknown"
        lines.append(
            f"Dominant population: {_display_class(dominant, class_display)} "
            f"({diff.get(dominant, 0)}% of informative WBCs). Blast-equivalent burden {blast_pct}%."
        )
    lines.append("")

    morph = _top_morphology_line(summary, cfg.get("aggregation", {}).get("morphology_min_cells", 5))
    if morph:
        lines.extend([morph, ""])

    lines.extend([
        "**Differential considerations:**",
        "- Correlate with clinical history, CBC, and peripheral smear morphology.",
        "- Flow cytometric immunophenotyping if acute leukemia is suspected.",
        "- Bone marrow aspirate and trephine biopsy as clinically indicated.",
        "",
        "**Recommended workup:**",
        "- Flow cytometric immunophenotyping for lineage assignment.",
        "- Bone marrow aspirate and trephine biopsy when indicated.",
        "- Cytogenetics and molecular profiling per institutional protocol.",
        "",
        f"**QC:** {n_fov} FOVs; {n_inf}/{n_all} cells classifiable "
        f"({summary.get('qc', {}).get('pct_class_none', 0)}% artefact); "
        f"source={summary.get('source', 'unknown')}; "
        f"mean detection confidence={summary.get('qc', {}).get('mean_det_conf', 0)}.",
        "",
        "---",
        "*Automated multi-image peripheral blood smear analysis. Findings are intended to support "
        "— not replace — review by a board-certified hematopathologist.*",
    ])
    return "\n".join(lines)
