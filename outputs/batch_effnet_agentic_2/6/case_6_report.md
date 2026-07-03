# Hematology Report — Case 6

**Specimen:** Peripheral blood smear, 56 fields of view, 77 of 105 detected objects classified as informative WBCs (28 artefacts excluded).

**Differential (clinical denominator):**

| Cell type | % of informative WBCs |
|---|---|
| Lymphoblasts | 50.6% |
| Myeloblasts | 24.7% |
| Neutrophils | 11.7% |
| Lymphocytes | 9.1% |
| Eosinophils | 2.6% |
| Myelocytes | 1.3% |

**Diagnostic flags:** blasts present; blast threshold met.

**Impression:** Acute Lymphoblastic Leukemia (ALL).

Blast-equivalent burden is 75.3% of informative WBCs, meeting the 20.0% threshold for acute leukemia consideration.

**Cohort morphology (n = 39 Lymphoblasts):** nuclear chromatin (86.8%); nucleus (76.3%); cytoplasm (58.7%); cytoplasmic basophilia (58.3%).

**Differential considerations:**
- Correlate with clinical history, CBC, and peripheral smear morphology.
- Flow cytometric immunophenotyping if acute leukemia is suspected.
- Bone marrow aspirate and trephine biopsy as clinically indicated.

**Recommended workup:**
- Flow cytometric immunophenotyping for lineage assignment.
- Bone marrow aspirate and trephine biopsy when indicated.
- Cytogenetics and molecular profiling per institutional protocol.

**QC:** 56 FOVs; 77/105 cells classifiable (26.7% artefact); source=agentic_orchestrator; mean detection confidence=0.783.

---
*Automated multi-image peripheral blood smear analysis. Findings are intended to support — not replace — review by a board-certified hematopathologist.*

## Quantitative Cell Summary

- Fields of view: 56
- Detected cells: 105
- Informative WBCs: 77
- Artefacts/non-WBC detections: 28

| Cell type | Count | % informative WBCs |
|---|---:|---:|
| Lymphoblast | 39 | 50.6% |
| Myeloblast | 19 | 24.7% |
| Neutrophil | 9 | 11.7% |
| Lymphocyte | 7 | 9.1% |
| Eosinophil | 2 | 2.6% |
| Myelocyte | 1 | 1.3% |

## Agentic Diagnosis
Predicted diagnosis: **ALL** (confidence 0.53). Rationale: learned classifier prediction from detection-derived features.

## Cell Grounding

- `img000_c000` in `6_10_1000_ALL.png` bbox=[376.0, 451.0, 431.0, 542.5]: Lymphoblast (0.83); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c000` in `6_12_1000_ALL.png` bbox=[176.5, 286.0, 232.0, 383.0]: Lymphoblast (0.91); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img002_c001` in `6_12_1000_ALL.png` bbox=[177.25, 287.0, 232.25, 384.0]: Myeloblast (0.42); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img003_c000` in `6_13_1000_ALL.png` bbox=[584.0, 477.5, 640.0, 589.5]: Lymphoblast (0.82); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img004_c002` in `6_14_1000_ALL.png` bbox=[429.0, 514.0, 512.0, 632.0]: Myeloblast (0.35); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img005_c000` in `6_15_1000_ALL.png` bbox=[413.5, 466.5, 469.0, 554.5]: Lymphoblast (0.69); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img005_c001` in `6_15_1000_ALL.png` bbox=[381.0, 91.56, 436.0, 192.5]: Lymphoblast (0.63); nuclear chromatin; nuclear shape; nucleus; cytoplasm.
- `img005_c002` in `6_15_1000_ALL.png` bbox=[412.75, 467.0, 469.75, 554.0]: Lymphocyte (0.61); nuclear chromatin; nuclear shape; nucleus; cytoplasm.

> **⚠ Flagged for mandatory human review by the reflection agent.** Reason(s): High pct_class_none and low classifier confidence suggest unreliable detection quality.
