#!/usr/bin/env bash
# GRPO + LoRA on Qwen3.5-2B + SFT adapter
# verl hybrid engine requires rollout: vllm/sglang/trtllm + mode=async
# Usage: bash verl_scripts/run_grpo.sh
# Prerequisite: bash verl_scripts/install.sh

set -euo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="$PROJECT/report"
cd "$REPORT"
# shellcheck source=env.sh
source "$PROJECT/verl_scripts/env.sh"

REWARD_FN="${REWARD_FN:-$PROJECT/verl_scripts/reward_report_e2e.py}"
BASE_MODEL="${BASE_MODEL:-$MODEL_PATH}"
LORA_ADAPTER="${LORA_ADAPTER:-$SFT_LORA_ADAPTER}"
LORA_ADAPTER="${LORA_ADAPTER:-${SFT_CHECKPOINT:+${SFT_CHECKPOINT}/lora_adapter}}"
# vLLM language_model_only requires LM-only adapter (no visual.* keys)
if [ -f "${LORA_ADAPTER%/}_vllm/adapter_model.safetensors" ]; then
  export VLLM_LORA_ADAPTER="${LORA_ADAPTER%/}_vllm"
elif [ -f "${VLLM_LORA_ADAPTER}/adapter_model.safetensors" ]; then
  :
else
  export VLLM_LORA_ADAPTER="${LORA_ADAPTER}"
fi
ROLLOUT_BACKEND="${ROLLOUT_BACKEND:-vllm}"

TRAIN_FILE="${TRAIN_FILE:-$REPORT_LLM_ARTIFACT_ROOT/data/verl/grpo_e2e/train.parquet}"
VAL_FILE="${VAL_FILE:-$REPORT_LLM_ARTIFACT_ROOT/data/verl/grpo_e2e/val.parquet}"
SAVE_DIR="${SAVE_DIR:-$GRPO_SAVE_DIR}"

[ -f "$BASE_MODEL/config.json" ] || { echo "Missing base model: $BASE_MODEL"; exit 1; }
[ -f "$LORA_ADAPTER/adapter_config.json" ] || {
  echo "Missing LoRA adapter: $LORA_ADAPTER"
  echo "Run SFT first, then: bash verl_scripts/export_lora.sh 50"
  exit 1
}
[ -f "$TRAIN_FILE" ] || { echo "Missing $TRAIN_FILE — run: bash verl_scripts/train.sh data"; exit 1; }

python3 -c "import ${ROLLOUT_BACKEND}" 2>/dev/null || {
  echo "Missing rollout backend: ${ROLLOUT_BACKEND}"
  echo "Run: bash verl_scripts/install.sh"
  exit 1
}

# Cap Ray CPUs on Slurm nodes with few allocated CPUs
RAY_CPUS="${RAY_CPUS:-${SLURM_CPUS_PER_TASK:-8}}"
REWARD_WORKERS="${REWARD_WORKERS:-2}"
DATALOADER_WORKERS="${DATALOADER_WORKERS:-2}"

if [ "${CLEAN_RAY:-1}" != "0" ]; then
  bash "$PROJECT/verl_scripts/cleanup_ray.sh" || true
fi
ulimit -u 65535 2>/dev/null || ulimit -u 8192 2>/dev/null || true
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export VLLM_USE_V1="${VLLM_USE_V1:-1}"
setup_vllm_cuda_path
# Ray workers need the same LD_LIBRARY_PATH as the driver (incl. libnvidia-ml)
RAY_LD_LIBRARY_PATH="${RAY_LD_LIBRARY_PATH:-${VERL_LD_LIBRARY_PATH:-${LD_LIBRARY_PATH:-}}}"

# Keep response length modest for text-only reports (GT reports ~400-600 tokens)
MAX_RESPONSE_LENGTH="${MAX_RESPONSE_LENGTH:-768}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-$(( ${MAX_PROMPT_LENGTH:-3072} + ${MAX_RESPONSE_LENGTH} ))}"
ROLLOUT_TEMPERATURE="${ROLLOUT_TEMPERATURE:-0.8}"
ROLLOUT_REPETITION_PENALTY="${ROLLOUT_REPETITION_PENALTY:-1.08}"
GRPO_FRESH_START="${GRPO_FRESH_START:-0}"
ROLLOUT_LANGUAGE_MODEL_ONLY="${ROLLOUT_LANGUAGE_MODEL_ONLY:-true}"
ATTN_IMPLEMENTATION="${ATTN_IMPLEMENTATION:-sdpa}"
ROLLOUT_ENFORCE_EAGER="${ROLLOUT_ENFORCE_EAGER:-true}"
VLLM_ATTENTION_BACKEND="${VLLM_ATTENTION_BACKEND:-TRITON_ATTN}"

mkdir -p "$SAVE_DIR"
echo "GRPO LoRA: base=${BASE_MODEL} actor_adapter=${LORA_ADAPTER} vllm_adapter=${VLLM_LORA_ADAPTER} rollout=${ROLLOUT_BACKEND} -> ${SAVE_DIR}"
echo "Ray CPUs=${RAY_CPUS} reward_workers=${REWARD_WORKERS} dataloader_workers=${DATALOADER_WORKERS}"
echo "vLLM rollout: enforce_eager=${ROLLOUT_ENFORCE_EAGER} attention=${VLLM_ATTENTION_BACKEND}"
echo "max_response=${MAX_RESPONSE_LENGTH} temp=${ROLLOUT_TEMPERATURE} rep_penalty=${ROLLOUT_REPETITION_PENALTY} fresh_start=${GRPO_FRESH_START}"
echo "Ray LD_LIBRARY_PATH: ${RAY_LD_LIBRARY_PATH}"

GRPO_RESUME_ARGS=()
if [ "${GRPO_FRESH_START}" = "1" ]; then
  GRPO_RESUME_ARGS+=(trainer.resume_mode=disable)
  echo "GRPO_FRESH_START=1: no GRPO resume; initialize from SFT LoRA only"
fi

python3 -m verl.trainer.main_ppo \
  "${GRPO_RESUME_ARGS[@]}" \
  algorithm.adv_estimator=grpo \
  data.train_files="${TRAIN_FILE}" \
  data.val_files="${VAL_FILE}" \
  data.train_batch_size="${TRAIN_BATCH_SIZE:-4}" \
  data.max_prompt_length="${MAX_PROMPT_LENGTH:-3072}" \
  data.max_response_length="${MAX_RESPONSE_LENGTH}" \
  data.filter_overlong_prompts=True \
  data.dataloader_num_workers="${DATALOADER_WORKERS}" \
  data.truncation=error \
  "+data.apply_chat_template_kwargs.enable_thinking=false" \
  algorithm.use_kl_in_reward=False \
  actor_rollout_ref.model.path="${BASE_MODEL}" \
  actor_rollout_ref.model.lora_adapter_path="${LORA_ADAPTER}" \
  actor_rollout_ref.model.lora_rank="${LORA_RANK}" \
  actor_rollout_ref.model.lora_alpha="${LORA_ALPHA}" \
  actor_rollout_ref.model.trust_remote_code=True \
  actor_rollout_ref.model.use_remove_padding=True \
  actor_rollout_ref.model.enable_gradient_checkpointing=True \
  "+actor_rollout_ref.model.override_config.attn_implementation=${ATTN_IMPLEMENTATION}" \
  actor_rollout_ref.actor.optim.lr="${ACTOR_LR:-5e-6}" \
  actor_rollout_ref.actor.ppo_mini_batch_size="${PPO_MINI_BATCH_SIZE:-4}" \
  actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu="${PPO_MICRO_BATCH_SIZE_PER_GPU:-1}" \
  actor_rollout_ref.actor.use_kl_loss=True \
  actor_rollout_ref.actor.kl_loss_coef=0.001 \
  actor_rollout_ref.actor.kl_loss_type=low_var_kl \
  actor_rollout_ref.actor.entropy_coeff=0 \
  actor_rollout_ref.actor.fsdp_config.param_offload="${ACTOR_PARAM_OFFLOAD:-true}" \
  actor_rollout_ref.actor.fsdp_config.model_dtype=bf16 \
  actor_rollout_ref.actor.fsdp_config.optimizer_offload=False \
  actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu="${LOG_PROB_MICRO_BATCH_SIZE_PER_GPU:-2}" \
  actor_rollout_ref.rollout.tensor_model_parallel_size="${ROLLOUT_TP:-1}" \
  actor_rollout_ref.rollout.name="${ROLLOUT_BACKEND}" \
  actor_rollout_ref.rollout.mode=async \
  actor_rollout_ref.rollout.load_format=safetensors \
  actor_rollout_ref.rollout.layered_summon="${ROLLOUT_LAYERED_SUMMON:-True}" \
  actor_rollout_ref.rollout.logprobs_mode=null \
  actor_rollout_ref.rollout.gpu_memory_utilization="${ROLLOUT_GPU_MEM:-0.4}" \
  actor_rollout_ref.rollout.max_model_len="${MAX_MODEL_LEN}" \
  actor_rollout_ref.rollout.enforce_eager="${ROLLOUT_ENFORCE_EAGER}" \
  actor_rollout_ref.rollout.skip_tokenizer_init=false \
  actor_rollout_ref.rollout.temperature="${ROLLOUT_TEMPERATURE}" \
  "+actor_rollout_ref.rollout.repetition_penalty=${ROLLOUT_REPETITION_PENALTY}" \
  "+actor_rollout_ref.rollout.engine_kwargs.vllm.language_model_only=${ROLLOUT_LANGUAGE_MODEL_ONLY}" \
  "+actor_rollout_ref.rollout.engine_kwargs.vllm.generation_config=vllm" \
  "+actor_rollout_ref.rollout.engine_kwargs.vllm.attention_config.backend=${VLLM_ATTENTION_BACKEND}" \
  "+actor_rollout_ref.rollout.engine_kwargs.vllm.compilation_config.cudagraph_mode=NONE" \
  actor_rollout_ref.rollout.n="${ROLLOUT_N:-4}" \
  actor_rollout_ref.rollout.agent.num_workers="${ROLLOUT_AGENT_WORKERS:-2}" \
  actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu="${LOG_PROB_MICRO_BATCH_SIZE_PER_GPU:-2}" \
  actor_rollout_ref.ref.fsdp_config.param_offload=True \
  trainer.critic_warmup=0 \
  trainer.logger='["console"]' \
  trainer.project_name=leukemia_report_grpo \
  trainer.experiment_name="${VERL_RUN_TAG}" \
  trainer.n_gpus_per_node="${NGPUS_PER_NODE:-${NGPUS:-4}}" \
  trainer.nnodes="${NNODES:-1}" \
  trainer.default_local_dir="${SAVE_DIR}" \
  trainer.save_freq="${SAVE_FREQ:-1}" \
  trainer.test_freq="${TEST_FREQ:-1}" \
  trainer.log_val_generations="${LOG_VAL_GENERATIONS:-2}" \
  trainer.total_epochs="${TOTAL_EPOCHS:-3}" \
  ray_kwargs.ray_init.num_cpus="${RAY_CPUS}" \
  '+ray_kwargs.ray_init.runtime_env.env_vars.VLLM_USE_V1="1"' \
  "+ray_kwargs.ray_init.runtime_env.env_vars.LD_LIBRARY_PATH=\"${RAY_LD_LIBRARY_PATH}\"" \
  '+ray_kwargs.ray_init.runtime_env.env_vars.CUDA_MODULE_LOADING="LAZY"' \
  reward.num_workers="${REWARD_WORKERS}" \
  custom_reward_function.path="${REWARD_FN}" \
  custom_reward_function.name=compute_score \
  "$@"
