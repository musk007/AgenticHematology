# Hematology Report — Case patient_31

**Specimen:** Peripheral blood smear, 50 fields of view, 304 of 399 detected objects classified as informative WBCs (95 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Neutrophils | 66.4% |
| Myelocytes | 17.8% |
| Metamyelocytes | 8.2% |
| Myeloblasts | 4.3% |
| Basophils | 1.3% |
| Monocytes | 1.3% |
| Lymphocytes | 0.3% |
| Eosinophils | 0.3% |

**Diagnostic flags:** blasts present.

**Impression:** Chronic Myeloid Leukemia (CML).

Dominant population: Neutrophils (66.4% of informative WBCs). Blast-equivalent burden 4.3%.

**Cohort morphology (n = 202 Neutrophils):** nucleus (100.0%); cytoplasmic basophilia (99.7%); cytoplasmic vacuoles (99.0%); nuclear chromatin (98.8%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 50 FOVs; 304/399 cells classifiable (23.8% artefact); source=agentic_orchestrator; mean detection confidence=0.795.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 50
- Raw detected cells before overlap deduplication: 449
- Deduplicated detected cells: 399
- Informative WBCs: 304
- Artefacts/non-WBC detections: 95

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Neutrophil | 202 | 66.4% |
| Myelocyte | 54 | 17.8% |
| Metamyelocyte | 25 | 8.2% |
| Myeloblast | 13 | 4.3% |
| Basophil | 4 | 1.3% |
| Monocyte | 4 | 1.3% |
| Eosinophil | 1 | 0.3% |
| Lymphocyte | 1 | 0.3% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **CML** (confidence 0.67). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img025_c000` in `31_33_72_400_CML.png` bbox=[168.5, 286.25, 231.5, 399.25]: Myelocyte (0.95); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img049_c000` in `31_9_9_400_CML.png` bbox=[319.0, 407.0, 389.0, 535.0]: Metamyelocyte (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `31_12_58_400_CML.png` bbox=[327.5, 400.0, 387.5, 508.0]: Metamyelocyte (0.92); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img019_c000` in `31_28_29_400_CML.png` bbox=[92.25, 314.0, 155.75, 422.5]: Myelocyte (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img021_c001` in `31_2_2_400_CML.png` bbox=[249.12, 208.75, 318.0, 336.75]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img022_c000` in `31_30_31_400_CML.png` bbox=[432.0, 0.0, 495.0, 84.56]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img018_c000` in `31_27_27_400_CML.png` bbox=[50.16, 494.0, 117.38, 615.0]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img001_c000` in `31_11_57_400_CML.png` bbox=[340.5, 42.5, 397.0, 129.75]: Neutrophil (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.