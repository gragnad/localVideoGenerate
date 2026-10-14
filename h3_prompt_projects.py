from __future__ import annotations

"""H3 R2V and first-frame I2V production prompt projects.

The schema is deliberately small so a prompt-authoring session can create or
edit H3 projects through one compact, versioned format.
"""

import json
import hashlib
import re
from pathlib import Path
from typing import Any

import h3_prompt_contract


PROJECT_KIND = "h3_r2v_production"
WORKFLOW = "h3_r2v_production"
I2V_PROJECT_KIND = "h3_i2v_production"
I2V_WORKFLOW = "h3_i2v_production"
ACTION_ASSET_PROJECT_KIND = "action_asset_project"
PROJECT_KIND_MODES = {
    PROJECT_KIND: "r2v",
    I2V_PROJECT_KIND: "i2v",
    ACTION_ASSET_PROJECT_KIND: "r2v",
}
WORKFLOW_MODES = {WORKFLOW: "r2v", I2V_WORKFLOW: "i2v"}
PROTECTED_PROJECT_IDS = {"H3_PROJECT_TEMPLATE", "H3_I2V_PROJECT_TEMPLATE"}
LEGACY_EVENT_CONTRACT_VERSION = "independent_shot_plans_v2"
GRID_EVENT_CONTRACT_VERSION = "locked_storyboard_shot_plans_v3"
GRID_FREE_EVENT_CONTRACT_VERSION = "locked_storyboard_shot_plans_v4"
EVENT_CONTRACT_VERSION = "locked_storyboard_shot_plans_v5"
ACTION_SCENE_TYPE = "action"
ACTION_PROMPT_PROFILE = "h3_action_scene_v1"
ACTION_PROMPT_GENERATOR = "h3_action_scene_prompt_generator_v1"
ACTION_SCENE_CONTRACT_VERSION = "action_scene_contract_v1"
ISOLATED_ACTION_STORYBOARD_MODE = "delegated_entry_storyboard_action_delegated_exit_v1"
FOUR_SHOT_TEMPORAL_STORYBOARD_MODE = "four_storyboard_panels_four_timed_action_shots_v1"
SIX_SHOT_TEMPORAL_STORYBOARD_MODE = "six_storyboard_panels_six_timed_shots_v1"
FOUR_SHOT_TEXT_DIRECTED_MODE = "four_text_directed_timed_action_shots_v1"
FOUR_SUBJECT_STATE_ACTION_MODE = "four_subject_state_action_shots_v2"
FOUR_OBJECT_ACTION_PAIRS_MODE = "four_object_action_pairs_v1"
FOUR_DESCRIBED_OBJECT_BEHAVIOR_MODE = "four_described_object_behavior_shots_v1"
# Backward-compatible name used by the first action-only pilot. The mode is now
# intentionally genre-neutral and applies to any four-panel temporal storyboard.
FOUR_SHOT_ACTION_STORYBOARD_MODE = FOUR_SHOT_TEMPORAL_STORYBOARD_MODE
# Backward-compatible import name for older local specs; new code should use the
# isolated 3-Shot name above.
SINGLE_SHOT_ACTION_STORYBOARD_MODE = ISOLATED_ACTION_STORYBOARD_MODE
SUPPORTED_EVENT_CONTRACT_VERSIONS = frozenset({
    LEGACY_EVENT_CONTRACT_VERSION,
    GRID_EVENT_CONTRACT_VERSION,
    GRID_FREE_EVENT_CONTRACT_VERSION,
    EVENT_CONTRACT_VERSION,
})
PAYLOAD_RE = re.compile(r"## Machine Payload\s*```json\s*(\{.*?\})\s*```", re.DOTALL)
DETAILED_DESCRIPTION_RE = re.compile(
    r"^detailed_description:[ \t]*\n(.*?)(?=^[ \t]*overall_soundscape:[ \t]*$)",
    re.DOTALL | re.MULTILINE,
)


def _safe(value: str, label: str) -> str:
    value = str(value or "").strip()
    if not value or Path(value).name != value or value in {".", ".."}:
        raise ValueError(f"올바른 {label}이(가) 아닙니다.")
    return value


def projects_root(root: Path) -> Path:
    return root / "prompt_projects"


def project_dir(root: Path, project_id: str) -> Path:
    return projects_root(root) / _safe(project_id, "H3 프로젝트 ID")


def project_manifest(root: Path, project_id: str) -> dict[str, Any]:
    """Read one prompt-project manifest without loading every clip."""
    path = project_dir(root, project_id) / "manifest.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise ValueError("H3 프로젝트 manifest.json을 읽을 수 없습니다.") from exc
    if not isinstance(payload, dict):
        raise ValueError("H3 프로젝트 manifest.json은 JSON 객체여야 합니다.")
    return payload


def project_generation_block_reason(root: Path, project_id: str) -> str | None:
    """Return the fail-closed reason for a superseded/read-only project."""
    if not (project_dir(root, project_id) / "manifest.json").is_file():
        return None
    manifest = project_manifest(root, project_id)
    if not bool(manifest.get("generation_blocked")):
        return None
    reason = str(manifest.get("generation_block_reason") or "").strip()
    replacements = [
        str(value).strip()
        for value in manifest.get("replacement_project_ids") or []
        if str(value).strip()
    ]
    if replacements:
        suffix = ", ".join(replacements)
        reason = f"{reason} 대체 프로젝트: {suffix}" if reason else f"대체 프로젝트: {suffix}"
    return reason or "이 프로젝트는 신규 영상 생성이 차단된 읽기 전용 프로젝트입니다."


def action_scene_routing_errors(payload: dict[str, Any]) -> list[str]:
    """Validate the explicit action-scene generator route stored in a clip."""
    if str(payload.get("scene_type") or "").strip() != ACTION_SCENE_TYPE:
        return []
    errors: list[str] = []
    if str(payload.get("prompt_profile") or "").strip() != ACTION_PROMPT_PROFILE:
        errors.append(
            f"액션 씬은 prompt_profile={ACTION_PROMPT_PROFILE}을 사용해야 합니다."
        )
    if str(payload.get("prompt_generator") or "").strip() != ACTION_PROMPT_GENERATOR:
        errors.append(
            f"액션 씬은 prompt_generator={ACTION_PROMPT_GENERATOR}를 사용해야 합니다."
        )
    contract = payload.get("action_scene_contract")
    if not isinstance(contract, dict):
        errors.append("액션 씬에는 action_scene_contract가 필요합니다.")
        return errors
    if str(contract.get("version") or "") != ACTION_SCENE_CONTRACT_VERSION:
        errors.append(
            f"action_scene_contract.version은 {ACTION_SCENE_CONTRACT_VERSION}이어야 합니다."
        )
    if not str(contract.get("phase") or "").strip():
        errors.append("action_scene_contract.phase가 비어 있습니다.")
    speed_profiles = contract.get("speed_profiles") or []
    motion_links = contract.get("motion_links") or []
    if not isinstance(speed_profiles, list) or len(speed_profiles) != 4:
        errors.append("액션 씬은 Shot 1~4의 speed_profiles 네 개가 필요합니다.")
    if not isinstance(motion_links, list) or len(motion_links) != 3:
        errors.append("액션 씬은 Shot 사이 motion_links 세 개가 필요합니다.")
    if not str(contract.get("environmental_proof") or "").strip():
        errors.append("액션 씬에는 environmental_proof가 필요합니다.")
    variants = payload.get("prompt_variants") or []
    prompts = variants or [{
        "variant_id": "video_prompt",
        "video_prompt": payload.get("video_prompt"),
    }]
    for variant in prompts:
        variant_id = str(variant.get("variant_id") or "?")
        prompt = str(variant.get("video_prompt") or variant.get("prompt") or "")
        storyboard_mode = str(contract.get("storyboard_mode") or "").strip()
        if storyboard_mode == ISOLATED_ACTION_STORYBOARD_MODE:
            if "Action timing:" in prompt:
                errors.append(
                    f"액션 후보 {variant_id}에는 Action timing 라벨을 사용하지 않습니다."
                )
            if not re.search(
                r"in this order:\s*top-left,\s*top-right,\s*bottom-left,\s*bottom-right",
                prompt,
                re.IGNORECASE,
            ):
                errors.append(
                    f"액션 후보 {variant_id}는 스토리보드 패널 순서를 명시해야 합니다."
                )
        elif storyboard_mode == FOUR_SHOT_ACTION_STORYBOARD_MODE:
            if "Action timing:" in prompt:
                errors.append(
                    f"액션 후보 {variant_id}에는 Action timing 라벨을 사용하지 않습니다."
                )
            storyboard_picture_id = int(
                contract.get("storyboard_picture_id") or 0
            )
            if storyboard_picture_id <= 0 or prompt.count(
                f"<Picture {storyboard_picture_id}>"
            ) < 5:
                errors.append(
                    f"액션 후보 {variant_id}는 storyboard Picture 정의와 네 Shot 연결이 필요합니다."
                )
        elif storyboard_mode == FOUR_SHOT_TEXT_DIRECTED_MODE:
            if "Action timing:" in prompt:
                errors.append(
                    f"텍스트 지시형 액션 후보 {variant_id}에는 Action timing 라벨을 사용하지 않습니다."
                )
            detail = extract_detailed_description(prompt)
            shots = list(h3_prompt_contract.SHOT_RE.finditer(detail))
            if len(shots) != 4:
                errors.append(
                    f"텍스트 지시형 액션 후보 {variant_id}는 4개 Shot이 필요합니다."
                )
            background_picture_id = int(contract.get("background_picture_id") or 0)
            effect_picture_id = int(contract.get("effect_picture_id") or 0)
            if (
                background_picture_id <= 0
                or effect_picture_id <= 0
                or background_picture_id == effect_picture_id
            ):
                errors.append(
                    f"텍스트 지시형 액션 후보 {variant_id}에는 서로 다른 배경/이펙트 Picture ID가 필요합니다."
                )
            for shot_number, shot in enumerate(shots, start=1):
                body = shot.group(4)
                if body.count("Starting composition:") != 1 or body.count("Following action:") != 1:
                    errors.append(
                        f"텍스트 지시형 액션 후보 {variant_id} Shot {shot_number}에는 "
                        "Starting composition과 Following action이 각각 한 번 필요합니다."
                    )
                    continue
                composition = body.split("Starting composition:", 1)[1].split(
                    "Following action:", 1
                )[0]
                action = body.split("Following action:", 1)[1]
                if background_picture_id > 0 and f"<Picture {background_picture_id}>" not in composition:
                    errors.append(
                        f"텍스트 지시형 액션 후보 {variant_id} Shot {shot_number}의 "
                        "Starting composition에는 배경 Picture 연결이 필요합니다."
                    )
                if effect_picture_id > 0 and f"<Picture {effect_picture_id}>" not in composition:
                    errors.append(
                        f"텍스트 지시형 액션 후보 {variant_id} Shot {shot_number}의 "
                        "Starting composition에는 이펙트 Picture 연결이 필요합니다."
                    )
                if not re.search(r"<Subject \d+>,\s+the\s+[^.;]+", composition):
                    errors.append(
                        f"텍스트 지시형 액션 후보 {variant_id} Shot {shot_number}의 "
                        "Starting composition에는 Subject 태그와 간략 설명이 필요합니다."
                    )
                if not re.search(r"<Subject \d+>,\s+the\s+[^.;]+", action):
                    errors.append(
                        f"텍스트 지시형 액션 후보 {variant_id} Shot {shot_number}의 "
                        "Following action에는 Subject 태그와 간략 설명이 필요합니다."
                    )
        elif storyboard_mode == FOUR_SUBJECT_STATE_ACTION_MODE:
            if "Action timing:" in prompt:
                errors.append(
                    f"Subject-State-Action 후보 {variant_id}에는 Action timing 라벨을 사용하지 않습니다."
                )
            detail = extract_detailed_description(prompt)
            shots = list(h3_prompt_contract.SHOT_RE.finditer(detail))
            if len(shots) != 4:
                errors.append(f"Subject-State-Action 후보 {variant_id}는 4개 Shot이 필요합니다.")
            background_picture_id = int(contract.get("background_picture_id") or 0)
            effect_picture_id = int(contract.get("effect_picture_id") or 0)
            for shot_number, shot in enumerate(shots, start=1):
                body = shot.group(4)
                if body.count("Starting state:") != 1 or body.count("Action:") != 1:
                    errors.append(
                        f"Subject-State-Action 후보 {variant_id} Shot {shot_number}에는 "
                        "Starting state와 Action이 각각 한 번 필요합니다."
                    )
                    continue
                header = body.split("Starting state:", 1)[0]
                action = body.split("Action:", 1)[1]
                if not re.search(
                    r"<(?:Subject|Picture) \d+>,\s+the\s+[^.;]+", header
                ):
                    errors.append(
                        f"Subject-State-Action 후보 {variant_id} Shot {shot_number}은 "
                        "관련 Subject 또는 Picture 태그와 간략 설명으로 시작해야 합니다."
                    )
                if re.search(r"<Subject \d+>,\s+the\s+[^.;]+", action):
                    errors.append(
                        f"Subject-State-Action 후보 {variant_id} Shot {shot_number}의 "
                        "Action에서 Subject 설명을 반복하지 않습니다."
                    )
                if background_picture_id <= 0 or f"<Picture {background_picture_id}>" not in header:
                    errors.append(
                        f"Subject-State-Action 후보 {variant_id} Shot {shot_number}에는 배경 Picture가 필요합니다."
                    )
                if effect_picture_id <= 0 or f"<Picture {effect_picture_id}>" not in header:
                    errors.append(
                        f"Subject-State-Action 후보 {variant_id} Shot {shot_number}에는 이펙트 Picture가 필요합니다."
                    )
        elif storyboard_mode == FOUR_OBJECT_ACTION_PAIRS_MODE:
            detail = extract_detailed_description(prompt)
            shots = list(h3_prompt_contract.SHOT_RE.finditer(detail))
            if len(shots) != 4:
                errors.append(f"Object-Behavior 후보 {variant_id}는 4개 Shot이 필요합니다.")
            background_picture_id = int(contract.get("background_picture_id") or 0)
            effect_picture_id = int(contract.get("effect_picture_id") or 0)
            for shot_number, shot in enumerate(shots, start=1):
                body = shot.group(4).strip()
                if not body.startswith(("<Subject ", "<Picture ")):
                    errors.append(
                        f"Object-Behavior 후보 {variant_id} Shot {shot_number}은 객체 태그로 시작해야 합니다."
                    )
                if "Starting state:" in body or re.search(r"(?<!Object )Action:", body):
                    errors.append(
                        f"Object-Behavior 후보 {variant_id} Shot {shot_number}에는 공통 State/Action 덩어리를 쓰지 않습니다."
                    )
                object_tags = list(
                    re.finditer(r"<(Subject|Picture) (\d+)>\s+(?!\()", body)
                )
                if not object_tags:
                    errors.append(
                        f"Object-Behavior 후보 {variant_id} Shot {shot_number}에는 객체 태그와 상태·행동 문장이 필요합니다."
                    )
                    continue
                for index, tag in enumerate(object_tags):
                    end = object_tags[index + 1].start() if index + 1 < len(object_tags) else len(body)
                    segment = body[tag.start():end]
                    after_tag = segment[tag.end() - tag.start():].strip()
                    if not after_tag or re.match(r"^[,:;\-]", after_tag):
                        errors.append(
                            f"Object-Behavior 후보 {variant_id} Shot {shot_number}의 "
                            f"<{tag.group(1)} {tag.group(2)}> 뒤에는 구두점 없이 상태·행동을 바로 써야 합니다."
                        )
                if f"<Picture {background_picture_id}>" not in body:
                    errors.append(f"Object-Behavior 후보 {variant_id} Shot {shot_number}에는 배경 객체가 필요합니다.")
                if f"<Picture {effect_picture_id}>" not in body:
                    errors.append(f"Object-Behavior 후보 {variant_id} Shot {shot_number}에는 이펙트 객체가 필요합니다.")
        elif storyboard_mode == FOUR_DESCRIBED_OBJECT_BEHAVIOR_MODE:
            detail = extract_detailed_description(prompt)
            shots = list(h3_prompt_contract.SHOT_RE.finditer(detail))
            if len(shots) != 4:
                errors.append(f"Described-Object 후보 {variant_id}는 4개 Shot이 필요합니다.")
            background_picture_id = int(contract.get("background_picture_id") or 0)
            effect_picture_id = int(contract.get("effect_picture_id") or 0)
            for shot_number, shot in enumerate(shots, start=1):
                body = shot.group(4).strip()
                if any(label in body for label in ("Starting state:", "Action:", "Behavior:")):
                    errors.append(
                        f"Described-Object 후보 {variant_id} Shot {shot_number}에는 State/Action/Behavior 라벨을 쓰지 않습니다."
                    )
                tags = list(
                    re.finditer(r"<(Subject|Picture) (\d+)>\s+the\s+", body, re.IGNORECASE)
                )
                if not tags or not body.startswith(("<Subject ", "<Picture ")):
                    errors.append(
                        f"Described-Object 후보 {variant_id} Shot {shot_number}은 객체 태그로 시작해야 합니다."
                    )
                    continue
                for index, tag in enumerate(tags):
                    end = tags[index + 1].start() if index + 1 < len(tags) else len(body)
                    segment = body[tag.end():end].strip()
                    if not segment or re.match(r"^[,:;\-]", segment):
                        errors.append(
                            f"Described-Object 후보 {variant_id} Shot {shot_number}의 "
                            f"<{tag.group(1)} {tag.group(2)}> 뒤에는 구두점 없이 설명·상태·행동을 이어 써야 합니다."
                        )
                if f"<Picture {background_picture_id}>" not in body:
                    errors.append(f"Described-Object 후보 {variant_id} Shot {shot_number}에는 배경 객체가 필요합니다.")
                if f"<Picture {effect_picture_id}>" not in body:
                    errors.append(f"Described-Object 후보 {variant_id} Shot {shot_number}에는 이펙트 객체가 필요합니다.")
        elif prompt.count("Action timing:") != 4:
            errors.append(
                f"액션 후보 {variant_id}는 각 Shot에 Action timing을 한 번씩 기록해야 합니다."
            )
        if "reference-sheet background" not in prompt:
            errors.append(
                f"액션 후보 {variant_id}에는 참조 시트 배경 출력 금지가 필요합니다."
            )
    return errors


def extract_payload(text: str) -> dict[str, Any]:
    match = PAYLOAD_RE.search(text)
    if not match:
        raise ValueError("H3 클립에 ## Machine Payload JSON 블록이 없습니다.")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise ValueError("H3 Machine Payload는 JSON 객체여야 합니다.")
    return payload


def extract_detailed_description(prompt: str) -> str:
    match = DETAILED_DESCRIPTION_RE.search(str(prompt or ""))
    return match.group(1).strip() if match else ""


def normalize_prompt_variants(raw: Any) -> list[dict[str, Any]]:
    """Normalize the three independent R2V prompts stored by a clip."""
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        raise ValueError("prompt_variants는 JSON 배열이어야 합니다.")
    variants: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError("prompt_variants의 각 항목은 JSON 객체여야 합니다.")
        variant_id = str(item.get("variant_id") or chr(64 + index)).strip().upper()
        if not variant_id or variant_id in seen:
            raise ValueError("prompt_variants의 variant_id는 비어 있거나 중복될 수 없습니다.")
        prompt = str(item.get("video_prompt") or item.get("prompt") or "").strip()
        if not prompt:
            raise ValueError(f"후보 {variant_id}의 video_prompt가 비어 있습니다.")
        seen.add(variant_id)
        variants.append({
            "variant_id": variant_id,
            "label": str(item.get("label") or f"후보 {variant_id}").strip(),
            "rationale": str(item.get("rationale") or "").strip(),
            "video_prompt": prompt,
            "detailed_description": extract_detailed_description(prompt),
        })
    return variants


def _asset_path(root: Path, project_id: str, source_path: str) -> Path:
    base = project_dir(root, project_id).resolve()
    raw = str(source_path or "").strip()
    if not raw:
        raise FileNotFoundError("연결된 프로젝트 이미지가 없습니다.")
    candidate = (base / raw).resolve()
    if candidate == base or base not in candidate.parents:
        raise ValueError("H3 프로젝트 자산은 해당 프로젝트 폴더 안에 있어야 합니다.")
    if not candidate.is_file():
        raise FileNotFoundError(f"H3 프로젝트 이미지를 찾을 수 없습니다: {raw}")
    if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("H3 프로젝트 자산은 PNG, JPG, WEBP 이미지만 지원합니다.")
    return candidate


def _normalize_payload(root: Path, project_id: str, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    workflow = str(payload.get("workflow") or "")
    generation_mode = WORKFLOW_MODES.get(workflow)
    if not generation_mode:
        raise ValueError(
            f"workflow는 {WORKFLOW} 또는 {I2V_WORKFLOW} 형식이어야 합니다."
        )
    if str(payload.get("project_id") or "") != project_id:
        raise ValueError("Machine Payload의 project_id가 프로젝트 폴더와 다릅니다.")
    scene_id = _safe(str(payload.get("scene_id") or path.parent.name), "씬 ID")
    clip_id = _safe(str(payload.get("clip_id") or path.stem), "클립 ID")
    if path.parent.name != scene_id or path.stem != clip_id:
        raise ValueError("H3 클립 경로가 scene_id/clip_id와 다릅니다.")
    prompt = str(payload.get("video_prompt") or "").strip()
    prompt_variants = normalize_prompt_variants(payload.get("prompt_variants"))
    if prompt_variants and generation_mode != "r2v":
        raise ValueError("prompt_variants는 H3 R2V 프로젝트에서만 지원합니다.")
    if prompt_variants:
        prompt = prompt_variants[0]["video_prompt"]
    duration = float(payload.get("duration_seconds") or 0)
    references = []
    errors = []
    errors.extend(action_scene_routing_errors(payload))
    raw_references = payload.get("references") or []
    if generation_mode == "i2v":
        raw_start = payload.get("start_image") or {}
        if isinstance(raw_start, str):
            raw_start = {"source_path": raw_start}
        if not isinstance(raw_start, dict):
            raise ValueError("H3 I2V start_image는 JSON 객체여야 합니다.")
        raw_references = [{
            "picture_index": 1,
            "role": "start_frame",
            "label": str(raw_start.get("label") or "클립 시작 이미지"),
            "description": str(raw_start.get("description") or "H3 I2V 첫 프레임"),
            "required": True,
            "source_path": raw_start.get("source_path"),
        }]
        raw_last = payload.get("last_image")
        if raw_last:
            if isinstance(raw_last, str):
                raw_last = {"source_path": raw_last}
            if not isinstance(raw_last, dict):
                raise ValueError("H3 FFLF last_image는 JSON 객체여야 합니다.")
            raw_references.append({
                "picture_index": 2,
                "role": "last_frame",
                "label": str(raw_last.get("label") or "클립 종료 이미지"),
                "description": str(raw_last.get("description") or "H3 FFLF 마지막 프레임"),
                "required": True,
                "source_path": raw_last.get("source_path"),
            })
    for raw in raw_references:
        index = int(raw.get("picture_index") or 0)
        reference_kind = str(raw.get("reference_kind") or "visual_reference").strip().lower()
        if reference_kind not in {"visual_reference", "storyboard"}:
            errors.append(f"Picture {index} reference_kind가 올바르지 않습니다.")
            reference_kind = "visual_reference"
        storyboard_panel_count = int(raw.get("storyboard_panel_count") or 0)
        storyboard_beats = raw.get("storyboard_beats") or []
        if reference_kind == "storyboard":
            if storyboard_panel_count < 1:
                errors.append(f"Picture {index} 스토리보드 패널 수가 필요합니다.")
            if not isinstance(storyboard_beats, list) or len(storyboard_beats) != storyboard_panel_count:
                errors.append(
                    f"Picture {index} storyboard_beats는 패널 수와 같아야 합니다."
                )
        source_path = str(raw.get("source_path") or "").strip()
        linked = False
        asset_error = ""
        asset_version = ""
        if source_path:
            try:
                linked_path = _asset_path(root, project_id, source_path)
                info = linked_path.stat()
                asset_version = f"{info.st_mtime_ns:x}-{info.st_size:x}"
                linked = True
            except (ValueError, FileNotFoundError) as exc:
                asset_error = str(exc)
        references.append({
            "picture_index": index,
            "role": str(raw.get("role") or f"picture_{index}"),
            "label": str(raw.get("label") or raw.get("role") or f"Picture {index}"),
            "description": str(raw.get("description") or ""),
            "instruction_en": str(raw.get("instruction_en") or ""),
            "reference_kind": reference_kind,
            "storyboard_panel_count": storyboard_panel_count,
            "storyboard_reading_order": str(
                raw.get("storyboard_reading_order") or ""
            ),
            "storyboard_mode": str(raw.get("storyboard_mode") or ""),
            "storyboard_beats": storyboard_beats if isinstance(storyboard_beats, list) else [],
            "required": bool(raw.get("required", True)),
            "source_path": source_path or None,
            "linked": linked,
            "asset_error": asset_error,
            "asset_url": (
                f"/api/h3/projects/{project_id}/clips/{clip_id}/pictures/{index}"
                f"?v={asset_version}"
                if linked else None
            ),
        })
    indexes = [row["picture_index"] for row in references]
    if indexes != list(range(1, len(indexes) + 1)):
        errors.append("Picture는 1번부터 빈 슬롯 없이 순서대로 작성해야 합니다.")
    if len(references) > 9:
        errors.append("Picture는 최대 9장입니다.")
    require_shot_timestamps = not any(
        row.get("storyboard_mode") == ISOLATED_ACTION_STORYBOARD_MODE
        for row in references
    )
    action_contract = payload.get("action_scene_contract") or {}
    text_directed_four_shots = (
        isinstance(action_contract, dict)
        and str(action_contract.get("storyboard_mode") or "").strip()
        in {
            FOUR_SHOT_TEXT_DIRECTED_MODE,
            FOUR_SUBJECT_STATE_ACTION_MODE,
            FOUR_OBJECT_ACTION_PAIRS_MODE,
            FOUR_DESCRIBED_OBJECT_BEHAVIOR_MODE,
        }
    )
    allow_four_shots = text_directed_four_shots or any(
        row.get("storyboard_mode") == FOUR_SHOT_ACTION_STORYBOARD_MODE
        for row in references
    )
    allow_six_shots = any(
        row.get("storyboard_mode") == SIX_SHOT_TEMPORAL_STORYBOARD_MODE
        for row in references
    )
    if not prompt:
        errors.append("video_prompt가 비어 있습니다.")
    if generation_mode == "r2v":
        contract_version = str(payload.get("prompt_contract_version") or "")
        if contract_version not in h3_prompt_contract.SUPPORTED_CONTRACT_VERSIONS:
            errors.append(
                "지원하지 않는 R2V prompt_contract_version입니다: "
                f"{contract_version or '(empty)'}"
            )
        else:
            prompts = (
                [row["video_prompt"] for row in prompt_variants]
                if prompt_variants
                else [prompt]
            )
            for index, candidate_prompt in enumerate(prompts, start=1):
                candidate_label = (
                    prompt_variants[index - 1]["variant_id"]
                    if prompt_variants
                    else "video_prompt"
                )
                if contract_version in h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSIONS:
                    prompt_picture_ids = {
                        int(value)
                        for value in h3_prompt_contract.PICTURE_REFERENCE_RE.findall(
                            candidate_prompt
                        )
                    }
                    unknown_picture_ids = sorted(prompt_picture_ids - set(indexes))
                    if unknown_picture_ids:
                        errors.append(
                            f"후보 {candidate_label}: 프로젝트에 없는 Picture를 참조합니다: "
                            + ", ".join(str(value) for value in unknown_picture_ids)
                        )
                    continue
                report = h3_prompt_contract.validate_prompt(
                    candidate_prompt,
                    duration_seconds=duration,
                    require_shot_timestamps=require_shot_timestamps,
                    allow_four_shots=allow_four_shots,
                    allow_six_shots=allow_six_shots,
                )
                if not report.valid:
                    errors.extend(
                        f"후보 {candidate_label}: {issue.message}"
                        for issue in report.errors
                    )
                prompt_picture_ids = {
                    int(value)
                    for value in h3_prompt_contract.PICTURE_REFERENCE_RE.findall(
                        candidate_prompt
                    )
                }
                unknown_picture_ids = sorted(prompt_picture_ids - set(indexes))
                if unknown_picture_ids:
                    errors.append(
                        f"후보 {candidate_label}: 프로젝트에 없는 "
                        "Picture를 참조합니다: "
                        + ", ".join(str(value) for value in unknown_picture_ids)
                    )
                if contract_version in {
                    h3_prompt_contract.GRID_FREE_STORYBOARD_CONTRACT_VERSION,
                    h3_prompt_contract.CONTRACT_VERSION,
                }:
                    detail = extract_detailed_description(candidate_prompt)
                    shot_rows = list(h3_prompt_contract.SHOT_RE.finditer(detail))
                    planned_ordinals = ("first", "second", "third", "fourth")
                    for reference in references:
                        if reference.get("reference_kind") != "storyboard":
                            continue
                        picture_id = int(reference["picture_index"])
                        panel_count = int(reference.get("storyboard_panel_count") or 0)
                        storyboard_mode = str(reference.get("storyboard_mode") or "")
                        if storyboard_mode == SIX_SHOT_TEMPORAL_STORYBOARD_MODE:
                            if panel_count != 6 or len(shot_rows) != 6:
                                errors.append(
                                    f"후보 {candidate_label}: Picture {picture_id}의 6패널을 "
                                    "시간이 있는 6개 Shot으로 분리해야 합니다."
                                )
                                continue
                            if not re.search(
                                rf"^<Subject 1>\s+is\s+.*<Picture {picture_id}>",
                                candidate_prompt,
                                re.MULTILINE,
                            ):
                                errors.append(
                                    f"후보 {candidate_label}: Picture {picture_id}를 완전한 "
                                    "시간순 스토리보드 Subject로 정의해야 합니다."
                                )
                            for shot_number, shot_match in enumerate(shot_rows, start=1):
                                body = shot_match.group(4)
                                if (
                                    f"<Picture {picture_id}>" not in body
                                    or f"numbered action image {shot_number}" not in body.lower()
                                ):
                                    errors.append(
                                        f"후보 {candidate_label} Shot {shot_number}: Picture "
                                        f"{picture_id}의 numbered action image {shot_number} 연결이 필요합니다."
                                    )
                            continue
                        if storyboard_mode == ISOLATED_ACTION_STORYBOARD_MODE:
                            if panel_count != 4 or len(shot_rows) != 3:
                                errors.append(
                                    f"후보 {candidate_label}: Picture {picture_id} 순간 액션 "
                                    "스토리보드는 모델 진입·보드 액션·모델 종료의 3개 Shot 구조가 필요합니다."
                                )
                                continue
                            if not re.search(
                                rf"^<Picture {picture_id}>\s*(?::|is)\s*",
                                candidate_prompt,
                                re.MULTILINE,
                            ):
                                errors.append(
                                    f"후보 {candidate_label}: 스토리보드 Picture {picture_id}의 "
                                    "독립 정의가 없습니다."
                                )
                            entry_body = shot_rows[0].group(4)
                            body = shot_rows[1].group(4)
                            exit_body = shot_rows[2].group(4)
                            if (
                                f"<Picture {picture_id}>" not in body
                                or not re.search(
                                    r"in this order:\s*top-left,\s*top-right,\s*bottom-left,\s*bottom-right",
                                    body,
                                    re.IGNORECASE,
                                )
                            ):
                                errors.append(
                                    f"후보 {candidate_label} Shot 2: Picture {picture_id}의 네 액션 "
                                    "보드의 표시 순서와 행동 이름만 연결해야 합니다."
                                )
                            if (
                                f"<Picture {picture_id}>" in entry_body
                                or f"<Picture {picture_id}>" in exit_body
                            ):
                                errors.append(
                                    f"후보 {candidate_label}: Picture {picture_id}는 스토리보드 전용 "
                                    "Shot 2에서만 참조해야 합니다."
                                )
                            continue
                        if storyboard_mode == FOUR_SHOT_ACTION_STORYBOARD_MODE:
                            if panel_count != 4 or len(shot_rows) != 4:
                                errors.append(
                                    f"후보 {candidate_label}: Picture {picture_id}의 네 패널을 "
                                    "시간이 있는 4개 Shot으로 분리해야 합니다."
                                )
                                continue
                            positions = ("top-left", "top-right", "bottom-left", "bottom-right")
                            for shot_number, (shot_match, position) in enumerate(
                                zip(shot_rows, positions, strict=True), start=1
                            ):
                                body = shot_match.group(4)
                                if (
                                    f"<Picture {picture_id}>" not in body
                                    or f"{position} action image" not in body.lower()
                                ):
                                    errors.append(
                                        f"후보 {candidate_label} Shot {shot_number}: Picture "
                                        f"{picture_id}의 {position} action image 연결이 필요합니다."
                                    )
                            continue
                        if panel_count != 4 or len(shot_rows) != 4:
                            errors.append(
                                f"후보 {candidate_label}: Picture {picture_id} 4패널 스토리보드는 "
                                "정확히 4개 Shot으로 분리해야 합니다."
                            )
                            continue
                        if not re.search(
                            rf"^<Picture {picture_id}>\s*(?::|is)\s*",
                            candidate_prompt,
                            re.MULTILINE,
                        ):
                            errors.append(
                                f"후보 {candidate_label}: 스토리보드 Picture {picture_id}의 "
                                "독립 정의가 없습니다."
                            )
                        for shot_number, shot_match in enumerate(shot_rows, start=1):
                            body = shot_match.group(4)
                            if (
                                f"<Picture {picture_id}>" not in body
                                or f"{planned_ordinals[shot_number - 1]} planned composition"
                                not in body.lower()
                            ):
                                errors.append(
                                    f"후보 {candidate_label} Shot {shot_number}: Picture {picture_id}와 "
                                    f"{planned_ordinals[shot_number - 1]} planned composition 연결이 필요합니다."
                                )
                        if re.search(
                            r"\b(?:2x2|grid|quadrant|top-left|top-right|bottom-left|bottom-right|panel)\b",
                            detail,
                            re.IGNORECASE,
                        ):
                            errors.append(
                                f"후보 {candidate_label}: 2x2 배열·패널 좌표는 "
                                "subject_definitions에만 두고 Shot 본문에는 쓸 수 없습니다."
                            )
                if contract_version == h3_prompt_contract.CONTRACT_VERSION:
                    raw_required_dialogue = payload.get("required_dialogue") or []
                    if not isinstance(raw_required_dialogue, list) or any(
                        not isinstance(line, str) or not line.strip()
                        for line in raw_required_dialogue
                    ):
                        errors.append("required_dialogue는 비어 있지 않은 문자열의 배열이어야 합니다.")
                    else:
                        required_dialogue = [line.strip() for line in raw_required_dialogue]
                        dialogue_rows = h3_prompt_contract.DIALOGUE_RE.findall(candidate_prompt)
                        actual_dialogue = [line.strip() for _language, line in dialogue_rows]
                        languages = [language.strip() for language, _line in dialogue_rows]
                        if actual_dialogue != required_dialogue:
                            errors.append(
                                f"후보 {candidate_label}: required_dialogue와 실제 대사 순서가 "
                                f"다릅니다: required={required_dialogue}, actual={actual_dialogue}"
                            )
                        if any(language != "Korean" for language in languages):
                            errors.append(
                                f"후보 {candidate_label}: 확정 한국어 대사는 "
                                "<d>[Korean] ...</d> 형식을 사용해야 합니다."
                            )
        event_contract = payload.get("event_contract")
        if event_contract is not None:
            if not isinstance(event_contract, dict):
                errors.append("event_contract는 JSON 객체여야 합니다.")
            else:
                event_version = str(payload.get("event_contract_version") or "")
                if event_version not in SUPPORTED_EVENT_CONTRACT_VERSIONS:
                    errors.append(
                        "지원하지 않는 event_contract_version입니다: "
                        f"{event_version or '(empty)'}"
                    )
                event_description = str(event_contract.get("description") or "").strip()
                incoming_bridge = str(event_contract.get("incoming_bridge") or "").strip()
                outgoing_bridge = str(event_contract.get("outgoing_bridge") or "").strip()
                incoming_subjects = [
                    int(value)
                    for value in event_contract.get("incoming_reference_subjects") or []
                ]
                outgoing_subjects = [
                    int(value)
                    for value in event_contract.get("outgoing_reference_subjects") or []
                ]
                four_shot_action_storyboard = allow_four_shots
                subject_state_action = (
                    isinstance(action_contract, dict)
                    and str(action_contract.get("storyboard_mode") or "").strip()
                    == FOUR_SUBJECT_STATE_ACTION_MODE
                )
                object_action_pairs = (
                    isinstance(action_contract, dict)
                    and str(action_contract.get("storyboard_mode") or "").strip()
                    == FOUR_OBJECT_ACTION_PAIRS_MODE
                )
                described_object_behavior = (
                    isinstance(action_contract, dict)
                    and str(action_contract.get("storyboard_mode") or "").strip()
                    == FOUR_DESCRIBED_OBJECT_BEHAVIOR_MODE
                )
                expected_signature = hashlib.sha256(
                    json.dumps(
                        {
                            "event": event_description,
                            "bridge_in_id": str(event_contract.get("bridge_in_id") or ""),
                            "bridge_out_id": str(event_contract.get("bridge_out_id") or ""),
                            "boundary_policy": str(event_contract.get("boundary_policy") or ""),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ).encode("utf-8")
                ).hexdigest()
                if not event_description:
                    errors.append("event_contract.description이 비어 있습니다.")
                if (
                    not four_shot_action_storyboard
                    and (not incoming_bridge or not outgoing_bridge)
                ):
                    errors.append("event_contract의 입·출력 연결 문장이 비어 있습니다.")
                if str(payload.get("event_signature") or "") != expected_signature:
                    errors.append("event_signature가 공통 사건 설명과 일치하지 않습니다.")
                minimum_shots = 1 if duration <= 6 else 2 if duration <= 8 else 3
                for row in prompt_variants:
                    report = h3_prompt_contract.validate_prompt(
                        row["video_prompt"],
                        duration_seconds=duration,
                        require_shot_timestamps=require_shot_timestamps,
                        allow_four_shots=four_shot_action_storyboard,
                        allow_six_shots=allow_six_shots,
                    )
                    if report.shot_count < minimum_shots:
                        errors.append(
                            f"후보 {row['variant_id']}는 {duration:g}초에 최소 "
                            f"{minimum_shots}개 Shot이 필요합니다."
                        )
                    detail = row["detailed_description"]
                    shot_rows = list(h3_prompt_contract.SHOT_RE.finditer(detail))
                    if not shot_rows:
                        continue
                    first_shot = shot_rows[0].group(4)
                    last_shot = shot_rows[-1].group(4)
                    if (
                        not subject_state_action and not object_action_pairs and not described_object_behavior
                        and incoming_bridge
                        and incoming_bridge not in first_shot
                    ):
                        errors.append(
                            f"후보 {row['variant_id']} 첫 Shot에 입력 연결 단서가 없습니다."
                        )
                    if (
                        not subject_state_action and not object_action_pairs and not described_object_behavior
                        and outgoing_bridge
                        and outgoing_bridge not in last_shot
                    ):
                        errors.append(
                            f"후보 {row['variant_id']} 마지막 Shot에 다음 사건 단서가 없습니다."
                        )
                    for subject_id in (
                        () if four_shot_action_storyboard else incoming_subjects
                    ):
                        if f"<Subject {subject_id}>" not in first_shot:
                            errors.append(
                                f"후보 {row['variant_id']} 첫 Shot에 입력 Subject "
                                f"{subject_id}가 없습니다."
                            )
                    for subject_id in (
                        () if four_shot_action_storyboard else outgoing_subjects
                    ):
                        if f"<Subject {subject_id}>" not in last_shot:
                            errors.append(
                                f"후보 {row['variant_id']} 마지막 Shot에 출력 Subject "
                                f"{subject_id}가 없습니다."
                            )
    if duration < 1 or duration > 15:
        errors.append("duration_seconds는 1~15초여야 합니다.")
    for row in references:
        if row["required"] and not row["linked"]:
            errors.append(
                "클립 시작 이미지가 연결되지 않았습니다."
                if generation_mode == "i2v"
                else f"Picture {row['picture_index']} 필수 이미지가 연결되지 않았습니다."
            )
    scene_detailed_description = (
        "\n\n".join(
            f"[Candidate {row['variant_id']} · {row['label']}]\n{row['detailed_description']}"
            for row in prompt_variants
        )
        if prompt_variants
        else extract_detailed_description(prompt)
    )
    return {
        **payload,
        "project_id": project_id,
        "scene_id": scene_id,
        "clip_id": clip_id,
        "sequence": int(payload.get("sequence") or 0),
        "video_prompt": prompt,
        "detailed_description": scene_detailed_description,
        "prompt_variants": prompt_variants,
        "detailed_descriptions": [
            {
                "variant_id": row["variant_id"],
                "label": row["label"],
                "detailed_description": row["detailed_description"],
            }
            for row in prompt_variants
        ],
        "duration_seconds": duration,
        "generation_mode": generation_mode,
        "start_image": references[0] if generation_mode == "i2v" else None,
        "last_image": references[1] if generation_mode == "i2v" and len(references) > 1 else None,
        "references": references,
        "ready": not errors,
        "errors": errors,
        "markdown_path": path.relative_to(projects_root(root)).as_posix(),
    }


def load_clip(root: Path, project_id: str, clip_id: str) -> dict[str, Any]:
    project_id, clip_id = _safe(project_id, "H3 프로젝트 ID"), _safe(clip_id, "H3 클립 ID")
    matches = list(project_dir(root, project_id).glob(f"*/{clip_id}.md"))
    if len(matches) != 1:
        raise FileNotFoundError(f"H3 클립을 찾을 수 없습니다: {clip_id}")
    path = matches[0]
    return _normalize_payload(root, project_id, path, extract_payload(path.read_text(encoding="utf-8")))


def list_projects(root: Path) -> dict[str, Any]:
    projects = []
    base = projects_root(root)
    if not base.is_dir():
        return {"projects": []}
    for directory in sorted(path for path in base.iterdir() if path.is_dir()):
        manifest_path = directory / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
        project_kind = str(manifest.get("project_kind") or "")
        generation_mode = PROJECT_KIND_MODES.get(project_kind)
        if not generation_mode:
            continue
        clips = []
        for path in sorted(
            path
            for path in directory.glob("*/*.md")
            if path.parent.name != "source"
        ):
            try:
                clip = _normalize_payload(root, directory.name, path, extract_payload(path.read_text(encoding="utf-8")))
                if clip["generation_mode"] != generation_mode:
                    raise ValueError("프로젝트 종류와 클립 workflow가 일치하지 않습니다.")
                clips.append(clip)
            except Exception as exc:
                clips.append({"project_id": directory.name, "scene_id": path.parent.name, "clip_id": path.stem, "sequence": 0, "generation_mode": generation_mode, "ready": False, "errors": [str(exc)], "references": [], "video_prompt": "", "duration_seconds": 0})
        projects.append({
            "project_id": directory.name,
            "title": str(manifest.get("title") or directory.name),
            "description": str(manifest.get("description") or ""),
            "generation_mode": generation_mode,
            "project_kind": project_kind,
            "generation_blocked": bool(manifest.get("generation_blocked")),
            "generation_block_reason": str(
                manifest.get("generation_block_reason") or ""
            ),
            "replacement_project_ids": list(
                manifest.get("replacement_project_ids") or []
            ),
            "prompt_profile": str(manifest.get("prompt_profile") or ""),
            "prompt_generator": str(manifest.get("prompt_generator") or ""),
            "scene_count": len({row["scene_id"] for row in clips}),
            "clip_count": len(clips),
            "ready_count": sum(1 for row in clips if row.get("ready")),
            "deletable": directory.name not in PROTECTED_PROJECT_IDS,
            "delete_block_reason": (
                "기본 제공 프로젝트 템플릿은 삭제할 수 없습니다."
                if directory.name in PROTECTED_PROJECT_IDS
                else None
            ),
        })
    return {"projects": projects}


def project_clips(root: Path, project_id: str) -> dict[str, Any]:
    project_id = _safe(project_id, "H3 프로젝트 ID")
    directory = project_dir(root, project_id)
    if not directory.is_dir():
        raise FileNotFoundError("H3 프로젝트를 찾을 수 없습니다.")
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise ValueError("H3 프로젝트 manifest.json을 읽을 수 없습니다.") from exc
    generation_mode = PROJECT_KIND_MODES.get(str(manifest.get("project_kind") or ""))
    if not generation_mode:
        raise ValueError("지원하지 않는 H3 프로젝트 종류입니다.")
    clips = []
    for path in sorted(
        path
        for path in directory.glob("*/*.md")
        if path.parent.name != "source"
    ):
        try:
            clip = _normalize_payload(root, project_id, path, extract_payload(path.read_text(encoding="utf-8")))
            if clip["generation_mode"] != generation_mode:
                raise ValueError("프로젝트 종류와 클립 workflow가 일치하지 않습니다.")
            clips.append(clip)
        except Exception as exc:
            clips.append({"project_id": project_id, "scene_id": path.parent.name, "clip_id": path.stem, "sequence": 0, "generation_mode": generation_mode, "ready": False, "errors": [str(exc)], "references": [], "video_prompt": "", "duration_seconds": 0})
    clips.sort(key=lambda row: (int(row.get("sequence") or 0), str(row["scene_id"]), str(row["clip_id"])))
    scenes: dict[str, list[dict[str, Any]]] = {}
    for clip in clips:
        scenes.setdefault(str(clip["scene_id"]), []).append(clip)
    return {
        "project_id": project_id,
        "generation_mode": generation_mode,
        "project_kind": str(manifest.get("project_kind") or ""),
        "generation_blocked": bool(manifest.get("generation_blocked")),
        "generation_block_reason": str(
            manifest.get("generation_block_reason") or ""
        ),
        "replacement_project_ids": list(
            manifest.get("replacement_project_ids") or []
        ),
        "prompt_profile": str(manifest.get("prompt_profile") or ""),
        "prompt_generator": str(manifest.get("prompt_generator") or ""),
        "clips": clips,
        "scenes": [
            {"scene_id": key, "clips": value}
            for key, value in scenes.items()
        ],
    }


def picture_path(root: Path, project_id: str, clip_id: str, picture_index: int) -> Path:
    clip = load_clip(root, project_id, clip_id)
    row = next((item for item in clip["references"] if item["picture_index"] == int(picture_index)), None)
    if not row or not row.get("source_path"):
        raise FileNotFoundError("연결된 H3 Picture가 없습니다.")
    return _asset_path(root, project_id, str(row["source_path"]))
