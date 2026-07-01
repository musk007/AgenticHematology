# Hematology Report — Case 4

**Specimen:** Peripheral blood smear, 52 fields of view, 140 of 161 detected objects classified as informative WBCs (21 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 55.0% |
| Neutrophils | 27.9% |
| Lymphocytes | 10.7% |
| Eosinophils | 4.3% |
| Myelocytes | 0.7% |
| Atypical lymphocytes | 0.7% |
| Monocytes | 0.7% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 55.0% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 77 Lymphoblasts):** nucleus (80.2%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 52 FOVs; 140/161 cells classifiable (13.0% artefact); source=agentic_orchestrator; mean detection confidence=0.818.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 52
- Detected cells: 161
- Informative WBCs: 140
- Artefacts/non-WBC detections: 21

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 77 | 55.0% |
| Neutrophil | 39 | 27.9% |
| Lymphocyte | 15 | 10.7% |
| Eosinophil | 6 | 4.3% |
| Atypical lymphocyte | 1 | 0.7% |
| Monocyte | 1 | 0.7% |
| Myelocyte | 1 | 0.7% |

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.92). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img000_c000` in `4_102_1000_ALL.png` bbox=[373.5, 410.5, 441.5, 537.5]: Neutrophil (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c000` in `4_103_1000_ALL.png` bbox=[433.0, 382.5, 497.0, 465.0]: Lymphoblast (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c001` in `4_103_1000_ALL.png` bbox=[477.0, 239.38, 552.0, 368.5]: Eosinophil (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `4_104_1000_ALL.png` bbox=[210.0, 532.5, 288.5, 640.0]: Lymphoblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c001` in `4_104_1000_ALL.png` bbox=[557.0, 0.0, 610.0, 54.62]: Lymphoblast (0.83); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c000` in `4_105_1000_ALL.png` bbox=[443.5, 267.5, 504.5, 379.5]: Lymphoblast (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c000` in `4_15_1000_ALL.png` bbox=[80.38, 312.0, 137.5, 418.0]: Neutrophil (0.94); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c001` in `4_15_1000_ALL.png` bbox=[261.5, 449.5, 317.5, 537.5]: Neutrophil (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.