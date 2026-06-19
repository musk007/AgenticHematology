# Batch evaluation summary

- **Output directory:** `/home/roba.majzoub/agentic_hematology/outputs/batch_effnet`
- **Ground truth (stats):** `/home/roba.majzoub/AgenticHematology/data_preprocessing/patient_WBC_stats_NoOveralp.json`
- **Approved reports:** `/home/roba.majzoub/AgenticHematology/LLM_reports`
- **Patients:** 13 (4, 6, 8, 15, 18, 21, 23, 28, 31, 34, 40, 43, 45)
- **Generated:** 2026-06-19T02:48:00.191549+00:00

## Overall metrics

| Area | Metric | Value |
|------|--------|------:|
| Detection | Mean differential MAE (pp) vs stats GT | 8.041 |
| Detection | Mean informative WBC count error (%) | 17.38 |
| Classification | Accuracy vs diagnosis label | 0.6154 (8/13) |
| Report vs approved | Differential MAE (pp) | 8.92 |
| Report vs approved | Differential class recall | 0.8359 |
| Report vs approved | Blast % correct (≤2.0 pp) | 0.0 |
| Report vs approved | Diagnosis impression match rate | 0.6154 |
| Report vs approved | Morphology match rate | 0.4444 |
| Report vs approved | **Hallucination rate** | 0.1627 |
| Text similarity (secondary) | ROUGE-L | 0.2415 |
| Text similarity (secondary) | BERTScore F1 | 0.8828 |
| Agent ablation | Outcome change rate (vs --no-agent) | None |
| Agent | Flagged for review | 10/13 |
| Report structure | Mean structural quality score (0–1) | 1.0 |

## Report vs hematologist-approved (field-level)

Primary report-quality signals. Hallucination = numeric claims in the generated report not traceable to pipeline JSON **or** the approved reference report (within tolerance).

| Field | Cohort mean / rate |
|-------|-------------------:|
| Differential table MAE (pp) | 8.92 |
| Differential class recall | 0.8359 |
| Blast % within 2.0 pp | 0.0 |
| Diagnosis impression matches label | 0.6154 |
| Morphology cohort (when present) | 0.4444 |
| Hallucination rate | 0.1627 (41/252 claims) |

## Text similarity (secondary only)

Secondary textual similarity signal only; not the primary quality claim.

- ROUGE-1: 0.3868
- ROUGE-2: 0.1959
- ROUGE-L: 0.2415
- BERTScore F1: 0.8828

## Agent ablation (--no-agent)

- Non-agentic dir: `None`
- Compared patients: 0
- Outcome change rate: None (0 changed)
- Accuracy agentic / non-agentic: None / None

## Classification by ground-truth class

| Class | Correct / Total | Accuracy |
|-------|----------------:|---------:|
| ALL | 4/4 | 1.0 |
| AML | 2/5 | 0.4 |
| APML | 0/1 | 0.0 |
| CLL | 0/1 | 0.0 |
| CML | 2/2 | 1.0 |

## Per-patient table

| Patient | Clf | GT | Pred | Halluc% | Diff MAE† | Flagged | ROUGE-L |
|---------|:---:|----|------|--------:|----------:|:-------:|--------:|
| 4 | ✓ | ALL | ALL | 0.1765 | 6.42 | yes | 0.2638 |
| 6 | ✓ | ALL | ALL | 0.2 | 10.18 | yes | 0.247 |
| 8 | ✓ | ALL | ALL | 0.0 | 5.48 | no | 0.2641 |
| 15 | ✓ | AML | AML | 0.2632 | 39.57 | yes | 0.2246 |
| 18 | ✓ | ALL | ALL | 0.1765 | 2.65 | no | 0.2701 |
| 21 | ✗ | CLL | Indeterminate | 0.2105 | 0.33 | yes | 0.2045 |
| 23 | ✗ | APML | AML | 0.1429 | 13.65 | yes | 0.2275 |
| 28 | ✓ | CML | CML | 0.1818 | 1.83 | yes | 0.2277 |
| 31 | ✓ | CML | CML | 0.1905 | 2.31 | yes | 0.2236 |
| 34 | ✗ | AML | ALL | 0.0588 | 6.53 | yes | 0.2533 |
| 40 | ✗ | AML | Indeterminate | 0.1818 | 11.73 | yes | 0.2234 |
| 43 | ✓ | AML | AML | 0.1 | 2.32 | no | 0.2625 |
| 45 | ✗ | AML | ALL | 0.1905 | 12.93 | yes | 0.2473 |

## Notes

- **Detection GT** comes from `patient_WBC_stats_NoOveralp.json`.
- **† Diff MAE** in the per-patient table is vs hematologist-approved report tables.
- **Hallucination rate** counts untraceable numeric claims in the report body (excluding the 20% blast threshold boilerplate).
- **ROUGE/BERTScore** are secondary textual similarity signals vs approved reports.
- **Agent ablation**: run `run_orchestrator.py --no-agent --out outputs/batch_non_agentic` then pass `--non-agentic-dir`.
- Re-run: `python summarize_batch_eval.py --output-dir outputs/batch_traced`
