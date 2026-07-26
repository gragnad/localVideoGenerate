from __future__ import annotations

import copy
from pathlib import PurePosixPath
from typing import Any


VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".gif"}


def _find_single_node(
    workflow: dict[str, Any],
    class_type: str,
) -> tuple[str, dict[str, Any]]:
    matches = [
        (node_id, node)
        for node_id, node in workflow.items()
        if isinstance(node, dict) and node.get("class_type") == class_type
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{class_type} 노드는 정확히 1개여야 합니다. 현재 개수: {len(matches)}"
        )
    return matches[0]


def find_primary_video_output(
    outputs: list[dict[str, Any]],
) -> dict[str, str] | None:
    for item in outputs:
        filename = str(item.get("filename") or "")
        if PurePosixPath(filename).suffix.lower() in VIDEO_SUFFIXES:
            return {
                "filename": filename,
                "subfolder": str(item.get("subfolder") or ""),
                "type": str(item.get("type") or "output"),
            }
    return None


def comfy_video_path(file_info: dict[str, str]) -> str:
    """VHS_LoadVideoPath가 읽을 ComfyUI 상대 경로를 만듭니다."""
    file_type = str(file_info.get("type") or "output").strip("/")
    subfolder = str(file_info.get("subfolder") or "").strip("/")
    filename = str(file_info.get("filename") or "").strip("/")

    if not filename:
        raise ValueError("원본 영상 출력 정보에 filename이 없습니다.")

    parts = [file_type]
    if subfolder:
        parts.append(subfolder)
    parts.append(filename)
    return str(PurePosixPath(*parts))


def build_contact_sheet_workflow(
    *,
    template: dict[str, Any],
    source_video_path: str,
    filename_prefix: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    workflow = copy.deepcopy(template)
    load_id, load_video = _find_single_node(workflow, "VHS_LoadVideoPath")
    save_id, save_image = _find_single_node(workflow, "SaveImage")

    if not source_video_path.strip():
        raise ValueError("Contact Sheet 원본 영상 경로가 비어 있습니다.")
    if not filename_prefix.strip():
        raise ValueError("Contact Sheet 출력 prefix가 비어 있습니다.")

    load_video.setdefault("inputs", {})["video"] = source_video_path
    save_image.setdefault("inputs", {})["filename_prefix"] = filename_prefix

    load_video.setdefault("_meta", {})["title"] = "[INPUT_VIDEO] 검수할 영상 경로"
    save_image.setdefault("_meta", {})["title"] = (
        "[OUTPUT_CONTACT_SHEET] 검수 시트 저장"
    )

    summary = {
        "source_video_path": source_video_path,
        "filename_prefix": filename_prefix,
        "load_video_node": load_id,
        "save_image_node": save_id,
        "sample_count": 12,
        "grid": {"columns": 4, "rows": 3, "cell_width": 256, "cell_height": 144},
    }
    return workflow, summary
