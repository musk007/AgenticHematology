# Hematology Report — Case 45

**Specimen:** Peripheral blood smear, 54 fields of view, 172 of 202 detected objects classified as informative WBCs (30 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 57.0% |
| Monocytes | 19.2% |
| Neutrophils | 12.8% |
| Lymphocytes | 8.1% |
| Myelocytes | 1.7% |
| Promonocytes | 0.6% |
| Eosinophils | 0.6% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 56.98% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 54 FOVs; 172/202 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 54
- Deduplicated detected cells: 202
- Informative WBCs: 172
- Artefacts/non-WBC detections: 30

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 98 | 57.0% |
| Monocyte | 33 | 19.2% |
| Neutrophil | 22 | 12.8% |
| Lymphocyte | 14 | 8.1% |
| Myelocyte | 3 | 1.7% |
| Eosinophil | 1 | 0.6% |
| Promonocyte | 1 | 0.6% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.82). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** AML
- **Confidence:** 0.820
- **Ground truth (file label):** AML

### Top contributing features (SHAP)

- blast pool % of WBC (supports, SHAP=+0.0605)
- blasts lineage group % (supports, SHAP=+0.0583)
- slight cytoplasmic basophilia attribute % (supports, SHAP=+0.0411)
- moderate cytoplasmic basophilia attribute % (supports, SHAP=+0.0372)
- metamyelocyte differential % (supports, SHAP=+0.0370)
