"""GRPO parquet: prompt from stage-1 pred summary; reward uses det+attr+report."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from .aggregate import aggregate_gt_from_data_root, aggregate_predictions, save_summaries
from .cv_reward import load_predictions_by_patient, score_patient_bundle
from .prompt import build_messages, summary_to_user_content
from .sft_dataset import build_sft_jsonl
from .verl_parquet import normalize_messages_for_verl

DATA_SOURCE_E2E = "leukemia_report_e2e"

DEFAULT_SYSTEM = (
    "You are a hematopathology assistant. Write a structured peripheral blood smear "
    "report in Markdown from the detection summary JSON only."
)


def _prompt_from_pred_summary(summary: dict[str, Any], system_prompt: str | None = None) -> list[dict[str, str]]:
    msgs = build_messages(summary, system_prompt=system_prompt or DEFAULT_SYSTEM, assistant_content=None)
    return normalize_messages_for_verl(msgs)


def build_grpo_e2e_parquet(
    *,
    reports_gt_dir: Path,
    data_root: Path,
    predictions_paths: list[Path],
    summaries_pred_dir: Path,
    summaries_gt_dir: Path,
    out_dir: Path,
    val_ratio: float = 0.1,
    seed: int = 42,
    split: str = "test",
    conf_threshold: float = 0.25,
) -> tuple[Path, Path]:
    try:
        import datasets
    except ImportError as e:
        raise ImportError("pip install datasets pyarrow") from e

    summaries_pred_dir.mkdir(parents=True, exist_ok=True)
    summaries_gt_dir.mkdir(parents=True, exist_ok=True)

    pred_by_patient = {}
    for ppath in predictions_paths:
        pred_by_patient.update(load_predictions_by_patient(ppath))

    pred_summaries = aggregate_predictions(predictions_paths, conf_threshold=conf_threshold)
    save_summaries(pred_summaries, summaries_pred_dir)

    gt_summaries = aggregate_gt_from_data_root(data_root, splits=(split, "train"))
    save_summaries(gt_summaries, summaries_gt_dir)

    records: list[dict[str, Any]] = []
    for pid, pred_sum in sorted(pred_summaries.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
        gt_path = reports_gt_dir / f"case_{pid}_report.md"
        if not gt_path.is_file():
            continue
        gt_sum = gt_summaries.get(pid)
        if not gt_sum:
            continue
        gt_report = gt_path.read_text(encoding="utf-8")
        cv = score_patient_bundle(
            pid,
            pred_sum,
            gt_sum,
            pred_by_patient.get(pid, []),
            data_root,
            split=split,
        )
        records.append(
            {
                "patient_id": pid,
                "disease_label_file": pred_sum.get("disease_label_file"),
                "gt_report": gt_report,
                "pred_summary": pred_sum,
                "cv_scores": cv,
            }
        )

    if not records:
        raise ValueError("No GRPO e2e records — check reports_gt_dir and predictions paths")

    rng = random.Random(seed)
    rng.shuffle(records)
    n_val = max(1, int(len(records) * val_ratio)) if len(records) > 1 else 0
    val_recs = records[:n_val]
    train_recs = records[n_val:] if n_val else records

    def to_row(rec: dict, split_name: str, idx: int) -> dict:
        return {
            "data_source": DATA_SOURCE_E2E,
            "prompt": _prompt_from_pred_summary(rec["pred_summary"]),
            "enable_thinking": False,
            "ability": "hematology_report_e2e",
            "reward_model": {
                "style": "rule",
                "ground_truth": rec["gt_report"],
            },
            "extra_info": {
                "split": split_name,
                "index": idx,
                "patient_id": rec["patient_id"],
                "disease_label_file": rec.get("disease_label_file"),
                "pred_summary_json": json.dumps(rec["pred_summary"], ensure_ascii=False),
                "gt_summary_json": json.dumps(
                    gt_summaries.get(str(rec["patient_id"]), {}), ensure_ascii=False
                ),
                "cv_det_score": rec["cv_scores"]["det_reward"],
                "cv_attr_score": rec["cv_scores"]["attr_reward"],
                "cv_cell_det": rec["cv_scores"]["det_score"],
                "cv_cell_attr": rec["cv_scores"]["attr_score"],
                "cv_summary_score": rec["cv_scores"]["summary_score"],
            },
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "train.parquet"
    val_path = out_dir / "val.parquet"
    datasets.Dataset.from_list([to_row(r, "train", i) for i, r in enumerate(train_recs)]).to_parquet(
        str(train_path)
    )
    datasets.Dataset.from_list([to_row(r, "val", i) for i, r in enumerate(val_recs)]).to_parquet(str(val_path))
    return train_path, val_path


def rebuild_sft_from_new_gt(
    summaries_gt_dir: Path,
    reports_gt_dir: Path,
    sft_jsonl: Path,
) -> int:
    return build_sft_jsonl(summaries_gt_dir, reports_gt_dir, sft_jsonl)
