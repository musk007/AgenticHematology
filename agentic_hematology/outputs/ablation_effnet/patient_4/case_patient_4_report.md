# Hematology Report — Case patient_4

**Specimen:** Peripheral blood smear, 52 fields of view, 130 of 149 detected objects classified as informative WBCs (19 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 46.9% |
| Neutrophils | 26.2% |
| Lymphocytes | 20.0% |
| Eosinophils | 5.4% |
| Metamyelocytes | 1.5% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 46.9% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 61 Lymphoblasts):** nucleus (91.8%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 52 FOVs; 130/149 cells classifiable (12.8% artefact); source=agentic_orchestrator; mean detection confidence=0.766.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 52
- Raw detected cells before overlap deduplication: 167
- Deduplicated detected cells: 149
- Informative WBCs: 130
- Artefacts/non-WBC detections: 19

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 61 | 46.9% |
| Neutrophil | 34 | 26.2% |
| Lymphocyte | 26 | 20.0% |
| Eosinophil | 7 | 5.4% |
| Metamyelocyte | 2 | 1.5% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.81). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img039_c000` in `4_82_185_400_ALL.png` bbox=[0.03, 112.0, 40.88, 215.5]: Eosinophil (0.94); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img019_c000` in `4_42_117_400_ALL.png` bbox=[493.5, 210.0, 534.5, 274.75]: Lymphocyte (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img041_c000` in `4_85_137_400_ALL.png` bbox=[284.5, 523.0, 343.5, 611.0]: Eosinophil (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img037_c000` in `4_7_8_400_ALL.png` bbox=[206.5, 116.25, 283.5, 222.5]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img011_c000` in `4_32_50_400_ALL.png` bbox=[129.5, 89.25, 194.0, 203.75]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img009_c000` in `4_28_40_400_ALL.png` bbox=[495.0, 550.0, 551.0, 640.0]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img005_c000` in `4_16_103_400_ALL.png` bbox=[207.25, 440.0, 264.75, 540.0]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img017_c000` in `4_39_67_400_ALL.png` bbox=[241.25, 413.5, 305.75, 519.5]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.