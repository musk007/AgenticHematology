# Hematology Report — Case patient_40

**Specimen:** Peripheral blood smear, 50 fields of view, 63 of 111 detected objects classified as informative WBCs (48 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 58.7% |
| Lymphoblasts | 9.5% |
| Lymphocytes | 7.9% |
| Eosinophils | 7.9% |
| Monoblasts | 4.8% |
| Monocytes | 4.8% |
| Myeloblasts | 4.8% |
| Myelocytes | 1.6% |

**Diagnostic flags:** blasts present.

**Impression:** Acute Myeloid Leukemia (AML).

Dominant population: Neutrophils (58.7% of informative WBCs). Blast-equivalent burden 19.0%.

**Cohort morphology (n = 37 Neutrophils):** cytoplasmic basophilia (100.0%); nuclear chromatin (100.0%); nucleus (98.4%); cytoplasmic vacuoles (96.2%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 50 FOVs; 63/111 cells classifiable (43.2% artefact); source=agentic_orchestrator; mean detection confidence=0.736.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 50
- Raw detected cells before overlap deduplication: 132
- Deduplicated detected cells: 111
- Informative WBCs: 63
- Artefacts/non-WBC detections: 48

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 37 | 58.7% |
| Lymphoblast | 6 | 9.5% |
| Eosinophil | 5 | 7.9% |
| Lymphocyte | 5 | 7.9% |
| Monoblast | 3 | 4.8% |
| Monocyte | 3 | 4.8% |
| Myeloblast | 3 | 4.8% |
| Myelocyte | 1 | 1.6% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.59). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img049_c000` in `40_9_12_400_AML.png` bbox=[568.0, 447.5, 622.0, 547.5]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img044_c000` in `40_50_45_400_AML.png` bbox=[437.75, 35.59, 503.75, 153.38]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img004_c000` in `40_14_20_400_AML.png` bbox=[55.25, 476.0, 127.12, 601.0]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img042_c000` in `40_49_45_400_AML.png` bbox=[54.47, 292.25, 135.0, 413.25]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img038_c000` in `40_45_29_400_AML.png` bbox=[239.75, 0.0, 313.75, 115.69]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img013_c000` in `40_22_27_400_AML.png` bbox=[243.0, 221.0, 313.0, 335.0]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img042_c001` in `40_49_45_400_AML.png` bbox=[71.12, 179.0, 145.88, 299.75]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img013_c001` in `40_22_27_400_AML.png` bbox=[310.0, 183.25, 356.0, 264.75]: Lymphocyte (0.88); nuclear shape; nucleus.