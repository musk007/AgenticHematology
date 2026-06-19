# Hematology Report — Case 15

**Specimen:** Peripheral blood smear, 59 fields of view, 78 of 191 detected objects classified as informative WBCs (113 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 61.5% |
| Lymphocytes | 10.3% |
| Lymphoblasts | 10.3% |
| Monoblasts | 6.4% |
| Neutrophils | 6.4% |
| Eosinophils | 2.6% |
| Monocytes | 1.3% |
| Myelocytes | 1.3% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 78.2% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 48 Myeloblasts):** nucleus (95.3%); nuclear chromatin (89.3%); cytoplasmic vacuoles (80.9%); cytoplasmic basophilia (79.7%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 59 FOVs; 78/191 cells classifiable (59.2% artefact); source=agentic_orchestrator; mean detection confidence=0.655.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 59
- Raw detected cells before overlap deduplication: 229
- Deduplicated detected cells: 191
- Informative WBCs: 78
- Artefacts/non-WBC detections: 113

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 48 | 61.5% |
| Lymphoblast | 8 | 10.3% |
| Lymphocyte | 8 | 10.3% |
| Monoblast | 5 | 6.4% |
| Neutrophil | 5 | 6.4% |
| Eosinophil | 2 | 2.6% |
| Monocyte | 1 | 1.3% |
| Myelocyte | 1 | 1.3% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.88). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img032_c000` in `15_40_68_400_AML.png` bbox=[343.5, 218.62, 410.5, 329.5]: Myeloblast (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img043_c000` in `15_50_6_400_AML.png` bbox=[361.0, 538.0, 427.0, 640.0]: Monoblast (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c001` in `15_14_16_400_AML.png` bbox=[576.0, 463.75, 640.0, 578.0]: Neutrophil (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img052_c000` in `15_59_39_400_AML.png` bbox=[581.0, 525.0, 640.0, 633.0]: Myeloblast (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img048_c000` in `15_55_96_400_AML.png` bbox=[155.25, 414.0, 223.75, 516.5]: Neutrophil (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img049_c000` in `15_56_30_400_AML.png` bbox=[320.0, 428.0, 390.0, 533.0]: Neutrophil (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img054_c000` in `15_60_46_400_AML.png` bbox=[15.69, 28.12, 83.25, 141.25]: Myeloblast (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img033_c000` in `15_41_69_400_AML.png` bbox=[456.0, 137.5, 531.0, 247.75]: Myeloblast (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.

> **⚠ Flagged for mandatory human review by the reflection agent.** Reason(s): High pct_class_none and low mean detection confidence suggest unreliable detection quality despite high blast burden.
