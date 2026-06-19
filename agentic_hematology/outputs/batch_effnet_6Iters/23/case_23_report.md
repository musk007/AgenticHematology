# Hematology Report — Case 23

**Specimen:** Peripheral blood smear, 59 fields of view, 206 of 224 detected objects classified as informative WBCs (18 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 44.7% |
| Myelocytes | 19.9% |
| Neutrophils | 14.1% |
| Lymphoblasts | 13.6% |
| Metamyelocytes | 2.9% |
| Monocytes | 2.4% |
| Lymphocytes | 1.9% |
| Monoblasts | 0.5% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 58.7% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 92 Myeloblasts):** nucleus (99.4%); nuclear chromatin (95.8%); cytoplasmic vacuoles (88.9%); cytoplasm (71.9%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 59 FOVs; 206/224 cells classifiable (8.0% artefact); source=agentic_orchestrator; mean detection confidence=0.684.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 59
- Raw detected cells before overlap deduplication: 289
- Deduplicated detected cells: 224
- Informative WBCs: 206
- Artefacts/non-WBC detections: 18

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 92 | 44.7% |
| Myelocyte | 41 | 19.9% |
| Neutrophil | 29 | 14.1% |
| Lymphoblast | 28 | 13.6% |
| Metamyelocyte | 6 | 2.9% |
| Monocyte | 5 | 2.4% |
| Lymphocyte | 4 | 1.9% |
| Monoblast | 1 | 0.5% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.80). Rationale: myeloid/monocytic blast burden meets acute leukemia pattern.

## Cell Grounding

- `img047_c000` in `23_54_40_400_APML.png` bbox=[421.0, 453.0, 481.0, 554.0]: Myelocyte (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img037_c000` in `23_45_12_400_APML.png` bbox=[0.0, 386.5, 71.38, 509.5]: Myelocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img007_c000` in `23_17_89_400_APML.png` bbox=[251.5, 551.0, 317.5, 640.0]: Myelocyte (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img051_c000` in `23_58_58_400_APML.png` bbox=[427.75, 141.75, 495.75, 256.75]: Myelocyte (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img041_c000` in `23_49_17_400_APML.png` bbox=[569.0, 41.38, 637.0, 134.25]: Myeloblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img028_c000` in `23_36_63_400_APML.png` bbox=[540.5, 399.0, 601.5, 498.0]: Myelocyte (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img009_c000` in `23_19_32_400_APML.png` bbox=[363.5, 170.25, 422.5, 265.75]: Myeloblast (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img020_c000` in `23_29_48_400_APML.png` bbox=[432.5, 402.5, 489.5, 497.5]: Neutrophil (0.88); nuclear chromatin; nuclear shape; nucleus; cytoplasm.

> **⚠ Flagged for mandatory human review by the reflection agent.** Reason(s): High blast burden with borderline classifier confidence and non-WBC artifacts suggest need for expert review
