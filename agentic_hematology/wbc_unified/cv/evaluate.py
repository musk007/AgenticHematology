#!/usr/bin/env python3
"""Evaluate detector + attributes (GT crops and/or legacy-aligned e2e det-match)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from data.cell_dataset import CellAttributeDataset  # noqa: E402
from models.attribute_net import build_attribute_model  # noqa: E402
from utils.e2e_attributes import eval_attributes_e2e  # noqa: E402
from utils.labels import ATTR_NAMES  # noqa: E402
from utils.metrics import attribute_metrics, print_legacy_attribute_table  # noqa: E402


@torch.no_grad()
def eval_attributes_gt(attr_weights: Path, manifest: Path, split: str, device, batch: int) -> dict:
    ckpt = torch.load(attr_weights, map_location=device, weights_only=False)
    model = build_attribute_model(
        num_attrs=len(ATTR_NAMES),
        backbone=ckpt.get("backbone", "efficientnet_b0"),
        pretrained=False,
    )
    model.load_state_dict(ckpt["model"])
    model.to(device)
    model.eval()
    ds = CellAttributeDataset(manifest, split, imgsz=int(ckpt.get("imgsz", 224)))
    loader = DataLoader(ds, batch_size=batch, shuffle=False, num_workers=4)
    ys, ps = [], []
    for x, y, _ in loader:
        x = x.to(device)
        logits = model(x)
        ys.append(y.numpy())
        ps.append(torch.sigmoid(logits).cpu().numpy())
    y_true = np.concatenate(ys, axis=0)
    y_pred = np.concatenate(ps, axis=0)
    return attribute_metrics(y_true, y_pred, ATTR_NAMES)


def print_attribute_metrics(title: str, metrics: dict) -> None:
    print(f"\n=== {title} ===")
    if not metrics:
        print("  (no matched cells)")
        return
    rows = [[name, m["accuracy"], m["precision"], m["recall"], m["f1"]] for name, m in metrics.items()]
    print_legacy_attribute_table(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "dataset.yaml")
    ap.add_argument("--det-weights", type=Path, required=True)
    ap.add_argument("--attr-weights", type=Path, required=True)
    ap.add_argument("--split", type=str, default="test")
    ap.add_argument("--device", type=str, default="0")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument(
        "--attr-eval",
        type=str,
        default="both",
        choices=("gt", "e2e", "both"),
        help="gt=GT crops; e2e=detect+IoU-match; both=run both",
    )
    ap.add_argument("--conf", type=float, default=0.001, help="Detection conf (legacy default 0.001)")
    ap.add_argument("--iou-nms", type=float, default=0.6)
    ap.add_argument("--max-det", type=int, default=300)
    ap.add_argument("--attr-batch", type=int, default=64)
    ap.add_argument("--pad", type=float, default=0.15)
    ap.add_argument("--legacy-attr", action="store_true", help="Use val.py cell filter + sklearn metrics for e2e")
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    data_yaml = args.config
    device = torch.device(f"cuda:{args.device}" if args.device.isdigit() else args.device)
    manifest = Path(cfg["attr_manifest"])

    print("=== Detection (Ultralytics val) ===")
    det = YOLO(str(args.det_weights))
    det.val(
        data=str(data_yaml),
        split=args.split,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou_nms,
        max_det=args.max_det,
        device=args.device,
        batch=8,
    )

    if args.attr_eval in ("gt", "both"):
        print_attribute_metrics(
            "Attributes (GT crops)",
            eval_attributes_gt(args.attr_weights, manifest, args.split, device, args.batch),
        )

    if args.attr_eval in ("e2e", "both"):
        e2e_metrics, e2e_stats, table_rows = eval_attributes_e2e(
            args.det_weights,
            args.attr_weights,
            manifest,
            args.split,
            device,
            conf=args.conf,
            iou_nms=args.iou_nms,
            max_det=args.max_det,
            imgsz_det=args.imgsz,
            attr_batch=args.attr_batch,
            pad=args.pad,
            det_device=args.device,
            legacy=args.legacy_attr,
        )
        if args.legacy_attr and table_rows:
            print("\n=== Attributes (e2e, legacy val.py aligned) ===")
            print_legacy_attribute_table(table_rows)
        else:
            print_attribute_metrics("Attributes (e2e)", e2e_metrics)
        print(
            f"  matched {e2e_stats['n_matched']}/{e2e_stats['n_gt_cells']} GT cells "
            f"(skipped {e2e_stats['n_skipped_no_det']} with no detection); "
            f"mean match IoU={e2e_stats['mean_match_iou']:.3f}"
        )


if __name__ == "__main__":
    main()
