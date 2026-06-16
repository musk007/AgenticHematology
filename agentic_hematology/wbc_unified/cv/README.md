# NextGen WBC: Detection + Attributes

Two-stage CV pipeline for leukemia peripheral blood smear analysis.

| Stage | Script | Model | Description |
|-------|--------|-------|-------------|
| 0 | `data/prepare_dataset.py` | — | Build YOLO labels + attribute manifest from LLD `attributes/` |
| 1 | `train_detector.py` | **YOLO11** (Ultralytics) | 14-class cell detection |
| 2 | `train_attributes.py` | **EfficientNet-B0** | 6 morphology attributes on GT crops |
| — | `infer.py` / `scripts/pipeline_eval.py` | detector + attribute head | Inference and metrics |

## Data

```bash
export DATA_ROOT=/nfs-stor/zongyan/datasets/medical/LeukemiaDataset_Organized
```

Layout:

```
images/train  images/test
attributes/train  attributes/test   # 12 cols: cls xywh + 6 attributes (0/1/2)
```

Six attribute columns (aligned with report morphology fields). Label value `2` = ignore.

## Quick start

```bash
conda activate SLA_Det
cd nextgen_wbc_pipeline

python data/prepare_dataset.py
python train_detector.py --device 0 --epochs 100 --model yolo11m.pt --batch 16
python train_attributes.py --device 0 --epochs 40 --backbone efficientnet_b0
python infer.py \
  --det-weights runs/detector/train/weights/best.pt \
  --attr-weights runs/attribute/train/best_attr.pt \
  --split test --save-json
```

## Slurm (from repo root)

```bash
export CONFIRM_FULL_RETRAIN=1
sbatch sbatch_medical_stage1.sh
```

## Outputs

- `runs/detector/` — detection weights
- `runs/attribute/` — attribute head
- `runs/predict/infer/test_predictions.json` — consumed by `report_llm`

## Dependencies

- `ultralytics>=8.3.0`
- `torch`, `torchvision`, `timm` (optional)
