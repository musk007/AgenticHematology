# Hematology Report — Case patient_6

**Specimen:** Peripheral blood smear, 55 fields of view, 70 of 93 detected objects classified as informative WBCs (23 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 48.6% |
| Myeloblasts | 24.3% |
| Lymphocytes | 12.9% |
| Neutrophils | 5.7% |
| Eosinophils | 4.3% |
| Myelocytes | 2.9% |
| Monocytes | 1.4% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 72.9% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 34 Lymphoblasts):** nucleus (96.5%); nuclear chromatin (68.2%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 55 FOVs; 70/93 cells classifiable (24.7% artefact); source=agentic_orchestrator; mean detection confidence=0.787.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 55
- Raw detected cells before overlap deduplication: 112
- Deduplicated detected cells: 93
- Informative WBCs: 70
- Artefacts/non-WBC detections: 23

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 34 | 48.6% |
| Myeloblast | 17 | 24.3% |
| Lymphocyte | 9 | 12.9% |
| Neutrophil | 4 | 5.7% |
| Eosinophil | 3 | 4.3% |
| Myelocyte | 2 | 2.9% |
| Monocyte | 1 | 1.4% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.58). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img041_c000` in `6_49_52_400_ALL.png` bbox=[68.0, 509.5, 116.25, 597.5]: Lymphocyte (0.93); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img043_c000` in `6_50_101_400_ALL.png` bbox=[57.44, 56.12, 114.56, 145.5]: Lymphocyte (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img052_c000` in `6_7_28_400_ALL.png` bbox=[373.0, 326.0, 429.0, 416.0]: Lymphocyte (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img027_c000` in `6_36_17_400_ALL.png` bbox=[447.75, 347.0, 506.75, 451.0]: Lymphocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img006_c000` in `6_16_46_400_ALL.png` bbox=[278.5, 208.25, 329.5, 298.25]: Lymphocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img030_c000` in `6_39_31_400_ALL.png` bbox=[32.56, 212.12, 108.19, 360.0]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasmic basophilia.
- `img033_c000` in `6_41_35_400_ALL.png` bbox=[2.59, 335.25, 52.28, 425.75]: Lymphoblast (0.88); nuclear chromatin; nucleus; cytoplasm; cytoplasmic basophilia.
- `img009_c001` in `6_19_50_400_ALL.png` bbox=[370.0, 352.5, 443.0, 459.5]: Myeloblast (0.88); nuclear chromatin; nucleus; cytoplasm; cytoplasmic basophilia.