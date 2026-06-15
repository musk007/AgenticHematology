# Hematology Report — Case patient_15

**Specimen:** Peripheral blood smear, 59 fields of view, 89 of 191 detected objects classified as informative WBCs (102 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 67.4% |
| Monoblasts | 14.6% |
| Neutrophils | 5.6% |
| Lymphocytes | 5.6% |
| Lymphoblasts | 3.4% |
| Eosinophils | 1.1% |
| Promonocytes | 1.1% |
| Monocytes | 1.1% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 85.4% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 60 Myeloblasts):** nucleus (97.1%); nuclear chromatin (95.4%); cytoplasm (92.9%); cytoplasmic vacuoles (90.6%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 59 FOVs; 89/191 cells classifiable (53.4% artefact); source=agentic_orchestrator; mean detection confidence=0.682.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 59
- Raw detected cells before overlap deduplication: 236
- Deduplicated detected cells: 191
- Informative WBCs: 89
- Artefacts/non-WBC detections: 102

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 60 | 67.4% |
| Monoblast | 13 | 14.6% |
| Lymphocyte | 5 | 5.6% |
| Neutrophil | 5 | 5.6% |
| Lymphoblast | 3 | 3.4% |
| Eosinophil | 1 | 1.1% |
| Monocyte | 1 | 1.1% |
| Promonocyte | 1 | 1.1% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.91). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img032_c001` in `15_40_68_400_AML.png` bbox=[344.5, 219.12, 408.5, 330.0]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img033_c000` in `15_41_69_400_AML.png` bbox=[456.5, 137.38, 529.0, 247.38]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img048_c000` in `15_55_96_400_AML.png` bbox=[155.5, 414.0, 223.0, 515.0]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img021_c000` in `15_30_49_400_AML.png` bbox=[553.0, 223.5, 635.0, 373.0]: Monoblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img036_c000` in `15_44_78_400_AML.png` bbox=[132.25, 261.0, 211.25, 403.0]: Monoblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img014_c001` in `15_24_33_400_AML.png` bbox=[188.0, 514.0, 234.5, 585.0]: Lymphocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img049_c000` in `15_56_30_400_AML.png` bbox=[321.0, 429.0, 389.0, 534.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img043_c000` in `15_50_6_400_AML.png` bbox=[361.75, 540.0, 428.75, 640.0]: Monoblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.