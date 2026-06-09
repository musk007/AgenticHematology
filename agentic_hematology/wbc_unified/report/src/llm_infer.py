"""Batch report generation with Qwen3.5 + optional LoRA (HF backend)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .prompt import messages_for_inference


def load_model_and_tokenizer(
    model_path: str | Path,
    adapter_path: str | Path | None = None,
):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoTokenizer

    model_path = Path(model_path).expanduser().resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(f"Base model directory not found: {model_path}")
    model_path_str = str(model_path)
    tok = AutoTokenizer.from_pretrained(
        model_path_str,
        trust_remote_code=True,
        local_files_only=True,
    )
    model = AutoModelForImageTextToText.from_pretrained(
        model_path_str,
        trust_remote_code=True,
        local_files_only=True,
        dtype=torch.bfloat16,
        device_map="auto",
    )
    if adapter_path:
        adapter_path = Path(adapter_path).expanduser().resolve()
        if not adapter_path.is_dir():
            raise FileNotFoundError(f"LoRA adapter directory not found: {adapter_path}")
        model = PeftModel.from_pretrained(
            model,
            str(adapter_path),
            is_trainable=False,
            local_files_only=True,
        )
    model.eval()
    return model, tok


def encode_messages(tokenizer, messages: list[dict[str, str]]) -> list[int]:
    try:
        import sys
        from .paths import REPO_ROOT
        verl_root = REPO_ROOT / "third_party" / "verl"
        if str(verl_root) not in sys.path:
            sys.path.insert(0, str(verl_root))
        from verl.utils.chat_template import apply_chat_template
        from verl.utils.tokenizer import normalize_token_ids
        return normalize_token_ids(
            apply_chat_template(
                tokenizer,
                messages,
                add_generation_prompt=True,
                tokenize=True,
                enable_thinking=False,
            )
        )
    except (ImportError, ModuleNotFoundError):
        pass
    # Fallback: HF tokenizer directly (no verl dependency)
    try:
        ids = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            enable_thinking=False,
        )
    except TypeError:
        ids = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
        )
    return list(ids)


def encode_prompt(tokenizer, summary: dict[str, Any]) -> list[int]:
    msgs = messages_for_inference(summary)
    return encode_messages(tokenizer, msgs)


def generate_from_messages(
    model,
    tokenizer,
    messages: list[dict[str, str]],
    *,
    max_new_tokens: int = 768,
    temperature: float = 0.0,
    repetition_penalty: float = 1.08,
) -> str:
    import torch

    prompt_ids = encode_messages(tokenizer, messages)
    inp = torch.tensor([prompt_ids], device=model.device)
    gen_kw: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    if temperature > 0:
        gen_kw.update(do_sample=True, temperature=temperature, repetition_penalty=repetition_penalty)
    else:
        gen_kw["do_sample"] = False

    with torch.no_grad():
        out = model.generate(inp, **gen_kw)
    return tokenizer.decode(out[0, len(prompt_ids) :], skip_special_tokens=True)


def generate_report(
    model,
    tokenizer,
    summary: dict[str, Any],
    *,
    max_new_tokens: int = 768,
    temperature: float = 0.0,
    repetition_penalty: float = 1.08,
) -> str:
    import torch

    prompt_ids = encode_prompt(tokenizer, summary)
    inp = torch.tensor([prompt_ids], device=model.device)
    gen_kw: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    if temperature > 0:
        gen_kw.update(do_sample=True, temperature=temperature, repetition_penalty=repetition_penalty)
    else:
        gen_kw["do_sample"] = False

    with torch.no_grad():
        out = model.generate(inp, **gen_kw)
    return tokenizer.decode(out[0, len(prompt_ids) :], skip_special_tokens=True)


def generate_all_summaries(
    summaries_dir: Path,
    out_dir: Path,
    model,
    tokenizer,
    *,
    max_new_tokens: int = 768,
    temperature: float = 0.0,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path in sorted(summaries_dir.glob("patient_*.json")):
        import json

        summary = json.loads(path.read_text(encoding="utf-8"))
        pid = summary["patient_id"]
        text = generate_report(
            model,
            tokenizer,
            summary,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
        out_path = out_dir / f"case_{pid}_report.md"
        out_path.write_text(text, encoding="utf-8")
        written.append(out_path)
    return written
