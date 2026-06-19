# AgenticHematology — LLD workflow




```bash
YOLO=wbc_unified/cv/runs/detector/train/weights/best.pt
EFFNET=wbc_unified/cv/runs/attribute/train/best_attr.pt
CLASSIFIER=outputs/ablations/classifier/dinobloom/random_forest/leukemia_random_forest.pkl
DINOBLOOM_ATTR=wbc_unified/cv/runs/attribute_dinobloom/train/best_attr_dinobloom.pt
```

---

#### 1) Prepare the data

```bash
python wbc_unified/cv/data/prepare_dataset.py \
  --data-root /nfs-stor/roba.majzoub/LeukemiaDataset_Organized \
  --out wbc_unified/cv/generated --image-mode hardlink
```

#### 2) Train the detector
```bash
sbatch scripts/sbatch_train_yolo.sh
```

#### 3) Train EfficientNet for attribute classification
```bash
python wbc_unified/cv/train_attributes.py \
  --config wbc_unified/cv/configs/dataset.yaml \
  --epochs 40 --batch 256 --device 0 \
  --project wbc_unified/cv/runs/attribute --name train
```

#### 4)Train leukemia classifier using EfficientNet predictions (this trains all 3 types of classifiers including XGBoost, light GBM, and random forest):

```bash
python train_leukemia_from_efficientnet.py --backend all --device 0
```

---
Alternative for attribute classification
#### 3) Train DinoBloom MLP for attribute classification
```bash
python wbc_unified/cv/train_dinobloom_attributes_torch.py \
  --manifest wbc_unified/cv/generated/attr_manifest.csv \
  --dinobloom-weights /home/roba.majzoub/DinoBloom-L.pth \
  --dinobloom-variant l \
  --project wbc_unified/cv/runs/attribute_dinobloom \
  --name train \
  --epochs 40 --batch 64 --device 0 --workers 2
```
#### 4) Train leukemia classifier using DinoBloom predictions (this trains all 3 types of classifiers including XGBoost, light GBM, and random forest):

```bash
python train_leukemia_from_dinobloom.py --backend all --device 0
```

Re-train classifiers only from cached detection features:


#### 5) Full agentic pipeline (detect → aggregate → classify → reflect → report)

Classification + report numbers come only from live detection/aggregation.  
Use a classifier trained with `train_leukemia_from_dinobloom.py` (not stats JSON).

Single patient with reflection + re_aggregate + flag_for_review:

```bash
# sbatch scripts/sbatch_orchestrator.sh
#   export CASE_ID=4 IMAGES_GLOB='wbc_unified/cv/generated/det_dataset/images/test/4_*.png'
#   export CLASSIFIER_MODEL=runs/classifier/random_forest/leukemia_random_forest.pkl
#   export USE_AGENT=1
```

Batch: all 13 test patients with agent traces:

EfficientNet batch:

```bash
python run_orchestrator.py \
  --lld-split test \
  --patients-dir /wbc_unified/cv/generated/det_dataset/images/test \
  --backend wbc-unified \
  --yolo-weights "${YOLO}" \
  --effnet-weights "${EFFNET}" \
  --classifier-model path/to/trained/RF_Classifier.pkl \
  --llm-model /models/Qwen3-VL-4B-Instruct \
  --max-reflect-iterations 2 \
  --device 0 \
  --out outputs/batch_effnet
```

DinoBloom batch:

```bash
python run_orchestrator.py \
  --lld-split test \
  --backend dinobloom \
  --yolo-weights "${YOLO}" \
  --dinobloom-attr-weights "${DINOBLOOM_ATTR}" \
  --classifier-model "${CLASSIFIER}" \
  --llm-model models/Qwen3-VL-4B-Instruct \
  --max-reflect-iterations 2 \
  --report-backend template \
  --device 0 \
  --out outputs/batch_traced
```


#### Summarize reflection actions:

```bash
python analyze_agent_trace.py --agentic-dir outputs/batch_traced
```

---

## Running the pipeline — DinoBloom

```bash
python run_orchestrator.py \
  --lld-split test \
  --backend dinobloom \
  --yolo-weights wbc_unified/cv/runs/detector/train/weights/best.pt \
  --dinobloom-attr-weights /home/roba.majzoub/agentic_hematology/wbc_unified/cv/runs/attribute_dinobloom/train/best_attr_dinobloom.pt \
  --classifier /home/roba.majzoub/agentic_hematology/wbc_unified/cv/runs/classifier/dinobloom/random_forest/leukemia_random_forest.pkl \
  --llm-model /home/roba.majzoub/agentic_hematology/models/Qwen3-VL-4B-Instruct \
  --max-reflect-iterations 2 \
  --device 0 \
  --out outputs/batch_dinobloom
```



## Summarizing results

EfficientNet:

```bash
python summarize_batch_eval.py \
  --output-dir agentic_hematology/outputs/batch_effnet \
  --stats-json data_preprocessing/patient_WBC_stats_NoOveralp.json \
  --approved-reports-dir LLM_reports \
  --non-agentic-dir outputs/batch_effnet_noAgent \
  --out-json agentic_hematology/outputs/effnet_results_summary.json \
  --out-md agentic_hematology/outputs/effnet_results_summary.md
```


Per-patient detection eval:

```bash
python eval_detection_patient.py \
  --results_dir /home/roba.majzoub/agentic_hematology/outputs/batch_effnet/4 \
  --stats_json /home/roba.majzoub/AgenticHematology/data_preprocessing/patient_WBC_stats_NoOveralp.json
```
