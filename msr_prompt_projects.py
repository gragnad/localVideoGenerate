from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import msr_sequence_v2

PROMPT_PROJECTS_DIR_NAME = "prompt_projects"
SCENARIO_PROJECT_DIR_NAME = "RaisingaDragonSeason01"
BACKGROUND_CATALOG_FILE = "background_catalog.json"
BACKGROUND_LINKS_FILE = "background_links.json"
MAX_CLIP_SECONDS = 30.0
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".jfif"}
JSON_BLOCK_RE = re.compile(r"```json\s*\n([\s\S]*?)\n```", re.IGNORECASE)
VALID_STATUSES = {"reviewed", "needs_confirmation", "awaiting_background", "invalid"}


class PromptProjectError(ValueError):
    pass


def prompt_projects_root(root: Path) -> Path:
    return root / PROMPT_PROJECTS_DIR_NAME


def scenario_asset_root(root: Path) -> Path:
    return root / SCENARIO_PROJECT_DIR_NAME


def is_sequence_v2_project(root: Path, project_id: str) -> bool:
    manifest_path = prompt_projects_root(root) / str(project_id) / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        manifest.get("workflow") == msr_sequence_v2.WORKFLOW
        and manifest.get("prompt_strategy") == msr_sequence_v2.PROMPT_STRATEGY
        and manifest.get("director_prompt_inheritance") is False
    )


def project_backgrounds_dir(root: Path, project_id: str) -> Path:
    return _project_dir(root, project_id) / "backgrounds"


def allowed_asset_roots(root: Path) -> dict[str, Path]:
    return {
        SCENARIO_PROJECT_DIR_NAME: scenario_asset_root(root),
    }


def _normalize_relative_path(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.strip("/")


def is_safe_relative_path(value: str) -> bool:
    text = _normalize_relative_path(value)
    if not text or text in {".", ".."}:
        return False
    parts = [part for part in text.split("/") if part not in {"", "."}]
    return ".." not in parts and not any(part.startswith("..") for part in parts)


def _safe_filename(name: str) -> str:
    filename = Path(str(name or "")).name
    if not filename or filename in {".", ".."} or "/" in filename or "\\" in filename:
        raise PromptProjectError("허용되지 않는 파일 이름입니다.")
    return filename


def _resolve_under(base: Path, *parts: str) -> Path:
    base = base.resolve()
    candidate = base.joinpath(*parts).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise PromptProjectError("경로 탐색이 차단되었습니다.") from exc
    if candidate.is_symlink():
        raise PromptProjectError("심볼릭 링크 경로는 허용되지 않습니다.")
    return candidate


def resolve_allowed_asset(root: Path, source_path: str) -> Path:
    rel = _normalize_relative_path(source_path)
    if not is_safe_relative_path(rel):
        raise PromptProjectError("허용되지 않는 상대 경로입니다.")
    if rel.startswith(f"{PROMPT_PROJECTS_DIR_NAME}/"):
        _, project_and_rest = rel.split("/", 1)
        project_id, _, remainder = project_and_rest.partition("/")
        if remainder.startswith("backgrounds/"):
            filename = _safe_filename(remainder.split("/", 1)[1])
            path = _resolve_under(project_backgrounds_dir(root, project_id), filename)
        else:
            raise PromptProjectError("허용된 prompt project asset 경로가 아닙니다.")
    else:
        top, _, remainder = rel.partition("/")
        allowed = allowed_asset_roots(root).get(top)
        if allowed is None:
            raise PromptProjectError("허용된 프로젝트 루트 밖의 경로입니다.")
        path = _resolve_under(allowed, remainder)
    if not path.is_file():
        raise FileNotFoundError(f"에셋 파일을 찾을 수 없습니다: {rel}")
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        raise PromptProjectError("허용되지 않는 이미지 형식입니다.")
    return path


def background_source_path(project_id: str, filename: str) -> str:
    safe = _safe_filename(filename)
    return f"{PROMPT_PROJECTS_DIR_NAME}/{project_id}/backgrounds/{safe}"


def load_background_catalog(root: Path, project_id: str) -> dict[str, Any]:
    path = _project_dir(root, project_id) / BACKGROUND_CATALOG_FILE
    if not path.is_file():
        return {"backgrounds": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {"backgrounds": {}}


def load_background_links(root: Path, project_id: str) -> dict[str, Any]:
    path = _project_dir(root, project_id) / BACKGROUND_LINKS_FILE
    if not path.is_file():
        return {"schema_version": 1, "project_id": project_id, "links": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    links = payload.get("links") if isinstance(payload, dict) else {}
    return {
        "schema_version": int(payload.get("schema_version") or 1),
        "project_id": project_id,
        "links": links if isinstance(links, dict) else {},
        "updated_at": payload.get("updated_at"),
    }


def save_background_links(root: Path, project_id: str, links: dict[str, Any]) -> dict[str, Any]:
    path = _project_dir(root, project_id) / BACKGROUND_LINKS_FILE
    payload = {
        "schema_version": 1,
        "project_id": project_id,
        "links": links,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def scan_background_files(root: Path, project_id: str) -> dict[str, str]:
    folder = project_backgrounds_dir(root, project_id)
    detected: dict[str, str] = {}
    if not folder.is_dir():
        return detected
    for entry in sorted(folder.iterdir()):
        if not entry.is_file() or entry.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        detected[entry.name] = background_source_path(project_id, entry.name)
    return detected


def resolve_background_link(
    root: Path,
    project_id: str,
    background_id: str,
    *,
    links: dict[str, Any] | None = None,
    detected: dict[str, str] | None = None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    background_id = str(background_id or "").strip()
    if not background_id:
        return None
    links = links if links is not None else load_background_links(root, project_id).get("links") or {}
    detected = detected if detected is not None else scan_background_files(root, project_id)
    catalog = catalog if catalog is not None else load_background_catalog(root, project_id)
    entry = (catalog.get("backgrounds") or {}).get(background_id) or {}
    suggested = str(entry.get("suggested_filename") or f"{background_id}.png")

    filename = None
    link = links.get(background_id) if isinstance(links.get(background_id), dict) else None
    if link:
        filename = _safe_filename(str(link.get("filename") or link.get("source_path") or "").split("/")[-1])
    elif suggested in detected:
        filename = suggested
    elif background_id + ".png" in detected:
        filename = background_id + ".png"

    if not filename:
        return None

    source_path = background_source_path(project_id, filename)
    try:
        resolve_allowed_asset(root, source_path)
    except (FileNotFoundError, PromptProjectError):
        return None
    return {
        "background_id": background_id,
        "filename": filename,
        "source_path": source_path,
        "linked": bool(link),
        "auto_detected": not bool(link),
        "review_status": str((link or {}).get("review_status") or "approved"),
        "reviewed_at": (link or {}).get("reviewed_at"),
        "review_notes": list((link or {}).get("review_notes") or []),
        "review_checklist": dict((link or {}).get("review_checklist") or {}),
        "linked_at": (link or {}).get("linked_at"),
        "replaced_at": (link or {}).get("replaced_at"),
        "previous_review_notes": list((link or {}).get("previous_review_notes") or []),
    }


def build_background_generation(catalog_entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "required": True,
        "suggested_filename": catalog_entry.get("suggested_filename"),
        "aspect_ratio": catalog_entry.get("aspect_ratio") or "16:9",
        "recommended_resolution": catalog_entry.get("recommended_resolution") or {"width": 1536, "height": 864},
        "prompt": catalog_entry.get("prompt") or "",
        "negative_prompt": catalog_entry.get("negative_prompt") or "",
        "continuity_notes": list(catalog_entry.get("continuity_notes") or []),
    }


def merge_payload_background(
    root: Path,
    project_id: str,
    payload: dict[str, Any],
    *,
    links: dict[str, Any] | None = None,
    detected: dict[str, str] | None = None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(payload)
    background = dict(payload.get("background") or {})
    background_id = str(background.get("background_id") or "")
    catalog = catalog if catalog is not None else load_background_catalog(root, project_id)
    catalog_entry = (catalog.get("backgrounds") or {}).get(background_id) or {}

    if not payload.get("background_generation") and catalog_entry:
        payload["background_generation"] = build_background_generation(catalog_entry)

    resolved = resolve_background_link(
        root,
        project_id,
        background_id,
        links=links,
        detected=detected,
        catalog=catalog,
    )
    if resolved:
        instant_ready = payload.get("workflow") == msr_sequence_v2.WORKFLOW and payload.get("prompt_strategy") == msr_sequence_v2.PROMPT_STRATEGY
        background.update(
            status="linked",
            source_path=resolved["source_path"],
            filename=resolved["filename"],
            linked=resolved["linked"],
            auto_detected=resolved["auto_detected"],
            review_status="approved" if instant_ready else resolved["review_status"],
            review_notes=[] if instant_ready else resolved["review_notes"],
            review_checklist={} if instant_ready else resolved["review_checklist"],
            linked_at=resolved.get("linked_at"),
            replaced_at=resolved.get("replaced_at"),
        )
    else:
        background.setdefault("status", "missing")
        background["source_path"] = background.get("source_path") or None
    payload["background"] = background
    return payload


def resolve_effective_status(payload: dict[str, Any], *, has_errors: bool) -> str:
    if has_errors:
        return "invalid"
    unresolved = list((payload.get("review") or {}).get("unresolved_questions") or [])
    if unresolved:
        return "needs_confirmation"
    background = payload.get("background") or {}
    instant_ready = payload.get("workflow") == msr_sequence_v2.WORKFLOW and payload.get("prompt_strategy") == msr_sequence_v2.PROMPT_STRATEGY
    if not instant_ready and background.get("review_status") in {"pending", "changes_required"}:
        return "awaiting_background"
    if background.get("status") != "linked" and not background.get("source_path"):
        return "awaiting_background"
    return "reviewed"


def extract_machine_payload(markdown_text: str) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(markdown_text or "")
    if not match:
        raise PromptProjectError("Machine Payload JSON 코드 블록이 없습니다.")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise PromptProjectError(f"Machine Payload JSON 파싱 실패: {exc}") from exc
    if not isinstance(payload, dict):
        raise PromptProjectError("Machine Payload는 JSON 객체여야 합니다.")
    return payload


def _relay_total_seconds(payload: dict[str, Any]) -> float:
    return round(sum(float(item.get("seconds") or 0) for item in payload.get("relay_segments") or []), 4)


def validate_machine_payload(root: Path, payload: dict[str, Any], *, project_id: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = list((payload.get("review") or {}).get("warnings") or [])
    unresolved: list[str] = list((payload.get("review") or {}).get("unresolved_questions") or [])

    workflow = str(payload.get("workflow") or "")
    prompt_strategy = str(payload.get("prompt_strategy") or "")
    is_sequence_v2 = workflow == msr_sequence_v2.WORKFLOW
    if is_sequence_v2 and prompt_strategy != msr_sequence_v2.PROMPT_STRATEGY:
        errors.append("msr_sequence_v2는 prompt_strategy=msr_continuity_v1이어야 합니다.")
    if prompt_strategy == msr_sequence_v2.PROMPT_STRATEGY and not is_sequence_v2:
        errors.append("msr_continuity_v1은 msr_sequence_v2 워크플로만 사용할 수 있습니다.")
    if is_sequence_v2 and payload.get("director_prompt_inheritance") is not False:
        errors.append("새 MSR 연속 생성은 director_prompt_inheritance=false여야 합니다.")

    requested = float(payload.get("requested_seconds") or 0)
    maximum_seconds = msr_sequence_v2.MAX_SECONDS if is_sequence_v2 else MAX_CLIP_SECONDS
    if requested <= 0:
        errors.append("requested_seconds가 0보다 커야 합니다.")
    elif requested > maximum_seconds:
        errors.append(f"requested_seconds({requested})가 {maximum_seconds}초를 초과합니다.")

    relay_total = _relay_total_seconds(payload)
    if abs(relay_total - requested) > 0.05:
        errors.append(f"Relay Segment 합계({relay_total})와 requested_seconds({requested})가 일치하지 않습니다.")

    references = payload.get("references") or []
    if not references:
        errors.append("references가 비어 있습니다.")
    if is_sequence_v2:
        try:
            normalized_references = msr_sequence_v2.normalize_references(list(references))
            expected_global = msr_sequence_v2.compile_global_prompt(
                str(payload.get("world_prompt") or ""), normalized_references
            )
            if str(payload.get("global_prompt") or "").strip() != expected_global:
                errors.append("global_prompt는 새 MSR 세계관·캐릭터·소품 필드에서 다시 컴파일해야 합니다.")
        except msr_sequence_v2.MSRSequenceValidationError as exc:
            errors.append(str(exc))
    seen_ids: set[int] = set()
    for ref in references:
        ref_id = int(ref.get("reference_id") or 0)
        if ref_id <= 0 or ref_id > 4:
            errors.append(f"잘못된 reference_id: {ref_id}")
        if ref_id in seen_ids:
            errors.append(f"중복 reference_id: {ref_id}")
        seen_ids.add(ref_id)
        source_path = str(ref.get("source_path") or "")
        if not source_path:
            errors.append(f"reference_id {ref_id} source_path가 비어 있습니다.")
        else:
            try:
                resolve_allowed_asset(root, source_path)
            except FileNotFoundError:
                errors.append(f"reference_id {ref_id} 이미지 없음: {source_path}")
            except PromptProjectError as exc:
                errors.append(f"reference_id {ref_id} 경로 오류: {exc}")

    background = payload.get("background") or {}
    bg_path = str(background.get("source_path") or "")
    if background.get("status") != "linked" and not bg_path:
        gen = payload.get("background_generation") or {}
        if not gen.get("prompt"):
            warnings.append("배경 생성 프롬프트가 비어 있습니다.")
        if not background.get("background_id"):
            errors.append("background.background_id가 필요합니다.")
    elif bg_path:
        try:
            resolve_allowed_asset(root, bg_path)
        except FileNotFoundError:
            errors.append(f"배경 이미지 없음: {bg_path}")
        except PromptProjectError as exc:
            errors.append(f"배경 경로 오류: {exc}")

    status = resolve_effective_status(payload, has_errors=bool(errors))
    return {
        "valid": not errors,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "unresolved_questions": unresolved,
        "requested_seconds": requested,
        "relay_total_seconds": relay_total,
        "background_linked": background.get("status") == "linked" or bool(bg_path),
        "background_id": background.get("background_id"),
    }


def _clip_sort_key(item: dict[str, Any]) -> tuple[str, int, str]:
    return (
        str(item.get("scene_id") or ""),
        int(item.get("sequence") or 0),
        str(item.get("clip_id") or ""),
    )


def _project_dir(root: Path, project_id: str) -> Path:
    project_id = str(project_id or "").strip()
    if not project_id or Path(project_id).name != project_id or project_id in {".", ".."}:
        raise PromptProjectError("허용되지 않는 프로젝트 ID입니다.")
    return prompt_projects_root(root) / project_id


def _clip_markdown_path(root: Path, project_id: str, clip_id: str) -> Path:
    clip_id = str(clip_id or "").strip()
    if not clip_id or Path(clip_id).name != clip_id or clip_id in {".", ".."}:
        raise PromptProjectError("허용되지 않는 clip_id입니다.")
    project_dir = _project_dir(root, project_id)
    scene_id = clip_id.rsplit("_", 1)[0]
    return project_dir / scene_id / f"{clip_id}.md"


def _project_runtime(root: Path, project_id: str) -> dict[str, Any]:
    catalog = load_background_catalog(root, project_id)
    links = load_background_links(root, project_id).get("links") or {}
    detected = scan_background_files(root, project_id)
    return {"catalog": catalog, "links": links, "detected": detected}


def parse_clip_markdown(
    root: Path,
    markdown_path: Path,
    *,
    project_id: str | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = markdown_path.read_text(encoding="utf-8")
    raw_payload = extract_machine_payload(text)
    project_id = project_id or raw_payload.get("project_id") or markdown_path.parent.parent.name
    runtime = runtime or _project_runtime(root, project_id)
    payload = merge_payload_background(
        root,
        project_id,
        raw_payload,
        links=runtime["links"],
        detected=runtime["detected"],
        catalog=runtime["catalog"],
    )
    validation = validate_machine_payload(root, payload, project_id=project_id)
    rel_path = markdown_path.relative_to(prompt_projects_root(root)).as_posix()
    background = payload.get("background") or {}
    return {
        "project_id": project_id,
        "clip_id": payload.get("clip_id") or markdown_path.stem,
        "scene_id": payload.get("scene_id") or markdown_path.parent.name,
        "sequence": int(payload.get("sequence") or 0),
        "status": validation["status"],
        "requested_seconds": validation["requested_seconds"],
        "markdown_path": rel_path,
        "summary": _extract_summary(text),
        "global_prompt_preview": str(payload.get("global_prompt") or "")[:240],
        "relay_segment_count": len(payload.get("relay_segments") or []),
        "previous_clip": payload.get("previous_clip"),
        "next_clip": payload.get("next_clip"),
        "warnings": validation["warnings"],
        "errors": validation["errors"],
        "unresolved_questions": validation["unresolved_questions"],
        "valid": validation["valid"],
        "background_id": background.get("background_id"),
        "background_linked": validation["background_linked"],
        "background_status": background.get("status"),
        "payload": payload,
    }


def _extract_summary(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("## Summary"):
            continue
        if line.startswith("## ") and "Summary" not in line:
            break
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def scan_project_clips(root: Path, project_id: str) -> list[dict[str, Any]]:
    project_dir = _project_dir(root, project_id)
    if not project_dir.is_dir():
        raise FileNotFoundError(f"프롬프트 프로젝트를 찾을 수 없습니다: {project_id}")
    runtime = _project_runtime(root, project_id)
    clips: list[dict[str, Any]] = []
    for md_path in sorted(project_dir.rglob("*.md")):
        try:
            item = parse_clip_markdown(root, md_path, project_id=project_id, runtime=runtime)
            clips.append({k: v for k, v in item.items() if k != "payload"})
        except Exception as exc:
            clip_id = md_path.stem
            scene_id = md_path.parent.name
            clips.append(
                {
                    "project_id": project_id,
                    "clip_id": clip_id,
                    "scene_id": scene_id,
                    "sequence": 0,
                    "status": "invalid",
                    "requested_seconds": 0,
                    "markdown_path": md_path.relative_to(prompt_projects_root(root)).as_posix(),
                    "summary": "",
                    "global_prompt_preview": "",
                    "relay_segment_count": 0,
                    "previous_clip": None,
                    "next_clip": None,
                    "warnings": [],
                    "errors": [str(exc)],
                    "unresolved_questions": [],
                    "valid": False,
                    "background_id": None,
                    "background_linked": False,
                    "background_status": "missing",
                }
            )
    clips.sort(key=_clip_sort_key)
    return clips


def list_prompt_projects_action(root: Path, _data: dict[str, Any] | None = None) -> dict[str, Any]:
    base = prompt_projects_root(root)
    projects: list[dict[str, Any]] = []
    if not base.is_dir():
        return {"projects": projects}
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        manifest_path = entry / "manifest.json"
        manifest = {}
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
                "reviewed_count": sum(1 for clip in clips if clip["status"] == "reviewed"),
                "needs_confirmation_count": sum(1 for clip in clips if clip["status"] == "needs_confirmation"),
                "awaiting_background_count": sum(1 for clip in clips if clip["status"] == "awaiting_background"),
                "invalid_count": sum(1 for clip in clips if clip["status"] == "invalid"),
            }
        )
    return {"projects": projects}


def list_prompt_project_clips_action(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = str(data.get("project_id") or "")
    clips = scan_project_clips(root, project_id)
    scenes: dict[str, list[dict[str, Any]]] = {}
    for clip in clips:
        scenes.setdefault(clip["scene_id"], []).append(clip)
    return {
        "project_id": project_id,
        "clips": clips,
        "scenes": [{"scene_id": scene_id, "clips": scene_clips} for scene_id, scene_clips in sorted(scenes.items())],
    }


def list_project_backgrounds_action(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = str(data.get("project_id") or "")
    catalog = load_background_catalog(root, project_id)
    links_payload = load_background_links(root, project_id)
    detected = scan_background_files(root, project_id)
    backgrounds = []
    instant_ready = is_sequence_v2_project(root, project_id)
    for background_id, entry in sorted((catalog.get("backgrounds") or {}).items()):
        resolved = resolve_background_link(root, project_id, background_id, links=links_payload.get("links"), detected=detected, catalog=catalog)
        backgrounds.append(
            {
                **entry,
                "linked": bool(resolved),
                "source_path": resolved["source_path"] if resolved else None,
                "filename": resolved["filename"] if resolved else entry.get("suggested_filename"),
                "asset_url": _background_asset_url(project_id, resolved["filename"]) if resolved else None,
                "review_status": "approved" if instant_ready and resolved else (resolved["review_status"] if resolved else "pending"),
                "reviewed_at": resolved["reviewed_at"] if resolved else None,
                "review_notes": [] if instant_ready else (resolved["review_notes"] if resolved else []),
                "review_checklist": {} if instant_ready else (resolved["review_checklist"] if resolved else {}),
                "linked_at": resolved["linked_at"] if resolved else None,
                "replaced_at": resolved["replaced_at"] if resolved else None,
                "previous_review_notes": resolved["previous_review_notes"] if resolved else [],
                "background_generation": build_background_generation(entry),
            }
        )
    return {
        "project_id": project_id,
        "backgrounds": backgrounds,
        "detected_files": detected,
        "links": links_payload.get("links") or {},
        "backgrounds_dir": f"{PROMPT_PROJECTS_DIR_NAME}/{project_id}/backgrounds/",
    }


def save_background_link_action(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = str(data.get("project_id") or "")
    background_id = str(data.get("background_id") or "").strip()
    filename = _safe_filename(str(data.get("filename") or ""))
    if not background_id:
        raise PromptProjectError("background_id가 필요합니다.")
    upload_path = str(data.get("upload_path") or "").strip()
    if upload_path:
        src = Path(upload_path).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(f"업로드 파일을 찾을 수 없습니다: {upload_path}")
        folder = project_backgrounds_dir(root, project_id)
        folder.mkdir(parents=True, exist_ok=True)
        dest = _resolve_under(folder, filename)
        shutil.copy2(src, dest)
    source_path = background_source_path(project_id, filename)
    resolve_allowed_asset(root, source_path)
    links_payload = load_background_links(root, project_id)
    links = dict(links_payload.get("links") or {})
    previous = links.get(background_id) if isinstance(links.get(background_id), dict) else {}
    link_entry: dict[str, Any] = {
        "filename": filename,
        "source_path": source_path,
        "linked_at": datetime.now(timezone.utc).isoformat(),
    }
    if upload_path:
        instant_ready = is_sequence_v2_project(root, project_id)
        link_entry["review_status"] = "approved" if instant_ready else "pending"
        link_entry["review_notes"] = []
        link_entry["review_checklist"] = {}
        link_entry["reviewed_at"] = datetime.now(timezone.utc).isoformat() if instant_ready else None
        link_entry["replaced_at"] = datetime.now(timezone.utc).isoformat()
        if previous.get("review_status") == "changes_required":
            link_entry["previous_review_notes"] = list(previous.get("review_notes") or [])
    else:
        for key in ("review_status", "review_notes", "review_checklist", "reviewed_at"):
            if key in previous:
                link_entry[key] = previous[key]
    links[background_id] = link_entry
    saved = save_background_links(root, project_id, links)
    resolved = resolve_background_link(root, project_id, background_id, links=links)
    return {"project_id": project_id, "background_id": background_id, "link": links[background_id], "resolved": resolved, "links": saved.get("links") or {}}


def _background_asset_url(project_id: str, filename: str) -> str:
    return f"/api/msr-prompt-assets/{quote(project_id, safe='')}/backgrounds/{quote(_safe_filename(filename), safe='')}"


def _asset_url(project_id: str, source_path: str) -> str | None:
    rel = _normalize_relative_path(source_path)
    if not rel:
        return None
    if rel.startswith(f"{PROMPT_PROJECTS_DIR_NAME}/"):
        _, project_and_rest = rel.split("/", 1)
        pid, _, remainder = project_and_rest.partition("/")
        if remainder.startswith("backgrounds/"):
            return _background_asset_url(pid, remainder.split("/", 1)[1])
        return None
    if "/" not in rel:
        return None
    _, _, remainder = rel.partition("/")
    return f"/api/msr-prompt-assets/{quote(project_id, safe='')}/{quote(remainder, safe='/')}"


def get_prompt_project_clip_action(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = str(data.get("project_id") or "")
    clip_id = str(data.get("clip_id") or "")
    md_path = _clip_markdown_path(root, project_id, clip_id)
    if not md_path.is_file():
        raise FileNotFoundError(f"클립 Markdown을 찾을 수 없습니다: {clip_id}")
    item = parse_clip_markdown(root, md_path, project_id=project_id)
    payload = item.pop("payload")
    background = payload.get("background") or {}
    asset_urls = {
        "references": [
            {
                **ref,
                "asset_url": _asset_url(project_id, str(ref.get("source_path") or "")),
            }
            for ref in payload.get("references") or []
        ],
        "background": {
            **background,
            "asset_url": _asset_url(project_id, str(background.get("source_path") or "")),
        },
    }
    can_register = item["status"] == "reviewed"
    background_review = str((payload.get("background") or {}).get("review_status") or "")
    block_reason = None
    if not can_register:
        instant_ready = payload.get("workflow") == msr_sequence_v2.WORKFLOW and payload.get("prompt_strategy") == msr_sequence_v2.PROMPT_STRATEGY
        if instant_ready and item["status"] == "awaiting_background":
            block_reason = "통합 앵커 이미지가 등록되지 않았습니다. 이미지를 등록하면 즉시 생성할 수 있습니다."
        elif background_review == "changes_required":
            block_reason = "배경 검수에서 수정이 필요합니다. 배경을 교체한 뒤 재검수하세요."
        elif background_review == "pending":
            block_reason = "배경 검수가 아직 완료되지 않았습니다."
        elif item["status"] == "awaiting_background":
            block_reason = "배경 이미지가 연결되지 않았습니다."
        else:
            block_reason = "프롬프트 확인 또는 오류 해결이 필요합니다."
    return {
        **item,
        "machine_payload": payload,
        "asset_urls": asset_urls,
        "can_register_msr": can_register,
        "registration_block_reason": block_reason,
    }


def resolve_prompt_asset_action(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = str(data.get("project_id") or "")
    rel_asset = _normalize_relative_path(str(data.get("asset_path") or ""))
    if not is_safe_relative_path(rel_asset):
        raise PromptProjectError("허용되지 않는 asset_path입니다.")
    if rel_asset.startswith("backgrounds/"):
        filename = _safe_filename(rel_asset.split("/", 1)[1])
        path = _resolve_under(project_backgrounds_dir(root, project_id), filename)
        if not path.is_file():
            raise FileNotFoundError(f"배경 파일을 찾을 수 없습니다: {filename}")
        source_path = background_source_path(project_id, filename)
        return {"path": str(path), "source_path": source_path}
    source_path = f"{SCENARIO_PROJECT_DIR_NAME}/{rel_asset}"
    path = resolve_allowed_asset(root, source_path)
    return {"path": str(path), "source_path": source_path}


def resolve_msr_upload_path(root: Path, row: dict[str, Any]) -> Path:
    upload_path = str(row.get("upload_path") or "").strip()
    if upload_path:
        path = Path(upload_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"업로드 파일을 찾을 수 없습니다: {upload_path}")
        return path
    source_path = str(row.get("source_path") or "").strip()
    if source_path:
        return resolve_allowed_asset(root, source_path)
    raise ValueError("upload_path 또는 source_path가 필요합니다.")
