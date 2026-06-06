# Peripheral Blood Smear Diagnostic Report

## **Predicted Diagnosis**
**Acute Lymphoblastic Leukemia (ALL)**
*   **Confidence:** High (0.8)
*   **Primary Evidence:** Marked lymphoblast burden (46.9%) exceeding the diagnostic threshold, combined with morphologic features of immature cells (high nuclear-to-cytoplasmic ratio, fine chromatin, scant cytoplasm) and the presence of eosinophils and neutrophils in the differential.

---

## **Morphologic Descriptors**

The smear demonstrates a leukemic infiltrate dominated by **Lymphoblasts**, which are the hallmark of acute lymphoblastic leukemia.

### **1. Lymphoblasts (Predominant Findings)**
*   **Count:** 61 cells (46.9% of total informative cells)
*   **Morphology:**
    *   **Nucleus:** High nuclear-to-cytoplasmic (N:C) ratio. Nuclei are generally round to oval, sometimes slightly indented. Chromatin appears fine, lacy, or "smudgy" rather than condensed.
    *   **Cytoplasm:** Scant to moderate amount (0.18–0.98 µm). Basophilia is variable (0.00–1.0), often described as "ground glass" or pale blue.
    *   **Vacuoles:** Present in a minority of cells (0.27–0.99), suggesting metabolic activity or degenerative changes.
    *   **Nuclear Shape:** Highly variable (0.00–1.0), indicating a lack of specific lineage commitment.
*   **Key Attributes:**
    *   `Nucleus`: 0.91–1.0 (High confidence)
    *   `Cytoplasm`: 0.18–0.98 (Variable)
    *   `Cytoplasmic_Basophilia`: 0.00–1.0 (Variable)

### **2. Neutrophils**
*   **Count:** 34 cells (26.2%)
*   **Morphology:** Mature segmented neutrophils with distinct lobes and clear cytoplasmic borders.
*   **Key Attributes:**
    *   `Nucleus`: 1.0 (Perfect segmentation)
    *   `Cytoplasmic_Basophilia`: 1.0 (Strong)

### **3. Lymphocytes**
*   **Count:** 26 cells (20.0%)
*   **Morphology:** Small to medium-sized cells with condensed chromatin and peripheral cytoplasm.
*   **Key Attributes:**
    *   `Nucleus`: 0.00–0.99 (Variable)
    *   `Cytoplasmic_Basophilia`: 0.00–0.13 (Low)

### **4. Eosinophils**
*   **Count:** 7 cells (5.4%)
*   **Morphology:** Bi-lobed nucleus with bright red-orange cytoplasmic granules.
*   **Key Attributes:**
    *   `Cytoplasmic_Basophilia`: 1.0 (Strong)
    *   `Cytoplasmic_Vacuoles`: 0.99–1.0 (High)

### **5. Metamyelocytes**
*   **Count:** 2 cells (1.5%)
*   **

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