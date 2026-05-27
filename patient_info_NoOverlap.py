"""
Patient Cell-Type Percentages + Report-Ready Summary for LLD (Fixed Global Canvas)
Deduplicates 20% spatial tile overlap using absolute canvas positioning.
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
DOMAINS: list[str] = ["H_40X_C2"]
SPLITS = ["train", "test"]

# ---------------------------------------------------------------------------
# Semantics & Corrected Lookups
# ---------------------------------------------------------------------------
KNOWN_DIAGNOSES = {"ALL", "AML", "APML", "CLL", "CML"}
PERCENT_DECIMALS = 2

# Global Canvas Parameters
IOU_MATCH_THRESHOLD = 0.4
DEFAULT_IMAGE_WH = (640, 640)
OVERLAP_PERCENTAGE = 0.20

# Calculated unique non-overlapping translation stride (640 * 0.8 = 512 pixels)
GLOBAL_STRIDE_PX = int(DEFAULT_IMAGE_WH[0] * (1.0 - OVERLAP_PERCENTAGE))

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

OUT_PATH = os.path.join(HERE, "patient_WBC_stats_NoOveralp.json")
OUT_CSV_PATH = os.path.join(HERE, "patient_WBC_stats_NoOveralp.csv")

# ---------------------------------------------------------------------------
# Global Bounding Box Canvas Object
# ---------------------------------------------------------------------------
class GlobalBoundedBox:
    def __init__(self, local_x1, local_y1, local_x2, local_y2, cell_type, attrs=None, grid_x=0, grid_y=0):
        self.cell_type = cell_type
        self.attrs = attrs if attrs else {k: N_A_CODE for k in ATTRIBUTE_KEYS}
        
        # Map local pixel coordinates to absolute spatial matrix offsets
        self.global_x1 = (grid_x * GLOBAL_STRIDE_PX) + float(local_x1)
        self.global_y1 = (grid_y * GLOBAL_STRIDE_PX) + float(local_y1)
        self.global_x2 = (grid_x * GLOBAL_STRIDE_PX) + float(local_x2)
        self.global_y2 = (grid_y * GLOBAL_STRIDE_PX) + float(local_y2)
        
        self.global_area = (self.global_x2 - self.global_x1) * (self.global_y2 - self.global_y1)

    def compute_global_iou(self, other) -> float:
        """Computes canvas IoU. Class restriction removed to catch cross-lineage classification drift."""
        inter_x1 = max(self.global_x1, other.global_x1)
        inter_y1 = max(self.global_y1, other.global_y1)
        inter_x2 = min(self.global_x2, other.global_x2)
        inter_y2 = min(self.global_y2, other.global_y2)
        
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
            
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        union_area = self.global_area + other.global_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0

# ---------------------------------------------------------------------------
# Data Accumulator Storage Elements
# ---------------------------------------------------------------------------
def _new_patient_store() -> dict:
    return {
        "metadata_filename_diagnosis": None,
        "filenames": set(),
        "raw_canvas_box_pool": [],  
        "cell_counts": Counter(),
        "attribute_counts": {k: Counter() for k in ATTRIBUTE_KEYS},
        "celltype_attribute_counts": defaultdict(lambda: {k: Counter() for k in ATTRIBUTE_KEYS}),
    }

def parse_filename_grid(fname: str) -> tuple[int, int, str, str]:
    stem = os.path.splitext(os.path.basename(fname))[0]
    parts = stem.split("_")
    if len(parts) < 5:
        raise ValueError(f"Filename {fname} does not conform to expected LLD structure.")
    
    pid = parts[0]
    
    # DEFENSIVE FIX: Sanitizes stray backticks, symbols, or formatting noise from digits
    clean_grid_x = "".join(filter(str.isdigit, parts[1]))
    clean_grid_y = "".join(filter(str.isdigit, parts[2]))
    
    if not clean_grid_x or not clean_grid_y:
        raise ValueError(f"Unable to parse coordinates from raw string segments: {parts[1]} or {parts[2]}")

    grid_x = int(clean_grid_x)
    grid_y = int(clean_grid_y)
    dx = parts[-1]
    
    return grid_x, grid_y, pid, dx

# ---------------------------------------------------------------------------
# Pure AttriDet Ingestion Engine (JSON Double-Loading Removed)
# ---------------------------------------------------------------------------
def ingest_yolo_attribute_dir(stores: dict[str, dict], label_dir: str) -> None:
    if not os.path.isdir(label_dir):
        return

    paths = sorted(glob.glob(os.path.join(label_dir, "*.txt")))
    img_w, img_h = DEFAULT_IMAGE_WH
    
    for path in paths:
        fname = os.path.basename(path)
        grid_x, grid_y, pid, dx = parse_filename_grid(fname)
        stem = os.path.splitext(fname)[0]
        
        if pid not in stores:
            stores[pid] = _new_patient_store()
        if stores[pid]["metadata_filename_diagnosis"] is None:
            stores[pid]["metadata_filename_diagnosis"] = dx
        stores[pid]["filenames"].add(stem)

        with open(path) as f:
            for row in f:
                parts = row.strip().split()
                # Targets 12-column AttriDet structure explicitly
                if not parts or len(parts) < 12:
                    continue
                    
                try:
                    cls, cx, cy, w, h = int(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                except ValueError:
                    continue
                    
                x1 = (cx - w / 2.0) * img_w
                y1 = (cy - h / 2.0) * img_h
                x2 = (cx + w / 2.0) * img_w
                y2 = (cy + h / 2.0) * img_h
                
                ct = YOLO_CLASS_NAMES.get(cls, "none")
                
                attrs = {}
                for idx, attr_key in enumerate(ATTRIBUTE_KEYS):
                    try:
                        attrs[attr_key] = int(parts[5 + idx])
                    except (ValueError, IndexError):
                        attrs[attr_key] = N_A_CODE
                            
                global_box = GlobalBoundedBox(x1, y1, x2, y2, ct, attrs=attrs, 
                                              grid_x=grid_x, grid_y=grid_y)
                stores[pid]["raw_canvas_box_pool"].append(global_box)

def run_global_canvas_nms(boxes: list[GlobalBoundedBox]) -> list[GlobalBoundedBox]:
    """Collapses duplicate boxes across overlapping boundaries based on unified canvas space."""
    if not boxes:
        return []
    sorted_boxes = sorted(boxes, key=lambda b: b.global_area, reverse=True)
    retained = []
    
    while sorted_boxes:
        current = sorted_boxes.pop(0)
        retained.append(current)
        # Discards any border box sharing a high global IoU, completely independent of lineage class
        sorted_boxes = [b for b in sorted_boxes if current.compute_global_iou(b) < IOU_MATCH_THRESHOLD]
        
    return retained

def load_patient_data() -> dict:
    stores: dict[str, dict] = {}
    
    for domain in DOMAINS:
        paths = _domain_paths(domain)
        for split in SPLITS:
            # FIX: Only loading 12-column AttriDet files to prevent double-counting truth sources
            ingest_yolo_attribute_dir(stores, paths["yolo_attr"][split])
            
    for pid, s in stores.items():
        unique_canvas_cells = run_global_canvas_nms(s["raw_canvas_box_pool"])
        
        for box in unique_canvas_cells:
            ct = box.cell_type
            s["cell_counts"][ct] += 1
            for attr_key, code in box.attrs.items():
                if code == N_A_CODE:
                    continue
                label = ATTRIBUTE_VALUE_MAPS[attr_key].get(code, f"code_{code}")
                s["attribute_counts"][attr_key][label] += 1
                s["celltype_attribute_counts"][ct][attr_key][label] += 1
                
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

def _select_cohort_from_counts(counts: dict) -> set[str]:
    """Data-driven tracker to avoid ground-truth metadata label leaks."""
    abnormal_pool = CLINICAL_GROUPS["blasts"] | CLINICAL_GROUPS["abnormal_precursors"] | CLINICAL_GROUPS["lymphoid"]
    candidates = {ct: counts.get(ct, 0) for ct in abnormal_pool if counts.get(ct, 0) > 0}
    if not candidates:
        return set()
    return {max(candidates, key=candidates.get)}

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

    cohort_types = _select_cohort_from_counts(counts)
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

    qc = {
        "n_annotated_cells": sum(counts.values()),
        "n_identified_wbc": n_wbc,
        "n_artifacts": counts.get("none", 0),
        "n_fields_of_view": rec["n_images"],
        "n_cells_in_cohort": n_cohort,
        "low_cell_count_warning": n_wbc < LOW_CELL_COUNT_THRESHOLD,
        "sparse_annotation_skew_warning": is_sparse_skew_suspected,
        "global_canvas_stitching_active": True
    }

    return {
        "metadata_filename_diagnosis": dx,
        "blast_pool_percentage_of_wbc": blast_pool_pct,
        "dominant_cell_type": max(pct_clinical, key=pct_clinical.get) if pct_clinical else None,
        "dominant_cell_pct": max(pct_clinical.values()) if pct_clinical else 0.0,
        "diagnostic_flags": flags,
        "blast_morphology": blast_morphology,
        "qc": qc
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
        print(f"[SUCCESS] Pipeline completed safely. Global Canvas Stitched NMS active.")
    except Exception as e:
        print(f"[FATAL PIPELINE CRASH] Execution halted: {str(e)}")