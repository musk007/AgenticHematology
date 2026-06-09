# Agentic Hematology Pipeline

An agentic orchestration system for peripheral blood smear analysis. A YOLOv11 localizer detects white blood cells, an EfficientNet attribute classifier describes their morphology, a deterministic rule-based classifier assigns the leukemia subtype, and an optional Qwen3-VL LLM drives intent routing and reflection-based process control.

---

## Environment Setup

All commands must be run from the **repository parent directory** (`/home/roba.majzoub`) with the `agentic` conda environment active.

```bash
source /apps/local/anaconda3.10/bin/activate
conda activate /home/roba.majzoub/envs/agentic
cd /home/roba.majzoub
```

If you see `ImportError: libpython3.10.so.1.0: cannot open shared object file`, run:

```bash
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"
```

---

## Running the Pipeline

### Single patient — non-agentic mode

Deterministic pipeline only. No LLM is loaded. Intent is decided by keyword rules. Reflection is skipped.

```bash
python agentic_hematology/run_orchestrator.py \
  --case-id PATIENT_004 \
  --backend wbc-unified \
  --images agentic_hematology/wbc_unified/cv/generated/patients/patient_4/images \
  --yolo-weights agentic_hematology/wbc_unified/cv/runs/detector/train/weights/best.pt \
  --effnet-weights agentic_hematology/wbc_unified/cv/runs/attribute/train/best_attr.pt \
  --instruction "diagnose this case" \
  --report-backend template \
  --no-agent \
  --out agentic_hematology/outputs
```

### Single patient — agentic mode

Loads a local Qwen3-VL model (with optional LoRA adapter) to drive LLM intent routing and the reflection agent. The model is loaded once and shared across routing, reflection, and report generation.

```bash
python agentic_hematology/run_orchestrator.py \
  --case-id PATIENT_004 \
  --backend wbc-unified \
  --images agentic_hematology/wbc_unified/cv/generated/patients/patient_4/images \
  --yolo-weights agentic_hematology/wbc_unified/cv/runs/detector/train/weights/best.pt \
  --effnet-weights agentic_hematology/wbc_unified/cv/runs/attribute/train/best_attr.pt \
  --instruction "diagnose this case" \
  --report-backend template \
  --llm-model /nfs-stor/roba.majzoub/LLMs/Qwen3-VL-4B-Instruct \
  --lora-adapter /nfs-stor/roba.majzoub/wbc_medical/runs/wbc_sft_only/checkpoints/wbc_qwen3_4b_sft_lora \
  --out agentic_hematology/outputs
```

### Submitting via SLURM

```bash
sbatch agentic_hematology/inference.sh
```

The script activates the conda environment, sets up paths, and submits the agentic single-patient run. Logs are written to `agentic_hematology/logs/`.

### All patients — batch mode

Discovers every subdirectory under `--patients-dir` that contains an `images/` folder and runs them all in one process. The detector, classifier, and LLM are loaded **once** and reused across all patients.

```bash
python agentic_hematology/run_orchestrator.py \
  --patients-dir agentic_hematology/wbc_unified/cv/generated/patients \
  --yolo-weights agentic_hematology/wbc_unified/cv/runs/detector/train/weights/best.pt \
  --effnet-weights agentic_hematology/wbc_unified/cv/runs/attribute/train/best_attr.pt \
  --llm-model /nfs-stor/roba.majzoub/LLMs/Qwen3-VL-4B-Instruct \
  --lora-adapter /nfs-stor/roba.majzoub/wbc_medical/runs/wbc_sft_only/checkpoints/wbc_qwen3_4b_sft_lora \
  --out agentic_hematology/outputs/batch
```

Each patient's outputs are saved to `<out>/<patient_name>/`. Patients with no images are skipped with a warning; errors in individual patients are logged and the batch continues.

---

## Intent Router

The orchestrator classifies the user's `--instruction` into one of five intents and runs only the pipeline stages that intent requires.

| Intent | Triggered by | Pipeline stages | Output files |
|---|---|---|---|
| `FULL_REPORT` | Report-like or default diagnostic prompts (default fallback) | detect → aggregate → classify → reflect → report → validate | `_detections.json`, `_classification.json`, `_report.md` |
| `DETECT_ONLY` | "only detect", "count cells", "localize cells" | detect → aggregate | `_detections.json` |
| `CLASSIFY_ONLY` | "only classify", "just tell me the subtype", "which leukemia" | detect → aggregate → classify | `_detections.json`, `_classification.json` |
| `REPORT_FROM_JSON` | Precomputed findings supplied via API (no images) | load findings → classify → reflect → report → validate | `_classification.json`, `_report.md` |
| `EXPLAIN` | "explain", "why", "justify", "what does X mean" | full pipeline (if images present) + LLM answer | `_explain.txt` (+ report files if pipeline ran) |

**Routing modes:**
- **Non-agentic (`--no-agent`):** keyword/regex rules only — deterministic, no GPU cost.
- **Agentic (default):** the LLM classifies the instruction first; falls back to keyword rules if the LLM call fails or returns an unrecognised label.

The intent can be overridden at the API level by setting `forced_intent` on `OrchestratorRequest`.

### Reflection agent (agentic mode only)

After detect → aggregate → classify, the reflection agent reads the case state and decides one of three process actions before the report is written:

- **`proceed`** — evidence is coherent and sufficient.
- **`re_aggregate`** — re-run aggregation at a stricter confidence threshold, re-classify, and reflect again. Used when detection quality looks noisy. Can only be used once per case.
- **`flag_for_review`** — mark the case for mandatory human review. Written as a banner at the bottom of the report.

The reflection agent never modifies the diagnosis — the deterministic classifier is always authoritative.

---

## Output Files

All files are written to `--out` (or `--out/<patient_name>/` in batch mode). If `--out` is not set, results are printed to the terminal instead.

| File | Contents |
|---|---|
| `case_<id>_detections.json` | `patient_id`, `n_images`, and per cell: `cell_id`, `image_id`, `bbox_xyxy`, `class`, `confidence`, binarised `attributes`, raw `attribute_probs` |
| `case_<id>_classification.json` | `patient_id`, `predicted_class`, `confidence`, `rationale` |
| `case_<id>_report.md` | Full narrative Markdown report with quantitative summary, agentic diagnosis, and cell grounding |
| `case_<id>_explain.txt` | LLM free-text answer (EXPLAIN intent only) |

---

## Key CLI Arguments

| Argument | Description |
|---|---|
| `--case-id` | Case identifier for single-patient mode |
| `--patients-dir` | Root directory for batch mode (`--case-id` and `--patients-dir` are mutually exclusive) |
| `--backend` | `wbc-unified` (default), `two-stage`, or `stub` |
| `--images` | Image paths or glob for single-patient mode |
| `--yolo-weights` | Path to YOLOv11 detection weights |
| `--effnet-weights` | Path to EfficientNet attribute classifier weights |
| `--instruction` | Free-text instruction that drives intent routing (default: `"diagnose this case"`) |
| `--report-backend` | `template` (default), `local-llm`, `claude`, `openai` |
| `--llm-model` | Path to local Qwen3 base model (required for agentic mode) |
| `--lora-adapter` | Path to LoRA adapter checkpoint (optional) |
| `--no-agent` | Disable LLM routing and reflection; use keyword rules only |
| `--max-reflect-iterations` | Max reflection loop iterations before forced escalation (default: 2) |
| `--out` | Output directory |

---

## Training the Leukemia Classifier

Detection and attribute weights are frozen. Only the downstream rule-based / learned classifier is trained.

```bash
# Option 1 — direct
python agentic_hematology/Train_pipeline.py \
  --data-root /nfs-stor/roba.majzoub/LeukemiaDataset_Organized \
  --device 0 \
  --det-weights agentic_hematology/wbc_unified/cv/runs/detector/train/weights/best.pt \
  --attr-weights agentic_hematology/wbc_unified/cv/runs/attribute/train/best_attr.pt

# Option 2 — SLURM
sbatch agentic_hematology/train_agentic_pipeline.sh
```
