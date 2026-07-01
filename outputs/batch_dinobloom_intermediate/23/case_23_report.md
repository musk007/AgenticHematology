# Hematology Report — Case 23

**Specimen:** Peripheral blood smear, 60 fields of view, 234 of 252 detected objects classified as informative WBCs (18 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 52.1% |
| Lymphoblasts | 20.9% |
| Neutrophils | 8.5% |
| Myelocytes | 8.5% |
| Monocytes | 4.7% |
| Lymphocytes | 3.8% |
| Eosinophils | 1.3% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 73.1% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 122 Myeloblasts):** nucleus (95.7%); nuclear chromatin (94.3%); cytoplasmic vacuoles (93.0%); cytoplasmic basophilia (84.1%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 60 FOVs; 234/252 cells classifiable (7.1% artefact); source=agentic_orchestrator; mean detection confidence=0.768.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 60
- Detected cells: 252
- Informative WBCs: 234
- Artefacts/non-WBC detections: 18

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 122 | 52.1% |
| Lymphoblast | 49 | 20.9% |
| Myelocyte | 20 | 8.5% |
| Neutrophil | 20 | 8.5% |
| Monocyte | 11 | 4.7% |
| Lymphocyte | 9 | 3.8% |
| Eosinophil | 3 | 1.3% |

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 1.00). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img000_c000` in `23_10_1000_APML.png` bbox=[411.0, 182.25, 474.0, 283.0]: Lymphoblast (0.83); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img000_c001` in `23_10_1000_APML.png` bbox=[351.25, 274.25, 425.75, 397.25]: Lymphoblast (0.77); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c000` in `23_11_1000_APML.png` bbox=[321.0, 418.0, 385.0, 521.0]: Myeloblast (0.94); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c001` in `23_11_1000_APML.png` bbox=[347.5, 343.5, 423.0, 448.5]: Myeloblast (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c002` in `23_11_1000_APML.png` bbox=[203.0, 406.5, 274.5, 510.5]: Myeloblast (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c003` in `23_11_1000_APML.png` bbox=[197.0, 322.5, 258.5, 412.5]: Myeloblast (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `23_12_1000_APML.png` bbox=[379.5, 213.5, 432.5, 311.0]: Neutrophil (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c001` in `23_12_1000_APML.png` bbox=[563.0, 465.0, 615.0, 556.0]: Neutrophil (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.