# Hematology Report — Case 21

**Specimen:** Peripheral blood smear, 62 fields of view, 234 of 283 detected objects classified as informative WBCs (49 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Atypical lymphocytes | 91.9% |
| Neutrophils | 6.4% |
| Lymphoblasts | 0.9% |
| Myelocytes | 0.4% |
| Lymphocytes | 0.4% |

**Diagnostic flags:** blasts present.

**Impression:** Chronic Lymphocytic Leukemia (CLL).

Dominant population: Atypical lymphocytes (91.9% of informative WBCs). Blast-equivalent burden 0.9%.

**Cohort morphology (n = 215 Atypical lymphocytes):** nucleus (98.0%); nuclear shape (90.3%); cytoplasmic basophilia (87.8%); nuclear chromatin (86.4%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 62 FOVs; 234/283 cells classifiable (17.3% artefact); source=agentic_orchestrator; mean detection confidence=0.773.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 62
- Raw detected cells before overlap deduplication: 292
- Deduplicated detected cells: 283
- Informative WBCs: 234
- Artefacts/non-WBC detections: 49

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Atypical lymphocyte | 215 | 91.9% |
| Neutrophil | 15 | 6.4% |
| Lymphoblast | 2 | 0.9% |
| Lymphocyte | 1 | 0.4% |
| Myelocyte | 1 | 0.4% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **CLL** (confidence 0.36). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img004_c000` in `21_14_17_400_CLL.png` bbox=[444.25, 511.75, 495.75, 612.0]: Atypical lymphocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `21_12_66_400_CLL.png` bbox=[114.5, 56.88, 171.25, 166.75]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c000` in `21_13_77_400_CLL.png` bbox=[172.5, 353.0, 236.25, 449.0]: Atypical lymphocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img034_c000` in `21_41_3_400_CLL.png` bbox=[373.5, 106.88, 420.5, 196.38]: Atypical lymphocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img008_c000` in `21_18_21_400_CLL.png` bbox=[0.09, 216.0, 59.91, 354.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img023_c000` in `21_31_41_400_CLL.png` bbox=[105.19, 400.0, 174.75, 470.0]: Atypical lymphocyte (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img047_c000` in `21_54_36_400_CLL.png` bbox=[236.0, 327.25, 302.0, 427.25]: Atypical lymphocyte (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img029_c000` in `21_37_52_400_CLL.png` bbox=[323.5, 394.5, 389.0, 519.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.