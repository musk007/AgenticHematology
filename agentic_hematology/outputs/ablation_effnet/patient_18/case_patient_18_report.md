# Hematology Report — Case patient_18

**Specimen:** Peripheral blood smear, 27 fields of view, 42 of 43 detected objects classified as informative WBCs (1 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 76.2% |
| Neutrophils | 16.7% |
| Lymphocytes | 4.8% |
| Eosinophils | 2.4% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 76.2% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 32 Lymphoblasts):** nuclear chromatin (91.6%); nucleus (84.4%); cytoplasmic basophilia (80.4%); cytoplasm (71.3%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 27 FOVs; 42/43 cells classifiable (2.3% artefact); source=agentic_orchestrator; mean detection confidence=0.836.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 27
- Raw detected cells before overlap deduplication: 45
- Deduplicated detected cells: 43
- Informative WBCs: 42
- Artefacts/non-WBC detections: 1

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 32 | 76.2% |
| Neutrophil | 7 | 16.7% |
| Lymphocyte | 2 | 4.8% |
| Eosinophil | 1 | 2.4% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.90). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img013_c000` in `18_26_63_400_ALL.png` bbox=[477.0, 345.5, 540.0, 454.0]: Eosinophil (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img007_c000` in `18_19_40_400_ALL.png` bbox=[471.5, 489.75, 534.5, 590.0]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img010_c000` in `18_23_55_400_ALL.png` bbox=[355.5, 354.75, 415.5, 464.25]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c000` in `18_16_31_400_ALL.png` bbox=[0.19, 96.0, 59.62, 198.75]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img006_c001` in `18_18_37_400_ALL.png` bbox=[200.5, 448.5, 254.0, 550.0]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img023_c000` in `18_4_14_400_ALL.png` bbox=[44.38, 302.75, 106.38, 418.75]: Lymphoblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img022_c000` in `18_37_72_400_ALL.png` bbox=[565.0, 406.0, 619.0, 503.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c000` in `18_11_21_400_ALL.png` bbox=[570.0, 520.0, 620.0, 590.0]: Lymphocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.