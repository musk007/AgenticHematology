#!/usr/bin/env python3
"""PCA / t-SNE sanity check: LLD attribute vectors vs MLL Helmholtz Healthy cells."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _load_attr_matrix_from_infer_json(path: Path, max_rows: int | None) -> np.ndarray:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "predictions" in payload:
        records = payload["predictions"]
    elif isinstance(payload, list):
        records = payload
    else:
        raise ValueError(f"Unexpected JSON layout in {path}")

    rows: list[list[float]] = []
    for rec in records:
        for cell in rec.get("cells", []):
            attrs = cell.get("attributes") or {}
            if not attrs:
                continue
            rows.append([float(attrs[k]) for k in sorted(attrs.keys())])
            if max_rows and len(rows) >= max_rows:
                return np.asarray(rows, dtype=np.float32)
    if not rows:
        raise ValueError(f"No attribute vectors in {path}")
    return np.asarray(rows, dtype=np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lld-json", type=Path, required=True, help="LLD infer JSON (train or test predictions)")
    ap.add_argument("--mll-json", type=Path, required=True, help="MLL Helmholtz extract_mll_attributes output")
    ap.add_argument("--out-plot", type=Path, default=ROOT / "runs" / "predict" / "feature_distribution.png")
    ap.add_argument("--max-per-domain", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    lld = _load_attr_matrix_from_infer_json(args.lld_json, args.max_per_domain)
    mll = _load_attr_matrix_from_infer_json(args.mll_json, args.max_per_domain)
    n_attr = min(lld.shape[1], mll.shape[1])
    lld, mll = lld[:, :n_attr], mll[:, :n_attr]

    X = np.vstack([lld, mll])
    labels = np.array(["LLD"] * len(lld) + ["MLL_Healthy"] * len(mll))

    pca = PCA(n_components=2, random_state=args.seed)
    xy = pca.fit_transform(X)

    perplexity = min(30, max(5, len(X) // 10))
    tsne = TSNE(n_components=2, random_state=args.seed, perplexity=perplexity, init="pca")
    xy_tsne = tsne.fit_transform(X)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, coords, title in [
        (axes[0], xy, f"PCA (var={pca.explained_variance_ratio_.sum():.2f})"),
        (axes[1], xy_tsne, "t-SNE"),
    ]:
        for name, color in [("LLD", "#1f77b4"), ("MLL_Healthy", "#ff7f0e")]:
            mask = labels == name
            ax.scatter(coords[mask, 0], coords[mask, 1], s=8, alpha=0.5, label=name, c=color)
        ax.set_title(title)
        ax.legend()
        ax.set_xlabel("dim 1")
        ax.set_ylabel("dim 2")

    # Domain-shift flag: centroid distance in PCA space relative to LLD spread.
    lld_xy = xy[labels == "LLD"]
    mll_xy = xy[labels == "MLL_Healthy"]
    centroid_dist = float(np.linalg.norm(lld_xy.mean(axis=0) - mll_xy.mean(axis=0)))
    lld_spread = float(np.mean(np.linalg.norm(lld_xy - lld_xy.mean(axis=0), axis=1)))
    shift_ratio = centroid_dist / max(lld_spread, 1e-6)
    flag = shift_ratio > 1.5
    fig.suptitle(
        f"DinoBloom attribute vectors (MLP head)  |  domain shift ratio={shift_ratio:.2f}"
        + ("  ** FLAG **" if flag else "  (OK)"),
        fontsize=11,
    )
    args.out_plot.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(args.out_plot, dpi=150)
    print(f"Wrote plot: {args.out_plot}")
    print(f"LLD cells: {len(lld)}  MLL Healthy cells: {len(mll)}")
    print(f"PCA centroid distance / LLD spread = {shift_ratio:.3f}  flagged={flag}")


if __name__ == "__main__":
    main()
