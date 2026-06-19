"""DinoBloom + MLP attribute evaluation (GT crops and YOLO e2e)."""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO_ROOT))

from data.cell_dataset import CellAttributeDataset, attr_target_value, load_manifest  # noqa: E402
from utils.boxes import match_gt_to_best_det  # noqa: E402
from utils.e2e_attributes import (  # noqa: E402
    det_crops_from_xyxy,
    gt_row_to_legacy_targets,
    row_all_attrs_labeled,
    xywhn_to_xyxy,
)
from utils.labels import ATTR_NAMES, IGNORE_ATTR  # noqa: E402
from utils.metrics import attribute_metrics, attribute_metrics_legacy  # noqa: E402

from agentic_hematology.detection_agent_dinobloom import (  # noqa: E402
    DINOBLOOM_VARIANTS,
    DinoBloomEmbedder,
    build_dinobloom_attribute_head,
    resolve_dinobloom_weights,
)


@torch.no_grad()
def embed_tensor_batch(embedder: DinoBloomEmbedder, x: torch.Tensor) -> torch.Tensor:
    """Embed pre-normalized crop tensors (CellAttributeDataset layout)."""
    x = x.to(embedder.device)
    model = embedder.model
    if hasattr(model, "forward_features"):
        feats = model.forward_features(x)
        if isinstance(feats, dict):
            if "x_norm_clstoken" in feats:
                emb = feats["x_norm_clstoken"]
            elif "cls_token" in feats:
                emb = feats["cls_token"]
            else:
                emb = next(iter(feats.values()))
        else:
            emb = feats
    else:
        emb = model(x)

    if emb.ndim > 2:
        emb = emb[:, 0] if emb.shape[1] > 1 else emb.mean(dim=1)
    return emb


def load_dinobloom_attribute_stack(
    attr_weights: Path,
    device: torch.device,
    *,
    dinobloom_weights: str | Path = "auto",
    dinobloom_hub_dir: str | None = None,
) -> tuple[DinoBloomEmbedder, nn.Module, int, dict]:
    ckpt = torch.load(attr_weights, map_location="cpu", weights_only=False)
    if not isinstance(ckpt, dict) or "model" not in ckpt:
        raise ValueError(f"Expected DinoBloom MLP checkpoint with 'model' state dict: {attr_weights}")

    variant = str(ckpt.get("dinobloom_variant", "l"))
    imgsz = int(ckpt.get("imgsz", 224))
    embed_dim = int(ckpt.get("embed_dim", DINOBLOOM_VARIANTS[variant][1]))
    num_attrs = int(ckpt.get("num_attrs", len(ATTR_NAMES)))

    if str(dinobloom_weights) == "auto" and ckpt.get("dinobloom_weights"):
        backbone_path = str(ckpt["dinobloom_weights"])
    else:
        backbone_path = resolve_dinobloom_weights(str(dinobloom_weights), variant)

    embedder = DinoBloomEmbedder(
        weights_path=backbone_path,
        variant=variant,
        device=str(device),
        hub_dir=dinobloom_hub_dir,
    )
    for param in embedder.model.parameters():
        param.requires_grad = False

    head = build_dinobloom_attribute_head(embed_dim, num_attrs)
    head.load_state_dict(ckpt["model"])
    head.to(device)
    head.eval()
    return embedder, head, imgsz, ckpt


@torch.no_grad()
def predict_dinobloom_attributes_pil(
    embedder: DinoBloomEmbedder,
    head: nn.Module,
    crops: list[Image.Image],
    device: torch.device,
    batch: int = 64,
) -> np.ndarray:
    if not crops:
        return np.zeros((0, len(ATTR_NAMES)), dtype=np.float32)

    head.eval()
    outs: list[np.ndarray] = []
    for start in range(0, len(crops), batch):
        batch_crops = crops[start : start + batch]
        embeddings = embedder.embed_pil_batch(batch_crops)
        logits = head(torch.from_numpy(embeddings).to(device))
        outs.append(torch.sigmoid(logits).cpu().numpy())
    return np.concatenate(outs, axis=0)


@torch.no_grad()
def eval_attributes_gt_dinobloom(
    attr_weights: Path,
    manifest: Path,
    split: str,
    device: torch.device,
    batch: int,
    *,
    dinobloom_weights: str | Path = "auto",
    dinobloom_hub_dir: str | None = None,
) -> dict:
    embedder, head, imgsz, _ = load_dinobloom_attribute_stack(
        attr_weights,
        device,
        dinobloom_weights=dinobloom_weights,
        dinobloom_hub_dir=dinobloom_hub_dir,
    )
    ds = CellAttributeDataset(manifest, split, imgsz=imgsz)
    loader = DataLoader(ds, batch_size=batch, shuffle=False, num_workers=4)
    ys, ps = [], []
    for x, y, _ in loader:
        x = x.to(device)
        emb = embed_tensor_batch(embedder, x)
        logits = head(emb)
        ys.append(y.numpy())
        ps.append(torch.sigmoid(logits).cpu().numpy())
    if not ys:
        return {}
    y_true = np.concatenate(ys, axis=0)
    y_pred = np.concatenate(ps, axis=0)
    return attribute_metrics(y_true, y_pred, ATTR_NAMES)


@torch.no_grad()
def eval_attributes_e2e_dinobloom(
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
    dinobloom_weights: str | Path = "auto",
    dinobloom_hub_dir: str | None = None,
) -> tuple[dict, dict, list | None]:
    rows = load_manifest(manifest, split)
    by_image: dict[str, list[dict]] = defaultdict(list)
    cell_filter = row_all_attrs_labeled if legacy else lambda r: any(int(r[n]) != IGNORE_ATTR for n in ATTR_NAMES)
    for row in rows:
        if cell_filter(row):
            by_image[row["image"]].append(row)

    det = YOLO(str(det_weights))
    embedder, head, _, _ = load_dinobloom_attribute_stack(
        attr_weights,
        device,
        dinobloom_weights=dinobloom_weights,
        dinobloom_hub_dir=dinobloom_hub_dir,
    )

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
        all_det_attrs = predict_dinobloom_attributes_pil(
            embedder, head, det_crops, device, batch=attr_batch
        )

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
                y_true_list.append(
                    np.array([attr_target_value(int(row[n])) for n in ATTR_NAMES], dtype=np.float32)
                )
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
