# Hematology Report — Case 43

**Specimen:** Peripheral blood smear, 61 fields of view, 127 of 131 detected objects classified as informative WBCs (4 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 76.4% |
| Lymphocytes | 8.7% |
| Neutrophils | 7.9% |
| Lymphoblasts | 3.9% |
| Monocytes | 1.6% |
| Myelocytes | 0.8% |
| Eosinophils | 0.8% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 80.3% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 97 Myeloblasts):** nucleus (97.6%); nuclear chromatin (90.8%); cytoplasmic vacuoles (89.9%); cytoplasm (87.7%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 61 FOVs; 127/131 cells classifiable (3.1% artefact); source=agentic_orchestrator; mean detection confidence=0.761.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 61
- Raw detected cells before overlap deduplication: 145
- Deduplicated detected cells: 131
- Informative WBCs: 127
- Artefacts/non-WBC detections: 4

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 97 | 76.4% |
| Lymphocyte | 11 | 8.7% |
| Neutrophil | 10 | 7.9% |
| Lymphoblast | 5 | 3.9% |
| Monocyte | 2 | 1.6% |
| Eosinophil | 1 | 0.8% |
| Myelocyte | 1 | 0.8% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.96). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img042_c000` in `43_4_73_400_AML.png` bbox=[197.5, 269.0, 275.5, 376.0]: Myeloblast (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `43_12_59_400_AML.png` bbox=[130.25, 444.5, 201.25, 537.5]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img054_c000` in `43_60_55_400_AML.png` bbox=[182.25, 442.0, 243.25, 531.5]: Myeloblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img059_c000` in `43_8_8_400_AML.png` bbox=[424.0, 253.0, 499.0, 364.0]: Myeloblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img038_c000` in `43_46_39_400_AML.png` bbox=[566.0, 74.81, 634.0, 186.25]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img044_c000` in `43_51_44_400_AML.png` bbox=[398.0, 544.0, 463.5, 640.0]: Myeloblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c001` in `43_12_59_400_AML.png` bbox=[366.5, 463.0, 441.5, 540.5]: Myeloblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img007_c000` in `43_18_75_400_AML.png` bbox=[75.12, 456.5, 140.25, 549.0]: Myeloblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.