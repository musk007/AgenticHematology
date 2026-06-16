# Report LLM Evaluation Metrics

Deploy path: **CV prediction JSON → pred summary → LoRA report → compare to GT report**.

Output: `data/eval/metrics_llm_pred.json` (`aggregate` + `per_case`).

## Three layers

### Layer A — input fidelity (pred summary vs GT summary)

Measures stage-1 detection/aggregation error (independent of the LLM).

| Field | Meaning | Better |
|-------|---------|--------|
| `summary_mae_pct` | Mean absolute % error per class vs GT summary | lower |
| `summary_class_recall` | Fraction of GT classes present in pred summary | higher |
| `summary_blast_pct_abs_err` | Blast % absolute error | lower |
| `summary_blast_flag_match` | `blast_threshold_met` agreement (0/1) | 1 |
| `cv_mean_det_conf` | Mean detection confidence | reference |
| `cv_artifact_pct` | Fraction flagged as artefact | reference |

### Layer B — report quality (generated vs GT report)

| Field | Meaning | Better |
|-------|---------|--------|
| `report_reward_score` | Rule score aligned with GRPO training (0–1) | higher |
| `report_mae_pct` | MAE of cell % in differential table | lower |
| `report_class_recall` | Matched GT classes / total GT classes | higher |
| `report_diff_score` | `max(0, 1 - mae/15)` | higher |
| `report_fmt_score` | Title / table / impression structure | higher |
| `report_imp_score` | Impression mentions correct disease | higher |

`report_reward_score` (aligned with `reward_report.py`):

```
0.45 * report_diff_score
+ 0.25 * report_coverage
+ 0.20 * report_fmt_score
+ 0.05 * report_imp_score
+ 0.05 * shaping_bonus
- penalty
```

### Layer C — end-to-end

| Field | Meaning |
|-------|---------|
| `e2e_score` | `0.7 * report_reward_score + 0.3 * (1 - summary_mae/15)` |

## Cohort aggregate (`aggregate`)

- Per metric: `mean` / `median` / `std` / `min` / `max`
- `pass_rate`: e.g. `report_reward_ge_0.70`, `report_mae_le_10`
- `by_disease`: grouped means for ALL / AML / …

## GRPO e2e reward (`reward_report_e2e.py`)

Training uses **pred summaries in the prompt** (same as deploy); GT is only for report scoring and frozen CV labels.

```
total = W_REPORT * report_score + W_DET * cv_det_score + W_ATTR * cv_attr_score
```

Default `W_REPORT=0.5, W_DET=0.25, W_ATTR=0.25`. CV scores are precomputed in `scripts/10_build_grpo_e2e.py` via `src/cv_reward.py`.

## Commands

```bash
bash run_validate_pred.sh
python scripts/08_eval_llm_reports.py
python scripts/09_print_metrics.py
python scripts/09_print_metrics.py --sort-by report_mae_pct --top 5
```
