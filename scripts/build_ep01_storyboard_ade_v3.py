from __future__ import annotations

"""Build the separated EP01 narrative H3 storyboard project."""

import copy
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_project_builder
import build_ep00_ep01_storyboard_ade_v2 as source


PROJECT_ID = "RaisingaDragonSeason01_EP01_H3_R2V_STORYBOARD_ADE_V3"
SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "rebuild_v2"
SPEC_PATH = SOURCE_DIR / "EP01_H3_R2V_STORYBOARD_ADE_V3_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP01_H3_R2V_STORYBOARD_ADE_V3_EVENT_CONTRACTS.json"
DIALOGUE_LOCK_PATH = SOURCE_DIR / "EP01_DIALOGUE_PERFORMANCE_LOCK_V3.json"
PROMPT_PROFILE = "h3_storyboard_scene_v1"
PROMPT_GENERATOR = "h3_storyboard_prompt_generator_v1"


def _reindex_contracts(
    clips: list[dict[str, Any]], contracts: dict[str, Any]
) -> None:
    for sequence, clip in enumerate(clips, start=1):
        clip_id = str(clip["clip_id"])
        clip["sequence"] = sequence
        clip["continuity_in"] = f"EP01_STORY_V3_STATE_{sequence - 1:03d}"
        clip["continuity_out"] = f"EP01_STORY_V3_STATE_{sequence:03d}"
        contract = contracts[clip_id]
        contract["bridge_in_id"] = clip["continuity_in"]
        contract["bridge_out_id"] = clip["continuity_out"]
        contract["boundary_policy"] = (
            "terminal" if sequence == len(clips) else "referenced_cut"
        )


def _load_dialogue_lock() -> tuple[dict[str, Any], dict[str, list[dict[str, object]]]]:
    payload = json.loads(DIALOGUE_LOCK_PATH.read_text(encoding="utf-8"))
    if payload.get("version") != "EP01_DIALOGUE_PERFORMANCE_LOCK_V3":
        raise ValueError("EP01 dialogue lock version is not approved V3.")
    raw_dialogue = payload.get("dialogue_by_clip")
    if not isinstance(raw_dialogue, dict):
        raise ValueError("EP01 dialogue lock must contain dialogue_by_clip.")

    source_rows = {
        str(row["clip_id"]): row
        for row in source.CLIPS
        if str(row.get("clip_id") or "").startswith("EP01-")
    }
    expected_clip_count = int(payload.get("expected_clip_count") or 0)
    if len(source_rows) != expected_clip_count:
        raise ValueError(
            f"EP01 dialogue lock clip count mismatch: expected={expected_clip_count}, "
            f"actual={len(source_rows)}"
        )

    dialogue: dict[str, list[dict[str, object]]] = {}
    for clip_id, raw_rows in raw_dialogue.items():
        if clip_id not in source_rows:
            raise ValueError(f"Unknown EP01 dialogue clip: {clip_id}")
        if not isinstance(raw_rows, list) or not raw_rows:
            raise ValueError(f"{clip_id}: dialogue rows must be a non-empty list.")
        assets = set(source_rows[clip_id]["assets"])
        normalized_rows: list[dict[str, object]] = []
        for raw_row in raw_rows:
            if not isinstance(raw_row, dict):
                raise ValueError(f"{clip_id}: dialogue row must be an object.")
            row = dict(raw_row)
            shot = int(row.get("shot") or 0)
            speaker = str(row.get("speaker") or "").strip()
            line = str(row.get("line") or "").strip()
            delivery = str(row.get("delivery") or "").strip()
            if shot not in {1, 2, 3, 4} or not line or not delivery:
                raise ValueError(f"{clip_id}: dialogue requires Shot 1-4, line, and delivery.")
            if speaker not in assets:
                raise ValueError(f"{clip_id}: dialogue speaker is not a referenced asset: {speaker}")
            if speaker == "mir-young":
                raise ValueError(f"{clip_id}: Young Mir cannot speak human dialogue.")
            normalized_rows.append(row)
        dialogue[clip_id] = normalized_rows

    line_count = sum(len(rows) for rows in dialogue.values())
    expected_dialogue_clip_count = int(payload.get("expected_dialogue_clip_count") or 0)
    expected_line_count = int(payload.get("expected_line_count") or 0)
    if len(dialogue) != expected_dialogue_clip_count or line_count != expected_line_count:
        raise ValueError(
            "EP01 dialogue lock totals mismatch: "
            f"clips={len(dialogue)}/{expected_dialogue_clip_count}, "
            f"lines={line_count}/{expected_line_count}"
        )

    # The reinforcement layer may add lines, but it cannot silently remove any
    # Korean line that was already locked in the approved V2 conversion.
    for clip_id, old_rows in source.DIALOGUE_BY_CLIP.items():
        if not clip_id.startswith("EP01-"):
            continue
        old_lines = Counter(str(row["line"]).strip() for row in old_rows)
        new_lines = Counter(str(row["line"]).strip() for row in dialogue.get(clip_id, []))
        if old_lines - new_lines:
            raise ValueError(f"{clip_id}: V3 dialogue lock removed a V2 line.")
    return payload, dialogue


def _build_source_payloads_with_dialogue(
    dialogue: dict[str, list[dict[str, object]]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    original_dialogue = source.DIALOGUE_BY_CLIP
    source.DIALOGUE_BY_CLIP = {**original_dialogue, **dialogue}
    try:
        return source.build_payloads()
    finally:
        source.DIALOGUE_BY_CLIP = original_dialogue


def build_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    dialogue_lock, dialogue = _load_dialogue_lock()
    combined_spec, combined_contracts = _build_source_payloads_with_dialogue(dialogue)
    spec = copy.deepcopy(combined_spec)
    contracts_payload = copy.deepcopy(combined_contracts)
    clips = [
        clip for clip in spec["clips"]
        if str(clip.get("clip_id") or "").startswith("EP01-")
    ]
    contracts = {
        clip_id: contract
        for clip_id, contract in contracts_payload["clips"].items()
        if clip_id.startswith("EP01-")
    }
    _reindex_contracts(clips, contracts)
    for clip in clips:
        clip["scene_type"] = "narrative"
        clip["prompt_profile"] = PROMPT_PROFILE
        clip["prompt_generator"] = PROMPT_GENERATOR
        lineage = list(clip.get("canonical_source_lineage") or [])
        if DIALOGUE_LOCK_PATH.name not in lineage:
            lineage.append(DIALOGUE_LOCK_PATH.name)
        clip["canonical_source_lineage"] = lineage
        clip["dialogue_lock_version"] = dialogue_lock["version"]
        clip["authoring_notes"] = (
            str(clip.get("authoring_notes") or "")
            + " This clip belongs to the separated EP01 narrative project and must not use the EP00 action-scene generator. Dialogue is governed by the EP01 V3 performance lock; dialogue-free clips must remain dialogue-free."
        ).strip()

    canonical_source_lineage = list(spec.get("canonical_source_lineage") or [])
    if DIALOGUE_LOCK_PATH.name not in canonical_source_lineage:
        canonical_source_lineage.append(DIALOGUE_LOCK_PATH.name)
    spec.update({
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP01 · Storyboard A/D/E V3",
        "description": "Separated EP01 narrative and performance project with the approved storyboards, reinforced Korean character dialogue, and general A/D/E camera grammar.",
        "source_policy": "rebuild_v2_approved_ep01_storyboards_only_separated_from_ep00_action",
        "canonical_source_lineage": canonical_source_lineage,
        "build_script": "scripts/build_ep01_storyboard_ade_v3.py",
        "event_contracts_file": CONTRACTS_PATH.name,
        "dialogue_lock_file": DIALOGUE_LOCK_PATH.name,
        "dialogue_lock_version": dialogue_lock["version"],
        "dialogue_clip_count": len(dialogue),
        "dialogue_line_count": sum(len(rows) for rows in dialogue.values()),
        "prompt_profile": PROMPT_PROFILE,
        "prompt_generator": PROMPT_GENERATOR,
        "generation_blocked": False,
        "replacement_project_ids": [],
        "clips": clips,
        "review_decision": "ep01_dialogue_reinforced_internal_validation_pass_user_prompt_review_pending_no_queue_no_video",
    })
    contracts_payload["clips"] = contracts
    contracts_payload["project_id"] = PROJECT_ID
    return spec, contracts_payload


def main() -> int:
    spec, contracts = build_payloads()
    SPEC_PATH.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    CONTRACTS_PATH.write_text(
        json.dumps(contracts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    result = h3_prompt_project_builder.build_project(ROOT, SPEC_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
