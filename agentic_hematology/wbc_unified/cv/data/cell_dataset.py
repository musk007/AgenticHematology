"""PyTorch dataset: cell crops + 6 binary attributes."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

from utils.labels import ATTR_NAMES, IGNORE_ATTR, crop_with_padding

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def load_manifest(path: Path, split: str) -> List[dict]:
    rows = []
    with path.open() as f:
        for row in csv.DictReader(f):
            if row["split"] == split:
                rows.append(row)
    return rows


class CellAttributeDataset(Dataset):
    def __init__(
        self,
        manifest_csv: Path,
        split: str,
        imgsz: int = 224,
        pad: float = 0.15,
        augment: Optional[Callable] = None,
    ):
        self.rows = load_manifest(manifest_csv, split)
        self.imgsz = imgsz
        self.pad = pad
        self.augment = augment
        self.attr_names = ATTR_NAMES

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, dict]:
        r = self.rows[idx]
        img_path = Path(r["image"])
        image = Image.open(img_path).convert("RGB")
        w, h = image.size
        xywh = np.array([float(r["x"]), float(r["y"]), float(r["w"]), float(r["h"])], dtype=np.float32)
        x1, y1, x2, y2 = crop_with_padding(w, h, xywh, pad=self.pad)
        crop = image.crop((x1, y1, x2, y2)).resize((self.imgsz, self.imgsz), Image.BILINEAR)

        if self.augment is not None:
            crop = self.augment(crop)

        arr = np.asarray(crop, dtype=np.float32) / 255.0
        arr = (arr - np.array(IMAGENET_MEAN)) / np.array(IMAGENET_STD)
        tensor = torch.from_numpy(arr).permute(2, 0, 1).float()

        targets = []
        for name in ATTR_NAMES:
            v = int(r[name])
            targets.append(attr_target_value(v))
        meta = {"image": str(img_path), "cell_idx": int(r["cell_idx"]), "class_id": int(r["class_id"])}
        return tensor, torch.tensor(targets, dtype=torch.float32), meta


def attr_target_value(v: int) -> float:
    """Map raw label to BCE target; -1 = masked (ignore)."""
    if v == IGNORE_ATTR or v > 1:
        return -1.0
    return float(v)


def compute_pos_weights(manifest_csv: Path, split: str) -> torch.Tensor:
    rows = load_manifest(manifest_csv, split)
    counts = np.zeros((len(ATTR_NAMES), 2), dtype=np.float64)
    for r in rows:
        for j, name in enumerate(ATTR_NAMES):
            v = int(r[name])
            if attr_target_value(v) < 0:
                continue
            counts[j, v] += 1
    weights = []
    for j in range(len(ATTR_NAMES)):
        neg, pos = counts[j, 0], counts[j, 1]
        if pos < 1:
            weights.append(1.0)
        else:
            weights.append(min(10.0, max(1.0, neg / pos)))
    return torch.tensor(weights, dtype=torch.float32)
