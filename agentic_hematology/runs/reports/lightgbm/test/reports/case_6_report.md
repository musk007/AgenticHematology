# Hematology Report — Case 6

**Specimen:** Peripheral blood smear, 55 fields of view, 77 of 92 detected objects classified as informative WBCs (15 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 58.4% |
| Eosinophils | 19.5% |
| Lymphocytes | 19.5% |
| Neutrophils | 1.3% |
| Monocytes | 1.3% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 58.44% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 55 FOVs; 77/92 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 55
- Deduplicated detected cells: 92
- Informative WBCs: 77
- Artefacts/non-WBC detections: 15

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 45 | 58.4% |
| Eosinophil | 15 | 19.5% |
| Lymphocyte | 15 | 19.5% |
| Monocyte | 1 | 1.3% |
| Neutrophil | 1 | 1.3% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 1.00). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** ALL
- **Confidence:** 1.000
- **Ground truth (file label):** ALL

### Top contributing features (SHAP)

- lymphoblast differential % (supports, SHAP=+5.2612)
- scanty cytoplasm attribute % (supports, SHAP=+0.8429)
- identified WBC cell count (supports, SHAP=+0.5847)
- slight cytoplasmic basophilia attribute % (supports, SHAP=+0.1541)
- blast pool % of WBC (opposes, SHAP=-0.0671)
