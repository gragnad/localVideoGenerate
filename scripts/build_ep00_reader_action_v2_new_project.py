from __future__ import annotations

"""Build the independent EP00 reader-action V2 storyboard prompt project.

The source is the human-readable V2 screenplay and the 28 newly generated 2D
storyboards.  No legacy EP00 prompt project is imported or patched.
"""

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_project_builder  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts.ep00_reader_action_v2_project_data import (  # noqa: E402
    CLIPS,
    DIALOGUE_LOCK,
    SOURCE_SHA256,
)


SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_reader_action_v2_new"
PROJECT_ID = "RaisingaDragonSeason01_EP00_READER_ACTION_V2_H3_R2V_STORYBOARD_ADE_V1"
SPEC_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_STORYBOARD_ADE_V1_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_STORYBOARD_ADE_V1_EVENT_CONTRACTS.json"
MODE = h3_prompt_projects.FOUR_SHOT_TEMPORAL_STORYBOARD_MODE
POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")

FIGHTER = "<Subject 1>, the injured young spear fighter with blue scales"
ENEMY = "<Subject 2>, the towering connected black liquid-stone humanoid"
SPEAR = "<Subject 3>, the single weathered wooden spear"


def _times(duration: float, variant: str) -> tuple[float, float, float]:
    ratios = {
        "A": (0.25, 0.50, 0.75),
        "D": (0.20, 0.46, 0.72),
        "E": (0.16, 0.40, 0.68),
    }[variant]
    return tuple(round(duration * ratio, 3) for ratio in ratios)


def _subject_action(text: str) -> str:
    """Add model-readable Subject tags without expanding the action."""
    value = text.strip()
    if value.startswith("Her "):
        return f"{FIGHTER}: her {value[4:]}"
    replacements = (
        ("The black humanoid", ENEMY),
        ("The enemy", ENEMY),
        ("The fighter", FIGHTER),
        ("She ", f"{FIGHTER} "),
        ("The spear", SPEAR),
    )
    for old, new in replacements:
        if value.startswith(old):
            return new + value[len(old):]
    if "<Subject " not in value:
        lower = value.lower()
        if any(token in lower for token in ("black ", "enemy", "palm", "fingertip", "wrist", "shoulder rotation")):
            return f"{ENEMY}: {value}"
        if any(token in lower for token in ("spear", "shaft", "weapon")):
            return f"{SPEAR}: {value}"
    return value


def _dialogue_clause(dialogue: dict[str, Any]) -> str:
    speaker = int(dialogue["speaker"])
    listener = int(dialogue["listener"])
    shot = int(dialogue["shot"])
    delivery = str(dialogue["delivery"]).strip()
    line = str(dialogue["line"]).strip()
    return (
        f"<Subject {speaker}> (S{shot}), delivery: {delivery}: <d>[Korean] {line}</d> "
        f"Listener <Subject {listener}>: mouth closed."
    )


def _shots(clip: dict[str, Any], variant: str) -> list[dict[str, Any]]:
    duration = float(clip["duration"])
    starts = _times(duration, variant)
    dialogue_by_shot: dict[int, list[dict[str, Any]]] = {}
    for dialogue in clip["dialogue"]:
        dialogue_by_shot.setdefault(int(dialogue["shot"]), []).append(dialogue)

    rows: list[dict[str, Any]] = []
    for index, raw_action in enumerate(clip["actions"], start=1):
        action = _subject_action(str(raw_action))
        if index == 1:
            action = (
                f"{FIGHTER}, {ENEMY}, and {SPEAR} occupy the wet circular altar "
                f"in the starting state shown. {action}"
            )
        clauses = [_dialogue_clause(row) for row in dialogue_by_shot.get(index, [])]
        camera = " ".join([action, *clauses])
        shot: dict[str, Any] = {
            "camera": camera,
            "panel_index": index,
            "panel_position": POSITIONS[index - 1],
            "beat_ids": [f"P{index}"],
        }
        if index > 1:
            shot["start_seconds"] = starts[index - 2]
        rows.append(shot)
    return rows


def _asset_catalog() -> dict[str, Any]:
    catalog: dict[str, Any] = {
        "fighter": {
            "role": "fighter_identity",
            "label": "approved blue-scaled fighter identity",
            "copy_from": "../rebuild_v2/designs_hq_v1/h3_identity_sheets/H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2.png",
            "subject_id": 1,
            "subject_name": "the injured young spear fighter with blue scales",
            "subject_description": (
                "One athletic young woman with warm tan skin, blue-grey eyes, asymmetric ink-navy short hair, "
                "sleeveless navy fishing clothes, and overlapping blue scales only on the full right arm and right leg."
            ),
            "retention_description": "Preserve one fighter, her face, clothing, scale boundaries, accumulated water, fatigue, and injury.",
        },
        "enemy": {
            "role": "black_humanoid_identity",
            "label": "approved connected black humanoid identity",
            "copy_from": "../rebuild_v2/designs_hq_v1/h3_identity_sheets/H3_ABYSS_KING_IDENTITY_HQ_V2.png",
            "subject_id": 2,
            "subject_name": "the towering connected black liquid-stone humanoid",
            "subject_description": (
                "One connected black liquid-stone humanoid about three times the fighter's height, with restrained "
                "cyan channels, a crown-like head, exactly two continuous arms, exactly two hands, and no legs or tendrils."
            ),
            "retention_description": "Preserve one connected three-times-taller black humanoid with exactly two arms and two hands.",
        },
        "spear": {
            "role": "single_spear_identity",
            "label": "approved single spear identity",
            "copy_from": "../rebuild_v2/designs_hq_v1/h3_prop_sheets/H3_LUA_SPEAR_PROP_HQ_V3.png",
            "subject_id": 3,
            "subject_name": "the single weathered wooden spear",
            "subject_description": (
                "One fixed-length weathered wooden spear with one dark metal head, one downward barb, bindings, grip wear, scratches, and one rear ring."
            ),
            "retention_marker": "partially_preserved",
            "retention_description": "Preserve exactly one intact fixed-length spear and the ownership shown in each Shot.",
        },
    }
    for clip in CLIPS:
        clip_id = str(clip["clip_id"])
        key = "storyboard-" + clip_id.lower()
        filename = clip_id.replace("-", "_") + "_STORYBOARD_V1.png"
        catalog[key] = {
            "role": "chronological_storyboard",
            "label": f"{clip_id} four-panel 2D storyboard",
            "copy_from": f"storyboards/{filename}",
            "reference_kind": "storyboard",
            "storyboard_panel_count": 4,
            "storyboard_reading_order": "top-left, top-right, bottom-left, bottom-right",
            "storyboard_beats": list(clip["panels"]),
            "standalone_picture_name": "the four ordered 2D animation starting images",
            "standalone_picture_description": (
                "Read the 2x2 planning sheet once in this order: top-left, top-right, bottom-left, bottom-right. "
                "They are the full-screen starting images for Shots 1, 2, 3, and 4. Never render the combined sheet, borders, or labels."
            ),
            "retention_shots": [1, 2, 3, 4],
            "retention_marker": "fully_preserved",
            "retention_description": "Use the four starting images in order without reproducing the combined sheet.",
            "storyboard_mode": MODE,
        }
    return catalog


def build_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    assets = _asset_catalog()
    clip_specs: list[dict[str, Any]] = []
    contracts: dict[str, Any] = {}
    for sequence, source in enumerate(CLIPS, start=1):
        clip_id = str(source["clip_id"])
        next_state = f"EP00V2_STATE_{sequence:02d}"
        previous_state = f"EP00V2_STATE_{sequence - 1:02d}"
        required_dialogue = [str(row["line"]) for row in source["dialogue"]]
        contract = {
            "shared_event": str(source["summary"]),
            "bridge_in_id": previous_state,
            "bridge_out_id": next_state,
            "boundary_policy": "terminal" if sequence == len(CLIPS) else "referenced_cut",
            "source_shot_ids": [clip_id],
            "incoming_reference_subjects": [1, 2, 3],
            "outgoing_reference_subjects": [1, 2, 3],
            "incoming_bridge": "",
            "outgoing_bridge": "",
            "storyboard_required": True,
            "storyboard_picture_id": 4,
            "storyboard_panel_count": 4,
            "storyboard_mode": MODE,
            "beats": [
                {"beat_id": f"P{index}", "description": str(panel)}
                for index, panel in enumerate(source["panels"], start=1)
            ],
            "candidate_plans": {
                variant: {
                    "emphasis": {
                        "A": "balanced spacing for the same four storyboard actions",
                        "D": "earlier opening cuts for the same four storyboard actions",
                        "E": "compressed middle cuts for the same four storyboard actions",
                    }[variant],
                    "shots": _shots(source, variant),
                }
                for variant in ("A", "D", "E")
            },
        }
        contracts[clip_id] = contract
        clip_specs.append({
            "scene_id": str(source["scene_id"]),
            "clip_id": clip_id,
            "sequence": sequence,
            "source_shot_id": clip_id,
            "status": "pending_user_prompt_review",
            "duration_seconds": float(source["duration"]),
            "references": ["fighter", "enemy", "spear", "storyboard-" + clip_id.lower()],
            "prompt_base": {
                "summary": str(source["summary"]),
                "style_opening": [
                    "High-detail hand-drawn 2D cel animation; each Shot uses one full-screen storyboard image and only the short action written after it; never render a reference-sheet background"
                ],
                "overall_soundscape": "Only sounds directly caused by the four written Shot actions and the exact written dialogue.",
                "non_diegetic_music": "None.",
            },
            "prompt_variants": [
                {
                    "variant_id": variant,
                    "label": f"Candidate {variant} · identical actions, timing variation only",
                    "rationale": {
                        "A": "Balanced temporal spacing across the same four storyboard states.",
                        "D": "Earlier opening changes across the same four storyboard states.",
                        "E": "Compressed middle changes across the same four storyboard states.",
                    }[variant],
                    "prompt_spec": {},
                }
                for variant in ("A", "D", "E")
            ],
            "canonical_source_lineage": [
                "EP00_READER_SCREENPLAY_ACTION_REVISION_V2.md",
                "EP00_V2_PRODUCTION_SEGMENTATION_V1.json",
                "EP00_V2_DIALOGUE_LOCK_V1.json",
                "EP00_V2_STORYBOARD_GENERATION_MANIFEST_V1.json",
            ],
            "locked_rule_id": "EP00_READER_ACTION_V2_NEW_PROJECT_V1",
            "continuity_in": previous_state,
            "continuity_out": next_state,
            "summary": str(source["summary"]),
            "required_dialogue": required_dialogue,
            "dialogue_lock_version": "EP00_V2_DIALOGUE_LOCK_V1",
            "storyboard_review_contract": {
                "picture_id": 4,
                "storyboard_mode": MODE,
                "storyboard_shots": [1, 2, 3, 4],
                "model_delegated_shots": [],
                "panel_to_shot": "top-left_to_1_top-right_to_2_bottom-left_to_3_bottom-right_to_4",
                "timing_source": "variant_specific_shot_start_ratios",
            },
            "scene_type": h3_prompt_projects.ACTION_SCENE_TYPE,
            "prompt_profile": h3_prompt_projects.ACTION_PROMPT_PROFILE,
            "prompt_generator": h3_prompt_projects.ACTION_PROMPT_GENERATOR,
            "action_scene_contract": {
                "version": h3_prompt_projects.ACTION_SCENE_CONTRACT_VERSION,
                "phase": "reader_action_v2_four_state_clip",
                "speed_profiles": [f"Follow storyboard Shot {index} and perform only its short action." for index in range(1, 5)],
                "motion_links": ["Cut on the completed visible change." for _ in range(3)],
                "environmental_proof": "Wet floor water, cyan channels, debris, and contact deformation visibly prove each action.",
                "storyboard_mode": MODE,
                "storyboard_picture_id": 4,
            },
            "authoring_notes": "New V2 screenplay only; four storyboard panels become four Shots; no delegated entry/exit Shots; no queue or video generation.",
            "visual_review": "generated_2d_storyboard_pending_final_user_approval",
            "semantic_review": "pending_user_prompt_review",
        })

    spec = {
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · Reader Action V2 · 2D Storyboard A/D/E V1",
        "description": "Independent V2 screenplay project: 28 chronological 2D storyboards mapped one panel to one concise timed Shot.",
        "source_policy": "ep00_reader_action_revision_v2_only",
        "canonical_source_lineage": [
            "EP00_READER_SCREENPLAY_ACTION_REVISION_V2.md",
            "EP00_V2_PRODUCTION_SEGMENTATION_V1.json",
            "EP00_V2_DIALOGUE_LOCK_V1.json",
        ],
        "locked_rule_id": "EP00_READER_ACTION_V2_NEW_PROJECT_V1",
        "build_script": "scripts/build_ep00_reader_action_v2_new_project.py",
        "prompt_profile": h3_prompt_projects.ACTION_PROMPT_PROFILE,
        "prompt_generator": h3_prompt_projects.ACTION_PROMPT_GENERATOR,
        "dialogue_lock_version": "EP00_V2_DIALOGUE_LOCK_V1",
        "dialogue_clip_count": len({row["clip_id"] for row in DIALOGUE_LOCK}),
        "dialogue_line_count": len(DIALOGUE_LOCK),
        "event_contracts_file": CONTRACTS_PATH.name,
        "asset_catalog": assets,
        "clips": clip_specs,
        "generation_blocked": False,
        "replacement_project_ids": [],
    }
    events = {
        "version": h3_prompt_project_builder.EVENT_CONTRACT_VERSION,
        "project_id": PROJECT_ID,
        "source_sha256": SOURCE_SHA256,
        "clips": contracts,
    }
    return spec, events


def _storyboard_inventory() -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for clip in CLIPS:
        filename = str(clip["clip_id"]).replace("-", "_") + "_STORYBOARD_V1.png"
        path = SOURCE_DIR / "storyboards" / filename
        inventory.append({
            "clip_id": clip["clip_id"],
            "file": f"storyboards/{filename}",
            "size_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    return inventory


def finalize_storyboard_manifest(inventory: list[dict[str, Any]]) -> None:
    path = SOURCE_DIR / "EP00_V2_STORYBOARD_GENERATION_MANIFEST_V1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    indexed = {str(row["clip_id"]): row for row in inventory}
    for item in payload["items"]:
        row = indexed[str(item["clip_id"])]
        item.update({
            "status": "generated_reviewed_and_linked",
            "size_bytes": int(row["size_bytes"]),
            "sha256": str(row["sha256"]),
            "prompt_project_id": PROJECT_ID,
            "storyboard_picture_index": 4,
        })
    payload.update({
        "status": "generated_reviewed_and_linked",
        "generated_count": len(inventory),
        "prompt_project_id": PROJECT_ID,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    })
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    spec, events = build_payloads()
    SPEC_PATH.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CONTRACTS_PATH.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    inventory_path = SOURCE_DIR / "EP00_V2_STORYBOARD_INVENTORY_V1.json"
    inventory = _storyboard_inventory()
    inventory_path.write_text(
        json.dumps({"version": "EP00_V2_STORYBOARD_INVENTORY_V1", "count": len(CLIPS), "items": inventory}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    finalize_storyboard_manifest(inventory)
    result = h3_prompt_project_builder.build_project(ROOT, SPEC_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
