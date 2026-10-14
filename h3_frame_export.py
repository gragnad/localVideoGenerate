from __future__ import annotations

"""Extract fixed-interval still frames from completed H3 videos for offline markup."""

import hashlib
import json
import re
import shutil
import subprocess
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path
from typing import Any

import h3_queue
from job_queue import atomic_write_json, now_iso, read_json


EXPORT_VERSION = 2
INTERVALS = {"0.25": Fraction(1, 4), "0.5": Fraction(1, 2), "1": Fraction(1)}
MAX_FRAMES = 400
PREVIEW_WIDTH = 360
FFMPEG_TIMEOUT_SECONDS = 180
LABEL_FONT_CANDIDATES = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)


def exports_root(root: Path) -> Path:
    return root / "runtime/h3/frame_exports"


def interval_tag(interval: str) -> str:
    return f"{interval.replace('.', 'p')}s"


def _interval(value: Any) -> tuple[str, Fraction]:
    text = str(value if value is not None else "").strip()
    try:
        normalized = format(float(text), "g")
    except ValueError:
        normalized = text
    if normalized not in INTERVALS:
        raise ValueError("프레임 간격은 0.25, 0.5, 1초 중 하나여야 합니다.")
    return normalized, INTERVALS[normalized]


def _file_label(value: Any, fallback: str) -> str:
    label = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._-")
    return label[:80] or fallback


def _probe(video: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,avg_frame_rate,r_frame_rate,nb_frames",
            "-show_entries", "format=duration", "-of", "json", str(video),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"영상 정보를 읽지 못했습니다: {completed.stderr.strip()[:300]}")
    payload = json.loads(completed.stdout or "{}")
    stream = (payload.get("streams") or [{}])[0]
    fps = Fraction(0)
    for key in ("avg_frame_rate", "r_frame_rate"):
        try:
            fps = Fraction(str(stream.get(key) or "0/1"))
        except (ValueError, ZeroDivisionError):
            continue
        if fps > 0:
            break
    if fps <= 0:
        raise RuntimeError("영상 FPS를 확인하지 못했습니다.")
    duration = float((payload.get("format") or {}).get("duration") or 0)
    try:
        frame_count = int(stream.get("nb_frames") or 0)
    except ValueError:
        frame_count = 0
    if frame_count <= 0:
        frame_count = int(duration * fps)
    if frame_count <= 0:
        raise RuntimeError("영상 프레임 수를 확인하지 못했습니다.")
    return {
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "fps": fps,
        "duration_seconds": duration,
        "frame_count": frame_count,
    }


def _frame_indices(frame_count: int, fps: Fraction, interval: Fraction) -> list[int]:
    """Nearest source frame for every interval tick that lies inside the video."""
    indices: list[int] = []
    tick = 0
    while True:
        index = round(tick * interval * fps)
        if index >= frame_count:
            break
        if not indices or index != indices[-1]:
            indices.append(index)
        tick += 1
        if len(indices) > MAX_FRAMES:
            raise ValueError(
                f"추출 프레임이 {MAX_FRAMES}장을 넘습니다. 더 큰 간격을 선택하세요."
            )
    return indices


def _label_text(clip: str, candidate: Any, seconds: float, index: int) -> str:
    parts = [clip]
    if candidate:
        parts.append(f"cand{candidate}")
    parts += [f"t={seconds:.3f}s", f"f{index:04d}"]
    return "   ".join(parts)


def _burn_label(source: Path, target: Path, text: str, height: int) -> None:
    """Append a caption strip below the frame so the picture itself stays uncovered."""
    bar = max(28, round(height * 0.06))
    font_size = max(14, round(bar * 0.55))
    text_file = target.with_suffix(".label.txt")
    text_file.write_text(text, encoding="utf-8")
    font = next((path for path in LABEL_FONT_CANDIDATES if path.is_file()), None)
    drawtext = [
        f"textfile={text_file}",
        "fontcolor=white",
        f"fontsize={font_size}",
        f"x={max(8, bar // 3)}",
        f"y=h-{bar}+({bar}-text_h)/2",
    ]
    if font:
        drawtext.insert(0, f"fontfile={font}")
    try:
        completed = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                "-vf", f"pad=iw:ih+{bar}:0:0:black,drawtext={':'.join(drawtext)}",
                "-frames:v", "1", str(target),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        text_file.unlink(missing_ok=True)
    if completed.returncode != 0 or not target.is_file():
        raise RuntimeError(
            f"프레임 시간 표시를 넣지 못했습니다: {completed.stderr.strip()[:300]}"
        )


def _frame_files(frame: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(frame.get(key) or "")
        for key in ("filename", "labeled_filename", "preview_filename")
    )


def _zip_files(manifest: dict[str, Any]) -> set[str]:
    return {
        str(name)
        for name in (
            manifest.get("zip_filename"),
            manifest.get("labeled_zip_filename"),
            *(manifest.get("selection_zips") or []),
        )
        if name
    }


def _public(export_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return {**manifest, "export_dir": str(export_dir)}


def _is_fresh(manifest: dict[str, Any], video: Path, export_dir: Path) -> bool:
    if manifest.get("export_version") != EXPORT_VERSION:
        return False
    try:
        info = video.stat()
    except OSError:
        return False
    if (
        manifest.get("source_video_path") != str(video)
        or manifest.get("source_video_size") != info.st_size
        or manifest.get("source_video_mtime_ns") != info.st_mtime_ns
    ):
        return False
    names = [manifest.get("zip_filename"), manifest.get("labeled_zip_filename")] + [
        name for frame in manifest.get("frames") or [] for name in _frame_files(frame)
    ]
    return all(name and (export_dir / str(name)).is_file() for name in names)


def export_frames(root: Path, job_id: str, interval: Any) -> dict[str, Any]:
    interval_text, interval_value = _interval(interval)
    video = h3_queue.video_path(root, job_id)
    job_dir = h3_queue.roots(root)["jobs"] / job_id
    request = read_json(job_dir / "request.json", {}) or {}
    tag = interval_tag(interval_text)
    export_dir = exports_root(root) / job_id / tag
    existing = read_json(export_dir / "frames.json", {}) or {}
    if existing and _is_fresh(existing, video, export_dir):
        return _public(export_dir, {**existing, "cached": True})

    probe = _probe(video)
    fps: Fraction = probe["fps"]
    indices = _frame_indices(probe["frame_count"], fps, interval_value)
    clip = _file_label(request.get("source_clip_id"), "direct")
    candidate = request.get("candidate_index")
    prefix = f"{clip}_cand{candidate}" if candidate else clip
    zip_filename = f"{prefix}_{job_id}_frames_{tag}.zip"
    labeled_zip_filename = f"{prefix}_{job_id}_frames_{tag}_labeled.zip"

    work = export_dir.parent / f".{tag}.{uuid.uuid4().hex}.tmp"
    work.mkdir(parents=True)
    try:
        select = "+".join(f"eq(n\\,{index})" for index in indices)
        completed = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
                "-filter_complex",
                f"[0:v]select='{select}',split=2[full][small];"
                f"[small]scale='min({PREVIEW_WIDTH},iw)':-2[preview]",
                "-map", "[full]", "-fps_mode", "passthrough", str(work / "full_%04d.png"),
                "-map", "[preview]", "-fps_mode", "passthrough", "-q:v", "4",
                str(work / "preview_%04d.jpg"),
            ],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"ffmpeg 프레임 추출에 실패했습니다: {completed.stderr.strip()[:500]}"
            )
        produced = sorted(work.glob("full_*.png"))
        if len(produced) != len(indices):
            raise RuntimeError(
                f"추출된 프레임 수가 예상과 다릅니다: {len(produced)}/{len(indices)}"
            )
        frames: list[dict[str, Any]] = []
        for order, index in enumerate(indices, start=1):
            seconds = float(Fraction(index) / fps)
            stem = f"{prefix}_t{seconds:07.3f}s_f{index:04d}"
            full = work / f"full_{order:04d}.png"
            preview = work / f"preview_{order:04d}.jpg"
            full.rename(work / f"{stem}.png")
            preview.rename(work / f"{stem}_preview.jpg")
            frames.append({
                "order": order,
                "frame_index": index,
                "time_seconds": round(seconds, 3),
                "filename": f"{stem}.png",
                "labeled_filename": f"{stem}_label.png",
                "label_text": _label_text(clip, candidate, seconds, index),
                "preview_filename": f"{stem}_preview.jpg",
                "size_bytes": (work / f"{stem}.png").stat().st_size,
            })
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(
                lambda frame: _burn_label(
                    work / frame["filename"],
                    work / frame["labeled_filename"],
                    frame["label_text"],
                    probe["height"],
                ),
                frames,
            ))
        info = video.stat()
        manifest = {
            "export_version": EXPORT_VERSION,
            "job_id": job_id,
            "interval_seconds": interval_text,
            "interval_tag": tag,
            "source_video_path": str(video),
            "source_video_size": info.st_size,
            "source_video_mtime_ns": info.st_mtime_ns,
            "width": probe["width"],
            "height": probe["height"],
            "fps": float(fps),
            "duration_seconds": round(probe["duration_seconds"], 3),
            "source_frame_count": probe["frame_count"],
            "candidate_set_id": request.get("candidate_set_id"),
            "candidate_index": candidate,
            "source_project_id": request.get("source_project_id"),
            "source_scene_id": request.get("source_scene_id"),
            "source_clip_id": request.get("source_clip_id"),
            "seed": request.get("seed_text", request.get("seed")),
            "zip_filename": zip_filename,
            "labeled_zip_filename": labeled_zip_filename,
            "frames": frames,
            "created_at": now_iso(),
        }
        atomic_write_json(work / "frames.json", manifest)
        for name, key in ((zip_filename, "filename"), (labeled_zip_filename, "labeled_filename")):
            with zipfile.ZipFile(work / name, "w", zipfile.ZIP_STORED) as archive:
                archive.write(work / "frames.json", "frames.json")
                for frame in frames:
                    archive.write(work / frame[key], frame[key])
        manifest["zip_size_bytes"] = (work / zip_filename).stat().st_size
        manifest["labeled_zip_size_bytes"] = (work / labeled_zip_filename).stat().st_size
        atomic_write_json(work / "frames.json", manifest)

        if export_dir.exists():
            stale = export_dir.parent / f".{tag}.{uuid.uuid4().hex}.old"
            export_dir.rename(stale)
            shutil.rmtree(stale, ignore_errors=True)
        work.rename(export_dir)
    finally:
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
    return _public(export_dir, {**manifest, "cached": False})


def selection_zip(
    root: Path, job_id: str, tag: str, filenames: Any, labeled: bool = False,
) -> dict[str, Any]:
    """Bundle only the frames the user picked; the full export stays untouched."""
    job_id = h3_queue._safe_id(job_id, "작업 ID")
    if tag not in {interval_tag(value) for value in INTERVALS}:
        raise FileNotFoundError("프레임 추출 간격을 찾을 수 없습니다.")
    export_dir = exports_root(root) / job_id / tag
    manifest = read_json(export_dir / "frames.json", {}) or {}
    frames = {str(frame.get("filename")): frame for frame in manifest.get("frames") or []}
    if not frames:
        raise FileNotFoundError("먼저 프레임을 추출하세요.")
    if not isinstance(filenames, list) or not filenames:
        raise ValueError("다운로드할 프레임을 한 장 이상 선택하세요.")
    picked = sorted(
        {str(name) for name in filenames},
        key=lambda name: int((frames.get(name) or {}).get("frame_index") or 0),
    )
    missing = [name for name in picked if name not in frames]
    if missing:
        raise ValueError(f"추출 목록에 없는 프레임입니다: {missing[0]}")
    digest = hashlib.sha256("\n".join(picked).encode("utf-8")).hexdigest()[:10]
    base = str(manifest.get("zip_filename") or f"{job_id}_frames_{tag}.zip")
    variant = "_labeled" if labeled else ""
    zip_filename = (
        base.removesuffix(".zip") + f"_selected{len(picked)}{variant}_{digest}.zip"
    )
    file_key = "labeled_filename" if labeled else "filename"
    if any(not frames[name].get(file_key) for name in picked):
        raise FileNotFoundError("시간 표시 프레임이 없습니다. 프레임을 다시 추출하세요.")
    target = export_dir / zip_filename
    if not target.is_file():
        temporary = export_dir / f".{zip_filename}.{uuid.uuid4().hex}.tmp"
        selected_manifest = {
            **{key: value for key, value in manifest.items() if key != "selection_zips"},
            "frames": [frames[name] for name in picked],
            "selected_from_zip": manifest.get(
                "labeled_zip_filename" if labeled else "zip_filename"
            ),
            "labeled": labeled,
        }
        try:
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_STORED) as archive:
                archive.writestr(
                    "frames.json",
                    json.dumps(selected_manifest, ensure_ascii=False, indent=2),
                )
                for name in picked:
                    member = str(frames[name][file_key])
                    archive.write(export_dir / member, member)
            temporary.rename(target)
        finally:
            temporary.unlink(missing_ok=True)
    selections = [
        name for name in manifest.get("selection_zips") or [] if name != zip_filename
    ]
    manifest["selection_zips"] = selections + [zip_filename]
    atomic_write_json(export_dir / "frames.json", manifest)
    return {
        "job_id": job_id,
        "interval_tag": tag,
        "zip_filename": zip_filename,
        "frame_count": len(picked),
        "labeled": labeled,
        "size_bytes": target.stat().st_size,
    }


def export_file(root: Path, job_id: str, tag: str, filename: str) -> Path:
    job_id = h3_queue._safe_id(job_id, "작업 ID")
    if tag not in {interval_tag(value) for value in INTERVALS}:
        raise FileNotFoundError("프레임 추출 간격을 찾을 수 없습니다.")
    if Path(filename).name != filename or filename.startswith("."):
        raise FileNotFoundError("허용되지 않은 프레임 파일입니다.")
    export_dir = exports_root(root) / job_id / tag
    manifest = read_json(export_dir / "frames.json", {}) or {}
    allowed = _zip_files(manifest) | {
        name for frame in manifest.get("frames") or [] for name in _frame_files(frame)
    }
    path = export_dir / filename
    if filename not in allowed or not path.is_file():
        raise FileNotFoundError("추출된 프레임 파일을 찾을 수 없습니다.")
    return path
