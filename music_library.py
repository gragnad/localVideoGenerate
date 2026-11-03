"""Completed music registry. No generation, GPU access, source deletion, or project ownership."""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from job_queue import atomic_write_json, now_iso, queue_claim_lock


EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
TEXT_FIELDS = {"title": 300, "description": 20000, "mood": 1000, "genre": 1000,
               "instruments": 2000, "use_case": 4000, "model": 1000, "prompt": 100000,
               "workflow": 2000, "license_note": 4000, "generated_at": 100}


def tracks_root(root: Path) -> Path:
    return root / "runtime/music_library/tracks"


def folder(root: Path, track_id: str) -> Path:
    if not isinstance(track_id, str) or not re.fullmatch(r"music_[0-9a-f]{32}", track_id):
        raise ValueError("유효하지 않은 음악 ID입니다.")
    base = tracks_root(root).resolve()
    target = base / track_id
    if target.is_symlink() or target.resolve().parent != base:
        raise ValueError("음악 저장소 밖의 경로입니다.")
    return target


def metadata(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("음악 설명은 JSON 객체여야 합니다.")
    unknown = set(raw) - set(TEXT_FIELDS) - {"tags", "instrumental", "bpm", "seed"}
    if unknown:
        raise ValueError("알 수 없는 설명 항목: " + ", ".join(sorted(unknown)))
    result = {}
    for key, limit in TEXT_FIELDS.items():
        value = raw.get(key, "")
        if not isinstance(value, str) or len(value) > limit or "\0" in value:
            raise ValueError(f"{key} 항목의 형식 또는 길이를 확인하세요.")
        result[key] = value.strip()
    if not result["title"] or not result["description"]:
        raise ValueError("음악 제목(title)과 설명(description)을 입력하세요.")
    tags = raw.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 100 or any(not isinstance(t, str) or not t.strip() or len(t) > 100 or "\0" in t for t in tags):
        raise ValueError("tags는 100개 이하의 짧은 문자열 목록이어야 합니다.")
    result["tags"] = list(dict.fromkeys(t.strip() for t in tags))
    instrumental = raw.get("instrumental")
    if instrumental is not None and not isinstance(instrumental, bool):
        raise ValueError("instrumental은 true/false 또는 null이어야 합니다.")
    result["instrumental"] = instrumental
    bpm = raw.get("bpm")
    if bpm is not None and (isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or not math.isfinite(bpm) or bpm <= 0):
        raise ValueError("bpm은 양수 또는 null이어야 합니다.")
    result["bpm"] = bpm  # User-supplied musical intent; never presented as measured BPM.
    seed = raw.get("seed", "")
    if isinstance(seed, bool) or not isinstance(seed, (str, int)) or len(str(seed)) > 100:
        raise ValueError("seed는 짧은 문자열 또는 정수여야 합니다.")
    result["seed"] = str(seed)
    return result


def read_record(root: Path, track_id: str) -> dict:
    target = folder(root, track_id) / "track.json"
    if target.is_symlink():
        raise ValueError("음악 설명 파일의 경로가 올바르지 않습니다.")
    record = json.loads(target.read_text(encoding="utf-8"))
    if (not isinstance(record, dict) or record.get("schema_version") != 1 or record.get("track_id") != track_id
            or not isinstance(record.get("metadata"), dict) or not isinstance(record.get("audio"), dict)
            or not isinstance(record.get("created_at"), str) or not record["created_at"]):
        raise ValueError("음악 등록 정보가 손상되었습니다.")
    metadata(record["metadata"])
    audio = record["audio"]
    if (audio.get("filename") not in {"audio" + ext for ext in EXTENSIONS}
            or any(isinstance(audio.get(key), bool) or not isinstance(audio.get(key), (int, float))
                   or not math.isfinite(audio[key]) or audio[key] <= 0
                   for key in ("duration_seconds", "sample_rate", "channels", "size_bytes"))
            or not isinstance(audio.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", audio["sha256"])):
        raise ValueError("음악 파일 정보가 손상되었습니다.")
    return record


def media_path(root: Path, record: dict) -> Path:
    directory = folder(root, record["track_id"])
    name = record["audio"].get("filename", "")
    if name not in {"audio" + ext for ext in EXTENSIONS}:
        raise ValueError("음악 파일 이름이 올바르지 않습니다.")
    target = directory / name
    if target.is_symlink() or target.resolve().parent != directory.resolve():
        raise ValueError("음악 저장소 밖의 파일입니다.")
    if not target.is_file():
        raise FileNotFoundError("등록된 음악 원본 파일이 없습니다.")
    return target


def records(root: Path) -> tuple[list[dict], int]:
    values, invalid = [], 0
    for path in tracks_root(root).glob("music_*"):
        try:
            values.append(read_record(root, path.name))
        except (ValueError, OSError, TypeError):
            invalid += 1
    return values, invalid


def public_record(root: Path, record: dict) -> dict:
    try:
        media_path(root, record)
        available = True
    except (OSError, ValueError):
        available = False
    return {"track_id": record["track_id"], "created_at": record["created_at"],
            "metadata": record["metadata"], "audio": record["audio"], "available": available}


def listing(root: Path, data: dict) -> dict:
    rows, invalid = records(root)
    query = str(data.get("q") or "").strip().casefold()
    if query:
        rows = [r for r in rows if query in json.dumps(r["metadata"], ensure_ascii=False).casefold()]
    if data.get("sort") == "name":
        rows.sort(key=lambda r: (r["metadata"]["title"].casefold(), r["track_id"]))
    else:
        rows.sort(key=lambda r: (r["created_at"], r["track_id"]), reverse=True)
    size = max(1, min(100, int(data.get("page_size") or 24)))
    pages = max(1, (len(rows) + size - 1) // size)
    page = max(1, min(pages, int(data.get("page") or 1)))
    return {"tracks": [public_record(root, r) for r in rows[(page - 1) * size:page * size]],
            "pagination": {"page": page, "total_pages": pages, "total": len(rows)}, "invalid_count": invalid}


def download(root: Path, data: dict) -> dict:
    record = read_record(root, data.get("track_id"))
    path = media_path(root, record)
    title = re.sub(r'[\x00-\x1f\x7f/\\<>:"|?*]', "_", record["metadata"]["title"]).strip(". ")[:120] or "music"
    return {"path": str(path), "filename": title + path.suffix}


def probe_audio(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                            capture_output=True, text=True, timeout=60, check=True)
    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not audio or any(s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic") for s in streams):
        raise ValueError("완성된 오디오 전용 파일을 지정하세요.")
    duration = float(info.get("format", {}).get("duration") or audio.get("duration") or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("음악의 실제 재생 길이를 확인할 수 없습니다.")
    return {"duration_seconds": duration, "sample_rate": int(audio.get("sample_rate") or 0),
            "channels": int(audio.get("channels") or 0), "codec": audio.get("codec_name", "")}


def register(root: Path, source: Path, raw: dict) -> dict:
    meta = metadata(raw)
    source = source.expanduser().resolve(strict=True)
    extension = source.suffix.lower()
    if not source.is_file() or extension not in EXTENSIONS:
        raise ValueError("지원 파일: WAV, MP3, FLAC, OGG, M4A")
    base = tracks_root(root)
    with queue_claim_lock(base):
        staging = Path(tempfile.mkdtemp(prefix=".import-", dir=base))
        try:
            target = staging / ("audio" + extension)
            before = source.stat()
            shutil.copyfile(source, target)
            after = source.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError("복사 중 원본이 변경됐습니다. 생성 완료 후 다시 등록하세요.")
            audio = probe_audio(target)
            digest = hashlib.sha256()
            with target.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            checksum = digest.hexdigest()
            identity = hashlib.sha256((checksum + json.dumps(meta, ensure_ascii=False, sort_keys=True)).encode()).hexdigest()
            existing, _ = records(root)
            for record in existing:
                if record.get("identity") == identity:
                    media_path(root, record)  # Do not silently return a broken previous import.
                    return {"track": public_record(root, record), "already_exists": True}
            track_id = "music_" + uuid.uuid4().hex
            record = {"schema_version": 1, "track_id": track_id, "created_at": now_iso(), "identity": identity,
                      "metadata": meta, "audio": {**audio, "filename": target.name, "size_bytes": target.stat().st_size, "sha256": checksum}}
            atomic_write_json(staging / "track.json", record)
            staging.rename(folder(root, track_id))  # Publish only after both media and metadata are complete.
            return {"track": public_record(root, record), "already_exists": False}
        finally:
            if staging.exists():
                shutil.rmtree(staging)  # Only this newly-created import staging folder; never the source.
