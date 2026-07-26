from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class VideoAssemblerError(RuntimeError):
    pass


def probe_video(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "duration_seconds": None,
        "fps": None,
        "width": None,
        "height": None,
    }
    if not path.is_file():
        raise VideoAssemblerError(f"영상 파일을 찾을 수 없습니다: {path}")
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height,r_frame_rate",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except FileNotFoundError as exc:
        raise VideoAssemblerError("ffprobe 명령을 찾지 못했습니다.") from exc
    if proc.returncode != 0:
        raise VideoAssemblerError(
            "ffprobe 실패:\n" + (proc.stderr or proc.stdout)[-4000:]
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise VideoAssemblerError("ffprobe JSON 해석 실패") from exc

    duration = (payload.get("format") or {}).get("duration")
    if duration is not None:
        result["duration_seconds"] = round(float(duration), 3)

    for stream in payload.get("streams") or []:
        if stream.get("codec_type") != "video":
            continue
        result["width"] = int(stream.get("width") or 0) or result["width"]
        result["height"] = int(stream.get("height") or 0) or result["height"]
        rate = str(stream.get("r_frame_rate") or "")
        if "/" in rate:
            num, den = rate.split("/", 1)
            den_value = float(den or 1)
            if den_value:
                result["fps"] = round(float(num) / den_value, 3)
        break
    return result


def _run_ffmpeg(command: list[str], label: str) -> None:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise VideoAssemblerError(f"{label} 시간 초과") from exc
    if proc.returncode != 0:
        raise VideoAssemblerError(
            f"{label} 실패:\n" + (proc.stderr or proc.stdout)[-8000:]
        )


def trim_clip(
    *,
    source: Path,
    start_seconds: float,
    end_seconds: float,
    output: Path,
    fps: int,
) -> None:
    duration = float(end_seconds) - float(start_seconds)
    if duration <= 0:
        raise VideoAssemblerError("클립 길이는 0보다 커야 합니다.")
    output.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{float(start_seconds):.3f}",
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-r",
            str(int(fps)),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ],
        "클립 자르기",
    )


def concat_clips(*, clip_paths: list[Path], output: Path) -> None:
    if not clip_paths:
        raise VideoAssemblerError("합성할 클립이 없습니다.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
        list_path = Path(handle.name)
        for clip in clip_paths:
            escaped = str(clip.resolve()).replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")
    try:
        _run_ffmpeg(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output),
            ],
            "클립 이어붙이기",
        )
    finally:
        list_path.unlink(missing_ok=True)


def assemble_clips(
    *,
    clips: list[dict[str, Any]],
    output: Path,
    work_dir: Path,
    fps: int,
) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    trimmed: list[Path] = []
    details: list[dict[str, Any]] = []
    for index, clip in enumerate(clips, 1):
        source = Path(str(clip["source_path"]))
        start = float(clip["start_seconds"])
        end = float(clip["end_seconds"])
        trimmed_path = work_dir / f"clip_{index:02d}.mp4"
        trim_clip(
            source=source,
            start_seconds=start,
            end_seconds=end,
            output=trimmed_path,
            fps=fps,
        )
        trimmed.append(trimmed_path)
        details.append(
            {
                "source_job_id": clip.get("source_job_id"),
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": round(end - start, 3),
                "trimmed_path": str(trimmed_path),
            }
        )
    concat_clips(clip_paths=trimmed, output=output)
    summary = probe_video(output)
    summary["clip_details"] = details
    summary["output_path"] = str(output)
    return summary
