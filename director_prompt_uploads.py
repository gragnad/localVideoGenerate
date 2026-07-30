from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import director_prompt_projects as projects


ALLOWED_REVIEW_STATUSES = {"pending", "approved", "changes_required"}


def _load_document(
    root: Path, project_id: str, clip_id: str
) -> tuple[Path, str, dict[str, Any]]:
    markdown_path = projects._clip_markdown_path(root, project_id, clip_id)
    markdown = markdown_path.read_text(encoding="utf-8")
    payload = projects.extract_machine_payload(markdown)
    if str(payload.get("project_id") or "") != project_id:
        raise projects.DirectorPromptProjectError(
            "Machine Payload의 project_id가 프로젝트와 다릅니다."
        )
    if str(payload.get("clip_id") or "") != clip_id:
        raise projects.DirectorPromptProjectError(
            "Machine Payload의 clip_id가 요청과 다릅니다."
        )
    return markdown_path, markdown, payload


def _find_segment(payload: dict[str, Any], segment_id: str) -> dict[str, Any]:
    for segment in payload.get("segments") or []:
        if str(segment.get("segment_id") or "") == segment_id:
            return segment
    raise projects.DirectorPromptProjectError(
        f"Director Segment가 없습니다: {segment_id}"
    )


def _write_payload(
    markdown_path: Path, markdown: str, payload: dict[str, Any]
) -> None:
    replacement = "```json\n" + json.dumps(
        payload, ensure_ascii=False, indent=2
    ) + "\n```"
    updated, count = projects.JSON_BLOCK_RE.subn(
        lambda _match: replacement, markdown, count=1
    )
    if count != 1:
        raise projects.DirectorPromptProjectError(
            "Machine Payload JSON 블록을 갱신할 수 없습니다."
        )
    temporary = markdown_path.with_name(
        f".{markdown_path.name}.{os.getpid()}.tmp"
    )
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(markdown_path)


def save_segment_image_action(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = projects._safe_component(data.get("project_id"), "project_id")
    clip_id = projects._safe_component(data.get("clip_id"), "clip_id")
    segment_id = projects._safe_component(data.get("segment_id"), "segment_id")
    upload_path = Path(str(data.get("upload_path") or ""))
    suffix = upload_path.suffix.lower()
    if not upload_path.is_file() or suffix not in projects.IMAGE_SUFFIXES:
        raise projects.DirectorPromptProjectError(
            "지원하는 장면 이미지 파일을 선택해야 합니다."
        )

    markdown_path, markdown, payload = _load_document(
        root, project_id, clip_id
    )
    segment = _find_segment(payload, segment_id)
    target_dir = projects._project_dir(root, project_id) / "scene_images" / clip_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{segment_id}{suffix}"
    shutil.copyfile(upload_path, target)
    digest = projects._sha256(target)
    scene_image = dict(segment.get("scene_image") or {})
    scene_image.update(
        {
            "status": "uploaded",
            "source_path": target.relative_to(
                projects._project_dir(root, project_id)
            ).as_posix(),
            "review_status": "pending",
            "review_notes": [],
            "sha256": digest,
        }
    )
    segment["scene_image"] = scene_image
    _sync_payload_image_status(payload)
    _write_payload(markdown_path, markdown, payload)
    return projects.get_clip_action(
        root, {"project_id": project_id, "clip_id": clip_id}
    )


def review_segment_image_action(
    root: Path, data: dict[str, Any]
) -> dict[str, Any]:
    project_id = projects._safe_component(data.get("project_id"), "project_id")
    clip_id = projects._safe_component(data.get("clip_id"), "clip_id")
    segment_id = projects._safe_component(data.get("segment_id"), "segment_id")
    review_status = str(data.get("review_status") or "").strip().lower()
    if review_status not in ALLOWED_REVIEW_STATUSES:
        raise projects.DirectorPromptProjectError(
            "review_status는 pending, approved, changes_required 중 하나여야 합니다."
        )

    markdown_path, markdown, payload = _load_document(
        root, project_id, clip_id
    )
    segment = _find_segment(payload, segment_id)
    scene_image = dict(segment.get("scene_image") or {})
    source_path = str(scene_image.get("source_path") or "")
    image_path = projects.resolve_scene_asset(root, project_id, source_path)
    notes = data.get("review_notes")
    if isinstance(notes, str):
        notes = [notes.strip()] if notes.strip() else []
    elif not isinstance(notes, list):
        notes = []
    scene_image.update(
        {
            "status": "approved" if review_status == "approved" else "uploaded",
            "review_status": review_status,
            "review_notes": [str(note).strip() for note in notes if str(note).strip()],
            "sha256": projects._sha256(image_path),
        }
    )
    segment["scene_image"] = scene_image
    _sync_payload_image_status(payload)
    _write_payload(markdown_path, markdown, payload)
    return projects.get_clip_action(
        root, {"project_id": project_id, "clip_id": clip_id}
    )


def _image_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    images = [
        dict(segment.get("scene_image") or {})
        for segment in payload.get("segments") or []
    ]
    approved = sum(
        image.get("review_status") == "approved" for image in images
    )
    changes = sum(
        image.get("review_status") == "changes_required" for image in images
    )
    total = len(images)
    status = (
        "approved"
        if total and approved == total
        else "changes_required"
        if changes
        else "pending"
    )
    return {
        "status": status,
        "approved_count": approved,
        "total_count": total,
        "warnings": [],
    }


def _sync_payload_image_status(payload: dict[str, Any]) -> None:
    summary = _image_review_summary(payload)
    payload["image_review_summary"] = summary
    if str(payload.get("status") or "") == "needs_confirmation":
        return
    prompt_review = payload.get("prompt_review") or {}
    images = [
        dict(segment.get("scene_image") or {})
        for segment in payload.get("segments") or []
    ]
    if str(prompt_review.get("status") or "").lower() != "approved":
        status = "prompt_review_required"
    elif any(not str(image.get("source_path") or "").strip() for image in images):
        status = "awaiting_scene_images"
    elif summary["status"] == "changes_required":
        status = "image_changes_required"
    elif summary["status"] == "approved":
        status = "ready_for_director"
    else:
        status = "image_review_required"
    payload["status"] = status
