from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import director_prompt_projects as projects


def _location_registry(root: Path, project_id: str) -> dict[str, Any]:
    path = projects._project_dir(root, project_id) / "location_registry.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise projects.DirectorPromptProjectError(
            f"location_registry.json 파싱 실패: {exc}"
        ) from exc
    locations = payload.get("locations") or {}
    if not isinstance(locations, dict):
        raise projects.DirectorPromptProjectError(
            "location_registry.locations는 객체여야 합니다."
        )
    return locations


def _background_prompt_status(image_generation: dict[str, Any]) -> str:
    prompt = str(
        image_generation.get("generation_prompt")
        or image_generation.get("prompt")
        or ""
    ).strip()
    source_path = str(image_generation.get("source_path") or "").strip()
    review_status = str(
        image_generation.get("review_status") or "pending"
    ).strip().lower()
    if not prompt:
        return "prompt_required"
    if not source_path:
        return "awaiting_background_image"
    if review_status == "changes_required":
        return "image_changes_required"
    if review_status != "approved":
        return "image_review_required"
    return "ready"


def _clip_prompt_stats(payload: dict[str, Any]) -> dict[str, int]:
    segments = payload.get("segments") or []
    standalone = 0
    legacy = 0
    missing = 0
    for segment in segments:
        image = segment.get("scene_image") or {}
        if str(image.get("generation_prompt") or "").strip():
            standalone += 1
        elif str(image.get("prompt") or "").strip():
            legacy += 1
        else:
            missing += 1
    return {
        "standalone_prompt_count": standalone,
        "legacy_prompt_count": legacy,
        "missing_prompt_count": missing,
    }


def project_overview_action(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = projects._safe_component(data.get("project_id"), "project_id")
    locations = _location_registry(root, project_id)
    clips = projects.scan_project_clips(root, project_id)
    groups: dict[str, dict[str, Any]] = {}

    for location_id, raw in locations.items():
        location = dict(raw or {})
        image_generation = dict(
            location.get("image_generation")
            or location.get("background_image")
            or {}
        )
        background_id = str(
            location.get("background_id") or f"BG_{location_id}"
        )
        groups[str(location_id)] = {
            "location_id": str(location_id),
            "background_id": background_id,
            "display_name": str(
                location.get("display_name") or location_id
            ),
            "description": str(
                location.get("description")
                or location.get("terrain")
                or ""
            ),
            "terrain": str(location.get("terrain") or ""),
            "structures": str(location.get("structures") or ""),
            "lighting": str(location.get("lighting") or ""),
            "color_palette": str(location.get("color_palette") or ""),
            "fixed_elements": list(location.get("fixed_elements") or []),
            "image_generation": {
                **image_generation,
                "generation_prompt": str(
                    image_generation.get("generation_prompt")
                    or image_generation.get("prompt")
                    or ""
                ),
                "negative_prompt": str(
                    image_generation.get("negative_prompt") or ""
                ),
                "status": _background_prompt_status(image_generation),
            },
            "clips": [],
        }

    enriched_clips: list[dict[str, Any]] = []
    for clip in clips:
        markdown_path = projects.projects_root(root) / clip["markdown_path"]
        location_id = ""
        background_id = ""
        stats = {
            "standalone_prompt_count": 0,
            "legacy_prompt_count": 0,
            "missing_prompt_count": 0,
        }
        try:
            payload = projects.extract_machine_payload(
                markdown_path.read_text(encoding="utf-8")
            )
            location = payload.get("location") or {}
            location_id = str(location.get("location_id") or "")
            group = groups.get(location_id)
            background_id = str(
                (group or {}).get("background_id")
                or location.get("background_id")
                or ""
            )
            stats = _clip_prompt_stats(payload)
        except Exception as exc:
            clip = {
                **clip,
                "status": "invalid",
                "valid": False,
                "errors": [*(clip.get("errors") or []), str(exc)],
            }
        enriched = {
            **clip,
            "location_id": location_id,
            "background_id": background_id,
            **stats,
        }
        enriched_clips.append(enriched)
        if location_id not in groups:
            groups[location_id or "__unassigned__"] = {
                "location_id": location_id,
                "background_id": background_id,
                "display_name": location_id or "배경 미지정",
                "description": "",
                "terrain": "",
                "structures": "",
                "lighting": "",
                "color_palette": "",
                "fixed_elements": [],
                "image_generation": {
                    "generation_prompt": "",
                    "negative_prompt": "",
                    "status": "prompt_required",
                },
                "clips": [],
            }
        groups[location_id or "__unassigned__"]["clips"].append(enriched)

    background_groups = sorted(
        groups.values(),
        key=lambda item: (item["display_name"], item["location_id"]),
    )
    return {
        "project_id": project_id,
        "clips": enriched_clips,
        "background_groups": background_groups,
        "summary": {
            "background_group_count": len(background_groups),
            "background_prompt_ready_count": sum(
                bool(
                    group["image_generation"].get("generation_prompt")
                )
                for group in background_groups
            ),
            "standalone_segment_prompt_count": sum(
                clip["standalone_prompt_count"] for clip in enriched_clips
            ),
            "legacy_segment_prompt_count": sum(
                clip["legacy_prompt_count"] for clip in enriched_clips
            ),
        },
    }
