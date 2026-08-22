from __future__ import annotations

"""Build EP00 V2 as four text-directed Shots without storyboard Pictures.

Every Shot contains a complete starting composition followed by one concise
action. Candidate A is neutral; D and E change only viewpoint/camera energy and
Shot timing while preserving the same event and dialogue.
"""

import json
from pathlib import Path
import re
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


SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_reader_action_v2_text_directed_new"
PROJECT_ID = "RaisingaDragonSeason01_EP00_READER_ACTION_V2_H3_R2V_TEXT_DIRECTED_ADE_V1"
SPEC_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_TEXT_DIRECTED_ADE_V1_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_TEXT_DIRECTED_ADE_V1_EVENT_CONTRACTS.json"
MODE = h3_prompt_projects.FOUR_SHOT_TEXT_DIRECTED_MODE
BACKGROUND_PICTURE_ID = 4
EFFECT_PICTURE_ID = 5

FIGHTER = "<Subject 1>, the injured young spear fighter with blue scales"
ENEMY = "<Subject 2>, the towering connected black liquid-stone humanoid"
SPEAR = "<Subject 3>, the single weathered wooden spear"
SUBJECT_BRIEFS = {1: FIGHTER, 2: ENEMY, 3: SPEAR}


def _times(duration: float, variant: str) -> tuple[float, float, float]:
    ratios = {
        "A": (0.25, 0.50, 0.75),
        "D": (0.19, 0.44, 0.71),
        "E": (0.15, 0.38, 0.66),
    }[variant]
    return tuple(round(duration * ratio, 3) for ratio in ratios)


def _tag_entities(text: str) -> str:
    value = str(text).strip()
    possessives = (
        (r"\bthe blue-scaled young spear fighter's\b", "<Subject 1>'s"),
        (r"\bthe young spear fighter's\b", "<Subject 1>'s"),
        (r"\bthe fallen fighter's\b", "<Subject 1>'s"),
        (r"\bthe fighter's\b", "<Subject 1>'s"),
        (r"\bthe towering black humanoid's\b", "<Subject 2>'s"),
        (r"\bthe black humanoid's\b", "<Subject 2>'s"),
        (r"\bthe enemy's\b", "<Subject 2>'s"),
        (r"\bthe spear's\b", "<Subject 3>'s"),
    )
    for pattern, replacement in possessives:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    substitutions = (
        (r"\bthe blue-scaled young spear fighter\b", FIGHTER),
        (r"\bthe young spear fighter\b", FIGHTER),
        (r"\bthe fallen fighter\b", FIGHTER),
        (r"\bthe fighter\b", FIGHTER),
        (r"\bher\b", "her"),
        (r"\bthe towering black humanoid\b", ENEMY),
        (r"\bthe black humanoid\b", ENEMY),
        (r"\bthe enemy\b", ENEMY),
        (r"\bthe single wooden spear\b", SPEAR),
        (r"\bthe intact spear\b", SPEAR),
        (r"\bthe spear\b", SPEAR),
    )
    for pattern, replacement in substitutions:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    return value


def _shot_subject_ids(panel: str, action: str) -> tuple[int, ...]:
    """Resolve the visible/causal identity anchors required by one Shot."""
    text = f"{panel} {action}".lower()
    subject_ids: list[int] = []
    if any(token in text for token in (
        "fighter", " she ", " her ", "human left", "scaled right", "eye", "breath",
        "wrist mark", "shield", "toe", "foot", "knee", "elbow shakes",
    )):
        subject_ids.append(1)
    if any(token in text for token in (
        "enemy", "black", "humanoid", "palm", "fingertip", "shoulder rotation",
        "chest", "surface", "indentation", "dark ripples", "long arm", "right arm",
        "left hand", "right hand", "lower mass", "crown", "connected mass",
    )):
        subject_ids.append(2)
    if any(token in text for token in (
        "spear", "shaft", "weapon", "metal point", "rear grip", "spear point",
    )):
        subject_ids.append(3)
    return tuple(subject_ids or [1])


def _subject_context(subject_ids: tuple[int, ...]) -> str:
    return "; ".join(SUBJECT_BRIEFS[subject_id] for subject_id in subject_ids)


def _composition(panel: str, variant: str, subject_ids: tuple[int, ...]) -> str:
    state = str(panel).strip()
    context = _subject_context(subject_ids)
    anchors = (
        "Use <Picture 4> for the Heartstone chamber background. "
        "Use <Picture 5> only for an effect explicitly named in this Shot; do not add an unrequested effect."
    )
    if variant == "A":
        return f"Starting composition: {context}. {anchors} {state}"
    if variant == "D":
        return (
            f"Starting composition: {context}. {anchors} Preserve the exact subject placement and state, "
            f"but use a more forceful oblique or low viewpoint: {state}"
        )
    return (
        f"Starting composition: {context}. {anchors} Preserve the exact subject placement and state, "
        f"but use stronger foreground depth and compressed perspective: {state}"
    )


def _action(text: str, subject_ids: tuple[int, ...]) -> str:
    return f"Following action: {_subject_context(subject_ids)}. {str(text).strip()}"


def _dialogue_clause(row: dict[str, Any]) -> str:
    speaker = int(row["speaker"])
    listener = int(row["listener"])
    shot = int(row["shot"])
    return (
        f"<Subject {speaker}> (S{shot}), delivery: {str(row['delivery']).strip()}: "
        f"<d>[Korean] {str(row['line']).strip()}</d> "
        f"Listener <Subject {listener}>: mouth closed."
    )


def _plans(clip: dict[str, Any]) -> dict[str, Any]:
    dialogue_by_shot: dict[int, list[dict[str, Any]]] = {}
    for row in clip["dialogue"]:
        dialogue_by_shot.setdefault(int(row["shot"]), []).append(row)
    plans: dict[str, Any] = {}
    for variant in ("A", "D", "E"):
        starts = _times(float(clip["duration"]), variant)
        shots: list[dict[str, Any]] = []
        for index, (panel, action) in enumerate(
            zip(clip["panels"], clip["actions"], strict=True), start=1
        ):
            subject_ids = _shot_subject_ids(str(panel), str(action))
            beat_action = _action(str(action), subject_ids)
            dialogue = " ".join(
                _dialogue_clause(row) for row in dialogue_by_shot.get(index, [])
            )
            if dialogue:
                beat_action += " " + dialogue
            shot: dict[str, Any] = {
                "camera": _composition(str(panel), variant, subject_ids),
                "beat_ids": [f"P{index}"],
            }
            if index > 1:
                shot["start_seconds"] = starts[index - 2]
            shots.append(shot)
        plans[variant] = {
            "emphasis": {
                "A": "neutral readable compositions for all four states",
                "D": "oblique and low viewpoints for stronger physical force",
                "E": "foreground depth and compressed perspective for stronger pressure",
            }[variant],
            "shots": shots,
        }
        # Beats are shared by all candidates, so store the candidate-independent
        # actions separately from the candidate-specific starting compositions.
        plans[variant]["beat_actions"] = [
            _action(str(action), _shot_subject_ids(str(panel), str(action)))
            for panel, action in zip(clip["panels"], clip["actions"], strict=True)
        ]
    return plans


def _assets() -> dict[str, Any]:
    return {
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
            "retention_description": "Preserve one fighter, exact face, clothing, scale boundaries, accumulated water, fatigue, and injury.",
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
            "retention_description": "Preserve exactly one intact fixed-length spear and its current ownership or off-screen location.",
        },
        "heartstone-background": {
            "role": "heartstone_chamber_environment",
            "label": "approved Heartstone chamber environment",
            "copy_from": "../rebuild_v2/action_moment_test_v1/images/HEARTSTONE_CHAMBER_ENVIRONMENT_V1.png",
            "standalone_picture_name": "the Heartstone altar chamber environment",
            "standalone_picture_description": (
                "A dark circular stone altar chamber with concentric wet floor rings, restrained cyan water channels, "
                "a low central dais, carved masonry, and stable architectural scale; use it only as the location background."
            ),
            "retention_marker": "fully_preserved",
            "retention_shots": [1, 2, 3, 4],
            "retention_description": "Preserve the same chamber layout, wet floor, cyan channels, central dais, and screen geography in all four Shots.",
        },
        "ep00-effects": {
            "role": "ep00_cyan_current_and_shield_effect_language",
            "label": "approved EP00 cyan current and shield effect language",
            "copy_from": "../Dragon_Language_Current_Shield_Effects.png",
            "standalone_picture_name": "the approved cyan current and shield effect language",
            "standalone_picture_description": (
                "A visual-form reference for translucent cyan water-current rings and curved or vertical water shields; "
                "use only the effect type explicitly named in a Shot and never reproduce the reference image layout."
            ),
            "retention_marker": "partially_preserved",
            "retention_shots": [1, 2, 3, 4],
            "retention_description": "Keep the approved translucent cyan water language only when the Shot explicitly calls for that effect; otherwise keep it absent.",
        },
    }


def build_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    clips: list[dict[str, Any]] = []
    contracts: dict[str, Any] = {}
    for sequence, source in enumerate(CLIPS, start=1):
        clip_id = str(source["clip_id"])
        state_in = f"EP00V2_TEXT_STATE_{sequence - 1:02d}"
        state_out = f"EP00V2_TEXT_STATE_{sequence:02d}"
        plans = _plans(source)
        continuity_in = (
            "Continuity in: retain <Subject 1>, <Subject 2>, and <Subject 3> injury, "
            "distance, screen direction, and ownership; off-frame subjects stay off-frame."
        )
        continuity_out = (
            "End on the resulting physical state of <Subject 1>, <Subject 2>, and <Subject 3>."
        )
        beats = []
        dialogue_by_shot: dict[int, list[dict[str, Any]]] = {}
        for row in source["dialogue"]:
            dialogue_by_shot.setdefault(int(row["shot"]), []).append(row)
        for index, action in enumerate(source["actions"], start=1):
            subject_ids = _shot_subject_ids(
                str(source["panels"][index - 1]), str(action)
            )
            description = _action(str(action), subject_ids)
            clauses = " ".join(
                _dialogue_clause(row) for row in dialogue_by_shot.get(index, [])
            )
            if clauses:
                description += " " + clauses
            beats.append({"beat_id": f"P{index}", "description": description})
        contracts[clip_id] = {
            "shared_event": str(source["summary"]),
            "bridge_in_id": state_in,
            "bridge_out_id": state_out,
            "boundary_policy": "terminal" if sequence == len(CLIPS) else "referenced_cut",
            "source_shot_ids": [clip_id],
            "incoming_reference_subjects": [1, 2, 3],
            "outgoing_reference_subjects": [1, 2, 3],
            "incoming_bridge": continuity_in,
            "outgoing_bridge": continuity_out,
            "storyboard_required": False,
            "storyboard_mode": MODE,
            "beats": beats,
            "candidate_plans": {
                variant: {
                    "emphasis": plans[variant]["emphasis"],
                    "shots": plans[variant]["shots"],
                }
                for variant in ("A", "D", "E")
            },
        }
        required_dialogue = [str(row["line"]) for row in source["dialogue"]]
        clips.append({
            "scene_id": str(source["scene_id"]),
            "clip_id": clip_id,
            "sequence": sequence,
            "source_shot_id": clip_id,
            "status": "pending_user_prompt_review",
            "duration_seconds": float(source["duration"]),
            "references": ["fighter", "enemy", "spear", "heartstone-background", "ep00-effects"],
            "prompt_base": {
                "summary": str(source["summary"]),
                "style_opening": [
                    "High-detail hand-drawn 2D cel animation; every Shot begins from the written composition and performs only the following written action; use the attached chamber as the location, use only explicitly named attached effect forms, and never render a reference-sheet background or layout"
                ],
                "overall_soundscape": "Only sounds directly caused by the four written actions and the exact written dialogue.",
                "non_diegetic_music": "None.",
            },
            "prompt_variants": [
                {
                    "variant_id": variant,
                    "label": {
                        "A": "Candidate A · neutral readable direction",
                        "D": "Candidate D · oblique physical direction",
                        "E": "Candidate E · compressed pressure direction",
                    }[variant],
                    "rationale": {
                        "A": "Neutral readable viewpoint and balanced Shot spacing.",
                        "D": "Lower or oblique viewpoint and earlier physical acceleration.",
                        "E": "Foreground depth, compressed perspective, and tighter pressure spacing.",
                    }[variant],
                    "prompt_spec": {},
                }
                for variant in ("A", "D", "E")
            ],
            "canonical_source_lineage": ["EP00_READER_SCREENPLAY_ACTION_REVISION_V2.md"],
            "locked_rule_id": "EP00_READER_ACTION_V2_TEXT_DIRECTED_V1",
            "continuity_in": state_in,
            "continuity_out": state_out,
            "summary": str(source["summary"]),
            "required_dialogue": required_dialogue,
            "dialogue_lock_version": "EP00_V2_DIALOGUE_LOCK_V1",
            "action_requirements": {
                "shot_count": 4,
                "each_shot_requires": ["Starting composition", "Following action"],
                "storyboard_picture_used": False,
                "background_picture_id": BACKGROUND_PICTURE_ID,
                "effect_picture_id": EFFECT_PICTURE_ID,
                "background_and_effect_assets_required": True,
                "delegated_shots": [],
            },
            "scene_type": h3_prompt_projects.ACTION_SCENE_TYPE,
            "prompt_profile": h3_prompt_projects.ACTION_PROMPT_PROFILE,
            "prompt_generator": h3_prompt_projects.ACTION_PROMPT_GENERATOR,
            "action_scene_contract": {
                "version": h3_prompt_projects.ACTION_SCENE_CONTRACT_VERSION,
                "phase": "reader_action_v2_text_directed_four_shot",
                "speed_profiles": ["Begin from the written state and perform one following action." for _ in range(4)],
                "motion_links": ["Preserve the resulting state across the cut." for _ in range(3)],
                "environmental_proof": "Wet floor water, cyan channels, debris, contact deformation, and injury prove the written action.",
                "storyboard_mode": MODE,
                "storyboard_picture_id": 0,
                "background_picture_id": BACKGROUND_PICTURE_ID,
                "effect_picture_id": EFFECT_PICTURE_ID,
            },
            "authoring_notes": "No storyboard Picture. Picture 4 fixes the chamber background and Picture 5 fixes only explicitly named effects. Every Shot explicitly contains a starting composition and one following action. No queue or video generation.",
            "semantic_review": "pending_user_prompt_review",
        })
    spec = {
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · Reader Action V2 · Text-Directed A/D/E V1",
        "description": "Independent non-storyboard project with mandatory chamber-background and effect-language Pictures plus a complete starting composition and action in every Shot.",
        "source_policy": "ep00_reader_action_revision_v2_text_directed_only",
        "canonical_source_lineage": ["EP00_READER_SCREENPLAY_ACTION_REVISION_V2.md"],
        "locked_rule_id": "EP00_READER_ACTION_V2_TEXT_DIRECTED_V1",
        "build_script": "scripts/build_ep00_reader_action_v2_text_directed_project.py",
        "prompt_profile": h3_prompt_projects.ACTION_PROMPT_PROFILE,
        "prompt_generator": h3_prompt_projects.ACTION_PROMPT_GENERATOR,
        "dialogue_lock_version": "EP00_V2_DIALOGUE_LOCK_V1",
        "dialogue_clip_count": len({str(row["clip_id"]) for row in DIALOGUE_LOCK}),
        "dialogue_line_count": len(DIALOGUE_LOCK),
        "event_contracts_file": CONTRACTS_PATH.name,
        "asset_catalog": _assets(),
        "clips": clips,
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


def main() -> int:
    spec, events = build_payloads()
    SPEC_PATH.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CONTRACTS_PATH.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = h3_prompt_project_builder.build_project(ROOT, SPEC_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
