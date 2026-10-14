from __future__ import annotations

"""Durable motion-only action reference assets for H3 Director Studio."""

import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

from job_queue import atomic_write_json, now_iso, queue_claim_lock, read_json


ACTION_CATEGORIES = {
    "movement": ["출발", "가속", "전력 질주", "급정지", "도약", "착지", "구르기", "넘어짐", "다시 일어나기"],
    "humanoid_attack": ["찌르기", "양손 내려베기", "양손 대각선 베기", "수평 휘두르기", "전진 타격"],
    "quadruped_attack": ["앞발 타격", "몸통 박치기", "공중 돌진", "꼬리 휘두르기"],
    "tentacle_attack": ["직선 찌르기", "옆으로 휘두르기", "감아 잡기", "잡은 무기 뿌리치기"],
    "evasion": ["옆으로 피하기", "뒤로 피하기", "몸을 낮춰 피하기", "공중 회피"],
    "defense": ["막기", "쳐내기", "무기 붙잡기"],
    "hit_reaction": ["순간 경직", "뒤로 밀림", "중심 상실", "옆으로 구름", "뒤로 넘어짐"],
    "two_participant_combat": ["공격-피격", "공격-회피", "공격-방어", "공격-반격", "붙잡기-탈출", "무기 붙잡기-뿌리치기"],
}
CATEGORY_LABELS = {
    "movement": "이동",
    "humanoid_attack": "인간형 공격",
    "quadruped_attack": "사족형 공격",
    "tentacle_attack": "촉수형 공격",
    "evasion": "회피",
    "defense": "방어",
    "hit_reaction": "피격 반응",
    "two_participant_combat": "두 명 전투",
}
BODY_TYPES = {"humanoid", "small_quadruped", "quadruped", "flying", "tentacle", "other"}
PARTICIPANT_ROLES = {"attacker", "defender", "target", "evader", "counterattacker", "other"}
SOURCE_TYPES = {
    "internal_generated", "direct_upload", "blender_render", "external_licensed",
}
RIGHTS_STATES = {"confirmed", "rights_review_required", "rejected"}
AVAILABILITY_STATES = {"available", "needs_preparation", "rights_review_required"}
ALLOWED_VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
EDITABLE_FIELDS = {
    "title", "description", "category", "action_type", "participant_count",
    "participant_a", "participant_b", "handedness", "weapon_type",
    "attack_start_direction", "attack_end_direction", "screen_direction",
    "timing", "camera", "contact_type", "source_type", "source_url", "blender_source",
    "creator", "license_name", "license_evidence", "downloaded_at",
    "commercial_use_confirmed", "ai_reference_use_confirmed", "rights_state",
    "availability_state", "active", "archived",
}


def asset_root(root: Path) -> Path:
    return root / "runtime/h3/action_assets"


def _safe_id(value: Any, label: str = "액션 자산 ID") -> str:
    text = str(value or "").strip()
    if not text or Path(text).name != text or text in {".", ".."}:
        raise ValueError(f"올바른 {label}이(가) 아닙니다.")
    return text


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rate(value: Any) -> float:
    try:
        return float(Fraction(str(value or "0")))
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe_video(path: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error", "-count_frames",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,nb_read_frames",
                "-of", "json", str(path),
            ],
            capture_output=True, text=True, timeout=60, check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise ValueError("ffprobe로 액션 영상을 검사할 수 없습니다.") from exc
    if proc.returncode != 0:
        raise ValueError("손상되었거나 지원하지 않는 액션 영상입니다.")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("액션 영상 검사 결과를 읽을 수 없습니다.") from exc
    streams = payload.get("streams") or []
    video_streams = [row for row in streams if row.get("codec_type") == "video"]
    if not video_streams:
        raise ValueError("액션 영상에 비디오 스트림이 없습니다.")
    stream = video_streams[0]
    duration = float((payload.get("format") or {}).get("duration") or 0)
    fps = _rate(stream.get("avg_frame_rate") or stream.get("r_frame_rate"))
    frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or round(duration * fps))
    if duration <= 0 or fps <= 0 or frames <= 0:
        raise ValueError("액션 영상의 길이, FPS 또는 프레임 수가 올바르지 않습니다.")
    h3_frames = min(frames, round(duration * 24))
    while h3_frames >= 5 and h3_frames % 17 != 5:
        h3_frames -= 1
    return {
        "duration_seconds": round(duration, 3),
        "fps": round(fps, 3),
        "frame_count": frames,
        "h3_frame_count": h3_frames,
        "h3_frame_rule": "24fps frames trimmed by H3 to n % 17 == 5",
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "codec": str(stream.get("codec_name") or ""),
        "has_audio": any(row.get("codec_type") == "audio" for row in streams),
    }


def _validate_probe(probe: dict[str, Any], *, h3_copy: bool = False) -> None:
    duration = float(probe.get("duration_seconds") or 0)
    if duration < 2 or duration > 15.1:
        raise ValueError("액션 영상은 2~15초 범위여야 합니다.")
    if int(probe.get("h3_frame_count") or 0) < 5:
        raise ValueError("MiniMax H3가 사용할 수 있는 참조 프레임이 부족합니다.")
    if h3_copy and (
        int(probe.get("width") or 0) != 1024
        or int(probe.get("height") or 0) != 576
        or abs(float(probe.get("fps") or 0) - 24) > 0.05
        or str(probe.get("codec") or "").lower() != "h264"
        or bool(probe.get("has_audio"))
    ):
        raise ValueError("H3 입력용 영상은 1024×576, 24fps, H.264 무음이어야 합니다.")


def _upload_path(root: Path, value: Any) -> Path:
    upload_root = (root / "runtime/ui-uploads").resolve()
    source = Path(str(value or "")).resolve()
    try:
        source.relative_to(upload_root)
    except ValueError as exc:
        raise ValueError("등록 업로드 경로가 허용된 임시 영역 밖에 있습니다.") from exc
    if not source.is_file():
        raise FileNotFoundError("등록할 액션 영상 파일을 찾을 수 없습니다.")
    if source.suffix.lower() not in ALLOWED_VIDEO_SUFFIXES:
        raise ValueError("액션 영상은 MP4, MOV, WEBM, MKV 또는 AVI 파일이어야 합니다.")
    return source


def _prepare_h3_copy(source: Path, target: Path, duration: float) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(source), "-t", f"{min(15.0, duration):.3f}",
                "-vf",
                "scale=1024:576:force_original_aspect_ratio=decrease,"
                "pad=1024:576:(ow-iw)/2:(oh-ih)/2:color=black,fps=24",
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(target),
            ],
            capture_output=True, text=True, timeout=300, check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise ValueError("H3 입력용 무음 영상을 준비하지 못했습니다.") from exc
    if proc.returncode != 0 or not target.is_file():
        raise ValueError("H3 입력용 무음 영상을 준비하지 못했습니다.")
    probe = probe_video(target)
    _validate_probe(probe, h3_copy=True)
    return probe


def _normalise_participant(value: Any, label: str) -> dict[str, Any]:
    row = dict(value or {}) if isinstance(value, dict) else {}
    role = str(row.get("role") or "other").strip()
    body_type = str(row.get("body_type") or "other").strip()
    if role not in PARTICIPANT_ROLES:
        raise ValueError(f"{label} 역할이 올바르지 않습니다.")
    if body_type not in BODY_TYPES:
        raise ValueError(f"{label} 신체 유형이 올바르지 않습니다.")
    return {"role": role, "body_type": body_type, "description": str(row.get("description") or "").strip()}


def _normalise_blender_source(value: Any, *, enabled: bool) -> dict[str, str] | None:
    if not enabled:
        return None
    row = dict(value or {}) if isinstance(value, dict) else {}
    return {
        "project_file": Path(str(row.get("project_file") or "").strip()).name,
        "scene_name": str(row.get("scene_name") or "").strip(),
        "action_name": str(row.get("action_name") or "").strip(),
        "blender_version": str(row.get("blender_version") or "").strip(),
        "render_engine": str(row.get("render_engine") or "").strip(),
    }


def _normalise_metadata(data: dict[str, Any], *, source_type: str) -> dict[str, Any]:
    title = str(data.get("title") or "").strip()
    if not title:
        raise ValueError("액션 자산 제목이 필요합니다.")
    category = str(data.get("category") or "movement").strip()
    action_type = str(data.get("action_type") or "").strip()
    if category not in ACTION_CATEGORIES or action_type not in ACTION_CATEGORIES[category]:
        raise ValueError("기본 액션 분류와 액션 종류를 확인하세요.")
    participant_count = int(data.get("participant_count") or 1)
    if participant_count not in {1, 2}:
        raise ValueError("액션 참가자 수는 1명 또는 2명이어야 합니다.")
    if source_type not in SOURCE_TYPES:
        raise ValueError("액션 영상 출처 유형이 올바르지 않습니다.")
    commercial = bool(data.get("commercial_use_confirmed"))
    ai_reference = bool(data.get("ai_reference_use_confirmed"))
    rights_state = str(data.get("rights_state") or "").strip()
    if not rights_state:
        rights_state = "confirmed" if source_type != "external_licensed" and commercial and ai_reference else "rights_review_required"
    if rights_state not in RIGHTS_STATES:
        raise ValueError("권리 확인 상태가 올바르지 않습니다.")
    availability = str(data.get("availability_state") or "").strip()
    if not availability:
        availability = "available" if rights_state == "confirmed" and commercial and ai_reference else "rights_review_required"
    if availability not in AVAILABILITY_STATES:
        raise ValueError("액션 자산 사용 상태가 올바르지 않습니다.")
    if not commercial or not ai_reference or rights_state != "confirmed":
        availability = "rights_review_required"
    return {
        "title": title,
        "description": str(data.get("description") or "").strip(),
        "reference_role": "motion_only",
        "category": category,
        "category_label": CATEGORY_LABELS[category],
        "action_type": action_type,
        "participant_count": participant_count,
        "participant_a": _normalise_participant(data.get("participant_a"), "참가자 A"),
        "participant_b": _normalise_participant(data.get("participant_b"), "참가자 B") if participant_count == 2 else None,
        "handedness": str(data.get("handedness") or "none").strip(),
        "weapon_type": str(data.get("weapon_type") or "none").strip(),
        "attack_start_direction": str(data.get("attack_start_direction") or "").strip(),
        "attack_end_direction": str(data.get("attack_end_direction") or "").strip(),
        "screen_direction": str(data.get("screen_direction") or "").strip(),
        "timing": dict(data.get("timing") or {}),
        "camera": dict(data.get("camera") or {}),
        "contact_type": str(data.get("contact_type") or "").strip(),
        "source_type": source_type,
        "blender_source": _normalise_blender_source(
            data.get("blender_source"), enabled=source_type == "blender_render"
        ),
        "source_url": str(data.get("source_url") or "").strip(),
        "creator": str(data.get("creator") or "").strip(),
        "license_name": str(data.get("license_name") or "").strip(),
        "license_evidence": str(data.get("license_evidence") or "").strip(),
        "downloaded_at": str(data.get("downloaded_at") or "").strip() or None,
        "commercial_use_confirmed": commercial,
        "ai_reference_use_confirmed": ai_reference,
        "rights_state": rights_state,
        "availability_state": availability,
        "h3_usable": availability == "available",
        "active": bool(data.get("active", True)),
        "archived": bool(data.get("archived", False)),
    }


def _existing_sha(root: Path, digest: str, *, exclude_id: str = "") -> dict[str, Any] | None:
    for asset in list_assets(root, include_archived=True)["assets"]:
        if asset["action_asset_id"] != exclude_id and asset.get("sha256") == digest:
            return asset
    return None


def _new_asset_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    token = hashlib.sha256(f"{stamp}:{now_iso()}".encode()).hexdigest()[:8]
    return f"action_{stamp}_{token}"


def _write_asset(root: Path, metadata: dict[str, Any], original: Path, h3_input: Path) -> dict[str, Any]:
    asset_id = metadata["action_asset_id"]
    directory = asset_root(root) / asset_id
    original_dir, h3_dir = directory / "original", directory / "h3"
    original_target = original_dir / f"source{original.suffix.lower()}"
    h3_target = h3_dir / "action_h3_1024x576_24fps_h264.mp4"
    h3_digest = _sha256(h3_input)
    with queue_claim_lock(asset_root(root)):
        duplicate = _existing_sha(root, h3_digest, exclude_id=asset_id)
        if duplicate:
            raise ValueError(
                "동일 영상이 이미 등록되어 있습니다: "
                f"{duplicate['action_asset_id']} · {duplicate['title']}"
            )
        original_dir.mkdir(parents=True, exist_ok=False)
        h3_dir.mkdir(parents=True, exist_ok=False)
        shutil.copy2(original, original_target)
        shutil.copy2(h3_input, h3_target)
        metadata.update({
            "original_file": str(original_target),
            "h3_input_file": str(h3_target),
            "file_relationship": "h3_input_is_standardized_silent_copy",
            "sha256": h3_digest,
            "original_sha256": _sha256(original_target),
            "created_at": metadata.get("created_at") or now_iso(),
            "updated_at": now_iso(),
        })
        atomic_write_json(directory / "metadata.json", metadata)
    return metadata


def register_external(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    source = _upload_path(root, data.get("upload_path"))
    source_probe = probe_video(source)
    _validate_probe(source_probe)
    source_type = str(data.get("source_type") or "direct_upload").strip()
    metadata = _normalise_metadata(data, source_type=source_type)
    asset_id = _new_asset_id()
    temp = root / "runtime/h3/action-assets-work" / f"{asset_id}.mp4"
    temp.parent.mkdir(parents=True, exist_ok=True)
    try:
        h3_probe = _prepare_h3_copy(
            source,
            temp,
            float(source_probe["duration_seconds"]),
        )
        metadata.update({
            "action_asset_id": asset_id,
            "original_name": str(data.get("original_name") or source.name),
            "original_media": source_probe,
            "h3_media": h3_probe,
            "source_registration": (
                "blender_video_upload"
                if source_type == "blender_render"
                else "external_upload"
            ),
        })
        return _write_asset(root, metadata, source, temp)
    finally:
        temp.unlink(missing_ok=True)


def _completed_job_video(root: Path, job_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    job_id = _safe_id(job_id, "H3 작업 ID")
    directory = root / "runtime/h3/jobs" / job_id
    status = read_json(directory / "status.json", {}) or {}
    request = read_json(directory / "request.json", {}) or {}
    manifest = read_json(directory / "manifest.json", {}) or {}
    if status.get("status") != "completed":
        raise ValueError("완료된 1024×576 재생성 결과만 등록할 수 있습니다.")
    path = Path(str(manifest.get("local_video_path") or ""))
    if not path.is_file():
        raise FileNotFoundError("완료된 재생성 영상 파일을 찾을 수 없습니다.")
    digest = str(manifest.get("output_sha256") or "")
    if not digest or _sha256(path) != digest:
        raise ValueError("완료된 재생성 영상의 해시가 변경되었습니다.")
    return path, request, manifest


def register_rerender(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    rerender_job_id = _safe_id(data.get("rerender_job_id"), "재생성 작업 ID")
    video, request, manifest = _completed_job_video(root, rerender_job_id)
    if request.get("render_purpose") != "resolution_rerender" or (
        int(request.get("width") or 0), int(request.get("height") or 0)
    ) != (1024, 576):
        raise ValueError("완료된 1024×576 해상도 재생성 결과만 액션 자산으로 등록할 수 있습니다.")
    source_project_id = str(request.get("source_project_id") or "")
    manifest_path = root / "prompt_projects" / source_project_id / "manifest.json"
    project_manifest = read_json(manifest_path, {}) or {}
    if project_manifest.get("project_kind") != "action_asset_project":
        raise ValueError("액션 자산 프로젝트에서 생성한 결과만 내부 액션 자산으로 등록할 수 있습니다.")
    probe = probe_video(video)
    _validate_probe(probe)
    source_type = "internal_generated"
    defaults = {
        "title": data.get("title") or f"{request.get('source_clip_id') or rerender_job_id} 액션",
        "category": data.get("category") or "movement",
        "action_type": data.get("action_type") or ACTION_CATEGORIES["movement"][0],
        "source_type": source_type,
        "commercial_use_confirmed": True,
        "ai_reference_use_confirmed": True,
        "rights_state": "confirmed",
        "availability_state": "available",
        **data,
    }
    metadata = _normalise_metadata(defaults, source_type=source_type)
    asset_id = _new_asset_id()
    temp = root / "runtime/h3/action-assets-work" / f"{asset_id}.mp4"
    try:
        h3_probe = _prepare_h3_copy(
            video,
            temp,
            float(probe["duration_seconds"]),
        )
        metadata.update({
            "action_asset_id": asset_id,
            "original_name": video.name,
            "original_media": probe,
            "h3_media": h3_probe,
            "source_registration": "completed_1024x576_rerender",
            "source_project_id": source_project_id,
            "source_scene_id": request.get("source_scene_id"),
            "source_clip_id": request.get("source_clip_id"),
            "source_candidate_set_id": request.get("source_candidate_set_id"),
            "source_selected_job_id": request.get("source_selected_job_id"),
            "source_rerender_job_id": rerender_job_id,
            "source_output_sha256": manifest.get("output_sha256"),
        })
        return _write_asset(root, metadata, video, temp)
    finally:
        temp.unlink(missing_ok=True)


def list_assets(root: Path, *, include_archived: bool = True) -> dict[str, Any]:
    assets = []
    base = asset_root(root)
    if base.is_dir():
        for directory in base.iterdir():
            if not directory.is_dir():
                continue
            metadata = read_json(directory / "metadata.json", {}) or {}
            if not metadata or metadata.get("deleted") or (metadata.get("archived") and not include_archived):
                continue
            metadata = dict(metadata)
            metadata["h3_usable"] = bool(
                metadata.get("availability_state") == "available"
                and metadata.get("active")
                and not metadata.get("archived")
                and Path(str(metadata.get("h3_input_file") or "")).is_file()
            )
            assets.append(metadata)
    assets.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return {
        "assets": assets,
        "presets": {
            "categories": ACTION_CATEGORIES,
            "category_labels": CATEGORY_LABELS,
            "body_types": sorted(BODY_TYPES),
            "participant_roles": sorted(PARTICIPANT_ROLES),
            "source_types": sorted(SOURCE_TYPES),
            "availability_states": sorted(AVAILABILITY_STATES),
        },
    }


def get_asset(root: Path, asset_id: str, *, require_usable: bool = False) -> dict[str, Any]:
    asset_id = _safe_id(asset_id)
    metadata = read_json(asset_root(root) / asset_id / "metadata.json", {}) or {}
    if not metadata or metadata.get("deleted"):
        raise FileNotFoundError("액션 자산을 찾을 수 없습니다.")
    path = Path(str(metadata.get("h3_input_file") or ""))
    metadata = dict(metadata)
    metadata["h3_usable"] = bool(
        metadata.get("availability_state") == "available"
        and metadata.get("active") and not metadata.get("archived") and path.is_file()
    )
    if require_usable and not metadata["h3_usable"]:
        raise ValueError("이 액션 자산은 현재 H3 참조에 사용할 수 없습니다.")
    if path.is_file() and _sha256(path) != str(metadata.get("sha256") or ""):
        raise ValueError("액션 자산 H3 입력 파일의 해시가 변경되었습니다.")
    return metadata


def update_asset(root: Path, asset_id: str, data: dict[str, Any]) -> dict[str, Any]:
    asset_id = _safe_id(asset_id)
    path = asset_root(root) / asset_id / "metadata.json"
    with queue_claim_lock(asset_root(root)):
        current = read_json(path, {}) or {}
        if not current or current.get("deleted"):
            raise FileNotFoundError("액션 자산을 찾을 수 없습니다.")
        updates = {key: value for key, value in data.items() if key in EDITABLE_FIELDS}
        merged = {**current, **updates}
        normal = _normalise_metadata(merged, source_type=str(current.get("source_type") or "direct_upload"))
        current.update(normal, updated_at=now_iso())
        atomic_write_json(path, current)
    return get_asset(root, asset_id)


def media_path(root: Path, asset_id: str, kind: str = "h3") -> Path:
    asset = get_asset(root, asset_id)
    key = "original_file" if kind == "original" else "h3_input_file"
    path = Path(str(asset.get(key) or ""))
    directory = (asset_root(root) / _safe_id(asset_id)).resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(directory)
    except ValueError as exc:
        raise ValueError("액션 자산 파일 경로가 저장 영역 밖을 가리킵니다.") from exc
    if not resolved.is_file():
        raise FileNotFoundError("액션 자산 영상 파일을 찾을 수 없습니다.")
    return resolved


def delete_asset(root: Path, asset_id: str) -> dict[str, Any]:
    """Remove from the library while retaining media used by existing jobs."""
    asset_id = _safe_id(asset_id)
    path = asset_root(root) / asset_id / "metadata.json"
    with queue_claim_lock(asset_root(root)):
        current = read_json(path, {}) or {}
        if not current:
            raise FileNotFoundError("액션 자산을 찾을 수 없습니다.")
        if not current.get("deleted"):
            current.update(deleted=True, deleted_at=now_iso(), updated_at=now_iso(), active=False)
            atomic_write_json(path, current)
    return {"action_asset_id": asset_id, "deleted": True, "media_preserved": True}
