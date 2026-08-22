from __future__ import annotations

"""Build EP00 V2 with one state/behavior sentence immediately after each object tag."""

from copy import deepcopy
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
from scripts import build_ep00_reader_action_v2_subject_state_action_project as previous  # noqa: E402
from scripts.ep00_reader_action_v2_project_data import CLIPS  # noqa: E402


SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_reader_action_v2_object_behavior_new"
PROJECT_ID = "RaisingaDragonSeason01_EP00_READER_ACTION_V2_H3_R2V_OBJECT_BEHAVIOR_ADE_V4"
SPEC_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_OBJECT_BEHAVIOR_ADE_V4_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_OBJECT_BEHAVIOR_ADE_V4_EVENT_CONTRACTS.json"
MODE = h3_prompt_projects.FOUR_OBJECT_ACTION_PAIRS_MODE


def _clean_state(text: str) -> str:
    value = str(text).strip().rstrip(".?!")
    return re.sub(r"^([^:]{1,36}):\s*", r"\1 shows ", value)


def _active_subject_ids(action: str) -> set[int]:
    text = str(action).strip().lower()
    result: set[int] = set()
    if re.match(
        r"^(?:the fighter|she|her\b|dragon eye|the planted leg|the right leg|"
        r"the human left|her body|her gaze|her first|the toe|the damaged shield)",
        text,
    ):
        result.add(1)
    if re.match(
        r"^(?:the enemy|the black|the hand|the palm|the shoulder|the rotating shoulder|"
        r"the missed right|the left hand|the right hand|both hands|its)",
        text,
    ):
        result.add(2)
    if re.match(r"^(?:the spear|the shaft|the weapon|the scraping shaft|the point)", text):
        result.add(3)
    return result


def _subject_behavior(subject_id: int, action: str, active: set[int]) -> str:
    if subject_id in active:
        return str(action).strip().rstrip(".?!")
    return {
        1: "holds the established body position and reacts only to the contact or force stated in this Shot",
        2: "holds the established placement and makes no additional attack beyond the movement stated in this Shot",
        3: "stays in the established grip or contact and moves only through force applied by the other objects",
    }[subject_id]


def _effect_behavior(state: str, action: str, active_subjects: set[int]) -> str:
    text = f"{state} {action}".lower()
    effect_named = any(
        token in text
        for token in (
            "cyan", "current", "water", "shield", "light", "droplet", "ripple", "channel",
            "pressure wake", "dragon word", "dust", "grit",
        )
    )
    if not effect_named:
        return "remains absent and adds no extra effect"
    if not active_subjects:
        return str(action).strip().rstrip(".?!")
    return "follows only the effect response explicitly stated in this Shot"


def _viewpoint(variant: str) -> str:
    return {
        "A": "with a neutral readable viewpoint",
        "D": "with a forceful oblique or low viewpoint while preserving placement",
        "E": "with stronger foreground depth and compressed perspective while preserving placement",
    }[variant]


def build_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    base_spec, base_events = previous.build_payloads()
    spec = deepcopy(base_spec)
    events = deepcopy(base_events)
    source_by_id = {str(row["clip_id"]): row for row in CLIPS}
    dialogue = previous._dialogue_by_clip_shot()

    spec.update({
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · Object State and Behavior A/D/E V4",
        "description": (
            "A separate non-storyboard project where every object tag is immediately followed by "
            "that object's state and behavior without repeating its identity definition."
        ),
        "source_policy": "ep00_reader_action_revision_v2_object_behavior_only",
        "locked_rule_id": "EP00_READER_ACTION_V2_OBJECT_BEHAVIOR_V4",
        "build_script": "scripts/build_ep00_reader_action_v2_object_behavior_project.py",
        "event_contracts_file": CONTRACTS_PATH.name,
    })
    events["project_id"] = PROJECT_ID

    for clip in spec["clips"]:
        clip_id = str(clip["clip_id"])
        source = source_by_id[clip_id]
        contract = events["clips"][clip_id]
        contract["storyboard_mode"] = MODE
        background_id = int(clip["action_scene_contract"]["background_picture_id"])
        effect_id = int(clip["action_scene_contract"]["effect_picture_id"])

        ids_by_shot = [
            previous._visible_subject_ids(str(state), str(action))
            for state, action in zip(source["panels"], source["actions"], strict=True)
        ]
        contract["incoming_reference_subjects"] = list(ids_by_shot[0])
        contract["outgoing_reference_subjects"] = list(ids_by_shot[-1])

        for variant in ("A", "D", "E"):
            for shot_number, (shot, state, action, subject_ids) in enumerate(
                zip(
                    contract["candidate_plans"][variant]["shots"],
                    source["panels"],
                    source["actions"],
                    ids_by_shot,
                    strict=True,
                ),
                start=1,
            ):
                active = _active_subject_ids(str(action))
                units = [
                    f"<Subject {subject_id}> {_subject_behavior(subject_id, str(action), active)}."
                    for subject_id in subject_ids
                ]
                units.append(
                    f"<Picture {background_id}> presents {_clean_state(str(state))} {_viewpoint(variant)}."
                )
                units.append(
                    f"<Picture {effect_id}> {_effect_behavior(str(state), str(action), active)}."
                )
                units.extend(dialogue.get((clip_id, shot_number), []))
                shot["camera"] = " ".join(units)

        clip["locked_rule_id"] = "EP00_READER_ACTION_V2_OBJECT_BEHAVIOR_V4"
        clip["prompt_base"]["style_opening"] = [
            "High-detail hand-drawn 2D cel animation; each object tag is immediately followed by only that object's state and behavior; identity appearance stays in subject_definitions and is not repeated in Shots; never render a reference-sheet background or layout"
        ]
        clip["action_requirements"].update({
            "each_shot_requires": ["object tag followed immediately by object state and behavior"],
            "shot_level_shared_action_block": False,
            "identity_description_repeated_in_shot": False,
            "punctuation_immediately_after_object_tag": False,
        })
        clip["action_scene_contract"]["storyboard_mode"] = MODE
        clip["action_scene_contract"]["phase"] = "reader_action_v2_object_behavior_four_shot"
        clip["authoring_notes"] = (
            "Separate non-storyboard project. Object identity is defined once above. In every Shot each "
            "Subject or Picture tag is followed immediately by that object's state and behavior with no comma or colon."
        )
    return spec, events


def main() -> int:
    if h3_prompt_projects.project_dir(ROOT, PROJECT_ID).exists():
        raise FileExistsError(f"Project already exists and will not be overwritten: {PROJECT_ID}")
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    spec, events = build_payloads()
    SPEC_PATH.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CONTRACTS_PATH.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = h3_prompt_project_builder.build_project(ROOT, SPEC_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
