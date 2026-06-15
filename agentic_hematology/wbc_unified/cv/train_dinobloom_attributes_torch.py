#!/usr/bin/env python3
"""Train DinoBloom attribute head on LLD cell crops (frozen backbone, like linear probe + MLP).

Uses the same manifest/splits/loss as ``train_attributes.py`` (EfficientNet), but keeps
the MarrLab DinoBloom foundation weights frozen and only trains a small multi-label head.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml
from torch.utils.data import DataLoader
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
REPO_PARENT = ROOT.parent.parent.parent
sys.path.insert(0, str(REPO_PARENT))
sys.path.insert(0, str(ROOT))

from agentic_hematology.detection_agent_dinobloom import (  # noqa: E402
    DinoBloomEmbedder,
    build_dinobloom_attribute_head,
    resolve_dinobloom_weights,
)
from data.cell_dataset import CellAttributeDataset, compute_pos_weights  # noqa: E402
from models.attribute_net import masked_bce_loss  # noqa: E402
from utils.labels import ATTR_NAMES  # noqa: E402
from utils.metrics import attribute_metrics  # noqa: E402


def _resolve_torch_device(device: str) -> torch.device:
    try:
        from agentic_hematology.detection_agent_v2 import _resolve_device
    except ModuleNotFoundError:
        from detection_agent_v2 import _resolve_device  # type: ignore

    torch_dev, _ = _resolve_device(device)
    if str(torch_dev).startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA was requested but torch.cuda.is_available() is false. "
            "On Slurm: submit with --gres=gpu:1 --qos=cscc-gpu-qos, load "
            "'module load nvidia/cuda/11.8' before conda, and set "
            "LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH."
        )
    return torch.device(torch_dev)


class DinoBloomAttributeNet(nn.Module):
    """Frozen DinoBloom encoder + trainable attribute head."""

    def __init__(self, embedder: DinoBloomEmbedder):
        super().__init__()
        self.encoder = embedder.model
        for param in self.encoder.parameters():
            param.requires_grad = False
        self.encoder.eval()
        self.embed_dim = embedder.embed_dim
        self.head = build_dinobloom_attribute_head(self.embed_dim, len(ATTR_NAMES))

    @torch.no_grad()
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        if hasattr(self.encoder, "forward_features"):
            feats = self.encoder.forward_features(x)
            if isinstance(feats, dict):
                if "x_norm_clstoken" in feats:
                    return feats["x_norm_clstoken"]
                return next(iter(feats.values()))
            return feats
        return self.encoder(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        emb = self.encode(x)
        return self.head(emb)


@torch.no_grad()
def evaluate(model: DinoBloomAttributeNet, loader: DataLoader, device: torch.device) -> dict:
    model.eval()
    ys, ps = [], []
    for x, y, _ in loader:
        x = x.to(device)
        logits = model(x)
        ys.append(y.numpy())
        ps.append(torch.sigmoid(logits).cpu().numpy())
    if not ys:
        return {}
    y_true = np.concatenate(ys, axis=0)
    y_pred = np.concatenate(ps, axis=0)
    return attribute_metrics(y_true, y_pred, ATTR_NAMES)


def main() -> None:
    ap = argparse.ArgumentParser(description="Train DinoBloom attribute head on LLD manifest crops.")
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "dataset.yaml")
    ap.add_argument("--manifest", type=Path, default=None, help="Override attr manifest CSV path.")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--device", type=str, default="0")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dinobloom-weights", type=str, default="auto")
    ap.add_argument("--dinobloom-variant", choices=["s", "b", "l", "g"], default="l")
    ap.add_argument("--dinobloom-hub-dir", type=Path, default=None)
    ap.add_argument("--project", type=Path, default=ROOT / "runs" / "attribute_dinobloom")
    ap.add_argument("--name", type=str, default="train")
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    manifest = Path(args.manifest) if args.manifest else Path(cfg["attr_manifest"])
    if not manifest.is_file():
        sys.exit(f"Missing manifest {manifest}. Run: python data/prepare_dataset.py")

    device = _resolve_torch_device(args.device)
    save_dir = args.project / args.name
    save_dir.mkdir(parents=True, exist_ok=True)

    train_ds = CellAttributeDataset(manifest, "train", imgsz=args.imgsz)
    val_ds = CellAttributeDataset(manifest, "test", imgsz=args.imgsz)
    print(
        f"DinoBloom attribute train cells: {len(train_ds)}  val: {len(val_ds)}  device={device}",
        flush=True,
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch,
        shuffle=True,
        num_workers=args.workers,
        pin_memory=True,
        drop_last=len(train_ds) >= args.batch,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=True,
    )

    weights_path = resolve_dinobloom_weights(args.dinobloom_weights, args.dinobloom_variant)
    embedder = DinoBloomEmbedder(
        weights_path=weights_path,
        variant=args.dinobloom_variant,
        device=str(device),
        hub_dir=str(args.dinobloom_hub_dir) if args.dinobloom_hub_dir else None,
    )
    model = DinoBloomAttributeNet(embedder).to(device)
    pos_weight = compute_pos_weights(manifest, "train").to(device)
    opt = torch.optim.AdamW(model.head.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)

    best_f1 = -1.0
    history = []

    for epoch in range(args.epochs):
        model.train()
        model.encoder.eval()
        running = 0.0
        n_batches = 0
        for x, y, _ in tqdm(train_loader, desc=f"epoch {epoch + 1}/{args.epochs}", leave=False):
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            logits = model(x)
            loss = masked_bce_loss(logits, y, pos_weight=pos_weight)
            loss.backward()
            nn.utils.clip_grad_norm_(model.head.parameters(), 5.0)
            opt.step()
            running += float(loss.item())
            n_batches += 1
        sched.step()

        metrics = evaluate(model, val_loader, device)
        mean_f1 = sum(m.get("f1", 0) for m in metrics.values()) / max(len(metrics), 1)
        row = {
            "epoch": epoch + 1,
            "train_loss": running / max(n_batches, 1),
            "mean_attr_f1": mean_f1,
            "per_attr": metrics,
        }
        history.append(row)
        print(f"epoch {epoch + 1}: loss={row['train_loss']:.4f}  mean_attr_f1={mean_f1:.4f}", flush=True)

        ckpt = {
            "model": model.head.state_dict(),
            "embed_dim": model.embed_dim,
            "num_attrs": len(ATTR_NAMES),
            "attr_names": ATTR_NAMES,
            "dinobloom_variant": args.dinobloom_variant,
            "dinobloom_weights": weights_path,
            "imgsz": args.imgsz,
            "epoch": epoch + 1,
            "metrics": metrics,
        }
        torch.save(ckpt, save_dir / "last_attr_dinobloom.pt")
        if mean_f1 >= best_f1:
            best_f1 = mean_f1
            torch.save(ckpt, save_dir / "best_attr_dinobloom.pt")

    (save_dir / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"Best DinoBloom attribute head: {save_dir / 'best_attr_dinobloom.pt'}  (mean_f1={best_f1:.4f})")


if __name__ == "__main__":
    main()
