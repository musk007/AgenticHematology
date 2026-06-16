# Hematology Report — Case 31

**Specimen:** Peripheral blood smear, 50 fields of view, 307 of 405 detected objects classified as informative WBCs (98 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 66.8% |
| Myelocytes | 20.5% |
| Metamyelocytes | 4.9% |
| Myeloblasts | 4.9% |
| Basophils | 1.3% |
| Eosinophils | 0.7% |
| Monocytes | 0.7% |
| Lymphocytes | 0.3% |

**Diagnostic flags:** blasts present.

**Impression:** Chronic Myeloid Leukemia (CML).

Dominant population: Neutrophils (66.8% of informative WBCs). Blast-equivalent burden 4.9%.

**Cohort morphology (n = 205 Neutrophils):** nucleus (100.0%); cytoplasmic vacuoles (99.8%); cytoplasmic basophilia (99.0%); nuclear chromatin (98.1%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 50 FOVs; 307/405 cells classifiable (24.2% artefact); source=agentic_orchestrator; mean detection confidence=0.781.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 50
- Raw detected cells before overlap deduplication: 450
- Deduplicated detected cells: 405
- Informative WBCs: 307
- Artefacts/non-WBC detections: 98

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 205 | 66.8% |
| Myelocyte | 63 | 20.5% |
| Metamyelocyte | 15 | 4.9% |
| Myeloblast | 15 | 4.9% |
| Basophil | 4 | 1.3% |
| Eosinophil | 2 | 0.7% |
| Monocyte | 2 | 0.7% |
| Lymphocyte | 1 | 0.3% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **CML** (confidence 0.70). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img025_c000` in `31_33_72_400_CML.png` bbox=[167.75, 284.5, 232.25, 401.5]: Myelocyte (0.95); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `31_12_58_400_CML.png` bbox=[327.0, 399.0, 388.0, 508.5]: Metamyelocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img022_c000` in `31_30_31_400_CML.png` bbox=[431.0, 0.0, 497.0, 85.0]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img017_c000` in `31_26_69_400_CML.png` bbox=[501.5, 406.0, 561.5, 515.5]: Myelocyte (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img005_c000` in `31_15_60_400_CML.png` bbox=[96.56, 529.0, 168.0, 640.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img007_c000` in `31_17_62_400_CML.png` bbox=[598.0, 262.5, 640.0, 382.5]: Myelocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img046_c000` in `31_6_53_400_CML.png` bbox=[189.75, 14.72, 251.5, 126.75]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c000` in `31_11_57_400_CML.png` bbox=[561.5, 166.0, 637.5, 282.75]: Myelocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.