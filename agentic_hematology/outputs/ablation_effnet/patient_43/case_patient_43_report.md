# Hematology Report — Case patient_43

**Specimen:** Peripheral blood smear, 61 fields of view, 122 of 128 detected objects classified as informative WBCs (6 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Myeloblasts | 74.6% |
| Neutrophils | 8.2% |
| Lymphoblasts | 8.2% |
| Lymphocytes | 5.7% |
| Eosinophils | 1.6% |
| Monocytes | 0.8% |
| Myelocytes | 0.8% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Myeloid Leukemia (AML).

Blast-equivalent burden is 82.8% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 91 Myeloblasts):** nucleus (99.7%); cytoplasm (92.6%); nuclear chromatin (92.0%); cytoplasmic vacuoles (90.6%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 61 FOVs; 122/128 cells classifiable (4.7% artefact); source=agentic_orchestrator; mean detection confidence=0.766.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 61
- Raw detected cells before overlap deduplication: 144
- Deduplicated detected cells: 128
- Informative WBCs: 122
- Artefacts/non-WBC detections: 6

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Myeloblast | 91 | 74.6% |
| Lymphoblast | 10 | 8.2% |
| Neutrophil | 10 | 8.2% |
| Lymphocyte | 7 | 5.7% |
| Eosinophil | 2 | 1.6% |
| Monocyte | 1 | 0.8% |
| Myelocyte | 1 | 0.8% |

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.2).

## Agentic Diagnosis
Predicted diagnosis: **AML** (confidence 0.93). Rationale: learned classifier prediction from aggregated differential features.

## Cell Grounding

- `img002_c000` in `43_12_59_400_AML.png` bbox=[131.0, 443.0, 199.5, 538.0]: Myeloblast (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img039_c000` in `43_47_40_400_AML.png` bbox=[84.75, 89.12, 157.38, 207.12]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img054_c000` in `43_60_55_400_AML.png` bbox=[310.75, 257.5, 374.25, 368.5]: Neutrophil (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img032_c000` in `43_40_34_400_AML.png` bbox=[274.5, 542.0, 328.5, 632.0]: Lymphocyte (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img052_c000` in `43_59_54_400_AML.png` bbox=[260.5, 169.0, 337.0, 282.75]: Myeloblast (0.90); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c001` in `43_12_59_400_AML.png` bbox=[365.5, 463.5, 441.5, 547.5]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img044_c000` in `43_51_44_400_AML.png` bbox=[396.5, 547.0, 465.5, 640.0]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img059_c000` in `43_8_8_400_AML.png` bbox=[425.0, 254.0, 498.0, 365.0]: Myeloblast (0.89); nuclear chromatin; nuclear shape; nucleus; cytoplasm.