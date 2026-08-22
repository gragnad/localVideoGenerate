from __future__ import annotations

"""Build the EP00 action-revision V2 prompt review project.

V5 carries every new canonical action and Korean line, but remains generation
blocked until the eight stale 2D storyboards listed in the alignment audit are
regenerated and approved.
"""

import copy
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_project_builder  # noqa: E402
import build_ep00_2d_temporal_storyboard_ade_v4 as source  # noqa: E402


SOURCE_DIR = source.SOURCE_DIR
PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_2D_ACTION_REVISION_V2_ADE_V5"
SPEC_PATH = SOURCE_DIR / "EP00_H3_R2V_2D_ACTION_REVISION_V2_ADE_V5_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP00_H3_R2V_2D_ACTION_REVISION_V2_ADE_V5_EVENT_CONTRACTS.json"
SOURCE_SCREENPLAY = "EP00_READER_SCREENPLAY_ACTION_REVISION_V2.md"
SOURCE_SHA256 = "22786cca1be10f0ecf37caf9db23daf63279d6b66efbdad4f64d260f241d785e"
LOCK_ID = "EP00_ACTION_REVISION_V2_PROMPT_ALIGNMENT_V1"
STALE_STORYBOARD_CLIPS = {
    "EP00-S01-C01",
    "EP00-S02-C02",
    "EP00-S04-C03",
    "EP00-S05-C01",
    "EP00-S05-C02",
    "EP00-S05-C03",
    "EP00-S06-C01",
    "EP00-S06-C02",
}


def spoken(subject_id: int, delivery: str, line: str, listener_id: int) -> str:
    return (
        f"<Subject {subject_id}> (S1), {delivery}: <d>[Korean] {line}</d> "
        f"Listener <Subject {listener_id}>: mouth closed."
    )


ACTIONS = copy.deepcopy(source.ACTIONS)
ACTIONS.update({
    "EP00-S01-C01": (
        "Three cyan channel sections extinguish while <Subject 1>, the young spear fighter with blue scales, measures the shrinking route.",
        " ".join((
            spoken(2, "speaks in a low restrained voice", "혼자서도 여기까지 왔구나.", 1),
            "<Subject 1>, the young spear fighter with blue scales, keeps watching shoulder, elbow, and contact hand instead of the face.",
        )),
        "<Subject 2>, the towering black liquid-stone humanoid, begins turning the right shoulder before moving the palm.",
        "<Subject 1>, the young spear fighter with blue scales, compresses her knees but the over-tight spear grip delays her launch.",
    ),
    "EP00-S02-C02": (
        " ".join((
            "<Subject 2>, the towering black liquid-stone humanoid, stops the spear with one short hand closure.",
            spoken(2, "gives one quiet command", "놓아라.", 1),
        )),
        "<Subject 1>, the young spear fighter with blue scales, answers by clamping both hands harder around the rear shaft.",
        "<Subject 2>, the towering black liquid-stone humanoid, lifts fighter and spear together and rotates one shoulder.",
        "<Subject 1>, the young spear fighter with blue scales, pulls the spear to her chest and turns her shoulder and back toward the floor.",
    ),
    "EP00-S04-C03": (
        "<Subject 1>, the young spear fighter with blue scales, takes two steps deeper between the separated hands.",
        "Her human left foot catches the groove; her waist drops and the spear point falls one hand-width below its target.",
        " ".join((
            "Her voice and segmented scale light fail together.",
            spoken(2, "states the diagnosis without raising his voice", "힘이 아니라.", 1),
            spoken(2, "continues in the same measured tone", "힘과 힘 사이가 느리구나.", 1),
        )),
        "<Subject 1>, the fallen young spear fighter with blue scales, silently redirects the spear from the chest to the channel contact point.",
    ),
    "EP00-S05-C01": (
        "Torn shield water runs under the right black palm as <Subject 1>, the fallen young spear fighter with blue scales, strikes the floor with her left hand.",
        "The thin water wedge lifts the right palm by one fingernail and one cyan channel relights.",
        "She slides the middle of <Subject 3>, the weathered wooden spear, beneath the left wrist and locks the opposite end into a floor groove.",
        "Her scaled right leg extends the lever until both black hands lift and every chamber channel ignites together.",
    ),
    "EP00-S05-C02": (
        "The fully lit channels reveal the altar as the lifted black lower edge gives <Subject 1>, the young spear fighter with blue scales, one visible chance.",
        "<Subject 2>, the towering black liquid-stone humanoid, liquefies only the left wrist around both sides of the spear shaft and removes its resistance.",
        "The same black liquid reforms as one left hand behind the shaft, presses the channel, and extinguishes half the light.",
        "Its free right hand pulls the spear upward and rotates the shaft, flipping the fighter because her numb fingers release too late.",
    ),
    "EP00-S05-C03": (
        "<Subject 2>, the towering black liquid-stone humanoid, releases the spear and opens that same right hand over the falling fighter.",
        "The palm drives <Subject 1>, the young spear fighter with blue scales, into the floor; stone drops and circular water bursts outward.",
        "<Subject 3>, the weathered wooden spear, leaves her grip, hits two channel lips, then spins and slides into the far darkness.",
        "Cyan channels extinguish from the outer ring inward while the fighter remains down and the black body remains unwounded.",
    ),
    "EP00-S06-C01": (
        "<Subject 1>, the defeated young spear fighter with blue scales, raises her torso by one palm-width, slips down, and fails a second attempt.",
        "She looks from the distant spear to her dark wrist as Dragon Eye, shield water, and voice remain inactive.",
        " ".join((
            "<Subject 2>, the towering black liquid-stone humanoid, advances as one connected lower mass and lowers an open right hand until its shadow covers her.",
            spoken(2, "speaks without haste", "놓았더라면 아프지 않았을 것이다.", 1),
        )),
        " ".join((
            spoken(1, "forces the words through a damaged breath", "그 말….", 2),
            spoken(1, "finishes with exhausted refusal", "진짜 싫어.", 2),
            "The open black palm descends farther over her face.",
        )),
    ),
    "EP00-S06-C02": (
        "One unfamiliar internal heartbeat stops both <Subject 1>, the defeated young spear fighter with blue scales, and the descending black hand; no light, weapon, aura, or new figure appears.",
        "The two cyan eyes of <Subject 2>, the towering black liquid-stone humanoid, look separately toward the fighter and the dark end of the dead channel.",
        "The black palm lifts slightly and reveals one fighter eye holding a new question rather than an answer.",
        "The same palm lowers to cover the full frame and all sound cuts immediately before the second heartbeat.",
    ),
})


SUMMARIES = copy.deepcopy(source.SUMMARIES)
SUMMARIES.update({
    "EP00-S01-C01": "<Subject 2>, the towering black liquid-stone humanoid, speaks while closing the route, and the fighter reads his shoulder but launches late.",
    "EP00-S02-C02": "<Subject 2>, the towering black liquid-stone humanoid, orders release, uses the fighter's refusal, and throws her with the spear.",
    "EP00-S04-C03": "<Subject 1>, the young spear fighter with blue scales, loses one step to mismatched senses and silently retargets after the enemy names the gap between her powers.",
    "EP00-S05-C01": "<Subject 1>, the young spear fighter with blue scales, wedges water and spear under both hands until every chamber channel ignites.",
    "EP00-S05-C02": "<Subject 2>, the towering black liquid-stone humanoid, liquefies and reforms one wrist, steals the hand exchange, and flips the fighter by the spear.",
    "EP00-S05-C03": "<Subject 2>, the towering black liquid-stone humanoid, slams the fighter down as her spear escapes and the channels die from outside inward.",
    "EP00-S06-C01": "<Subject 1>, the defeated young spear fighter with blue scales, fails to rise, rejects the enemy's final words, and remains under his descending palm.",
    "EP00-S06-C02": "One unfamiliar heartbeat stops the black palm; the enemy's gaze splits, one questioning eye is revealed, and the palm completes the blackout before the second beat.",
})


DIALOGUE_BY_CLIP = {
    "EP00-S01-C01": ["혼자서도 여기까지 왔구나."],
    "EP00-S02-C02": ["놓아라."],
    "EP00-S04-C03": ["힘이 아니라.", "힘과 힘 사이가 느리구나."],
    "EP00-S06-C01": ["놓았더라면 아프지 않았을 것이다.", "그 말….", "진짜 싫어."],
}


START_STATES = copy.deepcopy(source.START_STATES)
START_STATES.update({
    "EP00-S01-C01": "<Subject 1>, the young spear fighter with blue scales, stands at the last open route with <Subject 3>, the weathered wooden spear, opposite <Subject 2>, the towering black liquid-stone humanoid, whose right palm is cutting one cyan channel.",
    "EP00-S02-C02": "<Subject 2>, the towering black liquid-stone humanoid, grips the middle of <Subject 3>, the weathered wooden spear, while <Subject 1>, the young spear fighter with blue scales, owns the rear grip.",
    "EP00-S04-C03": "<Subject 1>, the young spear fighter with blue scales, is already two steps inside the gap with <Subject 3>, the weathered wooden spear, aimed between the separated hands of <Subject 2>, the towering black liquid-stone humanoid.",
    "EP00-S05-C01": "<Subject 1>, the falling young spear fighter with blue scales, reaches her left hand toward the floor while torn shield water trails beside <Subject 3>, the weathered wooden spear, and the two channel-contact hands of <Subject 2>, the towering black liquid-stone humanoid.",
    "EP00-S05-C02": "<Subject 1>, the young spear fighter with blue scales, holds <Subject 3>, the weathered wooden spear, as a loaded lever while every cyan channel shines and both hands of <Subject 2>, the towering black liquid-stone humanoid, remain lifted.",
    "EP00-S05-C03": "<Subject 1>, the young spear fighter with blue scales, is falling beside <Subject 3>, the weathered wooden spear, under the free right hand of <Subject 2>, the towering black liquid-stone humanoid.",
    "EP00-S06-C01": "<Subject 1>, the defeated young spear fighter with blue scales, lies beneath <Subject 2>, the towering black liquid-stone humanoid, with <Subject 3>, the weathered wooden spear, far across the dark altar.",
    "EP00-S06-C02": "<Subject 1>, the defeated young spear fighter with blue scales, lies under the descending right palm of <Subject 2>, the towering black liquid-stone humanoid, with <Subject 3>, the weathered wooden spear, still distant.",
})


def build_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    spec, events = source.build_payloads()
    spec = copy.deepcopy(spec)
    events = copy.deepcopy(events)
    for clip in spec["clips"]:
        clip_id = str(clip["clip_id"])
        contract = events["clips"][clip_id]
        duration = float(clip["duration_seconds"])
        for variant_id in ("A", "D", "E"):
            starts = source.shot_starts(duration, variant_id)
            contract["candidate_plans"][variant_id]["shots"] = [
                {
                    "camera": (
                        f"{START_STATES[clip_id]} {action}"
                        if index == 1 else action
                    ),
                    "panel_index": index,
                    "panel_position": source.POSITIONS[index - 1],
                    "beat_ids": [f"P{index}"],
                    **({} if index == 1 else {"start_seconds": starts[index - 2]}),
                }
                for index, action in enumerate(ACTIONS[clip_id], start=1)
            ]
        clip["prompt_base"]["summary"] = SUMMARIES[clip_id]
        required_dialogue = DIALOGUE_BY_CLIP.get(clip_id, [])
        clip["required_dialogue"] = required_dialogue
        clip["prompt_base"]["overall_soundscape"] = (
            "Render each tagged Korean line exactly once in order with synchronized mouth movement only on its marked speaker; otherwise use only sounds caused by the four written Shot actions."
            if required_dialogue else
            "Only sounds directly caused by the four written Shot actions."
        )
        clip["canonical_source_lineage"] = [
            SOURCE_SCREENPLAY,
            "EP00_ACTION_REVISION_V2_PROMPT_ALIGNMENT_AUDIT_V1.md",
            *list(clip.get("canonical_source_lineage") or []),
        ]
        clip["locked_rule_id"] = LOCK_ID
        clip["storyboard_revision_status"] = (
            "stale_requires_v3_regeneration"
            if clip_id in STALE_STORYBOARD_CLIPS else
            "compatible_with_action_revision_v2"
        )
        clip["status"] = "prompt_review_only_generation_blocked"
        clip["semantic_review"] = "action_revision_v2_prompt_mapped_storyboard_revision_pending"
        clip["authoring_notes"] = (
            "Actions and dialogue follow EP00_READER_SCREENPLAY_ACTION_REVISION_V2. "
            "This project is review-only until all eight stale 2D boards are regenerated and approved."
        )

    spec.update({
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · 2D Action Revision V2 A/D/E V5",
        "description": "Prompt-complete review build for the reader screenplay action revision V2; generation remains blocked pending eight revised 2D storyboards.",
        "source_policy": "ep00_reader_screenplay_action_revision_v2_exact_dialogue_and_event_mapping",
        "canonical_source_lineage": [
            SOURCE_SCREENPLAY,
            "EP00_ACTION_REVISION_V2_PROMPT_ALIGNMENT_AUDIT_V1.md",
        ],
        "canonical_source_sha256": SOURCE_SHA256,
        "locked_rule_id": LOCK_ID,
        "build_script": "scripts/build_ep00_2d_action_revision_v2_ade_v5.py",
        "event_contracts_file": CONTRACTS_PATH.name,
        "generation_blocked": True,
        "generation_block_reason": "새 액션 개정 V2와 충돌하는 2D 스토리보드 8장의 V3 재생성·승인 전에는 영상을 생성할 수 없습니다.",
        "replacement_project_ids": [],
        "dialogue_lock_version": "ep00_action_revision_v2_dialogue_v1",
        "dialogue_clip_count": len(DIALOGUE_BY_CLIP),
        "dialogue_line_count": sum(len(value) for value in DIALOGUE_BY_CLIP.values()),
        "stale_storyboard_clips": sorted(STALE_STORYBOARD_CLIPS),
        "review_decision": "prompt_review_complete_storyboard_regeneration_pending_no_queue_no_video",
    })
    events.update({
        "project_id": PROJECT_ID,
        "locked_rule_id": LOCK_ID,
        "canonical_source_lineage": [SOURCE_SCREENPLAY],
        "canonical_source_sha256": SOURCE_SHA256,
    })
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
