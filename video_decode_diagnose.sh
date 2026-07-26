#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "사용법: qwen-review-video-decode-diagnose /path/to/video.mp4" >&2
  exit 2
fi

HOST_ROOT="${VLLM_REVIEW_HOST_MEDIA_ROOT:-$HOME/local-ai}"
ENGINE_DIR="${VIDEO_ENGINE_ROOT:-$HOME/local-ai/video-engine}"
SOURCE="$(realpath "$1")"

case "$SOURCE" in
  "$HOST_ROOT"/*) ;;
  *)
    echo "영상이 공유 루트 밖에 있습니다: $SOURCE" >&2
    echo "공유 루트: $HOST_ROOT" >&2
    exit 3
    ;;
esac

RELATIVE="${SOURCE#"$HOST_ROOT"/}"
CONTAINER_PATH="/review-media/$RELATIVE"
IMAGE="$(docker inspect qwen-review --format '{{.Config.Image}}')"

echo "Image          : $IMAGE"
echo "Host video     : $SOURCE"
echo "Container video: $CONTAINER_PATH"
echo

docker run --rm \
  --entrypoint python3 \
  -v "$HOST_ROOT:/review-media:ro" \
  -v "$ENGINE_DIR/video_decode_probe.py:/diag/video_decode_probe.py:ro" \
  "$IMAGE" \
  /diag/video_decode_probe.py \
  "$CONTAINER_PATH"
