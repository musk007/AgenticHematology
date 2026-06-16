#!/usr/bin/env python3
"""Strip vision-tower LoRA weights for vLLM language_model_only rollout."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from safetensors import safe_open
from safetensors.torch import save_file


def is_language_lora_key(key: str) -> bool:
    k = key.lower()
    if ".visual." in k or k.startswith("visual."):
        return False
    if "patch_embed" in k and "visual" in k:
        return False
    return "language_model" in k or (
        ".layers." in k and "visual" not in k and "model.model.model." in k
    )


def is_vllm_lora_key(key: str) -> bool:
    """vLLM 0.21 has a bug applying GDN/linear_attn LoRA on Qwen3.5 (repeated tokens)."""
    if not is_language_lora_key(key):
        return False
    k = key.lower()
    if ".linear_attn." in k or ".conv1d" in k:
        return False
    return True


GDN_TARGETS = frozenset({"in_proj_a", "in_proj_b", "in_proj_qkv", "in_proj_z", "conv1d"})


def _filter_keys(
    src: Path,
    dst: Path,
    keep_fn,
    *,
    skip_targets: frozenset[str] = frozenset(),
    force: bool = False,
) -> tuple[int, int]:
    src = src.resolve()
    dst = dst.resolve()
    src_weights = src / "adapter_model.safetensors"
    if not src_weights.is_file():
        raise FileNotFoundError(f"Missing {src_weights}")

    if dst.is_dir() and (dst / "adapter_model.safetensors").is_file() and not force:
        return 0, 0

    dst.mkdir(parents=True, exist_ok=True)
    kept, dropped = {}, 0
    with safe_open(src_weights, framework="pt") as f:
        for key in f.keys():
            if keep_fn(key):
                kept[key] = f.get_tensor(key)
            else:
                dropped += 1

    if not kept:
        raise RuntimeError(f"No LoRA keys kept from {src_weights}")

    save_file(kept, dst / "adapter_model.safetensors")
    cfg_src = src / "adapter_config.json"
    if cfg_src.is_file():
        cfg = json.loads(cfg_src.read_text())
        cfg["target_modules"] = [
            m
            for m in cfg.get("target_modules", [])
            if "visual" not in str(m).lower() and str(m) not in skip_targets
        ]
        (dst / "adapter_config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    for name in ("README.md",):
        p = src / name
        if p.is_file():
            shutil.copy2(p, dst / name)
    return len(kept), dropped


def filter_adapter(src: Path, dst: Path, force: bool = False) -> tuple[int, int]:
    return _filter_keys(src, dst, is_language_lora_key, force=force)


def filter_adapter_vllm(src: Path, dst: Path, force: bool = False) -> tuple[int, int]:
    return _filter_keys(
        src, dst, is_vllm_lora_key, skip_targets=GDN_TARGETS, force=force
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("src", type=Path, help="Full LoRA adapter dir (with visual keys)")
    p.add_argument(
        "--dst",
        type=Path,
        default=None,
        help="Output dir (default: <src>_lm)",
    )
    p.add_argument("--force", action="store_true")
    p.add_argument(
        "--vllm",
        action="store_true",
        help="Also write <stem>_vllm adapter (drop linear_attn/conv1d for vLLM rollout)",
    )
    args = p.parse_args()
    src = args.src.resolve()
    lm_dst = args.dst or Path(str(src).rstrip("/") + "_lm")
    kept, dropped = filter_adapter(src, lm_dst, force=args.force)
    print(f"Wrote LM-only adapter: {lm_dst}")
    print(f"kept={kept} dropped={dropped}")

    stem = lm_dst.name[:-3] if lm_dst.name.endswith("_lm") else lm_dst.name
    vllm_dst = lm_dst.parent / f"{stem}_vllm"
    vkept, vdropped = filter_adapter_vllm(lm_dst, vllm_dst, force=args.force)
    print(f"Wrote vLLM adapter: {vllm_dst}")
    print(f"kept={vkept} dropped_gdn={vdropped}")


if __name__ == "__main__":
    main()
