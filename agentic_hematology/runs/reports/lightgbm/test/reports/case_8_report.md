# Hematology Report — Case 8

**Specimen:** Peripheral blood smear, 55 fields of view, 92 of 116 detected objects classified as informative WBCs (24 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 80.4% |
| Neutrophils | 9.8% |
| Lymphocytes | 6.5% |
| Monocytes | 2.2% |
| Myelocytes | 1.1% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 80.43% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 55 FOVs; 92/116 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 55
- Deduplicated detected cells: 116
- Informative WBCs: 92
- Artefacts/non-WBC detections: 24

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 74 | 80.4% |
| Neutrophil | 9 | 9.8% |
| Lymphocyte | 6 | 6.5% |
| Monocyte | 2 | 2.2% |
| Myelocyte | 1 | 1.1% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 1.00). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** ALL
- **Confidence:** 1.000
- **Ground truth (file label):** ALL

### Top contributing features (SHAP)

- lymphoblast differential % (supports, SHAP=+5.2458)
- scanty cytoplasm attribute % (supports, SHAP=+0.8367)
- identified WBC cell count (supports, SHAP=+0.6336)
- slight cytoplasmic basophilia attribute % (supports, SHAP=+0.1548)
- small cell size attribute % (supports, SHAP=+0.0596)
