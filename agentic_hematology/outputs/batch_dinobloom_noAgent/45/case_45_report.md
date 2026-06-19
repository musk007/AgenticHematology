# Hematology Report — Case 45

**Specimen:** Peripheral blood smear, 54 fields of view, 176 of 227 detected objects classified as informative WBCs (51 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 42.6% |
| Neutrophils | 29.0% |
| Lymphocytes | 15.3% |
| Myeloblasts | 7.4% |
| Monocytes | 2.8% |
| Promonocytes | 1.1% |
| Myelocytes | 1.1% |
| Eosinophils | 0.6% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 50.0% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 75 Lymphoblasts):** nucleus (93.7%); nuclear chromatin (82.5%); cytoplasmic vacuoles (61.8%); cytoplasmic basophilia (60.5%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 54 FOVs; 176/227 cells classifiable (22.5% artefact); source=agentic_orchestrator; mean detection confidence=0.691.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 54
- Raw detected cells before overlap deduplication: 274
- Deduplicated detected cells: 227
- Informative WBCs: 176
- Artefacts/non-WBC detections: 51

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 75 | 42.6% |
| Neutrophil | 51 | 29.0% |
| Lymphocyte | 27 | 15.3% |
| Myeloblast | 13 | 7.4% |
| Monocyte | 5 | 2.8% |
| Myelocyte | 2 | 1.1% |
| Promonocyte | 2 | 1.1% |
| Eosinophil | 1 | 0.6% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.62). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img002_c000` in `45_12_13_400_AML.png` bbox=[449.0, 407.0, 518.5, 524.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img021_c000` in `45_2_5_400_AML.png` bbox=[533.0, 373.0, 601.0, 486.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c000` in `45_13_68_400_AML.png` bbox=[383.0, 150.0, 448.0, 259.5]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img053_c000` in `45_9_11_400_AML.png` bbox=[582.0, 222.5, 640.0, 333.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c001` in `45_12_13_400_AML.png` bbox=[425.0, 309.75, 472.5, 393.75]: Lymphocyte (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img023_c000` in `45_31_71_400_AML.png` bbox=[94.75, 247.5, 155.75, 362.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img022_c000` in `45_30_71_400_AML.png` bbox=[361.5, 484.0, 421.5, 598.0]: Neutrophil (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img014_c001` in `45_23_20_400_AML.png` bbox=[588.0, 99.44, 640.0, 196.0]: Lymphoblast (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.