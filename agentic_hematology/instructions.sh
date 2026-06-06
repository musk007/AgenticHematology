python3 agentic_hematology/run_orchestrator.py \
  --case-id PATIENT_001 \
  --backend wbc-unified \
  --images "/path/to/patient/images/*.png" \
  --yolo-weights /path/to/yolo/best.pt \
  --effnet-weights /path/to/best_attr.pt \
  --instruction "diagnose this case" \
  --report-backend template \
  --out /path/to/output



python3 agentic_hematology/run_orchestrator.py \
  --case-id PATIENT_001 \
  --backend wbc-unified \
  --images "/path/to/patient/images/*.png" \
  --yolo-weights /path/to/yolo/best.pt \
  --effnet-weights /path/to/best_attr.pt \
  --instruction "diagnose this case" \
  --report-backend local-llm \
  --llm-model /nfs-stor/zongyan/pretrained_models/Qwen3.5-2B \
  --lora-adapter /path/to/lora_adapter \
  --out /path/to/output

if ImportError: libpython3.10.so.1.0: cannot open shared object file: No such file or directory:
use:
    export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"
