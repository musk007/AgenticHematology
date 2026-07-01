# Hematology Report — Case 40

**Specimen:** Peripheral blood smear, 50 fields of view, 109 of 142 detected objects classified as informative WBCs (33 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 35.8% |
| Eosinophils | 24.8% |
| Lymphoblasts | 12.8% |
| Monocytes | 10.1% |
| Promonocytes | 4.6% |
| Monoblasts | 4.6% |
| Lymphocytes | 3.7% |
| Myeloblasts | 2.8% |
| Myelocytes | 0.9% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 20.2% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 39 Neutrophils):** cytoplasmic basophilia (99.9%); nucleus (99.9%); cytoplasmic vacuoles (99.6%); nuclear chromatin (99.5%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 50 FOVs; 109/142 cells classifiable (23.2% artefact); source=agentic_orchestrator; mean detection confidence=0.746.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 50
- Detected cells: 142
- Informative WBCs: 109
- Artefacts/non-WBC detections: 33

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 39 | 35.8% |
| Eosinophil | 27 | 24.8% |
| Lymphoblast | 14 | 12.8% |
| Monocyte | 11 | 10.1% |
| Monoblast | 5 | 4.6% |
| Promonocyte | 5 | 4.6% |
| Lymphocyte | 4 | 3.7% |
| Myeloblast | 3 | 2.8% |
| Myelocyte | 1 | 0.9% |

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.56). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img000_c000` in `40_10_1000_AML.png` bbox=[124.06, 265.0, 213.5, 409.5]: Eosinophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c000` in `40_11_1000_AML.png` bbox=[204.5, 279.25, 278.5, 397.25]: Eosinophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `40_12_1000_AML.png` bbox=[488.0, 233.75, 555.0, 345.75]: Neutrophil (0.94); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c000` in `40_13_1000_AML.png` bbox=[412.5, 343.0, 486.5, 482.0]: Monocyte (0.76); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c001` in `40_13_1000_AML.png` bbox=[182.0, 198.0, 229.5, 280.0]: Lymphoblast (0.55); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c002` in `40_13_1000_AML.png` bbox=[412.5, 343.5, 485.0, 478.5]: Eosinophil (0.31); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c000` in `40_14_1000_AML.png` bbox=[67.38, 397.5, 141.0, 517.5]: Neutrophil (0.94); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c001` in `40_14_1000_AML.png` bbox=[444.5, 168.5, 494.5, 241.0]: Lymphoblast (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.

> **⚠ Flagged for mandatory human review by the reflection agent.** Reason(s): Low classifier confidence and high non-WBC fraction suggest diagnostic uncertainty.
