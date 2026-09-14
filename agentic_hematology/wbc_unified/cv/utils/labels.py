"""LLD YOLO label parsing (12-column blood smear format).

Layout per line: ``cls x y w h  Cell_Size  <6 binary attrs>``  (12 fields).

Attribute encoding:
  - ``Cell_Size``  : 0=small, 1=medium, 2=large. Has NO ignore code in the raw
                     file; ``CELL_SIZE_IGNORE`` (-1) is written by this module
                     only when the value is missing or out of range.
  - binary attrs   : 0 / 1, with ``IGNORE_ATTR`` (2) meaning "unannotated".
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import numpy as np

# 7 morphology attributes, label columns 5..11 (all of them are used).
ATTR_NAMES = [
    "Cell_Size",                # col 5  — categorical: 0=small, 1=medium, 2=large
    "Nuclear_Chromatin",        # col 6  — binary
    "Nuclear_Shape",            # col 7  — binary
    "Nucleolus",                # col 8  — binary
    "Cytoplasm",                # col 9  — binary
    "Cytoplasmic_Basophilia",   # col 10 — binary
    "Cytoplasmic_Vacuoles",     # col 11 — binary
]
NUM_ATTRS = len(ATTR_NAMES)
N_LABEL_COLS = 5 + NUM_ATTRS  # 12

CATEGORICAL_ATTRS = {"Cell_Size": 3}
BINARY_ATTRS = [n for n in ATTR_NAMES if n not in CATEGORICAL_ATTRS]

IGNORE_ATTR = 2          # "unannotated" — valid for BINARY_ATTRS only
CELL_SIZE_IDX = 0
CELL_SIZE_N_CLASSES = CATEGORICAL_ATTRS["Cell_Size"]
CELL_SIZE_IGNORE = -1     # written only for missing/out-of-range Cell_Size

# Column index of each attribute inside the 12-column row.
ATTR_COL = {name: 5 + i for i, name in enumerate(ATTR_NAMES)}
# Index of each binary attribute inside the 7-wide attribute block.
BINARY_ATTR_IDX = [ATTR_NAMES.index(n) for n in BINARY_ATTRS]

def parse_label_file(path: Path, stats: dict | None = None) -> np.ndarray:
    """Return float array (N, 12): cls, xywh, 7 attrs.
    Rows shorter than 12 fields are padded with the correct *ignore* codes
    rather than with zeros, so a truncated line can never be mistaken for a
    real negative annotation. Pass ``stats`` (a dict) to collect counts of
    malformed / short rows.
    """
    if stats is not None:
        stats.setdefault("files", 0)
        stats.setdefault("rows", 0)
        stats.setdefault("short_rows", 0)
        stats.setdefault("unparsable_rows", 0)
        stats.setdefault("bad_attr_values", 0)
        stats["files"] += 1

    if not path.is_file():
        return np.zeros((0, N_LABEL_COLS), dtype=np.float32)

    rows: List[List[float]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        if len(parts) < 5:
            if stats is not None:
                stats["unparsable_rows"] += 1
            continue
        try:
            row = [float(x) for x in parts[:N_LABEL_COLS]]
        except ValueError:
            if stats is not None:
                stats["unparsable_rows"] += 1
            continue

        if len(row) < N_LABEL_COLS:
            if stats is not None:
                stats["short_rows"] += 1
            # Pad geometry with 0.0 (should never trigger: len >= 5 above),
            # attributes with their ignore code.
            while len(row) < 5:
                row.append(0.0)
            while len(row) < N_LABEL_COLS:
                col = len(row)
                row.append(
                    float(CELL_SIZE_IGNORE)
                    if col == ATTR_COL["Cell_Size"]
                    else float(IGNORE_ATTR)
                )

        rows.append(row[:N_LABEL_COLS])
        if stats is not None:
            stats["rows"] += 1

    if not rows:
        return np.zeros((0, N_LABEL_COLS), dtype=np.float32)

    lb = np.asarray(rows, dtype=np.float32)
    lb = sanitize_attrs(lb, stats=stats)
    return lb

def sanitize_attrs(lb: np.ndarray, stats: dict | None = None) -> np.ndarray:
    """Clamp out-of-range attribute codes to their ignore value."""
    if lb.size == 0:
        return lb
    bad = 0

    size_col = ATTR_COL["Cell_Size"]
    size = lb[:, size_col]
    invalid_size = ~np.isin(size, np.arange(CELL_SIZE_N_CLASSES))
    bad += int(invalid_size.sum())
    lb[invalid_size, size_col] = CELL_SIZE_IGNORE

    for name in BINARY_ATTRS:
        col = ATTR_COL[name]
        vals = lb[:, col]
        invalid = ~np.isin(vals, (0.0, 1.0, float(IGNORE_ATTR)))
        bad += int(invalid.sum())
        lb[invalid, col] = IGNORE_ATTR

    if stats is not None and bad:
        stats["bad_attr_values"] = stats.get("bad_attr_values", 0) + bad
    return lb


def det_rows(lb: np.ndarray) -> np.ndarray:
    """YOLO detection-only labels (N, 5): cls + xywh."""
    if lb.size == 0:
        return np.zeros((0, 5), dtype=np.float32)
    return lb[:, :5].copy()


def attr_rows(lb: np.ndarray) -> np.ndarray:
    """Attribute block (N, 7). Binary attrs use 2 = ignore; Cell_Size uses -1."""
    if lb.size == 0:
        return np.zeros((0, NUM_ATTRS), dtype=np.float32)
    return lb[:, 5 : 5 + NUM_ATTRS].copy()


def is_unannotated_row(attrs: np.ndarray) -> bool:
    """True when every binary attribute is ignore-coded (e.g. class-0 'None').

    Cell_Size is deliberately excluded: value 2 there means 'large', so an
    all-2 row would otherwise look like a legitimate large cell.
    """
    binary = np.asarray(attrs, dtype=np.float32)[BINARY_ATTR_IDX]
    return bool((binary == IGNORE_ATTR).all())


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
