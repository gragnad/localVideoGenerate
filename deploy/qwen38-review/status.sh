#!/usr/bin/env bash
set -Eeuo pipefail

config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/h3-video-engine"
env_file="$config_dir/qwen38-review.env"
set -a
source "$env_file"
set +a

systemctl --user --no-pager --full status qwen38-review.service || true
curl -fsS "http://${QWEN38_HOST}:${QWEN38_PORT}/v1/models" || true
