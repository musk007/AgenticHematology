# Hematology Report — Case 40

**Specimen:** Peripheral blood smear, 50 fields of view, 52 of 86 detected objects classified as informative WBCs (34 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 78.8% |
| Lymphoblasts | 7.7% |
| Lymphocytes | 3.8% |
| Myelocytes | 3.8% |
| Monocytes | 1.9% |
| Monoblasts | 1.9% |
| Eosinophils | 1.9% |

**Diagnostic flags:** blasts present.

**Impression:** Acute Myeloid Leukemia (AML).

Dominant population: Neutrophils (78.8% of informative WBCs). Blast-equivalent burden 9.6%.

**Cohort morphology (n = 41 Neutrophils):** nucleus (99.9%); cytoplasmic basophilia (99.7%); nuclear chromatin (99.6%); cytoplasmic vacuoles (99.5%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 50 FOVs; 52/86 cells classifiable (39.5% artefact); source=agentic_orchestrator; mean detection confidence=0.802.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 50
- Raw detected cells before overlap deduplication: 86
- Deduplicated detected cells: 86
- Informative WBCs: 52
- Artefacts/non-WBC detections: 34

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 41 | 78.8% |
| Lymphoblast | 4 | 7.7% |
| Lymphocyte | 2 | 3.8% |
| Myelocyte | 2 | 3.8% |
| Eosinophil | 1 | 1.9% |
| Monoblast | 1 | 1.9% |
| Monocyte | 1 | 1.9% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.64). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img049_c000` in `40_9_12_400_AML.png` bbox=[568.0, 447.0, 622.0, 550.0]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img046_c000` in `40_6_11_400_AML.png` bbox=[557.0, 433.5, 633.0, 566.0]: Monocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img007_c000` in `40_17_23_400_AML.png` bbox=[314.75, 190.5, 386.25, 311.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img044_c000` in `40_50_45_400_AML.png` bbox=[437.0, 39.03, 502.0, 156.25]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img042_c000` in `40_49_45_400_AML.png` bbox=[72.12, 175.25, 147.88, 301.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img038_c000` in `40_45_29_400_AML.png` bbox=[239.75, 0.0, 313.25, 117.75]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img042_c001` in `40_49_45_400_AML.png` bbox=[53.75, 288.0, 137.38, 415.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c000` in `40_14_20_400_AML.png` bbox=[54.5, 475.0, 128.0, 601.0]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.

> **⚠ Flagged for mandatory human review by the reflection agent.** Reason(s): High pct_class_none and low classifier confidence suggest unreliable evidence despite AML prediction.
