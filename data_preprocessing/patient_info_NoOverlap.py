"""
Patient Cell-Type Percentages + Report-Ready Summary for LLD (100X, no overlap)
Aggregates AttriDet labels directly per patient without global-canvas deduplication.
Use this when input tiles are already non-overlapping.

Optimized to run strictly on 12-column AttriDet labels to eliminate JSON double-loading.
"""

import json
import csv
import os
import glob
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# Config -- Paths & Canonical Domain Selection
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))

DATASET_ROOT = (
    "/Volumes/One Touch/Data/Hematology/Large Leukemia Dataset/"
    "Leukemia_Attr/LeukemiaAttri_Dataset"
)

# Restriced to a single canonical camera domain to prevent sensor multiplication
DOMAINS: list[str] = ["H_100X_C2"]
SPLITS = ["train", "test"]

# ---------------------------------------------------------------------------
# Semantics & Corrected Lookups
# ---------------------------------------------------------------------------
KNOWN_DIAGNOSES = {"ALL", "AML", "APML", "CLL", "CML"}
PERCENT_DECIMALS = 2

ATTRIBUTE_VALUE_MAPS: dict[str, dict[int, str]] = {
    "cell_size":              {0: "small",   1: "medium",     2: "large",               4: "n_a"},
    "nuclear_chromatio":      {0: "open",    1: "coarse",                               4: "n_a"},
    "nuclear_shape":          {0: "regular", 1: "irregular",  2: "cleaved_or_folded",   4: "n_a"},
    "nucleolus":              {0: "inconspicuous", 1: "prominent",                      4: "n_a"},
    "cytoplasm":              {0: "scanty",  1: "abundant",                             4: "n_a"},
    "cytoplasmic_basophilia": {0: "slight",  1: "moderate",                             4: "n_a"},
    "cytoplasmic_vacuoles":   {0: "absent",  1: "prominent",                            4: "n_a"},
}
ATTRIBUTE_KEYS = list(ATTRIBUTE_VALUE_MAPS.keys())
N_A_CODE = 4

# Strict 0-indexed schema matching your AttriDet text file findings (none = 0)
YOLO_CLASS_NAMES: dict[int, str] = {
    0:  "none",
    1:  "myeloblast",
    2:  "lymphoblast",
    3:  "neutrophil",
    4:  "atypical lymphocyte",
    5:  "promonocyte",
    6:  "monoblast",
    7:  "lymphocyte",
    8:  "myelocyte",
    9:  "abnormal promyelocyte",
    10: "monocyte",
    11: "metamyelocyte",
    12: "eosinophil",
    13: "basophil"
}
# Lower rank = higher diagnostic priority when counts tie.
# Ordered by: (1) clinical urgency, (2) lineage-defining specificity, (3) maturity.
CELL_TYPE_PRIORITY: dict[str, int] = {
    "abnormal promyelocyte": 1,   # APML — emergency (DIC), near-pathognomonic
    "myeloblast":            2,   # AML-defining blast
    "lymphoblast":           3,   # ALL-defining blast
    "monoblast":             4,   # AML monocytic blast-equivalent
    "promonocyte":           5,   # AML monocytic, one step more mature
    "atypical lymphocyte":   6,   # reactive/mimic flag — supportive only
    "lymphocyte":            7,   # mature lymphoid — meaningful only in CLL context
}
COHORT_ELIGIBLE = set(CELL_TYPE_PRIORITY)        # only these can be selected as a cohort
DEFAULT_PRIORITY = 50                             # any unseen type sorts last

TIER1_BLAST_TYPES = {"myeloblast", "lymphoblast", "monoblast"}
MIN_BLAST_TIE_COUNT = 3                            # floor below which a tie is treated as noise


CLINICAL_GROUPS: dict[str, set[str]] = {
    "blasts":               {"myeloblast", "lymphoblast", "monoblast"},
    "abnormal_precursors":  {"abnormal promyelocyte"},
    "intermediate_myeloid": {"promonocyte", "myelocyte", "metamyelocyte"},
    "mature_granulocytes":  {"neutrophil", "eosinophil", "basophil"},
    "lymphoid":             {"lymphocyte", "atypical lymphocyte"},
    "monocytic":            {"monocyte"},
    "unidentified":         {"none"},
}

BLAST_THRESHOLD_PCT = 20.0
BASOPHILIA_THRESHOLD_PCT = 2.0
LOW_CELL_COUNT_THRESHOLD = 30

OUT_PATH = os.path.join(HERE, "patient_WBC_stats_100X.json")
OUT_CSV_PATH = os.path.join(HERE, "patient_WBC_stats_100X.csv")

# ---------------------------------------------------------------------------
# Data Accumulator Storage Elements
# ---------------------------------------------------------------------------
def _new_patient_store() -> dict:
    return {
        "metadata_filename_diagnosis": None,
        "filenames": set(),
        "cell_counts": Counter(),
        "attribute_counts": {k: Counter() for k in ATTRIBUTE_KEYS},
        "celltype_attribute_counts": defaultdict(lambda: {k: Counter() for k in ATTRIBUTE_KEYS}),
    }

def parse_filename(fname: str) -> tuple[str, str]:
    """Parse patient id and diagnosis from 100X or 40X-style filenames."""
    stem = os.path.splitext(os.path.basename(fname))[0]
    parts = stem.split("_")
    if len(parts) < 4:
        raise ValueError(f"Filename {fname} does not conform to expected LLD structure.")
    return parts[0], parts[-1]

# ---------------------------------------------------------------------------
# Pure AttriDet Ingestion Engine (JSON Double-Loading Removed)
# ---------------------------------------------------------------------------
def ingest_yolo_attribute_dir(stores: dict[str, dict], label_dir: str) -> None:
    if not os.path.isdir(label_dir):
        return

    paths = sorted(glob.glob(os.path.join(label_dir, "*.txt")))
    breakpoint()
    for path in paths:
        fname = os.path.basename(path)
        pid, dx = parse_filename(fname)
        stem = os.path.splitext(fname)[0]
        
        if pid not in stores:
            stores[pid] = _new_patient_store()
        if stores[pid]["metadata_filename_diagnosis"] is None:
            stores[pid]["metadata_filename_diagnosis"] = dx
        stores[pid]["filenames"].add(stem)
        breakpoint()

        with open(path) as f:
            for row in f:
                parts = row.strip().split()
                # Targets 12-column AttriDet structure explicitly
                if not parts or len(parts) < 12:
                    continue
                    
                try:
                    cls = int(parts[0])
                except ValueError:
                    continue
                
                ct = YOLO_CLASS_NAMES.get(cls, "none")
                stores[pid]["cell_counts"][ct] += 1
                breakpoint()

                for idx, attr_key in enumerate(ATTRIBUTE_KEYS):
                    try:
                        code = int(parts[5 + idx])
                    except (ValueError, IndexError):
                        code = N_A_CODE
                    if code == N_A_CODE:
                        continue
                    label = ATTRIBUTE_VALUE_MAPS[attr_key].get(code, f"code_{code}")
                    stores[pid]["attribute_counts"][attr_key][label] += 1
                    stores[pid]["celltype_attribute_counts"][ct][attr_key][label] += 1

def _build_differential_alerts(counts, pct_clinical, group_percentages,
                               blast_pool_pct, cohort_ambiguous) -> list[dict]:
    alerts = []
    neutrophil_pct      = pct_clinical.get("neutrophil", 0.0)
    dominant_cell       = max(pct_clinical, key=pct_clinical.get) if pct_clinical else None
    precursors_present  = group_percentages.get("intermediate_myeloid", 0.0) >= 10.0
    basophils_absent    = counts.get("basophil", 0) == 0

    if (dominant_cell == "neutrophil"
            and precursors_present
            and blast_pool_pct < BLAST_THRESHOLD_PCT
            and basophils_absent):
        alerts.append({
            "code": "CML_PATTERN_NO_BASOPHILIA",
            "severity": "review",
            "message": ("Smear shows a predominance of neutrophils followed by myelocytes "
                        "and other granulocytic precursors. The absence of identifiable "
                        "basophils is unusual for CML and raises the possibility of "
                        "alternative diagnoses such as a leukemoid reaction or severe "
                        "infection/sepsis."),
            "recommendation": ("Correlate with the CBC, differential count, and BCR::ABL1 "
                               "testing."),
            "suggested_action": "FLAG_FOR_REVIEW",
        })

    # Mixed-lineage blast tie (MPAL — outside the 5-class taxonomy)
    if cohort_ambiguous:
        alerts.append({
            "code": "MIXED_LINEAGE_BLAST_TIE",
            "severity": "review",
            "message": ("Co-dominant myeloid and lymphoid blast populations. Pattern is "
                        "compatible with mixed-phenotype acute leukemia, which lies outside "
                        "the five supported subtypes."),
            "recommendation": "Flow cytometry / immunophenotyping required to resolve lineage.",
            "suggested_action": "FLAG_FOR_REVIEW",
        })

    # Blast burden inconsistent with a chronic picture
    mature_lymphoid_dominant = pct_clinical.get("lymphocyte", 0.0) >= 50.0
    if blast_pool_pct >= BLAST_THRESHOLD_PCT and mature_lymphoid_dominant:
        alerts.append({
            "code": "BLASTS_IN_CHRONIC_PATTERN",
            "severity": "review",
            "message": ("Blast pool meets the acute threshold alongside a mature lymphoid "
                        "background — incompatible with a stable chronic process."),
            "recommendation": "Consider transformation/blast crisis; correlate clinically.",
            "suggested_action": "FLAG_FOR_REVIEW",
        })

    return alerts

def load_patient_data() -> dict:
    stores: dict[str, dict] = {}
    
    for domain in DOMAINS:
        paths = _domain_paths(domain)
        breakpoint()
        for split in SPLITS:
            ingest_yolo_attribute_dir(stores, paths["yolo_attr"][split])

    return _finalise_stores(stores)

def _finalise_stores(stores: dict[str, dict]) -> dict:
    return {
        pid: {
            "metadata_filename_diagnosis": s["metadata_filename_diagnosis"],
            "n_images": len(s["filenames"]),
            "n_cells_total": sum(s["cell_counts"].values()),
            "cell_counts": dict(s["cell_counts"].most_common()),
            "attribute_counts": {k: dict(s["attribute_counts"][k].most_common()) for k in ATTRIBUTE_KEYS},
            "celltype_attribute_counts": {
                ct: {k: dict(s["celltype_attribute_counts"][ct][k].most_common()) for k in ATTRIBUTE_KEYS}
                for ct in s["celltype_attribute_counts"]
            },
        }
        for pid, s in sorted(stores.items(), key=lambda kv: (int(kv[0]) if kv[0].isdigit() else float("inf"), kv[0]))
    }

def _domain_paths(domain: str) -> dict:
    root = os.path.join(DATASET_ROOT, domain)
    return {
        "yolo_attr": {s: os.path.join(root, "txt_labels", "AttriDet", s) for s in SPLITS},
    }

# ---------------------------------------------------------------------------
# Data Analysis and Reporting Framework
# ---------------------------------------------------------------------------
def _percentages_from_counts(counts: dict, denominator: int) -> dict:
    if not denominator:
        return {}
    return {k: round(v / denominator * 100, PERCENT_DECIMALS) for k, v in counts.items()}

def _attribute_summary(attribute_counts: dict) -> dict:
    out = {}
    for attr_key in ATTRIBUTE_KEYS:
        raw = dict(attribute_counts.get(attr_key, {}))
        informative = {k: v for k, v in raw.items() if k != "n_a"}
        n_inf = sum(informative.values())
        out[attr_key] = {
            "counts": raw,
            "n_informative_cells": n_inf,
            "n_na_cells": raw.get("n_a", 0),
            "percentages": _percentages_from_counts(informative, n_inf)
        }
    return out

def _select_cohort_from_counts(counts: dict) -> tuple[set[str], bool]:
    candidates = {ct: counts.get(ct, 0) for ct in COHORT_ELIGIBLE if counts.get(ct, 0) > 0}
    if not candidates:
        return set(), False

    max_count = max(candidates.values())
    tied = [ct for ct, v in candidates.items() if v == max_count]

    ambiguous = (
        len([ct for ct in tied if ct in TIER1_BLAST_TYPES]) >= 2
        and max_count >= MIN_BLAST_TIE_COUNT
    )

    # Deterministic AND medically ordered: lowest rank wins among ties.
    winner = min(tied, key=lambda ct: CELL_TYPE_PRIORITY.get(ct, DEFAULT_PRIORITY))
    return {winner}, ambiguous

def _build_report_ready(rec: dict, pct_clinical: dict) -> dict:
    counts = rec["cell_counts"]
    dx = rec["metadata_filename_diagnosis"]
    n_wbc = sum(counts.get(ct, 0) for ct in counts if ct != "none")

    group_counts = {g: sum(counts.get(ct, 0) for ct in members) for g, members in CLINICAL_GROUPS.items()}
    group_percentages = _percentages_from_counts(group_counts, n_wbc)

    blast_pool_count = group_counts["blasts"] + group_counts["abnormal_precursors"]
    blast_pool_pct = round((blast_pool_count / n_wbc * 100), PERCENT_DECIMALS) if n_wbc else 0.0

    flags = {
        "blasts_present":                  blast_pool_count > 0,
        "blast_threshold_met":             blast_pool_pct >= BLAST_THRESHOLD_PCT,
        "abnormal_promyelocytes_present":  counts.get("abnormal promyelocyte", 0) > 0,
        "atypical_lymphocytes_present":    counts.get("atypical lymphocyte", 0) > 0,
        "basophilia_present":              pct_clinical.get("basophil", 0.0) >= BASOPHILIA_THRESHOLD_PCT,
        "eosinophilia_present":            pct_clinical.get("eosinophil", 0.0) >= 5.0,
        "left_shifted_myeloid":            group_percentages.get("intermediate_myeloid", 0.0) >= 10.0,
        "monocytosis_present":             pct_clinical.get("monocyte", 0.0) >= 10.0,
    }

    # Deterministic, medically-ranked cohort selection (returns ambiguity flag for tier-1 blast ties)
    cohort_types, cohort_ambiguous = _select_cohort_from_counts(counts)
    merged_cohort_attrs = {k: Counter() for k in ATTRIBUTE_KEYS}
    n_cohort = 0
    for ct in cohort_types:
        n_cohort += counts.get(ct, 0)
        for attr_key in ATTRIBUTE_KEYS:
            for state, count in rec["celltype_attribute_counts"].get(ct, {}).get(attr_key, {}).items():
                merged_cohort_attrs[attr_key][state] += count

    cohort_summary = _attribute_summary(merged_cohort_attrs)
    blast_morphology = {}
    for k in ATTRIBUTE_KEYS:
        pcts = cohort_summary[k]["percentages"]
        dom_state = next(iter(pcts.keys())) if pcts else None
        dom_pct = next(iter(pcts.values())) if pcts else 0.0
        blast_morphology[k] = {"dominant": dom_state, "dominance_pct": dom_pct}

    is_sparse_skew_suspected = False
    if dx in {"ALL", "AML", "APML"} and n_wbc > 0:
        if blast_pool_pct < BLAST_THRESHOLD_PCT and n_wbc < LOW_CELL_COUNT_THRESHOLD:
            is_sparse_skew_suspected = True

    # Differential contradiction layer — patterns that point outside / against the 5-class taxonomy
    alerts = _build_differential_alerts(
        counts=counts,
        pct_clinical=pct_clinical,
        group_percentages=group_percentages,
        blast_pool_pct=blast_pool_pct,
        cohort_ambiguous=cohort_ambiguous,
    )

    qc = {
        "n_annotated_cells": sum(counts.values()),
        "n_identified_wbc": n_wbc,
        "n_artifacts": counts.get("none", 0),
        "n_fields_of_view": rec["n_images"],
        "n_cells_in_cohort": n_cohort,
        "low_cell_count_warning": n_wbc < LOW_CELL_COUNT_THRESHOLD,
        "sparse_annotation_skew_warning": is_sparse_skew_suspected,
        "global_canvas_stitching_active": False,
        "cohort_selection_ambiguous": cohort_ambiguous,
        "differential_alerts": alerts,
        "requires_review": any(a["severity"] == "review" for a in alerts),
    }

    return {
        "metadata_filename_diagnosis": dx,
        "blast_pool_percentage_of_wbc": blast_pool_pct,
        "dominant_cell_type": max(pct_clinical, key=pct_clinical.get) if pct_clinical else None,
        "dominant_cell_pct": max(pct_clinical.values()) if pct_clinical else 0.0,
        "diagnostic_flags": flags,
        "blast_morphology": blast_morphology,
        "qc": qc,
    }

def compute_percentages(summary: dict) -> dict:
    out = {}
    for pid, rec in summary.items():
        c_all = dict(rec["cell_counts"])
        c_clin = {k: v for k, v in c_all.items() if k != "none"}

        pct_all = _percentages_from_counts(c_all, sum(c_all.values()))
        pct_clin = _percentages_from_counts(c_clin, sum(c_clin.values()))
        
        out[pid] = {
            "metadata_filename_diagnosis": rec["metadata_filename_diagnosis"],
            "n_images": rec["n_images"],
            "n_cells_total": sum(c_all.values()),
            "n_cells_identified_wbc": sum(c_clin.values()),
            "cell_counts": c_all,
            "cell_percentages_all": pct_all,
            "cell_percentages_clinical": pct_clin,
            "attributes": _attribute_summary(rec["attribute_counts"]),
            "report_ready": _build_report_ready(rec, pct_clin)
        }
    return out

def write_csv(percentages: dict, path: str) -> None:
    all_cell_types = sorted({ct for rec in percentages.values() for ct in rec["cell_counts"]})
    header = ["patient_id", "metadata_filename_diagnosis", "n_images", "n_cells_total", "n_cells_identified_wbc"]
    for ct in all_cell_types:
        header += [f"celltype__{ct}__count", f"celltype__{ct}__pct_clinical"]
    header += ["blast_pool_pct_clinical", "qc__low_cell_count", "qc__canvas_stitching_active"]
    
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for pid, rec in percentages.items():
            rep = rec["report_ready"]
            row = [pid, rec["metadata_filename_diagnosis"], rec["n_images"], rec["n_cells_total"], rec["n_cells_identified_wbc"]]
            for ct in all_cell_types:
                row.append(rec["cell_counts"].get(ct, 0))
                row.append(rec["cell_percentages_clinical"].get(ct, 0.0))
            row += [rep["blast_pool_percentage_of_wbc"], rep["qc"]["low_cell_count_warning"], rep["qc"]["global_canvas_stitching_active"]]
            writer.writerow(row)

if __name__ == "__main__":
    try:
        summary_data = load_patient_data()
        final_percentages = compute_percentages(summary_data)
        with open(OUT_PATH, "w") as out_f:
            json.dump(final_percentages, out_f, indent=2)
        write_csv(final_percentages, OUT_CSV_PATH)
        print(f"[SUCCESS] Pipeline completed safely. Direct aggregation (no overlap deduplication).")
    except Exception as e:
        print(f"[FATAL PIPELINE CRASH] Execution halted: {str(e)}")