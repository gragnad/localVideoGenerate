from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote


DIRECTOR_PROMPT_PROJECTS_DIR = "director_prompt_projects"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".jfif"}
JSON_BLOCK_RE = re.compile(r"```json\s*\n([\s\S]*?)\n```", re.IGNORECASE)
VALID_STATUSES = {
    "draft",
    "prompt_review_required",
    "awaiting_scene_images",
    "image_review_required",
    "image_changes_required",
    "needs_confirmation",
    "ready_for_director",
    "registered",
    "invalid",
}


class DirectorPromptProjectError(ValueError):
    pass


def projects_root(root: Path) -> Path:
    return root / DIRECTOR_PROMPT_PROJECTS_DIR


def _safe_component(value: str, label: str) -> str:
    text = str(value or "").strip()
    if (
        not text
        or text in {".", ".."}
        or Path(text).name != text
        or "/" in text
        or "\\" in text
    ):
        raise DirectorPromptProjectError(f"허용되지 않는 {label}입니다.")
    return text


def _project_dir(root: Path, project_id: str) -> Path:
    return projects_root(root) / _safe_component(project_id, "project_id")


def _resolve_under(base: Path, relative_path: str) -> Path:
    relative = str(relative_path or "").strip().replace("\\", "/").strip("/")
    if not relative or any(part in {"", ".", ".."} for part in relative.split("/")):
        raise DirectorPromptProjectError("허용되지 않는 장면 이미지 경로입니다.")
    base = base.resolve()
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise DirectorPromptProjectError("프로젝트 밖의 장면 이미지 경로입니다.") from exc
    if candidate.is_symlink():
        raise DirectorPromptProjectError("심볼릭 링크 이미지는 허용되지 않습니다.")
    return candidate


def _normalize_scene_asset_path(project_id: str, source_path: str) -> str:
    text = str(source_path or "").strip().replace("\\", "/")
    prefix = f"{DIRECTOR_PROMPT_PROJECTS_DIR}/{project_id}/"
    if text.startswith(prefix):
        text = text[len(prefix) :]
    while text.startswith("./"):
        text = text[2:]
    return text.strip("/")


def resolve_scene_asset(root: Path, project_id: str, source_path: str) -> Path:
    relative = _normalize_scene_asset_path(project_id, source_path)
    if not relative.startswith("scene_images/"):
        raise DirectorPromptProjectError(
            "Director 장면 이미지는 프로젝트의 scene_images/ 아래에 있어야 합니다."
        )
    path = _resolve_under(_project_dir(root, project_id), relative)
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        raise DirectorPromptProjectError("지원하지 않는 장면 이미지 형식입니다.")
    if not path.is_file():
        raise FileNotFoundError(f"장면 이미지가 없습니다: {relative}")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_machine_payload(markdown: str) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(markdown)
    if not match:
        raise DirectorPromptProjectError("Machine Payload JSON 블록이 없습니다.")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise DirectorPromptProjectError(
            f"Machine Payload JSON 파싱 실패: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise DirectorPromptProjectError("Machine Payload는 JSON 객체여야 합니다.")
    return payload


def _review_status(value: Any) -> str:
    return str(value or "").strip().lower()


def validate_machine_payload(
    root: Path,
    payload: dict[str, Any],
    *,
    project_id: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    resolved_project_id = str(payload.get("project_id") or project_id or "").strip()
    if project_id and resolved_project_id != project_id:
        errors.append("Machine Payload의 project_id가 프로젝트 폴더와 다릅니다.")
    try:
        _safe_component(resolved_project_id, "project_id")
    except DirectorPromptProjectError as exc:
        errors.append(str(exc))

    workflow = str(payload.get("workflow") or "")
    if not workflow.startswith("director_prompt"):
        errors.append("workflow는 director_prompt 계열이어야 합니다.")
    if not str(payload.get("clip_id") or "").strip():
        errors.append("clip_id가 필요합니다.")
    if not str(payload.get("scene_id") or "").strip():
        errors.append("scene_id가 필요합니다.")
    if not str(payload.get("global_prompt") or "").strip():
        errors.append("global_prompt가 필요합니다.")

    try:
        fps = int(payload.get("fps") or 24)
        if fps <= 0:
            raise ValueError
    except (TypeError, ValueError):
        fps = 24
        errors.append("fps는 1 이상의 정수여야 합니다.")

    resolution = payload.get("resolution") or {}
    try:
        width = int(resolution.get("width"))
        height = int(resolution.get("height"))
        if width <= 0 or height <= 0:
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        width = height = 0
        errors.append("resolution.width/height가 필요합니다.")

    segments = payload.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append("segments가 한 개 이상 필요합니다.")
        segments = []

    seen_ids: set[str] = set()
    seen_orders: set[int] = set()
    normalized_segments: list[dict[str, Any]] = []
    missing_images = False
    pending_images = False
    changes_required = False
    total_seconds = 0.0

    for index, raw in enumerate(segments, 1):
        if not isinstance(raw, dict):
            errors.append(f"Segment {index}가 객체가 아닙니다.")
            continue
        segment = dict(raw)
        segment_id = str(segment.get("segment_id") or f"SEG{index:02d}").strip()
        if segment_id in seen_ids:
            errors.append(f"중복 segment_id: {segment_id}")
        seen_ids.add(segment_id)
        try:
            order = int(segment.get("order") or index)
        except (TypeError, ValueError):
            order = index
            errors.append(f"{segment_id}: order가 정수가 아닙니다.")
        if order in seen_orders:
            errors.append(f"중복 Segment order: {order}")
        seen_orders.add(order)
        try:
            seconds = float(segment.get("seconds"))
            if seconds <= 0:
                raise ValueError
        except (TypeError, ValueError):
            seconds = 0.0
            errors.append(f"{segment_id}: seconds는 0보다 커야 합니다.")
        total_seconds += seconds
        if not str(segment.get("director_prompt") or "").strip():
            errors.append(f"{segment_id}: director_prompt가 필요합니다.")

        scene_image = (
            dict(segment.get("scene_image") or {})
            if isinstance(segment.get("scene_image"), dict)
            else {}
        )
        source_path = str(scene_image.get("source_path") or "").strip()
        review_status = _review_status(scene_image.get("review_status") or "pending")
        actual_hash = None
        asset_error = None
        if not source_path:
            missing_images = True
        else:
            try:
                path = resolve_scene_asset(root, resolved_project_id, source_path)
                actual_hash = _sha256(path)
                expected_hash = str(scene_image.get("sha256") or "").strip().lower()
                if expected_hash and expected_hash != actual_hash:
                    pending_images = True
                    review_status = "pending"
                    warnings.append(
                        f"{segment_id}: 검수 후 이미지가 변경되어 승인이 무효화됐습니다."
                    )
            except (DirectorPromptProjectError, FileNotFoundError) as exc:
                missing_images = True
                asset_error = str(exc)
                warnings.append(f"{segment_id}: {exc}")

        if review_status == "changes_required":
            changes_required = True
        elif source_path and not asset_error and review_status != "approved":
            pending_images = True
        scene_image.update(
            source_path=source_path or None,
            review_status=review_status,
            actual_sha256=actual_hash,
            asset_error=asset_error,
        )
        segment.update(
            segment_id=segment_id,
            order=order,
            seconds=seconds,
            scene_image=scene_image,
        )
        normalized_segments.append(segment)

    if total_seconds > 30:
        warnings.append(
            f"총 구간 시간이 30초를 초과합니다: {total_seconds:g}초"
        )
    requested = payload.get("requested_seconds")
    if requested is not None:
        try:
            if abs(float(requested) - total_seconds) > 0.05:
                warnings.append(
                    "requested_seconds와 Segment 시간 합계가 일치하지 않습니다."
                )
        except (TypeError, ValueError):
            errors.append("requested_seconds가 숫자가 아닙니다.")

    prompt_review = (
        payload.get("prompt_review")
        if isinstance(payload.get("prompt_review"), dict)
        else {}
    )
    prompt_status = _review_status(prompt_review.get("status"))
    declared_status = _review_status(payload.get("status") or "draft")
    if declared_status not in VALID_STATUSES:
        warnings.append(f"알 수 없는 선언 상태: {declared_status}")

    if errors:
        computed_status = "invalid"
    elif declared_status == "needs_confirmation":
        computed_status = "needs_confirmation"
    elif prompt_status != "approved":
        computed_status = "prompt_review_required"
    elif missing_images:
        computed_status = "awaiting_scene_images"
    elif changes_required:
        computed_status = "image_changes_required"
    elif pending_images:
        computed_status = "image_review_required"
    else:
        computed_status = "ready_for_director"

    if (
        declared_status
        and declared_status not in {"draft", "registered", computed_status}
        and not errors
    ):
        warnings.append(
            f"선언 상태({declared_status})를 검증 상태({computed_status})로 표시합니다."
        )

    normalized_segments.sort(key=lambda item: (item["order"], item["segment_id"]))
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "status": computed_status,
        "declared_status": declared_status,
        "project_id": resolved_project_id,
        "fps": fps,
        "resolution": {"width": width, "height": height},
        "total_seconds": total_seconds,
        "segments": normalized_segments,
        "can_register_director": computed_status == "ready_for_director",
    }


def _clip_markdown_path(root: Path, project_id: str, clip_id: str) -> Path:
    project_dir = _project_dir(root, project_id)
    safe_clip = _safe_component(clip_id, "clip_id")
    matches = [
        path
        for path in project_dir.rglob("*.md")
        if path.stem == safe_clip and "scene_images" not in path.parts
    ]
    if len(matches) != 1:
        if not matches:
            raise FileNotFoundError(f"Director 클립 Markdown이 없습니다: {clip_id}")
        raise DirectorPromptProjectError(f"중복 Director 클립 Markdown: {clip_id}")
    return matches[0]


def parse_clip_markdown(
    root: Path,
    markdown_path: Path,
    *,
    project_id: str,
) -> dict[str, Any]:
    markdown = markdown_path.read_text(encoding="utf-8")
    payload = extract_machine_payload(markdown)
    validation = validate_machine_payload(root, payload, project_id=project_id)
    segments = validation["segments"]
    payload = dict(payload)
    payload["segments"] = segments
    payload["status"] = validation["status"]
    return {
        "project_id": project_id,
        "scene_id": str(payload.get("scene_id") or ""),
        "clip_id": str(payload.get("clip_id") or markdown_path.stem),
        "sequence": int(payload.get("sequence") or 0),
        "status": validation["status"],
        "declared_status": validation["declared_status"],
        "summary": str(
            payload.get("summary")
            or payload.get("narrative_purpose")
            or ""
        ),
        "requested_seconds": validation["total_seconds"],
        "segment_count": len(segments),
        "approved_image_count": sum(
            1
            for segment in segments
            if segment["scene_image"].get("review_status") == "approved"
            and not segment["scene_image"].get("asset_error")
        ),
        "warnings": validation["warnings"],
        "errors": validation["errors"],
        "valid": validation["valid"],
        "can_register_director": validation["can_register_director"],
        "markdown_path": markdown_path.relative_to(projects_root(root)).as_posix(),
        "payload": payload,
        "validation": validation,
    }


def scan_project_clips(root: Path, project_id: str) -> list[dict[str, Any]]:
    project_dir = _project_dir(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(f"Director Prompt Project가 없습니다: {project_id}")
    clips: list[dict[str, Any]] = []
    for path in sorted(project_dir.rglob("*.md")):
        if "scene_images" in path.parts:
            continue
        try:
            item = parse_clip_markdown(root, path, project_id=project_id)
            item.pop("payload", None)
            item.pop("validation", None)
            clips.append(item)
        except Exception as exc:
            clips.append(
                {
                    "project_id": project_id,
                    "scene_id": path.parent.name,
                    "clip_id": path.stem,
                    "sequence": 0,
                    "status": "invalid",
                    "summary": "",
                    "requested_seconds": 0,
                    "segment_count": 0,
                    "approved_image_count": 0,
                    "warnings": [],
                    "errors": [str(exc)],
                    "valid": False,
                    "can_register_director": False,
                    "markdown_path": path.relative_to(projects_root(root)).as_posix(),
                }
            )
    clips.sort(key=lambda item: (item["scene_id"], item["sequence"], item["clip_id"]))
    return clips


def list_projects_action(root: Path, _data: dict[str, Any] | None = None) -> dict[str, Any]:
    base = projects_root(root)
    projects: list[dict[str, Any]] = []
    if not base.is_dir():
        return {"projects": projects}
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        manifest = {}
        manifest_path = entry / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest = {"error": "manifest.json 파싱 실패"}
        clips = scan_project_clips(root, entry.name)
        projects.append(
            {
                "project_id": entry.name,
                "title": manifest.get("title") or entry.name,
                "description": manifest.get("description") or "",
                "scene_count": len({clip["scene_id"] for clip in clips}),
                "clip_count": len(clips),
                "ready_count": sum(
                    1 for clip in clips if clip["status"] == "ready_for_director"
                ),
                "awaiting_image_count": sum(
                    1
                    for clip in clips
                    if clip["status"]
                    in {"awaiting_scene_images", "image_review_required"}
                ),
                "changes_required_count": sum(
                    1
                    for clip in clips
                    if clip["status"] == "image_changes_required"
                ),
                "invalid_count": sum(
                    1 for clip in clips if clip["status"] == "invalid"
                ),
            }
        )
    return {"projects": projects}


def list_clips_action(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = str(data.get("project_id") or "")
    clips = scan_project_clips(root, project_id)
    scenes: dict[str, list[dict[str, Any]]] = {}
    for clip in clips:
        scenes.setdefault(clip["scene_id"], []).append(clip)
    return {
        "project_id": project_id,
        "clips": clips,
        "scenes": [
            {"scene_id": scene_id, "clips": items}
            for scene_id, items in sorted(scenes.items())
        ],
    }


def _asset_url(project_id: str, source_path: str) -> str:
    relative = _normalize_scene_asset_path(project_id, source_path)
    return (
        f"/api/director-prompt-assets/{quote(project_id, safe='')}/"
        f"{quote(relative, safe='/')}"
    )


def get_clip_action(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = str(data.get("project_id") or "")
    clip_id = str(data.get("clip_id") or "")
    path = _clip_markdown_path(root, project_id, clip_id)
    item = parse_clip_markdown(root, path, project_id=project_id)
    payload = item.pop("payload")
    validation = item.pop("validation")
    segments = []
    for segment in validation["segments"]:
        scene_image = dict(segment["scene_image"])
        source_path = str(scene_image.get("source_path") or "")
        scene_image["asset_url"] = (
            _asset_url(project_id, source_path)
            if source_path and not scene_image.get("asset_error")
            else None
        )
        segments.append({**segment, "scene_image": scene_image})
    payload["segments"] = segments
    block_reason = None
    if not validation["can_register_director"]:
        reasons = {
            "prompt_review_required": "Director 프롬프트 검수가 필요합니다.",
            "awaiting_scene_images": "한 개 이상의 장면 이미지가 없습니다.",
            "image_review_required": "장면 이미지 검수가 완료되지 않았습니다.",
            "image_changes_required": "장면 이미지 수정이 필요합니다.",
            "needs_confirmation": "사용자 확인이 필요한 클립입니다.",
            "invalid": "프로젝트 구조 오류를 해결해야 합니다.",
        }
        block_reason = reasons.get(validation["status"], "등록 준비가 완료되지 않았습니다.")
    return {
        **item,
        "machine_payload": payload,
        "can_register_director": validation["can_register_director"],
        "registration_block_reason": block_reason,
    }


def resolve_asset_action(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = str(data.get("project_id") or "")
    asset_path = str(data.get("asset_path") or "")
    path = resolve_scene_asset(root, project_id, asset_path)
    return {
        "path": str(path),
        "source_path": (
            f"{DIRECTOR_PROMPT_PROJECTS_DIR}/{project_id}/"
            f"{_normalize_scene_asset_path(project_id, asset_path)}"
        ),
    }

