# Hematology Report — Case 40

**Specimen:** Peripheral blood smear, 50 fields of view, 90 of 109 detected objects classified as informative WBCs (19 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 28.9% |
| Monocytes | 26.7% |
| Promonocytes | 17.8% |
| Lymphocytes | 11.1% |
| Myeloblasts | 8.9% |
| Eosinophils | 4.4% |
| Myelocytes | 1.1% |
| Metamyelocytes | 1.1% |

**Diagnostic flags:** blasts present.

**Impression:** Acute Myeloid Leukemia (AML).

Dominant population: Neutrophils (28.9% of informative WBCs). Blast-equivalent burden 8.89%.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 50 FOVs; 90/109 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 50
- Deduplicated detected cells: 109
- Informative WBCs: 90
- Artefacts/non-WBC detections: 19

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 26 | 28.9% |
| Monocyte | 24 | 26.7% |
| Promonocyte | 16 | 17.8% |
| Lymphocyte | 10 | 11.1% |
| Myeloblast | 8 | 8.9% |
| Eosinophil | 4 | 4.4% |
| Metamyelocyte | 1 | 1.1% |
| Myelocyte | 1 | 1.1% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.63). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** AML
- **Confidence:** 0.633
- **Ground truth (file label):** AML

### Top contributing features (SHAP)

- prominent nucleolus attribute % (opposes, SHAP=-0.5619)
- regular nuclear shape attribute % (supports, SHAP=+0.4147)
- identified WBC cell count (supports, SHAP=+0.2446)
- small cell size attribute % (supports, SHAP=+0.2235)
- inconspicuous nucleolus attribute % (opposes, SHAP=-0.1927)
