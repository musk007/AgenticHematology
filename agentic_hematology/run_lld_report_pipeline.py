#!/usr/bin/env python3
"""
Generate LLD hematology reports via the live detection pipeline.

Runs ``run_orchestrator.py`` on the LLD train/test split. All differential counts,
morphology, classification features, and report numbers come from detection →
aggregation only (no patient_WBC_stats JSON).

Ground-truth diagnosis labels for batch summary are read from image filenames
(``{patient}_*_{ALL|AML|...}.png``).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

WBC_CV = HERE / "wbc_unified" / "cv"
DEFAULT_OUT_DIR = HERE / "outputs" / "reports"
DEFAULT_CLASSIFIER = (
    HERE / "outputs" / "ablations" / "classifier" / "dinobloom" / "random_forest" / "leukemia_random_forest.pkl"
)
DEFAULT_DINOBLOOM_ATTR = WBC_CV / "runs" / "attribute_dinobloom" / "train" / "best_attr_dinobloom.pt"


def _run_orchestrator_batch(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        str(HERE / "run_orchestrator.py"),
        "--lld-split",
        args.split,
        "--backend",
        args.backend,
        "--yolo-weights",
        str(args.yolo_weights),
        "--classifier-model",
        str(args.classifier_model),
        "--report-backend",
        args.report_backend,
        "--instruction",
        args.instruction,
        "--device",
        str(args.device),
        "--out",
        str(args.out_dir),
    ]
    if args.backend == "dinobloom":
        cmd.extend(["--dinobloom-attr-weights", str(args.dinobloom_attr_weights)])
        if args.dinobloom_weights != "auto":
            cmd.extend(["--dinobloom-weights", str(args.dinobloom_weights)])
    elif args.backend == "wbc-unified":
        cmd.extend(["--effnet-weights", str(args.effnet_weights)])
    if not args.with_agent:
        cmd.append("--no-agent")
    print("Running detection → aggregation → classification → report pipeline...")
    print(" ".join(cmd))
    return subprocess.run(cmd, cwd=str(HERE)).returncode


def _write_manifest(args: argparse.Namespace, patient_ids: list[str], labels: dict[str, str]) -> Path:
    from agentic_hematology.leukemia_features import discover_lld_split_from_cv

    split = discover_lld_split_from_cv(args.cv_root)
    rows: list[dict] = []
    for pid in patient_ids:
        case_dir = args.out_dir / pid
        clf_path = case_dir / f"case_{pid}_classification.json"
        report_path = case_dir / f"case_{pid}_report.md"
        gt = labels.get(pid)
        pred = None
        if clf_path.is_file():
            pred = json.loads(clf_path.read_text(encoding="utf-8")).get("predicted_class")
        rows.append(
            {
                "patient_id": pid,
                "ground_truth_label": gt,
                "predicted_class": pred,
                "match": gt == pred if gt and pred else None,
                "classification_json": str(clf_path) if clf_path.is_file() else None,
                "report_md": str(report_path) if report_path.is_file() else None,
            }
        )

    manifest = {
        "split": args.split,
        "backend": args.backend,
        "label_source": "lld_image_filenames",
        "feature_source": "detection_pipeline",
        "n_patients": len(patient_ids),
        "patient_ids": patient_ids,
        "out_dir": str(args.out_dir),
        "cases": rows,
        "lld_split": split,
    }
    manifest_path = args.out_dir / "report_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Batch LLD reports from live detection (no stats JSON)."
    )
    ap.add_argument("--split", choices=("test", "train"), default="test")
    ap.add_argument("--cv-root", type=Path, default=WBC_CV)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument(
        "--backend",
        choices=("dinobloom", "wbc-unified"),
        default="dinobloom",
    )
    ap.add_argument("--yolo-weights", type=Path, default=WBC_CV / "runs" / "detector" / "train" / "weights" / "best.pt")
    ap.add_argument("--effnet-weights", type=Path, default=WBC_CV / "runs" / "attribute" / "train" / "best_attr.pt")
    ap.add_argument("--dinobloom-weights", default="auto")
    ap.add_argument("--dinobloom-attr-weights", type=Path, default=DEFAULT_DINOBLOOM_ATTR)
    ap.add_argument("--classifier-model", type=Path, default=DEFAULT_CLASSIFIER)
    ap.add_argument("--report-backend", choices=("template", "local-llm"), default="template")
    ap.add_argument("--device", default="0")
    ap.add_argument("--instruction", default="diagnose this case")
    ap.add_argument("--with-agent", action="store_true", help="Enable reflection agent loop.")
    args = ap.parse_args()

    if not args.classifier_model.is_file():
        raise SystemExit(
            f"Classifier not found: {args.classifier_model}\n"
            "Train first: python train_leukemia_from_dinobloom.py --backend all --device 0"
        )
    if args.backend == "dinobloom" and not args.dinobloom_attr_weights.is_file():
        raise SystemExit(f"DinoBloom attribute weights not found: {args.dinobloom_attr_weights}")

    from agentic_hematology.leukemia_features import (
        discover_lld_split_from_cv,
        discover_patient_labels_from_cv,
    )

    labels = discover_patient_labels_from_cv(args.cv_root)
    split = discover_lld_split_from_cv(args.cv_root)
    patient_ids = [pid for pid in split.get(args.split, []) if pid in labels]
    if not patient_ids:
        raise SystemExit(f"No labeled patients found for split={args.split}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rc = _run_orchestrator_batch(args)
    manifest_path = _write_manifest(args, patient_ids, labels)

    matched = sum(1 for row in json.loads(manifest_path.read_text())["cases"] if row.get("match") is True)
    total = sum(1 for row in json.loads(manifest_path.read_text())["cases"] if row.get("match") is not None)
    print(f"\nManifest: {manifest_path}")
    if total:
        print(f"Classifier accuracy on {args.split} split: {matched}/{total} ({100 * matched / total:.1f}%)")
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
