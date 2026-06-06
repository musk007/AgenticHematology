#!/usr/bin/env python3
"""Generate on val parquet and score reports (SFT or GRPO LoRA)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT_ROOT))
from bootstrap import DEFAULT_CONFIG, PROJECT_ROOT, setup_paths

setup_paths()

from src.config import load_config
from src.llm_infer import generate_from_messages, load_model_and_tokenizer
from src.verl_parquet import normalize_messages_for_verl
from verl_scripts.reward_report import compute_score
from verl_scripts.reward_report_e2e import compute_score as compute_score_e2e


def _load_rows(parquet: Path) -> list[dict]:
    try:
        import pyarrow.parquet as pq

        return pq.read_table(parquet).to_pylist()
    except ImportError:
        import pandas as pd

        return pd.read_parquet(parquet).to_dict(orient="records")


def _prompt_messages(row: dict, stage: str) -> list[dict[str, str]]:
    if stage == "grpo":
        prompt = row.get("prompt")
        if isinstance(prompt, str):
            return json.loads(prompt)
        return list(prompt)
    msgs = row.get("messages")
    if isinstance(msgs, str):
        msgs = json.loads(msgs)
    pre: list[dict[str, str]] = []
    for m in msgs:
        if m["role"] == "assistant":
            break
        pre.append({"role": m["role"], "content": m["content"]})
    return normalize_messages_for_verl(pre)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", type=Path, required=True)
    ap.add_argument("--adapter", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--stage", choices=("sft", "grpo"), default="sft")
    ap.add_argument("--max-new-tokens", type=int, default=768)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = ap.parse_args()

    cfg = load_config(args.config)
    base = Path(cfg["inference"]["base_model"])
    score_fn = compute_score_e2e if args.stage == "grpo" else compute_score

    model, tok = load_model_and_tokenizer(base, args.adapter)
    rows = _load_rows(args.parquet)
    per_case: dict[str, dict] = {}
    scores: list[float] = []

    for row in rows:
        extra = row.get("extra_info") or {}
        if hasattr(extra, "item"):
            extra = extra.item()
        pid = str(extra.get("patient_id", len(per_case)))
        gt = row["reward_model"]["ground_truth"]
        msgs = _prompt_messages(row, args.stage)
        gen = generate_from_messages(
            model,
            tok,
            msgs,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
        ds = row.get("data_source", "leukemia_report")
        out = score_fn(ds, gen, gt, extra)
        sc = float(out.get("score", out) if isinstance(out, dict) else out)
        scores.append(sc)
        per_case[pid] = {"score": sc, **(out if isinstance(out, dict) else {})}

    payload = {
        "stage": f"{args.stage}_val",
        "parquet": str(args.parquet.resolve()),
        "adapter": str(args.adapter.resolve()),
        "n_cases": len(scores),
        "mean_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "per_case": per_case,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}  mean_score={payload['mean_score']}  n={payload['n_cases']}")


if __name__ == "__main__":
    main()
