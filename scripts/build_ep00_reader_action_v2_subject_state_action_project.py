from __future__ import annotations

"""Build a new EP00 V2 prompt project with one Subject header per Shot."""

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
from scripts import build_ep00_reader_action_v2_clean_bgfx_dialogue_project as clean  # noqa: E402
from scripts.ep00_reader_action_v2_project_data import CLIPS  # noqa: E402


SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_reader_action_v2_subject_state_action_new"
PROJECT_ID = "RaisingaDragonSeason01_EP00_READER_ACTION_V2_H3_R2V_SUBJECT_STATE_ACTION_ADE_V3"
SPEC_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_SUBJECT_STATE_ACTION_ADE_V3_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_SUBJECT_STATE_ACTION_ADE_V3_EVENT_CONTRACTS.json"
MODE = h3_prompt_projects.FOUR_SUBJECT_STATE_ACTION_MODE

SUBJECT_BRIEFS = {
    1: "<Subject 1>, the injured young spear fighter with blue scales",
    2: "<Subject 2>, the towering connected black liquid-stone humanoid",
    3: "<Subject 3>, the single weathered wooden spear",
}


def _subject_ids(text: str) -> tuple[int, ...]:
    return tuple(dict.fromkeys(int(value) for value in re.findall(r"<Subject (\d+)>", text)))


def _visible_subject_ids(state: str, action: str) -> tuple[int, ...]:
    text = f" {state} {action} ".lower()
    ids: list[int] = []
    if any(token in text for token in (
        "fighter", " she ", " her ", "human left", "scaled right", "eye", "breath",
        "wrist", "shield", "toe", "foot", "knee", "elbow",
    )):
        ids.append(1)
    if any(token in text for token in (
        "enemy", "black", "humanoid", "palm", "fingertip", "shoulder", "chest",
        "dark ripple", "long arm", "right arm", "left hand", "right hand", "pressure wake",
    )):
        ids.append(2)
    if any(token in text for token in (
        "spear", "shaft", "weapon", "metal point", "rear grip", "spear point",
    )):
        ids.append(3)
    return tuple(ids)


def _primary_header(
    ids: tuple[int, ...], state: str, action: str, background_id: int, effect_id: int
) -> str:
    if ids:
        return _subject_header(ids)
    text = f"{state} {action}".lower()
    if any(value in text for value in ("cyan", "current", "water", "shield")):
        return f"<Picture {effect_id}>, the approved cyan current and water-effect language"
    return f"<Picture {background_id}>, the Heartstone altar chamber environment"


def _subject_header(ids: tuple[int, ...]) -> str:
    return "; ".join(SUBJECT_BRIEFS[value] for value in ids)


def _viewpoint(variant: str) -> str:
    return {
        "A": "Keep a neutral readable viewpoint.",
        "D": "Use a forceful oblique or low viewpoint without changing subject placement.",
        "E": "Use stronger foreground depth and compressed perspective without changing subject placement.",
    }[variant]


def _spoken_clause(row: dict[str, Any]) -> str:
    return (
        f"<Subject {int(row['speaker'])}> (S{int(row['shot'])}), delivery: "
        f"{str(row['delivery']).strip()}: <d>[Korean] {str(row['line']).strip()}</d> "
        f"Listener <Subject {int(row['listener'])}>: mouth closed."
    )


def _internal_clause(row: dict[str, Any]) -> str:
    return (
        f"<Subject 1> (S{int(row['shot'])}), delivery: {str(row['delivery']).strip()}: "
        f"<d>[Korean] {str(row['line']).strip()}</d> "
        "Internal voice-over; no visible lip movement; <Subject 2> remains silent."
    )


def _dialogue_by_clip_shot() -> dict[tuple[str, int], list[str]]:
    result: dict[tuple[str, int], list[str]] = {}
    for clip in CLIPS:
        for row in clip["dialogue"]:
            result.setdefault((str(clip["clip_id"]), int(row["shot"])), []).append(
                _spoken_clause(row)
            )
    for row in clean.INTERNAL_MONOLOGUE:
        result.setdefault((str(row["clip_id"]), int(row["shot"])), []).append(
            _internal_clause(row)
        )
    return result


def build_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    base_spec, base_events = clean.build_payloads()
    spec = deepcopy(base_spec)
    events = deepcopy(base_events)
    source_by_id = {str(row["clip_id"]): row for row in CLIPS}
    dialogue = _dialogue_by_clip_shot()

    spec.update({
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · Subject → State → Action A/D/E V3",
        "description": (
            "A separate non-storyboard project where every Shot contains one Subject tag/description block, "
            "then one starting state, then one action without repeating identity prose."
        ),
        "source_policy": "ep00_reader_action_revision_v2_subject_state_action_only",
        "locked_rule_id": "EP00_READER_ACTION_V2_SUBJECT_STATE_ACTION_V3",
        "build_script": "scripts/build_ep00_reader_action_v2_subject_state_action_project.py",
        "event_contracts_file": CONTRACTS_PATH.name,
    })
    events["project_id"] = PROJECT_ID

    for clip in spec["clips"]:
        clip_id = str(clip["clip_id"])
        source = source_by_id[clip_id]
        contract = events["clips"][clip_id]
        contract["storyboard_mode"] = MODE
        ids_by_shot: list[tuple[int, ...]] = []
        for state, action in zip(source["panels"], source["actions"], strict=True):
            ids_by_shot.append(_visible_subject_ids(str(state), str(action)))
        used_subject_ids = sorted({value for ids in ids_by_shot for value in ids})
        if used_subject_ids not in ([1, 2], [1, 2, 3]):
            raise ValueError(f"{clip_id} Subject IDs must remain contiguous: {used_subject_ids}")
        background_picture_id = len(used_subject_ids) + 1
        effect_picture_id = background_picture_id + 1
        clip["references"] = [
            *(["fighter", "enemy", "spear"][: len(used_subject_ids)]),
            "heartstone-background",
            "ep00-effects",
        ]
        contract["incoming_reference_subjects"] = list(ids_by_shot[0])
        contract["outgoing_reference_subjects"] = list(ids_by_shot[-1])

        for shot_number, (action, ids) in enumerate(
            zip(source["actions"], ids_by_shot, strict=True), start=1
        ):
            clauses = dialogue.get((clip_id, shot_number), [])
            description = f"Action: {str(action).strip()}"
            if clauses:
                description += " " + " ".join(clauses)
            contract["beats"][shot_number - 1]["description"] = description

        for variant in ("A", "D", "E"):
            for shot_number, (shot, state, ids) in enumerate(
                zip(
                    contract["candidate_plans"][variant]["shots"],
                    source["panels"],
                    ids_by_shot,
                    strict=True,
                ),
                start=1,
            ):
                primary = _primary_header(
                    ids,
                    str(state),
                    str(source["actions"][shot_number - 1]),
                    background_picture_id,
                    effect_picture_id,
                )
                anchors: list[str] = []
                if f"<Picture {background_picture_id}>" not in primary:
                    anchors.append(
                        f"Use <Picture {background_picture_id}> as the Heartstone chamber background."
                    )
                if f"<Picture {effect_picture_id}>" not in primary:
                    anchors.append(
                        f"Use <Picture {effect_picture_id}> only if this Shot explicitly names a cyan current or water shield."
                    )
                shot["camera"] = (
                    f"{primary}. {' '.join(anchors)} "
                    f"{_viewpoint(variant)} Starting state: {str(state).strip()}"
                )

        clip["locked_rule_id"] = "EP00_READER_ACTION_V2_SUBJECT_STATE_ACTION_V3"
        clip["prompt_base"]["style_opening"] = [
            "High-detail hand-drawn 2D cel animation; in each Shot read the Subject identity once, begin from the written starting state, then perform only the written action; never render a reference-sheet background or layout"
        ]
        clip["action_requirements"].update({
            "each_shot_requires": ["Subject tag and short description", "Starting state", "Action"],
            "subject_description_count_per_shot": 1,
            "action_repeats_subject_description": False,
            "background_picture_id": background_picture_id,
            "effect_picture_id": effect_picture_id,
        })
        clip["action_scene_contract"]["storyboard_mode"] = MODE
        clip["action_scene_contract"]["phase"] = "reader_action_v2_subject_state_action_four_shot"
        clip["action_scene_contract"]["background_picture_id"] = background_picture_id
        clip["action_scene_contract"]["effect_picture_id"] = effect_picture_id
        clip["authoring_notes"] = (
            "Separate non-storyboard project. Each Shot follows Subject tag plus one short description, "
            "Starting state, Action, and assigned dialogue. Subject descriptions never repeat inside Action."
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
