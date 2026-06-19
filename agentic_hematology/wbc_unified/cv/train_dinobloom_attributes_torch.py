#!/usr/bin/env python3
"""Train DinoBloom MLP attribute head on GT cell crops (frozen MarrLab backbone).

Mirrors ``train_attributes.py`` (EfficientNet) for a fair ablation:
  - same ``attr_manifest.csv`` train/test split
  - same 6 binary morphology attributes + masked BCE
  - frozen foundation model + trainable MLP head only

Output checkpoint (``best_attr_dinobloom.pt``) is loaded by
``DinoBloomAttributeClassifier`` with ``--dinobloom-attr-mode probes``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml
from torch.utils.data import DataLoader
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
AGENTIC = ROOT.parent.parent
REPO_ROOT = AGENTIC.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO_ROOT))

from data.cell_dataset import CellAttributeDataset, compute_pos_weights  # noqa: E402
from models.attribute_net import masked_bce_loss  # noqa: E402
from utils.labels import ATTR_NAMES  # noqa: E402
from utils.metrics import attribute_metrics  # noqa: E402

from agentic_hematology.detection_agent_dinobloom import (  # noqa: E402
    DINOBLOOM_VARIANTS,
    DinoBloomEmbedder,
    build_dinobloom_attribute_head,
    resolve_dinobloom_weights,
)


@torch.no_grad()
def embed_tensor_batch(embedder: DinoBloomEmbedder, x: torch.Tensor) -> torch.Tensor:
    """Embed pre-normalized crop tensors (same layout as CellAttributeDataset)."""
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


@torch.no_grad()
def evaluate(
    embedder: DinoBloomEmbedder,
    head: nn.Module,
    loader: DataLoader,
    device: torch.device,
    pos_weight: torch.Tensor,
) -> dict:
    head.eval()
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


def main() -> None:
    ap = argparse.ArgumentParser(description="Train DinoBloom attribute MLP on GT crops.")
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "dataset.yaml")
    ap.add_argument("--manifest", type=Path, default=None, help="Override attr manifest CSV.")
    ap.add_argument("--dinobloom-weights", type=str, default="auto")
    ap.add_argument("--dinobloom-variant", choices=["s", "b", "l", "g"], default="l")
    ap.add_argument("--dinobloom-hub-dir", type=str, default=None)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--device", type=str, default="0")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--project", type=Path, default=ROOT / "runs" / "attribute_dinobloom")
    ap.add_argument("--name", type=str, default="train")
    args = ap.parse_args()

    if args.manifest is not None:
        manifest = Path(args.manifest)
        if not manifest.is_file() and not manifest.is_absolute():
            manifest = (ROOT / manifest).resolve()
    else:
        cfg = yaml.safe_load(args.config.read_text())
        manifest = Path(cfg["attr_manifest"])

    if not manifest.is_file():
        raise SystemExit(
            f"Missing manifest {manifest}. Run: python data/prepare_dataset.py "
            f"--data-root <LeukemiaDataset_Organized>"
        )

    device = torch.device(f"cuda:{args.device}" if args.device.isdigit() else args.device)
    save_dir = args.project / args.name
    save_dir.mkdir(parents=True, exist_ok=True)

    _, embed_dim = DINOBLOOM_VARIANTS[args.dinobloom_variant]
    weights_path = resolve_dinobloom_weights(args.dinobloom_weights, args.dinobloom_variant)

    print(f"Loading frozen DinoBloom-{args.dinobloom_variant.upper()} from {weights_path}")
    embedder = DinoBloomEmbedder(
        weights_path=weights_path,
        variant=args.dinobloom_variant,
        device=str(device),
        hub_dir=args.dinobloom_hub_dir,
    )
    for param in embedder.model.parameters():
        param.requires_grad = False

    train_ds = CellAttributeDataset(manifest, "train", imgsz=args.imgsz)
    val_ds = CellAttributeDataset(manifest, "test", imgsz=args.imgsz)
    print(f"DinoBloom attribute train cells: {len(train_ds)}  val: {len(val_ds)}")

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

    pos_weight = compute_pos_weights(manifest, "train").to(device)
    head = build_dinobloom_attribute_head(embed_dim, len(ATTR_NAMES)).to(device)
    opt = torch.optim.AdamW(head.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)

    best_f1 = -1.0
    history: list[dict] = []

    for epoch in range(args.epochs):
        head.train()
        running = 0.0
        n_batches = 0
        pbar = tqdm(train_loader, desc=f"epoch {epoch + 1}/{args.epochs}", leave=False)
        for x, y, _ in pbar:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            emb = embed_tensor_batch(embedder, x)
            logits = head(emb)
            loss = masked_bce_loss(logits, y, pos_weight=pos_weight)
            loss.backward()
            nn.utils.clip_grad_norm_(head.parameters(), 5.0)
            opt.step()
            running += float(loss.item())
            n_batches += 1
        sched.step()

        metrics = evaluate(embedder, head, val_loader, device, pos_weight)
        mean_f1 = sum(m.get("f1", 0) for m in metrics.values()) / max(len(metrics), 1)
        row = {
            "epoch": epoch + 1,
            "train_loss": running / max(n_batches, 1),
            "mean_attr_f1": mean_f1,
            "per_attr": metrics,
        }
        history.append(row)
        print(f"epoch {epoch + 1}: loss={row['train_loss']:.4f}  mean_attr_f1={mean_f1:.4f}")

        ckpt = {
            "model": head.state_dict(),
            "embed_dim": embed_dim,
            "num_attrs": len(ATTR_NAMES),
            "dinobloom_variant": args.dinobloom_variant,
            "dinobloom_weights": str(weights_path),
            "attr_names": ATTR_NAMES,
            "imgsz": args.imgsz,
            "pos_weight": pos_weight.cpu(),
            "epoch": epoch + 1,
            "metrics": metrics,
        }
        torch.save(ckpt, save_dir / "last_attr_dinobloom.pt")
        if mean_f1 >= best_f1:
            best_f1 = mean_f1
            torch.save(ckpt, save_dir / "best_attr_dinobloom.pt")

    (save_dir / "history.json").write_text(json.dumps(history, indent=2))
    print(f"Best DinoBloom attribute weights: {save_dir / 'best_attr_dinobloom.pt'}  (mean_f1={best_f1:.4f})")


if __name__ == "__main__":
    main()
