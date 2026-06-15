# Hematology Report — Case patient_45

**Specimen:** Peripheral blood smear, 54 fields of view, 176 of 231 detected objects classified as informative WBCs (55 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 45.5% |
| Neutrophils | 25.0% |
| Myeloblasts | 11.4% |
| Lymphocytes | 10.8% |
| Monocytes | 4.0% |
| Eosinophils | 1.7% |
| Myelocytes | 1.1% |
| Promonocytes | 0.6% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 56.8% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 80 Lymphoblasts):** nucleus (93.5%); nuclear chromatin (76.5%); cytoplasmic vacuoles (52.5%); cytoplasmic basophilia (52.2%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 54 FOVs; 176/231 cells classifiable (23.8% artefact); source=agentic_orchestrator; mean detection confidence=0.725.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 54
- Raw detected cells before overlap deduplication: 272
- Deduplicated detected cells: 231
- Informative WBCs: 176
- Artefacts/non-WBC detections: 55

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 80 | 45.5% |
| Neutrophil | 44 | 25.0% |
| Myeloblast | 20 | 11.4% |
| Lymphocyte | 19 | 10.8% |
| Monocyte | 7 | 4.0% |
| Eosinophil | 3 | 1.7% |
| Myelocyte | 2 | 1.1% |
| Promonocyte | 1 | 0.6% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.55). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img003_c000` in `45_13_68_400_AML.png` bbox=[383.75, 152.25, 448.25, 257.75]: Neutrophil (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img013_c000` in `45_22_19_400_AML.png` bbox=[361.0, 141.75, 400.5, 211.25]: Lymphocyte (0.90); nuclear shape; nucleus.
- `img023_c000` in `45_31_71_400_AML.png` bbox=[95.38, 247.12, 155.0, 363.0]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img021_c000` in `45_2_5_400_AML.png` bbox=[533.0, 372.0, 601.0, 486.0]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img047_c000` in `45_57_78_400_AML.png` bbox=[469.0, 302.25, 512.0, 397.75]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img033_c000` in `45_43_29_400_AML.png` bbox=[11.75, 340.5, 73.62, 453.5]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img015_c001` in `45_24_21_400_AML.png` bbox=[168.0, 217.5, 207.5, 283.5]: Lymphocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img048_c000` in `45_59_79_400_AML.png` bbox=[465.5, 498.0, 523.5, 595.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.