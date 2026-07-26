#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from video_sequence import (
    prepare_video_jpeg_sequence,
    public_sequence_summary,
)


BASE = os.environ.get(
    "VLLM_URL",
    "http://127.0.0.1:8091",
).rstrip("/")
MAX_FRAMES = int(
    os.environ.get(
        "VLLM_REVIEW_VIDEO_MAX_FRAMES",
        "32",
    )
)
MAX_WIDTH = int(
    os.environ.get(
        "VLLM_REVIEW_VIDEO_MAX_WIDTH",
        "768",
    )
)
JPEG_QUALITY = int(
    os.environ.get(
        "VLLM_REVIEW_VIDEO_JPEG_QUALITY",
        "4",
    )
)


def model_id() -> str:
    with urlopen(
        f"{BASE}/v1/models",
        timeout=30,
    ) as response:
        payload = json.loads(
            response.read().decode("utf-8")
        )
    data = payload.get("data") or []
    if not data:
        raise RuntimeError(
            "vLLM 모델 목록이 비어 있습니다."
        )
    return str(data[0]["id"])


parser = argparse.ArgumentParser(
    description=(
        "Qwen3-Omni video/jpeg frame sequence smoke test"
    )
)
parser.add_argument(
    "video",
    help="검사할 로컬 영상 경로",
)
args = parser.parse_args()

video = Path(args.video).expanduser().resolve()
if not video.is_file():
    raise SystemExit(
        f"영상 파일이 없습니다: {video}"
    )

sequence = prepare_video_jpeg_sequence(
    video,
    max_frames=MAX_FRAMES,
    max_width=MAX_WIDTH,
    jpeg_quality=JPEG_QUALITY,
    cache_dir=video.parent / "review_video_frames_smoke",
)
summary = public_sequence_summary(sequence)
model = model_id()

print(f"모델: {model}")
print(f"원본 영상: {video}")
print("전송 방식: data:video/jpeg;base64")
print(
    f"샘플 프레임: {summary['sample_count']} / "
    f"{summary['total_num_frames']}"
)
print(
    f"원본 FPS: {summary['original_fps']:.6f}"
)
print(
    f"길이: {summary['duration_seconds']:.6f}"
)
print(
    f"JPEG 합계: {summary['total_jpeg_bytes']} bytes"
)
print(
    f"data URL 길이: {summary['data_url_length']}"
)
print(
    f"캐시 재사용: {summary['cache_reused']}"
)

payload = {
    "model": model,
    "temperature": 0,
    "max_tokens": 700,
    "media_io_kwargs": sequence[
        "media_io_kwargs"
    ],
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "video_url",
                    "video_url": {
                        "url": sequence["data_url"],
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "이 입력은 원본 영상에서 시간순으로 "
                        "균등 추출한 JPEG 프레임 시퀀스입니다. "
                        "프레임 순서와 제공된 시간 메타데이터를 "
                        "사용해 주된 움직임과 카메라 변화를 "
                        "관찰하세요. 샘플 사이의 동작은 추측하지 "
                        "마세요. 반드시 다음 JSON만 출력하세요: "
                        '{"video_loaded":true,'
                        '"summary_ko":"...",'
                        '"temporal_event_count":0}'
                    ),
                },
            ],
        }
    ],
}

request = Request(
    f"{BASE}/v1/chat/completions",
    data=json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
    },
    method="POST",
)

try:
    with urlopen(
        request,
        timeout=1200,
    ) as response:
        body = json.loads(
            response.read().decode("utf-8")
        )
except HTTPError as exc:
    detail = exc.read().decode(
        "utf-8",
        errors="replace",
    )
    print(
        f"JPEG 시퀀스 영상 smoke test 실패 "
        f"HTTP {exc.code}:\n{detail}",
        file=sys.stderr,
    )
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        file=sys.stderr,
    )
    raise SystemExit(1)

print(
    json.dumps(
        body,
        ensure_ascii=False,
        indent=2,
    )
)

message = (
    (body.get("choices") or [{}])[0]
    .get("message")
    or {}
)
if not any(
    isinstance(message.get(key), str)
    and message.get(key).strip()
    for key in (
        "content",
        "reasoning",
        "reasoning_content",
    )
):
    raise SystemExit(
        "영상 요청은 성공했지만 모델 본문이 비어 있습니다."
    )

print(
    "\nQwen3-Omni JPEG 시퀀스 영상 입력 성공"
)
