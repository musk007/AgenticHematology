"""Convert report SFT JSONL to verl SFT parquet."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_messages_for_verl(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Qwen3.5 + verl MultiTurnSFT: merge system into the first user turn.

    Rendering system alone triggers TemplateError (system must lead or pair with user).
    """
    system_chunks: list[str] = []
    turns: list[dict[str, str]] = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_chunks.append(content)
        elif role in ("user", "assistant"):
            turns.append({"role": role, "content": content})
        else:
            turns.append({"role": role, "content": content})

    if not system_chunks:
        return turns

    prefix = "\n\n".join(system_chunks).strip()
    merged = False
    out: list[dict[str, str]] = []
    for msg in turns:
        if msg["role"] == "user" and not merged:
            out.append({"role": "user", "content": f"{prefix}\n\n{msg['content']}"})
            merged = True
        else:
            out.append(dict(msg))
    if not merged:
        out.insert(0, {"role": "user", "content": prefix})
    return out


def build_sft_parquet(
    jsonl_path: Path,
    out_dir: Path,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[Path, Path]:
    """SFT parquet with `messages` column (verl data.messages_key=messages)."""
    try:
        import datasets
    except ImportError as e:
        raise ImportError("pip install datasets pyarrow") from e

    rows = _load_jsonl(jsonl_path)
    rng = random.Random(seed)
    rng.shuffle(rows)
    n_val = max(1, int(len(rows) * val_ratio)) if len(rows) > 1 else 0
    val_rows = rows[:n_val]
    train_rows = rows[n_val:] if n_val else rows

    def to_sft(rec: dict) -> dict:
        return {
            "patient_id": rec["patient_id"],
            "messages": normalize_messages_for_verl(rec["messages"]),
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "train.parquet"
    val_path = out_dir / "val.parquet"
    datasets.Dataset.from_list([to_sft(r) for r in train_rows]).to_parquet(str(train_path))
    datasets.Dataset.from_list([to_sft(r) for r in val_rows]).to_parquet(str(val_path))
    return train_path, val_path
