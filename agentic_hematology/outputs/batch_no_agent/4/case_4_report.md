# Hematology Report — Case 4

**Specimen:** Peripheral blood smear, 52 fields of view, 124 of 149 detected objects classified as informative WBCs (25 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 41.1% |
| Neutrophils | 31.5% |
| Lymphocytes | 23.4% |
| Eosinophils | 3.2% |
| Metamyelocytes | 0.8% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 41.1% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 51 Lymphoblasts):** nucleus (87.7%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 52 FOVs; 124/149 cells classifiable (16.8% artefact); source=agentic_orchestrator; mean detection confidence=0.743.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 52
- Raw detected cells before overlap deduplication: 166
- Deduplicated detected cells: 149
- Informative WBCs: 124
- Artefacts/non-WBC detections: 25

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 51 | 41.1% |
| Neutrophil | 39 | 31.5% |
| Lymphocyte | 29 | 23.4% |
| Eosinophil | 4 | 3.2% |
| Metamyelocyte | 1 | 0.8% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.92). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img039_c000` in `4_82_185_400_ALL.png` bbox=[0.06, 112.75, 41.44, 216.0]: Eosinophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img019_c000` in `4_42_117_400_ALL.png` bbox=[493.0, 208.5, 535.0, 275.5]: Lymphocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img041_c000` in `4_85_137_400_ALL.png` bbox=[286.5, 525.0, 340.5, 611.0]: Eosinophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img009_c000` in `4_28_40_400_ALL.png` bbox=[494.0, 550.0, 550.0, 640.0]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img007_c000` in `4_18_25_400_ALL.png` bbox=[384.75, 546.0, 451.25, 640.0]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img043_c000` in `4_88_139_400_ALL.png` bbox=[295.75, 498.5, 347.25, 584.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img008_c000` in `4_27_39_400_ALL.png` bbox=[280.5, 242.38, 332.0, 335.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img000_c000` in `4_102_147_400_ALL.png` bbox=[357.0, 389.75, 417.5, 510.75]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.