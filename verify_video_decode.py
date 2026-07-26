#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import av


path = Path(sys.argv[1])
result: dict[str, object] = {
    "path": str(path),
    "exists": path.is_file(),
    "size_bytes": path.stat().st_size if path.is_file() else 0,
    "pyav_version": av.__version__,
    "h264_available": "h264" in av.codecs_available,
    "container_format": None,
    "video_stream": None,
    "audio_stream_count": 0,
    "decoded_frames": [],
}

if not path.is_file():
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(2)

try:
    with av.open(str(path), mode="r") as container:
        result["container_format"] = container.format.name

        video_streams = list(container.streams.video)
        audio_streams = list(container.streams.audio)
        result["audio_stream_count"] = len(audio_streams)

        if not video_streams:
            raise RuntimeError("영상 스트림이 없습니다.")

        stream = video_streams[0]
        result["video_stream"] = {
            "codec": stream.codec_context.name,
            "width": stream.codec_context.width,
            "height": stream.codec_context.height,
            "average_rate": (
                str(stream.average_rate)
                if stream.average_rate is not None
                else None
            ),
            "frames": stream.frames,
            "duration": stream.duration,
            "time_base": str(stream.time_base),
        }

        decoded = []
        for frame in container.decode(video=0):
            decoded.append(
                {
                    "index": len(decoded),
                    "pts": frame.pts,
                    "time": (
                        float(frame.time)
                        if frame.time is not None
                        else None
                    ),
                    "width": frame.width,
                    "height": frame.height,
                    "format": frame.format.name,
                }
            )
            if len(decoded) >= 3:
                break

        if not decoded:
            raise RuntimeError("PyAV가 영상 프레임을 한 장도 디코딩하지 못했습니다.")

        result["decoded_frames"] = decoded
        result["ok"] = True

except Exception as exc:
    result["ok"] = False
    result["error"] = f"{type(exc).__name__}: {exc}"

print(json.dumps(result, ensure_ascii=False, indent=2))

if not result.get("ok"):
    raise SystemExit(1)
