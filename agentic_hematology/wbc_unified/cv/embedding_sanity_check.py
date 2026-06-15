#!/usr/bin/env python3
"""Quick sanity check: PCA / t-SNE of DinoBloom backbone embeddings (LLD vs Helmholtz).

Uses frozen DinoBloom-L embeddings (1024-d by default), not EfficientNet or attribute-head
outputs. Samples cell crops from LLD (attr_manifest.csv) and Helmholtz control pre-crops.

Example:
  python embedding_sanity_check.py --device 0 --max-per-domain 1000
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
from PIL import Image
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT.parent))
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(ROOT))

from agentic_hematology.detection_agent_dinobloom import (  # noqa: E402
    DINOBLOOM_INPUT_SIZE,
    DinoBloomEmbedder,
)
from dinobloom_infer import DEFAULT_DINOBLOOM_ATTR_WEIGHTS  # noqa: E402
from mll_helmholtz import iter_helmholtz_control_images, resolve_helmholtz_data_root  # noqa: E402
from utils.labels import crop_with_padding  # noqa: E402


def _load_manifest_rows(manifest: Path, split: str) -> list[dict]:
    rows: list[dict] = []
    with manifest.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("split") == split:
                rows.append(row)
    return rows


def _crop_from_manifest_row(row: dict, imgsz: int, pad: float) -> Image.Image:
    image = Image.open(row["image"]).convert("RGB")
    w, h = image.size
    xywh = np.array([float(row["x"]), float(row["y"]), float(row["w"]), float(row["h"])], dtype=np.float32)
    x1, y1, x2, y2 = crop_with_padding(w, h, xywh, pad=pad)
    return image.crop((x1, y1, x2, y2)).resize((imgsz, imgsz), Image.BILINEAR)


def extract_lld_embeddings(
    embedder: DinoBloomEmbedder,
    manifest: Path,
    split: str,
    max_rows: int,
    seed: int,
    batch: int,
    pad: float,
) -> np.ndarray:
    rows = _load_manifest_rows(manifest, split)
    if not rows:
        raise SystemExit(f"No LLD rows for split={split!r} in {manifest}")
    picked = random.Random(seed).sample(rows, min(max_rows, len(rows)))
    chunks: list[np.ndarray] = []
    batch_crops: list[Image.Image] = []
    for row in tqdm(picked, desc=f"LLD {split} embeddings"):
        batch_crops.append(_crop_from_manifest_row(row, DINOBLOOM_INPUT_SIZE, pad))
        if len(batch_crops) >= batch:
            chunks.append(embedder.embed_pil_batch(batch_crops))
            batch_crops.clear()
    if batch_crops:
        chunks.append(embedder.embed_pil_batch(batch_crops))
    return np.concatenate(chunks, axis=0)


def extract_helmholtz_embeddings(
    embedder: DinoBloomEmbedder,
    data_root: Path,
    max_rows: int,
    seed: int,
    batch: int,
) -> np.ndarray:
    rows = iter_helmholtz_control_images(data_root)
    if not rows:
        raise SystemExit(f"No Helmholtz control images under {data_root}")
    picked = random.Random(seed).sample(rows, min(max_rows, len(rows)))
    chunks: list[np.ndarray] = []
    batch_crops: list[Image.Image] = []
    for _, img_path in tqdm(picked, desc="Helmholtz embeddings"):
        batch_crops.append(Image.open(img_path).convert("RGB"))
        if len(batch_crops) >= batch:
            chunks.append(embedder.embed_pil_batch(batch_crops))
            batch_crops.clear()
    if batch_crops:
        chunks.append(embedder.embed_pil_batch(batch_crops))
    return np.concatenate(chunks, axis=0)


def _domain_shift_ratio(xy: np.ndarray, labels: np.ndarray) -> tuple[float, bool]:
    lld_xy = xy[labels == "LLD"]
    hz_xy = xy[labels == "Helmholtz"]
    centroid_dist = float(np.linalg.norm(lld_xy.mean(axis=0) - hz_xy.mean(axis=0)))
    lld_spread = float(np.mean(np.linalg.norm(lld_xy - lld_xy.mean(axis=0), axis=1)))
    ratio = centroid_dist / max(lld_spread, 1e-6)
    return ratio, ratio > 1.5


def plot_embeddings(
    X: np.ndarray,
    labels: np.ndarray,
    out_plot: Path,
    seed: int,
    title_suffix: str,
) -> dict:
    pca = PCA(n_components=2, random_state=seed)
    xy_pca = pca.fit_transform(X)
    perplexity = min(30, max(5, len(X) // 10))
    xy_tsne = TSNE(
        n_components=2,
        random_state=seed,
        perplexity=perplexity,
        init="pca",
        learning_rate="auto",
    ).fit_transform(X)

    pca_ratio, pca_flag = _domain_shift_ratio(xy_pca, labels)
    tsne_ratio, tsne_flag = _domain_shift_ratio(xy_tsne, labels)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, coords, title, ratio, flagged in [
        (
            axes[0],
            xy_pca,
            f"PCA (var={pca.explained_variance_ratio_.sum():.2f})",
            pca_ratio,
            pca_flag,
        ),
        (axes[1], xy_tsne, "t-SNE", tsne_ratio, tsne_flag),
    ]:
        for name, color in [("LLD", "#1f77b4"), ("Helmholtz", "#ff7f0e")]:
            mask = labels == name
            ax.scatter(coords[mask, 0], coords[mask, 1], s=8, alpha=0.45, label=name, c=color)
        status = "FLAG" if flagged else "OK"
        ax.set_title(f"{title}  |  shift={ratio:.2f} ({status})")
        ax.legend(markerscale=2)
        ax.set_xlabel("dim 1")
        ax.set_ylabel("dim 2")

    fig.suptitle(f"DinoBloom backbone embeddings: LLD vs Helmholtz ({title_suffix})", fontsize=11)
    out_plot.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_plot, dpi=150)

    return {
        "n_lld": int((labels == "LLD").sum()),
        "n_helmholtz": int((labels == "Helmholtz").sum()),
        "embedding_dim": int(X.shape[1]),
        "pca_explained_var": float(pca.explained_variance_ratio_.sum()),
        "pca_shift_ratio": pca_ratio,
        "pca_flagged": pca_flag,
        "tsne_shift_ratio": tsne_ratio,
        "tsne_flagged": tsne_flag,
        "out_plot": str(out_plot),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="PCA/t-SNE sanity check on DinoBloom embeddings (LLD vs Helmholtz).")
    ap.add_argument("--manifest", type=Path, default=ROOT / "generated" / "attr_manifest.csv")
    ap.add_argument("--lld-split", default="train", choices=["train", "test"])
    ap.add_argument(
        "--helmholtz-root",
        type=Path,
        default=None,
        help="Helmholtz control image root (default: ~/helmholtz/data/control; use .../data_stainnorm/control after stain norm)",
    )
    ap.add_argument("--dinobloom-weights", default="auto")
    ap.add_argument("--dinobloom-variant", choices=["s", "b", "l", "g"], default="l")
    ap.add_argument("--dinobloom-hub-dir", default=None)
    ap.add_argument(
        "--attr-weights",
        type=Path,
        default=DEFAULT_DINOBLOOM_ATTR_WEIGHTS,
        help="Reference path for trained DinoBloom MLP (logged in summary only)",
    )
    ap.add_argument("--max-per-domain", type=int, default=1000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--pad", type=float, default=0.15, help="BBox padding for LLD manifest crops")
    ap.add_argument("--device", default="0")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--out-plot",
        type=Path,
        default=ROOT / "runs" / "predict" / "dinobloom_embedding_lld_vs_helmholtz.png",
    )
    ap.add_argument("--cache-npz", type=Path, default=None)
    args = ap.parse_args()

    if not args.manifest.is_file():
        sys.exit(f"LLD manifest not found: {args.manifest}")

    helmholtz_root = args.helmholtz_root or (resolve_helmholtz_data_root() / "control")
    if not helmholtz_root.is_dir():
        sys.exit(f"Helmholtz control root not found: {helmholtz_root}")

    if args.cache_npz and args.cache_npz.is_file():
        cached = np.load(args.cache_npz, allow_pickle=False)
        X = cached["X"]
        labels = cached["labels"].astype(str)
        print(f"Loaded cached embeddings: {args.cache_npz}  shape={X.shape}")
    else:
        from agentic_hematology.detection_agent_dinobloom import resolve_dinobloom_weights

        weights_path = resolve_dinobloom_weights(args.dinobloom_weights, args.dinobloom_variant)
        embedder = DinoBloomEmbedder(
            weights_path=weights_path,
            variant=args.dinobloom_variant,
            device=args.device,
            hub_dir=args.dinobloom_hub_dir,
        )
        print(f"DinoBloom embedder: {weights_path}  dim={embedder.embed_dim}  device={embedder.device}")

        lld = extract_lld_embeddings(
            embedder, args.manifest, args.lld_split, args.max_per_domain, args.seed, args.batch, args.pad
        )
        hz = extract_helmholtz_embeddings(
            embedder, helmholtz_root, args.max_per_domain, args.seed, args.batch
        )
        X = np.vstack([lld, hz]).astype(np.float32)
        labels = np.array(["LLD"] * len(lld) + ["Helmholtz"] * len(hz))

        if args.cache_npz:
            args.cache_npz.parent.mkdir(parents=True, exist_ok=True)
            np.savez(args.cache_npz, X=X, labels=labels)
            print(f"Cached embeddings: {args.cache_npz}")

    variant = args.dinobloom_variant.upper()
    summary = plot_embeddings(X, labels, args.out_plot, args.seed, f"DinoBloom-{variant}")
    summary.update(
        {
            "embedding_model": f"dinobloom_{args.dinobloom_variant}",
            "dinobloom_weights": args.dinobloom_weights,
            "attr_weights": str(args.attr_weights),
            "manifest": str(args.manifest),
            "lld_split": args.lld_split,
            "helmholtz_root": str(helmholtz_root),
            "max_per_domain": args.max_per_domain,
        }
    )
    summary_path = args.out_plot.with_suffix(".json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote plot: {args.out_plot}")
    print(f"Wrote summary: {summary_path}")
    print(
        f"LLD={summary['n_lld']}  Helmholtz={summary['n_helmholtz']}  "
        f"dim={summary['embedding_dim']}  PCA shift={summary['pca_shift_ratio']:.3f}  "
        f"t-SNE shift={summary['tsne_shift_ratio']:.3f}"
    )


if __name__ == "__main__":
    main()
