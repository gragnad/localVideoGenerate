from __future__ import annotations

"""Clean-slate MSR continuity submission rules.

This module intentionally has no dependency on Director prompts.  It compiles a
small MSR-only global prompt from the world, character and prop fields supplied
for one continuous generation unit.
"""

from typing import Any

WORKFLOW = "msr_sequence_v2"
PROMPT_STRATEGY = "msr_continuity_v1"
FPS = 24
MAX_SECONDS = 20.0
SLOT_ROLES = {
    1: "character_1",
    2: "character_2",
    3: "prop_3",
    4: "prop_4",
}
CHARACTER_SLOTS = {1, 2}
PROP_SLOTS = {3, 4}
CONTINUITY_MODES = {"new_anchor", "continuity_frame"}


class MSRSequenceValidationError(ValueError):
    pass


def _text(value: Any) -> str:
    return str(value or "").strip()


def normalize_references(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index, source in enumerate(rows or [], 1):
        row = dict(source or {})
        try:
            slot = int(row.get("slot") or row.get("reference_id") or index)
        except (TypeError, ValueError) as exc:
            raise MSRSequenceValidationError("MSR 참조 슬롯 번호가 올바르지 않습니다.") from exc
        if slot not in SLOT_ROLES:
            raise MSRSequenceValidationError(f"MSR 참조 슬롯은 1~4만 가능합니다: {slot}")
        if slot in seen:
            raise MSRSequenceValidationError(f"MSR 참조 슬롯이 중복되었습니다: {slot}")
        seen.add(slot)
        expected_role = SLOT_ROLES[slot]
        role = _text(row.get("role")) or expected_role
        if role != expected_role:
            raise MSRSequenceValidationError(
                f"슬롯 {slot}의 역할은 {expected_role}이어야 합니다: {role}"
            )
        description = _text(row.get("description"))
        if not description:
            label = "캐릭터" if slot in CHARACTER_SLOTS else "소품"
            raise MSRSequenceValidationError(f"{label} 참조 {slot} 설명이 필요합니다.")
        row.update(slot=slot, reference_id=slot, role=role, description=description)
        normalized.append(row)
    normalized.sort(key=lambda item: int(item["slot"]))
    if not normalized or int(normalized[0]["slot"]) != 1:
        raise MSRSequenceValidationError("캐릭터 참조 1은 필수입니다.")
    return normalized


def compile_global_prompt(world_prompt: str, references: list[dict[str, Any]]) -> str:
    world = _text(world_prompt)
    if not world:
        raise MSRSequenceValidationError("MSR 세계관·영상 스타일 설명이 필요합니다.")
    lines = [world]
    for row in references:
        slot = int(row["slot"])
        label = "Character" if slot in CHARACTER_SLOTS else "Prop"
        lines.append(f"Picture {slot} — {label}: {row['description']}")
    if any(int(row["slot"]) == 2 for row in references):
        lines.append("Keep Picture 1 and Picture 2 visually distinct; never merge their identity, anatomy or costume.")
    if any(int(row["slot"]) in PROP_SLOTS for row in references):
        lines.append("Pictures 3 and 4 are objects only; keep their owner, shape and material consistent and never turn them into characters.")
    return "\n".join(lines)


def validate_submission(data: dict[str, Any]) -> dict[str, Any]:
    if _text(data.get("workflow")) not in {"", WORKFLOW}:
        raise MSRSequenceValidationError("새 MSR 연속 생성은 msr_sequence_v2 워크플로만 사용할 수 있습니다.")
    if _text(data.get("prompt_strategy")) != PROMPT_STRATEGY:
        raise MSRSequenceValidationError(
            "새 MSR 프롬프트 전략(msr_continuity_v1)이 필요합니다. 기존 Director/MSR 프롬프트는 불러올 수 없습니다."
        )
    references = normalize_references(list(data.get("references") or []))
    anchor = dict(data.get("anchor") or data.get("background") or {})
    if not anchor.get("upload_path") and not anchor.get("source_path"):
        raise MSRSequenceValidationError("통합 앵커 이미지를 선택하세요.")
    anchor_description = _text(anchor.get("description"))
    if not anchor_description:
        raise MSRSequenceValidationError("통합 앵커의 공간·구도 설명이 필요합니다.")
    anchor["description"] = anchor_description

    relay: list[dict[str, Any]] = []
    total = 0.0
    for index, source in enumerate(data.get("relay_segments") or [], 1):
        row = dict(source or {})
        prompt = _text(row.get("prompt"))
        if not prompt:
            raise MSRSequenceValidationError(f"릴레이 구간 {index} 프롬프트가 필요합니다.")
        try:
            seconds = float(row.get("seconds") or 0)
        except (TypeError, ValueError) as exc:
            raise MSRSequenceValidationError(f"릴레이 구간 {index} 시간이 올바르지 않습니다.") from exc
        if seconds <= 0:
            raise MSRSequenceValidationError(f"릴레이 구간 {index} 시간은 0초보다 커야 합니다.")
        total += seconds
        relay.append({**row, "order": index, "prompt": prompt, "seconds": seconds})
    if not relay:
        raise MSRSequenceValidationError("프롬프트 릴레이 구간을 한 개 이상 입력하세요.")
    if total > MAX_SECONDS + 1e-6:
        raise MSRSequenceValidationError(
            f"MSR 연속 생성은 최대 {MAX_SECONDS:g}초입니다. 현재 합계: {total:g}초"
        )

    continuity_mode = _text(data.get("continuity_mode")) or "new_anchor"
    if continuity_mode not in CONTINUITY_MODES:
        raise MSRSequenceValidationError(f"지원하지 않는 연결 방식입니다: {continuity_mode}")
    world_prompt = _text(data.get("world_prompt"))
    return {
        **data,
        "schema_version": 3,
        "workflow": WORKFLOW,
        "prompt_strategy": PROMPT_STRATEGY,
        "director_prompt_inheritance": False,
        "fps": FPS,
        "maximum_duration_seconds": MAX_SECONDS,
        "requested_seconds": round(total, 4),
        "world_prompt": world_prompt,
        "global_prompt": compile_global_prompt(world_prompt, references),
        "references": references,
        "anchor": anchor,
        "background": anchor,
        "relay_segments": relay,
        "continuity_mode": continuity_mode,
        "source_scene_refs": _text(data.get("source_scene_refs")),
    }
