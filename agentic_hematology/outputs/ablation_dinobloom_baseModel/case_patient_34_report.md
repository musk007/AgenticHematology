# Hematology Report — Case patient_34

**Specimen:** Peripheral blood smear, 39 fields of view, 59 of 70 detected objects classified as informative WBCs (11 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 37.3% |
| Myeloblasts | 28.8% |
| Lymphoblasts | 28.8% |
| Monocytes | 3.4% |
| Metamyelocytes | 1.7% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 57.6% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 22 Neutrophils):** cytoplasmic basophilia (100.0%); nuclear chromatin (100.0%); nucleus (100.0%); cytoplasmic vacuoles (99.1%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 39 FOVs; 59/70 cells classifiable (15.7% artefact); source=agentic_orchestrator; mean detection confidence=0.776.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 39
- Raw detected cells before overlap deduplication: 84
- Deduplicated detected cells: 70
- Informative WBCs: 59
- Artefacts/non-WBC detections: 11

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 22 | 37.3% |
| Lymphoblast | 17 | 28.8% |
| Myeloblast | 17 | 28.8% |
| Monocyte | 2 | 3.4% |
| Metamyelocyte | 1 | 1.7% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.48). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img037_c000` in `34_8_8_400_AML.png` bbox=[208.25, 194.0, 281.5, 322.5]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img034_c000` in `34_5_5_400_AML.png` bbox=[277.0, 17.25, 346.5, 143.0]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img013_c000` in `34_23_27_400_AML.png` bbox=[560.0, 249.62, 640.0, 387.5]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img022_c001` in `34_31_66_400_AML.png` bbox=[299.5, 393.5, 371.5, 493.0]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c000` in `34_13_14_400_AML.png` bbox=[47.62, 282.5, 119.5, 409.5]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img033_c000` in `34_4_3_400_AML.png` bbox=[339.5, 294.0, 409.0, 418.0]: Myeloblast (0.88); nuclear chromatin; nucleus; cytoplasm; cytoplasmic basophilia.
- `img015_c000` in `34_25_29_400_AML.png` bbox=[9.0, 448.0, 79.06, 565.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img023_c000` in `34_32_4_400_AML.png` bbox=[479.5, 258.0, 556.5, 383.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.