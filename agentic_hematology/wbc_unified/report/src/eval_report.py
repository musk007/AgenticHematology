"""Compare generated reports to ground-truth (numeric differential + simple overlap)."""
from __future__ import annotations

import json
import re
from pathlib import Path

# Qwen3.5 chat / thinking wrappers (SFT & rollout)
_THINK_BLOCK_RE = re.compile(
    r"<\s*(?:think|thinking|redacted_reasoning|redacted_thinking)\s*>"
    r".*?"
    r"<\s*/\s*(?:think|thinking|redacted_reasoning|redacted_thinking)\s*>",
    re.IGNORECASE | re.DOTALL,
)
_CHAT_SPECIAL_RE = re.compile(
    r"<\|im_start\|>assistant\s*|<\|im_end\|>|<\|im_start\|>user\s*|<\|im_start\|>system\s*",
    re.IGNORECASE,
)


def strip_model_artifacts(text: str) -> str:
    """Remove chain-of-thought and chat control tokens before scoring."""
    t = text or ""
    t = _THINK_BLOCK_RE.sub("", t)
    t = _CHAT_SPECIAL_RE.sub("", t)
    # Unclosed thinking block (truncated at max_response_length)
    t = re.sub(
        r"<\s*redacted_thinking\s*>.*",
        "",
        t,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return t.strip()


def extract_report_markdown(text: str) -> str:
    """Focus scoring on hematology report markdown (prefer explicit section)."""
    t = strip_model_artifacts(text)
    m = re.search(r"(#\s*Hematology\s+Report\b.*)", t, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    # Truncated rollout: report-like tail after long preamble
    if len(t) > 6000:
        t = t[-6000:]
    return t


def _is_differential_header(line: str) -> bool:
    low = line.lower()
    if not line.startswith("|"):
        return False
    has_cell = "cell type" in low or ("cell" in low and "type" in low) or re.search(
        r"\|\s*cell\s*\|", low
    )
    has_pct = "%" in line or "percent" in low or "wbc" in low
    return bool(has_cell and has_pct)


def _parse_differential_table(md: str) -> dict[str, float]:
    """Extract differential table rows from markdown."""
    out: dict[str, float] = {}
    in_table = False
    for line in extract_report_markdown(md).splitlines():
        if not in_table and _is_differential_header(line):
            in_table = True
            continue
        if in_table and line.startswith("|") and "---" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                try:
                    out[parts[0]] = float(parts[1].replace("%", "").strip())
                except ValueError:
                    pass
        elif in_table and line.strip() == "":
            if out:
                break
        elif in_table and not line.startswith("|") and out:
            break
    return out


def _normalize_name(name: str) -> str:
    n = re.sub(r"\s+", " ", name.strip().lower())
    if n.endswith("s") and not n.endswith("ss"):
        n = n[:-1]
    return n


def eval_pair(generated: str, gt: str) -> dict:
    gen_diff = _parse_differential_table(generated)
    gt_diff = _parse_differential_table(gt)
    if not gt_diff:
        return {
            "mae_pct": None,
            "n_classes_gt": 0,
            "matched_classes": 0,
            "gen_diff": gen_diff,
            "gt_diff": gt_diff,
        }

    errors = []
    matched = 0
    for cls, gt_pct in gt_diff.items():
        key = None
        gt_norm = _normalize_name(cls)
        for gcls, gpct in gen_diff.items():
            if _normalize_name(gcls) == gt_norm:
                key = gcls
                break
        if key is not None:
            matched += 1
            errors.append(abs(gen_diff[key] - gt_pct))
    mae = sum(errors) / len(errors) if errors else None
    return {
        "mae_pct": round(mae, 2) if mae is not None else None,
        "n_classes_gt": len(gt_diff),
        "matched_classes": matched,
        "gen_diff": gen_diff,
        "gt_diff": gt_diff,
    }


def eval_directory(generated_dir: Path, gt_dir: Path) -> dict:
    results = {}
    for gen_path in sorted(generated_dir.glob("case_*_report.md")):
        pid = gen_path.stem.replace("case_", "").replace("_report", "")
        gt_path = gt_dir / gen_path.name
        if not gt_path.is_file():
            continue
        results[pid] = eval_pair(gen_path.read_text(), gt_path.read_text())
    maes = [r["mae_pct"] for r in results.values() if r.get("mae_pct") is not None]
    summary = {
        "n_cases": len(results),
        "mean_mae_differential_pct": round(sum(maes) / len(maes), 2) if maes else None,
        "per_case": results,
    }
    return summary
