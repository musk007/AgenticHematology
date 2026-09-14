"""LLD YOLO label parsing (12-column blood smear format)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import numpy as np

# 6 morphology attributes (cols 5..10 in 12-col file; col 11 if present is ignored)
ATTR_NAMES = [
    "Nuclear_Chromatin",
    "Nuclear_Shape",
    "Nucleus",
    "Cytoplasm",
    "Cytoplasmic_Basophilia",
    "Cytoplasmic_Vacuoles",
]
NUM_ATTRS = len(ATTR_NAMES)
IGNORE_ATTR = 2


def parse_label_file(path: Path) -> np.ndarray:
    """Return float array shape (N, 12) with cls, xywh, 6 attrs (pad/truncate)."""
    if not path.is_file():
        return np.zeros((0, 12), dtype=np.float32)
    rows: List[List[float]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        try:
            row = [float(x) for x in parts[:12]]
        except ValueError:
            continue
        while len(row) < 12:
            row.append(0.0)
        rows.append(row[:12])
    if not rows:
        return np.zeros((0, 12), dtype=np.float32)
    return np.asarray(rows, dtype=np.float32)


def det_rows(lb: np.ndarray) -> np.ndarray:
    """YOLO detection-only labels (N, 5): cls + xywh."""
    if lb.size == 0:
        return np.zeros((0, 5), dtype=np.float32)
    return lb[:, :5].copy()


def attr_rows(lb: np.ndarray) -> np.ndarray:
    """Attribute targets (N, 6), values in {0,1,2}."""
    if lb.size == 0:
        return np.zeros((0, NUM_ATTRS), dtype=np.float32)
    return lb[:, 5 : 5 + NUM_ATTRS].copy()


def write_det_label(path: Path, lb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for r in det_rows(lb):
        lines.append(" ".join(f"{int(r[0]) if i == 0 else v:.6g}" for i, v in enumerate(r)))
    path.write_text("\n".join(lines) + ("\n" if lines else ""))


def xywhn_to_xyxy(xywh: np.ndarray, w: int, h: int) -> np.ndarray:
    """Normalized xywh -> pixel xyxy."""
    x, y, bw, bh = xywh
    x1 = (x - bw / 2) * w
    y1 = (y - bh / 2) * h
    x2 = (x + bw / 2) * w
    y2 = (y + bh / 2) * h
    return np.array([x1, y1, x2, y2], dtype=np.float32)


def crop_with_padding(
    img_w: int, img_h: int, xywhn: np.ndarray, pad: float = 0.15
) -> Tuple[int, int, int, int]:
    """Pixel xyxy with fractional padding."""
    xyxy = xywhn_to_xyxy(xywhn, img_w, img_h)
    bw, bh = xyxy[2] - xyxy[0], xyxy[3] - xyxy[1]
    px, py = pad * bw, pad * bh
    x1 = max(0, int(xyxy[0] - px))
    y1 = max(0, int(xyxy[1] - py))
    x2 = min(img_w, int(xyxy[2] + px))
    y2 = min(img_h, int(xyxy[3] + py))
    if x2 <= x1:
        x2 = min(img_w, x1 + 1)
    if y2 <= y1:
        y2 = min(img_h, y1 + 1)
    return x1, y1, x2, y2
