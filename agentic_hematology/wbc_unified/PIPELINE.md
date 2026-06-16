# WBC Unified Pipeline

## Stages

| Stage | Module | Script | Output |
|-------|--------|--------|--------|
| 0 | `cv/` | `data/prepare_dataset.py` | YOLO labels + manifest |
| 1a | `cv/` | `train_detector.py` | `cv/runs/detector/` |
| 1b | `cv/` | `train_attributes.py` | `cv/runs/attribute/` |
| 1c | `cv/` | `infer.py` | `cv/runs/predict/infer/test_predictions.json` |
| 2 | `report/` | `01`–`06` scripts | parquet + summaries (NFS artifact) |
| 3 | `verl_scripts/` | SFT | LoRA adapter |
| 4 | `verl_scripts/` | GRPO | GRPO LoRA + deploy reports |

## Full run

```bash
cd wbc_unified
export CONFIRM_FULL_RETRAIN=1
bash pipeline/run.sh
```

Checkpoint wipe (`pipeline/wipe_checkpoints.sh`):

- Full: `cv/runs/*` + LLM checkpoints on NFS
- `SKIP_STAGE1=1`: keeps `cv/runs/`, wipes LLM only
- Stage-1-only (`SKIP_SFT=1 SKIP_GRPO=1`): wipes CV only

## Eval artifacts

| Stage | JSON |
|-------|------|
| Detector | `logs/pipeline_eval_*/metrics_detector_test.json` |
| Attributes | `metrics_attribute_test.json` |
| Joint | `metrics_stage1_joint_test.json` |
| Pred summaries | `metrics_pred_summaries.json` |
| SFT | `metrics_sft_val.json` |
| GRPO | `metrics_grpo_val.json` |
| Deploy | `$ARTIFACT/data/eval/metrics_llm_pred.json` |

Index: `logs/pipeline_eval_*/pipeline_summary.json`

## GPU defaults

| Stage | GPUs | Env |
|-------|------|-----|
| CV detect + attr | 1 | `STAGE1_NGPUS=1`, `module load cuda/11.8` |
| SFT / GRPO | 4 | `LLM_NGPUS=4`, **no** `module load cuda` |

## Environment variables

| Variable | Default |
|----------|---------|
| `CONFIRM_FULL_RETRAIN` | must be `1` for full wipe+train |
| `DATA_ROOT` | NFS LeukemiaDataset_Organized |
| `REPORT_LLM_ARTIFACT_ROOT` | NFS report_llm artifacts |
| `CONDA_ENV` | `SLA_Det` |
| `SKIP_STAGE1` / `SKIP_SFT` / `SKIP_GRPO` | `0` |
| `STAGE1_NGPUS` | `1` |
| `LLM_NGPUS` | `4` |
| `DET_WEIGHTS_LOCAL` | `1` (SLURM scratch for YOLO ckpt) |
| `RAY_CPUS` | `16` |

## Slurm recipes

```bash
# Recommended: split jobs
export CONFIRM_FULL_RETRAIN=1
sbatch pipeline/sbatch_stage1.sh
# after Stage-1 completes:
SKIP_STAGE1=1 sbatch pipeline/sbatch_full.sh
```
