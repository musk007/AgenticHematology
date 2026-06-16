# WBC Unified Pipeline

Merged `nextgen_wbc_pipeline` (CV detection + attributes) and `report_llm` (report SFT/GRPO) into a single project. The original directories are **kept** and still usable on their own.

## Layout

```
wbc_unified/
├── cv/                 # Stage-1: YOLO detection + attribute head + inference
├── report/             # Stage-2: summary aggregation + LLM train/infer scripts
├── verl_scripts/       # verl SFT/GRPO training entrypoints
├── config/             # Unified config (paths relative to wbc_unified/)
├── pipeline/           # End-to-end orchestration (run / sbatch / install)
└── logs/               # Run logs and eval summaries
```

External dependency (still at repo root):

- `../third_party/verl/` — verl framework (editable install)

## Environment setup

```bash
cd wbc_unified
conda activate SLA_Det
bash pipeline/install_env.sh          # CV + LLM full install
bash pipeline/install_env.sh verify   # dependency check only
```

LLM stack (verl + vLLM cu129):

```bash
export MODEL_PATH=/nfs-stor/zongyan/pretrained_models/Qwen3.5-2B
bash verl_scripts/install.sh
source verl_scripts/env.sh
```

## Full pipeline (train from scratch)

```bash
cd wbc_unified
export CONFIRM_FULL_RETRAIN=1
bash pipeline/run.sh
# Or Slurm (submit from wbc_unified/):
cd wbc_unified
sbatch pipeline/sbatch_full.sh
```

## Staged runs

```bash
# Stage-1 only (1 GPU)
export CONFIRM_FULL_RETRAIN=1
sbatch pipeline/sbatch_stage1.sh

# LLM only (keep CV weights, skip Stage-1)
export CONFIRM_FULL_RETRAIN=1
export SKIP_STAGE1=1
sbatch pipeline/sbatch_full.sh

# Deploy validation only (pred summary -> LoRA report)
source verl_scripts/env.sh
bash pipeline/run_validate_pred.sh
```

## Step-by-step LLM training

```bash
cd wbc_unified
source verl_scripts/env.sh

bash pipeline/run_stage1_infer.sh          # optional: re-run CV inference only
bash verl_scripts/train.sh data
python report/scripts/10_build_grpo_e2e.py --rebuild-sft
python report/scripts/06_prepare_verl_data.py --mode sft
bash verl_scripts/train.sh sft 4
bash verl_scripts/export_lora.sh 50
bash verl_scripts/cleanup_ray.sh
RAY_CPUS=16 bash verl_scripts/train.sh grpo
```

## Key paths

| Purpose | Path |
|---------|------|
| Dataset | `$DATA_ROOT` (default: NFS LeukemiaDataset_Organized) |
| CV weights | `cv/runs/{detector,attribute,predict}/` |
| LLM artifacts | `$REPORT_LLM_ARTIFACT_ROOT` (default: NFS) |
| Config | `config/default.yaml` |
| Eval summary | `logs/pipeline_eval_*/pipeline_summary.json` |

## Legacy command mapping

| Legacy (repo root) | New (wbc_unified) |
|--------------------|-------------------|
| `bash run_full_medical_pipeline.sh` | `bash pipeline/run.sh` |
| `sbatch sbatch_medical_full_pipeline.sh` | `sbatch pipeline/sbatch_full.sh` |
| `sbatch sbatch_medical_stage1.sh` | `sbatch pipeline/sbatch_stage1.sh` |
| `bash scripts/install_env.sh` | `bash pipeline/install_env.sh` |
| `nextgen_wbc_pipeline/` | `cv/` |
| `report_llm/` | `report/` + `verl_scripts/` |
