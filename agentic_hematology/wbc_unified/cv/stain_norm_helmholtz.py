#!/usr/bin/env python3
"""Stain-normalize MLL Helmholtz images toward LLD appearance (Macenko, no staintools).

Usage:
    # Reference from LLD train field images:
    python wbc_unified/cv/stain_norm_helmholtz.py \\
        --reference_dir /nfs-stor/roba.majzoub/LeukemiaDataset_Organized/images/train \\
        --input_dir ~/helmholtz/data \\
        --output_dir ~/helmholtz/data_stainnorm

    # Or one LLD image / LLD cell crops from attr_manifest.csv:
    python wbc_unified/cv/stain_norm_helmholtz.py \\
        --reference_manifest wbc_unified/cv/generated/attr_manifest.csv \\
        --input_dir ~/helmholtz/data \\
        --output_dir ~/helmholtz/data_stainnorm

Then point embedding / attribute extraction at ``~/helmholtz/data_stainnorm`` and re-run
``embedding_sanity_check.py --helmholtz-root .../data_stainnorm/control``.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from skimage import io as skio

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from utils.labels import crop_with_padding  # noqa: E402

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def get_stain_matrix(img: np.ndarray, angular_percentile: int = 99) -> np.ndarray:
    """Estimate 2x3 H&E stain matrix from RGB image (Macenko)."""
    od = -np.log((img.astype(np.float64) + 1.0) / 256.0)
    od = od.reshape((-1, 3))

    mask = (od > 0.15).any(axis=1)
    od_fg = od[mask]
    if od_fg.shape[0] < 10:
        od_fg = od

    _, eigvecs = np.linalg.eigh(np.cov(od_fg.T))
    eigvecs = eigvecs[:, [2, 1]]

    if eigvecs[0, 0] < 0:
        eigvecs[:, 0] *= -1
    if eigvecs[0, 1] < 0:
        eigvecs[:, 1] *= -1

    proj = od_fg @ eigvecs
    phi = np.arctan2(proj[:, 1], proj[:, 0])
    min_phi = np.percentile(phi, 100 - angular_percentile)
    max_phi = np.percentile(phi, angular_percentile)

    v1 = eigvecs @ np.array([np.cos(min_phi), np.sin(min_phi)])
    v2 = eigvecs @ np.array([np.cos(max_phi), np.sin(max_phi)])

    if v1[0] > v2[0]:
        he = np.array([v1, v2])
    else:
        he = np.array([v2, v1])

    return he / (np.linalg.norm(he, axis=1, keepdims=True) + 1e-8)


def get_concentrations(img: np.ndarray, stain_matrix: np.ndarray) -> np.ndarray:
    od = -np.log((img.astype(np.float64) + 1.0) / 256.0).reshape((-1, 3))
    conc = od @ stain_matrix.T @ np.linalg.inv(stain_matrix @ stain_matrix.T + 1e-8 * np.eye(2))
    return np.maximum(conc, 0)


def normalize_to_reference(
    img: np.ndarray,
    src_stain_matrix: np.ndarray,
    ref_stain_matrix: np.ndarray,
    ref_max_conc: np.ndarray,
) -> np.ndarray:
    h, w = img.shape[:2]
    src_conc = get_concentrations(img, src_stain_matrix)
    src_max_conc = np.percentile(src_conc, 99, axis=0)
    src_max_conc = np.clip(src_max_conc, 1e-6, None)
    norm_conc = src_conc * (ref_max_conc / src_max_conc)
    od_recon = norm_conc @ ref_stain_matrix
    rgb = 255.0 * np.exp(-od_recon)
    return np.clip(rgb, 0, 255).reshape((h, w, 3)).astype(np.uint8)


def load_rgb(path: Path) -> np.ndarray:
    img = skio.imread(str(path))
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    if img.shape[-1] == 4:
        img = img[..., :3]
    return img


def compute_reference_stats(ref_images: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    matrices: list[np.ndarray] = []
    max_concs: list[np.ndarray] = []
    for img in ref_images:
        sm = get_stain_matrix(img)
        conc = get_concentrations(img, sm)
        matrices.append(sm)
        max_concs.append(np.percentile(conc, 99, axis=0))
    if not matrices:
        raise RuntimeError("No valid reference images to compute stain matrix.")
    return np.mean(np.stack(matrices, axis=0), axis=0), np.mean(np.stack(max_concs, axis=0), axis=0)


def _crop_manifest_row(row: dict, pad: float = 0.15) -> np.ndarray:
    image = Image.open(row["image"]).convert("RGB")
    w, h = image.size
    xywh = np.array([float(row["x"]), float(row["y"]), float(row["w"]), float(row["h"])], dtype=np.float32)
    x1, y1, x2, y2 = crop_with_padding(w, h, xywh, pad=pad)
    crop = image.crop((x1, y1, x2, y2)).resize((144, 144), Image.BILINEAR)
    return np.asarray(crop)


def sample_reference_images_from_manifest(
    manifest: Path,
    n_ref: int,
    seed: int,
    split: str = "train",
    pad: float = 0.15,
) -> list[np.ndarray]:
    rows: list[dict] = []
    with manifest.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("split") == split and Path(row["image"]).is_file():
                rows.append(row)
    if not rows:
        raise RuntimeError(f"No manifest rows for split={split!r} in {manifest}")
    picked = random.Random(seed).sample(rows, min(n_ref, len(rows)))
    return [_crop_manifest_row(row, pad=pad) for row in picked]


def collect_reference_images(args: argparse.Namespace) -> list[np.ndarray]:
    if args.reference_manifest:
        return sample_reference_images_from_manifest(
            Path(args.reference_manifest),
            args.n_ref,
            args.seed,
            split=args.reference_split,
            pad=args.pad,
        )
    if args.reference:
        return [load_rgb(Path(args.reference))]
    if args.reference_dir:
        all_imgs = [p for p in Path(args.reference_dir).rglob("*") if p.suffix.lower() in IMG_EXTS]
        if not all_imgs:
            raise RuntimeError(f"No images found under {args.reference_dir}")
        rng = np.random.default_rng(args.seed)
        idx = rng.choice(len(all_imgs), size=min(args.n_ref, len(all_imgs)), replace=False)
        return [load_rgb(all_imgs[i]) for i in idx]
    raise RuntimeError("Must provide --reference, --reference_dir, or --reference_manifest")


def main() -> None:
    ap = argparse.ArgumentParser(description="Macenko stain-normalize Helmholtz images toward LLD.")
    ap.add_argument("--reference", type=Path, default=None, help="Single representative LLD image.")
    ap.add_argument("--reference_dir", type=Path, default=None, help="Folder of LLD images (field or crop).")
    ap.add_argument(
        "--reference_manifest",
        type=Path,
        default=None,
        help="LLD attr_manifest.csv — samples single-cell crops as references (recommended).",
    )
    ap.add_argument("--reference_split", default="train", choices=["train", "test"])
    ap.add_argument("--pad", type=float, default=0.15, help="BBox padding when using --reference_manifest.")
    ap.add_argument("--n_ref", type=int, default=20, help="Reference samples from dir/manifest.")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--input_dir", type=Path, required=True, help="Helmholtz data root (e.g. ~/helmholtz/data).")
    ap.add_argument("--output_dir", type=Path, required=True, help="Output root (mirrors input structure).")
    ap.add_argument("--limit", type=int, default=None, help="Cap images processed (smoke test).")
    args = ap.parse_args()

    if not (args.reference or args.reference_dir or args.reference_manifest):
        sys.exit("Must provide --reference, --reference_dir, or --reference_manifest")

    ref_images = collect_reference_images(args)
    print(f"Computing reference stain stats from {len(ref_images)} image(s)...")
    ref_stain_matrix, ref_max_conc = compute_reference_stats(ref_images)
    print("Reference stain matrix:\n", ref_stain_matrix)
    print("Reference max concentrations:", ref_max_conc)

    img_paths = [p for p in args.input_dir.rglob("*") if p.suffix.lower() in IMG_EXTS]
    if args.limit:
        img_paths = img_paths[: args.limit]
    print(f"Found {len(img_paths)} images under {args.input_dir}")

    n_ok, n_skip, n_fail = 0, 0, 0
    for i, p in enumerate(img_paths):
        rel = p.relative_to(args.input_dir)
        out_path = args.output_dir / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists():
            n_skip += 1
            continue

        try:
            img = load_rgb(p)
            src_stain_matrix = get_stain_matrix(img)
            norm_img = normalize_to_reference(img, src_stain_matrix, ref_stain_matrix, ref_max_conc)
            skio.imsave(str(out_path), norm_img, check_contrast=False)
            n_ok += 1
        except Exception as exc:
            print(f"  [fail] {p}: {exc}")
            n_fail += 1

        if (i + 1) % 200 == 0:
            print(f"  ...{i + 1}/{len(img_paths)} (ok={n_ok}, skip={n_skip}, fail={n_fail})")

    print(f"Done. ok={n_ok}, skipped(existing)={n_skip}, failed={n_fail}")
    print(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
