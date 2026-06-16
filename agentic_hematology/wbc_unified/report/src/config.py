"""Load and resolve wbc_unified config."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .paths import DEFAULT_CONFIG, PROJECT_ROOT, REPO_ROOT

_DEFAULT_ARTIFACT_ROOT = "/nfs-stor/zongyan/wbc_medical/rao.anwer/report_llm"


def artifact_root_from_raw(raw: dict[str, Any]) -> Path:
    """NFS artifact root; override with REPORT_LLM_ARTIFACT_ROOT."""
    env = os.environ.get("REPORT_LLM_ARTIFACT_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    ar = raw.get("artifact_root", _DEFAULT_ARTIFACT_ROOT)
    p = Path(str(ar)).expanduser()
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p.resolve()


def resolve_under_artifact(artifact_root: Path, rel: str | Path) -> Path:
    p = Path(rel)
    if p.is_absolute():
        return p.resolve()
    return (artifact_root / p).resolve()


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG
    raw = yaml.safe_load(cfg_path.read_text())
    artifact_root = artifact_root_from_raw(raw)
    raw["artifact_root"] = str(artifact_root)

    data_root = Path(str(raw["data_root"]).format(**raw))
    raw["data_root"] = str(data_root.resolve())
    raw["reports_gt_dir"] = str(
        Path(str(raw["reports_gt_dir"]).format(data_root=data_root)).resolve()
    )

    out = raw.setdefault("output", {})
    for key in (
        "summaries_gt",
        "summaries_pred",
        "reports_generated",
        "reports_llm_pred",
        "sft_dataset",
        "eval",
        "hydra_outputs",
    ):
        if key in out:
            out[key] = str(resolve_under_artifact(artifact_root, out[key]))

    verl = raw.setdefault("verl", {})
    for key in (
        "sft_parquet",
        "grpo_e2e_parquet",
        "sft_save_dir",
        "grpo_save_dir",
        "base_model",
    ):
        if key in verl:
            v = verl[key]
            verl[key] = str(
                resolve_under_artifact(artifact_root, v) if not Path(str(v)).is_absolute() else Path(v)
            )

    inf = raw.setdefault("inference", {})
    if inf.get("base_model"):
        bm = str(inf["base_model"])
        inf["base_model"] = str(
            resolve_under_artifact(artifact_root, bm) if not Path(bm).is_absolute() else Path(bm)
        )
    la = inf.get("lora_adapter")
    if la and str(la).lower() not in ("null", "none", ""):
        inf["lora_adapter"] = str(
            resolve_under_artifact(artifact_root, la) if not Path(str(la)).is_absolute() else Path(la)
        )
    else:
        inf["lora_adapter"] = None

    stage1 = raw.setdefault("stage1", {})
    for key in ("det_weights", "attr_weights", "predictions_json"):
        if key in stage1:
            v = stage1[key]
            stage1[key] = str(
                (PROJECT_ROOT / v).resolve() if not Path(str(v)).is_absolute() else Path(v).resolve()
            )

    preds = []
    for p in raw.get("predictions", []):
        preds.append(
            str((PROJECT_ROOT / p).resolve() if not Path(p).is_absolute() else Path(p))
        )
    raw["predictions"] = preds
    raw["project_root"] = str(PROJECT_ROOT)
    raw["repo_root"] = str(REPO_ROOT)
    return raw
