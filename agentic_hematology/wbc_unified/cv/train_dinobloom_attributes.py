#!/usr/bin/env python3
"""Train linear attribute probes on frozen DinoBloom embeddings (ablation vs EfficientNet)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
REPO_PARENT = ROOT.parent.parent.parent
sys.path.insert(0, str(REPO_PARENT))
sys.path.insert(0, str(ROOT))

from agentic_hematology.detection_agent_dinobloom import DinoBloomEmbedder, resolve_dinobloom_weights  # noqa: E402
from data.cell_dataset import load_manifest  # noqa: E402
from utils.labels import ATTR_NAMES, crop_with_padding  # noqa: E402


def _embed_manifest_rows(
    embedder: DinoBloomEmbedder,
    rows: list[dict],
    imgsz: int,
    pad: float,
    batch: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (embeddings, y_true, valid_mask) with shape (N,D), (N,A), (N,A) bool."""
    n = len(rows)
    d = embedder.embed_dim
    a = len(ATTR_NAMES)
    embeddings = np.zeros((n, d), dtype=np.float32)
    y_true = np.full((n, a), -1, dtype=np.int8)
    valid = np.zeros((n, a), dtype=bool)

    batch_crops: list[Image.Image] = []
    batch_idx: list[int] = []

    def flush() -> None:
        nonlocal batch_crops, batch_idx
        if not batch_crops:
            return
        embs = embedder.embed_pil_batch(batch_crops)
        for bi, row_i in enumerate(batch_idx):
            embeddings[row_i] = embs[bi]
        batch_crops = []
        batch_idx = []

    for i, row in enumerate(tqdm(rows, desc="Embedding crops")):
        image = Image.open(row["image"]).convert("RGB")
        w, h = image.size
        xywh = np.array([float(row["x"]), float(row["y"]), float(row["w"]), float(row["h"])], dtype=np.float32)
        x1, y1, x2, y2 = crop_with_padding(w, h, xywh, pad=pad)
        crop = image.crop((x1, y1, x2, y2)).resize((imgsz, imgsz), Image.BILINEAR)
        batch_crops.append(crop)
        batch_idx.append(i)
        for j, name in enumerate(ATTR_NAMES):
            v = int(row[name])
            if v in (0, 1):
                y_true[i, j] = v
                valid[i, j] = True
        if len(batch_crops) >= batch:
            flush()
    flush()
    return embeddings, y_true, valid


def _fit_probes(
    x: np.ndarray,
    y_true: np.ndarray,
    valid: np.ndarray,
    c_scale: float,
) -> tuple[dict[str, LogisticRegression], dict[str, float]]:
    probes: dict[str, LogisticRegression] = {}
    f1s: dict[str, float] = {}
    n_train = int(valid.any(axis=1).sum())
    for j, name in enumerate(ATTR_NAMES):
        mask = valid[:, j]
        if mask.sum() < 10:
            print(f"WARNING: too few labels for {name}; skipping probe.")
            continue
        y = y_true[mask, j]
        n_pos = int((y == 1).sum())
        n_neg = int((y == 0).sum())
        c = max(1e-3, c_scale * len(ATTR_NAMES) * n_train / 100.0)
        clf = LogisticRegression(
            penalty="l2",
            C=c,
            class_weight="balanced",
            max_iter=2000,
            random_state=0,
        )
        clf.fit(x[mask], y)
        pred = clf.predict(x[mask])
        f1s[name] = float(f1_score(y, pred, zero_division=0))
        probes[name] = clf
        print(f"  {name}: n={mask.sum()} pos={n_pos} neg={n_neg} val_f1={f1s[name]:.4f}")
    mean_f1 = float(np.mean(list(f1s.values()))) if f1s else 0.0
    return probes, {"per_attribute_f1": f1s, "mean_f1": mean_f1}


def main() -> None:
    ap = argparse.ArgumentParser(description="Fit DinoBloom linear probes for LLD morphology attributes.")
    ap.add_argument("--manifest", type=Path, default=ROOT / "generated" / "attr_manifest.csv")
    ap.add_argument("--train-split", type=str, default="train")
    ap.add_argument("--val-split", type=str, default="test", help="Validation split name in manifest.")
    ap.add_argument("--dinobloom-weights", type=str, default="auto")
    ap.add_argument("--dinobloom-variant", choices=["s", "b", "l", "g"], default="l")
    ap.add_argument("--dinobloom-hub-dir", type=Path, default=None)
    ap.add_argument("--device", type=str, default=None)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--pad", type=float, default=0.15)
    ap.add_argument("--embed-batch", type=int, default=32)
    ap.add_argument("--project", type=Path, default=ROOT / "runs" / "attribute_dinobloom")
    ap.add_argument("--name", type=str, default="train")
    args = ap.parse_args()

    if not args.manifest.is_file():
        sys.exit(f"Manifest not found: {args.manifest}")

    weights_path = resolve_dinobloom_weights(args.dinobloom_weights, args.dinobloom_variant)
    embedder = DinoBloomEmbedder(
        weights_path=weights_path,
        variant=args.dinobloom_variant,
        device=args.device,
        hub_dir=str(args.dinobloom_hub_dir) if args.dinobloom_hub_dir else None,
    )

    train_rows = load_manifest(args.manifest, args.train_split)
    val_rows = load_manifest(args.manifest, args.val_split)
    if not train_rows:
        sys.exit(f"No rows for split={args.train_split!r} in {args.manifest}")

    print(f"Embedding {len(train_rows)} train crops with DinoBloom-{args.dinobloom_variant.upper()}...")
    x_train, y_train, v_train = _embed_manifest_rows(
        embedder, train_rows, args.imgsz, args.pad, args.embed_batch
    )

    print("Fitting attribute linear probes...")
    probes, train_metrics = _fit_probes(x_train, y_train, v_train, c_scale=1.0)

    val_metrics: dict = {}
    if val_rows:
        print(f"Evaluating on {len(val_rows)} val crops...")
        x_val, y_val, v_val = _embed_manifest_rows(
            embedder, val_rows, args.imgsz, args.pad, args.embed_batch
        )
        val_f1s: dict[str, float] = {}
        for name, clf in probes.items():
            j = ATTR_NAMES.index(name)
            mask = v_val[:, j]
            if mask.sum() == 0:
                continue
            pred = clf.predict(x_val[mask])
            val_f1s[name] = float(f1_score(y_val[mask, j], pred, zero_division=0))
        val_metrics = {
            "per_attribute_f1": val_f1s,
            "mean_f1": float(np.mean(list(val_f1s.values()))) if val_f1s else 0.0,
        }
        print(f"Validation mean F1: {val_metrics['mean_f1']:.4f}")

    save_dir = args.project / args.name
    save_dir.mkdir(parents=True, exist_ok=True)
    out_path = save_dir / "best_attr_probes.joblib"
    payload = {
        "attribute_names": list(ATTR_NAMES),
        "probes": probes,
        "dinobloom_variant": args.dinobloom_variant,
        "dinobloom_weights": weights_path,
    }
    try:
        import joblib
    except ImportError as exc:
        raise SystemExit("pip install joblib") from exc
    joblib.dump(payload, out_path)

    meta = {
        "manifest": str(args.manifest),
        "train_split": args.train_split,
        "val_split": args.val_split,
        "train_metrics": train_metrics,
        "val_metrics": val_metrics,
        "probes_path": str(out_path),
    }
    meta_path = save_dir / "metrics.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Saved attribute probes: {out_path}")
    print(f"Metrics: {meta_path}")


if __name__ == "__main__":
    main()
