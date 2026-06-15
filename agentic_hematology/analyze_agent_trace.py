#!/usr/bin/env python3
"""Summarize the agentic reflection trace and outcome changes for the 13-case batch.

D1: per-case agent action sequence (proceed / re_aggregate / flag_for_review),
    including iteration-level reasons and any conf_threshold adjustments.
D2: outcome-change table — agentic vs non-agentic predicted class vs ground
    truth, and whether flag_for_review correlates with classifier errors.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent
AGENTIC_DIR = REPO / "outputs" / "batch_traced"
NON_AGENTIC_DIR = REPO / "outputs" / "batch_non_agentic"
PATIENTS_DIR = REPO / "wbc_unified" / "cv" / "generated" / "patients"


def ground_truth_label(patient_id: str) -> str | None:
    images_dir = PATIENTS_DIR / patient_id / "images"
    if not images_dir.is_dir():
        return None
    for f in images_dir.iterdir():
        m = re.match(r"\d+_\d+_\d+_\d+_([A-Za-z]+)\.png", f.name)
        if m:
            return m.group(1)
    return None


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


def find_classification(base: Path, pid: str) -> dict | None:
    return load_json(base / pid / f"case_{pid}_classification.json") or load_json(
        base / f"case_{pid}_classification.json"
    )


def main() -> None:
    patients = sorted(
        (p.name for p in PATIENTS_DIR.iterdir() if p.is_dir()),
        key=lambda n: int(re.search(r"\d+", n).group()),
    )

    print("=" * 100)
    print("D1 - Agent action trace (proceed / re_aggregate / flag_for_review)")
    print("=" * 100)

    final_actions: Counter[str] = Counter()
    for pid in patients:
        trace = load_json(AGENTIC_DIR / pid / f"case_{pid}_agent_trace.json")
        if trace is None:
            print(f"{pid:14s}  NO TRACE FOUND")
            continue
        actions = trace["agent_actions"]
        seq = " -> ".join(
            a["action"] + (f"(ct={a['conf_threshold']})" if a.get("conf_threshold") else "")
            for a in actions
        )
        final = actions[-1]["action"] if actions else "?"
        final_actions[final] += 1
        print(
            f"{pid:14s}  iters={trace['n_reflect_iterations']}  "
            f"flagged={trace['flagged_for_review']!s:5}  trace: {seq}"
        )
        for a in actions:
            print(f"               [iter {a['iteration']}] {a['action']}: {a['reason']}")

    print()
    print("Final-action distribution:", dict(final_actions))

    print()
    print("=" * 100)
    print("D2 - Outcome-change table (agentic vs non-agentic vs ground truth)")
    print("=" * 100)
    print(
        f"{'patient':14s} {'GT':6s} {'non-agentic':12s} {'agentic':10s} "
        f"{'flagged':8s} {'ag_correct':10s} {'non_ag_correct'}"
    )

    n_flagged_correct = n_flagged_incorrect = 0
    n_clean_correct = n_clean_incorrect = 0
    n_outcome_changed = 0
    for pid in patients:
        gt = ground_truth_label(pid)
        non_ag = find_classification(NON_AGENTIC_DIR, pid)
        ag = find_classification(AGENTIC_DIR, pid)
        trace = load_json(AGENTIC_DIR / pid / f"case_{pid}_agent_trace.json")

        non_ag_cls = non_ag["predicted_class"] if non_ag else None
        ag_cls = ag["predicted_class"] if ag else None
        flagged = trace["flagged_for_review"] if trace else None

        ag_correct = ag_cls == gt
        non_ag_correct = non_ag_cls == gt
        if ag_cls != non_ag_cls:
            n_outcome_changed += 1

        if flagged:
            if ag_correct:
                n_flagged_correct += 1
            else:
                n_flagged_incorrect += 1
        else:
            if ag_correct:
                n_clean_correct += 1
            else:
                n_clean_incorrect += 1

        print(
            f"{pid:14s} {gt or '?':6s} {non_ag_cls or '-':12s} {ag_cls or '-':10s} "
            f"{str(flagged):8s} {str(ag_correct):10s} {str(non_ag_correct)}"
        )

    print()
    print(f"Predicted-class changed by agentic pathway: {n_outcome_changed}/{len(patients)}")
    print(f"flag_for_review cases:  correct={n_flagged_correct}  incorrect={n_flagged_incorrect}")
    print(f"no-flag cases:          correct={n_clean_correct}  incorrect={n_clean_incorrect}")


if __name__ == "__main__":
    main()
