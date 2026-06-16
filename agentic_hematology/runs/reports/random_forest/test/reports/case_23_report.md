# Hematology Report — Case 23

**Specimen:** Peripheral blood smear, 59 fields of view, 177 of 207 detected objects classified as informative WBCs (30 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Abnormal promyelocytes | 91.5% |
| Neutrophils | 6.2% |
| Myeloblasts | 1.1% |
| Monocytes | 0.6% |
| Lymphocytes | 0.6% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 92.66% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 59 FOVs; 177/207 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 59
- Deduplicated detected cells: 207
- Informative WBCs: 177
- Artefacts/non-WBC detections: 30

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Abnormal promyelocyte | 162 | 91.5% |
| Neutrophil | 11 | 6.2% |
| Myeloblast | 2 | 1.1% |
| Lymphocyte | 1 | 0.6% |
| Monocyte | 1 | 0.6% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.79). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** AML
- **Confidence:** 0.792
- **Ground truth (file label):** APML

### Top contributing features (SHAP)

- blast pool % of WBC (supports, SHAP=+0.0603)
- blasts lineage group % (supports, SHAP=+0.0570)
- basophil differential % (supports, SHAP=+0.0387)
- metamyelocyte differential % (supports, SHAP=+0.0379)
- myelocyte differential % (supports, SHAP=+0.0346)
