#!/usr/bin/env python3
"""Build YOLO detection dataset + attribute cell manifest from LLD Organized."""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.labels import ATTR_NAMES, IGNORE_ATTR, parse_label_file, write_det_label  # noqa: E402

CLASS_NAMES = [
    "None",
    "Myeloblast",
    "Lymphoblast",
    "Neutrophil",
    "Atypical lymphocyte",
    "Promonocyte",
    "Monoblast",
    "Lymphocyte",
    "Myelocyte",
    "Abnormal promyelocyte",
    "Monocyte",
    "Metamyelocyte",
    "Eosinophil",
    "Basophil",
]


def resolve_image_path(src_img: Path, stem: str) -> Path:
    """Return expected image path even if not mounted on this node."""
    for ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
        p = src_img / f"{stem}{ext}"
        if p.is_file():
            return p
    return src_img / f"{stem}.png"


def remove_mac_resource_forks(img_dir: Path) -> int:
    """Remove AppleDouble resource-fork files (._*) that break YOLO label parsing."""
    if not img_dir.is_dir():
        return 0
    removed = 0
    for p in img_dir.glob("._*"):
        try:
            p.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def install_image(src: Path, dst: Path, mode: str = "auto") -> str:
    """
    Place image under det_dataset/images.
    Prefer hardlink (DDP-safe, no duplicate bytes); fall back to copy; symlink last.
    """
    src = src.resolve()
    if dst.exists() or dst.is_symlink():
        dst.unlink()

    if mode in ("auto", "hardlink"):
        try:
            os.link(src, dst)
            return "hardlink"
        except OSError:
            if mode == "hardlink":
                raise

    if mode in ("auto", "copy"):
        shutil.copy2(src, dst)
        return "copy"

    dst.symlink_to(src)
    return "symlink"


def ensure_split_image_dir(dst_img: Path) -> None:
    """Remove legacy whole-directory symlinks (they make YOLO read NFS labels/)."""
    dst_img.parent.mkdir(parents=True, exist_ok=True)
    if dst_img.is_symlink() or dst_img.is_file():
        dst_img.unlink()
    if not dst_img.is_dir():
        dst_img.mkdir(parents=True, exist_ok=True)


def link_split_images(data_root: Path, split: str, out_root: Path, image_mode: str = "auto") -> int:
    """
    Create per-file symlinks under generated/images/{split}.
    This is important: YOLO derives label paths from image paths.
    If we symlink the whole source images dir, labels are resolved to source labels/.
    """
    src_img = data_root / "images" / split
    src_attr = data_root / "attributes" / split
    dst_img = out_root / "images" / split
    ensure_split_image_dir(dst_img)

    # Clear old links/files to avoid stale mismatches across reruns.
    for p in dst_img.glob("*"):
        try:
            if p.is_symlink() or p.is_file():
                p.unlink()
        except OSError:
            pass

    if not src_img.is_dir() or not src_attr.is_dir():
        print(f"WARNING: missing split dirs for {split}: {src_img} / {src_attr}")
        return 0

    removed = remove_mac_resource_forks(src_img)
    if removed:
        print(f"  removed {removed} macOS ._* files from {src_img}")

    linked = 0
    modes: dict[str, int] = {}
    for lb_path in sorted(src_attr.glob("*.txt")):
        stem = lb_path.stem
        img_path = resolve_image_path(src_img, stem)
        if not img_path.exists():
            continue
        target = dst_img / img_path.name
        how = install_image(img_path, target, mode=image_mode)
        modes[how] = modes.get(how, 0) + 1
        linked += 1
    if modes:
        print(f"  images/{split}: {linked} files ({', '.join(f'{k}={v}' for k, v in sorted(modes.items()))})")
    return linked


def process_split(data_root: Path, split: str, out_root: Path) -> int:
    src_attr = data_root / "attributes" / split
    src_img = data_root / "images" / split
    out_lbl = out_root / "labels" / split
    n_cells = 0
    rows_csv = []

    if not src_attr.is_dir():
        print(f"WARNING: no attributes/{split} at {src_attr}")
        return 0

    for lb_path in sorted(src_attr.glob("*.txt")):
        stem = lb_path.stem
        img_path = resolve_image_path(src_img, stem)
        lb = parse_label_file(lb_path)
        write_det_label(out_lbl / f"{stem}.txt", lb)

        for i in range(lb.shape[0]):
            attrs = lb[i, 5 : 5 + len(ATTR_NAMES)]
            if (attrs == IGNORE_ATTR).all():
                continue
            rows_csv.append(
                {
                    "split": split,
                    "image": str(img_path),
                    "label_file": str(lb_path),
                    "cell_idx": i,
                    "class_id": int(lb[i, 0]),
                    "x": float(lb[i, 1]),
                    "y": float(lb[i, 2]),
                    "w": float(lb[i, 3]),
                    "h": float(lb[i, 4]),
                    **{name: int(attrs[j]) for j, name in enumerate(ATTR_NAMES)},
                }
            )
            n_cells += 1

    return n_cells


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("DATA_ROOT", "/home/rao.anwer/datasets/LeukemiaDataset_Organized")),
    )
    p.add_argument("--out", type=Path, default=ROOT / "generated")
    p.add_argument(
        "--image-mode",
        type=str,
        default=os.environ.get("DET_IMAGE_MODE", "auto"),
        choices=("auto", "hardlink", "copy", "symlink"),
        help="How to populate det_dataset/images (auto=hardlink then copy; avoid symlink for DDP)",
    )
    args = p.parse_args()

    det_root = args.out / "det_dataset"
    det_root.mkdir(parents=True, exist_ok=True)

    for split in ("train", "test"):
        remove_mac_resource_forks(args.data_root / "images" / split)

    linked_train = link_split_images(args.data_root, "train", det_root, args.image_mode)
    linked_test = link_split_images(args.data_root, "test", det_root, args.image_mode)

    n_train = process_split(args.data_root, "train", det_root)
    n_test = process_split(args.data_root, "test", det_root)

    manifest = args.out / "attr_manifest.csv"
    with manifest.open("w", newline="") as f:
        fields = ["split", "image", "label_file", "cell_idx", "class_id", "x", "y", "w", "h"] + ATTR_NAMES
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for split in ("train", "test"):
            src_attr = args.data_root / "attributes" / split
            src_img = args.data_root / "images" / split
            if not src_attr.is_dir():
                continue
            for lb_path in sorted(src_attr.glob("*.txt")):
                stem = lb_path.stem
                img_path = resolve_image_path(src_img, stem)
                lb = parse_label_file(lb_path)
                if lb.size == 0:
                    continue
                for i in range(lb.shape[0]):
                    attrs = lb[i, 5 : 5 + len(ATTR_NAMES)]
                    if (attrs == IGNORE_ATTR).all():
                        continue
                    w.writerow(
                        {
                            "split": split,
                            "image": str(img_path),
                            "label_file": str(lb_path),
                            "cell_idx": i,
                            "class_id": int(lb[i, 0]),
                            "x": float(lb[i, 1]),
                            "y": float(lb[i, 2]),
                            "w": float(lb[i, 3]),
                            "h": float(lb[i, 4]),
                            **{name: int(attrs[j]) for j, name in enumerate(ATTR_NAMES)},
                        }
                    )

    yaml_path = ROOT / "configs" / "dataset.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = {
        "path": str(det_root.resolve()),
        "train": "images/train",
        "val": "images/test",
        "test": "images/test",
        "nc": len(CLASS_NAMES),
        "names": CLASS_NAMES,
        "data_root": str(args.data_root.resolve()),
        "attr_manifest": str(manifest.resolve()),
    }
    yaml_path.write_text(yaml.safe_dump(cfg, sort_keys=False))

    # Count images
    n_img_train = len(list((det_root / "images" / "train").glob("*"))) if (det_root / "images" / "train").exists() else 0
    n_img_test = len(list((det_root / "images" / "test").glob("*"))) if (det_root / "images" / "test").exists() else 0
    print(f"Prepared detection dataset: {det_root}")
    print(f"  train cells (manifest): {n_train}  test cells: {n_test}")
    print(f"  linked images: train={linked_train}, test={linked_test}")
    print(f"  image entries: train={n_img_train}, test={n_img_test}")
    print(f"  config: {yaml_path}")
    print(f"  manifest: {manifest}")
    if n_img_train == 0:
        raise SystemExit(
            "No images under det_dataset/images/train. Check DATA_ROOT and re-run prepare_dataset."
        )
    for split in ("train", "test"):
        img_dir = det_root / "images" / split
        if img_dir.is_symlink():
            raise SystemExit(
                f"{img_dir} is still a directory symlink. Remove it and re-run prepare_dataset."
            )
        sample = next(img_dir.glob("*.png"), None)
        if sample is None:
            continue
        lbl = det_root / "labels" / split / f"{sample.stem}.txt"
        if not lbl.is_file():
            raise SystemExit(f"Missing detection label for sample image: {lbl}")
        ncol = len(lbl.read_text().strip().splitlines()[0].split()) if lbl.read_text().strip() else 0
        if ncol != 5:
            raise SystemExit(f"Expected 5-column YOLO labels, got {ncol} in {lbl}")
        if sample.is_symlink():
            print(f"WARNING: {sample} is still a symlink; use --image-mode copy or hardlink for stable DDP training")


if __name__ == "__main__":
    main()
