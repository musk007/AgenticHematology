#!/usr/bin/env python3
"""Evaluate AgenticHematology outputs against LLD labels and reference reports.

The script evaluates what is available from orchestrator outputs:

* Detection: AP/mAP and per-class precision/recall/F1 after global-canvas
  deduplication.
* Attributes: per-attribute accuracy/F1/AUC/balanced accuracy on matched cells.
* Patient classification: macro-F1, confusion matrix, APML recall, kappa,
  optional macro-AUC, bootstrap CIs.
* Reports: surface metrics when optional packages are installed, structured
  clinical accuracy, numeric hallucination checks, and grounding validity.

LLM-as-judge and expert review are represented as explicit placeholders because
they require external services/experts.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

try:
    from sklearn.metrics import (
        average_precision_score,
        balanced_accuracy_score,
        cohen_kappa_score,
        confusion_matrix,
        f1_score,
        precision_recall_fscore_support,
        roc_auc_score,
    )
except Exception as e:  # pragma: no cover - runtime dependency check
    raise SystemExit(
        "scikit-learn is required for this evaluator. Install it in the active env."
    ) from e


ATTR_NAMES = [
    "Nuclear_Chromatin",
    "Nuclear_Shape",
    "Nucleus",
    "Cytoplasm",
    "Cytoplasmic_Basophilia",
    "Cytoplasmic_Vacuoles",
]

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

DIAGNOSES = ["ALL", "AML", "APML", "CLL", "CML", "Indeterminate"]
DEFAULT_IMAGE_WH = (640, 640)
OVERLAP_PERCENTAGE = 0.20
GLOBAL_STRIDE_PX = int(DEFAULT_IMAGE_WH[0] * (1.0 - OVERLAP_PERCENTAGE))
CANVAS_IOU_THRESHOLD = 0.2

# BERTScore uses a domain model so semantic similarity reflects clinical
# language rather than general English. Medical BERT checkpoints often ship
# without a defined tokenizer ``model_max_length`` (it defaults to a huge
# sentinel int), which makes ``bert-score`` raise ``OverflowError`` during
# truncation; we pin it explicitly when building the scorer.
BERTSCORE_MODEL = "emilyalsentzer/Bio_ClinicalBERT"
BERTSCORE_NUM_LAYERS = 12
BERTSCORE_MAX_LENGTH = 512
_BERT_SCORER = None


def parse_image_name(path_or_name: str) -> tuple[str, int, int, str]:
    stem = Path(path_or_name).stem
    parts = stem.split("_")
    if len(parts) < 5:
        raise ValueError(f"Unexpected LLD image name: {path_or_name}")
    pid = parts[0]
    gx = int("".join(filter(str.isdigit, parts[1])) or 0)
    gy = int("".join(filter(str.isdigit, parts[2])) or 0)
    label = parts[-1]
    return pid, gx, gy, label


def xywhn_to_xyxy(row: list[float], image_wh: tuple[int, int] = DEFAULT_IMAGE_WH) -> list[float]:
    _, cx, cy, w, h = row[:5]
    iw, ih = image_wh
    return [
        (cx - w / 2.0) * iw,
        (cy - h / 2.0) * ih,
        (cx + w / 2.0) * iw,
        (cy + h / 2.0) * ih,
    ]


def to_global_box(image_id: str, bbox_xyxy: list[float]) -> list[float]:
    _, gx, gy, _ = parse_image_name(image_id)
    dx = gx * GLOBAL_STRIDE_PX
    dy = gy * GLOBAL_STRIDE_PX
    x1, y1, x2, y2 = bbox_xyxy
    return [x1 + dx, y1 + dy, x2 + dx, y2 + dy]


def box_iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    aa = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    ba = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    den = aa + ba - inter
    return inter / den if den > 0 else 0.0


def dedup_canvas(records: list[dict[str, Any]], iou_threshold: float = CANVAS_IOU_THRESHOLD) -> list[dict[str, Any]]:
    """Class-agnostic global-canvas NMS used for both GT and predictions."""
    items = []
    for rec in records:
        gbox = rec.get("global_bbox_xyxy") or to_global_box(rec["image_id"], rec["bbox_xyxy"])
        score = float(rec.get("confidence", 1.0))
        area = max(0.0, gbox[2] - gbox[0]) * max(0.0, gbox[3] - gbox[1])
        items.append((score, area, gbox, rec))
    items.sort(key=lambda x: (x[0], x[1]), reverse=True)
    kept: list[tuple[float, float, list[float], dict[str, Any]]] = []
    while items:
        cur = items.pop(0)
        kept.append(cur)
        items = [x for x in items if box_iou(cur[2], x[2]) < iou_threshold]
    return [x[3] for x in kept]


def load_predictions(outputs_dir: Path) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for path in sorted(outputs_dir.rglob("case_*_detections.json")):
        data = json.loads(path.read_text())
        pid = str(data.get("patient_id") or path.stem.replace("case_", "").replace("_detections", ""))
        cases.setdefault(pid, {})["detections"] = data
    for path in sorted(outputs_dir.rglob("case_*_classification.json")):
        data = json.loads(path.read_text())
        pid = str(data.get("patient_id") or path.stem.replace("case_", "").replace("_classification", ""))
        cases.setdefault(pid, {})["classification"] = data
    for path in sorted(outputs_dir.rglob("case_*_report.md")):
        pid = path.stem.replace("case_", "").replace("_report", "")
        cases.setdefault(pid, {})["report_path"] = str(path)
        cases[pid]["report_text"] = path.read_text(encoding="utf-8", errors="ignore")
    # breakpoint()
    return cases


def load_gt_labels(label_root: Path) -> dict[str, dict[str, Any]]:
    """Load 12-col AttriDet labels from a root containing train/test labels."""
    out: dict[str, dict[str, Any]] = defaultdict(lambda: {"detections": [], "label": None, "n_images": set()})
    label_files = sorted(label_root.rglob("*.txt"))
    for path in label_files:
        try:
            pid, _, _, dx = parse_image_name(path.name)
        except ValueError:
            continue
        rec = out[pid]
        rec["label"] = rec["label"] or dx
        rec["n_images"].add(path.stem)
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) < 11:
                continue
            try:
                vals = [float(x) for x in parts[:11]]
            except ValueError:
                continue
            cls_id = int(vals[0])
            attrs = {}
            for idx, attr in enumerate(ATTR_NAMES):
                v = int(vals[5 + idx])
                if v in {0, 1}:
                    attrs[attr] = v
            bbox = xywhn_to_xyxy(vals)
            rec["detections"].append(
                {
                    "image_id": path.with_suffix(".png").name,
                    "bbox_xyxy": bbox,
                    "global_bbox_xyxy": to_global_box(path.name, bbox),
                    "class_id": cls_id,
                    "class": CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else str(cls_id),
                    "attributes": attrs,
                }
            )
    return {pid: {"label": v["label"], "n_images": len(v["n_images"]), "detections": v["detections"]} for pid, v in out.items()}


def normalize_case_id(case_id: str) -> str:
    m = re.search(r"(\d+)", str(case_id))
    return m.group(1) if m else str(case_id)


def pred_records_for_case(case: dict[str, Any]) -> list[dict[str, Any]]:
    det = case.get("detections") or {}
    out = []
    for d in det.get("detections", []):
        image_id = d["image_id"]
        out.append(
            {
                "cell_id": d.get("cell_id"),
                "image_id": image_id,
                "bbox_xyxy": [float(x) for x in d["bbox_xyxy"]],
                "global_bbox_xyxy": to_global_box(image_id, [float(x) for x in d["bbox_xyxy"]]),
                "class": d.get("class") or d.get("cell_type"),
                "confidence": float(d.get("confidence", 0.0)),
                "attributes": d.get("attributes", {}),
                "attribute_probs": d.get("attribute_probs", {}),
            }
        )
    return out


def match_predictions_to_gt(preds: list[dict], gts: list[dict], iou_thr: float) -> list[tuple[int, int, float]]:
    candidates = []
    for i, p in enumerate(preds):
        for j, g in enumerate(gts):
            iou = box_iou(p["global_bbox_xyxy"], g["global_bbox_xyxy"])
            if iou >= iou_thr:
                candidates.append((iou, i, j))
    candidates.sort(reverse=True)
    used_p, used_g, matches = set(), set(), []
    for iou, i, j in candidates:
        if i in used_p or j in used_g:
            continue
        used_p.add(i)
        used_g.add(j)
        matches.append((i, j, iou))
    return matches


def detection_metrics(cases: dict[str, dict], gt: dict[str, dict]) -> dict[str, Any]:
    rows = []
    ap_by_iou: dict[float, list[float]] = {0.5: []}
    for t in np.arange(0.5, 1.0, 0.05):
        ap_by_iou[round(float(t), 2)] = []

    per_class_counts = {c: Counter() for c in CLASS_NAMES if c != "None"}
    for case_id, case in cases.items():
        pid = normalize_case_id(case_id)
        if pid not in gt or "detections" not in case:
            continue
        preds = dedup_canvas(pred_records_for_case(case))
        gts = dedup_canvas(gt[pid]["detections"])

        for cls in [c for c in CLASS_NAMES if c != "None"]:
            y_true, y_score = [], []
            cls_preds = [p for p in preds if p["class"] == cls]
            cls_gts = [g for g in gts if g["class"] == cls]
            matched_at_05 = match_predictions_to_gt(cls_preds, cls_gts, 0.5)
            per_class_counts[cls]["tp"] += len(matched_at_05)
            per_class_counts[cls]["fp"] += max(0, len(cls_preds) - len(matched_at_05))
            per_class_counts[cls]["fn"] += max(0, len(cls_gts) - len(matched_at_05))

            # AP approximation: predictions are positives ranked by confidence;
            # unmatched GT objects are appended as missed positives with score 0.
            match_by_pred = {i for i, _, _ in matched_at_05}
            for i, p in enumerate(cls_preds):
                y_true.append(1 if i in match_by_pred else 0)
                y_score.append(float(p.get("confidence", 0.0)))
            for _ in range(max(0, len(cls_gts) - len(matched_at_05))):
                y_true.append(1)
                y_score.append(0.0)
            if len(set(y_true)) > 1:
                ap_by_iou[0.5].append(float(average_precision_score(y_true, y_score)))

        for thr in ap_by_iou:
            cls_aps = []
            for cls in [c for c in CLASS_NAMES if c != "None"]:
                cls_preds = [p for p in preds if p["class"] == cls]
                cls_gts = [g for g in gts if g["class"] == cls]
                matches = match_predictions_to_gt(cls_preds, cls_gts, thr)
                y_true, y_score = [], []
                match_by_pred = {i for i, _, _ in matches}
                for i, p in enumerate(cls_preds):
                    y_true.append(1 if i in match_by_pred else 0)
                    y_score.append(float(p.get("confidence", 0.0)))
                for _ in range(max(0, len(cls_gts) - len(matches))):
                    y_true.append(1)
                    y_score.append(0.0)
                if len(set(y_true)) > 1:
                    cls_aps.append(float(average_precision_score(y_true, y_score)))
            if cls_aps:
                rows.append({"case_id": case_id, "iou": thr, "ap": statistics.mean(cls_aps)})

    per_class = {}
    for cls, cnt in per_class_counts.items():
        tp, fp, fn = cnt["tp"], cnt["fp"], cnt["fn"]
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[cls] = {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1}
    map50 = statistics.mean([r["ap"] for r in rows if math.isclose(r["iou"], 0.5)]) if rows else None
    map5095_vals = [r["ap"] for r in rows if 0.5 <= r["iou"] <= 0.95]
    return {
        "mAP@0.5": map50,
        "mAP@0.5:0.95": statistics.mean(map5095_vals) if map5095_vals else None,
        "per_class": per_class,
        "note": "Evaluated after global-canvas deduplication. AP is computed from saved final boxes, not raw YOLO validation internals.",
    }


def attribute_metrics(cases: dict[str, dict], gt: dict[str, dict]) -> dict[str, Any]:
    y_true_by_attr = defaultdict(list)
    y_pred_by_attr = defaultdict(list)
    y_score_by_attr = defaultdict(list)
    for case_id, case in cases.items():
        pid = normalize_case_id(case_id)
        if pid not in gt or "detections" not in case:
            continue
        preds = dedup_canvas(pred_records_for_case(case))
        gts = dedup_canvas(gt[pid]["detections"])
        matches = match_predictions_to_gt(preds, gts, 0.5)
        for pi, gi, _ in matches:
            p, g = preds[pi], gts[gi]
            for attr in ATTR_NAMES:
                if attr not in g.get("attributes", {}):
                    continue
                yt = int(g["attributes"][attr])
                score = p.get("attribute_probs", {}).get(attr)
                if score is None:
                    score = p.get("attributes", {}).get(attr)
                if score is None:
                    continue
                score = float(score)
                y_true_by_attr[attr].append(yt)
                y_score_by_attr[attr].append(score)
                y_pred_by_attr[attr].append(int(score >= 0.5))

    per_attr = {}
    f1s = []
    for attr in ATTR_NAMES:
        yt = np.asarray(y_true_by_attr[attr], dtype=int)
        yp = np.asarray(y_pred_by_attr[attr], dtype=int)
        ys = np.asarray(y_score_by_attr[attr], dtype=float)
        if len(yt) == 0:
            per_attr[attr] = {"available": False}
            continue
        f1 = float(f1_score(yt, yp, zero_division=0))
        f1s.append(f1)
        auc = None
        if len(set(yt.tolist())) > 1:
            auc = float(roc_auc_score(yt, ys))
        per_attr[attr] = {
            "available": True,
            "n": int(len(yt)),
            "accuracy": float((yt == yp).mean()),
            "f1": f1,
            "auc": auc,
            "balanced_accuracy": float(balanced_accuracy_score(yt, yp)),
            "positive_recall": float(((yp == 1) & (yt == 1)).sum() / max((yt == 1).sum(), 1)),
            "negative_recall": float(((yp == 0) & (yt == 0)).sum() / max((yt == 0).sum(), 1)),
        }
    return {"per_attribute": per_attr, "macro_f1": statistics.mean(f1s) if f1s else None}


def extract_label_from_report(text: str) -> str | None:
    patterns = [
        ("APML", r"\bAPML\b|acute\s+promyelocytic\s+leukemia|abnormal\s+promyelocyte"),
        ("ALL", r"\bALL\b|acute\s+lymphoblastic\s+leukemia"),
        ("AML", r"\bAML\b|acute\s+myeloid\s+leukemia|acute\s+monoblastic|acute\s+myelomonocytic"),
        ("CLL", r"\bCLL\b|chronic\s+lymphocytic\s+leukemia"),
        ("CML", r"\bCML\b|chronic\s+myeloid\s+leukemia"),
        ("Indeterminate", r"\bindeterminate\b|no\s+subtype-defining|review\s+peripheral\s+smear"),
    ]
    for label, pattern in patterns:
        if re.search(pattern, text, re.I):
            return label
    return None


def classification_metrics(cases: dict[str, dict], gt: dict[str, dict], n_bootstrap: int = 1000) -> dict[str, Any]:
    y_true, y_pred, probs = [], [], []
    for case_id, case in cases.items():
        pid = normalize_case_id(case_id)
        if pid not in gt:
            continue
        pred = None
        score_map = None
        if case.get("classification"):
            pred = case["classification"].get("predicted_class")
            score_map = case["classification"].get("scores")
        if not pred and case.get("report_text"):
            pred = extract_label_from_report(case["report_text"])
        if pred:
            y_true.append(gt[pid]["label"])
            y_pred.append(str(pred))
            probs.append(score_map)
    if not y_true:
        return {"available": False, "reason": "No matched classification outputs and labels."}
    labels = sorted(set(y_true) | set(y_pred) | set(DIAGNOSES))
    p, r, f, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    per_class = {
        label: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(support[i])}
        for i, label in enumerate(labels)
    }
    macro_f1 = float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    kappa = float(cohen_kappa_score(y_true, y_pred, labels=labels))
    macro_auc = None
    if all(isinstance(x, dict) for x in probs):
        try:
            y_bin = np.asarray([[1 if t == label else 0 for label in labels] for t in y_true])
            score_arr = np.asarray([[float((score_map or {}).get(label, 0.0)) for label in labels] for score_map in probs])
            macro_auc = float(roc_auc_score(y_bin, score_arr, average="macro", multi_class="ovr"))
        except Exception:
            macro_auc = None
    return {
        "available": True,
        "n": len(y_true),
        "macro_f1": macro_f1,
        "macro_f1_bootstrap_ci": bootstrap_ci_macro_f1(y_true, y_pred, labels, n=n_bootstrap),
        "cohen_kappa": kappa,
        "macro_auc_ovr": macro_auc,
        "apml_recall": per_class.get("APML", {}).get("recall"),
        "labels": labels,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "per_class": per_class,
    }


def bootstrap_ci_macro_f1(y_true: list[str], y_pred: list[str], labels: list[str], n: int = 1000) -> dict[str, float] | None:
    if len(y_true) < 2 or n <= 0:
        return None
    rng = np.random.default_rng(42)
    vals = []
    idxs = np.arange(len(y_true))
    for _ in range(n):
        sample = rng.choice(idxs, size=len(idxs), replace=True)
        vals.append(
            f1_score(
                [y_true[i] for i in sample],
                [y_pred[i] for i in sample],
                labels=labels,
                average="macro",
                zero_division=0,
            )
        )
    return {"low": float(np.percentile(vals, 2.5)), "high": float(np.percentile(vals, 97.5))}


def optional_text_metric(name: str, fn):
    try:
        return fn()
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}


def report_metrics(cases: dict[str, dict], gt_reports_dir: Path | None = None) -> dict[str, Any]:
    rows = {}
    for case_id, case in cases.items():
        text = case.get("report_text")
        if not text:
            continue
        pid = normalize_case_id(case_id)
        row: dict[str, Any] = {
            "predicted_subtype": extract_label_from_report(text),
            "has_quantitative_summary": "Quantitative Cell Summary" in text,
            "has_grounding": "Cell Grounding" in text,
            "numeric_hallucination_rate": numeric_hallucination_rate(text, case.get("detections", {})),
            "grounding_validity": grounding_validity(text, case.get("detections", {})),
            "llm_as_judge": {
                "available": False,
                "reason": "Requires external GPT-4o or expert service; not run locally.",
                "criteria": ["coverage", "consistency", "diagnostic_accuracy", "clarity"],
            },
            "expert_review": {
                "available": False,
                "reason": "Requires expert review from clinical reviewers.",
            },
        }
        if gt_reports_dir:
            gt_path = find_gt_report(gt_reports_dir, pid)
            if gt_path and gt_path.is_file():
                gt_text = gt_path.read_text(encoding="utf-8", errors="ignore")
                row["surface_metrics"] = surface_report_metrics(text, gt_text)
                row["clinical_accuracy"] = {
                    "subtype_correct": int((extract_label_from_report(text) or "") == infer_label_from_text_or_name(gt_text, gt_path.name)),
                    "blast_call_correct": compare_blast_call(text, gt_text),
                }
            else:
                row["surface_metrics"] = {"available": False, "reason": "No GT report found."}
        rows[case_id] = row
    return {"aggregate": aggregate_report_metrics(rows), "per_case": rows}


def find_gt_report(gt_reports_dir: Path, pid: str) -> Path | None:
    for ext in (".md", ".txt"):
        direct = gt_reports_dir / f"case_{pid}_report{ext}"
        if direct.is_file():
            return direct
    candidates = [
        p for p in gt_reports_dir.rglob(f"case_{pid}_report.*")
        if p.suffix.lower() in {".md", ".txt"}
    ]
    return candidates[0] if candidates else None


def infer_label_from_text_or_name(text: str, name: str) -> str | None:
    return extract_label_from_report(name) or extract_label_from_report(text)


def compare_blast_call(a: str, b: str) -> int | None:
    def has_blast_call(t: str) -> bool | None:
        if re.search(r"blast.*threshold met|blast.*>=|acute leukemia", t, re.I):
            return True
        if re.search(r"no blast threshold|blast.*below", t, re.I):
            return False
        return None
    aa, bb = has_blast_call(a), has_blast_call(b)
    return int(aa == bb) if aa is not None and bb is not None else None


def surface_report_metrics(pred: str, ref: str) -> dict[str, Any]:
    pred = truncate_for_encoder(strip_grounding_for_text_metrics(pred))
    ref = truncate_for_encoder(strip_grounding_for_text_metrics(ref))
    out: dict[str, Any] = {}
    out["rouge_l"] = optional_text_metric("rouge_l", lambda: rouge_l_score(pred, ref))
    out["bleu"] = optional_text_metric("bleu", lambda: bleu_score(pred, ref))
    out["meteor"] = optional_text_metric("meteor", lambda: meteor_score(pred, ref))
    out["bertscore"] = optional_text_metric("bertscore", lambda: bert_score(pred, ref))
    return out


def strip_grounding_for_text_metrics(text: str) -> str:
    """Keep report prose/tables, but remove long cell-id/bbox grounding lists."""
    return re.split(r"\n##\s*Cell Grounding\b", text, maxsplit=1, flags=re.I)[0]


def truncate_for_encoder(text: str, max_words: int = 450) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def aggregate_report_metrics(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    def mean(values: list[float]) -> float | None:
        return float(statistics.mean(values)) if values else None

    def collect(path: tuple[str, ...]) -> list[float]:
        values = []
        for row in rows.values():
            cur: Any = row
            for key in path:
                if not isinstance(cur, dict) or key not in cur:
                    cur = None
                    break
                cur = cur[key]
            if isinstance(cur, (int, float)) and cur is not None:
                values.append(float(cur))
        return values

    subtype = collect(("clinical_accuracy", "subtype_correct"))
    blast = collect(("clinical_accuracy", "blast_call_correct"))
    numeric_rates = collect(("numeric_hallucination_rate", "rate"))
    grounding = collect(("grounding_validity", "validity"))
    rouge_l = collect(("surface_metrics", "rouge_l", "fmeasure"))
    bleu = collect(("surface_metrics", "bleu", "score"))
    meteor = collect(("surface_metrics", "meteor", "score"))
    bert = collect(("surface_metrics", "bertscore", "f1"))

    return {
        "n_reports": len(rows),
        "subtype_accuracy": mean(subtype),
        "blast_call_accuracy": mean(blast),
        "numeric_hallucination_rate_mean": mean(numeric_rates),
        "grounding_validity_mean": mean(grounding),
        "rouge_l_f1_mean": mean(rouge_l),
        "bleu_mean": mean(bleu),
        "meteor_mean": mean(meteor),
        "bertscore_f1_mean": mean(bert),
        "bertscore_available_cases": len(bert),
        "meteor_available_cases": len(meteor),
    }


def rouge_l_score(pred: str, ref: str) -> dict[str, float]:
    from rouge_score import rouge_scorer

    score = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True).score(ref, pred)["rougeL"]
    return {"precision": score.precision, "recall": score.recall, "fmeasure": score.fmeasure}


def bleu_score(pred: str, ref: str) -> dict[str, float]:
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

    return {
        "score": float(
            sentence_bleu(
                [ref.split()],
                pred.split(),
                smoothing_function=SmoothingFunction().method1,
            )
        )
    }


def _ensure_nltk_data() -> None:
    """Register local nltk_data dirs so NLTK can find wordnet for METEOR.

    NLTK only searches a fixed list of default directories, so a custom
    download location must be added to ``nltk.data.path`` explicitly.
    """
    import nltk

    candidates = [
        os.environ.get("NLTK_DATA"),
        str(Path(__file__).resolve().parent / "nltk_data"),
        str(Path.home() / "nltk_data"),
    ]
    for path in candidates:
        if path and path not in nltk.data.path and Path(path).is_dir():
            nltk.data.path.insert(0, path)


def meteor_score(pred: str, ref: str) -> dict[str, float]:
    _ensure_nltk_data()
    from nltk.translate.meteor_score import meteor_score as _meteor

    return {"score": float(_meteor([ref.split()], pred.split()))}


def bert_score(pred: str, ref: str) -> dict[str, Any]:
    global _BERT_SCORER
    if _BERT_SCORER is None:
        from bert_score import BERTScorer

        _BERT_SCORER = BERTScorer(
            model_type=BERTSCORE_MODEL,
            num_layers=BERTSCORE_NUM_LAYERS,
            rescale_with_baseline=False,
        )
        # Medical BERT tokenizers often lack model_max_length; pin it so
        # bert-score truncation does not overflow on long reports.
        if getattr(_BERT_SCORER._tokenizer, "model_max_length", 0) > BERTSCORE_MAX_LENGTH:
            _BERT_SCORER._tokenizer.model_max_length = BERTSCORE_MAX_LENGTH
    p, r, f = _BERT_SCORER.score([pred], [ref])
    return {
        "model_type": BERTSCORE_MODEL,
        "num_layers": BERTSCORE_NUM_LAYERS,
        "precision": float(p[0]),
        "recall": float(r[0]),
        "f1": float(f[0]),
    }


def numeric_hallucination_rate(report: str, det_payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the report's quantitative summary.

    The saved detections JSON can contain the broader detection set while an
    agentic reflection step may write a report from a stricter re-aggregation.
    For that reason, the hallucination rate below checks internal numeric
    consistency of the report itself. Source-data consistency is reported
    separately for debugging.
    """
    fields = extract_first_number(report, r"Fields of view:\s*(\d+)")
    raw = extract_first_number(report, r"Raw detected cells before overlap deduplication:\s*(\d+)")
    dedup = extract_first_number(report, r"Deduplicated detected cells:\s*(\d+)")
    informative = extract_first_number(report, r"Informative WBCs:\s*(\d+)")
    artifacts = extract_first_number(report, r"Artefacts/non-WBC detections:\s*(\d+)")
    reported_table = extract_quantitative_table(report)
    checks: list[dict[str, Any]] = []

    def add_check(name: str, reported: float | None, expected: float, tol: float = 0.0) -> None:
        if reported is None:
            checks.append({"name": name, "reported": None, "expected": expected, "passed": False})
            return
        passed = abs(float(reported) - float(expected)) <= tol
        checks.append({"name": name, "reported": reported, "expected": expected, "passed": passed})

    if fields is None or raw is None or dedup is None or informative is None or artifacts is None:
        missing = [
            name for name, value in {
                "fields_of_view": fields,
                "raw_detected_cells": raw,
                "deduplicated_detected_cells": dedup,
                "informative_wbcs": informative,
                "artifacts_non_wbc": artifacts,
            }.items()
            if value is None
        ]
        return {"available": False, "reason": f"Missing quantitative fields: {', '.join(missing)}"}

    add_check("informative_plus_artifacts_equals_dedup", informative + artifacts, dedup)
    checks.append({
        "name": "raw_detected_ge_deduplicated",
        "reported": raw,
        "expected": f">= {dedup}",
        "passed": raw >= dedup,
    })
    table_count_sum = sum(v["count"] for v in reported_table.values())
    add_check("table_counts_sum_to_informative", table_count_sum, informative)
    for cell_type, values in sorted(reported_table.items()):
        expected_pct = (values["count"] / informative * 100.0) if informative else 0.0
        add_check(f"{cell_type}_pct_matches_count", values["pct"], expected_pct, tol=0.15)

    failed = [c for c in checks if not c["passed"]]
    return {
        "available": True,
        "checked": len(checks),
        "mismatches": len(failed),
        "rate": len(failed) / len(checks) if checks else None,
        "failed_checks": failed,
        "source_consistency": source_numeric_consistency(det_payload, dedup, informative, artifacts),
    }


def source_numeric_consistency(
    det_payload: dict[str, Any],
    reported_dedup: float,
    reported_informative: float,
    reported_artifacts: float,
) -> dict[str, Any]:
    raw_detections = det_payload.get("detections", []) if det_payload else []
    if not raw_detections:
        return {"available": False, "reason": "No detection payload available."}
    detections = dedup_canvas(
        [
            {
                "image_id": d["image_id"],
                "bbox_xyxy": d["bbox_xyxy"],
                "class": d.get("class"),
                "confidence": d.get("confidence", 1.0),
            }
            for d in raw_detections
            if d.get("image_id") and d.get("bbox_xyxy")
        ]
    )
    informative = sum(1 for d in detections if d.get("class") and d.get("class") != "None")
    artifacts = len(detections) - informative
    return {
        "available": True,
        "saved_raw_detections": len(raw_detections),
        "saved_canvas_dedup_detections": len(detections),
        "saved_informative_wbcs": informative,
        "saved_artifacts": artifacts,
        "matches_report_dedup": len(detections) == int(reported_dedup),
        "matches_report_informative": informative == int(reported_informative),
        "matches_report_artifacts": artifacts == int(reported_artifacts),
    }


def extract_first_number(text: str, pattern: str) -> float | None:
    m = re.search(pattern, text, re.I)
    return float(m.group(1)) if m else None


def normalize_cell_type(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip())
    if name.endswith("s") and not name.lower().endswith("ss"):
        name = name[:-1]
    aliases = {
        "Artefact": "None",
        "Artifact": "None",
        "Abnormal promyelocytes": "Abnormal promyelocyte",
        "Atypical lymphocytes": "Atypical lymphocyte",
    }
    return aliases.get(name, name)


def extract_quantitative_table(report: str) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    in_summary = False
    for line in report.splitlines():
        if line.strip().lower().startswith("## quantitative cell summary"):
            in_summary = True
            continue
        if in_summary and line.strip().startswith("## "):
            break
        if not in_summary or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0].lower() in {"cell type", "---"} or set(cells[0]) == {"-"}:
            continue
        try:
            out[normalize_cell_type(cells[0])] = {
                "count": float(cells[1]),
                "pct": float(cells[2].rstrip("%")),
            }
        except ValueError:
            continue
    return out


def grounding_validity(report: str, det_payload: dict[str, Any]) -> dict[str, Any]:
    cited = set(re.findall(r"`(img\d+_c\d+)`", report))
    valid_ids = {d.get("cell_id") for d in det_payload.get("detections", [])}
    valid = cited & valid_ids
    return {
        "n_cited": len(cited),
        "n_valid": len(valid),
        "validity": len(valid) / len(cited) if cited else None,
        "invalid_cell_ids": sorted(cited - valid_ids),
    }


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    keys = sorted({k for row in rows for k in row})
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def main() -> None:
    global BERTSCORE_MODEL, BERTSCORE_NUM_LAYERS
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs-dir", type=Path, required=True, help="Directory containing case_* outputs.")
    ap.add_argument("--label-root", type=Path, required=True, help="Root containing LLD .txt labels.")
    ap.add_argument("--gt-reports-dir", type=Path, default=None, help="Optional reference report directory.")
    ap.add_argument("--out", type=Path, default=Path("eval_outputs"))
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument(
        "--bertscore-model",
        default=BERTSCORE_MODEL,
        help="HF model for BERTScore (default: clinical model emilyalsentzer/Bio_ClinicalBERT).",
    )
    ap.add_argument(
        "--bertscore-num-layers",
        type=int,
        default=BERTSCORE_NUM_LAYERS,
        help="Encoder layer to extract embeddings from for BERTScore.",
    )
    args = ap.parse_args()

    BERTSCORE_MODEL = args.bertscore_model
    BERTSCORE_NUM_LAYERS = args.bertscore_num_layers

    args.out.mkdir(parents=True, exist_ok=True)
    cases = load_predictions(args.outputs_dir)
    gt = load_gt_labels(args.label_root)
    results = {
        "n_cases_with_outputs": len(cases),
        "n_gt_patients": len(gt),
        "detection": detection_metrics(cases, gt),
        "attributes": attribute_metrics(cases, gt),
        "classification": classification_metrics(cases, gt, n_bootstrap=args.bootstrap),
        "reports": report_metrics(cases, args.gt_reports_dir),
    }

    (args.out / "evaluation_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    class_rows = []
    cls = results["classification"]
    if cls.get("available"):
        for label, row in cls["per_class"].items():
            class_rows.append({"class": label, **row})
        write_csv_rows(args.out / "classification_per_class.csv", class_rows)
    write_csv_rows(
        args.out / "detection_per_class.csv",
        [{"class": k, **v} for k, v in results["detection"].get("per_class", {}).items()],
    )
    write_csv_rows(
        args.out / "attribute_per_attribute.csv",
        [{"attribute": k, **v} for k, v in results["attributes"].get("per_attribute", {}).items()],
    )
    print(f"Wrote {args.out / 'evaluation_summary.json'}")


if __name__ == "__main__":
    main()
