#!/usr/bin/env python3
"""
train_pipeline.py
=================
Training entry point for the AgenticHematology wbc_unified pipeline.

BY DEFAULT this script only fits the sklearn HybridClassifier — the
detector (YOLOv11) and attribute head (EfficientNet) are assumed to be
already trained and their weights present on disk. This matches the
project's design: those two models are fixed; only the patient-level
classifier is trained here.

What runs by default:
  Step 1 — cv/infer.py         : run existing det+attr weights on train split
  Step 2 — aggregate per patient: same aggregator used at inference time
  Step 3 — fit RandomForest    : saved to cv/runs/classifier/leukemia_rf.pkl

Opt-in only (use explicit flags if you ever need to retrain from scratch):
  --run-data-prep   : run data/prepare_dataset.py
  --run-detector    : run train_detector.py
  --run-attributes  : run train_attributes.py

Usage
-----
# Default — fit classifier using existing weights:
  python train_pipeline.py \
      --det-weights cv/runs/detector/train/weights/best.pt \
      --attr-weights cv/runs/attribute/train/best_attr.pt

# Weights at default paths (no args needed if trained in-place):
  python train_pipeline.py

# Explicitly retrain everything from scratch:
  python train_pipeline.py \
      --run-data-prep --run-detector --run-attributes \
      --det-ngpus 4 --det-batch 64 --attr-ngpus 4 --attr-batch 256

Environment variables (all optional):
  DATA_ROOT       path to LeukemiaDataset_Organized
  DET_MODEL       pretrained YOLO weights
  DET_EPOCHS      detector epochs (default 100)
  DET_BATCH       detector global batch (default 64)
  ATTR_EPOCHS     attribute epochs (default 40)
  ATTR_BATCH      attribute global batch (default 64)
  STAGE1_NGPUS    GPU count for both stages if not set individually
  STAGE1_DEVICE   GPU index for single-GPU runs (default 0)
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo layout
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent          # agentic_hematology/
WBC_UNIFIED = HERE / "wbc_unified"
CV   = WBC_UNIFIED / "cv"                       # wbc_unified/cv/

sys.path.insert(0, str(WBC_UNIFIED))
sys.path.insert(0, str(CV))

DEFAULT_DET_WEIGHTS  = CV / "runs" / "detector"  / "train" / "weights" / "best.pt"
DEFAULT_ATTR_WEIGHTS = CV / "runs" / "attribute" / "train" / "best_attr.pt"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))

def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)

def run(cmd: list[str], *, desc: str, cwd: Path | None = None) -> None:
    print(f"\n{'='*60}\n  {desc}\n  cmd: {' '.join(str(c) for c in cmd)}\n{'='*60}\n")
    result = subprocess.run(cmd, cwd=str(cwd or HERE))
    if result.returncode != 0:
        sys.exit(f"FAILED [{desc}] — exit code {result.returncode}")


# ---------------------------------------------------------------------------
# Optional Stage 0 — data preparation
# ---------------------------------------------------------------------------

def stage_data_prep(args: argparse.Namespace) -> None:
    cmd = [
        sys.executable,
        str(CV / "data" / "prepare_dataset.py"),
        "--data-root", str(args.data_root),
        "--out", str(CV / "generated"),
        "--image-mode", _env_str("DET_IMAGE_MODE", args.image_mode),
    ]
    run(cmd, desc="Stage 0: prepare_dataset", cwd=CV)
    manifest = CV / "generated" / "attr_manifest.csv"
    if not manifest.is_file():
        sys.exit(f"prepare_dataset did not produce {manifest}")


# ---------------------------------------------------------------------------
# Optional Stage 1a — detector
# ---------------------------------------------------------------------------

def stage_detector(args: argparse.Namespace) -> Path:
    ngpus  = args.det_ngpus
    device = ",".join(str(i) for i in range(ngpus)) if ngpus > 1 else str(args.device)
    det_model_default = (
        "/nfs-stor/zongyan/wbc_medical/rao.anwer/home_archive/"
        "LLD_nextgen_wbc_pipeline/yolo11m.pt"
    )
    cmd = [
        sys.executable, str(CV / "train_detector.py"),
        "--config",      str(CV / "configs" / "dataset.yaml"),
        "--model",       _env_str("DET_MODEL", det_model_default),
        "--epochs",      str(_env_int("DET_EPOCHS",      args.det_epochs)),
        "--imgsz",       str(args.det_imgsz),
        "--batch",       str(_env_int("DET_BATCH",       args.det_batch)),
        "--device",      device,
        "--ngpus",       str(ngpus),
        "--workers",     str(_env_int("DET_WORKERS",     args.det_workers)),
        "--project",     str(CV / "runs" / "detector"),
        "--name",        "train",
        "--save-period", str(_env_int("DET_SAVE_PERIOD", args.det_save_period)),
        "--patience",    str(args.det_patience),
    ]
    run(cmd, desc="Stage 1a: train_detector", cwd=CV)
    best = CV / "runs" / "detector" / "train" / "weights" / "best.pt"
    if not best.is_file():
        last = CV / "runs" / "detector" / "train" / "weights" / "last.pt"
        if last.is_file():
            return last
        sys.exit(f"Detector training produced no weights at {best}")
    return best


# ---------------------------------------------------------------------------
# Optional Stage 1b — attribute classifier
# ---------------------------------------------------------------------------

def stage_attributes(args: argparse.Namespace) -> Path:
    ngpus = args.attr_ngpus
    master_port = _env_int("MASTER_PORT", 29500 + (os.getpid() % 1000))
    base_cmd = [
        sys.executable, str(CV / "train_attributes.py"),
        "--config",   str(CV / "configs" / "dataset.yaml"),
        "--epochs",   str(_env_int("ATTR_EPOCHS",  args.attr_epochs)),
        "--batch",    str(_env_int("ATTR_BATCH",   args.attr_batch)),
        "--imgsz",    str(args.attr_imgsz),
        "--lr",       str(args.attr_lr),
        "--backbone", args.attr_backbone,
        "--workers",  str(_env_int("ATTR_WORKERS", args.attr_workers)),
        "--project",  str(CV / "runs" / "attribute"),
        "--name",     "train",
    ]
    if ngpus > 1:
        cmd = [
            sys.executable, "-m", "torch.distributed.run",
            f"--nproc_per_node={ngpus}",
            f"--master_port={master_port}",
        ] + base_cmd[1:]
    else:
        cmd = base_cmd + ["--device", str(args.device)]
    run(cmd, desc="Stage 1b: train_attributes", cwd=CV)
    best = CV / "runs" / "attribute" / "train" / "best_attr.pt"
    if not best.is_file():
        sys.exit(f"Attribute training produced no weights at {best}")
    return best


# ---------------------------------------------------------------------------
# Stage 2 — sklearn HybridClassifier fit (DEFAULT, always runs)
# ---------------------------------------------------------------------------

def _run_infer(args: argparse.Namespace, det_weights: Path, attr_weights: Path) -> Path:
    out_dir = CV / "runs" / "predict" / "classifier_fit_infer"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, str(CV / "infer.py"),
        "--det-weights",  str(det_weights),
        "--attr-weights", str(attr_weights),
        "--split",        "train",
        "--conf",         str(args.conf_threshold),
        "--device",       str(args.device),
        "--save-json",
        "--out",          str(CV / "runs" / "predict"),
        "--name",         "classifier_fit_infer",
    ]
    run(cmd, desc="Classifier fit: infer train split", cwd=CV)
    pred_json = out_dir / "train_predictions.json"
    if not pred_json.is_file():
        sys.exit(f"infer.py did not produce {pred_json}")
    return pred_json


def _build_features_labels(pred_json: Path):
    import json as _json

    payload = _json.loads(pred_json.read_text())

    try:
        from agentic_hematology.aggregator import aggregate
        from agentic_hematology.schemas import Detection, DetectionResult
        from agentic_hematology.leukemia_classifier import HybridClassifier
    except ModuleNotFoundError:
        sys.path.insert(0, str(HERE.parent))
        from agentic_hematology.aggregator import aggregate
        from agentic_hematology.schemas import Detection, DetectionResult
        from agentic_hematology.leukemia_classifier import HybridClassifier

    patients: dict[str, dict] = {}
    for img_rec in payload:
        image_path = Path(str(img_rec.get("image", "")))
        stem_parts = image_path.stem.split("_")
        if len(stem_parts) < 5:
            continue
        pid = stem_parts[0]
        gt_label = stem_parts[-1].strip()
        if not gt_label:
            continue
        rec = patients.setdefault(pid, {"patient_id": pid, "label": gt_label, "images": []})
        rec["images"].append(img_rec)

    X, y = [], []
    for patient in patients.values():
        pid      = str(patient.get("patient_id", "unknown"))
        gt_label = str(patient.get("label", "")).strip()
        detections = []
        for img_idx, img_rec in enumerate(patient.get("images", [])):
            image_id = Path(str(img_rec.get("image", ""))).name
            for cell_idx, cell in enumerate(img_rec.get("cells", [])):
                attrs = dict(cell.get("attributes", {}))
                attrs["class_id"] = cell.get("class_id")
                detections.append(Detection(
                    cell_id=f"img{img_idx:03d}_c{cell_idx:03d}",
                    image_id=image_id,
                    bbox_xyxy=tuple(float(v) for v in cell.get("xyxy", [0, 0, 1, 1])),
                    cell_type=str(cell.get("class_name", "Unknown")),
                    objectness=float(cell.get("conf", 0.0)),
                    attributes=attrs,
                    attribute_probs={},
                ))
        if not detections:
            continue

        findings = aggregate(DetectionResult(
            case_id=pid,
            n_images=len(patient.get("images", [])),
            detections=detections,
        ))
        X.append(HybridClassifier._features(findings))
        y.append(gt_label)

    return X, y


def stage_classifier(args: argparse.Namespace, det_weights: Path, attr_weights: Path) -> Path:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder

    pred_json = _run_infer(args, det_weights, attr_weights)
    print("\nBuilding patient-level features from predictions...")
    X_dicts, y_raw = _build_features_labels(pred_json)

    if len(X_dicts) < 5:
        sys.exit(f"Only {len(X_dicts)} labelled patients found — cannot fit classifier.")

    all_keys = sorted({k for d in X_dicts for k in d})
    X = [[d.get(k, 0.0) for k in all_keys] for d in X_dicts]
    le = LabelEncoder()
    y  = le.fit_transform(y_raw).tolist()

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X, y)
    clf.classes_ = le.classes_   # string labels for LearnedClassifier wrapper

    save_dir = CV / "runs" / "classifier"
    save_dir.mkdir(parents=True, exist_ok=True)
    out_path = save_dir / "leukemia_rf.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(clf, f)

    meta = {"feature_keys": all_keys, "classes": list(le.classes_)}
    (save_dir / "leukemia_rf_meta.json").write_text(json.dumps(meta, indent=2))

    preds   = clf.predict(X)
    correct = sum(a == b for a, b in zip(preds, y))
    print(f"  Patients: {len(X)}  Classes: {list(le.classes_)}")
    print(f"  In-sample accuracy: {correct}/{len(X)} = {correct/len(X):.1%}  (sanity only)")
    print(f"  Model : {out_path}")
    print(f"  Meta  : {save_dir / 'leukemia_rf_meta.json'}")
    return out_path


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def write_summary(results: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "train_pipeline_summary.json"
    summary_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n{'='*60}\n  Training pipeline complete\n{'='*60}")
    for stage, info in results.items():
        print(f"  [{stage}]")
        for k, v in info.items():
            print(f"    {k}: {v}")
    print(f"\n  Summary: {summary_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "AgenticHematology classifier training. "
            "By default ONLY fits the sklearn HybridClassifier using existing "
            "detector and attribute weights. Use --run-detector / --run-attributes "
            "only if you need to retrain those models from scratch."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # ---- weights (used by default classifier-fit path) ----
    p.add_argument("--det-weights",  type=Path, default=DEFAULT_DET_WEIGHTS,
                   help="Existing YOLOv11 detector weights")
    p.add_argument("--attr-weights", type=Path, default=DEFAULT_ATTR_WEIGHTS,
                   help="Existing EfficientNet attribute weights")

    # ---- opt-in retraining flags ----
    retrain = p.add_argument_group("opt-in retraining (disabled by default)")
    retrain.add_argument("--run-data-prep",  action="store_true",
                         help="Run data/prepare_dataset.py before training")
    retrain.add_argument("--run-detector",   action="store_true",
                         help="Retrain the YOLOv11 detector from scratch")
    retrain.add_argument("--run-attributes", action="store_true",
                         help="Retrain the EfficientNet attribute head from scratch")

    # ---- shared ----
    p.add_argument("--data-root", type=Path,
                   default=Path(_env_str("DATA_ROOT",
                       "/nfs-stor/zongyan/datasets/medical/LeukemiaDataset_Organized")))
    p.add_argument("--device", default=_env_str("STAGE1_DEVICE", "0"))
    p.add_argument("--conf-threshold", type=float, default=0.25)
    p.add_argument("--image-mode", default=_env_str("DET_IMAGE_MODE", "auto"),
                   choices=("auto", "hardlink", "copy", "symlink"))

    # ---- detector (only used with --run-detector) ----
    det = p.add_argument_group("detector args (only with --run-detector)")
    det.add_argument("--det-ngpus",       type=int,  default=_env_int("STAGE1_NGPUS", 4))
    det.add_argument("--det-epochs",      type=int,  default=_env_int("DET_EPOCHS", 100))
    det.add_argument("--det-batch",       type=int,  default=_env_int("DET_BATCH", 64))
    det.add_argument("--det-imgsz",       type=int,  default=640)
    det.add_argument("--det-workers",     type=int,  default=_env_int("DET_WORKERS", 0))
    det.add_argument("--det-save-period", type=int,  default=_env_int("DET_SAVE_PERIOD", 5))
    det.add_argument("--det-patience",    type=int,  default=30)

    # ---- attribute (only used with --run-attributes) ----
    attr = p.add_argument_group("attribute args (only with --run-attributes)")
    attr.add_argument("--attr-ngpus",    type=int,   default=_env_int("STAGE1_NGPUS", 4))
    attr.add_argument("--attr-epochs",   type=int,   default=_env_int("ATTR_EPOCHS", 40))
    attr.add_argument("--attr-batch",    type=int,   default=_env_int("ATTR_BATCH", 256))
    attr.add_argument("--attr-imgsz",    type=int,   default=224)
    attr.add_argument("--attr-lr",       type=float, default=3e-4)
    attr.add_argument("--attr-backbone", default="efficientnet_b0",
                      choices=["efficientnet_b0", "resnet18"])
    attr.add_argument("--attr-workers",  type=int,   default=_env_int("ATTR_WORKERS", 2))

    return p.parse_args()


def main() -> None:
    args = parse_args()
    results: dict = {}

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    print("\nAgenticHematology — training pipeline")
    print(f"  run_detector   : {args.run_detector}")
    print(f"  run_attributes : {args.run_attributes}")
    print(f"  classifier fit : always (default)")
    print(f"  det_weights    : {args.det_weights}")
    print(f"  attr_weights   : {args.attr_weights}")

    # ---- optional data prep ----
    if args.run_data_prep:
        stage_data_prep(args)
        results["data_prep"] = {"done": True}

    # ---- optional detector retraining ----
    if args.run_detector:
        args.det_weights = stage_detector(args)
        results["detector"] = {"weights": str(args.det_weights)}
    else:
        if not args.det_weights.is_file():
            sys.exit(
                f"Detector weights not found: {args.det_weights}\n"
                "Pass --det-weights <path> or use --run-detector to train."
            )
        results["detector"] = {"skipped": True, "weights": str(args.det_weights)}

    # ---- optional attribute retraining ----
    if args.run_attributes:
        args.attr_weights = stage_attributes(args)
        results["attributes"] = {"weights": str(args.attr_weights)}
    else:
        if not args.attr_weights.is_file():
            sys.exit(
                f"Attribute weights not found: {args.attr_weights}\n"
                "Pass --attr-weights <path> or use --run-attributes to train."
            )
        results["attributes"] = {"skipped": True, "weights": str(args.attr_weights)}

    # ---- classifier fit (always) ----
    clf_path = stage_classifier(args, args.det_weights, args.attr_weights)
    results["classifier"] = {
        "model": str(clf_path),
        "meta":  str(clf_path.parent / "leukemia_rf_meta.json"),
    }

    write_summary(results, CV / "runs")


if __name__ == "__main__":
    main()