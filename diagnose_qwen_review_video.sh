#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "사용법: qwen-review-pyav-diagnose /path/to/review_source_video.mp4" >&2
  exit 2
fi

HOST_ROOT="${VLLM_REVIEW_HOST_MEDIA_ROOT:-$HOME/local-ai}"
SOURCE="$(realpath "$1")"
IMAGE="${QWEN_REVIEW_PYAV_IMAGE:-nalstudio/qwen3-omni-vllm:26.06-cu-seqlens-fix-v3-pyav}"
ENGINE_DIR="${VIDEO_ENGINE_ROOT:-$HOME/local-ai/video-engine}"

case "$SOURCE" in
  "$HOST_ROOT"/*) ;;
  *)
    echo "영상이 공유 루트 밖에 있습니다." >&2
    echo "영상: $SOURCE" >&2
    echo "루트: $HOST_ROOT" >&2
    exit 3
    ;;
esac

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "PyAV 이미지를 찾을 수 없습니다: $IMAGE" >&2
  exit 4
fi

RELATIVE="${SOURCE#"$HOST_ROOT"/}"
CONTAINER_PATH="/review-media/$RELATIVE"

echo "Image          : $IMAGE"
echo "Host video     : $SOURCE"
echo "Container video: $CONTAINER_PATH"
echo

docker run --rm \
  --entrypoint python3 \
  -v "$HOST_ROOT:/review-media:ro" \
  -v "$ENGINE_DIR/verify_video_decode.py:/diag/verify_video_decode.py:ro" \
  "$IMAGE" \
  /diag/verify_video_decode.py \
  "$CONTAINER_PATH"
