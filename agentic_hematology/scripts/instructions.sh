# Shared weight paths (defaults in run_orchestrator.py match these)
YOLO=agentic_hematology/wbc_unified/cv/runs/detector/train/weights/best.pt
DINOBLOOM_L_MLP=agentic_hematology/runs/attribute_dinobloom/train/best_attr_dinobloom.pt
CLASSIFIER=agentic_hematology/wbc_unified/cv/runs/classifier/leukemia_rf.pkl
CLASSIFIER_6CLASS=agentic_hematology/wbc_unified/cv/runs/classifier/leukemia_rf_6class.pkl
# Legacy EfficientNet attribute head (ablation only)
EFFNET=agentic_hematology/wbc_unified/cv/runs/attribute/train/best_attr.pt

# ---------------------------------------------------------------------------
# Default pipeline — DinoBloom-L MLP attributes + YOLO detection
# ---------------------------------------------------------------------------
python agentic_hematology/run_orchestrator.py \
  --patients-dir agentic_hematology/wbc_unified/cv/generated/patients \
  --backend dinobloom \
  --dinobloom-weights auto \
  --dinobloom-variant l \
  --dinobloom-attr-mode probes \
  --dinobloom-attr-weights "${DINOBLOOM_L_MLP}" \
  --yolo-weights "${YOLO}" \
  --classifier-model "${CLASSIFIER}" \
  --instruction "diagnose this case" \
  --report-backend template \
  --no-agent \
  --device 0 \
  --out outputs/ablation_dinobloom_l_mlp

# ---------------------------------------------------------------------------
# Patient-level RF classifier training (detector + attribute head frozen)
# Runs cv/infer.py on LLD train split, then fits sklearn RF.
# Note: infer step still uses EfficientNet attributes unless you regenerate
# predictions with DinoBloom-L first (see TODO below).
# ---------------------------------------------------------------------------
cd /home/roba.majzoub/agentic_hematology

# 5-class (LLD only) → leukemia_rf.pkl
python Train_pipeline.py \
  --device 0 \
  --det-weights wbc_unified/cv/runs/detector/train/weights/best.pt \
  --attr-weights wbc_unified/cv/runs/attribute/train/best_attr.pt

# 6-class (LLD train + Helmholtz train split) → leukemia_rf_6class.pkl
python wbc_unified/cv/train_dinobloom_cell_classifier.py --device 0 --epochs 30
python wbc_unified/cv/extract_helmholtz_cells.py --device 0 --batch 64
python wbc_unified/cv/split_helmholtz.py
python Train_pipeline.py --include-healthy-class --skip-infer
python wbc_unified/cv/validate_6class.py \
  --lld-json wbc_unified/cv/runs/predict/infer/test_predictions.json \
  --classifier-model wbc_unified/cv/runs/classifier/leukemia_rf_6class.pkl
# Legacy metadata-only Helmholtz: build_helmholtz_metadata.py --classifier-only

# 6-class + domain normalization (per-dataset z-score + dataset_source)
python Train_pipeline.py --include-healthy-class --domain-normalize --skip-infer
python wbc_unified/cv/validate_6class.py \
  --lld-json wbc_unified/cv/runs/predict/infer/test_predictions.json \
  --classifier-model wbc_unified/cv/runs/classifier/leukemia_rf_6class_domainnorm.pkl

# Or submit via Slurm:
# sbatch scripts/train_agentic_pipeline.sh

# ---------------------------------------------------------------------------
# Attribute ablation A — EfficientNet (baseline)
# YOLO detection + YOLO cell type + EfficientNet morphology attributes
# ---------------------------------------------------------------------------
python agentic_hematology/run_orchestrator.py \
  --patients-dir agentic_hematology/wbc_unified/cv/generated/patients \
  --backend wbc-unified \
  --attribute-model effnet \
  --yolo-weights "${YOLO}" \
  --effnet-weights "${EFFNET}" \
  --classifier-model "${CLASSIFIER}" \
  --instruction "diagnose this case" \
  --report-backend template \
  --no-agent \
  --out outputs/ablation_effnet

# ---------------------------------------------------------------------------
# DinoBloom inference — NO training step required
# Flow: PBS tile → YOLO (detect+crop) → DinoBloom attributes (k-NN)
# - YOLO: --yolo-weights (required for cropped PBS tiles)
# - DinoBloom weights: auto-downloaded from HuggingFace (MarrLab/DinoBloom)
# - Attributes: k-NN over train manifest (cached on first run)
# ---------------------------------------------------------------------------
python agentic_hematology/run_orchestrator.py \
  --patients-dir agentic_hematology/wbc_unified/cv/generated/patients \
  --backend dinobloom \
  --yolo-weights "${YOLO}" \
  --dinobloom-weights auto \
  --classifier-model "${CLASSIFIER}" \
  --instruction "diagnose this case" \
  --report-backend template \
  --no-agent \
  --device 0 \
  --out outputs/ablation_dinobloom

# Optional: use trained linear probes instead of k-NN (after train_dinobloom_attributes.py)
#   --dinobloom-attr-mode probes --dinobloom-attr-weights "${DINOBLOOM_ATTR}"

# Single patient (EffNet attributes)
python agentic_hematology/run_orchestrator.py \
  --case-id PATIENT_004 \
  --backend wbc-unified \
  --images agentic_hematology/wbc_unified/cv/generated/patients/patient_4/images \
  --yolo-weights "${YOLO}" \
  --effnet-weights "${EFFNET}" \
  --classifier-model "${CLASSIFIER}" \
  --instruction "diagnose this case" \
  --report-backend template \
  --no-agent \
  --out agentic_hematology/outputs

# Agentic pipeline (same weights; adds LLM router/reflection)
python agentic_hematology/run_orchestrator.py \
  --case-id PATIENT_004 \
  --backend wbc-unified \
  --images agentic_hematology/wbc_unified/cv/generated/patients/patient_4/images \
  --yolo-weights "${YOLO}" \
  --effnet-weights "${EFFNET}" \
  --classifier-model "${CLASSIFIER}" \
  --instruction "diagnose this case" \
  --report-backend template \
  --llm-model /nfs-stor/roba.majzoub/LLMs/Qwen3-VL-4B-Instruct \
  --out agentic_hematology/outputs

if ImportError: libpython3.10.so.1.0: cannot open shared object file: No such file or directory:
use:
    export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"


## Evaluate ablation outputs
python evaluate_pipeline_outputs.py   \
  --outputs-dir outputs/ablation_effnet   \
  --label-root /home/roba.majzoub/agentic_hematology/wbc_unified/cv/generated/attributes/test   \
  --gt-reports-dir /home/roba.majzoub/AgenticHematology/LLM_reports   \
  --out eval_outputs/ablation_effnet

python evaluate_pipeline_outputs.py   \
  --outputs-dir outputs/ablation_dinobloom   \
  --label-root /home/roba.majzoub/agentic_hematology/wbc_unified/cv/generated/attributes/test   \
  --gt-reports-dir /home/roba.majzoub/AgenticHematology/template_reports/   \
  --out /home/roba.majzoub/agentic_hematology/outputs/ablation_dinobloom



#running pipeline using dinobloom (from repo root: /home/roba.majzoub)
### Base model - no training
python run_orchestrator.py \
  --patients-dir wbc_unified/cv/generated/patients \
  --backend dinobloom \
  --yolo-weights wbc_unified/cv/runs/detector/train/weights/best.pt \
  --dinobloom-weights auto \
  --no-agent \
  --device 0 \
  --out outputs/ablation_dinobloom

### Trained model - using probes
python run_orchestrator.py \
  --patients-dir wbc_unified/cv/generated/patients \
  --backend dinobloom \
  --dinobloom-weights auto \
  --dinobloom-attr-mode probes \
  --dinobloom-attr-weights wbc_unified/cv/runs/attribute_dinobloom/train/best_attr_dinobloom.pt \
  --no-agent \
  --device 0 \
  --out outputs/ablation_dinobloom_trained


## running on efficientnet
python run_orchestrator.py \
  --patients-dir /home/roba.majzoub/agentic_hematology/wbc_unified/cv/generated/patients \
  --backend wbc-unified \
  --attribute-model effnet \
  --yolo-weights /home/roba.majzoub/agentic_hematology/wbc_unified/cv/runs/detector/train/weights/best.pt \
  --effnet-weights /home/roba.majzoub/agentic_hematology/wbc_unified/cv/runs/attribute/train/best_attr.pt \
  --classifier-model /home/roba.majzoub/agentic_hematology/wbc_unified/cv/runs/classifier/leukemia_rf.pkl \
  --instruction "diagnose this case" \
  --report-backend template \
  --no-agent \
  --device 0 \
  --out outputs/ablation_effnet

# ---------------------------------------------------------------------------
# Train DinoBloom attribute head (Slurm)
# ---------------------------------------------------------------------------
cd /home/roba.majzoub/agentic_hematology
sbatch scripts/sbatch_train_dinobloom_attributes.sh

# Or run locally on an interactive GPU node:
# bash scripts/sbatch_train_dinobloom_attributes.sh

# Sklearn linear probes instead of torch MLP head:
# TRAIN_MODE=sklearn bash scripts/sbatch_train_dinobloom_attributes.sh

# ---------------------------------------------------------------------------
# Train DinoBloom attribute head manually (same as sbatch script)
# ---------------------------------------------------------------------------
# Torch MLP training (DinoBloom-L)
cd /home/roba.majzoub/agentic_hematology

python wbc_unified/cv/train_dinobloom_attributes_torch.py \
  --manifest wbc_unified/cv/generated/attr_manifest.csv \
  --dinobloom-weights auto \
  --dinobloom-variant l \
  --project runs/attribute_dinobloom \
  --name train \
  --epochs 40 \
  --batch 64 \
  --lr 1e-3 \
  --device 0 \
  --workers 2

# Sklearn probes (alternative head)
cd /home/roba.majzoub/agentic_hematology/wbc_unified/cv

python train_dinobloom_attributes.py \
  --manifest generated/attr_manifest.csv \
  --dinobloom-weights auto \
  --dinobloom-variant l \
  --project runs/attribute_dinobloom \
  --name train \
  --device 0 \
  --embed-batch 32


# Infer with trained DinoBloom-L MLP (defaults — no extra flags needed):
cd /home/roba.majzoub/agentic_hematology

python run_orchestrator.py \
  --patients-dir wbc_unified/cv/generated/patients \
  --no-agent \
  --device 0 \
  --out outputs/ablation_dinobloom_l_mlp


# Infer with trained sklearn probes:
python run_orchestrator.py \
  --patients-dir wbc_unified/cv/generated/patients \
  --backend dinobloom \
  --dinobloom-weights auto \
  --dinobloom-attr-mode probes \
  --dinobloom-attr-weights wbc_unified/cv/runs/attribute_dinobloom/train/best_attr_probes.joblib \
  --no-agent --device 0 \
  --out outputs/ablation_dinobloom_sklearn


## running sanity check for the two datasets attributes features embeddings 
cd /home/roba.majzoub/agentic_hematology

# Fast CPU smoke test
python wbc_unified/cv/embedding_sanity_check.py --device cpu --max-per-domain 500

# Full check (GPU recommended)
python wbc_unified/cv/embedding_sanity_check.py \
  --device 0 \
  --max-per-domain 2000 \
  --cache-npz /home/roba.majzoub/agentic_hematology/wbc_unified/cv/runs/predict/cached_embeddings.npz



## Stain-normalize Helmholtz toward LLD (Macenko) — then re-check embedding shift
# Reference: LLD cell crops from manifest (recommended) or images/train folder
python wbc_unified/cv/stain_norm_helmholtz.py \
  --reference_manifest wbc_unified/cv/generated/attr_manifest.csv \
  --n_ref 20 \
  --input_dir /home/roba.majzoub/helmholtz/data \
  --output_dir /home/roba.majzoub/helmholtz/data_stainnorm

# Baseline t-SNE shift (raw Helmholtz control crops)
python wbc_unified/cv/embedding_sanity_check.py \
  --device 0 --max-per-domain 2000 \
  --helmholtz-root /home/roba.majzoub/helmholtz/data/control \
  --out-plot wbc_unified/cv/runs/predict/dinobloom_embedding_lld_vs_helmholtz_raw.png

# After stain norm — shift ratio should drop (do NOT reuse raw cache npz)
python wbc_unified/cv/embedding_sanity_check.py \
  --device 0 --max-per-domain 2000 \
  --helmholtz-root /home/roba.majzoub/helmholtz/data_stainnorm/control \
  --out-plot wbc_unified/cv/runs/predict/dinobloom_embedding_lld_vs_helmholtz_stainnorm.png

# DinoBloom attribute extraction on stain-normalized controls (optional):
# python wbc_unified/cv/extract_mll_attributes.py --data-root /home/roba.majzoub/helmholtz/data_stainnorm/control --device 0
# Note: current 6-class RF uses Helmholtz metadata differentials, not image features.



# 6-class (LLD train + Helmholtz train split) → leukemia_rf_6class.pkl
python wbc_unified/cv/train_dinobloom_cell_classifier.py --device 0 --epochs 30
python wbc_unified/cv/extract_helmholtz_cells.py --device 0 --batch 64
python wbc_unified/cv/split_helmholtz.py
python Train_pipeline.py --include-healthy-class --skip-infer
python wbc_unified/cv/validate_6class.py \
  --lld-json wbc_unified/cv/runs/predict/infer/test_predictions.json \
  --classifier-model wbc_unified/cv/runs/classifier/leukemia_rf_6class.pkl
# Legacy metadata-only Helmholtz: build_helmholtz_metadata.py --classifier-only


python wbc_unified/cv/stain_norm_helmholtz.py \
  --reference_manifest wbc_unified/cv/generated/attr_manifest.csv \
  --input_dir ~/helmholtz/data \
  --output_dir ~/helmholtz/data_stainnorm
# 2. Compare embedding shift (raw vs stainnorm) — check .json shift_ratio / FLAG
python wbc_unified/cv/embedding_sanity_check.py \
  --helmholtz-root ~/helmholtz/data/control \
  --out-plot .../dinobloom_embedding_lld_vs_helmholtz_raw.png
python wbc_unified/cv/embedding_sanity_check.py \
  --helmholtz-root ~/helmholtz/data_stainnorm/control \
  --out-plot .../dinobloom_embedding_lld_vs_helmholtz_stainnorm.png


## training on the added data source features
python Train_pipeline.py --include-healthy-class --domain-normalize --skip-infer
 # validate after the training
python wbc_unified/cv/validate_6class.py \
  --lld-json wbc_unified/cv/runs/predict/infer/test_predictions.json \
  --classifier-model wbc_unified/cv/runs/classifier/leukemia_rf_6class_domainnorm.pkl