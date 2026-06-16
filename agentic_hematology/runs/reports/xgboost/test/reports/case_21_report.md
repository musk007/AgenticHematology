# Hematology Report — Case 21

**Specimen:** Peripheral blood smear, 62 fields of view, 206 of 253 detected objects classified as informative WBCs (47 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Atypical lymphocytes | 92.2% |
| Neutrophils | 5.8% |
| Monocytes | 1.5% |
| Lymphocytes | 0.5% |

**Diagnostic flags:** no blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Dominant population: Atypical lymphocytes (92.2% of informative WBCs). Blast-equivalent burden 0.0%.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 62 FOVs; 206/253 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 62
- Deduplicated detected cells: 253
- Informative WBCs: 206
- Artefacts/non-WBC detections: 47

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Atypical lymphocyte | 190 | 92.2% |
| Neutrophil | 12 | 5.8% |
| Monocyte | 3 | 1.5% |
| Lymphocyte | 1 | 0.5% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.29). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** AML
- **Confidence:** 0.288
- **Ground truth (file label):** CLL

### Top contributing features (SHAP)

- prominent nucleolus attribute % (opposes, SHAP=-0.6718)
- small cell size attribute % (supports, SHAP=+0.4863)
- myeloblast differential % (opposes, SHAP=-0.3125)
- identified WBC cell count (supports, SHAP=+0.2053)
- inconspicuous nucleolus attribute % (opposes, SHAP=-0.1898)
