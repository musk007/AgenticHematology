#!/usr/bin/env python3
"""Joint inference: YOLO detection + attribute head on each box."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from data.cell_dataset import IMAGENET_MEAN, IMAGENET_STD  # noqa: E402
from models.attribute_net import build_attribute_model  # noqa: E402
from utils.labels import ATTR_NAMES, crop_with_padding  # noqa: E402


def preprocess_crop(crop: Image.Image, imgsz: int) -> torch.Tensor:
    crop = crop.resize((imgsz, imgsz), Image.BILINEAR)
    arr = np.asarray(crop, dtype=np.float32) / 255.0
    arr = (arr - np.array(IMAGENET_MEAN)) / np.array(IMAGENET_STD)
    return torch.from_numpy(arr).permute(2, 0, 1).float().unsqueeze(0)


@torch.no_grad()
def predict_attributes(model, crops: list, device, imgsz: int, batch: int = 32) -> np.ndarray:
    model.eval()
    outs = []
    for i in range(0, len(crops), batch):
        batch_crops = crops[i : i + batch]
        xs = torch.cat([preprocess_crop(c, imgsz) for c in batch_crops], dim=0).to(device)
        logits = model(xs)
        outs.append(torch.sigmoid(logits).cpu().numpy())
    return np.concatenate(outs, axis=0) if outs else np.zeros((0, len(ATTR_NAMES)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "dataset.yaml")
    ap.add_argument("--det-weights", type=Path, required=True)
    ap.add_argument("--attr-weights", type=Path, required=True)
    ap.add_argument("--split", type=str, default="test", choices=["train", "test"])
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--iou", type=float, default=0.6)
    ap.add_argument("--imgsz-det", type=int, default=640)
    ap.add_argument("--device", type=str, default="0")
    ap.add_argument("--attr-batch", type=int, default=64)
    ap.add_argument("--pad", type=float, default=0.15)
    ap.add_argument("--save-json", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "runs" / "predict")
    ap.add_argument("--name", type=str, default="infer")
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    det_root = Path(cfg["path"])
    print("****"*20)
    print(det_root)
    img_dir = det_root / "images" / args.split
    print(img_dir)
    print("****"*20)
    images = sorted(
        p for p in img_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    )
    if not images:
        raise SystemExit(f"No images in {img_dir}")

    device = torch.device(f"cuda:{args.device}" if args.device.isdigit() else args.device)
    det = YOLO(str(args.det_weights))
    ckpt = torch.load(args.attr_weights, map_location=device)
    attr_model = build_attribute_model(
        num_attrs=len(ATTR_NAMES),
        backbone=ckpt.get("backbone", "efficientnet_b0"),
        pretrained=False,
    )
    attr_model.load_state_dict(ckpt["model"])
    attr_model.to(device)
    attr_imgsz = int(ckpt.get("imgsz", 224))

    out_dir = args.out / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    all_results = []

    class_names = cfg.get("names", [])

    for img_path in images:
        res = det.predict(
            source=str(img_path),
            conf=args.conf,
            iou=args.iou,
            imgsz=args.imgsz_det,
            device=args.device,
            verbose=False,
        )[0]
        image = Image.open(img_path).convert("RGB")
        w, h = image.size
        boxes = []
        crops = []
        if res.boxes is not None and len(res.boxes):
            xyxy = res.boxes.xyxy.cpu().numpy()
            confs = res.boxes.conf.cpu().numpy()
            clss = res.boxes.cls.cpu().numpy().astype(int)
            for (x1, y1, x2, y2), cf, ci in zip(xyxy, confs, clss):
                bw, bh = x2 - x1, y2 - y1
                cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
                xywhn = np.array([cx, cy, bw / w, bh / h], dtype=np.float32)
                px1, py1, px2, py2 = crop_with_padding(w, h, xywhn, pad=args.pad)
                crops.append(image.crop((px1, py1, px2, py2)))
                boxes.append(
                    {
                        "xyxy": [float(x1), float(y1), float(x2), float(y2)],
                        "conf": float(cf),
                        "class_id": int(ci),
                        "class_name": class_names[ci] if ci < len(class_names) else str(ci),
                    }
                )

        attrs = predict_attributes(attr_model, crops, device, attr_imgsz, batch=args.attr_batch)
        cells = []
        for i, b in enumerate(boxes):
            attr_dict = {ATTR_NAMES[j]: float(attrs[i, j]) for j in range(len(ATTR_NAMES))}
            attr_bin = {k: int(v >= 0.5) for k, v in attr_dict.items()}
            cells.append({**b, "attributes": attr_dict, "attributes_bin": attr_bin})

        all_results.append({"image": str(img_path), "cells": cells})

    if args.save_json:
        out_json = out_dir / f"{args.split}_predictions.json"
        out_json.write_text(json.dumps(all_results, indent=2))
        print(f"Saved {out_json} ({len(all_results)} images)")


if __name__ == "__main__":
    main()
