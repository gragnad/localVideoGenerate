#!/usr/bin/env bash
set -Eeuo pipefail

config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/h3-video-engine"
env_file="$config_dir/qwen38-review.env"
set -a
source "$env_file"
set +a

if docker inspect "$QWEN38_CONTAINER" >/dev/null 2>&1; then
  docker stop --timeout "$QWEN38_STOP_TIMEOUT" "$QWEN38_CONTAINER" >/dev/null 2>&1 || true
  docker rm "$QWEN38_CONTAINER" >/dev/null
fi

mkdir -p "$QWEN38_HF_CACHE"

docker create \
  --name "$QWEN38_CONTAINER" \
  --gpus all \
  --network host \
  --ipc host \
  --shm-size 32g \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  --entrypoint python3 \
  -e HF_HOME=/root/.cache/huggingface \
  -e TRANSFORMERS_CACHE=/root/.cache/huggingface \
  -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e PYTHONNOUSERSITE=1 \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -v "$QWEN38_HF_CACHE:/root/.cache/huggingface" \
  "$QWEN38_IMAGE" \
  -m sglang.launch_server \
    --model-path "$QWEN38_MODEL" \
    --host "$QWEN38_HOST" \
    --port "$QWEN38_PORT" \
    --tp-size 1 \
    --context-length "$QWEN38_CONTEXT_LENGTH" \
    --mem-fraction-static "$QWEN38_MEM_FRACTION" \
    --max-running-requests "${QWEN38_MAX_RUNNING_REQUESTS:-2}" \
    --chunked-prefill-size 8192 \
    --attention-backend flashinfer \
    --mm-feature-transport cpu \
    --disable-prefill-cuda-graph \
    --reasoning-parser qwen3 \
    --tool-call-parser qwen3_coder \
    --trust-remote-code

docker inspect "$QWEN38_CONTAINER" \
  --format 'Container={{.Name}} Image={{.Config.Image}} Status={{.State.Status}}'
