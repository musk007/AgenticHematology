#!/usr/bin/env bash
# Stop leftover Ray / vLLM processes after a failed GRPO run
set -euo pipefail
echo "Stopping Ray ..."
ray stop --force 2>/dev/null || true
pkill -u "$(whoami)" -f 'ray::' 2>/dev/null || true
pkill -u "$(whoami)" -f 'raylet' 2>/dev/null || true
pkill -u "$(whoami)" -f 'gcs_server' 2>/dev/null || true
pkill -u "$(whoami)" -f 'vllm::' 2>/dev/null || true
pkill -u "$(whoami)" -f 'vLLMHttpServer' 2>/dev/null || true
pkill -u "$(whoami)" -f 'verl.trainer.main_ppo' 2>/dev/null || true
echo "Ray cleanup done."
