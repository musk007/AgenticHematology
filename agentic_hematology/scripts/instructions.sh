# =============================================================================
# AgenticHematology — LLD workflow
# Run from: cd /home/roba.majzoub/agentic_hematology
# Env:      source /apps/local/anaconda3.10/bin/activate /home/roba.majzoub/envs/agentic/
# =============================================================================

source /apps/local/anaconda3.10/bin/activate /home/roba.majzoub/envs/agentic/
cd /home/roba.majzoub/agentic_hematology

YOLO=wbc_unified/cv/runs/detector/train/weights/best.pt
EFFNET=wbc_unified/cv/runs/attribute/train/best_attr.pt
STATS_JSON=/home/roba.majzoub/AgenticHematology/data_preprocessing/patient_WBC_stats_NoOveralp.json
CLASSIFIER=runs/classifier/random_forest/leukemia_random_forest.pkl

# =============================================================================
# 1) Stage-1 weights (read-only calls into wbc_unified/cv/)
# =============================================================================
# python wbc_unified/cv/data/prepare_dataset.py \
#   --data-root /nfs-stor/roba.majzoub/LeukemiaDataset_Organized \
#   --out wbc_unified/cv/generated --image-mode hardlink
# sbatch scripts/sbatch_train_yolo.sh
# python wbc_unified/cv/train_attributes.py \
#   --config wbc_unified/cv/configs/dataset.yaml \
#   --epochs 40 --batch 256 --device 0 \
#   --project wbc_unified/cv/runs/attribute --name train

# =============================================================================
# 2) Patient classifier (train split only → evaluate on test split)
# =============================================================================
python train_leukemia_from_stats.py --backend random_forest \
  --stats-json "${STATS_JSON}" --out-dir runs/classifier/random_forest
python train_leukemia_from_stats.py --backend xgboost --model-name leukemia_xgboost \
  --stats-json "${STATS_JSON}" --out-dir runs/classifier/xgboost
python train_leukemia_from_stats.py --backend lightgbm --model-name leukemia_lightgbm \
  --stats-json "${STATS_JSON}" --out-dir runs/classifier/lightGBM

# =============================================================================
# 3) Template reports from stats + classifier predictions (CPU)
# =============================================================================
python run_lld_report_pipeline.py --backend random_forest --split test
python run_lld_report_pipeline.py --backend xgboost --split test
python run_lld_report_pipeline.py --backend lightgbm --split test

# =============================================================================
# 4) Full agentic pipeline (detect → aggregate → classify → reflect → report)
# =============================================================================
# Single patient with reflection + re_aggregate + flag_for_review:
# sbatch scripts/sbatch_orchestrator.sh
#   export CASE_ID=4 IMAGES_GLOB='wbc_unified/cv/generated/det_dataset/images/test/4_*.png'
#   export CLASSIFIER_MODEL=runs/classifier/random_forest/leukemia_random_forest.pkl
#   export USE_AGENT=1

# Batch: all 13 test patients with agent traces
# sbatch scripts/run_batch_agentic_traced.sh
# python analyze_agent_trace.py --agentic-dir outputs/batch_traced

# Or interactively:
python run_orchestrator.py \
  --lld-split test \
  --yolo-weights "${YOLO}" \
  --effnet-weights "${EFFNET}" \
  --classifier-model "${CLASSIFIER}" \
  --stats-json "${STATS_JSON}" \
  --llm-model models/Qwen3-VL-4B-Instruct \
  --max-reflect-iterations 2 \
  --report-backend template \
  --device 0 \
  --out outputs/batch_traced









#############################################
cd /home/roba.majzoub/agentic_hematology
source /apps/local/anaconda3.10/bin/activate /home/roba.majzoub/envs/agentic/

# Interactive (needs GPU + EfficientNet weights + Qwen model)
python run_orchestrator.py \
  --lld-split test \
  --classifier-model runs/classifier/random_forest/leukemia_random_forest.pkl \
  --stats-json /home/roba.majzoub/AgenticHematology/data_preprocessing/patient_WBC_stats_NoOveralp.json \
  --llm-model models/Qwen3-VL-4B-Instruct \
  --max-reflect-iterations 2 \
  --device 0 \
  --out outputs/batch_traced

# Or SLURM
sbatch scripts/run_batch_agentic_traced.sh

# Summarize reflection actions
python analyze_agent_trace.py --agentic-dir outputs/batch_traced