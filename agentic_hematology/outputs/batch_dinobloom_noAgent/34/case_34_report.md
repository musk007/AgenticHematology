# Hematology Report — Case 34

**Specimen:** Peripheral blood smear, 39 fields of view, 59 of 70 detected objects classified as informative WBCs (11 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 39.0% |
| Myeloblasts | 30.5% |
| Lymphoblasts | 27.1% |
| Monocytes | 3.4% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 57.6% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 23 Neutrophils):** cytoplasmic vacuoles (100.0%); nucleus (100.0%); cytoplasmic basophilia (99.9%); nuclear chromatin (99.9%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 39 FOVs; 59/70 cells classifiable (15.7% artefact); source=agentic_orchestrator; mean detection confidence=0.756.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 39
- Raw detected cells before overlap deduplication: 85
- Deduplicated detected cells: 70
- Informative WBCs: 59
- Artefacts/non-WBC detections: 11

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 23 | 39.0% |
| Myeloblast | 18 | 30.5% |
| Lymphoblast | 16 | 27.1% |
| Monocyte | 2 | 3.4% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.82). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img034_c000` in `34_5_5_400_AML.png` bbox=[276.5, 16.62, 346.5, 144.12]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img037_c000` in `34_8_8_400_AML.png` bbox=[209.0, 193.62, 282.75, 322.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img031_c000` in `34_44_33_400_AML.png` bbox=[571.0, 279.0, 640.0, 403.0]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c000` in `34_13_14_400_AML.png` bbox=[47.09, 282.5, 119.88, 412.0]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img013_c000` in `34_23_27_400_AML.png` bbox=[559.0, 249.5, 640.0, 387.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img020_c000` in `34_2_1_400_AML.png` bbox=[19.05, 141.5, 79.56, 250.5]: Myeloblast (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img033_c000` in `34_4_3_400_AML.png` bbox=[229.0, 132.75, 300.0, 253.75]: Myeloblast (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img007_c000` in `34_18_24_400_AML.png` bbox=[219.75, 419.5, 298.25, 547.0]: Neutrophil (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.