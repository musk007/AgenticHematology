# Hematology Report — Case 34

**Specimen:** Peripheral blood smear, 39 fields of view, 63 of 70 detected objects classified as informative WBCs (7 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 49.2% |
| Neutrophils | 39.7% |
| Lymphocytes | 4.8% |
| Monocytes | 3.2% |
| Myelocytes | 1.6% |
| Metamyelocytes | 1.6% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 49.21% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 39 FOVs; 63/70 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 39
- Deduplicated detected cells: 70
- Informative WBCs: 63
- Artefacts/non-WBC detections: 7

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 31 | 49.2% |
| Neutrophil | 25 | 39.7% |
| Lymphocyte | 3 | 4.8% |
| Monocyte | 2 | 3.2% |
| Metamyelocyte | 1 | 1.6% |
| Myelocyte | 1 | 1.6% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.96). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** AML
- **Confidence:** 0.957
- **Ground truth (file label):** AML

### Top contributing features (SHAP)

- prominent nucleolus attribute % (supports, SHAP=+1.2762)
- small cell size attribute % (supports, SHAP=+0.4613)
- myeloblast differential % (supports, SHAP=+0.2866)
- identified WBC cell count (supports, SHAP=+0.2594)
- regular nuclear shape attribute % (supports, SHAP=+0.1754)
