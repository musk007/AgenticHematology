"""DinoBloom + MLP attribute evaluation (GT crops and YOLO e2e).

Uses the same preprocessing, cell filters, metrics and e2e loop as the
EfficientNet arm (utils/e2e_attributes.py), so the ablation compares backbones
and nothing else.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO_ROOT))

from data.cell_dataset import CellAttributeDataset  # noqa: E402
from utils.e2e_attributes import (  # noqa: E402
    N_BINARY,
    crops_to_tensor,
    eval_attributes_e2e
)
from utils.labels import BINARY_ATTRS, CELL_SIZE_N_CLASSES  # noqa: E402
from utils.metrics import attribute_metrics, cell_size_metrics  # noqa: E402

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
    num_attrs = int(ckpt.get("num_attrs", N_BINARY + CELL_SIZE_N_CLASSES))

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
    embedder.model.eval()

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
    imgsz: int,
    batch: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (binary probabilities (N, 6), predicted size class (N,))."""
    if not crops:
        return (
            np.zeros((0, N_BINARY), dtype=np.float32),
            np.zeros((0,), dtype=np.int64)
        )

    probs, sizes = [], []
    for start in range(0, len(crops), batch):
        # same preprocessing as CellAttributeDataset / the EfficientNet arm
        x = crops_to_tensor(crops[start : start + batch], imgsz)
        emb = embed_tensor_batch(embedder, x)
        logits = head(emb)
        probs.append(torch.sigmoid(logits[:, :N_BINARY]).cpu().numpy())
        sizes.append(logits[:, N_BINARY:].argmax(1).cpu().numpy())
    return np.concatenate(probs, axis=0), np.concatenate(sizes, axis=0)


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
    ys, ps, sz_t, sz_p = [], [], [], []
    for x, y, s, _ in loader:
        emb = embed_tensor_batch(embedder, x.to(device))
        logits = head(emb)
        ys.append(y.numpy())
        ps.append(torch.sigmoid(logits[:, :N_BINARY]).cpu().numpy())
        sz_t.append(s.numpy())
        sz_p.append(logits[:, N_BINARY:].argmax(1).cpu().numpy())
    if not ys:
        return {}
    metrics = attribute_metrics(
        np.concatenate(ys, axis=0), np.concatenate(ps, axis=0), BINARY_ATTRS
    )
    size_m = cell_size_metrics(np.concatenate(sz_t), np.concatenate(sz_p))
    if size_m:
        metrics["Cell_Size"] = size_m
    return metrics


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
    legacy: bool = False,
    dinobloom_weights: str | Path = "auto",
    dinobloom_hub_dir: str | None = None,
) -> tuple[dict, dict, list | None]:
    """Same e2e loop as the EfficientNet arm, with a DinoBloom predict_fn."""
    embedder, head, imgsz, _ = load_dinobloom_attribute_stack(
        attr_weights,
        device,
        dinobloom_weights=dinobloom_weights,
        dinobloom_hub_dir=dinobloom_hub_dir,
    )

    def predict_fn(crops, batch):
        return predict_dinobloom_attributes_pil(
            embedder, head, crops, device, imgsz, batch=batch
        )

    return eval_attributes_e2e(
        det_weights,
        attr_weights,
        manifest,
        split,
        device,
        conf=conf,
        iou_nms=iou_nms,
        max_det=max_det,
        imgsz_det=imgsz_det,
        attr_batch=attr_batch,
        pad=pad,
        det_device=det_device,
        legacy=legacy,
        predict_fn=predict_fn,
    )
