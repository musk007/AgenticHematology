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
    pred_json = out_dir / "train_predictions.json"
    if getattr(args, "skip_infer", False):
        if not pred_json.is_file():
            sys.exit(
                f"--skip-infer set but {pred_json} not found.\n"
                "Run without --skip-infer once, or point --train-predictions-json to an existing file."
            )
        print(f"\nSkipping infer; using existing {pred_json}")
        return pred_json
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
    if not pred_json.is_file():
        sys.exit(f"infer.py did not produce {pred_json}")
    return pred_json


def _build_features_labels(
    pred_json: Path,
    mll_json: Path | None = None,
    helmholtz_patient_ids: set[str] | None = None,
    return_sources: bool = False,
):
    import json as _json

    payload = _json.loads(pred_json.read_text())
    if isinstance(payload, dict) and "predictions" in payload:
        payload = payload["predictions"]

    try:
        from agentic_hematology.aggregator import aggregate
        from agentic_hematology.schemas import Detection, DetectionResult
        from agentic_hematology.leukemia_classifier import HybridClassifier
    except ModuleNotFoundError:
        sys.path.insert(0, str(HERE.parent))
        from agentic_hematology.aggregator import aggregate
        from agentic_hematology.schemas import Detection, DetectionResult
        from agentic_hematology.leukemia_classifier import HybridClassifier

    def _ingest_records(records: list, patients: dict[str, dict]) -> None:
        for img_rec in records:
            image_path = Path(str(img_rec.get("image", "")))
            explicit_pid = img_rec.get("patient_id")
            explicit_label = img_rec.get("patient_label")
            if explicit_pid:
                pid = str(explicit_pid)
                gt_label = str(explicit_label or img_rec.get("label", "")).strip()
            else:
                stem_parts = image_path.stem.split("_")
                if len(stem_parts) < 5:
                    continue
                pid = stem_parts[0]
                gt_label = stem_parts[-1].strip()
            if not gt_label:
                continue
            rec = patients.setdefault(pid, {"patient_id": pid, "label": gt_label, "images": []})
            rec["images"].append(img_rec)

    patients: dict[str, dict] = {}
    helmholtz_pids: set[str] = set()
    _ingest_records(payload, patients)

    if mll_json and mll_json.is_file():
        mll_payload = _json.loads(mll_json.read_text())
        mll_records = mll_payload.get("predictions", mll_payload)
        if isinstance(mll_records, list):
            if helmholtz_patient_ids is not None:
                before = len({str(r.get("patient_id")) for r in mll_records})
                mll_records = [
                    r for r in mll_records
                    if str(r.get("patient_id", "")) in helmholtz_patient_ids
                ]
                after = len({str(r.get("patient_id")) for r in mll_records})
                print(f"  Helmholtz subset: {after}/{before} patients")
            for img_rec in mll_records:
                pid = str(img_rec.get("patient_id", ""))
                if pid:
                    helmholtz_pids.add(pid)
            _ingest_records(mll_records, patients)
            print(f"  Merged Helmholtz patients from {mll_json}")

    X, y, sources = [], [], []
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
        sources.append("helmholtz" if pid in helmholtz_pids else "lld")

    if return_sources:
        return X, y, sources
    return X, y


def stage_classifier(args: argparse.Namespace, det_weights: Path, attr_weights: Path) -> Path:
    from collections import Counter

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.preprocessing import LabelEncoder

    pred_json = (
        Path(args.train_predictions_json)
        if getattr(args, "train_predictions_json", None)
        else _run_infer(args, det_weights, attr_weights)
    )
    print("\nBuilding patient-level features from predictions...")
    mll_json = getattr(args, "mll_predictions_json", None)
    helmholtz_patient_ids: set[str] | None = None
    helmholtz_split_json = getattr(args, "helmholtz_split_json", None)
    split_path: Path | None = None
    if args.include_healthy_class:
        if mll_json is None:
            sys.path.insert(0, str(CV))
            from mll_helmholtz import resolve_helmholtz_classifier_predictions_json

            mll_json = resolve_helmholtz_classifier_predictions_json()
        if not Path(mll_json).is_file():
            sys.exit(
                f"Helmholtz training JSON not found: {mll_json}\n"
                "Run:\n"
                "  python wbc_unified/cv/train_dinobloom_cell_classifier.py\n"
                "  python wbc_unified/cv/extract_helmholtz_cells.py --device 0\n"
                "Or (metadata fallback): python wbc_unified/cv/build_helmholtz_metadata.py --classifier-only"
            )
        split_path = Path(helmholtz_split_json) if helmholtz_split_json else CV / "generated" / "helmholtz_split.json"
        if split_path.is_file():
            sys.path.insert(0, str(CV))
            from mll_helmholtz import helmholtz_patient_ids_for_split, load_helmholtz_split
            split_payload = load_helmholtz_split(split_path)
            helmholtz_patient_ids = helmholtz_patient_ids_for_split(split_payload, "train")
            print(f"  Using Helmholtz train split ({len(helmholtz_patient_ids)} patients) from {split_path}")
        elif helmholtz_split_json:
            sys.exit(f"Helmholtz split file not found: {split_path}")
        else:
            print("  No helmholtz_split.json found — using all Helmholtz patients for training")

    domain_normalize = bool(getattr(args, "domain_normalize", False))
    if domain_normalize and not args.include_healthy_class:
        sys.exit("--domain-normalize requires --include-healthy-class (LLD + Helmholtz training)")

    if domain_normalize or args.include_healthy_class:
        X_dicts, y_raw, sources = _build_features_labels(
            pred_json,
            mll_json if args.include_healthy_class else None,
            helmholtz_patient_ids,
            return_sources=True,
        )
    else:
        X_dicts, y_raw = _build_features_labels(
            pred_json,
            None,
            None,
        )
        sources = ["lld"] * len(X_dicts)

    if len(X_dicts) < 5:
        sys.exit(f"Only {len(X_dicts)} labelled patients found — cannot fit classifier.")

    label_counts = Counter(y_raw)
    print(f"  Label distribution: {dict(sorted(label_counts.items()))}")

    base_dim = len(sorted({k for d in X_dicts for k in d}))
    normalizer = None
    norm_stats_path: Path | None = None
    if domain_normalize:
        sys.path.insert(0, str(HERE.parent))
        from agentic_hematology.domain_feature_norm import DATASET_SOURCE_KEY, DomainFeatureNormalizer

        normalizer = DomainFeatureNormalizer()
        normalizer.fit(X_dicts, sources)
        X_dicts = normalizer.transform_batch(X_dicts, sources)
        all_keys = normalizer.feature_keys()
        print(f"  Domain normalize: base features={base_dim} -> model features={len(all_keys)} (+{DATASET_SOURCE_KEY})")
    else:
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
    if domain_normalize and args.include_healthy_class:
        out_name = "leukemia_rf_6class_domainnorm.pkl"
        meta_name = "leukemia_rf_6class_domainnorm_meta.json"
        norm_stats_path = save_dir / "leukemia_rf_6class_domainnorm_norm_stats.json"
    elif args.include_healthy_class:
        out_name = "leukemia_rf_6class.pkl"
        meta_name = "leukemia_rf_6class_meta.json"
    else:
        out_name = "leukemia_rf.pkl"
        meta_name = "leukemia_rf_meta.json"
    out_path = save_dir / out_name
    with open(out_path, "wb") as f:
        pickle.dump(clf, f)

    if normalizer is not None and norm_stats_path is not None:
        normalizer.save(norm_stats_path)
        lld_stats_path, hz_stats_path = normalizer.write_split_stats(save_dir)
        print(f"  Norm stats: {norm_stats_path}")
        print(f"  LLD stats : {lld_stats_path}")
        print(f"  HZ stats  : {hz_stats_path}")

    meta = {
        "feature_keys": all_keys,
        "classes": list(le.classes_),
        "include_healthy_class": args.include_healthy_class,
        "domain_normalize": domain_normalize,
        "healthy_cell_pct_threshold": args.healthy_cell_pct_threshold,
        "label_counts": dict(label_counts),
        "training_sources": {
            "lld_predictions_json": str(pred_json),
            "helmholtz_predictions_json": str(mll_json) if args.include_healthy_class else None,
            "helmholtz_split_json": str(split_path)
            if args.include_healthy_class and helmholtz_patient_ids is not None
            else None,
            "helmholtz_split_used": "train" if helmholtz_patient_ids is not None else None,
        },
    }
    if norm_stats_path is not None:
        meta["domain_norm_stats_json"] = str(norm_stats_path)
    (save_dir / meta_name).write_text(json.dumps(meta, indent=2))

    if hasattr(clf, "feature_importances_"):
        ranked = sorted(
            zip(all_keys, clf.feature_importances_.tolist()),
            key=lambda item: item[1],
            reverse=True,
        )
        print("  Top feature importances:")
        for name, score in ranked[:8]:
            print(f"    {name}: {score:.4f}")
        ds_rank = next((i + 1 for i, (name, _) in enumerate(ranked) if name == "dataset_source"), None)
        if ds_rank is not None:
            print(f"  dataset_source importance rank: {ds_rank}/{len(ranked)}")
        meta["feature_importances"] = {name: float(score) for name, score in ranked}
        (save_dir / meta_name).write_text(json.dumps(meta, indent=2))

    raw_preds = clf.predict(X)
    if len(raw_preds) and isinstance(raw_preds[0], str):
        pred_labels = list(raw_preds)
    else:
        pred_labels = le.inverse_transform(raw_preds)
    correct = sum(a == b for a, b in zip(pred_labels, y_raw))
    print(f"  Patients: {len(X)}  Classes: {list(le.classes_)}")
    print(f"  In-sample accuracy: {correct}/{len(X)} = {correct/len(X):.1%}  (sanity only)")
    print("  Confusion matrix (in-sample):")
    print(confusion_matrix(y_raw, pred_labels, labels=list(le.classes_)))
    print(classification_report(y_raw, pred_labels, labels=list(le.classes_)))
    print(f"  Model : {out_path}")
    print(f"  Meta  : {save_dir / meta_name}")
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

    # ---- classifier fit ----
    clf = p.add_argument_group("classifier fit")
    clf.add_argument(
        "--skip-infer",
        action="store_true",
        help="Reuse cv/runs/predict/classifier_fit_infer/train_predictions.json instead of re-running infer.py",
    )
    clf.add_argument(
        "--train-predictions-json",
        type=Path,
        default=None,
        help="LLD train-split predictions JSON (overrides infer / --skip-infer default path)",
    )

    # ---- 6-class: LLD train + full Helmholtz dataset ----
    healthy = p.add_argument_group("6-class LLD + Helmholtz training")
    healthy.add_argument(
        "--include-healthy-class",
        action="store_true",
        help=(
            "Train on LLD train split plus full Helmholtz dataset "
            "(AML/APML/Healthy from metadata differentials)"
        ),
    )
    healthy.add_argument(
        "--mll-predictions-json",
        type=Path,
        default=None,
        help=(
            "Helmholtz JSON from build_helmholtz_metadata.py --classifier-only "
            "(default: helmholtz_cell_predictions.json if present, else helmholtz_predictions.json)"
        ),
    )
    healthy.add_argument(
        "--helmholtz-split-json",
        type=Path,
        default=None,
        help=(
            "Helmholtz train/test manifest from split_helmholtz.py "
            "(default: cv/generated/helmholtz_split.json when present)"
        ),
    )
    healthy.add_argument(
        "--domain-normalize",
        action="store_true",
        help=(
            "Per-dataset z-score normalization + dataset_source feature "
            "(saves leukemia_rf_6class_domainnorm.pkl)"
        ),
    )
    healthy.add_argument(
        "--healthy-cell-pct-threshold",
        type=float,
        default=65.0,
        help="Rule-based Healthy call when mature WBC %% exceeds this (see leukemia_classifier.py)",
    )

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
        "meta":  str(clf_path.with_name(f"{clf_path.stem}_meta.json")),
    }

    write_summary(results, CV / "runs")


if __name__ == "__main__":
    main()