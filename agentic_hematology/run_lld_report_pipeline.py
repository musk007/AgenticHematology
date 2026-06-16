#!/usr/bin/env python3
"""
Generate LLD hematology reports from patient stats + trained classifier outputs.

Read-only use of wbc_unified/ (template report + LLD split). Does not modify
wbc_unified. Writes summaries and markdown under runs/reports/.

Default: test-split patients only (13), using stats JSON + classifier predictions.
Optional --run-detection invokes run_orchestrator.py (GPU + YOLO/EfficientNet weights).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

WBC_CV = HERE / "wbc_unified" / "cv"
DEFAULT_STATS_JSON = Path(
    "/home/roba.majzoub/AgenticHematology/data_preprocessing/patient_WBC_stats_NoOveralp.json"
)
DEFAULT_OUT_DIR = HERE / "runs" / "reports"
DEFAULT_CLASSIFIER_DIR = HERE / "runs" / "classifier"

CELL_DISPLAY: dict[str, str] = {
    "myeloblast": "Myeloblast",
    "lymphoblast": "Lymphoblast",
    "neutrophil": "Neutrophil",
    "atypical lymphocyte": "Atypical lymphocyte",
    "promonocyte": "Promonocyte",
    "monoblast": "Monoblast",
    "lymphocyte": "Lymphocyte",
    "myelocyte": "Myelocyte",
    "abnormal promyelocyte": "Abnormal promyelocyte",
    "monocyte": "Monocyte",
    "metamyelocyte": "Metamyelocyte",
    "eosinophil": "Eosinophil",
    "basophil": "Basophil",
    "none": "None",
}

BLAST_CLASSES = {
    "Myeloblast",
    "Lymphoblast",
    "Monoblast",
    "Abnormal promyelocyte",
}


def _display_cell(name: str) -> str:
    key = str(name).strip().lower()
    return CELL_DISPLAY.get(key, str(name).strip().title())


def _classifier_dir(backend: str) -> Path:
    aliases = {
        "lightgbm": ["lightgbm", "lightGBM", "LightGBM"],
        "random_forest": ["random_forest", "random-forest"],
        "xgboost": ["xgboost", "XGBoost"],
    }
    for name in aliases.get(backend, [backend]):
        path = DEFAULT_CLASSIFIER_DIR / name
        if path.is_dir():
            return path
    return DEFAULT_CLASSIFIER_DIR / backend


def _resolve_predictions_path(backend: str, explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.is_file():
            sys.exit(f"Classifier predictions not found: {explicit}")
        return explicit
    stem = {
        "random_forest": "leukemia_random_forest_predictions",
        "xgboost": "leukemia_xgboost_predictions",
        "lightgbm": "leukemia_lightgbm_predictions",
    }.get(backend, f"leukemia_{backend}_predictions")
    clf_dir = _classifier_dir(backend)
    candidates = [
        clf_dir / f"{stem}.json",
        DEFAULT_CLASSIFIER_DIR / f"{stem}.json",
        clf_dir / "leukemia_classifier_predictions.json",
        _classifier_dir("random_forest") / "leukemia_classifier_predictions.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    sys.exit(
        f"No predictions JSON for backend={backend}. Train first with "
        f"train_leukemia_from_stats.py --backend {backend}"
    )


def _stats_to_summary(
    patient_id: str,
    rec: dict[str, Any],
    prediction: dict[str, Any] | None,
) -> dict[str, Any]:
    report_ready = rec.get("report_ready") or {}
    pct_clinical = rec.get("cell_percentages_clinical") or {}
    differential = {
        _display_cell(k): round(float(v), 1) for k, v in pct_clinical.items() if k != "none"
    }
    counts = {
        _display_cell(k): int(v) for k, v in (rec.get("cell_counts") or {}).items() if k != "none"
    }
    n_inf = int(rec.get("n_cells_identified_wbc") or sum(counts.values()) or 0)
    n_all = int(rec.get("n_cells_total") or n_inf)
    n_art = max(0, n_all - n_inf)
    blast_n = sum(counts.get(c, 0) for c in BLAST_CLASSES)
    blast_pct = float(report_ready.get("blast_pool_percentage_of_wbc") or 0.0)
    if blast_pct <= 0 and n_inf:
        blast_pct = round(100.0 * blast_n / n_inf, 1)

    predicted = (prediction or {}).get("predicted_class")
    summary: dict[str, Any] = {
        "patient_id": str(patient_id),
        "ground_truth_label": rec.get("metadata_filename_diagnosis"),
        "disease_label_file": predicted or rec.get("metadata_filename_diagnosis", "UNKNOWN"),
        "source": "patient_WBC_stats",
        "n_images": int(rec.get("n_images") or 0),
        "n_cells_total": n_all,
        "n_cells_informative": n_inf,
        "n_cells_artifact": n_art,
        "class_counts": counts,
        "differential_pct": differential,
        "blast_pct": blast_pct,
        "flags": {
            "blasts_present": blast_n > 0,
            "blast_threshold_met": blast_pct >= 20.0,
        },
        "morphology_cohort": {},
        "qc": (report_ready.get("qc") or {}),
    }
    if prediction:
        summary["classifier"] = {
            "backend_prediction": prediction.get("predicted_class"),
            "confidence": prediction.get("confidence"),
            "class_probabilities": prediction.get("class_probabilities"),
            "top_features": prediction.get("top_features", []),
        }
    return summary


def _append_classifier_section(markdown: str, summary: dict[str, Any]) -> str:
    clf = summary.get("classifier")
    if not clf:
        return markdown
    lines = [
        markdown.rstrip(),
        "",
        "## Classifier Prediction",
        "",
        f"- **Predicted class:** {clf.get('backend_prediction', 'UNKNOWN')}",
        f"- **Confidence:** {float(clf.get('confidence') or 0.0):.3f}",
        f"- **Ground truth (file label):** {summary.get('ground_truth_label', 'UNKNOWN')}",
        "",
        "### Top contributing features (SHAP)",
        "",
    ]
    top = clf.get("top_features") or []
    if not top:
        lines.append("_No SHAP attributions available._")
    else:
        for item in top[:5]:
            label = item.get("label") or item.get("feature", "")
            direction = item.get("direction", "supports")
            shap_val = item.get("shap_value", 0.0)
            lines.append(f"- {label} ({direction}, SHAP={shap_val:+.4f})")
    return "\n".join(lines) + "\n"


def _group_test_images(image_dir: Path) -> dict[str, list[str]]:
    suffixes = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    by_patient: dict[str, list[str]] = {}
    for path in sorted(image_dir.iterdir()):
        if path.suffix.lower() not in suffixes:
            continue
        pid = path.stem.split("_")[0]
        by_patient.setdefault(pid, []).append(str(path))
    return by_patient


def _run_detection_for_patients(
    patient_ids: list[str],
    *,
    image_dir: Path,
    out_dir: Path,
    args: argparse.Namespace,
) -> None:
    images_by_patient = _group_test_images(image_dir)
    det_out = out_dir / "detection"
    det_out.mkdir(parents=True, exist_ok=True)
    for pid in patient_ids:
        image_paths = images_by_patient.get(pid, [])
        if not image_paths:
            print(f"WARNING: no images for patient {pid} under {image_dir}", file=sys.stderr)
            continue
        cmd = [
            sys.executable,
            str(HERE / "run_orchestrator.py"),
            "--case-id",
            pid,
            "--backend",
            "wbc-unified",
            "--images",
            *image_paths,
            "--yolo-weights",
            str(args.yolo_weights),
            "--effnet-weights",
            str(args.effnet_weights),
            "--classifier-model",
            str(args.classifier_model),
            "--report-backend",
            args.report_backend,
            "--instruction",
            args.instruction,
            "--no-agent",
            "--out",
            str(det_out / pid),
        ]
        if args.device:
            cmd.extend(["--device", args.device])
        print(f"Running detection pipeline for patient {pid} ({len(image_paths)} images)...")
        result = subprocess.run(cmd, cwd=str(HERE))
        if result.returncode != 0:
            print(f"WARNING: run_orchestrator failed for patient {pid}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate LLD reports from stats + classifier outputs.")
    ap.add_argument("--stats-json", type=Path, default=DEFAULT_STATS_JSON)
    ap.add_argument("--predictions-json", type=Path, default=None)
    ap.add_argument(
        "--backend",
        choices=("random_forest", "xgboost", "lightgbm"),
        default="random_forest",
    )
    ap.add_argument("--split", choices=("test", "train", "all"), default="test")
    ap.add_argument("--split-json", type=Path, default=None)
    ap.add_argument("--cv-root", type=Path, default=WBC_CV)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--run-detection", action="store_true",
                    help="Also run YOLO+EfficientNet+classifier via run_orchestrator (GPU).")
    ap.add_argument("--image-dir", type=Path,
                    default=WBC_CV / "generated" / "det_dataset" / "images" / "test")
    ap.add_argument("--yolo-weights", type=Path, default=WBC_CV / "runs" / "detector" / "train" / "weights" / "best.pt")
    ap.add_argument("--effnet-weights", type=Path, default=WBC_CV / "runs" / "attribute" / "train" / "best_attr.pt")
    ap.add_argument("--classifier-model", type=Path,
                    default=DEFAULT_CLASSIFIER_DIR / "random_forest" / "leukemia_random_forest.pkl")
    ap.add_argument("--report-backend", choices=("template", "local-llm"), default="template")
    ap.add_argument("--device", default="0")
    ap.add_argument("--instruction", default="diagnose this case")
    args = ap.parse_args()

    if not args.stats_json.is_file():
        sys.exit(f"Stats JSON not found: {args.stats_json}")

    from agentic_hematology.leukemia_features import load_or_create_split, load_patient_stats
    from agentic_hematology.report_generator import TemplateReportGenerator

    stats = load_patient_stats(args.stats_json)
    split = load_or_create_split(stats, split_path=args.split_json, cv_root=args.cv_root)
    if args.split == "test":
        patient_ids = [pid for pid in split.get("test", []) if pid in stats]
    elif args.split == "train":
        patient_ids = [pid for pid in split.get("train", []) if pid in stats]
    else:
        patient_ids = sorted(stats.keys(), key=lambda x: (not str(x).isdigit(), int(x) if str(x).isdigit() else x))

    if not patient_ids:
        sys.exit(f"No patients found for split={args.split}")

    predictions_path = _resolve_predictions_path(args.backend, args.predictions_json)
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))

    if args.run_detection:
        if not args.yolo_weights.is_file():
            sys.exit(f"YOLO weights not found: {args.yolo_weights}")
        if not args.effnet_weights.is_file():
            sys.exit(
                f"EfficientNet weights not found: {args.effnet_weights}\n"
                "Train attributes first, or omit --run-detection to generate reports from stats JSON only."
            )
        _run_detection_for_patients(
            patient_ids,
            image_dir=args.image_dir,
            out_dir=args.out_dir,
            args=args,
        )

    out_root = args.out_dir / args.backend / args.split
    summaries_dir = out_root / "summaries"
    reports_dir = out_root / "reports"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_gen = TemplateReportGenerator()
    written_reports: list[Path] = []

    print(f"Patients ({args.split}): {len(patient_ids)}")
    print(f"Predictions: {predictions_path}")
    print(f"Output: {out_root}")

    for pid in patient_ids:
        pred = predictions.get(pid)
        if pred is None:
            print(f"WARNING: no classifier prediction for patient {pid}; using ground-truth label only",
                  file=sys.stderr)
        summary = _stats_to_summary(pid, stats[pid], pred)
        summary_path = summaries_dir / f"patient_{pid}.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        from agentic_hematology.schemas import AggregatedFindings, LeukemiaClassification

        report_ready = dict(summary)
        report_ready["patient_id"] = pid
        findings = AggregatedFindings(
            case_id=str(pid),
            n_images=summary["n_images"],
            n_cells_total=summary["n_cells_total"],
            n_cells_identified_wbc=summary["n_cells_informative"],
            cell_counts={k: v for k, v in summary["class_counts"].items()},
            cell_percentages_all=summary["differential_pct"],
            cell_percentages_clinical=summary["differential_pct"],
            attributes={},
            report_ready=report_ready,
            grounding_index={},
        )
        classification = None
        if pred:
            classification = LeukemiaClassification(
                predicted_class=str(pred.get("predicted_class", "")),
                confidence=float(pred.get("confidence") or 0.0),
                rationale="learned classifier (stats features, train-split model)",
                scores={str(k): float(v) for k, v in (pred.get("class_probabilities") or {}).items()},
            )
        report = report_gen.generate(findings, classification, instruction=args.instruction)
        report.markdown = _append_classifier_section(report.markdown, summary)
        report_path = reports_dir / f"case_{pid}_report.md"
        report_path.write_text(report.markdown, encoding="utf-8")
        written_reports.append(report_path)
        gt = summary.get("ground_truth_label")
        pred_cls = (pred or {}).get("predicted_class", "?")
        ok = "OK" if gt == pred_cls else "MISMATCH"
        print(f"  patient {pid}: gt={gt} pred={pred_cls} [{ok}] -> {report_path.name}")

    manifest = {
        "split": args.split,
        "backend": args.backend,
        "n_patients": len(patient_ids),
        "patient_ids": patient_ids,
        "predictions_json": str(predictions_path),
        "stats_json": str(args.stats_json),
        "summaries_dir": str(summaries_dir),
        "reports_dir": str(reports_dir),
        "reports": [str(p) for p in written_reports],
    }
    manifest_path = out_root / "report_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {len(written_reports)} reports to {reports_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
