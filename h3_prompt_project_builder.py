from __future__ import annotations

"""Build a new H3 R2V project from structured specs only.

This builder intentionally has no import or patch path for an existing prompt
project.  All prompts are rendered through h3_prompt_contract before any
project becomes visible to the UI.
"""

import json
import hashlib
from pathlib import Path
import re
import secrets
import shutil
from typing import Any

import h3_prompt_contract
import h3_prompt_projects


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
COPY_FIELDS = (
    "canonical_source_lineage",
    "locked_rule_id",
    "source_shot_id",
    "continuity_in",
    "continuity_out",
    "event_state_in",
    "event_state_out",
    "before_state",
    "after_state",
    "world_action_axis",
    "screen_direction",
    "summary",
    "scenario_ko",
    "required_dialogue",
    "dialogue_lock_version",
    "action_requirements",
    "review_intent_ko",
    "storyboard_review_contract",
    "scene_type",
    "prompt_profile",
    "prompt_generator",
    "action_scene_contract",
    "authoring_notes",
    "visual_review",
    "semantic_review",
)
EVENT_CONTRACT_VERSION = h3_prompt_projects.EVENT_CONTRACT_VERSION


def _safe_id(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text or Path(text).name != text or text in {".", ".."}:
        raise ValueError(f"올바른 {label}이(가) 아닙니다.")
    return text


def _required_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label}는 비어 있지 않은 배열이어야 합니다.")
    return value


def _source_asset(spec_dir: Path, raw: Any) -> Path:
    value = str(raw or "").strip()
    if not value:
        raise ValueError("각 Picture reference에는 copy_from 원본 이미지가 필요합니다.")
    source = Path(value).expanduser()
    if not source.is_absolute():
        source = spec_dir / source
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"원본 이미지 파일을 찾을 수 없습니다: {source}")
    if source.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: {source.suffix}")
    return source


def _minimum_shots(duration: float) -> int:
    if duration <= 6:
        return 1
    if duration <= 8:
        return 2
    return 3


def _candidate_shots(
    clip_id: str,
    duration: float,
    contract: dict[str, Any],
    variant_id: str,
    event_contract_version: str = EVENT_CONTRACT_VERSION,
) -> tuple[list[dict[str, Any]], str]:
    raw_beats = _required_list(contract.get("beats"), f"{clip_id}.event_contract.beats")
    beat_order: list[str] = []
    beats: dict[str, str] = {}
    for raw_beat in raw_beats:
        if not isinstance(raw_beat, dict):
            raise ValueError(f"{clip_id}.event_contract.beats 항목은 JSON 객체여야 합니다.")
        beat_id = _safe_id(raw_beat.get("beat_id"), f"{clip_id} beat ID")
        description = str(raw_beat.get("description") or "").strip()
        if not description or beat_id in beats:
            raise ValueError(f"{clip_id} beat는 중복 없이 설명을 가져야 합니다: {beat_id}")
        beat_order.append(beat_id)
        beats[beat_id] = description

    plans = contract.get("candidate_plans") or {}
    if not isinstance(plans, dict) or len(plans) != 3:
        raise ValueError(f"{clip_id}.candidate_plans는 서로 다른 후보 3개를 정확히 가져야 합니다.")
    plan = plans.get(variant_id)
    if not isinstance(plan, dict):
        raise ValueError(f"{clip_id} 후보 {variant_id} Shot 계획이 없습니다.")
    emphasis = str(plan.get("emphasis") or "").strip()
    if not emphasis:
        raise ValueError(f"{clip_id} 후보 {variant_id} 강조점이 비어 있습니다.")
    raw_shots = _required_list(plan.get("shots"), f"{clip_id} 후보 {variant_id}.shots")
    storyboard_required = bool(contract.get("storyboard_required"))
    storyboard_picture_id = int(contract.get("storyboard_picture_id") or 0)
    storyboard_panel_count = int(contract.get("storyboard_panel_count") or 0)
    storyboard_mode = str(contract.get("storyboard_mode") or "").strip()
    storyboard_reading_order = str(
        contract.get("storyboard_reading_order") or ""
    ).strip()
    isolated_action_storyboard = (
        storyboard_mode == h3_prompt_projects.ISOLATED_ACTION_STORYBOARD_MODE
    )
    four_shot_action_storyboard = (
        storyboard_mode == h3_prompt_projects.FOUR_SHOT_TEMPORAL_STORYBOARD_MODE
    )
    four_shot_text_directed = (
        storyboard_mode == h3_prompt_projects.FOUR_SHOT_TEXT_DIRECTED_MODE
    )
    four_subject_state_action = (
        storyboard_mode == h3_prompt_projects.FOUR_SUBJECT_STATE_ACTION_MODE
    )
    four_object_action_pairs = (
        storyboard_mode == h3_prompt_projects.FOUR_OBJECT_ACTION_PAIRS_MODE
    )
    four_described_object_behavior = (
        storyboard_mode == h3_prompt_projects.FOUR_DESCRIBED_OBJECT_BEHAVIOR_MODE
    )
    panel_positions = ("top-left", "top-right", "bottom-left", "bottom-right")
    if storyboard_required:
        if storyboard_picture_id <= 0 or storyboard_panel_count != 4:
            raise ValueError(
                f"{clip_id} 스토리보드 계약에는 Picture 번호와 4개 패널이 필요합니다."
            )
        if isolated_action_storyboard and len(raw_shots) != 3:
            raise ValueError(
                f"{clip_id} 후보 {variant_id}는 모델 진입 Shot, 스토리보드 전용 액션 Shot, "
                "모델 종료 사건 Shot을 정확히 분리해야 합니다."
            )
        if isolated_action_storyboard and not storyboard_reading_order:
            raise ValueError(
                f"{clip_id} 순간 액션 스토리보드에는 명시적인 읽기 순서가 필요합니다."
            )
        if not isolated_action_storyboard and len(raw_shots) != storyboard_panel_count:
            raise ValueError(
                f"{clip_id} 후보 {variant_id}는 스토리보드 4개 패널을 "
                "각각 별도 Shot으로 가져야 합니다."
            )
    minimum = _minimum_shots(duration)
    maximum = h3_prompt_contract.max_shots_for_duration(duration)
    if isolated_action_storyboard:
        maximum = max(maximum, 3)
    if four_shot_action_storyboard:
        maximum = max(maximum, 4)
    if four_shot_text_directed:
        maximum = max(maximum, 4)
    if four_subject_state_action:
        maximum = max(maximum, 4)
    if four_object_action_pairs:
        maximum = max(maximum, 4)
    if four_described_object_behavior:
        maximum = max(maximum, 4)
    if len(raw_shots) < minimum or len(raw_shots) > maximum:
        raise ValueError(
            f"{clip_id} {duration:g}초 후보 {variant_id}는 Shot {minimum}~{maximum}개여야 합니다."
        )

    incoming_bridge = str(contract.get("incoming_bridge") or "").strip()
    outgoing_bridge = str(contract.get("outgoing_bridge") or "").strip()
    if not four_shot_action_storyboard and (not incoming_bridge or not outgoing_bridge):
        raise ValueError(f"{clip_id}에는 incoming_bridge와 outgoing_bridge가 필요합니다.")
    if four_subject_state_action or four_object_action_pairs or four_described_object_behavior:
        incoming_subjects = [int(value) for value in contract.get("incoming_reference_subjects") or []]
        outgoing_subjects = [int(value) for value in contract.get("outgoing_reference_subjects") or []]
    else:
        incoming_subjects = [
            int(value) for value in _required_list(
                contract.get("incoming_reference_subjects"),
                f"{clip_id}.incoming_reference_subjects",
            )
        ]
        outgoing_subjects = [
            int(value) for value in _required_list(
                contract.get("outgoing_reference_subjects"),
                f"{clip_id}.outgoing_reference_subjects",
            )
        ]

    flattened: list[str] = []
    shots: list[dict[str, Any]] = []
    for index, raw_shot in enumerate(raw_shots, start=1):
        if not isinstance(raw_shot, dict):
            raise ValueError(f"{clip_id} 후보 {variant_id} Shot은 JSON 객체여야 합니다.")
        camera = str(raw_shot.get("camera") or "").strip()
        if not camera:
            raise ValueError(f"{clip_id} 후보 {variant_id} Shot {index} 카메라가 비어 있습니다.")
        storyboard_controlled = bool(raw_shot.get("storyboard_controlled"))
        if storyboard_required and isolated_action_storyboard:
            if storyboard_controlled != (index == 2):
                raise ValueError(
                    f"{clip_id} 후보 {variant_id}는 Shot 2만 storyboard_controlled=true여야 합니다."
                )
        if storyboard_required and not isolated_action_storyboard:
            panel_index = int(raw_shot.get("panel_index") or 0)
            panel_position = str(raw_shot.get("panel_position") or "").strip().lower()
            if panel_index != index or panel_position != panel_positions[index - 1]:
                raise ValueError(
                    f"{clip_id} 후보 {variant_id} Shot {index}는 <Picture "
                    f"{storyboard_picture_id}>의 panel {index} "
                    f"({panel_positions[index - 1]})를 명시해야 합니다."
                )
            if re.search(
                r"\b(?:2x2|grid|quadrant|top-left|top-right|bottom-left|bottom-right|panel)\b",
                camera,
                re.IGNORECASE,
            ):
                raise ValueError(
                    f"{clip_id} 후보 {variant_id} Shot {index}의 camera가 "
                    "출력 화면으로 오인될 수 있는 2x2 배열·패널 좌표를 포함합니다."
                )
        beat_ids = [
            _safe_id(value, f"{clip_id} beat ID")
            for value in _required_list(
                raw_shot.get("beat_ids"),
                f"{clip_id} 후보 {variant_id} Shot {index}.beat_ids",
            )
        ]
        if any(beat_id not in beats for beat_id in beat_ids):
            raise ValueError(f"{clip_id} 후보 {variant_id} Shot {index}에 알 수 없는 beat가 있습니다.")
        flattened.extend(beat_ids)
        if storyboard_required and isolated_action_storyboard and storyboard_controlled:
            anchor = (
                f"Follow <Picture {storyboard_picture_id}> in this order: "
                f"{storyboard_reading_order}."
            )
            # The storyboard already carries the four visible action states. Keep
            # their structured beats for validation, but do not repeat them as a
            # second long-form action description in the model-facing Shot text.
            parts = [anchor, camera]
        elif storyboard_required and isolated_action_storyboard and index == 3:
            # The outgoing bridge below already contains the final event.
            parts = [camera]
        elif storyboard_required and four_shot_action_storyboard:
            if index == 1:
                anchor = (
                    f"Use the {panel_positions[index - 1]} action image from "
                    f"<Picture {storyboard_picture_id}> as the full-screen starting "
                    f"state for Shot {index}."
                )
            else:
                anchor = (
                    f"Use only the {panel_positions[index - 1]} action image from "
                    f"<Picture {storyboard_picture_id}> as full-screen Shot {index}."
                )
            parts = [anchor, camera]
        elif storyboard_required and not isolated_action_storyboard:
            ordinal = ("first", "second", "third", "fourth")[index - 1]
            anchor = (
                f"Use the {ordinal} planned composition from <Picture "
                f"{storyboard_picture_id}> only for this Shot's viewpoint and "
                "subject placement."
            )
            parts = [anchor, camera, *(beats[beat_id] for beat_id in beat_ids)]
        elif four_object_action_pairs or four_described_object_behavior:
            parts = [camera]
        else:
            parts = [camera, *(beats[beat_id] for beat_id in beat_ids)]
        if index == 1 and not four_shot_action_storyboard and not four_subject_state_action and not four_object_action_pairs and not four_described_object_behavior:
            parts.insert(0, incoming_bridge)
        if index == len(raw_shots) and not four_shot_action_storyboard and not four_subject_state_action and not four_object_action_pairs and not four_described_object_behavior:
            parts.append(outgoing_bridge)
        elif storyboard_required:
            transition = str(raw_shot.get("transition_to_next") or "").strip()
            if transition:
                if event_contract_version == EVENT_CONTRACT_VERSION:
                    raise ValueError(
                        f"{clip_id} 후보 {variant_id} Shot {index}는 다음 구도로 "
                        "미리 이동하는 transition_to_next를 사용할 수 없습니다."
                    )
                if re.fullmatch(
                    r"(?:move|transition|continue)(?: the camera)? (?:to|toward) "
                    r"(?:the )?(?:next )?panel\.?",
                    transition,
                    re.IGNORECASE,
                ):
                    raise ValueError(
                        f"{clip_id} 후보 {variant_id} Shot {index}의 전환은 "
                        "구체적인 Shot 내부 이동을 설명해야 합니다."
                    )
                parts.append(transition)
        shot: dict[str, Any] = {
            "number": index,
            "description": " ".join(parts),
        }
        if index > 1:
            if isolated_action_storyboard:
                if raw_shot.get("start_seconds") not in (None, ""):
                    raise ValueError(
                        f"{clip_id} 후보 {variant_id} Shot {index}에는 시간을 지정하지 않습니다."
                    )
            else:
                start_seconds = float(raw_shot.get("start_seconds") or 0)
                if start_seconds <= 0:
                    raise ValueError(
                        f"{clip_id} 후보 {variant_id} Shot {index}에는 start_seconds가 필요합니다."
                    )
                shot["start_seconds"] = start_seconds
        elif raw_shot.get("start_seconds") not in (None, ""):
            raise ValueError(f"{clip_id} 후보 {variant_id} Shot 1에는 시작 시간을 쓰지 않습니다.")
        shots.append(shot)

    if flattened != beat_order:
        raise ValueError(
            f"{clip_id} 후보 {variant_id}는 공통 beat를 원래 순서대로 정확히 한 번씩 사용해야 합니다."
        )
    first_description = shots[0]["description"]
    last_description = shots[-1]["description"]
    for subject_id in (
        () if four_shot_action_storyboard or four_subject_state_action or four_object_action_pairs or four_described_object_behavior else incoming_subjects
    ):
        if f"<Subject {subject_id}>" not in first_description:
            raise ValueError(
                f"{clip_id} 후보 {variant_id} 첫 Shot에 incoming Subject {subject_id}가 없습니다."
            )
    for subject_id in (
        () if four_shot_action_storyboard or four_subject_state_action or four_object_action_pairs or four_described_object_behavior else outgoing_subjects
    ):
        if f"<Subject {subject_id}>" not in last_description:
            raise ValueError(
                f"{clip_id} 후보 {variant_id} 마지막 Shot에 outgoing Subject {subject_id}가 없습니다."
            )
    return shots, emphasis


def _prepare_clip(
    project_id: str,
    spec_dir: Path,
    raw: dict[str, Any],
    asset_catalog: dict[str, Any] | None = None,
    event_contract: dict[str, Any] | None = None,
    candidate_templates: dict[str, Any] | None = None,
    event_contract_version: str = EVENT_CONTRACT_VERSION,
) -> tuple[dict[str, Any], list[tuple[Path, str]]]:
    scene_id = _safe_id(raw.get("scene_id"), "씬 ID")
    clip_id = _safe_id(raw.get("clip_id"), "클립 ID")
    duration = float(raw.get("duration_seconds") or 0)
    if duration < 4 or duration > 15:
        raise ValueError(f"{clip_id} duration_seconds는 공식 범위 4~15초여야 합니다.")

    contract = event_contract or raw.get("event_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{clip_id}에는 공통 event_contract가 필요합니다.")
    event_description = str(contract.get("shared_event") or "").strip()
    if not event_description:
        raise ValueError(f"{clip_id}.event_contract.shared_event가 비어 있습니다.")
    bridge_in_id = _safe_id(contract.get("bridge_in_id"), f"{clip_id} bridge_in_id")
    bridge_out_id = _safe_id(contract.get("bridge_out_id"), f"{clip_id} bridge_out_id")
    boundary_policy = str(contract.get("boundary_policy") or "").strip()
    if boundary_policy not in {"referenced_cut", "merged_unreferenced_object", "terminal"}:
        raise ValueError(f"{clip_id}.boundary_policy가 올바르지 않습니다.")

    raw_references = _required_list(raw.get("references"), f"{clip_id}.references")
    if len(raw_references) > 9:
        raise ValueError(f"{clip_id}에는 Picture를 최대 9장까지 사용할 수 있습니다.")
    references: list[dict[str, Any]] = []
    copies: list[tuple[Path, str]] = []
    subject_defaults: list[dict[str, Any]] = []
    picture_defaults: list[dict[str, Any]] = []
    retention_defaults: list[dict[str, Any]] = []
    catalog = asset_catalog or {}
    for expected_index, raw_reference in enumerate(raw_references, start=1):
        if isinstance(raw_reference, str):
            asset_key = _safe_id(raw_reference, f"{clip_id} asset key")
            catalog_entry = catalog.get(asset_key)
            if not isinstance(catalog_entry, dict):
                raise ValueError(f"{clip_id} asset_catalog에 {asset_key} 항목이 없습니다.")
            reference = {**catalog_entry, "picture_index": expected_index}
        elif isinstance(raw_reference, dict) and raw_reference.get("asset_key"):
            asset_key = _safe_id(
                raw_reference.get("asset_key"), f"{clip_id} asset key"
            )
            catalog_entry = catalog.get(asset_key)
            if not isinstance(catalog_entry, dict):
                raise ValueError(f"{clip_id} asset_catalog에 {asset_key} 항목이 없습니다.")
            reference = {
                **catalog_entry,
                **raw_reference,
                "picture_index": expected_index,
            }
        else:
            reference = raw_reference
        if not isinstance(reference, dict):
            raise ValueError(
                f"{clip_id} reference 항목은 asset key 문자열 또는 JSON 객체여야 합니다."
            )
        picture_index = int(reference.get("picture_index") or 0)
        if picture_index != expected_index:
            raise ValueError(f"{clip_id} Picture 번호는 1부터 빈 번호 없이 이어져야 합니다.")
        source = _source_asset(spec_dir, reference.get("copy_from"))
        relative_target = (
            Path("assets")
            / clip_id
            / f"picture_{picture_index}{source.suffix.lower()}"
        ).as_posix()
        references.append({
            "picture_index": picture_index,
            "role": str(reference.get("role") or f"picture_{picture_index}"),
            "label": str(reference.get("label") or f"Picture {picture_index}"),
            "description": str(reference.get("description") or "").strip(),
            "instruction_en": str(reference.get("instruction_en") or "").strip(),
            "reference_kind": str(
                reference.get("reference_kind") or "visual_reference"
            ).strip(),
            **(
                {
                    "storyboard_panel_count": int(
                        reference.get("storyboard_panel_count") or 0
                    ),
                    "storyboard_reading_order": str(
                        reference.get("storyboard_reading_order") or ""
                    ).strip(),
                    "storyboard_mode": str(
                        reference.get("storyboard_mode") or ""
                    ).strip(),
                    "storyboard_beats": list(
                        reference.get("storyboard_beats") or []
                    ),
                }
                if str(reference.get("reference_kind") or "") == "storyboard"
                else {}
            ),
            "required": True,
            "source_path": relative_target,
        })
        copies.append((source, relative_target))
        subject_name = str(reference.get("subject_name") or "").strip()
        subject_description = str(reference.get("subject_description") or "").strip()
        if subject_name and subject_description:
            subject_id = int(reference.get("subject_id") or len(subject_defaults) + 1)
            subject_defaults.append({
                "subject_id": subject_id,
                "picture_ids": [picture_index],
                "name": subject_name,
                "description": subject_description,
            })
            retention_defaults.append({
                "subject_id": subject_id,
                "shots": [1],
                "marker": str(reference.get("retention_marker") or "fully_preserved"),
                "description": str(
                    reference.get("retention_description")
                    or f"Preserve the defining appearance of {subject_name}"
                ).strip(),
            })
        else:
            picture_name = str(
                reference.get("standalone_picture_name")
                or reference.get("label")
                or f"Picture {picture_index} reference"
            ).strip()
            picture_description = str(
                reference.get("standalone_picture_description")
                or reference.get("instruction_en")
                or reference.get("description")
                or ""
            ).strip()
            if picture_description:
                picture_defaults.append({
                    "picture_id": picture_index,
                    "name": picture_name,
                    "description": picture_description,
                })
                retention_defaults.append({
                    "picture_id": picture_index,
                    "shots": [int(value) for value in reference.get("retention_shots") or []],
                    "marker": str(reference.get("retention_marker") or "fully_preserved"),
                    "description": str(
                        reference.get("retention_description")
                        or f"Preserve and use {picture_name} only for its stated role"
                    ).strip(),
                })

    if bool(contract.get("storyboard_required")):
        storyboard_picture_id = int(contract.get("storyboard_picture_id") or 0)
        if storyboard_picture_id < 1 or storyboard_picture_id > len(references):
            raise ValueError(f"{clip_id} storyboard_picture_id가 Picture 범위 밖입니다.")
        storyboard_reference = references[storyboard_picture_id - 1]
        if (
            storyboard_reference.get("reference_kind") != "storyboard"
            or int(storyboard_reference.get("storyboard_panel_count") or 0) != 4
        ):
            raise ValueError(
                f"{clip_id} Picture {storyboard_picture_id}는 4패널 storyboard 참조여야 합니다."
            )
        contract_mode = str(contract.get("storyboard_mode") or "").strip()
        reference_mode = str(storyboard_reference.get("storyboard_mode") or "").strip()
        if contract_mode != reference_mode:
            raise ValueError(
                f"{clip_id} storyboard_mode이 계약과 Picture 참조에서 일치해야 합니다."
            )
    raw_variants = _required_list(
        raw.get("prompt_variants"), f"{clip_id}.prompt_variants"
    )
    if len(raw_variants) != 3:
        raise ValueError(f"{clip_id}는 독립 프롬프트 후보를 정확히 3개 가져야 합니다.")
    variant_ids = [
        str(variant.get("variant_id") or "").strip().upper()
        if isinstance(variant, dict) else ""
        for variant in raw_variants
    ]
    if (
        len(set(variant_ids)) != 3
        or any(not re.fullmatch(r"[A-Z]", variant_id) for variant_id in variant_ids)
    ):
        raise ValueError(f"{clip_id} 후보 ID는 중복 없는 영문 대문자 한 글자 3개여야 합니다.")
    plans = contract.get("candidate_plans") or {}
    if list(plans) != variant_ids:
        raise ValueError(
            f"{clip_id}.candidate_plans 순서는 prompt_variants의 "
            f"{'/'.join(variant_ids)}와 일치해야 합니다."
        )
    variants: list[dict[str, Any]] = []
    rationales: list[str] = []
    details: list[str] = []
    for expected_id, variant in zip(variant_ids, raw_variants, strict=True):
        if not isinstance(variant, dict):
            raise ValueError(f"{clip_id} prompt_variant 항목은 JSON 객체여야 합니다.")
        variant_id = str(variant.get("variant_id") or "").strip().upper()
        if variant_id != expected_id:
            raise ValueError(f"{clip_id} 프로젝트 후보 ID 순서가 올바르지 않습니다.")
        rationale = str(variant.get("rationale") or "").strip()
        if not rationale:
            raise ValueError(f"{clip_id} 후보 {variant_id}에는 독립 연출 rationale이 필요합니다.")
        prompt_base = raw.get("prompt_base") or {}
        if not isinstance(prompt_base, dict):
            raise ValueError(f"{clip_id}.prompt_base는 JSON 객체여야 합니다.")
        prompt_spec = variant.get("prompt_spec")
        if not isinstance(prompt_spec, dict):
            raise ValueError(f"{clip_id} 후보 {variant_id} prompt_spec이 필요합니다.")
        if prompt_spec.get("shots"):
            raise ValueError(f"{clip_id} 후보 {variant_id} Shot은 event_contract에서 관리합니다.")
        shots, emphasis = _candidate_shots(
            clip_id,
            duration,
            contract,
            variant_id,
            event_contract_version,
        )
        prompt_spec = {**prompt_base, **prompt_spec, "duration_seconds": duration}
        prompt_spec["allow_untimed_shots"] = (
            str(contract.get("storyboard_mode") or "").strip()
            == h3_prompt_projects.ISOLATED_ACTION_STORYBOARD_MODE
        )
        prompt_spec["allow_four_shots"] = str(
            contract.get("storyboard_mode") or ""
        ).strip() in {
            h3_prompt_projects.FOUR_SHOT_TEMPORAL_STORYBOARD_MODE,
            h3_prompt_projects.FOUR_SHOT_TEXT_DIRECTED_MODE,
            h3_prompt_projects.FOUR_SUBJECT_STATE_ACTION_MODE,
            h3_prompt_projects.FOUR_OBJECT_ACTION_PAIRS_MODE,
            h3_prompt_projects.FOUR_DESCRIBED_OBJECT_BEHAVIOR_MODE,
        }
        prompt_spec["shots"] = shots
        if not prompt_spec.get("subjects") and subject_defaults:
            prompt_spec["subjects"] = subject_defaults
        if not prompt_spec.get("pictures") and picture_defaults:
            prompt_spec["pictures"] = picture_defaults
        if not prompt_spec.get("retention_analysis") and retention_defaults:
            retention_rows = []
            for row in retention_defaults:
                if row.get("subject_id"):
                    subject_id = int(row["subject_id"])
                    appearing = [
                        shot["number"]
                        for shot in shots
                        if f"<Subject {subject_id}>" in shot["description"]
                    ]
                    label = f"Subject {subject_id}"
                else:
                    picture_id = int(row["picture_id"])
                    appearing = list(row.get("shots") or []) or [
                        shot["number"]
                        for shot in shots
                        if f"<Picture {picture_id}>" in shot["description"]
                    ]
                    label = f"Picture {picture_id}"
                if not appearing:
                    raise ValueError(
                        f"{clip_id} 후보 {variant_id}에서 {label}이 어떤 Shot에도 없습니다."
                    )
                retention_rows.append({**row, "shots": appearing})
            prompt_spec["retention_analysis"] = retention_rows
        covered_picture_ids = {
            int(picture_id)
            for subject in prompt_spec.get("subjects") or []
            for picture_id in (
                subject.get("picture_ids")
                if subject.get("picture_ids") is not None
                else [subject.get("picture_id")]
            )
        } | {
            int(picture.get("picture_id") or 0)
            for picture in prompt_spec.get("pictures") or []
        }
        if covered_picture_ids != set(range(1, len(references) + 1)):
            raise ValueError(
                f"{clip_id} 후보 {variant_id}가 모든 Picture를 Subject 또는 "
                "독립 Picture 정의로 정확히 한 번 연결하지 않았습니다."
            )
        try:
            prompt = h3_prompt_contract.render_prompt(prompt_spec)
        except (ValueError, h3_prompt_contract.PromptContractError) as exc:
            raise ValueError(
                f"{clip_id} 후보 {variant_id} H3 프롬프트 검증 실패: {exc}"
            ) from exc
        detail = h3_prompt_projects.extract_detailed_description(prompt)
        rationales.append(rationale)
        details.append(detail)
        variants.append({
            "variant_id": variant_id,
            "label": str(variant.get("label") or f"후보 {variant_id}").strip(),
            "rationale": rationale,
            "video_prompt": prompt,
        })
    raw_required_dialogue = raw.get("required_dialogue") or []
    if not isinstance(raw_required_dialogue, list) or any(
        not isinstance(line, str) or not line.strip()
        for line in raw_required_dialogue
    ):
        raise ValueError(f"{clip_id}.required_dialogue는 문자열 배열이어야 합니다.")
    required_dialogue = [line.strip() for line in raw_required_dialogue]
    for variant in variants:
        dialogue_rows = h3_prompt_contract.DIALOGUE_RE.findall(variant["video_prompt"])
        actual_dialogue = [line.strip() for _language, line in dialogue_rows]
        languages = [language.strip() for language, _line in dialogue_rows]
        if actual_dialogue != required_dialogue:
            raise ValueError(
                f"{clip_id} 후보 {variant['variant_id']}: required_dialogue와 실제 "
                f"대사가 다릅니다: required={required_dialogue}, actual={actual_dialogue}"
            )
        if any(language != "Korean" for language in languages):
            raise ValueError(
                f"{clip_id} 후보 {variant['variant_id']}: 대사 언어는 Korean이어야 합니다."
            )
    if len(set(rationales)) != 3 or len(set(details)) != 3:
        raise ValueError(
            f"{clip_id} 세 후보는 rationale과 detailed_description 연출이 서로 달라야 합니다."
        )

    payload: dict[str, Any] = {
        "schema_version": 2,
        "prompt_contract_version": h3_prompt_contract.CONTRACT_VERSION,
        "workflow": h3_prompt_projects.WORKFLOW,
        "project_id": project_id,
        "scene_id": scene_id,
        "clip_id": clip_id,
        "sequence": int(raw.get("sequence") or 0),
        "status": str(raw.get("status") or "ready"),
        "duration_seconds": duration,
        "video_prompt": variants[0]["video_prompt"],
        "prompt_variants": variants,
        "references": references,
        "event_contract_version": event_contract_version,
        "event_contract": {
            "description": event_description,
            "source_shot_ids": [
                str(value).strip() for value in contract.get("source_shot_ids") or []
            ],
            "bridge_in_id": bridge_in_id,
            "bridge_out_id": bridge_out_id,
            "boundary_policy": boundary_policy,
            "incoming_bridge": str(contract["incoming_bridge"]).strip(),
            "outgoing_bridge": str(contract["outgoing_bridge"]).strip(),
            "incoming_reference_subjects": [
                int(value) for value in contract["incoming_reference_subjects"]
            ],
            "outgoing_reference_subjects": [
                int(value) for value in contract["outgoing_reference_subjects"]
            ],
            "candidate_emphasis": {
                variant_id: str(contract["candidate_plans"][variant_id]["emphasis"]).strip()
                for variant_id in variant_ids
            },
        },
        "event_signature": hashlib.sha256(
            json.dumps(
                {
                    "event": event_description,
                    "bridge_in_id": bridge_in_id,
                    "bridge_out_id": bridge_out_id,
                    "boundary_policy": boundary_policy,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
    }
    for field in COPY_FIELDS:
        if raw.get(field) is not None:
            payload[field] = raw[field]
    routing_errors = h3_prompt_projects.action_scene_routing_errors(payload)
    if routing_errors:
        raise ValueError(
            f"{clip_id} 액션 씬 생성 경로 검증 실패: "
            + "; ".join(routing_errors)
        )
    return payload, copies


def build_project(root: Path, spec_path: Path) -> dict[str, Any]:
    root = root.resolve()
    spec_path = spec_path.expanduser().resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError("프로젝트 명세는 JSON 객체여야 합니다.")
    project_id = _safe_id(spec.get("project_id"), "프로젝트 ID")
    if project_id in h3_prompt_projects.PROTECTED_PROJECT_IDS:
        raise ValueError("보호된 템플릿 ID로 프로젝트를 만들 수 없습니다.")
    destination = h3_prompt_projects.projects_root(root) / project_id
    if destination.exists():
        raise FileExistsError(
            f"기존 프로젝트는 수정하지 않습니다. 새 project_id를 사용하세요: {project_id}"
        )

    raw_clips = _required_list(spec.get("clips"), "clips")
    contains_action = any(
        isinstance(raw_clip, dict)
        and str(raw_clip.get("scene_type") or "").strip()
        == h3_prompt_projects.ACTION_SCENE_TYPE
        for raw_clip in raw_clips
    )
    if contains_action:
        if str(spec.get("prompt_profile") or "").strip() != h3_prompt_projects.ACTION_PROMPT_PROFILE:
            raise ValueError(
                "액션 씬 프로젝트는 전용 prompt_profile을 manifest에 기록해야 합니다."
            )
        if str(spec.get("prompt_generator") or "").strip() != h3_prompt_projects.ACTION_PROMPT_GENERATOR:
            raise ValueError(
                "액션 씬 프로젝트는 전용 prompt_generator를 manifest에 기록해야 합니다."
            )
    asset_catalog = spec.get("asset_catalog") or {}
    if not isinstance(asset_catalog, dict):
        raise ValueError("asset_catalog는 JSON 객체여야 합니다.")
    candidate_templates = spec.get("candidate_templates") or {}
    event_contracts: dict[str, Any] = {}
    event_contract_version = EVENT_CONTRACT_VERSION
    event_contracts_file = str(spec.get("event_contracts_file") or "").strip()
    if event_contracts_file:
        contracts_path = Path(event_contracts_file).expanduser()
        if not contracts_path.is_absolute():
            contracts_path = spec_path.parent / contracts_path
        contracts_payload = json.loads(contracts_path.resolve().read_text(encoding="utf-8"))
        if not isinstance(contracts_payload, dict):
            raise ValueError("event_contracts_file은 JSON 객체여야 합니다.")
        event_contract_version = str(contracts_payload.get("version") or "")
        if event_contract_version not in h3_prompt_projects.SUPPORTED_EVENT_CONTRACT_VERSIONS:
            raise ValueError(
                "지원하지 않는 event_contracts_file.version입니다: "
                f"{event_contract_version or '(empty)'}"
            )
        event_contracts = contracts_payload.get("clips") or {}
        if not isinstance(event_contracts, dict):
            raise ValueError("event_contracts_file.clips는 JSON 객체여야 합니다.")
    clip_ids = [str(raw_clip.get("clip_id") or "").strip() for raw_clip in raw_clips]
    if event_contracts and set(event_contracts) != set(clip_ids):
        missing = sorted(set(clip_ids) - set(event_contracts))
        extra = sorted(set(event_contracts) - set(clip_ids))
        raise ValueError(
            f"event_contracts와 clips가 일치해야 합니다. missing={missing}, extra={extra}"
        )
    for index, clip_id in enumerate(clip_ids):
        contract = event_contracts.get(clip_id)
        if not isinstance(contract, dict):
            continue
        policy = str(contract.get("boundary_policy") or "")
        source_shot_ids = contract.get("source_shot_ids") or []
        if policy == "merged_unreferenced_object" and len(source_shot_ids) < 2:
            raise ValueError(f"{clip_id} 병합 계약에는 source_shot_ids가 2개 이상 필요합니다.")
        if policy == "terminal" and index != len(clip_ids) - 1:
            raise ValueError(f"{clip_id} terminal 경계는 마지막 클립에만 허용됩니다.")
        if index < len(clip_ids) - 1:
            next_contract = event_contracts.get(clip_ids[index + 1]) or {}
            outgoing = str(contract.get("bridge_out_id") or "")
            incoming = str(next_contract.get("bridge_in_id") or "")
            if not outgoing or outgoing != incoming:
                raise ValueError(
                    f"{clip_id} → {clip_ids[index + 1]} bridge ID가 이어지지 않습니다: "
                    f"{outgoing!r} != {incoming!r}"
                )
    prepared: list[tuple[dict[str, Any], list[tuple[Path, str]]]] = []
    identities: set[tuple[str, str]] = set()
    sequences: set[int] = set()
    for raw_clip in raw_clips:
        if not isinstance(raw_clip, dict):
            raise ValueError("clips 항목은 JSON 객체여야 합니다.")
        clip_id = str(raw_clip.get("clip_id") or "").strip()
        payload, copies = _prepare_clip(
            project_id,
            spec_path.parent,
            raw_clip,
            asset_catalog,
            event_contracts.get(clip_id),
            candidate_templates,
            event_contract_version,
        )
        identity = (payload["scene_id"], payload["clip_id"])
        if identity in identities:
            raise ValueError(f"중복 클립입니다: {identity[0]}/{identity[1]}")
        if payload["sequence"] in sequences or payload["sequence"] <= 0:
            raise ValueError("sequence는 프로젝트 전체에서 중복되지 않는 양수여야 합니다.")
        identities.add(identity)
        sequences.add(payload["sequence"])
        prepared.append((payload, copies))

    base = h3_prompt_projects.projects_root(root)
    base.mkdir(parents=True, exist_ok=True)
    staging = base / f".{project_id}.building-{secrets.token_hex(4)}"
    staging.mkdir()
    try:
        manifest = {
            "schema_version": 2,
            "project_kind": h3_prompt_projects.PROJECT_KIND,
            "project_id": project_id,
            "title": str(spec.get("title") or project_id),
            "description": str(spec.get("description") or ""),
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": h3_prompt_contract.CONTRACT_VERSION,
            "asset_storage": "project_local",
            "source_policy": str(
                spec.get("source_policy") or "original_scenario_and_assets_only"
            ),
            "canonical_source_lineage": list(
                spec.get("canonical_source_lineage") or []
            ),
            "locked_rule_id": str(spec.get("locked_rule_id") or ""),
            "build_script": str(spec.get("build_script") or ""),
            "prompt_profile": str(spec.get("prompt_profile") or ""),
            "prompt_generator": str(spec.get("prompt_generator") or ""),
            "dialogue_lock_version": str(spec.get("dialogue_lock_version") or ""),
            "dialogue_clip_count": int(spec.get("dialogue_clip_count") or 0),
            "dialogue_line_count": int(spec.get("dialogue_line_count") or 0),
            "scene_types": sorted({
                str(payload.get("scene_type") or "unspecified")
                for payload, _copies in prepared
            }),
            "generation_blocked": bool(spec.get("generation_blocked", False)),
            "generation_block_reason": str(
                spec.get("generation_block_reason") or ""
            ),
            "replacement_project_ids": list(
                spec.get("replacement_project_ids") or []
            ),
            "candidate_semantics": event_contract_version,
            "review_status": (
                next(iter({payload["status"] for payload, _copies in prepared}))
                if len({payload["status"] for payload, _copies in prepared}) == 1
                else "mixed"
            ),
            "build_facts": {
                "clip_count": len(prepared),
                "prompt_count": sum(
                    len(payload["prompt_variants"])
                    for payload, _copies in prepared
                ),
                "total_duration_seconds": sum(
                    float(payload["duration_seconds"])
                    for payload, _copies in prepared
                ),
            },
            "queue_authorized": False,
            "video_generation_authorized": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        copied_targets: set[str] = set()
        for payload, copies in prepared:
            clip_dir = staging / payload["scene_id"]
            clip_dir.mkdir(parents=True, exist_ok=True)
            for source, relative_target in copies:
                if relative_target in copied_targets:
                    raise ValueError(f"중복 자산 대상 경로입니다: {relative_target}")
                target = staging / relative_target
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                copied_targets.add(relative_target)
            markdown = (
                f"# {payload['clip_id']} · MiniMax H3 R2V\n\n"
                "## Machine Payload\n\n```json\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
            (clip_dir / f"{payload['clip_id']}.md").write_text(
                markdown, encoding="utf-8"
            )
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    overview = h3_prompt_projects.project_clips(root, project_id)
    invalid = [clip for clip in overview["clips"] if not clip["ready"]]
    if invalid:
        # This should be unreachable because every prompt and asset was checked
        # before publication. Leave the project visible for forensic inspection.
        raise RuntimeError(f"생성 후 검증 실패: {invalid[0]['clip_id']}: {invalid[0]['errors']}")
    return {
        "project_id": project_id,
        "project_path": str(destination),
        "clip_count": len(overview["clips"]),
        "ready_count": sum(1 for clip in overview["clips"] if clip["ready"]),
        "prompt_contract_version": h3_prompt_contract.CONTRACT_VERSION,
    }
