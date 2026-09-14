"""End-to-end attribute eval: YOLO detections -> attribute head -> GT matching.

Two phases, as in the legacy val.py:
  1. inference (no GT): run the attribute head on every detection crop
  2. scoring (GT here): for each GT cell take the highest-IoU detection and
     compare that detection's prediction to the GT labels

Attribute layout: 6 binary attributes (BINARY_ATTRS, 2 = unannotated) plus a
3-class Cell_Size head. Cell_Size uses 2 = large, so it is NEVER included in
"is this cell annotated" tests.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO

from data.cell_dataset import (
    IMAGENET_MEAN,
    IMAGENET_STD,
    SIZE_IGNORE_INDEX,
    attr_target_value,
    load_manifest
)
from models.attribute_net import build_attribute_model
from utils.boxes import match_gt_to_best_det
from utils.labels import (
    BINARY_ATTRS, 
    IGNORE_ATTR, 
    CELL_SIZE_N_CLASSES,
    crop_with_padding, 
    xywhn_to_xyxy
)
from utils.metrics import attribute_metrics, attribute_metrics_legacy, cell_size_metrics

N_BINARY = len(BINARY_ATTRS)

# ---------------------------------------------------------------------------
# preprocessing — must match CellAttributeDataset exactly
# ---------------------------------------------------------------------------

def crops_to_tensor(crops: list[Image.Image], imgsz: int) -> torch.Tensor:
    arrs = []
    for crop in crops:
        c = crop.resize((imgsz, imgsz), Image.BILINEAR)
        a = np.asarray(c.convert("RGB"), dtype=np.float32) / 255.0
        a = (a - np.array(IMAGENET_MEAN)) / np.array(IMAGENET_STD)
        arrs.append(a.transpose(2, 0, 1))
    if not arrs:
        return torch.zeros((0, 3, imgsz, imgsz), dtype=torch.float32)
    return torch.from_numpy(np.stack(arrs)).float()

def load_attribute_model(weights: Path, device: torch.device):
    ckpt = torch.load(weights, map_location=device, weights_only=False)
    model = build_attribute_model(
        num_binary=N_BINARY,
        num_size=CELL_SIZE_N_CLASSES,
        backbone=ckpt.get("backbone", "efficientnet_b0"),
        pretrained=False,
    )
    model.load_state_dict(ckpt["model"])
    model.to(device)
    model.eval()
    return model, int(ckpt.get("imgsz", 224)), ckpt


@torch.no_grad()
def predict_attributes_pil(
    model,
    crops: list[Image.Image],
    device: torch.device,
    imgsz: int,
    batch: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (binary probabilities (N, 6), predicted size class (N,))."""
    if not crops:
        return (
            np.zeros((0, N_BINARY), dtype=np.float32),
            np.zeros((0,), dtype=np.int64),
        )
    probs, sizes = [], []
    for start in range(0, len(crops), batch):
        x = crops_to_tensor(crops[start : start + batch], imgsz).to(device)
        bin_logits, size_logits = model(x)
        probs.append(torch.sigmoid(bin_logits).cpu().numpy())
        sizes.append(size_logits.argmax(1).cpu().numpy())
    return np.concatenate(probs, axis=0), np.concatenate(sizes, axis=0)

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
    """Legacy val.py filter: every BINARY attribute must be 0/1.

    Cell_Size is excluded — 2 there means 'large', not unannotated.
    """
    return all(int(row[name]) != IGNORE_ATTR for name in BINARY_ATTRS)


def row_any_attr_labeled(row: dict) -> bool:
    return any(int(row[name]) != IGNORE_ATTR for name in BINARY_ATTRS)


def gt_row_to_legacy_targets(row: dict) -> np.ndarray:
    return np.array([int(row[name]) for name in BINARY_ATTRS], dtype=np.float32)


def gt_row_to_targets(row: dict) -> np.ndarray:
    return np.array([attr_target_value(int(row[name])) for name in BINARY_ATTRS], dtype=np.float32)


def gt_row_size_target(row: dict) -> int:
    v = int(row["Cell_Size"])
    return v if 0 <= v < CELL_SIZE_N_CLASSES else SIZE_IGNORE_INDEX

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
    legacy: bool = False,
    predict_fn=None,
) -> tuple[dict, dict, list | None]:
    """Score attribute predictions made on YOLO detections against GT cells.

    ``predict_fn(crops, batch) -> (bin_probs, size_pred)`` lets another backbone
    (e.g. DinoBloom) reuse this loop; defaults to the EfficientNet head.
    """
    rows = load_manifest(manifest, split)
    by_image: dict[str, list[dict]] = defaultdict(list)
    cell_filter = row_all_attrs_labeled if legacy else row_any_attr_labeled
    for row in rows:
        if cell_filter(row):
            by_image[row["image"]].append(row)

    det = YOLO(str(det_weights))
    if predict_fn is None:
        attr_model, attr_imgsz, _ = load_attribute_model(attr_weights, device)
        def predict_fn(crops, batch):  # noqa: F811
            return predict_attributes_pil(attr_model, crops, device, attr_imgsz, batch=batch)

    y_true_list: list[np.ndarray] = []
    y_pred_list: list[np.ndarray] = []
    size_true: list[int] = []
    size_pred: list[int] = []
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
        all_bin, all_size = predict_fn(det_crops, attr_batch)

        det_idx, best_iou = match_gt_to_best_det(gt_xyxy, det_xyxy)
        for row, di, iou_val in zip(img_rows, det_idx, best_iou):
            if di < 0:
                n_skipped_no_det += 1
                continue
            y_true_list.append(
                gt_row_to_legacy_targets(row) if legacy else gt_row_to_targets(row)
            )
            y_pred_list.append(all_bin[di])
            size_true.append(gt_row_size_target(row))
            size_pred.append(int(all_size[di]))
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
        metrics, table_rows = attribute_metrics_legacy(y_true, y_pred, BINARY_ATTRS)
    else:
        metrics = attribute_metrics(y_true, y_pred, BINARY_ATTRS)

    size_m = cell_size_metrics(np.array(size_true), np.array(size_pred))
    if size_m:
        metrics["Cell_Size"] = size_m
    return metrics, stats, table_rows
