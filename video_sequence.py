from __future__ import annotations

import base64
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any


class VideoSequenceError(RuntimeError):
    pass


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fraction(value: Any, default: float = 0.0) -> float:
    text = str(value or "").strip()
    if not text:
        return default
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        den = _safe_float(denominator, 0.0)
        if den == 0:
            return default
        return _safe_float(numerator, 0.0) / den
    return _safe_float(text, default)


def probe_video_for_sequence(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)

    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-count_frames",
                "-show_entries",
                (
                    "stream=index,codec_name,width,height,"
                    "r_frame_rate,avg_frame_rate,nb_frames,"
                    "nb_read_frames,duration:"
                    "format=duration,format_name"
                ),
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError as exc:
        raise VideoSequenceError(
            "ffprobe 명령을 찾지 못했습니다."
        ) from exc

    if proc.returncode != 0:
        raise VideoSequenceError(
            "ffprobe 실패:\n"
            + (proc.stderr or proc.stdout)[-6000:]
        )

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise VideoSequenceError(
            "ffprobe JSON 해석 실패:\n" + proc.stdout[-6000:]
        ) from exc

    streams = payload.get("streams") or []
    if not streams:
        raise VideoSequenceError("영상 스트림을 찾지 못했습니다.")

    stream = streams[0]
    fmt = payload.get("format") or {}

    fps = _fraction(stream.get("avg_frame_rate"), 0.0)
    if fps <= 0:
        fps = _fraction(stream.get("r_frame_rate"), 0.0)

    duration = _safe_float(fmt.get("duration"), 0.0)
    if duration <= 0:
        duration = _safe_float(stream.get("duration"), 0.0)

    total_frames = _safe_int(stream.get("nb_read_frames"), 0)
    if total_frames <= 0:
        total_frames = _safe_int(stream.get("nb_frames"), 0)
    if total_frames <= 0 and fps > 0 and duration > 0:
        total_frames = max(1, int(round(fps * duration)))

    if fps <= 0 and total_frames > 1 and duration > 0:
        fps = total_frames / duration

    if total_frames <= 0:
        raise VideoSequenceError(
            "영상 전체 프레임 수를 결정하지 못했습니다."
        )
    if fps <= 0:
        raise VideoSequenceError("영상 FPS를 결정하지 못했습니다.")
    if duration <= 0:
        duration = total_frames / fps

    return {
        "codec_name": stream.get("codec_name"),
        "width": _safe_int(stream.get("width"), 0),
        "height": _safe_int(stream.get("height"), 0),
        "fps": float(fps),
        "duration": float(duration),
        "total_num_frames": int(total_frames),
        "format_name": fmt.get("format_name"),
    }


def uniform_frame_indices(
    total_num_frames: int,
    max_frames: int,
) -> list[int]:
    if total_num_frames <= 0:
        raise ValueError("total_num_frames must be positive")
    if max_frames <= 0:
        raise ValueError("max_frames must be positive")

    count = min(total_num_frames, max_frames)
    if count == 1:
        return [0]

    indices: list[int] = []
    for position in range(count):
        index = round(
            position
            * (total_num_frames - 1)
            / (count - 1)
        )
        if not indices or index != indices[-1]:
            indices.append(index)

    return indices


def _manifest_matches(
    payload: dict[str, Any],
    *,
    source: Path,
    source_stat,
    config: dict[str, Any],
) -> bool:
    return (
        payload.get("source_path") == str(source.resolve())
        and payload.get("source_size_bytes") == source_stat.st_size
        and payload.get("source_mtime_ns") == source_stat.st_mtime_ns
        and payload.get("config") == config
    )


def prepare_video_jpeg_sequence(
    video_path: Path,
    *,
    max_frames: int = 32,
    max_width: int = 768,
    jpeg_quality: int = 4,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    source = video_path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    if max_frames < 2:
        raise ValueError("max_frames must be at least 2")
    if max_width < 64:
        raise ValueError("max_width must be at least 64")
    if not 2 <= jpeg_quality <= 31:
        raise ValueError("jpeg_quality must be between 2 and 31")

    metadata = probe_video_for_sequence(source)
    indices = uniform_frame_indices(
        metadata["total_num_frames"],
        max_frames,
    )

    if cache_dir is None:
        cache_dir = source.parent / "review_video_frames"
    cache_dir = cache_dir.expanduser().resolve()
    manifest_path = cache_dir / "sequence_manifest.json"

    config = {
        "max_frames": max_frames,
        "max_width": max_width,
        "jpeg_quality": jpeg_quality,
        "indices": indices,
    }
    source_stat = source.stat()

    reusable = False
    cached_manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            cached_manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            expected = [
                cache_dir / name
                for name in cached_manifest.get("frame_files") or []
            ]
            reusable = (
                _manifest_matches(
                    cached_manifest,
                    source=source,
                    source_stat=source_stat,
                    config=config,
                )
                and len(expected) == len(indices)
                and all(
                    path.is_file() and path.stat().st_size > 0
                    for path in expected
                )
            )
        except Exception:
            reusable = False

    if not reusable:
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        select_expression = "+".join(
            f"eq(n\\,{index})" for index in indices
        )
        filter_expression = (
            f"select='{select_expression}',"
            f"scale={max_width}:-2:"
            "force_original_aspect_ratio=decrease"
        )
        output_pattern = cache_dir / "frame_%05d.jpg"

        try:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(source),
                    "-map",
                    "0:v:0",
                    "-vf",
                    filter_expression,
                    "-fps_mode",
                    "vfr",
                    "-q:v",
                    str(jpeg_quality),
                    "-frames:v",
                    str(len(indices)),
                    str(output_pattern),
                ],
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
        except FileNotFoundError as exc:
            raise VideoSequenceError(
                "ffmpeg 명령을 찾지 못했습니다."
            ) from exc

        if proc.returncode != 0:
            raise VideoSequenceError(
                "FFmpeg JPEG 프레임 추출 실패:\n"
                + (proc.stderr or proc.stdout)[-10000:]
            )

        frames = sorted(cache_dir.glob("frame_*.jpg"))
        if len(frames) != len(indices):
            raise VideoSequenceError(
                "추출된 JPEG 프레임 수가 예상과 다릅니다. "
                f"expected={len(indices)} actual={len(frames)}"
            )

        frame_files = [path.name for path in frames]
        cached_manifest = {
            "source_path": str(source),
            "source_size_bytes": source_stat.st_size,
            "source_mtime_ns": source_stat.st_mtime_ns,
            "config": config,
            "probe": metadata,
            "frame_files": frame_files,
        }
        manifest_path.write_text(
            json.dumps(
                cached_manifest,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        frames = [
            cache_dir / name
            for name in cached_manifest["frame_files"]
        ]

    encoded_frames = [
        base64.b64encode(path.read_bytes()).decode("ascii")
        for path in frames
    ]
    data_url = (
        "data:video/jpeg;base64,"
        + ",".join(encoded_frames)
    )

    fps = float(metadata["fps"])
    duration = float(metadata["duration"])
    sample_times = [
        round(min(duration, index / fps), 4)
        for index in indices
    ]

    total_jpeg_bytes = sum(path.stat().st_size for path in frames)

    media_io_kwargs = {
        "video": {
            "num_frames": len(frames),
            "fps": fps,
            "frames_indices": indices,
            "total_num_frames": int(
                metadata["total_num_frames"]
            ),
            "duration": duration,
            "do_sample_frames": False,
        }
    }

    return {
        "data_url": data_url,
        "media_io_kwargs": media_io_kwargs,
        "transport": "video/jpeg_base64_sequence",
        "cache_dir": str(cache_dir),
        "manifest_path": str(manifest_path),
        "frame_files": [str(path) for path in frames],
        "sample_count": len(frames),
        "sample_frame_indices": indices,
        "sample_times_seconds": sample_times,
        "original_fps": fps,
        "total_num_frames": int(
            metadata["total_num_frames"]
        ),
        "duration_seconds": duration,
        "source_codec": metadata.get("codec_name"),
        "source_width": metadata.get("width"),
        "source_height": metadata.get("height"),
        "max_width": max_width,
        "jpeg_quality": jpeg_quality,
        "total_jpeg_bytes": total_jpeg_bytes,
        "data_url_length": len(data_url),
        "cache_reused": reusable,
    }


def public_sequence_summary(
    sequence: dict[str, Any],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in sequence.items()
        if key not in {"data_url"}
    }
