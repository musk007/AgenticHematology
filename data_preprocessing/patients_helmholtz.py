#!/usr/bin/env python3
"""
build_reports_aml_mll.py
========================
Generate report-ready JSON (and optional markdown) for the
AML-Cytomorphology_MLL_Helmholtz dataset directly from its metadata
spreadsheet.

Why this dataset needs no detection/classification run
------------------------------------------------------
The MLL metadata already provides the full peripheral-blood differential per
patient (pb_myeloblast ... pb_other, summing to ~100). These ARE the cell
percentages our aggregator would otherwise compute. So we map the metadata
columns straight into the same `report_ready` structure the LLD pipeline
produces, and hand it to the existing template report generator.

Important caveats (read before using the outputs)
-------------------------------------------------
1. Labels are GENETIC subtypes (NPM1, PML_RARA, RUNX1_RUNX1T1, CBFB_MYH11) or
   `control`, not FAB classes. All non-control cases are AML. We record the
   genetic label as `metadata_filename_diagnosis` for reference but the
   pipeline's rule classifier will read the differential, not the gene.
2. The differential has NO "abnormal promyelocyte" category. PML_RARA (APL)
   cases here carry their blasts under pb_myeloblast, so the APML rule will
   NOT fire from this metadata — PML_RARA will present as AML by morphology.
   This is a dataset limitation, not a pipeline bug; do not "fix" it by
   reassigning, that would be fabricating cell types.
3. There are no morphologic attributes in this metadata, so the blast
   morphology cohort block is omitted (cohort size 0).

Usage
-----
    python build_reports_aml_mll.py \
        --metadata AML-Cytomorphology_MLL_Helmholtz.xlsx \
        --out-json out/aml_mll_report_ready.json \
        --out-reports out/reports_aml_mll/        # optional markdown
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


# Map MLL differential columns -> our canonical cell-type names.
# Both "atypical reactive" and "atypical neoplastic" lymphocytes map to the
# atypical-lymphocyte bucket the classifier understands.
MLL_DIFF_COLUMNS = {
    "pb_myeloblast": "myeloblast",
    "pb_promyelocyte": "promyelocyte",
    "pb_myelocyte": "myelocyte",
    "pb_metamyelocyte": "metamyelocyte",
    "pb_neutrophil_band": "band_neutrophil",
    "pb_neutrophil_segmented": "neutrophil",
    "pb_eosinophil": "eosinophil",
    "pb_basophil": "basophil",
    "pb_monocyte": "monocyte",
    "pb_lymph_typ": "lymphocyte",
    "pb_lymph_atyp_react": "atypical lymphocyte",
    "pb_lymph_atyp_neopl": "atypical lymphocyte",
    "pb_other": "none",
}

# Blast-like classes for the blast-burden computation (matches the pipeline).
BLAST_CLASSES = {"myeloblast", "lymphoblast", "monoblast", "abnormal promyelocyte"}

# Map MLL genetic bag_labels -> the five leukemia classes (+ Healthy).
# All four recurrent genetic abnormalities here are AML subtypes. PML_RARA is
# genetically APL, but see the module docstring: this metadata codes APL blasts
# as pb_myeloblast, so morphologically it presents as AML. We therefore set the
# GROUND-TRUTH label to APML for PML_RARA (correct clinically), while the
# pipeline's morphology classifier will predict AML — that divergence is a real,
# reportable dataset limitation, not something to paper over.
MLL_LABEL_MAP = {
    "NPM1": "AML",
    "CBFB_MYH11": "AML",
    "RUNX1_RUNX1T1": "AML",
    "PML_RARA": "APML",
    "control": "Healthy",
}


def map_mll_label(bag_label: str) -> str:
    return MLL_LABEL_MAP.get(str(bag_label), str(bag_label))


def build_report_ready(row: pd.Series) -> dict:
    """Turn one metadata row into the report_ready structure."""
    # Collapse the metadata columns into our cell-type vocabulary.
    counts: dict[str, float] = {}
    for col, cell_type in MLL_DIFF_COLUMNS.items():
        val = row.get(col)
        if pd.isna(val):
            continue
        counts[cell_type] = counts.get(cell_type, 0.0) + float(val)

    total = sum(counts.values())
    # The metadata is already a percentage differential (sums ~100). Treat the
    # values as both the "counts" (per 100 cells) and the percentages.
    informative = {k: v for k, v in counts.items() if k != "none"}
    total_informative = sum(informative.values())

    clinical_pct = {
        k: round(100.0 * v / total_informative, 2) for k, v in informative.items()
    } if total_informative else {}
    all_pct = {
        k: round(100.0 * v / total, 2) for k, v in counts.items()
    } if total else {}

    blast_n = sum(informative.get(c, 0.0) for c in BLAST_CLASSES)
    blast_pct = round(100.0 * blast_n / total_informative, 2) if total_informative else 0.0

    dominant = max(informative, key=informative.get) if informative else "none"

    n_images = int(row.get("instance_count") or 0)

    mapped_label = map_mll_label(row.get("bag_label"))

    report_ready = {
        "metadata_filename_diagnosis": mapped_label,
        "metadata_genetic_label": str(row.get("bag_label")),
        "blast_pool_percentage_of_wbc": blast_pct,
        "dominant_cell_type": dominant,
        "dominant_cell_pct": clinical_pct.get(dominant, 0.0),
        "diagnostic_flags": {
            "blasts_present": blast_n > 0,
            "blast_threshold_met": blast_pct >= 20.0,
            "abnormal_promyelocytes_present": False,  # not separable in this metadata
            "atypical_lymphocytes_present": informative.get("atypical lymphocyte", 0) > 0,
            "basophilia_present": clinical_pct.get("basophil", 0.0) >= 2.0,
            "eosinophilia_present": clinical_pct.get("eosinophil", 0.0) >= 5.0,
            "left_shifted_myeloid": (
                informative.get("myelocyte", 0) + informative.get("metamyelocyte", 0)
            ) > 0,
            "monocytosis_present": clinical_pct.get("monocyte", 0.0) >= 10.0,
        },
        # No per-cell morphology attributes in this dataset.
        "blast_morphology": {},
        "qc": {
            "n_annotated_cells": int(round(total)),
            "n_identified_wbc": int(round(total_informative)),
            "n_artifacts": int(round(counts.get("none", 0.0))),
            "n_fields_of_view": n_images,
            "n_cells_in_cohort": 0,  # no morphology cohort available
            "low_cell_count_warning": total_informative < 50,
            "sparse_annotation_skew_warning": False,
            "global_canvas_stitching_active": False,  # pre-cropped cells
        },
    }

    case = {
        "metadata_filename_diagnosis": mapped_label,
        "metadata_genetic_label": str(row.get("bag_label")),
        "n_images": n_images,
        "n_cells_total": int(round(total)),
        "n_cells_identified_wbc": int(round(total_informative)),
        "cell_counts": {k: int(round(v)) for k, v in counts.items()},
        "cell_percentages_all": all_pct,
        "cell_percentages_clinical": clinical_pct,
        "attributes": {},  # none in this dataset
        "report_ready": report_ready,
        # Extra context preserved for the diagnosis-report stage.
        "patient_metadata": {
            "sex": "F" if row.get("sex_1f_2m") == 1 else ("M" if row.get("sex_1f_2m") == 2 else None),
            "age": float(row["age"]) if not pd.isna(row.get("age")) else None,
            "wbc_per_ul": float(row["leucocytes_per_¬µl"]) if not pd.isna(row.get("leucocytes_per_¬µl")) else None,
            "genetic_label": str(row.get("bag_label")),
        },
    }
    return case


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", required=True, help="AML-MLL .xlsx metadata file")
    ap.add_argument("--sheet", default="metadata")
    ap.add_argument("--out-json", required=True, help="Output combined report_ready JSON")
    ap.add_argument("--out-reports", default=None, help="Optional dir for per-case markdown")
    ap.add_argument("--exclude-controls", action="store_true",
                    help="Drop control patients. Default keeps them, labeled 'Healthy'.")
    args = ap.parse_args()

    df = pd.read_excel(args.metadata, sheet_name=args.sheet)

    cases: dict[str, dict] = {}
    for _, row in df.iterrows():
        pid = str(row["patient_id"])
        if args.exclude_controls and str(row.get("bag_label")) == "control":
            continue
        cases[pid] = build_report_ready(row)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} cases -> {out_json}")

    # Optional: render markdown using the existing LLD report generator.
    if args.out_reports:
        try:
            from leukemia_report_generator import generate_report
        except ImportError:
            print("NOTE: leukemia_report_generator.py not importable here; "
                  "skipping markdown. Run with it on PYTHONPATH to render reports.")
            return
        out_dir = Path(args.out_reports)
        out_dir.mkdir(parents=True, exist_ok=True)
        for pid, case in cases.items():
            md = generate_report(pid, case)
            (out_dir / f"case_{pid}_report.md").write_text(md, encoding="utf-8")
        print(f"Wrote {len(cases)} markdown reports -> {out_dir}")


if __name__ == "__main__":
    main()