# Hematology Report — Case 31

**Specimen:** Peripheral blood smear, 50 fields of view, 277 of 334 detected objects classified as informative WBCs (57 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 67.9% |
| Myelocytes | 16.6% |
| Metamyelocytes | 8.3% |
| Myeloblasts | 5.4% |
| Monocytes | 1.1% |
| Lymphocytes | 0.7% |

**Diagnostic flags:** blasts present.

**Impression:** Chronic Myeloid Leukemia (CML).

Dominant population: Neutrophils (67.9% of informative WBCs). Blast-equivalent burden 5.4%.

**Cohort morphology (n = 188 Neutrophils):** nucleus (100.0%); cytoplasmic vacuoles (99.9%); cytoplasmic basophilia (99.9%); nuclear chromatin (99.5%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 50 FOVs; 277/334 cells classifiable (17.1% artefact); source=agentic_orchestrator; mean detection confidence=0.906.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 50
- Detected cells: 334
- Informative WBCs: 277
- Artefacts/non-WBC detections: 57

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 188 | 67.9% |
| Myelocyte | 46 | 16.6% |
| Metamyelocyte | 23 | 8.3% |
| Myeloblast | 15 | 5.4% |
| Monocyte | 3 | 1.1% |
| Lymphocyte | 2 | 0.7% |

## Agentic Diagnosis
Predicted diagnosis: **CML** (confidence 0.64). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img000_c000` in `31_10_1000_CML.png` bbox=[103.38, 221.62, 174.62, 343.5]: Neutrophil (0.94); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img000_c001` in `31_10_1000_CML.png` bbox=[96.44, 510.75, 168.0, 623.0]: Neutrophil (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img000_c002` in `31_10_1000_CML.png` bbox=[56.94, 47.38, 117.44, 145.0]: Neutrophil (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img000_c003` in `31_10_1000_CML.png` bbox=[449.5, 40.72, 518.0, 147.25]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img000_c004` in `31_10_1000_CML.png` bbox=[608.0, 96.0, 640.0, 204.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img000_c005` in `31_10_1000_CML.png` bbox=[510.0, 3.06, 572.0, 127.69]: Myelocyte (0.86); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img000_c006` in `31_10_1000_CML.png` bbox=[36.34, 156.0, 99.88, 276.0]: Neutrophil (0.83); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c000` in `31_11_1000_CML.png` bbox=[283.75, 128.5, 351.75, 245.0]: Metamyelocyte (0.94); nuclear chromatin; nuclear shape; nucleus; cytoplasm.

> **⚠ Flagged for mandatory human review by the reflection agent.** Reason(s): Low classifier confidence (0.638) and high pct_class_none (17.1%) suggest potential misclassification or noisy data.
