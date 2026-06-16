# Hematology Report — Case 4

**Specimen:** Peripheral blood smear, 52 fields of view, 96 of 147 detected objects classified as informative WBCs (51 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 41.7% |
| Neutrophils | 38.5% |
| Lymphocytes | 7.3% |
| Myelocytes | 6.2% |
| Eosinophils | 5.2% |
| Monocytes | 1.0% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 41.67% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 52 FOVs; 96/147 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 52
- Deduplicated detected cells: 147
- Informative WBCs: 96
- Artefacts/non-WBC detections: 51

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 40 | 41.7% |
| Neutrophil | 37 | 38.5% |
| Lymphocyte | 7 | 7.3% |
| Myelocyte | 6 | 6.2% |
| Eosinophil | 5 | 5.2% |
| Monocyte | 1 | 1.0% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.92). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** ALL
- **Confidence:** 0.921
- **Ground truth (file label):** ALL

### Top contributing features (SHAP)

- lymphoblast differential % (supports, SHAP=+2.0170)
- slight cytoplasmic basophilia attribute % (supports, SHAP=+0.2055)
- scanty cytoplasm attribute % (supports, SHAP=+0.0858)
- myeloblast differential % (supports, SHAP=+0.0712)
- identified WBC cell count (supports, SHAP=+0.0486)
