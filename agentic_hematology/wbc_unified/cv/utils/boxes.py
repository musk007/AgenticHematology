"""Box IoU and GT-to-detection matching (aligned with legacy val.py my_process_batch)."""
from __future__ import annotations

import numpy as np


def box_iou_xyxy(gt: np.ndarray, det: np.ndarray) -> np.ndarray:
    """IoU between GT (M,4) and detections (N,4), both xyxy pixel coords."""
    if gt.size == 0 or det.size == 0:
        return np.zeros((gt.shape[0], det.shape[0]), dtype=np.float32)

    gt = gt.astype(np.float32)
    det = det.astype(np.float32)
    inter_x1 = np.maximum(gt[:, None, 0], det[None, :, 0])
    inter_y1 = np.maximum(gt[:, None, 1], det[None, :, 1])
    inter_x2 = np.minimum(gt[:, None, 2], det[None, :, 2])
    inter_y2 = np.minimum(gt[:, None, 3], det[None, :, 3])
    inter_w = np.clip(inter_x2 - inter_x1, 0, None)
    inter_h = np.clip(inter_y2 - inter_y1, 0, None)
    inter = inter_w * inter_h

    area_gt = np.clip(gt[:, 2] - gt[:, 0], 0, None) * np.clip(gt[:, 3] - gt[:, 1], 0, None)
    area_det = np.clip(det[:, 2] - det[:, 0], 0, None) * np.clip(det[:, 3] - det[:, 1], 0, None)
    union = area_gt[:, None] + area_det[None, :] - inter + 1e-9
    return inter / union


def match_gt_to_best_det(gt_xyxy: np.ndarray, det_xyxy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    For each GT box, pick the detection with highest IoU (no class filter).
    Mirrors legacy val.py my_process_batch top_indices = argmax(iou, dim=1).
    Returns (det_indices[M], ious[M]); det_indices[i] = -1 when there are no detections.
    """
    n_gt = gt_xyxy.shape[0]
    if n_gt == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
    if det_xyxy.size == 0:
        return np.full(n_gt, -1, dtype=np.int64), np.zeros(n_gt, dtype=np.float32)

    iou = box_iou_xyxy(gt_xyxy, det_xyxy)
    det_idx = iou.argmax(axis=1).astype(np.int64)
    best_iou = iou[np.arange(n_gt), det_idx]
    return det_idx, best_iou
