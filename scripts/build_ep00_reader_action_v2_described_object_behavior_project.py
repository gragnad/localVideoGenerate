from __future__ import annotations

"""Build EP00 V2 with description, state, and behavior continuous per object."""

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
from scripts import build_ep00_reader_action_v2_object_behavior_project as previous  # noqa: E402
from scripts import build_ep00_reader_action_v2_subject_state_action_project as source_tools  # noqa: E402
from scripts.ep00_reader_action_v2_project_data import CLIPS  # noqa: E402


SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_reader_action_v2_described_object_behavior_new"
PROJECT_ID = "RaisingaDragonSeason01_EP00_READER_ACTION_V2_H3_R2V_DESCRIBED_OBJECT_BEHAVIOR_ADE_V5"
SPEC_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_DESCRIBED_OBJECT_BEHAVIOR_ADE_V5_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_DESCRIBED_OBJECT_BEHAVIOR_ADE_V5_EVENT_CONTRACTS.json"
MODE = h3_prompt_projects.FOUR_DESCRIBED_OBJECT_BEHAVIOR_MODE

DESCRIPTIONS = {
    1: "the injured young spear fighter with blue scales",
    2: "the towering connected black liquid-stone humanoid",
    3: "the single weathered wooden spear",
}


def _lower_first(text: str) -> str:
    value = str(text).strip().rstrip(".?!")
    return value[:1].lower() + value[1:] if value else value


def _action_clause(subject_id: int, action: str) -> str:
    value = str(action).strip().rstrip(".?!")
    substitutions = {
        1: (
            (r"^The fighter\s+", ""),
            (r"^She\s+", "she "),
            (r"^Her\s+", "her "),
        ),
        2: (
            (r"^The enemy\s+", ""),
            (r"^The black humanoid\s+", ""),
            (r"^The black palm\s+", "its black palm "),
            (r"^The palm\s+", "its palm "),
            (r"^The hand\s+", "its hand "),
        ),
        3: (
            (r"^The spear\s+", "it "),
            (r"^The shaft\s+", "its shaft "),
            (r"^The weapon\s+", "it "),
        ),
    }
    for pattern, replacement in substitutions[subject_id]:
        updated = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
        if updated != value:
            value = updated
            break
    return _lower_first(value)


def _subject_unit(subject_id: int, action: str, active: set[int]) -> str:
    description = DESCRIPTIONS[subject_id]
    if subject_id in active:
        behavior = _action_clause(subject_id, action)
        return (
            f"<Subject {subject_id}> {description} begins in its established Shot state "
            f"and {behavior}."
        )
    passive = previous._subject_behavior(subject_id, action, active).rstrip(".?!")
    return f"<Subject {subject_id}> {description} {passive}."


def _viewpoint(variant: str) -> str:
    return {
        "A": "a neutral readable viewpoint",
        "D": "a forceful oblique or low viewpoint that preserves placement",
        "E": "stronger foreground depth and compressed perspective that preserve placement",
    }[variant]


def _effect_clause(behavior: str) -> str:
    value = str(behavior).strip().rstrip(".?!")
    if value[:1].isupper():
        return f"shows {_lower_first(value)}"
    return value


def build_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    base_spec, base_events = previous.build_payloads()
    spec = deepcopy(base_spec)
    events = deepcopy(base_events)
    source_by_id = {str(row["clip_id"]): row for row in CLIPS}
    dialogue = source_tools._dialogue_by_clip_shot()

    spec.update({
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · Described Object State and Behavior A/D/E V5",
        "description": (
            "A separate non-storyboard project where each object tag continues directly through "
            "one short description, its current state, and its own behavior."
        ),
        "source_policy": "ep00_reader_action_revision_v2_described_object_behavior_only",
        "locked_rule_id": "EP00_READER_ACTION_V2_DESCRIBED_OBJECT_BEHAVIOR_V5",
        "build_script": "scripts/build_ep00_reader_action_v2_described_object_behavior_project.py",
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
        subject_ids_by_shot = [
            source_tools._visible_subject_ids(str(state), str(action))
            for state, action in zip(source["panels"], source["actions"], strict=True)
        ]
        contract["incoming_reference_subjects"] = list(subject_ids_by_shot[0])
        contract["outgoing_reference_subjects"] = list(subject_ids_by_shot[-1])

        for variant in ("A", "D", "E"):
            for shot_number, (shot, state, action, subject_ids) in enumerate(
                zip(
                    contract["candidate_plans"][variant]["shots"],
                    source["panels"],
                    source["actions"],
                    subject_ids_by_shot,
                    strict=True,
                ),
                start=1,
            ):
                active = previous._active_subject_ids(str(action))
                units = [_subject_unit(value, str(action), active) for value in subject_ids]
                units.append(
                    f"<Picture {background_id}> the Heartstone altar chamber environment "
                    f"presents {_lower_first(previous._clean_state(str(state)))} with {_viewpoint(variant)}."
                )
                effect_behavior = previous._effect_behavior(str(state), str(action), active)
                units.append(
                    f"<Picture {effect_id}> the approved cyan current and water-effect language "
                    f"{_effect_clause(effect_behavior)}."
                )
                units.extend(dialogue.get((clip_id, shot_number), []))
                shot["camera"] = " ".join(units)

        clip["locked_rule_id"] = "EP00_READER_ACTION_V2_DESCRIBED_OBJECT_BEHAVIOR_V5"
        clip["prompt_base"]["style_opening"] = [
            "High-detail hand-drawn 2D cel animation; for each object continue directly from its tag through one short description, its current state, and its own behavior before introducing the next object; use no State, Action, or Behavior labels and never render a reference-sheet background or layout"
        ]
        clip["action_requirements"].update({
            "each_object_order": ["tag", "short description", "current state", "own behavior"],
            "description_and_behavior_separated_into_groups": False,
            "punctuation_immediately_after_object_tag": False,
            "state_action_labels_used": False,
        })
        clip["action_scene_contract"]["storyboard_mode"] = MODE
        clip["action_scene_contract"]["phase"] = "reader_action_v2_described_object_behavior_four_shot"
        clip["authoring_notes"] = (
            "Separate non-storyboard project. Each object unit is tag, short description, current state, "
            "and that object's behavior as one continuous sentence before the next object."
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
