# Batch evaluation summary

- **Output directory:** `/home/roba.majzoub/agentic_hematology/outputs/batch_dinobloom`
- **Ground truth (stats):** `/home/roba.majzoub/AgenticHematology/data_preprocessing/patient_WBC_stats_NoOveralp.json`
- **Approved reports:** `/home/roba.majzoub/AgenticHematology/LLM_reports`
- **Patients:** 13 (4, 6, 8, 15, 18, 21, 23, 28, 31, 34, 40, 43, 45)
- **Generated:** 2026-06-19T02:49:45.721415+00:00

## Overall metrics

| Area | Metric | Value |
|------|--------|------:|
| Detection | Mean differential MAE (pp) vs stats GT | 8.041 |
| Detection | Mean informative WBC count error (%) | 17.38 |
| Classification | Accuracy vs diagnosis label | 0.7692 (10/13) |
| Report vs approved | Differential MAE (pp) | 8.61 |
| Report vs approved | Differential class recall | 0.8417 |
| Report vs approved | Blast % correct (≤2.0 pp) | 0.0 |
| Report vs approved | Diagnosis impression match rate | 0.7692 |
| Report vs approved | Morphology match rate | 0.4444 |
| Report vs approved | **Hallucination rate** | 0.1514 |
| Text similarity (secondary) | ROUGE-L | 0.2408 |
| Text similarity (secondary) | BERTScore F1 | 0.8834 |
| Agent ablation | Outcome change rate (vs --no-agent) | None |
| Agent | Flagged for review | 12/13 |
| Report structure | Mean structural quality score (0–1) | 1.0 |

## Report vs hematologist-approved (field-level)

Primary report-quality signals. Hallucination = numeric claims in the generated report not traceable to pipeline JSON **or** the approved reference report (within tolerance).

| Field | Cohort mean / rate |
|-------|-------------------:|
| Differential table MAE (pp) | 8.61 |
| Differential class recall | 0.8417 |
| Blast % within 2.0 pp | 0.0 |
| Diagnosis impression matches label | 0.7692 |
| Morphology cohort (when present) | 0.4444 |
| Hallucination rate | 0.1514 (38/251 claims) |

## Text similarity (secondary only)

Secondary textual similarity signal only; not the primary quality claim.

- ROUGE-1: 0.3821
- ROUGE-2: 0.196
- ROUGE-L: 0.2408
- BERTScore F1: 0.8834

## Agent ablation (--no-agent)

- Non-agentic dir: `None`
- Compared patients: 0
- Outcome change rate: None (0 changed)
- Accuracy agentic / non-agentic: None / None

## Classification by ground-truth class

| Class | Correct / Total | Accuracy |
|-------|----------------:|---------:|
| ALL | 3/4 | 0.75 |
| AML | 5/5 | 1.0 |
| APML | 0/1 | 0.0 |
| CLL | 0/1 | 0.0 |
| CML | 2/2 | 1.0 |

## Per-patient table

| Patient | Clf | GT | Pred | Halluc% | Diff MAE† | Flagged | ROUGE-L |
|---------|:---:|----|------|--------:|----------:|:-------:|--------:|
| 4 | ✓ | ALL | ALL | 0.125 | 6.42 | yes | 0.2638 |
| 6 | ✓ | ALL | ALL | 0.1111 | 10.18 | yes | 0.2488 |
| 8 | ✓ | ALL | ALL | 0.125 | 5.48 | yes | 0.2551 |
| 15 | ✓ | AML | AML | 0.0952 | 29.06 | yes | 0.2233 |
| 18 | ✗ | ALL | AML | 0.1765 | 2.65 | yes | 0.2553 |
| 21 | ✗ | CLL | ALL | 0.1053 | 0.33 | yes | 0.2056 |
| 23 | ✗ | APML | AML | 0.1905 | 13.65 | yes | 0.2259 |
| 28 | ✓ | CML | CML | 0.1818 | 1.83 | yes | 0.2258 |
| 31 | ✓ | CML | CML | 0.1818 | 3.11 | yes | 0.219 |
| 34 | ✓ | AML | AML | 0.0 | 6.53 | yes | 0.2555 |
| 40 | ✓ | AML | AML | 0.2381 | 17.44 | yes | 0.2358 |
| 43 | ✓ | AML | AML | 0.15 | 2.32 | no | 0.2629 |
| 45 | ✓ | AML | AML | 0.2381 | 12.93 | yes | 0.2533 |

## Notes

- **Detection GT** comes from `patient_WBC_stats_NoOveralp.json`.
- **† Diff MAE** in the per-patient table is vs hematologist-approved report tables.
- **Hallucination rate** counts untraceable numeric claims in the report body (excluding the 20% blast threshold boilerplate).
- **ROUGE/BERTScore** are secondary textual similarity signals vs approved reports.
- **Agent ablation**: run `run_orchestrator.py --no-agent --out outputs/batch_non_agentic` then pass `--non-agentic-dir`.
- Re-run: `python summarize_batch_eval.py --output-dir outputs/batch_traced`
