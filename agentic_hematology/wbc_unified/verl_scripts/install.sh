#!/usr/bin/env bash
# =============================================================================
# wbc_unified LLM stack install (SFT + GRPO | Qwen3.5-2B | cu129 torch + vLLM wheel)
# Run once on a GPU node with conda env activated.
#
# Usage:
#   conda activate SLA_Det
#   cd wbc_unified
#   bash verl_scripts/install.sh          # full install (default)
#   bash verl_scripts/install.sh patch    # re-apply verl/vllm patches only
#   INSTALL_FLASH_ATTN=1 bash verl_scripts/install.sh
#
# Optional: VLLM_VERSION=0.21.0 | VLLM_CUDA=129 | DRY_RUN=1
# vLLM 0.21 wheels are cu129/cu130 only; keep torch and vLLM on the same CUDA build
# Do not module load cuda before GRPO (pollutes LD_LIBRARY_PATH)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERL_SRC="${VERL_SRC:-$(cd "$ROOT/.." && pwd)/third_party/verl}"
# shellcheck source=env.sh
source "$ROOT/verl_scripts/env.sh"

MODE="${1:-all}"
VLLM_VERSION="${VLLM_VERSION:-0.21.0}"
VLLM_CUDA="${VLLM_CUDA:-129}"
TORCH_INDEX="${TORCH_INDEX:-https://download.pytorch.org/whl/cu${VLLM_CUDA}}"
VLLM_WHEEL_INDEX="${VLLM_WHEEL_INDEX:-https://wheels.vllm.ai/${VLLM_VERSION}/cu${VLLM_CUDA}}"
TRANSFORMERS_SPEC="${TRANSFORMERS_SPEC:-transformers>=5.6,<6.0}"
DRY_RUN="${DRY_RUN:-0}"
INSTALL_FLASH_ATTN="${INSTALL_FLASH_ATTN:-0}"

run_pip() {
  if [ "$DRY_RUN" = "1" ]; then echo "[dry-run] pip $*"; return 0; fi
  pip "$@"
}

patch_fsdp_utils() {
  local FSDP_UTILS="${VERL_SRC}/verl/utils/fsdp_utils.py"
  [ -f "$FSDP_UTILS" ] || { echo "Missing $FSDP_UTILS"; exit 1; }
  if grep -q 'from __future__ import annotations' "$FSDP_UTILS"; then
    echo "patch ok (fsdp): already applied"
    return 0
  fi
  python3 - "$FSDP_UTILS" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
needle = "# limitations under the License.\n\nimport functools"
if needle not in text:
    sys.exit(f"unexpected file layout: {path}")
text = text.replace(
    needle,
    "# limitations under the License.\n\nfrom __future__ import annotations\n\nimport functools",
    1,
)
old = """elif version.parse(torch.__version__) >= version.parse("2.4"):
    from torch.distributed._composable.fsdp import CPUOffloadPolicy, FSDPModule, MixedPrecisionPolicy, fully_shard

    fully_shard_module = torch.distributed._composable.fsdp
else:"""
new = """elif version.parse(torch.__version__) >= version.parse("2.4"):
    from torch.distributed._composable.fsdp import CPUOffloadPolicy, FSDPModule, MixedPrecisionPolicy, fully_shard

    fully_shard_module = torch.distributed._composable.fsdp
    try:
        from torch.distributed.tensor import DTensor, Shard
        from torch.distributed.tensor._dtensor_spec import DTensorSpec
    except ImportError:
        DTensor = None  # type: ignore[misc, assignment]
        DTensorSpec = None  # type: ignore[misc, assignment]
else:"""
if old not in text:
    sys.exit(f"unexpected elif block in {path}")
path.write_text(text.replace(old, new, 1))
print(f"Patched {path}")
PY
}

patch_verl_vllm_server() {
  local TARGET="${VERL_SRC}/verl/workers/rollout/vllm_rollout/vllm_async_server.py"
  [ -f "$TARGET" ] || { echo "Missing $TARGET"; exit 1; }
  python3 - "$TARGET" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
changed = False
if "VERL_VLLM07_COMPAT" not in text:
    old_import = "from vllm.entrypoints.cli.serve import run_headless"
    new_import = """# VERL_VLLM07_COMPAT
try:
    from vllm.entrypoints.cli.serve import run_headless
except ImportError:
    from vllm.entrypoints.cli.serve import run_server as run_headless"""
    if old_import not in text:
        sys.exit(f"import line not found in {path}")
    text = text.replace(old_import, new_import, 1)
    changed = True
    old_mm = """        # Don't keep the dummy data in memory
        await engine_client.reset_mm_cache()"""
    new_mm = """        # Don't keep the dummy data in memory (vllm>=0.9)
        if _VLLM_VERSION >= version.parse("0.9.0") and hasattr(engine_client, "reset_mm_cache"):
            await engine_client.reset_mm_cache()"""
    if old_mm not in text:
        sys.exit(f"reset_mm_cache block not found in {path}")
    text = text.replace(old_mm, new_mm, 1)
    changed = True
if "VERL_VLLM_LEGACY_CLI" not in text:
    if "def _filter_vllm_legacy_cli_args" not in text:
        fn_anchor = 'if _VLLM_VERSION >= version.parse("0.13.0"):\n    _RESET_PREFIX_CACHE_KWARGS["reset_connector"] = True\n\n\n'
        fn_block = (
            fn_anchor
            + "def _filter_vllm_legacy_cli_args(args: dict[str, Any]) -> dict[str, Any]:\n"
            + '    """Drop vLLM serve flags that only exist in newer releases."""\n'
            + "    out = dict(args)\n"
            + '    if _VLLM_VERSION < version.parse("0.8.5"):\n'
            + '        out.pop("worker_extension_cls", None)\n'
            + '    if _VLLM_VERSION < version.parse("0.9.0"):\n'
            + '        out.pop("logprobs_mode", None)\n'
            + "    return out\n\n\n"
        )
        if fn_anchor not in text:
            sys.exit(f"fn anchor not found in {path}")
        text = text.replace(fn_anchor, fn_block, 1)
        changed = True
    old_line = '        server_args = ["serve", self.model_config.local_path] + build_cli_args_from_config(args)'
    new_line = (
        "        args = _filter_vllm_legacy_cli_args(args)\n"
        "        # VERL_VLLM_LEGACY_CLI\n"
        + old_line
    )
    if old_line not in text:
        sys.exit(f"server_args line not found in {path}")
    text = text.replace(old_line, new_line, 1)
    changed = True
if "VERL_SKIP_TOKENIZER_FROM_CONFIG" not in text:
    old_skip = '"skip_tokenizer_init": False,'
    new_skip = '"skip_tokenizer_init": self.config.skip_tokenizer_init,  # VERL_SKIP_TOKENIZER_FROM_CONFIG'
    if old_skip not in text:
        sys.exit(f"skip_tokenizer_init line not found in {path}")
    text = text.replace(old_skip, new_skip, 1)
    changed = True
if changed:
    path.write_text(text)
    print(f"Patched {path}")
else:
    print(f"patch ok (vllm server): already applied")
PY
}

patch_vllm_tokenizer_compat() {
  python3 - <<'PY'
import sys
from pathlib import Path
try:
    import vllm
    from packaging import version
    if version.parse(vllm.__version__) >= version.parse("0.19.0"):
        print(f"skip tokenizer patch (vllm {vllm.__version__} >= 0.19)")
        sys.exit(0)
except Exception as e:
    print(f"warn: cannot check vllm version: {e}")
import vllm.transformers_utils.tokenizer as m
path = Path(m.__file__)
text = path.read_text()
marker = "VERL_VLLM_TF5_TOKENIZER"
if marker in text:
    print(f"patch ok (tokenizer): already applied")
    sys.exit(0)
old = """    tokenizer_all_special_tokens_extended = (
        tokenizer.all_special_tokens_extended)"""
new = """    # VERL_VLLM_TF5_TOKENIZER: transformers>=5 removed all_special_tokens_extended
    tokenizer_all_special_tokens_extended = getattr(
        tokenizer, "all_special_tokens_extended", None
    ) or getattr(tokenizer, "all_special_tokens", [])"""
if old not in text:
    print(f"skip tokenizer patch (block not in {path})")
    sys.exit(0)
path.write_text(text.replace(old, new, 1))
print(f"Patched {path}")
PY
}

patch_fsdp_layered_summon() {
  local FSDP_UTILS="${VERL_SRC}/verl/utils/fsdp_utils.py"
  [ -f "$FSDP_UTILS" ] || { echo "Missing $FSDP_UTILS"; exit 1; }
  if grep -q "VERL_LAYERED_SUMMON_FIX" "$FSDP_UTILS"; then
    echo "patch ok (layered_summon): already applied"
    return 0
  fi
  python3 - "$FSDP_UTILS" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
old = """                    sub_lora_params = {
                        f\"{prefix}.{name}\": param.full_tensor().detach().cpu()
                        if hasattr(param, \"full_tensor\")
                        else param.detach().cpu()
                        for name, param in sub_lora_params.items()
                    }"""
new = """                    # VERL_LAYERED_SUMMON_FIX: get_peft_model_state_dict keys are already fully qualified
                    sub_lora_params = {
                        param_name: param.full_tensor().detach().cpu()
                        if hasattr(param, \"full_tensor\")
                        else param.detach().cpu()
                        for param_name, param in sub_lora_params.items()
                    }"""
if old not in text:
    sys.exit(f"layered_summon block not found in {path}")
path.write_text(text.replace(old, new, 1))
print(f"Patched layered_summon in {path}")
PY
}

patch_verl_vllm_lora_preload() {
  local TARGET="${VERL_SRC}/verl/workers/rollout/vllm_rollout/vllm_async_server.py"
  [ -f "$TARGET" ] || { echo "Missing $TARGET"; exit 1; }
  if grep -q "_ensure_lora_loaded" "$TARGET"; then
    echo "patch ok (vllm lora preload): already applied"
    return 0
  fi
  python3 - "$TARGET" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
anchor = "    async def collective_rpc(\n"
insert = '''    async def _ensure_lora_loaded(self) -> bool:
        """Preload SFT adapter from disk when IPC tensor sync has not registered LoRA yet."""
        if not self.lora_as_adapter:
            return True
        try:
            loras = await self.engine.list_loras()
        except Exception as e:
            logger.warning("vLLM list_loras failed: %s", e)
            loras = set()
        if VLLM_LORA_INT_ID in loras:
            return True
        adapter_path = getattr(self.model_config, "lora_adapter_path", None)
        if not adapter_path:
            logger.error(
                "vLLM rollout: LoRA id=%s missing and lora_adapter_path unset; using BASE model.",
                VLLM_LORA_INT_ID,
            )
            return False
        from verl.utils.fs import copy_to_local

        local_path = copy_to_local(adapter_path, use_shm=getattr(self.model_config, "use_shm", False))
        logger.info("vLLM preload LoRA from %s (int_id=%s)", local_path, VLLM_LORA_INT_ID)
        ok = await self.engine.add_lora(
            LoRARequest(
                lora_name=VLLM_LORA_NAME,
                lora_int_id=VLLM_LORA_INT_ID,
                lora_path=local_path,
            )
        )
        if not ok:
            logger.error("vLLM add_lora failed: path=%s", local_path)
            return False
        loras = await self.engine.list_loras()
        if VLLM_LORA_INT_ID not in loras:
            logger.error(
                "vLLM add_lora ok but id=%s not in list_loras=%s",
                VLLM_LORA_INT_ID,
                loras,
            )
            return False
        logger.info("vLLM LoRA ready: list_loras=%s", loras)
        return True

'''
if anchor not in text:
    sys.exit(f"collective_rpc anchor not found in {path}")
text = text.replace(anchor, insert + anchor, 1)
# Remove premature LoRA preload (engine not assigned yet)
bad_early = '''        )
        if self.lora_as_adapter and getattr(self.model_config, "lora_adapter_path", None):
            await self._ensure_lora_loaded()

        build_app_sig'''
good_early = '''        )

        build_app_sig'''
if bad_early in text:
    text = text.replace(bad_early, good_early, 1)
old_monkey = '''        await engine_client.collective_rpc(
            method="monkey_patch_model", kwargs={"vocab_size": len(self.model_config.tokenizer)}
        )

        build_app_sig = inspect.signature(build_app)'''
new_monkey = '''        await engine_client.collective_rpc(
            method="monkey_patch_model", kwargs={"vocab_size": len(self.model_config.tokenizer)}
        )

        build_app_sig = inspect.signature(build_app)'''
old_engine = '''        self.engine = engine_client
        self._server_port, self._server_task = await run_uvicorn(app, args, self._server_address)'''
new_engine = '''        self.engine = engine_client
        if self.lora_as_adapter and getattr(self.model_config, "lora_adapter_path", None):
            await self._ensure_lora_loaded()
        self._server_port, self._server_task = await run_uvicorn(app, args, self._server_address)'''
if old_monkey not in text:
    sys.exit(f"monkey_patch block not found in {path}")
text = text.replace(old_monkey, new_monkey, 1)
if old_engine in text:
    text = text.replace(old_engine, new_engine, 1)
elif "await self._ensure_lora_loaded()" in text and "self.engine = engine_client" in text:
    pass  # already fixed placement
else:
    sys.exit(f"engine assignment block not found in {path}")
old_gen = '''        if self.lora_as_adapter:
            # Make sure we also check that the lora is already loaded in the engine
            lora_loaded = VLLM_LORA_INT_ID in await self.engine.list_loras()
            if lora_loaded:
                lora_request = LoRARequest(
                    lora_name=VLLM_LORA_NAME, lora_int_id=VLLM_LORA_INT_ID, lora_path=VLLM_LORA_PATH
                )'''
new_gen = '''        if self.lora_as_adapter:
            await self._ensure_lora_loaded()
            loras = await self.engine.list_loras()
            if VLLM_LORA_INT_ID in loras:
                lora_request = LoRARequest(
                    lora_name=VLLM_LORA_NAME, lora_int_id=VLLM_LORA_INT_ID, lora_path=VLLM_LORA_PATH
                )
            else:
                logger.warning(
                    "vLLM generate WITHOUT LoRA (list_loras=%s); reward may be 0.",
                    loras,
                )'''
if old_gen not in text:
    sys.exit(f"generate lora block not found in {path}")
path.write_text(text.replace(old_gen, new_gen, 1))
print(f"Patched vLLM LoRA preload in {path}")
PY
}

apply_patches() {
  echo "========== verl / vllm patches =========="
  patch_fsdp_utils
  patch_fsdp_layered_summon
  patch_verl_vllm_server
  patch_verl_vllm_lora_preload
  patch_vllm_tokenizer_compat
}

install_verl_editable() {
  if [ ! -d "$VERL_SRC/.git" ]; then
    git clone --depth 1 https://github.com/verl-project/verl.git "$VERL_SRC"
  fi
  run_pip install --no-deps -e "$VERL_SRC"
}

install_python_deps() {
  run_pip install -r "$ROOT/report/requirements.txt"
  run_pip install --upgrade ${TRANSFORMERS_SPEC}
}

install_vllm_stack() {
  echo "========== uninstall old torch / vllm / nvidia =========="
  run_pip uninstall -y vllm xformers 2>/dev/null || true
  run_pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
  run_pip uninstall -y \
    nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 nvidia-cuda-nvrtc-cu12 nvidia-cuda-runtime-cu12 \
    nvidia-cudnn-cu12 nvidia-cufft-cu12 nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 \
    nvidia-nccl-cu12 nvidia-nvjitlink-cu12 nvidia-nvtx-cu12 2>/dev/null || true
  run_pip uninstall -y \
    nvidia-cublas-cu13 nvidia-cuda-cupti-cu13 nvidia-cuda-nvrtc-cu13 nvidia-cuda-runtime-cu13 \
    nvidia-cudnn-cu13 nvidia-cufft-cu13 nvidia-curand-cu13 nvidia-cusolver-cu13 nvidia-cusparse-cu13 \
    nvidia-nccl-cu13 nvidia-nvjitlink-cu13 nvidia-nvtx-cu13 2>/dev/null || true

  echo "========== vLLM ${VLLM_VERSION} (cu${VLLM_CUDA} wheel) + matching torch =========="
  echo "  wheel index: ${VLLM_WHEEL_INDEX}"
  echo "  torch index: ${TORCH_INDEX}"
  run_pip install \
    --extra-index-url "${VLLM_WHEEL_INDEX}" \
    --extra-index-url "${TORCH_INDEX}" \
    --upgrade "vllm==${VLLM_VERSION}"
  run_pip install --upgrade ${TRANSFORMERS_SPEC}

  if [ "$INSTALL_FLASH_ATTN" = "1" ]; then
    echo "========== flash-attn (optional) =========="
    run_pip install flash-attn --no-build-isolation || echo "flash-attn install failed; retry later"
  fi
}

verify_install() {
  [ "$DRY_RUN" = "1" ] && { echo "DRY_RUN=1 skip verification"; return 0; }
  echo "========== verify =========="
  command -v nvidia-smi >/dev/null && nvidia-smi -L || echo "warn: no nvidia-smi (ok on login node)"
  setup_vllm_cuda_path
  [ -n "${VLLM_CUDA_LIB_PATH:-}" ] || echo "warn: pip torch/lib not found (re-source env.sh or reinstall vLLM stack)"
  python3 - <<PY
import os, sys
sys.path.insert(0, "${VERL_SRC}")
import torch, transformers, vllm
from packaging import version
from transformers import AutoConfig
from transformers.models.auto.configuration_auto import CONFIG_MAPPING
print("torch", torch.__version__, "| cuda", torch.version.cuda)
assert transformers.__version__.startswith("5.")
assert "qwen3_5" in CONFIG_MAPPING
assert version.parse(vllm.__version__) >= version.parse("0.19.0")
from vllm.v1.engine.async_llm import AsyncLLM
cfg = AutoConfig.from_pretrained(os.environ["MODEL_PATH"], trust_remote_code=True)
print("vllm", vllm.__version__, "| model", cfg.model_type)
import verl.trainer.sft_trainer
import verl.trainer.main_ppo
from verl.workers.rollout.vllm_rollout import vllm_async_server
print("verl + rollout OK")
PY
}

case "$MODE" in
  patch)
    apply_patches
    exit 0
    ;;
  all|"")
    echo "========== report_llm full install =========="
    [ -f "$MODEL_PATH/config.json" ] || { echo "Missing model: $MODEL_PATH"; exit 1; }
    python3 -c "import sys; print('python', sys.version.split()[0])"
    install_python_deps
    install_verl_editable
    install_vllm_stack
    apply_patches
    setup_vllm_cuda_path
    verify_install
    echo ""
    echo "Done. Train: bash verl_scripts/train.sh data|sft|grpo|all"
    echo "Before GRPO: bash verl_scripts/cleanup_ray.sh && RAY_CPUS=16 bash verl_scripts/train.sh grpo"
    echo "E2E check: python scripts/11_verify_e2e_setup.py"
    echo "Full pipeline: export CONFIRM_FULL_RETRAIN=1 && sbatch ../sbatch_medical_full_pipeline.sh"
    ;;
  *)
    echo "Usage: $0 [all|patch]"
    exit 1
    ;;
esac
