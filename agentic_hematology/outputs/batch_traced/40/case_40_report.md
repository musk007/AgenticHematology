# Hematology Report — Case 40

**Specimen:** Peripheral blood smear, 50 fields of view, 43 of 74 detected objects classified as informative WBCs (31 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 81.4% |
| Lymphoblasts | 7.0% |
| Monocytes | 2.3% |
| Monoblasts | 2.3% |
| Lymphocytes | 2.3% |
| Eosinophils | 2.3% |
| Myelocytes | 2.3% |

**Diagnostic flags:** blasts present.

**Impression:** Acute Myeloid Leukemia (AML).

Dominant population: Neutrophils (81.4% of informative WBCs). Blast-equivalent burden 9.3%.

**Cohort morphology (n = 35 Neutrophils):** nuclear chromatin (100.0%); cytoplasmic basophilia (100.0%); nucleus (100.0%); cytoplasmic vacuoles (99.8%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 50 FOVs; 43/74 cells classifiable (41.9% artefact); source=agentic_orchestrator; mean detection confidence=0.831.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 50
- Raw detected cells before overlap deduplication: 74
- Deduplicated detected cells: 74
- Informative WBCs: 43
- Artefacts/non-WBC detections: 31

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 35 | 81.4% |
| Lymphoblast | 3 | 7.0% |
| Eosinophil | 1 | 2.3% |
| Lymphocyte | 1 | 2.3% |
| Monoblast | 1 | 2.3% |
| Monocyte | 1 | 2.3% |
| Myelocyte | 1 | 2.3% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.68). Rationale: learned classifier prediction from aggregated differential features.

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
