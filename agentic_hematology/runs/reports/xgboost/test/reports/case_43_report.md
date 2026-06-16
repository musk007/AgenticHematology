# Hematology Report — Case 43

**Specimen:** Peripheral blood smear, 61 fields of view, 113 of 118 detected objects classified as informative WBCs (5 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 80.5% |
| Neutrophils | 7.1% |
| Lymphocytes | 5.3% |
| Promonocytes | 4.4% |
| Monocytes | 2.6% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 80.53% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 61 FOVs; 113/118 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 61
- Deduplicated detected cells: 118
- Informative WBCs: 113
- Artefacts/non-WBC detections: 5

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 91 | 80.5% |
| Neutrophil | 8 | 7.1% |
| Lymphocyte | 6 | 5.3% |
| Promonocyte | 5 | 4.4% |
| Monocyte | 3 | 2.6% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.96). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** AML
- **Confidence:** 0.962
- **Ground truth (file label):** AML

### Top contributing features (SHAP)

- prominent nucleolus attribute % (supports, SHAP=+1.4387)
- small cell size attribute % (supports, SHAP=+0.4584)
- myeloblast differential % (supports, SHAP=+0.2866)
- inconspicuous nucleolus attribute % (supports, SHAP=+0.2385)
- identified WBC cell count (supports, SHAP=+0.2330)
