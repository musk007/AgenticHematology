#!/usr/bin/env python3
"""Train attribute classifier on GT cell crops (EfficientNet-B0)."""
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
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader
from torch.utils.data.distributed import DistributedSampler
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from data.cell_dataset import CellAttributeDataset, compute_pos_weights  # noqa: E402
from models.attribute_net import build_attribute_model, masked_bce_loss  # noqa: E402
from utils.labels import ATTR_NAMES  # noqa: E402
from utils.metrics import attribute_metrics  # noqa: E402


def init_distributed() -> tuple[int, int, int, bool]:
    """Return (rank, local_rank, world_size, is_distributed)."""
    if "RANK" not in os.environ:
        return 0, 0, 1, False
    import torch.distributed as dist

    dist.init_process_group(backend="nccl")
    rank = dist.get_rank()
    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    world_size = dist.get_world_size()
    torch.cuda.set_device(local_rank)
    return rank, local_rank, world_size, True


def cleanup_distributed(is_distributed: bool) -> None:
    if is_distributed:
        import torch.distributed as dist

        dist.destroy_process_group()


@torch.no_grad()
def evaluate(model, loader, device, pos_weight):
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "dataset.yaml")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=64, help="Global batch size (split across GPUs under DDP)")
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--device", type=str, default="0", help="Used only for single-GPU; DDP uses LOCAL_RANK")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--local-rank", type=int, default=-1, help="Set by torch.distributed.run")
    ap.add_argument("--backbone", type=str, default="efficientnet_b0", choices=["efficientnet_b0", "resnet18"])
    ap.add_argument("--project", type=Path, default=ROOT / "runs" / "attribute")
    ap.add_argument("--name", type=str, default="train")
    args = ap.parse_args()

    rank, local_rank, world_size, is_distributed = init_distributed()
    is_main = rank == 0

    cfg = yaml.safe_load(args.config.read_text())
    manifest = Path(cfg["attr_manifest"])
    if not manifest.is_file():
        raise SystemExit(f"Missing manifest {manifest}. Run: python data/prepare_dataset.py")

    save_dir = args.project / args.name
    if is_main:
        save_dir.mkdir(parents=True, exist_ok=True)

    if is_distributed:
        device = torch.device(f"cuda:{local_rank}")
    else:
        device = torch.device(f"cuda:{args.device}" if args.device.isdigit() else args.device)

    if world_size > 1 and args.batch % world_size != 0:
        raise SystemExit(f"ATTR batch={args.batch} must be divisible by world_size={world_size}")
    batch_per_gpu = args.batch // world_size

    max_total_workers = int(os.environ.get("MAX_DATALOADER_WORKERS", "32"))
    if args.workers * world_size > max_total_workers:
        args.workers = max(2, max_total_workers // world_size)
        if is_main:
            print(f"Capped dataloader workers to {args.workers}/GPU ({args.workers * world_size} total)")

    train_ds = CellAttributeDataset(manifest, "train", imgsz=args.imgsz)
    val_ds = CellAttributeDataset(manifest, "test", imgsz=args.imgsz)
    if is_main:
        print(
            f"Attribute train cells: {len(train_ds)}  val: {len(val_ds)}  "
            f"world_size={world_size}  batch={args.batch} ({batch_per_gpu}/GPU)"
        )

    train_sampler = DistributedSampler(train_ds, shuffle=True) if is_distributed else None
    train_loader = DataLoader(
        train_ds,
        batch_size=batch_per_gpu,
        shuffle=train_sampler is None,
        sampler=train_sampler,
        num_workers=args.workers,
        pin_memory=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_per_gpu, shuffle=False, num_workers=args.workers, pin_memory=True
    )

    pos_weight = compute_pos_weights(manifest, "train").to(device)
    model = build_attribute_model(num_attrs=len(ATTR_NAMES), backbone=args.backbone, pretrained=True).to(device)
    if is_distributed:
        model = DDP(model, device_ids=[local_rank], output_device=local_rank)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)

    best_f1 = -1.0
    history = []

    for epoch in range(args.epochs):
        if train_sampler is not None:
            train_sampler.set_epoch(epoch)
        model.train()
        running = 0.0
        n_batches = 0
        pbar = tqdm(train_loader, desc=f"epoch {epoch+1}/{args.epochs}", leave=False, disable=not is_main)
        for x, y, _ in pbar:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            logits = model(x)
            loss = masked_bce_loss(logits, y, pos_weight=pos_weight)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            running += float(loss.item())
            n_batches += 1
        sched.step()

        eval_model = model.module if is_distributed else model
        metrics = evaluate(eval_model, val_loader, device, pos_weight) if is_main else {}
        mean_f1 = sum(m.get("f1", 0) for m in metrics.values()) / max(len(metrics), 1)
        row = {"epoch": epoch + 1, "train_loss": running / max(n_batches, 1), "mean_attr_f1": mean_f1, "per_attr": metrics}
        if is_main:
            history.append(row)
            print(f"epoch {epoch+1}: loss={row['train_loss']:.4f}  mean_attr_f1={mean_f1:.4f}")

        state = eval_model.state_dict()
        ckpt = {
            "model": state,
            "backbone": args.backbone,
            "attr_names": ATTR_NAMES,
            "imgsz": args.imgsz,
            "pos_weight": pos_weight.cpu(),
            "epoch": epoch + 1,
            "metrics": metrics,
        }
        if is_main:
            torch.save(ckpt, save_dir / "last_attr.pt")
            if mean_f1 >= best_f1:
                best_f1 = mean_f1
                torch.save(ckpt, save_dir / "best_attr.pt")

    if is_main:
        (save_dir / "history.json").write_text(json.dumps(history, indent=2))
        print(f"Best attribute weights: {save_dir / 'best_attr.pt'}  (mean_f1={best_f1:.4f})")
    cleanup_distributed(is_distributed)


if __name__ == "__main__":
    main()
