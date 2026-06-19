# Batch evaluation summary

- **Output directory:** `/home/roba.majzoub/agentic_hematology/outputs/batch_dinobloom_noAgent`
- **Ground truth (stats):** `/home/roba.majzoub/AgenticHematology/data_preprocessing/patient_WBC_stats_NoOveralp.json`
- **Approved reports:** `/home/roba.majzoub/AgenticHematology/LLM_reports`
- **Patients:** 13 (4, 6, 8, 15, 18, 21, 23, 28, 31, 34, 40, 43, 45)
- **Generated:** 2026-06-19T02:44:07.637399+00:00

## Overall metrics

| Area | Metric | Value |
|------|--------|------:|
| Detection | Mean differential MAE (pp) vs stats GT | 8.041 |
| Detection | Mean informative WBC count error (%) | 17.38 |
| Classification | Accuracy vs diagnosis label | 0.7692 (10/13) |
| Report vs approved | Differential MAE (pp) | 8.1 |
| Report vs approved | Differential class recall | 0.8513 |
| Report vs approved | Blast % correct (≤2.0 pp) | 0.0 |
| Report vs approved | Diagnosis impression match rate | 0.7692 |
| Report vs approved | Morphology match rate | 0.4444 |
| Report vs approved | **Hallucination rate** | 0.1587 |
| Text similarity (secondary) | ROUGE-L | 0.2476 |
| Text similarity (secondary) | BERTScore F1 | 0.8836 |
| Agent ablation | Outcome change rate (vs --no-agent) | None |
| Agent | Flagged for review | 0/13 |
| Report structure | Mean structural quality score (0–1) | 1.0 |

## Report vs hematologist-approved (field-level)

Primary report-quality signals. Hallucination = numeric claims in the generated report not traceable to pipeline JSON **or** the approved reference report (within tolerance).

| Field | Cohort mean / rate |
|-------|-------------------:|
| Differential table MAE (pp) | 8.1 |
| Differential class recall | 0.8513 |
| Blast % within 2.0 pp | 0.0 |
| Diagnosis impression matches label | 0.7692 |
| Morphology cohort (when present) | 0.4444 |
| Hallucination rate | 0.1587 (40/252 claims) |

## Text similarity (secondary only)

Secondary textual similarity signal only; not the primary quality claim.

- ROUGE-1: 0.383
- ROUGE-2: 0.2014
- ROUGE-L: 0.2476
- BERTScore F1: 0.8836

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
| 4 | ✓ | ALL | ALL | 0.125 | 6.42 | no | 0.2727 |
| 6 | ✓ | ALL | ALL | 0.1111 | 10.18 | no | 0.2578 |
| 8 | ✓ | ALL | ALL | 0.125 | 5.48 | no | 0.2637 |
| 15 | ✓ | AML | AML | 0.0952 | 29.06 | no | 0.231 |
| 18 | ✗ | ALL | AML | 0.1765 | 2.65 | no | 0.2646 |
| 21 | ✗ | CLL | ALL | 0.1053 | 0.33 | no | 0.2115 |
| 23 | ✗ | APML | AML | 0.1905 | 13.65 | no | 0.2351 |
| 28 | ✓ | CML | CML | 0.1818 | 1.83 | no | 0.2335 |
| 31 | ✓ | CML | CML | 0.2273 | 2.21 | no | 0.2244 |
| 34 | ✓ | AML | AML | 0.0588 | 6.53 | no | 0.2668 |
| 40 | ✓ | AML | AML | 0.1818 | 11.73 | no | 0.2334 |
| 43 | ✓ | AML | AML | 0.15 | 2.32 | no | 0.2629 |
| 45 | ✓ | AML | AML | 0.2857 | 12.93 | no | 0.2613 |

## Notes

- **Detection GT** comes from `patient_WBC_stats_NoOveralp.json`.
- **† Diff MAE** in the per-patient table is vs hematologist-approved report tables.
- **Hallucination rate** counts untraceable numeric claims in the report body (excluding the 20% blast threshold boilerplate).
- **ROUGE/BERTScore** are secondary textual similarity signals vs approved reports.
- **Agent ablation**: run `run_orchestrator.py --no-agent --out outputs/batch_non_agentic` then pass `--non-agentic-dir`.
- Re-run: `python summarize_batch_eval.py --output-dir outputs/batch_traced`
