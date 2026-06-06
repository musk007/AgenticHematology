# Peripheral Blood Smear Diagnostic Report

## 1. Predicted Diagnosis
**Acute Lymphoblastic Leukemia (ALL)**
*   **Confidence:** High (0.8)
*   **Rationale:** The presence of a high burden of lymphoblasts (46.9%) significantly exceeds the diagnostic threshold for acute leukemia. The morphology cohort confirms the presence of immature lymphoid cells with characteristic features (high nuclear-to-cytoplasmic ratio, scant cytoplasm, fine chromatin).

## 2. Morphologic Descriptors
The smear demonstrates a leukemic infiltrate dominated by **Lymphoblasts**.

*   **Cell Type:** Lymphoblast (Predominant)
*   **Key Features:**
    *   **Nuclear Morphology:** High nuclear-to-cytoplasmic (N:C) ratio. Nuclei are generally round to oval with condensed chromatin (though some show variation).
    *   **Cytoplasm:** Scant to moderate amount (Cytoplasmic_Vacuoles: 0.2667).
    *   **Basophilia:** Minimal to absent (Cytoplasmic_Basophilia: 0.3593).
    *   **Vacuoles:** Present in a minority of cells (0.2667), suggesting maturation or specific differentiation pathways.
*   **Differential Diagnosis:**
    *   **Neutrophilic Leukemia:** Ruled out by the absence of neutrophilic precursors (Metamyelocytes: 1.5%) and the overwhelming lymphoid population.
    *   **Myeloid Leukemia:** Ruled out by the absence of myeloid precursors (Metamyelocytes: 1.5%) and the presence of lymphoblasts.
    *   **Chronic Myeloid Leukemia (CML):** Ruled out by the lack of granulocytic series dominance and the presence of blasts.

## 3. Grounding Section
The following image IDs and bounding boxes (bbox_xyxy) provide representative examples of the predicted cell types, confirming the morphologic descriptors:

*   **Lymphoblasts (Primary Diagnosis):**
    *   `img029_c000`: `4_29_156_400_ALL.png` (Nucleus: 0.99885, Cytoplasm: 0.066)
    *   `img019_c001`: `4_42_117_400_ALL.png` (Nucleus: 0.99997, Cytoplasm: ~0)
    *   `img024_c000`: `4_50_90_400_ALL.png` (Nucleus: 0.99998, Cytoplasm: 0.9829)
    *   `img011_c001`: `4_32_50_400_ALL.png` (Nucleus: 1.0, Cytoplasm: ~0)
    *   `img030_c000`: `4_68_177_400_ALL.png` (Nucleus: 0.99909, Cytoplasm: 0.021)
    *   `img002_c000`: `4_104_149_400_ALL.png` (Nucle

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

Overlap correction: global canvas stitching active (20% tile overlap, IoU threshold 0.4).