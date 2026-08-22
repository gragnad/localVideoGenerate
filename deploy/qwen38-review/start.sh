#!/usr/bin/env bash
set -Eeuo pipefail

config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/h3-video-engine"
env_file="$config_dir/qwen38-review.env"
set -a
source "$env_file"
set +a

"$HOME/bin/ai-stop-comfy" >/dev/null 2>&1 || true
systemctl --user stop qwen-review-omni-local.service >/dev/null 2>&1 || true
docker stop --timeout "$QWEN38_STOP_TIMEOUT" qwen-review-omni-local >/dev/null 2>&1 || true

systemctl --user reset-failed qwen38-review.service >/dev/null 2>&1 || true
systemctl --user start qwen38-review.service

deadline=$((SECONDS + QWEN38_START_TIMEOUT))
while (( SECONDS < deadline )); do
  if response="$(curl -fsS "http://${QWEN38_HOST}:${QWEN38_PORT}/v1/models" 2>/dev/null)"; then
    if [[ "$response" == *"$QWEN38_MODEL"* ]]; then
      echo "Qwen3.8 visual review API ready"
      exit 0
    fi
  fi

  if ! systemctl --user is-active --quiet qwen38-review.service; then
    echo "Qwen3.8 서비스가 모델 초기화 중 종료되었습니다." >&2
    journalctl --user -u qwen38-review.service -n 240 --no-pager
    exit 1
  fi
  sleep 5
done

echo "Qwen3.8 시작 시간 초과: ${QWEN38_START_TIMEOUT}s" >&2
exit 1
