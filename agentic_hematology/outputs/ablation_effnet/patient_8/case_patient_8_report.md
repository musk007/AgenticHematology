# Hematology Report — Case patient_8

**Specimen:** Peripheral blood smear, 55 fields of view, 109 of 125 detected objects classified as informative WBCs (16 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 71.6% |
| Lymphocytes | 9.2% |
| Neutrophils | 8.3% |
| Myeloblasts | 7.3% |
| Monocytes | 2.8% |
| Myelocytes | 0.9% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 78.9% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 78 Lymphoblasts):** nucleus (96.1%); nuclear chromatin (72.9%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 55 FOVs; 109/125 cells classifiable (12.8% artefact); source=agentic_orchestrator; mean detection confidence=0.792.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 55
- Raw detected cells before overlap deduplication: 134
- Deduplicated detected cells: 125
- Informative WBCs: 109
- Artefacts/non-WBC detections: 16

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 78 | 71.6% |
| Lymphocyte | 10 | 9.2% |
| Neutrophil | 9 | 8.3% |
| Myeloblast | 8 | 7.3% |
| Monocyte | 3 | 2.8% |
| Myelocyte | 1 | 0.9% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.71). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img001_c000` in `8_11_102_400_ALL.png` bbox=[29.25, 127.12, 92.44, 234.12]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img046_c000` in `8_57_58_400_ALL.png` bbox=[303.25, 407.0, 388.75, 534.0]: Myeloblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img043_c000` in `8_54_107_400_ALL.png` bbox=[441.75, 360.25, 496.75, 453.25]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img031_c000` in `8_42_98_400_ALL.png` bbox=[273.25, 355.0, 336.75, 460.0]: Myeloblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `8_12_80_400_ALL.png` bbox=[471.0, 406.25, 519.0, 490.75]: Lymphoblast (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img015_c000` in `8_26_23_400_ALL.png` bbox=[434.75, 366.5, 503.25, 481.5]: Lymphoblast (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img023_c000` in `8_35_108_400_ALL.png` bbox=[383.75, 49.66, 444.25, 166.38]: Lymphoblast (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img037_c000` in `8_48_102_400_ALL.png` bbox=[54.81, 378.5, 95.69, 458.5]: Neutrophil (0.87); nuclear chromatin; nuclear shape; nucleus; cytoplasm.