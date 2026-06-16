# Hematology Report — Case 28

**Specimen:** Peripheral blood smear, 59 fields of view, 324 of 358 detected objects classified as informative WBCs (34 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 64.5% |
| Myelocytes | 14.8% |
| Myeloblasts | 7.4% |
| Metamyelocytes | 7.4% |
| Lymphocytes | 2.5% |
| Monocytes | 2.2% |
| Basophils | 0.9% |
| Eosinophils | 0.3% |

**Diagnostic flags:** blasts present.

**Impression:** Chronic Myeloid Leukemia (CML).

Dominant population: Neutrophils (64.5% of informative WBCs). Blast-equivalent burden 7.4%.

**Cohort morphology (n = 209 Neutrophils):** nucleus (100.0%); cytoplasmic vacuoles (99.8%); cytoplasmic basophilia (99.7%); nuclear chromatin (98.0%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 59 FOVs; 324/358 cells classifiable (9.5% artefact); source=agentic_orchestrator; mean detection confidence=0.751.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 59
- Raw detected cells before overlap deduplication: 402
- Deduplicated detected cells: 358
- Informative WBCs: 324
- Artefacts/non-WBC detections: 34

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 209 | 64.5% |
| Myelocyte | 48 | 14.8% |
| Metamyelocyte | 24 | 7.4% |
| Myeloblast | 24 | 7.4% |
| Lymphocyte | 8 | 2.5% |
| Monocyte | 7 | 2.2% |
| Basophil | 3 | 0.9% |
| Eosinophil | 1 | 0.3% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **CML** (confidence 0.67). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img037_c000` in `28_45_21_400_CML.png` bbox=[330.5, 326.0, 394.5, 437.0]: Myelocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img033_c000` in `28_41_11_400_CML.png` bbox=[104.06, 410.5, 173.0, 508.5]: Myelocyte (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img010_c000` in `28_1_109_400_CML.png` bbox=[421.5, 249.0, 494.0, 360.0]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img024_c000` in `28_33_102_400_CML.png` bbox=[255.75, 205.5, 319.75, 322.0]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img024_c001` in `28_33_102_400_CML.png` bbox=[510.5, 494.5, 569.5, 597.5]: Metamyelocyte (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img042_c000` in `28_4_3_400_CML.png` bbox=[545.0, 426.0, 622.0, 527.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c000` in `28_14_20_400_CML.png` bbox=[541.0, 462.0, 607.0, 584.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img007_c000` in `28_17_100_400_CML.png` bbox=[370.5, 394.0, 439.5, 519.0]: Metamyelocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.