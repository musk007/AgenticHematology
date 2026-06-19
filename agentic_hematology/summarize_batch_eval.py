#!/usr/bin/env python3
"""Summarize batch orchestrator outputs: detection, classification, report quality.

Reads per-patient artifacts under an output directory (default: outputs/batch_traced):
  case_<id>_detections.json, case_<id>_classification.json,
  case_<id>_report.md, case_<id>_agent_trace.json

Ground truth for detection differentials and diagnosis labels comes from
patient_WBC_stats_NoOveralp.json (same source as train_leukemia_from_stats.py).

Report-vs-approved metrics (hematologist-approved reports, hallucination rate,
field-level accuracy, BERTScore/ROUGE) reuse read-only helpers from
wbc_unified/report/src/eval_report.py.

Writes:
  - evaluation_summary.json  (machine-readable)
  - evaluation_summary.md    (human-readable)
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent
WBC_UNIFIED = REPO / "wbc_unified"
DEFAULT_STATS_JSON = Path(
    "/home/roba.majzoub/AgenticHematology/data_preprocessing/patient_WBC_stats_NoOveralp.json"
)
DEFAULT_OUTPUT_DIR = REPO / "outputs" / "batch_traced"
DEFAULT_APPROVED_REPORTS_DIR = Path(
    "/nfs-stor/roba.majzoub/LeukemiaDataset_Organized/report"
)
DEFAULT_NON_AGENTIC_DIR = REPO / "outputs" / "batch_non_agentic"

EXCLUDED_CELL_TYPES = {"none", "unknown"}
REQUIRED_REPORT_SECTIONS = (
    "## Quantitative Cell Summary",
    "## Agentic Diagnosis",
    "## Cell Grounding",
)
BANNED_REPORT_PHRASES = ("as an ai language model", "i cannot diagnose")
REVIEW_BANNER_MARKER = "Flagged for mandatory human review"
MORPHOLOGY_PCT_TOLERANCE = 15.0

from report_validation import (  # noqa: E402
    BLAST_PCT_TOLERANCE,
    COUNT_TOLERANCE,
    PCT_TOLERANCE,
    WHITELIST_PCT,
    evaluate_numerical_hallucination as evaluate_hallucination_rate,
    extract_blast_pct_from_report,
    extract_integer_claims,
    extract_percentages,
)
DISEASE_ALIASES = {
    "all": ["lymphoblastic", "all", "acute lymphoblastic"],
    "aml": ["myeloid", "aml", "acute myeloid"],
    "cml": ["myeloid", "cml", "chronic myeloid", "chronic myelogenous"],
    "cll": ["lymphocytic", "cll", "chronic lymphocytic"],
    "apml": ["promyelocytic", "apml", "acute promyelocytic"],
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def load_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def discover_patient_ids(output_dir: Path) -> list[str]:
    ids: set[str] = set()
    if not output_dir.is_dir():
        return []
    for path in output_dir.iterdir():
        if path.is_dir() and path.name.isdigit():
            ids.add(path.name)
    for pattern in ("case_*_classification.json", "case_*_agent_trace.json"):
        for f in output_dir.glob(pattern):
            m = re.search(r"case_(.+?)_", f.name)
            if m:
                ids.add(m.group(1))
        for f in output_dir.glob(f"*/{pattern}"):
            m = re.search(r"case_(.+?)_", f.name)
            if m:
                ids.add(m.group(1))
    return sorted(ids, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))


def patient_dir(output_dir: Path, pid: str) -> Path:
    nested = output_dir / pid
    return nested if nested.is_dir() else output_dir


def ground_truth_diagnosis(stats: dict, pid: str) -> str | None:
    rec = stats.get(str(pid))
    if not rec:
        return None
    diag = rec.get("metadata_filename_diagnosis")
    return str(diag).strip() if diag else None


def aggregate_detections(detections_payload: dict) -> dict[str, Any]:
    cells = detections_payload.get("detections") or []
    informative = [
        c for c in cells if _slug(c.get("class", "")) not in EXCLUDED_CELL_TYPES
    ]
    counts = Counter(_slug(c["class"]) for c in informative)
    total_inf = sum(counts.values())
    total_all = len(cells)
    clinical_pct = {
        name: round(100.0 * count / total_inf, 2) for name, count in counts.items()
    } if total_inf else {}
    confidences = [float(c.get("confidence", 0.0)) for c in informative]
    blast_classes = {"myeloblast", "lymphoblast", "monoblast", "abnormal_promyelocyte"}
    blast_n = sum(counts.get(n, 0) for n in blast_classes)
    blast_pct = round(100.0 * blast_n / total_inf, 2) if total_inf else 0.0
    return {
        "n_cells_total": total_all,
        "n_cells_informative": total_inf,
        "n_cells_artifact": max(0, total_all - total_inf),
        "cell_counts": dict(counts),
        "cell_percentages_clinical": clinical_pct,
        "mean_det_conf": round(statistics.mean(confidences), 4) if confidences else 0.0,
        "pct_class_none": round(100.0 * (total_all - total_inf) / max(total_all, 1), 2),
        "blast_pct": blast_pct,
    }


def differential_mae(gt_pct: dict, pred_pct: dict) -> float | None:
    keys = set(map(_slug, gt_pct)) | set(map(_slug, pred_pct))
    keys -= EXCLUDED_CELL_TYPES
    if not keys:
        return None
    errors = [abs(float(gt_pct.get(k, 0.0)) - float(pred_pct.get(k, 0.0))) for k in keys]
    return round(statistics.mean(errors), 3)


def evaluate_detection(stats: dict, pid: str, detections: dict | None) -> dict[str, Any]:
    gt = stats.get(str(pid)) or {}
    if detections is None:
        return {"status": "missing", "patient_id": pid}

    pred = aggregate_detections(detections)
    gt_counts = {_slug(k): int(v) for k, v in (gt.get("cell_counts") or {}).items()}
    gt_pct = {_slug(k): float(v) for k, v in (gt.get("cell_percentages_clinical") or {}).items()}
    pred_counts = pred["cell_counts"]
    pred_pct = pred["cell_percentages_clinical"]

    gt_inf = int(gt.get("n_cells_identified_wbc") or sum(
        v for k, v in gt_counts.items() if k not in EXCLUDED_CELL_TYPES
    ))
    pred_inf = pred["n_cells_informative"]
    count_err = pred_inf - gt_inf
    count_err_pct = round(100.0 * count_err / gt_inf, 2) if gt_inf else None

    return {
        "status": "ok",
        "patient_id": pid,
        "gt_informative_wbc": gt_inf,
        "pred_informative_wbc": pred_inf,
        "informative_wbc_count_error": count_err,
        "informative_wbc_count_error_pct": count_err_pct,
        "differential_mae_pct_points": differential_mae(gt_pct, pred_pct),
        "gt_blast_pct": round(float((gt.get("report_ready") or {}).get("blast_pct", 0.0)), 2),
        "pred_blast_pct": pred["blast_pct"],
        "blast_pct_error": round(pred["blast_pct"] - float((gt.get("report_ready") or {}).get("blast_pct", 0.0)), 2),
        "mean_det_conf": pred["mean_det_conf"],
        "pct_class_none": pred["pct_class_none"],
        "gt_top_cell_type": max(gt_pct, key=gt_pct.get) if gt_pct else None,
        "pred_top_cell_type": max(pred_pct, key=pred_pct.get) if pred_pct else None,
        "top_cell_type_match": (
            max(gt_pct, key=gt_pct.get) == max(pred_pct, key=pred_pct.get)
            if gt_pct and pred_pct
            else None
        ),
    }


def evaluate_classification(stats: dict, pid: str, clf: dict | None) -> dict[str, Any]:
    gt = ground_truth_diagnosis(stats, pid)
    if clf is None:
        return {"status": "missing", "patient_id": pid, "ground_truth": gt}
    pred = str(clf.get("predicted_class", "")).strip()
    return {
        "status": "ok",
        "patient_id": pid,
        "ground_truth": gt,
        "predicted_class": pred,
        "confidence": float(clf.get("confidence", 0.0)),
        "correct": pred == gt if gt else None,
    }


def evaluate_report_quality(
    pid: str,
    report_text: str | None,
    clf: dict | None,
    trace: dict | None,
) -> dict[str, Any]:
    base_dir_ok = report_text is not None
    if not base_dir_ok:
        return {
            "status": "missing",
            "patient_id": pid,
            "files_complete": False,
        }

    text = report_text or ""
    pred = str((clf or {}).get("predicted_class", "")).strip()
    flagged = bool((trace or {}).get("flagged_for_review"))
    consistency_ok = (not pred) or (pred in text)
    llm_output_ok = bool(text.strip()) and not any(p in text.lower() for p in BANNED_REPORT_PHRASES)
    sections_present = {s: s in text for s in REQUIRED_REPORT_SECTIONS}
    review_banner_ok = (not flagged) or (REVIEW_BANNER_MARKER in text)

    checks_passed = sum(
        [
            consistency_ok,
            llm_output_ok,
            all(sections_present.values()),
            review_banner_ok,
        ]
    )

    return {
        "status": "ok",
        "patient_id": pid,
        "files_complete": True,
        "non_empty": bool(text.strip()),
        "consistency_passed": consistency_ok,
        "llm_output_passed": llm_output_ok,
        "required_sections": sections_present,
        "review_banner_ok": review_banner_ok,
        "flagged_for_review": flagged,
        "quality_score": round(checks_passed / 4.0, 3),
        "word_count": len(text.split()),
    }


def evaluate_artifacts(output_dir: Path, pid: str) -> dict[str, bool]:
    base = patient_dir(output_dir, pid)
    names = (
        f"case_{pid}_detections.json",
        f"case_{pid}_classification.json",
        f"case_{pid}_report.md",
        f"case_{pid}_agent_trace.json",
    )
    return {name: (base / name).is_file() for name in names}


def _eval_report_helpers():
    if str(WBC_UNIFIED) not in sys.path:
        sys.path.insert(0, str(WBC_UNIFIED))
    from report.src.eval_report import eval_pair, extract_report_markdown  # noqa: WPS433

    return eval_pair, extract_report_markdown


def find_classification(output_dir: Path, pid: str) -> dict | None:
    base = patient_dir(output_dir, pid)
    return load_json(base / f"case_{pid}_classification.json")


def extract_morphology_percentages(md: str) -> list[float]:
    m = re.search(r"\*\*cohort morphology[^:]*:\*\*(.+?)(?:\n\n|\*\*)", md, re.I | re.S)
    if not m:
        return []
    return extract_percentages(m.group(1))


def impression_matches_disease(report_md: str, disease: str | None, extract_report_markdown) -> bool:
    if not disease:
        return False
    body = extract_report_markdown(report_md)
    imp = re.search(r"\*\*impression:\*\*\s*(.+)", body, re.I | re.S)
    if not imp:
        return False
    block = imp.group(1).split("\n\n")[0].lower()
    aliases = DISEASE_ALIASES.get(disease.lower(), [disease.lower()])
    return any(alias in block for alias in aliases)


def evaluate_vs_approved_report(
    pid: str,
    generated_md: str,
    approved_md: str,
    stats: dict,
    det_agg: dict[str, Any],
    clf: dict | None,
) -> dict[str, Any]:
    eval_pair, extract_report_markdown = _eval_report_helpers()
    gt_disease = ground_truth_diagnosis(stats, pid)

    pair = eval_pair(generated_md, approved_md)
    gen_blast = extract_blast_pct_from_report(generated_md)
    gt_blast = extract_blast_pct_from_report(approved_md)
    blast_err = (
        round(abs(gen_blast - gt_blast), 2)
        if gen_blast is not None and gt_blast is not None
        else None
    )

    gen_morph = extract_morphology_percentages(generated_md)
    gt_morph = extract_morphology_percentages(approved_md)
    morph_mae = None
    morph_ok = None
    if gen_morph and gt_morph:
        n = min(len(gen_morph), len(gt_morph))
        morph_mae = round(
            statistics.mean(abs(gen_morph[i] - gt_morph[i]) for i in range(n)), 2
        )
        morph_ok = morph_mae <= MORPHOLOGY_PCT_TOLERANCE

    return {
        "patient_id": pid,
        "approved_report_found": True,
        "differential_mae_pct_vs_approved": pair.get("mae_pct"),
        "differential_class_recall_vs_approved": (
            round(pair["matched_classes"] / pair["n_classes_gt"], 4)
            if pair.get("n_classes_gt")
            else None
        ),
        "blast_pct_vs_approved_error": blast_err,
        "blast_pct_vs_approved_correct": (
            blast_err is not None and blast_err <= BLAST_PCT_TOLERANCE
        ),
        "diagnosis_impression_matches_label": impression_matches_disease(
            generated_md, gt_disease, extract_report_markdown
        ),
        "morphology_pct_mae_vs_approved": morph_mae,
        "morphology_vs_approved_correct": morph_ok,
        "hallucination": evaluate_hallucination_rate(
            generated_md, det_agg, clf, approved_md=approved_md
        ),
    }


def compute_text_similarity_secondary(
    generated_reports: list[str],
    approved_reports: list[str],
    patient_ids: list[str],
    *,
    compute_bertscore: bool,
) -> dict[str, Any]:
    _, extract_report_markdown = _eval_report_helpers()
    gens = [extract_report_markdown(t) for t in generated_reports]
    refs = [extract_report_markdown(t) for t in approved_reports]

    from rouge_score import rouge_scorer

    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    rouge1, rouge2, rougeL = [], [], []
    per_case: list[dict[str, float]] = []
    for cand, ref in zip(gens, refs):
        scores = scorer.score(ref, cand)
        r1 = scores["rouge1"].fmeasure
        r2 = scores["rouge2"].fmeasure
        rl = scores["rougeL"].fmeasure
        rouge1.append(r1)
        rouge2.append(r2)
        rougeL.append(rl)
        per_case.append(
            {
                "patient_id": patient_ids[len(per_case)] if len(per_case) < len(patient_ids) else None,
                "rouge1": round(r1, 4),
                "rouge2": round(r2, 4),
                "rougeL": round(rl, 4),
            }
        )

    out: dict[str, Any] = {
        "note": "Secondary textual similarity signal only; not the primary quality claim.",
        "rouge1_mean": round(statistics.mean(rouge1), 4) if rouge1 else None,
        "rouge2_mean": round(statistics.mean(rouge2), 4) if rouge2 else None,
        "rougeL_mean": round(statistics.mean(rougeL), 4) if rougeL else None,
        "per_case": per_case,
    }

    if compute_bertscore and gens:
        try:
            import bert_score

            _, _, f1 = bert_score.score(gens, refs, lang="en", verbose=False)
            f1_vals = [float(x) for x in f1.tolist()]
            out["bertscore_f1_mean"] = round(statistics.mean(f1_vals), 4)
            out["bertscore_f1_per_case"] = [round(v, 4) for v in f1_vals]
        except Exception as exc:
            out["bertscore_error"] = str(exc)
    return out


def evaluate_agent_ablation(
    patients: list[str],
    agentic_dir: Path,
    non_agentic_dir: Path | None,
    stats: dict,
) -> dict[str, Any]:
    if non_agentic_dir is None or not non_agentic_dir.is_dir():
        return {
            "non_agentic_dir": None,
            "n_compared": 0,
            "outcome_change_rate": None,
            "classification_accuracy_agentic": None,
            "classification_accuracy_non_agentic": None,
            "per_patient": [],
            "note": "Provide --non-agentic-dir with outputs from run_orchestrator.py --no-agent.",
        }

    rows: list[dict[str, Any]] = []
    changed = 0
    ag_correct = 0
    non_correct = 0
    compared = 0

    for pid in patients:
        ag = find_classification(agentic_dir, pid)
        non_ag = find_classification(non_agentic_dir, pid)
        if not ag or not non_ag:
            continue
        gt = ground_truth_diagnosis(stats, pid)
        ag_cls = str(ag.get("predicted_class", ""))
        non_cls = str(non_ag.get("predicted_class", ""))
        outcome_changed = ag_cls != non_cls
        if outcome_changed:
            changed += 1
        compared += 1
        if gt:
            ag_correct += int(ag_cls == gt)
            non_correct += int(non_cls == gt)
        rows.append(
            {
                "patient_id": pid,
                "ground_truth": gt,
                "agentic_class": ag_cls,
                "non_agentic_class": non_cls,
                "outcome_changed": outcome_changed,
                "agentic_correct": ag_cls == gt if gt else None,
                "non_agentic_correct": non_cls == gt if gt else None,
            }
        )

    return {
        "non_agentic_dir": str(non_agentic_dir.resolve()),
        "n_compared": compared,
        "outcome_change_rate": round(changed / compared, 4) if compared else None,
        "n_outcome_changed": changed,
        "classification_accuracy_agentic": round(ag_correct / compared, 4) if compared else None,
        "classification_accuracy_non_agentic": round(non_correct / compared, 4) if compared else None,
        "per_patient": rows,
    }


def summarize_agent_traces(traces: list[dict | None]) -> dict[str, Any]:
    valid = [t for t in traces if t]
    final_actions: Counter[str] = Counter()
    flagged = 0
    re_aggregate = 0
    for trace in valid:
        if trace.get("flagged_for_review"):
            flagged += 1
        actions = trace.get("agent_actions") or []
        if any(a.get("action") == "re_aggregate" for a in actions):
            re_aggregate += 1
        if actions:
            final_actions[str(actions[-1].get("action", "?"))] += 1
    return {
        "n_with_trace": len(valid),
        "flagged_for_review": flagged,
        "re_aggregate_used": re_aggregate,
        "final_action_counts": dict(final_actions),
    }


def build_summary(
    output_dir: Path,
    stats_path: Path,
    *,
    approved_reports_dir: Path | None,
    non_agentic_dir: Path | None,
    compute_bertscore: bool,
) -> dict[str, Any]:
    stats = load_json(stats_path) or {}
    if not isinstance(stats, dict):
        sys.exit(f"Expected dict in stats JSON: {stats_path}")

    patients = discover_patient_ids(output_dir)
    if not patients:
        sys.exit(f"No patient outputs found under {output_dir}")

    detection_rows: list[dict] = []
    classification_rows: list[dict] = []
    report_rows: list[dict] = []
    approved_rows: list[dict] = []
    traces: list[dict | None] = []
    artifact_rows: list[dict] = []
    generated_for_similarity: list[str] = []
    approved_for_similarity: list[str] = []
    similarity_patient_ids: list[str] = []

    for pid in patients:
        base = patient_dir(output_dir, pid)
        artifacts = evaluate_artifacts(output_dir, pid)
        artifact_rows.append({"patient_id": pid, **artifacts})

        det = load_json(base / f"case_{pid}_detections.json")
        clf = load_json(base / f"case_{pid}_classification.json")
        trace = load_json(base / f"case_{pid}_agent_trace.json")
        report_path = base / f"case_{pid}_report.md"
        report_text = report_path.read_text(encoding="utf-8") if report_path.is_file() else None

        detection_rows.append(evaluate_detection(stats, pid, det if isinstance(det, dict) else None))
        classification_rows.append(evaluate_classification(stats, pid, clf if isinstance(clf, dict) else None))
        report_rows.append(
            evaluate_report_quality(pid, report_text, clf if isinstance(clf, dict) else None, trace)
        )
        traces.append(trace if isinstance(trace, dict) else None)

        if report_text and isinstance(det, dict):
            approved_path = (
                approved_reports_dir / f"case_{pid}_report.md"
                if approved_reports_dir
                else None
            )
            if approved_path and approved_path.is_file():
                approved_md = approved_path.read_text(encoding="utf-8")
                det_agg = aggregate_detections(det)
                row = evaluate_vs_approved_report(
                    pid,
                    report_text,
                    approved_md,
                    stats,
                    det_agg,
                    clf if isinstance(clf, dict) else None,
                )
                approved_rows.append(row)
                generated_for_similarity.append(report_text)
                approved_for_similarity.append(approved_md)
                similarity_patient_ids.append(pid)
            else:
                det_agg = aggregate_detections(det)
                approved_rows.append(
                    {
                        "patient_id": pid,
                        "approved_report_found": False,
                        "hallucination": evaluate_hallucination_rate(
                            report_text,
                            det_agg,
                            clf if isinstance(clf, dict) else None,
                            approved_md=None,
                        ),
                    }
                )

    det_ok = [r for r in detection_rows if r.get("status") == "ok"]
    clf_ok = [r for r in classification_rows if r.get("status") == "ok" and r.get("correct") is not None]
    rpt_ok = [r for r in report_rows if r.get("status") == "ok"]

    clf_correct = sum(1 for r in clf_ok if r["correct"])
    clf_accuracy = round(clf_correct / len(clf_ok), 4) if clf_ok else None

    mae_values = [r["differential_mae_pct_points"] for r in det_ok if r.get("differential_mae_pct_points") is not None]
    count_err_pct = [r["informative_wbc_count_error_pct"] for r in det_ok if r.get("informative_wbc_count_error_pct") is not None]
    top_match = [r for r in det_ok if r.get("top_cell_type_match") is True]

    per_class: Counter[str] = Counter()
    per_class_correct: Counter[str] = Counter()
    for r in clf_ok:
        gt = r["ground_truth"] or "?"
        per_class[gt] += 1
        if r["correct"]:
            per_class_correct[gt] += 1

    approved_ok = [r for r in approved_rows if r.get("approved_report_found")]
    halluc_rows = [r["hallucination"] for r in approved_rows if r.get("hallucination")]
    total_claims = sum(int(h.get("n_claims", 0)) for h in halluc_rows)
    total_untraceable = sum(int(h.get("n_untraceable", 0)) for h in halluc_rows)

    field_summary = {
        "differential_mae_pct_vs_approved_mean": round(
            statistics.mean(
                r["differential_mae_pct_vs_approved"]
                for r in approved_ok
                if r.get("differential_mae_pct_vs_approved") is not None
            ),
            2,
        )
        if approved_ok
        else None,
        "differential_class_recall_vs_approved_mean": round(
            statistics.mean(
                r["differential_class_recall_vs_approved"]
                for r in approved_ok
                if r.get("differential_class_recall_vs_approved") is not None
            ),
            4,
        )
        if approved_ok
        else None,
        "blast_pct_vs_approved_correct_rate": round(
            sum(1 for r in approved_ok if r.get("blast_pct_vs_approved_correct")) / len(approved_ok),
            4,
        )
        if approved_ok
        else None,
        "diagnosis_impression_match_rate": round(
            sum(1 for r in approved_ok if r.get("diagnosis_impression_matches_label")) / len(approved_ok),
            4,
        )
        if approved_ok
        else None,
        "morphology_vs_approved_correct_rate": round(
            sum(1 for r in approved_ok if r.get("morphology_vs_approved_correct") is True)
            / max(1, sum(1 for r in approved_ok if r.get("morphology_vs_approved_correct") is not None)),
            4,
        )
        if any(r.get("morphology_vs_approved_correct") is not None for r in approved_ok)
        else None,
    }

    text_similarity = (
        compute_text_similarity_secondary(
            generated_for_similarity,
            approved_for_similarity,
            similarity_patient_ids,
            compute_bertscore=compute_bertscore,
        )
        if generated_for_similarity
        else {"note": "No approved report pairs found for ROUGE/BERTScore."}
    )

    agent_ablation = evaluate_agent_ablation(patients, output_dir, non_agentic_dir, stats)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir.resolve()),
        "stats_json": str(stats_path.resolve()),
        "approved_reports_dir": str(approved_reports_dir.resolve()) if approved_reports_dir else None,
        "n_patients": len(patients),
        "patient_ids": patients,
        "artifacts": {
            "all_four_files_present": sum(
                1
                for row in artifact_rows
                if all(
                    row.get(key, False)
                    for key in row
                    if key != "patient_id"
                )
            ),
            "per_patient": artifact_rows,
        },
        "detection": {
            "n_evaluated": len(det_ok),
            "mean_differential_mae_pct_points": round(statistics.mean(mae_values), 3) if mae_values else None,
            "median_differential_mae_pct_points": round(statistics.median(mae_values), 3) if mae_values else None,
            "mean_informative_wbc_count_error_pct": round(statistics.mean(count_err_pct), 2) if count_err_pct else None,
            "top_dominant_cell_type_match_rate": round(len(top_match) / len(det_ok), 4) if det_ok else None,
            "mean_detection_confidence": round(
                statistics.mean(r["mean_det_conf"] for r in det_ok), 4
            ) if det_ok else None,
            "mean_artifact_rate_pct": round(
                statistics.mean(r["pct_class_none"] for r in det_ok), 2
            ) if det_ok else None,
            "per_patient": detection_rows,
        },
        "classification": {
            "n_evaluated": len(clf_ok),
            "accuracy": clf_accuracy,
            "n_correct": clf_correct,
            "per_class_accuracy": {
                cls: round(per_class_correct[cls] / per_class[cls], 4) for cls in sorted(per_class)
            },
            "per_patient": classification_rows,
        },
        "report_quality": {
            "n_evaluated": len(rpt_ok),
            "mean_quality_score": round(statistics.mean(r["quality_score"] for r in rpt_ok), 3) if rpt_ok else None,
            "consistency_pass_rate": round(
                sum(1 for r in rpt_ok if r["consistency_passed"]) / len(rpt_ok), 4
            ) if rpt_ok else None,
            "llm_output_pass_rate": round(
                sum(1 for r in rpt_ok if r["llm_output_passed"]) / len(rpt_ok), 4
            ) if rpt_ok else None,
            "all_required_sections_rate": round(
                sum(1 for r in rpt_ok if all(r["required_sections"].values())) / len(rpt_ok), 4
            ) if rpt_ok else None,
            "review_banner_pass_rate": round(
                sum(1 for r in rpt_ok if r["review_banner_ok"]) / len(rpt_ok), 4
            ) if rpt_ok else None,
            "per_patient": report_rows,
        },
        "report_vs_approved": {
            "n_evaluated_with_approved_report": len(approved_ok),
            "field_level_accuracy": field_summary,
            "hallucination": {
                "mean_hallucination_rate": round(total_untraceable / total_claims, 4) if total_claims else None,
                "n_total_claims": total_claims,
                "n_untraceable_claims": total_untraceable,
                "definition": (
                    "Fraction of numeric claims in the generated report body that are not "
                    "traceable (within tolerance) to either pipeline JSON evidence or the "
                    "hematologist-approved report."
                ),
            },
            "text_similarity_secondary": text_similarity,
            "per_patient": approved_rows,
        },
        "agent_ablation": agent_ablation,
        "agent_trace": summarize_agent_traces(traces),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    det = summary["detection"]
    clf = summary["classification"]
    rpt = summary["report_quality"]
    agent = summary["agent_trace"]
    vs_approved = summary.get("report_vs_approved") or {}
    field = vs_approved.get("field_level_accuracy") or {}
    halluc = vs_approved.get("hallucination") or {}
    text_sim = vs_approved.get("text_similarity_secondary") or {}
    ablation = summary.get("agent_ablation") or {}
    lines = [
        "# Batch evaluation summary",
        "",
        f"- **Output directory:** `{summary['output_dir']}`",
        f"- **Ground truth (stats):** `{summary['stats_json']}`",
        f"- **Approved reports:** `{summary.get('approved_reports_dir', 'n/a')}`",
        f"- **Patients:** {summary['n_patients']} ({', '.join(summary['patient_ids'])})",
        f"- **Generated:** {summary['generated_at']}",
        "",
        "## Overall metrics",
        "",
        "| Area | Metric | Value |",
        "|------|--------|------:|",
        f"| Detection | Mean differential MAE (pp) vs stats GT | {det.get('mean_differential_mae_pct_points', 'n/a')} |",
        f"| Detection | Mean informative WBC count error (%) | {det.get('mean_informative_wbc_count_error_pct', 'n/a')} |",
        f"| Classification | Accuracy vs diagnosis label | {clf.get('accuracy', 'n/a')} ({clf.get('n_correct', 0)}/{clf.get('n_evaluated', 0)}) |",
        f"| Report vs approved | Differential MAE (pp) | {field.get('differential_mae_pct_vs_approved_mean', 'n/a')} |",
        f"| Report vs approved | Differential class recall | {field.get('differential_class_recall_vs_approved_mean', 'n/a')} |",
        f"| Report vs approved | Blast % correct (≤{BLAST_PCT_TOLERANCE} pp) | {field.get('blast_pct_vs_approved_correct_rate', 'n/a')} |",
        f"| Report vs approved | Diagnosis impression match rate | {field.get('diagnosis_impression_match_rate', 'n/a')} |",
        f"| Report vs approved | Morphology match rate | {field.get('morphology_vs_approved_correct_rate', 'n/a')} |",
        f"| Report vs approved | **Hallucination rate** | {halluc.get('mean_hallucination_rate', 'n/a')} |",
        f"| Text similarity (secondary) | ROUGE-L | {text_sim.get('rougeL_mean', 'n/a')} |",
        f"| Text similarity (secondary) | BERTScore F1 | {text_sim.get('bertscore_f1_mean', text_sim.get('bertscore_error', 'n/a'))} |",
        f"| Agent ablation | Outcome change rate (vs --no-agent) | {ablation.get('outcome_change_rate', 'n/a')} |",
        f"| Agent | Flagged for review | {agent.get('flagged_for_review', 0)}/{agent.get('n_with_trace', 0)} |",
        f"| Report structure | Mean structural quality score (0–1) | {rpt.get('mean_quality_score', 'n/a')} |",
        "",
        "## Report vs hematologist-approved (field-level)",
        "",
        "Primary report-quality signals. Hallucination = numeric claims in the generated report "
        "not traceable to pipeline JSON **or** the approved reference report (within tolerance).",
        "",
        "| Field | Cohort mean / rate |",
        "|-------|-------------------:|",
        f"| Differential table MAE (pp) | {field.get('differential_mae_pct_vs_approved_mean', 'n/a')} |",
        f"| Differential class recall | {field.get('differential_class_recall_vs_approved_mean', 'n/a')} |",
        f"| Blast % within {BLAST_PCT_TOLERANCE} pp | {field.get('blast_pct_vs_approved_correct_rate', 'n/a')} |",
        f"| Diagnosis impression matches label | {field.get('diagnosis_impression_match_rate', 'n/a')} |",
        f"| Morphology cohort (when present) | {field.get('morphology_vs_approved_correct_rate', 'n/a')} |",
        f"| Hallucination rate | {halluc.get('mean_hallucination_rate', 'n/a')} ({halluc.get('n_untraceable_claims', 0)}/{halluc.get('n_total_claims', 0)} claims) |",
        "",
        "## Text similarity (secondary only)",
        "",
        text_sim.get("note", ""),
        "",
        f"- ROUGE-1: {text_sim.get('rouge1_mean', 'n/a')}",
        f"- ROUGE-2: {text_sim.get('rouge2_mean', 'n/a')}",
        f"- ROUGE-L: {text_sim.get('rougeL_mean', 'n/a')}",
        f"- BERTScore F1: {text_sim.get('bertscore_f1_mean', text_sim.get('bertscore_error', 'n/a'))}",
        "",
        "## Agent ablation (--no-agent)",
        "",
        f"- Non-agentic dir: `{ablation.get('non_agentic_dir', 'not provided')}`",
        f"- Compared patients: {ablation.get('n_compared', 0)}",
        f"- Outcome change rate: {ablation.get('outcome_change_rate', 'n/a')} ({ablation.get('n_outcome_changed', 0)} changed)",
        f"- Accuracy agentic / non-agentic: {ablation.get('classification_accuracy_agentic', 'n/a')} / {ablation.get('classification_accuracy_non_agentic', 'n/a')}",
        "",
        "## Classification by ground-truth class",
        "",
        "| Class | Correct / Total | Accuracy |",
        "|-------|----------------:|---------:|",
    ]
    for cls, acc in sorted((clf.get("per_class_accuracy") or {}).items()):
        total = sum(1 for r in clf["per_patient"] if r.get("ground_truth") == cls)
        correct = sum(1 for r in clf["per_patient"] if r.get("ground_truth") == cls and r.get("correct"))
        lines.append(f"| {cls} | {correct}/{total} | {acc} |")

    lines.extend(["", "## Per-patient table", ""])
    lines.append(
        "| Patient | Clf | GT | Pred | Halluc% | Diff MAE† | Flagged | ROUGE-L |"
    )
    lines.append("|---------|:---:|----|------|--------:|----------:|:-------:|--------:|")
    clf_by_id = {r["patient_id"]: r for r in clf["per_patient"]}
    rpt_by_id = {r["patient_id"]: r for r in rpt["per_patient"]}
    appr_by_id = {r["patient_id"]: r for r in vs_approved.get("per_patient", [])}
    rouge_by_pid = {
        str(row.get("patient_id")): row.get("rougeL")
        for row in (text_sim.get("per_case") or [])
        if row.get("patient_id") is not None
    }
    for pid in summary["patient_ids"]:
        c = clf_by_id.get(pid, {})
        r = rpt_by_id.get(pid, {})
        a = appr_by_id.get(pid, {})
        h = a.get("hallucination") or {}
        flagged = "yes" if r.get("flagged_for_review") else "no" if r.get("status") == "ok" else "-"
        ok = "✓" if c.get("correct") else ("✗" if c.get("correct") is False else "?")
        rouge_l = rouge_by_pid.get(pid, "-")
        lines.append(
            f"| {pid} | {ok} | {c.get('ground_truth', '?')} | {c.get('predicted_class', '-')} | "
            f"{h.get('hallucination_rate', '-')} | {a.get('differential_mae_pct_vs_approved', '-')} | "
            f"{flagged} | {rouge_l} |"
        )

    lines.extend(["", "## Notes", ""])
    lines.extend([
        "- **Detection GT** comes from `patient_WBC_stats_NoOveralp.json`.",
        "- **† Diff MAE** in the per-patient table is vs hematologist-approved report tables.",
        "- **Hallucination rate** counts untraceable numeric claims in the report body (excluding the 20% blast threshold boilerplate).",
        "- **ROUGE/BERTScore** are secondary textual similarity signals vs approved reports.",
        "- **Agent ablation**: run `run_orchestrator.py --no-agent --out outputs/batch_non_agentic` then pass `--non-agentic-dir`.",
        "- Re-run: `python summarize_batch_eval.py --output-dir outputs/batch_traced`",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Summarize batch detection, classification, and report quality.")
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory with per-patient case_* outputs (default: outputs/batch_traced).",
    )
    ap.add_argument("--stats-json", type=Path, default=DEFAULT_STATS_JSON)
    ap.add_argument(
        "--approved-reports-dir",
        type=Path,
        default=DEFAULT_APPROVED_REPORTS_DIR,
        help="Hematologist-approved reference reports (case_<id>_report.md).",
    )
    ap.add_argument(
        "--non-agentic-dir",
        type=Path,
        default=None,
        help="Batch outputs from run_orchestrator.py --no-agent for ablation comparison.",
    )
    ap.add_argument(
        "--skip-bertscore",
        action="store_true",
        help="Skip BERTScore (ROUGE still computed; faster on CPU).",
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="JSON summary path (default: <output-dir>/evaluation_summary.json).",
    )
    ap.add_argument(
        "--out-md",
        type=Path,
        default=None,
        help="Markdown summary path (default: <output-dir>/evaluation_summary.md).",
    )
    args = ap.parse_args()

    approved_dir = args.approved_reports_dir if args.approved_reports_dir.is_dir() else None
    if args.approved_reports_dir and not approved_dir:
        print(f"WARNING: approved reports dir not found: {args.approved_reports_dir}", file=sys.stderr)

    summary = build_summary(
        args.output_dir,
        args.stats_json,
        approved_reports_dir=approved_dir,
        non_agentic_dir=args.non_agentic_dir,
        compute_bertscore=not args.skip_bertscore,
    )
    out_json = args.out_json or (args.output_dir / "evaluation_summary.json")
    out_md = args.out_md or (args.output_dir / "evaluation_summary.md")

    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    out_md.write_text(render_markdown(summary), encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print()
    print(f"Patients: {summary['n_patients']}")
    print(f"Classification accuracy: {summary['classification']['accuracy']}")
    print(f"Detection mean differential MAE (pp): {summary['detection']['mean_differential_mae_pct_points']}")
    rv = summary.get("report_vs_approved") or {}
    print(f"Hallucination rate: {(rv.get('hallucination') or {}).get('mean_hallucination_rate')}")
    print(f"ROUGE-L (secondary): {(rv.get('text_similarity_secondary') or {}).get('rougeL_mean')}")
    print(f"Agent outcome change rate: {(summary.get('agent_ablation') or {}).get('outcome_change_rate')}")
    print(f"Flagged for review: {summary['agent_trace']['flagged_for_review']}/{summary['agent_trace']['n_with_trace']}")


if __name__ == "__main__":
    main()
