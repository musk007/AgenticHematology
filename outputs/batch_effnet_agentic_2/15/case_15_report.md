# Hematology Report — Case 15

**Specimen:** Peripheral blood smear, 59 fields of view, 133 of 219 detected objects classified as informative WBCs (86 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 60.2% |
| Lymphoblasts | 15.0% |
| Monoblasts | 12.8% |
| Neutrophils | 6.0% |
| Lymphocytes | 3.0% |
| Promonocytes | 1.5% |
| Eosinophils | 0.8% |
| Monocytes | 0.8% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 88.0% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 80 Myeloblasts):** nuclear chromatin (95.5%); nucleus (94.3%); cytoplasm (93.0%); cytoplasmic basophilia (91.8%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 59 FOVs; 133/219 cells classifiable (39.3% artefact); source=agentic_orchestrator; mean detection confidence=0.74.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 59
- Detected cells: 219
- Informative WBCs: 133
- Artefacts/non-WBC detections: 86

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 80 | 60.2% |
| Lymphoblast | 20 | 15.0% |
| Monoblast | 17 | 12.8% |
| Neutrophil | 8 | 6.0% |
| Lymphocyte | 4 | 3.0% |
| Promonocyte | 2 | 1.5% |
| Eosinophil | 1 | 0.8% |
| Monocyte | 1 | 0.8% |

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.86). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img000_c000` in `15_10_1000_AML.png` bbox=[40.62, 119.0, 115.38, 254.5]: Myeloblast (0.94); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `15_12_1000_AML.png` bbox=[467.5, 104.75, 524.5, 197.5]: Lymphoblast (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c001` in `15_12_1000_AML.png` bbox=[0.0, 450.5, 41.62, 549.0]: Myeloblast (0.74); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c002` in `15_12_1000_AML.png` bbox=[0.0, 452.0, 41.59, 549.0]: Lymphoblast (0.58); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c003` in `15_12_1000_AML.png` bbox=[250.88, 503.0, 329.0, 639.0]: Myeloblast (0.48); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c000` in `15_14_1000_AML.png` bbox=[576.0, 455.5, 640.0, 577.5]: Neutrophil (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c001` in `15_14_1000_AML.png` bbox=[34.25, 384.0, 112.62, 518.0]: Myeloblast (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c003` in `15_14_1000_AML.png` bbox=[67.12, 105.0, 136.38, 222.75]: Myeloblast (0.85); nuclear chromatin; nuclear shape; nucleus; cytoplasm.

> **⚠ Flagged for mandatory human review by the reflection agent.** Reason(s): High pct_class_none and low mean detection confidence suggest data quality issues despite high blast burden.
