#!/usr/bin/env python3
"""Summarize agentic reflection traces (proceed / re_aggregate / flag_for_review)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent
WBC_CV = REPO / "wbc_unified" / "cv"


def ground_truth_for_patient(labels: dict[str, str], patient_id: str) -> str | None:
    return labels.get(str(patient_id))


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def find_classification(base: Path, pid: str) -> dict | None:
    return load_json(base / pid / f"case_{pid}_classification.json") or load_json(
        base / f"case_{pid}_classification.json"
    )


def discover_patient_ids(agentic_dir: Path) -> list[str]:
    ids: set[str] = set()
    if not agentic_dir.is_dir():
        return []
    for path in agentic_dir.iterdir():
        if path.is_dir():
            ids.add(path.name)
        for suffix in ("_agent_trace.json", "_classification.json"):
            for f in agentic_dir.glob(f"case_*{suffix}"):
                m = re.search(r"case_(.+?)_", f.name)
                if m:
                    ids.add(m.group(1))
    return sorted(ids, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))


def main() -> None:
    ap = argparse.ArgumentParser(description="Summarize agentic reflection batch outputs.")
    ap.add_argument("--agentic-dir", type=Path, default=REPO / "outputs" / "batch_traced")
    ap.add_argument("--non-agentic-dir", type=Path, default=REPO / "outputs" / "batch_non_agentic")
    ap.add_argument("--cv-root", type=Path, default=WBC_CV)
    args = ap.parse_args()

    from agentic_hematology.leukemia_features import discover_patient_labels_from_cv

    labels = discover_patient_labels_from_cv(args.cv_root)
    patients = discover_patient_ids(args.agentic_dir)
    if not patients:
        sys.exit(f"No patient outputs found under {args.agentic_dir}")

    print("=" * 100)
    print("D1 - Agent action trace (proceed / re_aggregate / flag_for_review)")
    print("=" * 100)

    final_actions: Counter[str] = Counter()
    for pid in patients:
        trace = load_json(args.agentic_dir / pid / f"case_{pid}_agent_trace.json")
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
    print("D2 - Outcome table (agentic vs optional non-agentic vs ground truth)")
    print("=" * 100)
    print(
        f"{'patient':14s} {'GT':6s} {'non-agentic':12s} {'agentic':10s} "
        f"{'flagged':8s} {'ag_correct':10s} {'non_ag_correct'}"
    )

    n_flagged_correct = n_flagged_incorrect = 0
    n_clean_correct = n_clean_incorrect = 0
    n_outcome_changed = 0
    for pid in patients:
        gt = ground_truth_for_patient(labels, pid)
        non_ag = find_classification(args.non_agentic_dir, pid) if args.non_agentic_dir.is_dir() else None
        ag = find_classification(args.agentic_dir, pid)
        trace = load_json(args.agentic_dir / pid / f"case_{pid}_agent_trace.json")

        non_ag_cls = non_ag["predicted_class"] if non_ag else None
        ag_cls = ag["predicted_class"] if ag else None
        flagged = trace["flagged_for_review"] if trace else None

        ag_correct = ag_cls == gt
        non_ag_correct = non_ag_cls == gt if non_ag_cls else None
        if non_ag_cls and ag_cls and ag_cls != non_ag_cls:
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
