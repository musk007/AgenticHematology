# Hematology Report — Case 31

**Specimen:** Peripheral blood smear, 50 fields of view, 300 of 368 detected objects classified as informative WBCs (68 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 59.0% |
| Myelocytes | 19.7% |
| Myeloblasts | 6.3% |
| Metamyelocytes | 6.0% |
| Monocytes | 5.0% |
| Lymphocytes | 1.7% |
| Eosinophils | 1.3% |
| Basophils | 1.0% |

**Diagnostic flags:** blasts present.

**Impression:** Chronic Myeloid Leukemia (CML).

Dominant population: Neutrophils (59.0% of informative WBCs). Blast-equivalent burden 6.33%.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 50 FOVs; 300/368 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 50
- Deduplicated detected cells: 368
- Informative WBCs: 300
- Artefacts/non-WBC detections: 68

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 177 | 59.0% |
| Myelocyte | 59 | 19.7% |
| Myeloblast | 19 | 6.3% |
| Metamyelocyte | 18 | 6.0% |
| Monocyte | 15 | 5.0% |
| Lymphocyte | 5 | 1.7% |
| Eosinophil | 4 | 1.3% |
| Basophil | 3 | 1.0% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **CML** (confidence 1.00). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** CML
- **Confidence:** 1.000
- **Ground truth (file label):** CML

### Top contributing features (SHAP)

- neutrophil differential % (supports, SHAP=+3.8260)
- metamyelocyte differential % (supports, SHAP=+3.4862)
- myelocyte differential % (supports, SHAP=+3.2390)
- basophil differential % (supports, SHAP=+0.2662)
- small cell size attribute % (opposes, SHAP=-0.0054)
