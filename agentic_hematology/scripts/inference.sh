#!/bin/bash

#SBATCH --job-name=wbc_agent
#SBATCH --time=4:00:00
#SBATCH --nodes=1
#SBATCH --partition=cscc-gpu-p
#SBATCH --qos=cscc-gpu-qos
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --output=/home/roba.majzoub/agentic_hematology/logs/sbatch_orchestrator_%j.out
#SBATCH --error=/home/roba.majzoub/agentic_hematology/logs/sbatch_orchestrator_%j.err

source /apps/local/anaconda3.10/bin/activate
conda activate /home/roba.majzoub/envs/agentic

cd /home/roba.majzoub
python agentic_hematology/run_orchestrator.py \
  --case-id PATIENT_004 \
  --backend wbc-unified \
  --images /home/roba.majzoub/agentic_hematology/wbc_unified/cv/generated/patients/patient_4/images \
  --yolo-weights wbc_unified/cv/runs/detector/train/weights/best.pt \
  --effnet-weights wbc_unified/cv/runs/attribute/train/best_attr.pt \
  --instruction "diagnose this case" \
  --report-backend template \
  --llm-model /nfs-stor/roba.majzoub/LLMs/Qwen3-VL-4B-Instruct \
  --lora-adapter /nfs-stor/roba.majzoub/wbc_medical/runs/wbc_sft_only/checkpoints/wbc_qwen3_4b_sft_lora \
  --out /home/roba.majzoub/agentic_hematology/outputs