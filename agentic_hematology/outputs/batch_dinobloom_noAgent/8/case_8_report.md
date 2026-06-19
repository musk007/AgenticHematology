# Hematology Report — Case 8

**Specimen:** Peripheral blood smear, 55 fields of view, 109 of 125 detected objects classified as informative WBCs (16 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 66.1% |
| Myeloblasts | 12.8% |
| Lymphocytes | 11.0% |
| Neutrophils | 7.3% |
| Monocytes | 2.8% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 78.9% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 72 Lymphoblasts):** nucleus (88.1%); nuclear chromatin (58.3%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 55 FOVs; 109/125 cells classifiable (12.8% artefact); source=agentic_orchestrator; mean detection confidence=0.73.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 55
- Raw detected cells before overlap deduplication: 139
- Deduplicated detected cells: 125
- Informative WBCs: 109
- Artefacts/non-WBC detections: 16

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 72 | 66.1% |
| Myeloblast | 14 | 12.8% |
| Lymphocyte | 12 | 11.0% |
| Neutrophil | 8 | 7.3% |
| Monocyte | 3 | 2.8% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.68). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img047_c000` in `8_58_108_400_ALL.png` bbox=[374.5, 311.5, 435.5, 414.5]: Monocyte (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img044_c000` in `8_55_54_400_ALL.png` bbox=[169.62, 293.5, 232.38, 398.5]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img031_c000` in `8_42_98_400_ALL.png` bbox=[273.0, 354.0, 337.5, 461.0]: Myeloblast (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c000` in `8_11_102_400_ALL.png` bbox=[32.25, 121.25, 92.12, 235.25]: Neutrophil (0.85); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img043_c000` in `8_54_107_400_ALL.png` bbox=[441.0, 360.75, 498.0, 453.25]: Neutrophil (0.85); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img025_c000` in `8_37_85_400_ALL.png` bbox=[260.0, 277.0, 327.0, 392.0]: Neutrophil (0.85); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img019_c000` in `8_31_39_400_ALL.png` bbox=[326.5, 224.0, 374.5, 295.5]: Lymphoblast (0.85); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img031_c001` in `8_42_98_400_ALL.png` bbox=[16.17, 152.5, 69.06, 251.0]: Myeloblast (0.84); nuclear chromatin; nuclear shape; nucleus; cytoplasm.