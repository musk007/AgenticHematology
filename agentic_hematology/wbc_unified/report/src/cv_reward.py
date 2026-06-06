"""Stage-1 CV reward: detection + attributes vs GT labels (numpy, no torch)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .filename import parse_image_stem

ATTR_NAMES = [
    "Nuclear_Chromatin",
    "Nuclear_Shape",
    "Nucleus",
    "Cytoplasm",
    "Cytoplasmic_Basophilia",
    "Cytoplasmic_Vacuoles",
]
IGNORE_ATTR = 2
CLASS_NAMES = [
    "None",
    "Myeloblast",
    "Lymphoblast",
    "Neutrophil",
    "Atypical lymphocyte",
    "Promonocyte",
    "Monoblast",
    "Lymphocyte",
    "Myelocyte",
    "Abnormal promyelocyte",
    "Monocyte",
    "Metamyelocyte",
    "Eosinophil",
    "Basophil",
]


def _box_iou_xyxy(gt: np.ndarray, det: np.ndarray) -> np.ndarray:
    if gt.size == 0 or det.size == 0:
        return np.zeros((gt.shape[0], det.shape[0]), dtype=np.float32)
    inter_x1 = np.maximum(gt[:, None, 0], det[None, :, 0])
    inter_y1 = np.maximum(gt[:, None, 1], det[None, :, 1])
    inter_x2 = np.minimum(gt[:, None, 2], det[None, :, 2])
    inter_y2 = np.minimum(gt[:, None, 3], det[None, :, 3])
    inter = np.clip(inter_x2 - inter_x1, 0, None) * np.clip(inter_y2 - inter_y1, 0, None)
    area_gt = np.clip(gt[:, 2] - gt[:, 0], 0, None) * np.clip(gt[:, 3] - gt[:, 1], 0, None)
    area_det = np.clip(det[:, 2] - det[:, 0], 0, None) * np.clip(det[:, 3] - det[:, 1], 0, None)
    union = area_gt[:, None] + area_det[None, :] - inter + 1e-9
    return inter / union


def _xywhn_to_xyxy(xywhn: np.ndarray, w: int, h: int) -> np.ndarray:
    cx, cy, bw, bh = xywhn
    x1 = (cx - bw / 2) * w
    y1 = (cy - bh / 2) * h
    x2 = (cx + bw / 2) * w
    y2 = (cy + bh / 2) * h
    return np.array([x1, y1, x2, y2], dtype=np.float32)


def _load_gt_cells(label_path: Path, img_w: int, img_h: int) -> list[dict[str, Any]]:
    cells = []
    if not label_path.is_file():
        return cells
    for line in label_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            cls_id = int(float(parts[0]))
        except ValueError:
            continue
        if cls_id < 0 or cls_id >= len(CLASS_NAMES):
            continue
        if len(parts) < 11:
            continue
        if any(int(float(parts[5 + j])) == IGNORE_ATTR for j in range(len(ATTR_NAMES))):
            continue
        attrs = {ATTR_NAMES[j]: int(float(parts[5 + j])) for j in range(len(ATTR_NAMES))}
        xyxy = _xywhn_to_xyxy(np.array(parts[1:5], dtype=np.float32), img_w, img_h)
        cells.append(
            {
                "class_id": cls_id,
                "class_name": CLASS_NAMES[cls_id],
                "xyxy": xyxy,
                "attributes_bin": attrs,
            }
        )
    return cells


def _load_image_size(image_path: Path) -> tuple[int, int]:
    from PIL import Image

    with Image.open(image_path) as im:
        return im.size


def _pred_dets_xyxy(item: dict, conf_threshold: float = 0.001) -> list[dict]:
    image_path = Path(item["image"])
    w, h = _load_image_size(image_path)
    out = []
    for det in item.get("cells", []):
        conf = float(det.get("conf", 0))
        if conf < conf_threshold:
            continue
        xyxy = np.array(det["xyxy"], dtype=np.float32)
        if xyxy.max() <= 1.5:
            xyxy = _xywhn_to_xyxy(
                np.array(
                    [
                        (xyxy[0] + xyxy[2]) / 2 / w,
                        (xyxy[1] + xyxy[3]) / 2 / h,
                        (xyxy[2] - xyxy[0]) / w,
                        (xyxy[3] - xyxy[1]) / h,
                    ],
                    dtype=np.float32,
                ),
                w,
                h,
            )
        out.append(
            {
                "class_id": int(det.get("class_id", 0)),
                "class_name": det.get("class_name", CLASS_NAMES[0]),
                "xyxy": xyxy,
                "attributes_bin": det.get("attributes_bin", {}),
                "conf": conf,
            }
        )
    return out


def score_image_e2e(
    item: dict,
    data_root: Path,
    split: str = "test",
    iou_min: float = 0.3,
) -> dict[str, float]:
    """One image: GT cells matched to best det; class + attribute accuracy."""
    stem = Path(item["image"]).stem
    label_path = data_root / "attributes" / split / f"{stem}.txt"
    img_path = Path(item["image"])
    gt_cells = _load_gt_cells(label_path, *_load_image_size(img_path))
    pred_cells = _pred_dets_xyxy(item)

    if not gt_cells:
        return {"n_gt": 0.0, "det_score": 1.0, "attr_score": 1.0, "mean_iou": 1.0}

    gt_xyxy = np.stack([c["xyxy"] for c in gt_cells])
    det_xyxy = np.stack([c["xyxy"] for c in pred_cells]) if pred_cells else np.zeros((0, 4))
    if det_xyxy.size == 0:
        return {"n_gt": float(len(gt_cells)), "det_score": 0.0, "attr_score": 0.0, "mean_iou": 0.0}

    iou_mat = _box_iou_xyxy(gt_xyxy, det_xyxy)
    det_idx = iou_mat.argmax(axis=1)
    best_iou = iou_mat[np.arange(len(gt_cells)), det_idx]

    class_hits = 0
    attr_hits = 0
    attr_total = 0
    matched = 0
    for i, gt_c in enumerate(gt_cells):
        j = int(det_idx[i])
        iou = float(best_iou[i])
        if iou < iou_min:
            continue
        matched += 1
        pred_c = pred_cells[j]
        if pred_c["class_name"] == gt_c["class_name"]:
            class_hits += 1
        for attr in ATTR_NAMES:
            gv = gt_c["attributes_bin"].get(attr)
            pv = pred_c["attributes_bin"].get(attr)
            if gv is None or pv is None:
                continue
            attr_total += 1
            if int(pv) == int(gv):
                attr_hits += 1

    n_gt = len(gt_cells)
    det_score = class_hits / max(matched, 1) if matched else 0.0
    attr_score = attr_hits / max(attr_total, 1) if attr_total else 0.0
    return {
        "n_gt": float(n_gt),
        "n_matched": float(matched),
        "det_score": round(det_score, 4),
        "attr_score": round(attr_score, 4),
        "mean_iou": round(float(best_iou[best_iou >= iou_min].mean()) if (best_iou >= iou_min).any() else 0.0, 4),
    }


def score_patient_predictions(
    patient_id: str,
    pred_items: list[dict],
    data_root: Path,
    split: str = "test",
) -> dict[str, float]:
    per_img = [score_image_e2e(it, data_root, split=split) for it in pred_items]
    if not per_img:
        return {"det_score": 0.0, "attr_score": 0.0, "mean_iou": 0.0, "n_images": 0.0}
    det_scores = [x["det_score"] for x in per_img if x["n_gt"] > 0]
    attr_scores = [x["attr_score"] for x in per_img if x["n_gt"] > 0]
    ious = [x["mean_iou"] for x in per_img if x["n_gt"] > 0]
    return {
        "det_score": round(float(np.mean(det_scores)) if det_scores else 0.0, 4),
        "attr_score": round(float(np.mean(attr_scores)) if attr_scores else 0.0, 4),
        "mean_iou": round(float(np.mean(ious)) if ious else 0.0, 4),
        "n_images": float(len(per_img)),
    }


def morphology_attr_score(pred_summary: dict, gt_summary: dict) -> float:
    """Compare cohort morphology attr_pos_rate vectors."""
    pred_m = pred_summary.get("morphology_cohort") or {}
    gt_m = gt_summary.get("morphology_cohort") or {}
    if not gt_m:
        return 1.0
    errors = []
    for cls, gt_stats in gt_m.items():
        pred_stats = pred_m.get(cls)
        if not pred_stats:
            errors.append(1.0)
            continue
        gt_rates = gt_stats.get("attr_pos_rate") or {}
        pred_rates = pred_stats.get("attr_pos_rate") or {}
        for attr, gv in gt_rates.items():
            pv = pred_rates.get(attr, 0.0)
            errors.append(min(1.0, abs(float(pv) - float(gv))))
    return round(max(0.0, 1.0 - float(np.mean(errors)) if errors else 0.0), 4)


def load_predictions_by_patient(predictions_path: Path) -> dict[str, list[dict]]:
    data = json.loads(predictions_path.read_text(encoding="utf-8"))
    by_patient: dict[str, list[dict]] = {}
    for item in data:
        meta = parse_image_stem(Path(item["image"]).stem)
        pid = str(meta["patient_id"])
        by_patient.setdefault(pid, []).append(item)
    return by_patient


def score_patient_bundle(
    patient_id: str,
    pred_summary: dict,
    gt_summary: dict,
    pred_items: list[dict],
    data_root: Path,
    split: str = "test",
) -> dict[str, float]:
    from .report_metrics import compare_summaries

    cell = score_patient_predictions(patient_id, pred_items, data_root, split=split)
    summ = compare_summaries(pred_summary, gt_summary)
    summ_mae = summ.get("summary_mae_pct")
    summary_score = max(0.0, 1.0 - (summ_mae or 15.0) / 15.0) if summ_mae is not None else 0.0
    morph = morphology_attr_score(pred_summary, gt_summary)
    det_combined = 0.6 * cell["det_score"] + 0.4 * summary_score
    attr_combined = 0.5 * cell["attr_score"] + 0.5 * morph
    return {
        **cell,
        "summary_score": round(summary_score, 4),
        "morph_attr_score": morph,
        "det_reward": round(det_combined, 4),
        "attr_reward": round(attr_combined, 4),
    }
