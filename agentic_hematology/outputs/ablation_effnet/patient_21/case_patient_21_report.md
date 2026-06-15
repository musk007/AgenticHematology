# Hematology Report — Case patient_21

**Specimen:** Peripheral blood smear, 62 fields of view, 238 of 281 detected objects classified as informative WBCs (43 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Atypical lymphocytes | 92.9% |
| Neutrophils | 5.9% |
| Lymphoblasts | 0.8% |
| Myelocytes | 0.4% |

**Diagnostic flags:** blasts present.

**Impression:** Chronic Lymphocytic Leukemia (CLL).

Dominant population: Atypical lymphocytes (92.9% of informative WBCs). Blast-equivalent burden 0.8%.

**Cohort morphology (n = 221 Atypical lymphocytes):** nucleus (99.1%); nuclear chromatin (93.4%); cytoplasmic basophilia (92.0%); nuclear shape (85.7%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 62 FOVs; 238/281 cells classifiable (15.3% artefact); source=agentic_orchestrator; mean detection confidence=0.793.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 62
- Raw detected cells before overlap deduplication: 288
- Deduplicated detected cells: 281
- Informative WBCs: 238
- Artefacts/non-WBC detections: 43

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Atypical lymphocyte | 221 | 92.9% |
| Neutrophil | 14 | 5.9% |
| Lymphoblast | 2 | 0.8% |
| Myelocyte | 1 | 0.4% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **CLL** (confidence 0.49). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img002_c000` in `21_12_66_400_CLL.png` bbox=[113.88, 56.78, 170.12, 166.25]: Neutrophil (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c000` in `21_14_17_400_CLL.png` bbox=[444.0, 511.0, 497.0, 614.0]: Atypical lymphocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img018_c000` in `21_27_72_400_CLL.png` bbox=[185.0, 353.0, 249.75, 454.5]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img016_c000` in `21_25_71_400_CLL.png` bbox=[78.38, 339.75, 147.62, 430.75]: Atypical lymphocyte (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img029_c000` in `21_37_52_400_CLL.png` bbox=[35.5, 11.06, 107.0, 126.94]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img029_c001` in `21_37_52_400_CLL.png` bbox=[324.5, 395.0, 389.5, 521.0]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img034_c000` in `21_41_3_400_CLL.png` bbox=[373.0, 107.62, 421.0, 196.88]: Atypical lymphocyte (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img023_c000` in `21_31_41_400_CLL.png` bbox=[105.25, 401.0, 172.75, 467.5]: Atypical lymphocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.