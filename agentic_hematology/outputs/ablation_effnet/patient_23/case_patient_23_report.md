# Hematology Report — Case patient_23

**Specimen:** Peripheral blood smear, 59 fields of view, 204 of 228 detected objects classified as informative WBCs (24 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 36.8% |
| Myelocytes | 22.5% |
| Lymphoblasts | 20.6% |
| Neutrophils | 11.8% |
| Monocytes | 3.9% |
| Metamyelocytes | 2.9% |
| Lymphocytes | 1.0% |
| Monoblasts | 0.5% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 57.8% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 75 Myeloblasts):** nucleus (99.2%); nuclear chromatin (96.4%); cytoplasmic vacuoles (90.0%); cytoplasmic basophilia (83.2%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 59 FOVs; 204/228 cells classifiable (10.5% artefact); source=agentic_orchestrator; mean detection confidence=0.7.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 59
- Raw detected cells before overlap deduplication: 289
- Deduplicated detected cells: 228
- Informative WBCs: 204
- Artefacts/non-WBC detections: 24

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 75 | 36.8% |
| Myelocyte | 46 | 22.5% |
| Lymphoblast | 42 | 20.6% |
| Neutrophil | 24 | 11.8% |
| Monocyte | 8 | 3.9% |
| Metamyelocyte | 6 | 2.9% |
| Lymphocyte | 2 | 1.0% |
| Monoblast | 1 | 0.5% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.55). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img037_c000` in `23_45_12_400_APML.png` bbox=[0.0, 389.0, 70.88, 507.0]: Myelocyte (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img023_c000` in `23_31_51_400_APML.png` bbox=[312.0, 188.0, 374.0, 299.0]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img050_c000` in `23_57_88_400_APML.png` bbox=[186.5, 533.0, 246.5, 637.0]: Myelocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img051_c000` in `23_58_58_400_APML.png` bbox=[426.75, 141.5, 494.25, 253.75]: Myelocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img023_c001` in `23_31_51_400_APML.png` bbox=[282.0, 364.0, 345.0, 484.0]: Myeloblast (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img026_c000` in `23_34_56_400_APML.png` bbox=[427.5, 523.0, 496.5, 627.0]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img041_c000` in `23_49_17_400_APML.png` bbox=[570.0, 41.38, 636.0, 133.88]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img029_c000` in `23_37_71_400_APML.png` bbox=[418.5, 318.0, 477.0, 419.5]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.