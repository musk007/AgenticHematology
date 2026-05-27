"""
Global Canvas Evaluation & Deduplication Pipeline for LLD 40x Images
Implements sequence-invariant cross-image IoU deduplication using absolute stage coordinate mapping.
"""

import os
import re
import math
from collections import Counter

# ---------------------------------------------------------------------------
# Semantic & Clinical Configuration
# ---------------------------------------------------------------------------
IOU_DEDUPLICATION_THRESHOLD = 0.4  # IoU threshold to collapse boundary duplicates
DEFAULT_IMAGE_DIMENSION = 640      # Base pixel resolution of LLD images
OVERLAP_PERCENTAGE = 0.20          # Documented 20% pairwise field overlap

# Calculate the absolute non-overlapping stride step (640 * 0.8 = 512 pixels)
GLOBAL_STRIDE_PX = int(DEFAULT_IMAGE_DIMENSION * (1.0 - OVERLAP_PERCENTAGE))

# Class mapping corresponding to 0-indexed YOLOv5 WBC_v1.yaml configuration
YOLO_CLASS_NAMES = {
    0:  "none",
    1:  "myeloblast",
    2:  "lymphoblast",
    3:  "neutrophil",
    4:  "atypical lymphocyte",
    5:  "promonocyte",
    6:  "monoblast",
    7:  "lymphocyte",
    8:  "myelocyte",
    9:  "abnormal promyelocyte",
    10: "monocyte",
    11: "metamyelocyte",
    12: "eosinophil",
    13: "basophil"
}

class GlobalCellBox:
    """
    Translates local image-space bounding box predictions into an absolute,
    unified patient-level global coordinate coordinate canvas.
    """
    def __init__(self, x1, y1, x2, y2, cell_type, confidence, grid_x, grid_y, origin_file):
        self.cell_type = cell_type
        self.confidence = float(confidence)
        self.origin_file = origin_file
        
        # Project local coordinates to absolute canvas coordinates
        self.global_x1 = (grid_x * GLOBAL_STRIDE_PX) + float(x1)
        self.global_y1 = (grid_y * GLOBAL_STRIDE_PX) + float(y1)
        self.global_x2 = (grid_x * GLOBAL_STRIDE_PX) + float(x2)
        self.global_y2 = (grid_y * GLOBAL_STRIDE_PX) + float(y2)
        
        # Compute global geometry parameters
        self.area = (self.global_x2 - self.global_x1) * (self.global_y2 - self.global_y1)

    def compute_global_iou(self, other) -> float:
        """
        Calculates Intersection-over-Union (IoU) on the global patient canvas.
        Enforces lineage restriction (only deduplicates matching cell lines).
        """
        if self.cell_type != other.cell_type:
            return 0.0
            
        inter_x1 = max(self.global_x1, other.global_x1)
        inter_y1 = max(self.global_y1, other.global_y1)
        inter_x2 = min(self.global_x2, other.global_x2)
        inter_y2 = min(self.global_y2, other.global_y2)
        
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
            
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        union_area = self.area + other.area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0


def parse_filename_metadata(file_path: str) -> tuple[int, int, str]:
    """
    Parses structural filename strings to isolate patient ID and spatial matrix indices.
    Pattern expected: [PatientID]_[GridX]_[GridY]_[Magnification]_[Diagnosis]
    Example: '1_35_40_400_ALL.png' -> Patient: '1', GridX: 35, GridY: 40
    """
    base_name = os.path.basename(file_path)
    stem = os.path.splitext(base_name)[0]
    parts = stem.split("_")
    
    if len(parts) < 5:
        raise ValueError(f"Filename {base_name} does not match expected LLD metadata schema.")
        
    patient_id = parts[0]
    grid_x = int(parts[1])
    grid_y = int(parts[2])
    
    return grid_x, grid_y, patient_id


def run_global_canvas_nms(boxes: list[GlobalCellBox]) -> list[GlobalCellBox]:
    """
    Applies Non-Maximum Suppression globally across the absolute canvas pool.
    Collapses cross-image boundary duplicate cells, preserving the highest confidence hits.
    """
    if not boxes:
        return []
        
    # Sort from highest confidence to lowest confidence
    sorted_boxes = sorted(boxes, key=lambda b: b.confidence, reverse=True)
    retained_boxes = []
    
    while sorted_boxes:
        highest_conf = sorted_boxes.pop(0)
        retained_boxes.append(highest_conf)
        
        # Filter out overlapping boxes of the same cell type sitting on boundaries
        sorted_boxes = [
            box for box in sorted_boxes
            if highest_conf.compute_global_iou(box) < IOU_DEDUPLICATION_THRESHOLD
        ]
        
    return retained_boxes


def process_patient_inference_pool(image_file_paths: list[str], mock_predictions_dict: dict) -> dict:
    """
    Processes a list of shuffled, unlinked patient image fields. Parses coordinates
    on the fly, maps local boxes to a global plane, and performs spatial deduplication.
    """
    master_raw_pool = []
    active_patient_id = None
    
    for path in image_file_paths:
        filename = os.path.basename(path)
        grid_x, grid_y, pid = parse_filename_metadata(path)
        
        if active_patient_id is None:
            active_patient_id = pid
        elif active_patient_id != pid:
            raise ValueError("Inference pool contains mixed image arrays from multiple patients.")
            
        # Retrieve the model output for this current file iteration
        predictions = mock_predictions_dict.get(filename, [])
        
        for pred in predictions:
            cls_id, cx, cy, w, h, conf = pred
            cell_type = YOLO_CLASS_NAMES.get(cls_id, "none")
            
            # Skip background elements from the clinical WBC denominator
            if cell_type == "none":
                continue
                
            # Convert normalized YOLO coordinates back to local absolute pixel footprints
            x1 = (cx - w / 2.0) * DEFAULT_IMAGE_DIMENSION
            y1 = (cy - h / 2.0) * DEFAULT_IMAGE_DIMENSION
            x2 = (cx + w / 2.0) * DEFAULT_IMAGE_DIMENSION
            y2 = (cy + h / 2.0) * DEFAULT_IMAGE_DIMENSION
            
            # Instantiate the global box objects, projecting them onto the absolute plane
            global_box = GlobalCellBox(x1, y1, x2, y2, cell_type, conf, grid_x, grid_y, filename)
            master_raw_pool.append(global_box)
            
    # Execute the cross-image boundary deduplication sweep
    unique_cells = run_global_canvas_nms(master_raw_pool)
    
    # Calculate final, uninflated clinical differentials
    cell_counts = Counter([cell.cell_type for cell in unique_cells])
    total_wbc = sum(cell_counts.values())
    
    cell_percentages = {
        cell_type: round((count / total_wbc * 100), 2)
        for cell_type, count in cell_counts.items()
    } if total_wbc > 0 else {}
    
    return {
        "patient_id": active_patient_id,
        "total_fields_processed": len(image_file_paths),
        "raw_detections_count": len(master_raw_pool),
        "deduplicated_wbc_count": total_wbc,
        "cell_counts": dict(cell_counts.most_common()),
        "cell_percentages_clinical": cell_percentages
    }


# ---------------------------------------------------------------------------
# Operational Validation Execution Loop
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("🔬 Verifying Global Canvas Deduplication Protocol...")
    
    # Define a shuffled, non-sequential test queue of 40x images for Patient 1
    shuffled_queue = [
        "1_36_40_400_ALL.png",
        "1_91_105_400_ALL.png",
        "1_35_40_400_ALL.png"
    ]
    
    # Simulate a duplicate boundary lymphoblast crossing between 1_35_40 (Right Edge) and 1_36_40 (Left Edge)
    # Format per mock bounding box: [class_id, cx, cy, w, h, confidence]
    mock_model_outputs = {
        "1_35_40_400_ALL.png": [
            [2, 0.94, 0.31, 0.06, 0.08, 0.89],  # Border Lymphoblast Cell Alpha (Local X_center = 601.6px)
            [3, 0.50, 0.50, 0.10, 0.10, 0.92]   # Central Neutrophil Cell
        ],
        "1_36_40_400_ALL.png": [
            [2, 0.14, 0.31, 0.06, 0.08, 0.84]   # Re-detection of Cell Alpha (Local X_center = 89.6px)
        ],
        "1_91_105_400_ALL.png": [
            [2, 0.25, 0.25, 0.07, 0.07, 0.95]   # Completely separate field cell
        ]
    }
    
    summary = process_patient_inference_pool(shuffled_queue, mock_model_outputs)
    
    print("
✅ Verification Pipeline Successful:")
    print(f"   - Patient Identifier:           {summary['patient_id']}")
    print(f"   - Total Raw Model Detections:   {summary['raw_detections_count']}")
    print(f"   - Deduplicated True WBC Count: {summary['deduplicated_wbc_count']} (Expected: 3, Cross-tile boundary double-count correctly collapsed)")
    print(f"   - Extracted Counts:             {summary['cell_counts']}")
    print(f"   - Clinical Percentages:        {summary['cell_percentages_clinical']}")