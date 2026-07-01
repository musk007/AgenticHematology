# Hematology Report — Case 34

**Specimen:** Peripheral blood smear, 44 fields of view, 80 of 96 detected objects classified as informative WBCs (16 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 37.5% |
| Lymphoblasts | 30.0% |
| Myeloblasts | 23.8% |
| Monocytes | 6.2% |
| Lymphocytes | 1.2% |
| Eosinophils | 1.2% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 53.8% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 30 Neutrophils):** nuclear shape (99.8%); cytoplasmic basophilia (99.2%); nucleus (98.8%); nuclear chromatin (98.3%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 44 FOVs; 80/96 cells classifiable (16.7% artefact); source=agentic_orchestrator; mean detection confidence=0.821.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 44
- Detected cells: 96
- Informative WBCs: 80
- Artefacts/non-WBC detections: 16

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 30 | 37.5% |
| Lymphoblast | 24 | 30.0% |
| Myeloblast | 19 | 23.8% |
| Monocyte | 5 | 6.2% |
| Eosinophil | 1 | 1.2% |
| Lymphocyte | 1 | 1.2% |

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.91). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img000_c000` in `34_10_1000_AML.png` bbox=[208.0, 204.5, 275.0, 299.5]: Myeloblast (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img000_c001` in `34_10_1000_AML.png` bbox=[378.0, 387.0, 450.0, 500.0]: Neutrophil (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c000` in `34_11_1000_AML.png` bbox=[423.0, 228.75, 506.0, 369.75]: Neutrophil (0.94); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `34_12_1000_AML.png` bbox=[303.0, 339.5, 372.0, 466.5]: Lymphoblast (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c000` in `34_13_1000_AML.png` bbox=[48.81, 284.5, 119.56, 413.5]: Neutrophil (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c000` in `34_14_1000_AML.png` bbox=[561.5, 512.0, 625.5, 615.0]: Monocyte (0.62); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img005_c000` in `34_16_1000_AML.png` bbox=[334.5, 447.5, 406.5, 562.5]: Lymphoblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img005_c001` in `34_16_1000_AML.png` bbox=[313.25, 206.25, 374.75, 319.75]: Myeloblast (0.84); nuclear chromatin; nuclear shape; nucleus; cytoplasm.

> **⚠ Flagged for mandatory human review by the reflection agent.** Reason(s): High blast burden (53.8%) with low informative cell count (80) and 16.7% non-WBC detections suggests borderline quality.
