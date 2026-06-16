# Hematology Report — Case 18

**Specimen:** Peripheral blood smear, 27 fields of view, 43 of 43 detected objects classified as informative WBCs (0 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 76.7% |
| Neutrophils | 16.3% |
| Lymphocytes | 4.7% |
| Eosinophils | 2.3% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 76.74% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 27 FOVs; 43/43 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 27
- Deduplicated detected cells: 43
- Informative WBCs: 43
- Artefacts/non-WBC detections: 0

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 33 | 76.7% |
| Neutrophil | 7 | 16.3% |
| Lymphocyte | 2 | 4.7% |
| Eosinophil | 1 | 2.3% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.90). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** ALL
- **Confidence:** 0.896
- **Ground truth (file label):** ALL

### Top contributing features (SHAP)

- lymphoblast differential % (supports, SHAP=+2.0170)
- slight cytoplasmic basophilia attribute % (supports, SHAP=+0.2055)
- scanty cytoplasm attribute % (supports, SHAP=+0.0858)
- myeloblast differential % (supports, SHAP=+0.0712)
- identified WBC cell count (supports, SHAP=+0.0486)
