#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(uname -m)" != "aarch64" ]]; then
  echo "이 설치 구성은 DGX Spark aarch64 호스트용입니다." >&2
  exit 1
fi

source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target_dir="$HOME/local-ai/review-qwen38"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/h3-video-engine"
service_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
bin_dir="$HOME/bin"

mkdir -p "$target_dir" "$config_dir" "$service_dir" "$bin_dir"
install -m 0755 "$source_dir/create-container.sh" "$target_dir/create-container.sh"
install -m 0755 "$source_dir/start.sh" "$target_dir/start.sh"
install -m 0755 "$source_dir/stop.sh" "$target_dir/stop.sh"
install -m 0755 "$source_dir/status.sh" "$target_dir/status.sh"
if [[ ! -f "$config_dir/qwen38-review.env" ]]; then
  install -m 0600 "$source_dir/qwen38-review.env.example" "$config_dir/qwen38-review.env"
fi
install -m 0644 "$source_dir/qwen38-review.service" "$service_dir/qwen38-review.service"
install -m 0755 "$source_dir/ai-start-vllm" "$bin_dir/ai-start-vllm"
install -m 0755 "$source_dir/ai-stop-vllm" "$bin_dir/ai-stop-vllm"
systemctl --user daemon-reload

echo "Qwen3.8 review service files installed"
echo "Next: docker pull lmsysorg/sglang:qwen38-27b"
echo "Then: $target_dir/create-container.sh"
