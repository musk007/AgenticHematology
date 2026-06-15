# Hematology Report — Case patient_28

**Specimen:** Peripheral blood smear, 59 fields of view, 323 of 355 detected objects classified as informative WBCs (32 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 63.5% |
| Myelocytes | 14.6% |
| Myeloblasts | 8.0% |
| Metamyelocytes | 7.1% |
| Monocytes | 2.8% |
| Basophils | 1.9% |
| Lymphocytes | 1.5% |
| Eosinophils | 0.6% |

**Diagnostic flags:** blasts present.

**Impression:** Chronic Myeloid Leukemia (CML).

Dominant population: Neutrophils (63.5% of informative WBCs). Blast-equivalent burden 8.0%.

**Cohort morphology (n = 205 Neutrophils):** nucleus (99.1%); cytoplasmic basophilia (98.5%); nuclear shape (95.5%); cytoplasmic vacuoles (94.9%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 59 FOVs; 323/355 cells classifiable (9.0% artefact); source=agentic_orchestrator; mean detection confidence=0.771.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 59
- Raw detected cells before overlap deduplication: 395
- Deduplicated detected cells: 355
- Informative WBCs: 323
- Artefacts/non-WBC detections: 32

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 205 | 63.5% |
| Myelocyte | 47 | 14.6% |
| Myeloblast | 26 | 8.0% |
| Metamyelocyte | 23 | 7.1% |
| Monocyte | 9 | 2.8% |
| Basophil | 6 | 1.9% |
| Lymphocyte | 5 | 1.5% |
| Eosinophil | 2 | 0.6% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **CML** (confidence 0.70). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img005_c000` in `28_15_24_400_CML.png` bbox=[246.5, 253.75, 310.0, 373.25]: Myelocyte (0.96); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img033_c000` in `28_41_11_400_CML.png` bbox=[104.88, 414.0, 171.62, 508.5]: Myelocyte (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img024_c000` in `28_33_102_400_CML.png` bbox=[511.0, 494.25, 569.0, 598.0]: Metamyelocyte (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img037_c000` in `28_45_21_400_CML.png` bbox=[329.25, 328.0, 393.25, 438.0]: Myelocyte (0.92); nuclear chromatin; nucleus; cytoplasm; cytoplasmic basophilia.
- `img007_c000` in `28_17_100_400_CML.png` bbox=[371.75, 393.5, 439.25, 518.5]: Metamyelocyte (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img024_c001` in `28_33_102_400_CML.png` bbox=[256.0, 207.38, 320.0, 320.5]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img047_c000` in `28_54_49_400_CML.png` bbox=[217.25, 346.5, 292.75, 473.5]: Metamyelocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img004_c000` in `28_14_20_400_CML.png` bbox=[310.0, 526.0, 386.0, 640.0]: Myelocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.