# Hematology Report — Case 28

**Specimen:** Peripheral blood smear, 59 fields of view, 271 of 299 detected objects classified as informative WBCs (28 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 59.0% |
| Myelocytes | 17.0% |
| Metamyelocytes | 7.8% |
| Myeloblasts | 7.0% |
| Monocytes | 5.2% |
| Lymphocytes | 3.0% |
| Eosinophils | 1.1% |

**Diagnostic flags:** blasts present.

**Impression:** Chronic Myeloid Leukemia (CML).

Dominant population: Neutrophils (59.0% of informative WBCs). Blast-equivalent burden 7.01%.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 59 FOVs; 271/299 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 59
- Deduplicated detected cells: 299
- Informative WBCs: 271
- Artefacts/non-WBC detections: 28

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 160 | 59.0% |
| Myelocyte | 46 | 17.0% |
| Metamyelocyte | 21 | 7.8% |
| Myeloblast | 19 | 7.0% |
| Monocyte | 14 | 5.2% |
| Lymphocyte | 8 | 3.0% |
| Eosinophil | 3 | 1.1% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **CML** (confidence 1.00). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** CML
- **Confidence:** 1.000
- **Ground truth (file label):** CML

### Top contributing features (SHAP)

- neutrophil differential % (supports, SHAP=+3.8270)
- metamyelocyte differential % (supports, SHAP=+3.4862)
- myelocyte differential % (supports, SHAP=+3.2392)
- basophil differential % (opposes, SHAP=-0.0258)
- small cell size attribute % (opposes, SHAP=-0.0054)
