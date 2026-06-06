#!/usr/bin/env python3
"""Generate markdown reports from CV prediction summaries using fine-tuned LoRA."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPORT_ROOT))
from bootstrap import DEFAULT_CONFIG, PROJECT_ROOT, setup_paths

setup_paths()

from src.config import load_config
from src.llm_infer import generate_all_summaries, load_model_and_tokenizer


def main() -> None:
    ap = argparse.ArgumentParser(
        description="LLM reports from stage-1 prediction summaries (not GT summaries)."
    )
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument(
        "--summaries",
        type=Path,
        default=None,
        help="Patient JSON dir from 02_aggregate_pred (default: summaries_pred)",
    )
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--model", type=Path, default=None)
    ap.add_argument("--adapter", type=Path, default=None, help="LoRA dir (lora_adapter_lm)")
    ap.add_argument("--max-new-tokens", type=int, default=None)
    ap.add_argument("--temperature", type=float, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    inf = cfg.get("inference", {})
    summaries = args.summaries or Path(cfg["output"]["summaries_pred"])
    out = args.out or Path(cfg["output"]["reports_llm_pred"])
    model_path = args.model or Path(inf.get("base_model", cfg["verl"]["base_model"]))
    adapter = args.adapter
    if adapter is None and inf.get("lora_adapter"):
        adapter = Path(inf["lora_adapter"])
    max_new = args.max_new_tokens if args.max_new_tokens is not None else int(inf.get("max_new_tokens", 768))
    temp = args.temperature if args.temperature is not None else float(inf.get("temperature", 0.0))

    if not summaries.is_dir():
        raise SystemExit(f"Missing summaries dir: {summaries}. Run: python scripts/02_aggregate_pred.py")
    n_json = len(list(summaries.glob("patient_*.json")))
    if n_json == 0:
        raise SystemExit(f"No patient_*.json under {summaries}")

    print(f"Summaries (predictions): {summaries} ({n_json} patients)")
    print(f"Model: {model_path}")
    print(f"LoRA:  {adapter or '(base only)'}")
    print(f"Out:   {out}")
    print(f"max_new_tokens={max_new} temperature={temp}")

    model, tok = load_model_and_tokenizer(model_path, adapter)
    paths = generate_all_summaries(
        summaries,
        out,
        model,
        tok,
        max_new_tokens=max_new,
        temperature=temp,
    )
    print(f"Wrote {len(paths)} LLM reports -> {out}")


if __name__ == "__main__":
    main()
