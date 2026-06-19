# Hematology Report — Case 6

**Specimen:** Peripheral blood smear, 55 fields of view, 75 of 96 detected objects classified as informative WBCs (21 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 33.3% |
| Myeloblasts | 32.0% |
| Lymphocytes | 16.0% |
| Neutrophils | 6.7% |
| Eosinophils | 5.3% |
| Monocytes | 4.0% |
| Myelocytes | 2.7% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 65.3% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 25 Lymphoblasts):** nucleus (93.9%); nuclear chromatin (68.1%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 55 FOVs; 75/96 cells classifiable (21.9% artefact); source=agentic_orchestrator; mean detection confidence=0.71.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 55
- Raw detected cells before overlap deduplication: 113
- Deduplicated detected cells: 96
- Informative WBCs: 75
- Artefacts/non-WBC detections: 21

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 25 | 33.3% |
| Myeloblast | 24 | 32.0% |
| Lymphocyte | 12 | 16.0% |
| Neutrophil | 5 | 6.7% |
| Eosinophil | 4 | 5.3% |
| Monocyte | 3 | 4.0% |
| Myelocyte | 2 | 2.7% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.87). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img031_c000` in `6_3_13_400_ALL.png` bbox=[141.0, 145.25, 206.0, 274.25]: Myelocyte (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img027_c000` in `6_36_17_400_ALL.png` bbox=[447.0, 345.5, 506.0, 450.5]: Lymphocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img052_c000` in `6_7_28_400_ALL.png` bbox=[372.0, 321.0, 432.0, 417.0]: Lymphocyte (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img009_c001` in `6_19_50_400_ALL.png` bbox=[369.5, 344.25, 442.5, 459.75]: Myeloblast (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img030_c000` in `6_39_31_400_ALL.png` bbox=[34.12, 212.0, 107.75, 361.0]: Neutrophil (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img043_c000` in `6_50_101_400_ALL.png` bbox=[57.5, 55.75, 114.5, 144.75]: Lymphocyte (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img034_c000` in `6_42_42_400_ALL.png` bbox=[323.5, 142.62, 374.5, 235.38]: Lymphoblast (0.85); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img031_c001` in `6_3_13_400_ALL.png` bbox=[68.5, 355.5, 124.5, 455.0]: Lymphoblast (0.85); nuclear chromatin; nuclear shape; nucleus; cytoplasm.

> **⚠ Flagged for mandatory human review by the reflection agent.** Reason(s): High blast burden with low detection confidence and significant non-WBC noise suggests potential misclassification or artifact interference.
