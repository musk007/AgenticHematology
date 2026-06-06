"""End-to-end attribute eval aligned with legacy val.py (two-phase: infer on dets, then score)."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO

from data.cell_dataset import load_manifest
from infer import predict_attributes
from models.attribute_net import build_attribute_model
from utils.boxes import match_gt_to_best_det
from utils.labels import ATTR_NAMES, IGNORE_ATTR, crop_with_padding, xywhn_to_xyxy
from utils.metrics import attribute_metrics, attribute_metrics_legacy


def load_attribute_model(weights: Path, device: torch.device):
    ckpt = torch.load(weights, map_location=device, weights_only=False)
    model = build_attribute_model(
        num_attrs=len(ATTR_NAMES),
        backbone=ckpt.get("backbone", "efficientnet_b0"),
        pretrained=False,
    )
    model.load_state_dict(ckpt["model"])
    model.to(device)
    model.eval()
    return model, int(ckpt.get("imgsz", 224)), ckpt


def xyxy_to_xywhn(xyxy: np.ndarray, w: int, h: int) -> np.ndarray:
    x1, y1, x2, y2 = xyxy
    bw = max(x2 - x1, 1.0) / w
    bh = max(y2 - y1, 1.0) / h
    cx = (x1 + x2) / 2 / w
    cy = (y1 + y2) / 2 / h
    return np.array([cx, cy, bw, bh], dtype=np.float32)


def det_crops_from_xyxy(image: Image.Image, det_xyxy: np.ndarray, pad: float) -> list[Image.Image]:
    w, h = image.size
    crops = []
    for xyxy in det_xyxy:
        xywhn = xyxy_to_xywhn(xyxy, w, h)
        x1, y1, x2, y2 = crop_with_padding(w, h, xywhn, pad=pad)
        crops.append(image.crop((x1, y1, x2, y2)))
    return crops


def row_all_attrs_labeled(row: dict) -> bool:
    """Legacy val.py: include cell only if all(x != 2 for x in label)."""
    return all(int(row[name]) != IGNORE_ATTR for name in ATTR_NAMES)


def gt_row_to_legacy_targets(row: dict) -> np.ndarray:
    return np.array([int(row[name]) for name in ATTR_NAMES], dtype=np.float32)


@torch.no_grad()
def eval_attributes_e2e(
    det_weights: Path,
    attr_weights: Path,
    manifest: Path,
    split: str,
    device: torch.device,
    *,
    conf: float = 0.001,
    iou_nms: float = 0.6,
    max_det: int = 300,
    imgsz_det: int = 640,
    attr_batch: int = 64,
    pad: float = 0.15,
    det_device: str = "0",
    legacy: bool = True,
) -> tuple[dict, dict, list | None]:
    """
    Legacy val.py / test.py (batch_size=1) attribute scoring:

    Phase 1 — inference (no GT):
      For every detection box, run attribute head on that det crop.

    Phase 2 — metrics only (GT used here):
      For each GT cell, pick detection with highest IoU (my_process_batch argmax).
      Compare that detection's attribute prediction to GT labels.

    legacy=True matches val.py filters and sklearn metrics:
      - conf_thres=0.001, iou_thres=0.6, max_det=300
      - skip cells where any attribute == 2 (all six must be 0/1)
    """
    rows = load_manifest(manifest, split)
    by_image: dict[str, list[dict]] = defaultdict(list)
    cell_filter = row_all_attrs_labeled if legacy else lambda r: any(int(r[n]) != IGNORE_ATTR for n in ATTR_NAMES)
    for row in rows:
        if cell_filter(row):
            by_image[row["image"]].append(row)

    det = YOLO(str(det_weights))
    attr_model, attr_imgsz, _ = load_attribute_model(attr_weights, device)

    y_true_list: list[np.ndarray] = []
    y_pred_list: list[np.ndarray] = []
    ious: list[float] = []
    n_gt = 0
    n_matched = 0
    n_skipped_no_det = 0

    for img_path_str, img_rows in sorted(by_image.items()):
        img_path = Path(img_path_str)
        if not img_path.is_file():
            continue

        res = det.predict(
            source=str(img_path),
            conf=conf,
            iou=iou_nms,
            imgsz=imgsz_det,
            max_det=max_det,
            device=det_device,
            verbose=False,
        )[0]

        image = Image.open(img_path).convert("RGB")
        w, h = image.size

        if res.boxes is not None and len(res.boxes):
            det_xyxy = res.boxes.xyxy.cpu().numpy().astype(np.float32)
        else:
            det_xyxy = np.zeros((0, 4), dtype=np.float32)

        gt_xyxy = np.stack(
            [
                xywhn_to_xyxy(
                    np.array([float(r["x"]), float(r["y"]), float(r["w"]), float(r["h"])], dtype=np.float32),
                    w,
                    h,
                )
                for r in img_rows
            ],
            axis=0,
        )
        n_gt += len(img_rows)

        if det_xyxy.size == 0:
            n_skipped_no_det += len(img_rows)
            continue

        det_crops = det_crops_from_xyxy(image, det_xyxy, pad=pad)
        all_det_attrs = predict_attributes(attr_model, det_crops, device, attr_imgsz, batch=attr_batch)

        det_idx, best_iou = match_gt_to_best_det(gt_xyxy, det_xyxy)
        for row, di, iou_val in zip(img_rows, det_idx, best_iou):
            if di < 0:
                n_skipped_no_det += 1
                continue
            if not cell_filter(row):
                continue
            if legacy:
                y_true_list.append(gt_row_to_legacy_targets(row))
            else:
                from data.cell_dataset import attr_target_value

                y_true_list.append(np.array([attr_target_value(int(row[n])) for n in ATTR_NAMES], dtype=np.float32))
            y_pred_list.append(all_det_attrs[di])
            ious.append(float(iou_val))
            n_matched += 1

    stats = {
        "n_gt_cells": n_gt,
        "n_matched": n_matched,
        "n_skipped_no_det": n_skipped_no_det,
        "mean_match_iou": float(np.mean(ious)) if ious else 0.0,
    }
    if not y_true_list:
        return {}, stats, None

    y_true = np.stack(y_true_list, axis=0)
    y_pred = np.stack(y_pred_list, axis=0)
    table_rows = None
    if legacy:
        metrics, table_rows = attribute_metrics_legacy(y_true, y_pred, ATTR_NAMES)
    else:
        metrics = attribute_metrics(y_true, y_pred, ATTR_NAMES)
    return metrics, stats, table_rows
