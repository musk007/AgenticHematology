# Hematology Report — Case 15

**Specimen:** Peripheral blood smear, 59 fields of view, 137 of 164 detected objects classified as informative WBCs (27 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Monoblasts | 86.1% |
| Lymphocytes | 7.3% |
| Neutrophils | 4.4% |
| Myeloblasts | 1.5% |
| Monocytes | 0.7% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 87.59% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 59 FOVs; 137/164 cells classifiable (0% artefact); source=patient_WBC_stats; mean detection confidence=0.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 59
- Deduplicated detected cells: 164
- Informative WBCs: 137
- Artefacts/non-WBC detections: 27

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Monoblast | 118 | 86.1% |
| Lymphocyte | 10 | 7.3% |
| Neutrophil | 6 | 4.4% |
| Myeloblast | 2 | 1.5% |
| Monocyte | 1 | 0.7% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.93). Rationale: learned classifier (stats features, train-split model).

## Cell Grounding

## Classifier Prediction

- **Predicted class:** AML
- **Confidence:** 0.933
- **Ground truth (file label):** AML

### Top contributing features (SHAP)

- prominent nucleolus attribute % (supports, SHAP=+1.3384)
- small cell size attribute % (supports, SHAP=+0.4684)
- myeloblast differential % (opposes, SHAP=-0.2521)
- inconspicuous nucleolus attribute % (supports, SHAP=+0.2451)
- identified WBC cell count (supports, SHAP=+0.2248)
