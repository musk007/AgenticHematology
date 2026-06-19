# Hematology Report — Case 18

**Specimen:** Peripheral blood smear, 27 fields of view, 42 of 43 detected objects classified as informative WBCs (1 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 71.4% |
| Neutrophils | 16.7% |
| Lymphocytes | 9.5% |
| Eosinophils | 2.4% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 71.4% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 30 Lymphoblasts):** nucleus (87.7%); nuclear chromatin (78.2%); cytoplasmic basophilia (73.6%); cytoplasm (63.5%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 27 FOVs; 42/43 cells classifiable (2.3% artefact); source=agentic_orchestrator; mean detection confidence=0.797.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 27
- Raw detected cells before overlap deduplication: 43
- Deduplicated detected cells: 43
- Informative WBCs: 42
- Artefacts/non-WBC detections: 1

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 30 | 71.4% |
| Neutrophil | 7 | 16.7% |
| Lymphocyte | 4 | 9.5% |
| Eosinophil | 1 | 2.4% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.55). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img010_c000` in `18_23_55_400_ALL.png` bbox=[355.5, 355.0, 415.5, 466.0]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c000` in `18_16_31_400_ALL.png` bbox=[0.12, 94.25, 60.53, 197.75]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img007_c000` in `18_19_40_400_ALL.png` bbox=[472.5, 491.25, 534.5, 593.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img006_c000` in `18_18_37_400_ALL.png` bbox=[199.5, 449.0, 254.5, 549.5]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img022_c000` in `18_37_72_400_ALL.png` bbox=[564.0, 404.75, 620.0, 503.25]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img013_c000` in `18_26_63_400_ALL.png` bbox=[475.5, 344.0, 541.5, 456.0]: Eosinophil (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img021_c000` in `18_36_71_400_ALL.png` bbox=[74.38, 376.25, 139.38, 485.75]: Neutrophil (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img026_c000` in `18_8_64_400_ALL.png` bbox=[397.0, 451.5, 448.0, 550.5]: Lymphoblast (0.85); nuclear chromatin; nuclear shape; nucleus; cytoplasm.