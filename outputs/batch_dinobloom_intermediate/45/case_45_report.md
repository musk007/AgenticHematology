# Hematology Report — Case 45

**Specimen:** Peripheral blood smear, 54 fields of view, 241 of 268 detected objects classified as informative WBCs (27 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 49.4% |
| Neutrophils | 24.5% |
| Myeloblasts | 10.8% |
| Lymphocytes | 9.5% |
| Monocytes | 2.9% |
| Eosinophils | 1.7% |
| Myelocytes | 1.2% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 60.2% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 119 Lymphoblasts):** nucleus (84.3%); nuclear chromatin (77.3%); cytoplasmic vacuoles (61.2%); cytoplasmic basophilia (59.9%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 54 FOVs; 241/268 cells classifiable (10.1% artefact); source=agentic_orchestrator; mean detection confidence=0.774.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 54
- Detected cells: 268
- Informative WBCs: 241
- Artefacts/non-WBC detections: 27

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 119 | 49.4% |
| Neutrophil | 59 | 24.5% |
| Myeloblast | 26 | 10.8% |
| Lymphocyte | 23 | 9.5% |
| Monocyte | 7 | 2.9% |
| Eosinophil | 4 | 1.7% |
| Myelocyte | 3 | 1.2% |

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.98). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img000_c000` in `45_10_1000_AML.png` bbox=[367.5, 218.88, 420.5, 319.0]: Lymphoblast (0.66); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c000` in `45_11_1000_AML.png` bbox=[349.25, 414.5, 417.75, 529.5]: Myeloblast (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `45_12_1000_AML.png` bbox=[183.5, 65.75, 243.75, 180.0]: Lymphoblast (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c001` in `45_12_1000_AML.png` bbox=[453.5, 403.5, 517.5, 522.5]: Monocyte (0.78); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c002` in `45_12_1000_AML.png` bbox=[447.5, 180.75, 536.5, 310.25]: Lymphoblast (0.72); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c003` in `45_12_1000_AML.png` bbox=[423.5, 307.5, 472.5, 388.5]: Lymphocyte (0.63); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c000` in `45_13_1000_AML.png` bbox=[383.75, 143.25, 451.75, 262.5]: Neutrophil (0.94); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c001` in `45_13_1000_AML.png` bbox=[216.5, 475.5, 275.5, 579.5]: Lymphoblast (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasm.

> **⚠ Flagged for mandatory human review by the reflection agent.** Reason(s): High blast burden (60.2%) with borderline detection quality and 10.1% non-WBC/None detections warrants review.
