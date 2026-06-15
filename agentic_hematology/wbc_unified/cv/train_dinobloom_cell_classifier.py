#!/usr/bin/env python3
"""Train DinoBloom cell-type classifier on LLD single-cell crops (for Helmholtz precropped path)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import classification_report
from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT.parent))
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(ROOT))

from agentic_hematology.detection_agent import LLD_CLASSES  # noqa: E402
from agentic_hematology.detection_agent_dinobloom import (  # noqa: E402
    DINOBLOOM_INPUT_SIZE,
    DinoBloomEmbedder,
    resolve_dinobloom_weights,
)
from data.cell_dataset import load_manifest  # noqa: E402
from utils.labels import crop_with_padding  # noqa: E402

EXCLUDED_CLASS_IDS = {0}  # None


def _embed_rows(
    embedder: DinoBloomEmbedder,
    rows: list[dict],
    imgsz: int,
    pad: float,
    batch: int,
) -> tuple[np.ndarray, np.ndarray]:
    labels: list[int] = []
    batch_crops: list[Image.Image] = []
    batch_labels: list[int] = []
    chunks: list[np.ndarray] = []
    label_chunks: list[np.ndarray] = []

    def flush() -> None:
        if not batch_crops:
            return
        embs = embedder.embed_pil_batch(batch_crops)
        chunks.append(embs)
        label_chunks.append(np.asarray(batch_labels, dtype=np.int64))
        batch_crops.clear()
        batch_labels.clear()

    for row in tqdm(rows, desc="Embedding LLD crops"):
        class_id = int(row["class_id"])
        if class_id in EXCLUDED_CLASS_IDS:
            continue
        image = Image.open(row["image"]).convert("RGB")
        w, h = image.size
        xywh = np.array(
            [float(row["x"]), float(row["y"]), float(row["w"]), float(row["h"])],
            dtype=np.float32,
        )
        x1, y1, x2, y2 = crop_with_padding(w, h, xywh, pad=pad)
        crop = image.crop((x1, y1, x2, y2)).resize((imgsz, imgsz), Image.BILINEAR)
        batch_crops.append(crop)
        batch_labels.append(class_id)
        if len(batch_crops) >= batch:
            flush()
    flush()
    if not chunks:
        raise SystemExit("No labeled crops found in manifest.")
    return np.concatenate(chunks, axis=0), np.concatenate(label_chunks, axis=0)


def _class_names_from_ids(class_ids: np.ndarray) -> list[str]:
    used = sorted(set(int(i) for i in class_ids))
    return [LLD_CLASSES[i] for i in used if i < len(LLD_CLASSES)]


def main() -> None:
    ap = argparse.ArgumentParser(description="Train DinoBloom linear cell-type head on LLD manifest.")
    ap.add_argument("--manifest", type=Path, default=ROOT / "generated" / "attr_manifest.csv")
    ap.add_argument("--train-split", default="train")
    ap.add_argument("--val-split", default="test")
    ap.add_argument("--dinobloom-weights", default="auto")
    ap.add_argument("--dinobloom-variant", choices=["s", "b", "l", "g"], default="l")
    ap.add_argument("--dinobloom-hub-dir", default=None)
    ap.add_argument("--project", type=Path, default=REPO_ROOT / "runs" / "cell_dinobloom")
    ap.add_argument("--name", default="train")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--pad", type=float, default=0.15)
    ap.add_argument("--device", default="0")
    ap.add_argument("--workers", type=int, default=0)
    args = ap.parse_args()

    train_rows = load_manifest(args.manifest, args.train_split)
    val_rows = load_manifest(args.manifest, args.val_split)
    if not train_rows:
        sys.exit(f"No rows for split={args.train_split!r} in {args.manifest}")

    weights_path = resolve_dinobloom_weights(args.dinobloom_weights, args.dinobloom_variant)
    embedder = DinoBloomEmbedder(
        weights_path=weights_path,
        variant=args.dinobloom_variant,
        device=args.device,
        hub_dir=args.dinobloom_hub_dir,
    )
    imgsz = DINOBLOOM_INPUT_SIZE

    x_train, y_train = _embed_rows(embedder, train_rows, imgsz, args.pad, args.batch)
    x_val, y_val = _embed_rows(embedder, val_rows, imgsz, args.pad, args.batch)

    class_ids = sorted(set(int(i) for i in np.concatenate([y_train, y_val])))
    id_to_idx = {cid: idx for idx, cid in enumerate(class_ids)}
    classes = [LLD_CLASSES[cid] for cid in class_ids]
    y_train_idx = np.array([id_to_idx[int(y)] for y in y_train], dtype=np.int64)
    y_val_idx = np.array([id_to_idx[int(y)] for y in y_val], dtype=np.int64)

    device = embedder.device
    head = nn.Linear(x_train.shape[1], len(class_ids)).to(device)
    opt = torch.optim.AdamW(head.parameters(), lr=args.lr, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()

    train_ds = TensorDataset(
        torch.from_numpy(x_train).float(),
        torch.from_numpy(y_train_idx).long(),
    )
    loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=args.workers)

    best_acc = -1.0
    save_dir = args.project / args.name
    save_dir.mkdir(parents=True, exist_ok=True)
    out_path = save_dir / "best_cell_dinobloom.pt"

    for epoch in range(1, args.epochs + 1):
        head.train()
        total_loss = 0.0
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            opt.zero_grad(set_to_none=True)
            logits = head(xb)
            loss = crit(logits, yb)
            loss.backward()
            opt.step()
            total_loss += float(loss.item()) * len(xb)
        head.eval()
        with torch.no_grad():
            val_logits = head(torch.from_numpy(x_val).float().to(device))
            val_pred = val_logits.argmax(dim=-1).cpu().numpy()
        val_acc = float((val_pred == y_val_idx).mean())
        print(f"epoch {epoch:02d}  loss={total_loss/len(train_ds):.4f}  val_acc={val_acc:.3f}")
        if val_acc >= best_acc:
            best_acc = val_acc
            payload = {
                "classes": classes,
                "class_ids": class_ids,
                "weight": head.weight.detach().cpu().numpy(),
                "bias": head.bias.detach().cpu().numpy(),
                "dinobloom_variant": args.dinobloom_variant,
                "dinobloom_weights": str(weights_path),
                "manifest": str(args.manifest),
                "val_accuracy": val_acc,
            }
            torch.save(payload, out_path)

    report = classification_report(
        [classes[id_to_idx[int(y)]] for y in y_val],
        [classes[i] for i in val_pred],
        zero_division=0,
    )
    meta = {
        "classes": classes,
        "class_ids": class_ids,
        "val_accuracy": best_acc,
        "model_path": str(out_path),
        "dinobloom_variant": args.dinobloom_variant,
    }
    (save_dir / "best_cell_dinobloom_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Saved {out_path}  val_acc={best_acc:.3f}")
    print(report)


if __name__ == "__main__":
    main()
