from __future__ import annotations

"""Build a new clean EP00 V2 text-directed project.

This project is intentionally separate from every earlier EP00 prompt project.
It keeps mandatory background/effect Pictures and preserves both spoken lines
and screenplay-formatted internal monologue at their source Shot.
"""

from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_project_builder  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_reader_action_v2_text_directed_project as baseline  # noqa: E402


SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_reader_action_v2_clean_bgfx_dialogue_new"
PROJECT_ID = "RaisingaDragonSeason01_EP00_READER_ACTION_V2_H3_R2V_CLEAN_BGFX_DIALOGUE_ADE_V2"
SPEC_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_CLEAN_BGFX_DIALOGUE_ADE_V2_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP00_V2_H3_R2V_CLEAN_BGFX_DIALOGUE_ADE_V2_EVENT_CONTRACTS.json"


INTERNAL_MONOLOGUE: tuple[dict[str, Any], ...] = (
    {
        "clip_id": "EP00V2-S01-C03",
        "shot": 2,
        "line": "맞혀서라도 손을 떼게 한다.",
        "delivery": "a terse internal voice-over",
    },
    {
        "clip_id": "EP00V2-S02-C02",
        "shot": 3,
        "line": "정면으로는 못 버틴다.",
        "delivery": "a strained internal voice-over",
    },
    {
        "clip_id": "EP00V2-S02-C05",
        "shot": 3,
        "line": "한 손을 빼면 다른 손이 닫는다.",
        "delivery": "an analytical internal voice-over",
    },
    {
        "clip_id": "EP00V2-S02-C05",
        "shot": 4,
        "line": "그럼 둘 다 움직이게 한다.",
        "delivery": "a decisive internal voice-over",
    },
)


def _internal_clause(row: dict[str, Any]) -> str:
    return (
        f"<Subject 1> (S{int(row['shot'])}), delivery: {str(row['delivery']).strip()}: "
        f"<d>[Korean] {str(row['line']).strip()}</d> "
        "No visible lip movement; <Subject 2> remains silent."
    )


def build_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    raw_spec, raw_events = baseline.build_payloads()
    spec = deepcopy(raw_spec)
    events = deepcopy(raw_events)

    spec.update({
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · Reader Action V2 · Clean BG/FX + Dialogue A/D/E V2",
        "description": (
            "A separate clean text-directed project with mandatory chamber/effect assets, "
            "seven spoken lines, and four source internal-monologue lines."
        ),
        "source_policy": "ep00_reader_action_revision_v2_clean_bgfx_dialogue_only",
        "locked_rule_id": "EP00_READER_ACTION_V2_CLEAN_BGFX_DIALOGUE_V2",
        "build_script": "scripts/build_ep00_reader_action_v2_clean_bgfx_dialogue_project.py",
        "dialogue_lock_version": "EP00_V2_ALL_SCRIPT_LINES_LOCK_V2",
        "dialogue_clip_count": 7,
        "dialogue_line_count": 11,
        "event_contracts_file": CONTRACTS_PATH.name,
    })
    events["project_id"] = PROJECT_ID

    clips_by_id = {str(row["clip_id"]): row for row in spec["clips"]}
    contracts_by_id = events["clips"]
    for row in INTERNAL_MONOLOGUE:
        clip_id = str(row["clip_id"])
        shot = int(row["shot"])
        line = str(row["line"])
        clause = _internal_clause(row)
        clip = clips_by_id[clip_id]
        contract = contracts_by_id[clip_id]
        beat = contract["beats"][shot - 1]
        beat["description"] = f"{str(beat['description']).strip()} {clause}"
        clip["required_dialogue"].append(line)
        clip["dialogue_lock_version"] = "EP00_V2_ALL_SCRIPT_LINES_LOCK_V2"

    for clip in spec["clips"]:
        clip["locked_rule_id"] = "EP00_READER_ACTION_V2_CLEAN_BGFX_DIALOGUE_V2"
        clip["dialogue_lock_version"] = "EP00_V2_ALL_SCRIPT_LINES_LOCK_V2"
        clip["action_requirements"]["spoken_dialogue_and_internal_monologue_required"] = True
        clip["authoring_notes"] = (
            "Separate clean project. Pictures 4 and 5 are mandatory background/effect anchors. "
            "Quoted screenplay lines are spoken with visible mouth motion; italic screenplay lines are "
            "internal voice-over with no visible lip movement. No storyboard, queue, or video generation."
        )
    return spec, events


def main() -> int:
    if h3_prompt_projects.project_dir(ROOT, PROJECT_ID).exists():
        raise FileExistsError(
            f"Clean project already exists and will not be overwritten: {PROJECT_ID}"
        )
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    spec, events = build_payloads()
    SPEC_PATH.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CONTRACTS_PATH.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = h3_prompt_project_builder.build_project(ROOT, SPEC_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
