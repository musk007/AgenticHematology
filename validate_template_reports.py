import json
import re
from pathlib import Path


REPORTS_DIR = Path("/Users/roba.almajzoub/Desktop/MBZU/2026/Hematology/code/template_reports")
STATS_JSON = Path("/Users/roba.almajzoub/Desktop/MBZU/2026/Hematology/code/patient_WBC_stats_NoOveralp.json")

# Report percentages are rendered to one decimal place in markdown.
PCT_TOLERANCE = 0.11


CELL_TYPE_MAP = {
    "Lymphoblasts": "lymphoblast",
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


DIAGNOSIS_ALIASES = {
    "APML": ["APML", "APL"],
    "APL": ["APL", "APML"],
    "AML": ["AML", "Acute Myeloid Leukemia"],
    "ALL": ["ALL", "Acute Lymphoblastic Leukemia"],
    "CML": ["CML", "Chronic Myeloid Leukemia"],
    "CLL": ["CLL", "Chronic Lymphocytic Leukemia"],
}


def parse_report(report_text: str) -> dict:
    parsed = {}

    case_match = re.search(r"#\s+Hematology Report\s+—\s+Case\s+(\d+)", report_text)
    if not case_match:
        raise ValueError("Could not parse case ID from report title.")
    parsed["case_id"] = case_match.group(1)

    specimen_re = re.search(
        r"\*\*Specimen:\*\*\s*Peripheral blood smear,\s*(\d+)\s*fields of view,\s*"
        r"(\d+)\s*of\s*(\d+)\s*annotated objects classified as informative WBCs\s*"
        r"\((\d+)\s*artefacts excluded\)\.",
        report_text,
    )
    if not specimen_re:
        raise ValueError(f"Could not parse specimen line for case {parsed['case_id']}.")
    parsed["n_images"] = int(specimen_re.group(1))
    parsed["n_identified_wbc"] = int(specimen_re.group(2))
    parsed["n_annotated"] = int(specimen_re.group(3))
    parsed["n_artifacts"] = int(specimen_re.group(4))

    parsed["differential"] = {}
    for label, pct in re.findall(r"\|\s*([A-Za-z\s\-]+)\s*\|\s*([\d.]+)%\s*\|", report_text):
        if label.strip() == "Cell type":
            continue
        key = CELL_TYPE_MAP.get(label.strip())
        if key:
            parsed["differential"][key] = float(pct)

    impression_match = re.search(r"\*\*Impression:\*\*\s*(.+?)\.", report_text)
    parsed["impression"] = impression_match.group(1).strip() if impression_match else None

    blast_match = re.search(r"Lymphoblasts comprise\s*([\d.]+)%\s*of WBCs", report_text)
    parsed["blast_pool_percentage_of_wbc"] = float(blast_match.group(1)) if blast_match else None

    qc_re = re.search(
        r"\*\*QC:\*\*\s*(\d+)\s*FOVs;\s*(\d+)/(\d+)\s*cells classifiable\s*"
        r"\(([\d.]+)%\s*artefact\);\s*cohort cell count\s*=\s*(\d+);",
        report_text,
    )
    if not qc_re:
        raise ValueError(f"Could not parse QC line for case {parsed['case_id']}.")
    parsed["qc_n_fields_of_view"] = int(qc_re.group(1))
    parsed["qc_n_identified_wbc"] = int(qc_re.group(2))
    parsed["qc_n_annotated"] = int(qc_re.group(3))
    parsed["qc_artefact_pct"] = float(qc_re.group(4))
    parsed["qc_n_cells_in_cohort"] = int(qc_re.group(5))

    return parsed


def compare_case(parsed_report: dict, expected_case: dict) -> list[str]:
    issues = []
    rr = expected_case["report_ready"]

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
        if got != expected:
            issues.append(f"{key}: report={got}, json={expected}")

    expected_artefact_pct = round((rr["qc"]["n_artifacts"] / rr["qc"]["n_annotated_cells"]) * 100, 1)
    if abs(parsed_report["qc_artefact_pct"] - expected_artefact_pct) > PCT_TOLERANCE:
        issues.append(
            f"qc_artefact_pct: report={parsed_report['qc_artefact_pct']}, json={expected_artefact_pct}"
        )

    if parsed_report["blast_pool_percentage_of_wbc"] is not None:
        expected_blast_pct = round(rr["blast_pool_percentage_of_wbc"], 1)
        if abs(parsed_report["blast_pool_percentage_of_wbc"] - expected_blast_pct) > PCT_TOLERANCE:
            issues.append(
                "blast_pool_percentage_of_wbc: "
                f"report={parsed_report['blast_pool_percentage_of_wbc']}, json={expected_blast_pct}"
            )

    # Normalize diagnosis shortcuts to handle equivalent clinical acronyms safely.
    diagnosis_json = expected_case.get("metadata_filename_diagnosis")
    impression_text = parsed_report["impression"] or ""
    if diagnosis_json and impression_text:
        aliases = DIAGNOSIS_ALIASES.get(diagnosis_json, [diagnosis_json])
        impression_lower = impression_text.lower()
        if not any(alias.lower() in impression_lower for alias in aliases):
            if "unclassified" in impression_text.lower():
                issues.append(
                    "impression diagnosis mismatch (likely threshold fallback): "
                    f"report='{impression_text}', json='{diagnosis_json}'"
                )
            else:
                issues.append(
                    f"impression diagnosis mismatch: report='{impression_text}', json='{diagnosis_json}'"
                )

    clinical = expected_case.get("cell_percentages_clinical", {})
    for cell_type, report_pct in parsed_report["differential"].items():
        if cell_type not in clinical:
            issues.append(f"differential '{cell_type}' missing in json clinical percentages")
            continue
        expected_pct = round(float(clinical[cell_type]), 1)
        if abs(report_pct - expected_pct) > PCT_TOLERANCE:
            issues.append(f"differential {cell_type}: report={report_pct}, json={expected_pct}")

    return issues


def main() -> None:
    stats = json.loads(STATS_JSON.read_text())
    report_paths = sorted(REPORTS_DIR.glob("*.md"))

    if not report_paths:
        print(f"No markdown reports found in: {REPORTS_DIR}")
        return

    total_issues = 0
    for path in report_paths:
        parsed = parse_report(path.read_text())
        case_id = parsed["case_id"]
        if case_id not in stats:
            print(f"[FAIL] {path.name} -> case '{case_id}' not found in JSON")
            total_issues += 1
            continue

        issues = compare_case(parsed, stats[case_id])
        if issues:
            print(f"[FAIL] {path.name} (case {case_id})")
            for issue in issues:
                print(f"  - {issue}")
            total_issues += len(issues)
        else:
            print(f"[PASS] {path.name} (case {case_id})")

    print(f"\nValidation complete. Total mismatches: {total_issues}")


if __name__ == "__main__":
    main()
