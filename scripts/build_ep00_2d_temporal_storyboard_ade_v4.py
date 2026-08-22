from __future__ import annotations

"""Build the current 2D EP00 as four concise timed storyboard Shots.

The approved rebuild_v2 storyboard is the visual source.  Every panel is the
starting image of one full-screen Shot; model-facing Shot text adds only the
short action that follows that image.  A/D/E keep identical action wording and
vary only the Shot start times.
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
import h3_prompt_projects  # noqa: E402
import build_ep00_action_storyboard_ade_v3 as source  # noqa: E402


SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "rebuild_v2"
PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_2D_TEMPORAL_STORYBOARD_ADE_V4"
SPEC_PATH = SOURCE_DIR / "EP00_H3_R2V_2D_TEMPORAL_STORYBOARD_ADE_V4_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP00_H3_R2V_2D_TEMPORAL_STORYBOARD_ADE_V4_EVENT_CONTRACTS.json"
MODE = h3_prompt_projects.FOUR_SHOT_TEMPORAL_STORYBOARD_MODE
POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")


START_STATES = {
    "EP00-S01-C01": "<Subject 1>, the young spear fighter with blue scales, stands small at the chamber edge holding <Subject 3>, the weathered wooden spear, opposite <Subject 2>, the towering black liquid-stone humanoid.",
    "EP00-S01-C02": "<Subject 1>, the young spear fighter with blue scales, is compressed low with <Subject 3>, the weathered wooden spear, beside the level right arm of <Subject 2>, the towering black liquid-stone humanoid.",
    "EP00-S02-C01": "<Subject 1>, the young spear fighter with blue scales, faces <Subject 2>, the towering black liquid-stone humanoid, with <Subject 3>, the weathered wooden spear, held low behind her.",
    "EP00-S02-C02": "<Subject 2>, the towering black liquid-stone humanoid, grips the middle of <Subject 3>, the weathered wooden spear, while <Subject 1>, the young spear fighter with blue scales, holds the rear grip.",
    "EP00-S03-C01": "<Subject 1>, the young spear fighter with blue scales, holds one curved water shield and <Subject 3>, the weathered wooden spear, before the approaching right palm of <Subject 2>, the towering black liquid-stone humanoid.",
    "EP00-S03-C02": "<Subject 1>, the young spear fighter with blue scales, carries <Subject 3>, the weathered wooden spear, inside the lane as the low left hand of <Subject 2>, the towering black liquid-stone humanoid, occupies her path.",
    "EP00-S04-C01": "<Subject 1>, the exhausted young spear fighter with blue scales, holds <Subject 3>, the weathered wooden spear, while reading both attached hands of <Subject 2>, the towering black liquid-stone humanoid, from above.",
    "EP00-S04-C02": "<Subject 1>, the young spear fighter with blue scales, enters with <Subject 3>, the weathered wooden spear, while the right hand of <Subject 2>, the towering black liquid-stone humanoid, begins to commit.",
    "EP00-S04-C03": "<Subject 1>, the young spear fighter with blue scales, carries <Subject 3>, the weathered wooden spear, inside the narrow gap between the separated hands of <Subject 2>, the towering black liquid-stone humanoid.",
    "EP00-S05-C01": "<Subject 1>, the young spear fighter with blue scales, controls shield residue beside one contact hand of <Subject 2>, the towering black liquid-stone humanoid, while holding <Subject 3>, the weathered wooden spear.",
    "EP00-S05-C02": "<Subject 2>, the towering black liquid-stone humanoid, begins one small shoulder rotation while <Subject 1>, the young spear fighter with blue scales, keeps hold of <Subject 3>, the weathered wooden spear.",
    "EP00-S05-C03": "<Subject 1>, the exhausted young spear fighter with blue scales, is exposed before the open palm of <Subject 2>, the towering black liquid-stone humanoid.",
    "EP00-S06-C01": "<Subject 1>, the defeated young spear fighter with blue scales, lies under the open hand of <Subject 2>, the towering black liquid-stone humanoid, with <Subject 3>, the weathered wooden spear, far out of reach.",
    "EP00-S06-C02": "<Subject 1>, the defeated young spear fighter with blue scales, lies nearly still before <Subject 2>, the towering black liquid-stone humanoid, with <Subject 3>, the weathered wooden spear, still distant.",
}


ACTIONS: dict[str, tuple[str, str, str, str]] = {
    "EP00-S01-C01": (
        "Three cyan channel sections extinguish while she measures the shrinking route.",
        "<Subject 2>, the towering black liquid-stone humanoid, closes the rear route with almost no body movement.",
        "<Subject 1>, the young spear fighter with blue scales, scans shoulder, elbow, and contact hand in one motion.",
        "<Subject 1>, the young spear fighter with blue scales, tightens her spear grip and loads one foot too late.",
    ),
    "EP00-S01-C02": (
        "<Subject 1>, the young spear fighter with blue scales, explodes upward over the committed arm.",
        "<Subject 1>, the young spear fighter with blue scales, clears the arm and drops toward the wet floor.",
        "<Subject 1>, the young spear fighter with blue scales, hits one knee and carries the impact into a roll.",
        "<Subject 1>, the young spear fighter with blue scales, rises without posing and aims the spear at the dark channel.",
    ),
    "EP00-S02-C01": (
        "<Subject 1>, the young spear fighter with blue scales, completes three hard steps toward the black torso.",
        "<Subject 1>, the young spear fighter with blue scales, drives hips, shoulders, and <Subject 3>, the weathered wooden spear, into one thrust.",
        "The spear point stops at the black surface as concentric ripples spread beyond it.",
        "<Subject 1>, the young spear fighter with blue scales, shifts her gaze from the unwounded torso to the hand touching the dark channel.",
    ),
    "EP00-S02-C02": (
        "<Subject 2>, the towering black liquid-stone humanoid, stops the spear with one short hand closure.",
        "<Subject 1>, the young spear fighter with blue scales, clamps the rear grip instead of releasing it.",
        "<Subject 2>, the towering black liquid-stone humanoid, lifts and throws fighter and spear on one force line.",
        "<Subject 1>, the young spear fighter with blue scales, hits shoulder-first, rolls once, and retargets from one knee.",
    ),
    "EP00-S03-C01": (
        "<Subject 1>, the young spear fighter with blue scales, finishes one irregular curved water shield.",
        "<Subject 1>, the young spear fighter with blue scales, turns the shield and slides the black palm sideways.",
        "Directional droplets leave the palm as the right cyan channel flashes once.",
        "<Subject 1>, the young spear fighter with blue scales, takes two steps through the open lane with the spear aligned.",
    ),
    "EP00-S03-C02": (
        "<Subject 2>, the towering black liquid-stone humanoid, sends the waiting left fingertip across the remaining gap.",
        "<Subject 1>, the young spear fighter with blue scales, leans away only a fraction before contact.",
        "The fingertip grazes her shoulder, tears the shield edge, and numbs her wrist.",
        "<Subject 1>, the young spear fighter with blue scales, lowers the spear and maps both black hands on one eyeline.",
    ),
    "EP00-S04-C01": (
        "<Subject 1>, the exhausted young spear fighter with blue scales, reduces the full chamber map to the two contact hands.",
        "Her eyes lock onto the two contact outlines without predicting their next motion.",
        "<Subject 1>, the exhausted young spear fighter with blue scales, takes one controlled inhale and forceful exhale.",
        "She redistributes weight through feet, scaled limbs, and the trembling spear grip.",
    ),
    "EP00-S04-C02": (
        "<Subject 1>, the young spear fighter with blue scales, feints right and cuts away as the right hand commits.",
        "She plants the spear butt hard into wet stone and compresses around it.",
        "<Subject 1>, the young spear fighter with blue scales, vaults to the opposite side as both black hands separate.",
        "One short nonverbal dragon utterance slows the hands and droplets for a single beat.",
    ),
    "EP00-S04-C03": (
        "<Subject 1>, the young spear fighter with blue scales, sprints deeper through the open gap.",
        "Two conflicting depth reads make her step land one pace late.",
        "Her foot misses the groove; ankle, breath, and scale light fail together.",
        "<Subject 1>, the young spear fighter with blue scales, drives spear and shield residue forward before balance returns.",
    ),
    "EP00-S05-C01": (
        "<Subject 1>, the young spear fighter with blue scales, snaps the remaining shield water sideways into the right hand.",
        "The compact water shove moves the black hand only a short distance.",
        "She jams the spear shaft into the opposite groove before the hand returns.",
        "The wedged shaft lifts a thin edge of the black lower mass while she remains under load.",
    ),
    "EP00-S05-C02": (
        "<Subject 2>, the towering black liquid-stone humanoid, exchanges both hand roles with one economical shoulder turn.",
        "Its right hand reaches the wedged spear while its left hand closes the retreat line.",
        "The right hand lifts the shaft free in one short motion.",
        "<Subject 1>, the young spear fighter with blue scales, feels the restored pressure too late through her numb fingers.",
    ),
    "EP00-S05-C03": (
        "The open black palm releases pressure across the remaining route.",
        "<Subject 1>, the young spear fighter with blue scales, slams flat into the wet floor and rebounds once.",
        "<Subject 3>, the weathered wooden spear, leaves her numb grip and skids intact across the altar.",
        "<Subject 1>, the defeated young spear fighter with blue scales, remains down as the cyan channels restore in sequence.",
    ),
    "EP00-S06-C01": (
        "<Subject 1>, the defeated young spear fighter with blue scales, tries one incomplete arm lift and drops it.",
        "Her wrist mark, channel response, and water shield remain inactive.",
        "She completes one compressed check of every known external response.",
        "<Subject 1>, the defeated young spear fighter with blue scales, turns her attention inward toward her chest.",
    ),
    "EP00-S06-C02": (
        "One unfamiliar internal heartbeat interrupts her exhausted breathing.",
        "<Subject 1>, the defeated young spear fighter with blue scales, stops breathing for one beat without producing light or aura.",
        "She raises her eyes back toward <Subject 2>, the towering black liquid-stone humanoid.",
        "Darkness closes from the frame edges to full black before a second heartbeat.",
    ),
}


SUMMARIES = {
    "EP00-S01-C01": "<Subject 1>, the young spear fighter with blue scales, reads the shrinking route but loads her first move too late.",
    "EP00-S01-C02": "<Subject 1>, the young spear fighter with blue scales, clears one arm, suffers a collapsed landing, and retargets from one knee.",
    "EP00-S02-C01": "<Subject 1>, the young spear fighter with blue scales, thrusts once, sees surface ripples instead of a wound, and checks the dark channel.",
    "EP00-S02-C02": "<Subject 2>, the towering black liquid-stone humanoid, catches the spear, throws the fighter, and leaves her retargeting from one knee.",
    "EP00-S03-C01": "<Subject 1>, the young spear fighter with blue scales, forms one shield, redirects one palm, and enters the opened lane.",
    "EP00-S03-C02": "<Subject 2>, the towering black liquid-stone humanoid, pre-empts the entry, tears the shield, and numbs the fighter's wrist.",
    "EP00-S04-C01": "<Subject 1>, the exhausted young spear fighter with blue scales, maps both hands, resets one breath, and reloads her stance.",
    "EP00-S04-C02": "<Subject 1>, the young spear fighter with blue scales, feints, plants the spear, vaults, and delays both hands for one beat.",
    "EP00-S04-C03": "<Subject 1>, the young spear fighter with blue scales, enters the gap, misreads depth, loses footing, and commits her remaining force.",
    "EP00-S05-C01": "<Subject 1>, the young spear fighter with blue scales, shoves one hand, wedges the spear, and lifts a thin black edge.",
    "EP00-S05-C02": "<Subject 2>, the towering black liquid-stone humanoid, exchanges hand roles, frees the spear, closes retreat, and restores pressure.",
    "EP00-S05-C03": "<Subject 2>, the towering black liquid-stone humanoid, releases pressure that floors the fighter and sends her spear out of reach.",
    "EP00-S06-C01": "<Subject 1>, the defeated young spear fighter with blue scales, fails every known external response and turns her attention inward.",
    "EP00-S06-C02": "<Subject 1>, the defeated young spear fighter with blue scales, senses one unfamiliar heartbeat before the frame becomes black.",
}


def shot_starts(duration: float, variant: str) -> tuple[float, float, float]:
    ratios = {
        "A": (0.25, 0.50, 0.75),
        "D": (0.20, 0.46, 0.72),
        "E": (0.16, 0.40, 0.68),
    }[variant]
    return tuple(round(duration * ratio, 3) for ratio in ratios)


def clean_storyboard_beat(value: str) -> str:
    """Keep structured review metadata readable without proprietary name tokens."""
    return (
        value.replace("<Subject 1> Lua's", "the young spear fighter's")
        .replace("<Subject 2> AbyssKing's", "the black humanoid's")
        .replace("<Subject 3> LuaSpear", "<Subject 3>, the weathered wooden spear,")
        .replace("<Subject 1> Lua", "<Subject 1>, the young spear fighter with blue scales,")
        .replace("<Subject 2> AbyssKing", "<Subject 2>, the towering black liquid-stone humanoid,")
    )


def build_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    base_spec, base_contracts = source.build_payloads()
    spec = copy.deepcopy(base_spec)
    events = copy.deepcopy(base_contracts)
    clips = [row for row in spec["clips"] if str(row["clip_id"]).startswith("EP00-")]
    contracts = {
        key: value for key, value in events["clips"].items() if key.startswith("EP00-")
    }
    if set(ACTIONS) != {str(row["clip_id"]) for row in clips}:
        raise ValueError("Concise 2D actions must cover the approved 14 EP00 clips exactly.")

    catalog = spec["asset_catalog"]
    catalog["lua-complete"].update({
        "subject_name": "the young spear fighter with blue scales",
        "subject_description": (
            "One athletic young woman with warm tan skin, blue-grey eyes, asymmetric ink-navy short hair, unchanged sleeveless fishing clothes, and real overlapping blue scales only on the full right arm and right leg from ankle through exposed thigh."
        ),
        "retention_description": "Preserve one fighter with the same face, clothing, scale boundaries, fatigue, and injury",
    })
    catalog["abyss-king"].update({
        "subject_name": "the towering black liquid-stone humanoid",
        "subject_description": (
            "One connected black liquid-stone humanoid about three times the fighter's height, with restrained cyan channels, a crown-like head, exactly two continuous arms, and exactly two hands."
        ),
        "retention_description": "Preserve one connected three-times-taller black humanoid with the same cyan channels and exactly two hands",
    })
    catalog["spear"].update({
        "subject_name": "the weathered wooden spear",
        "subject_description": (
            "One fixed-length weathered wooden spear with one dark metal head, one downward barb, bindings, grip wear, scratches, and one rear ring."
        ),
        "retention_description": "Preserve one intact fixed-length spear with the same geometry and shown ownership",
    })

    for sequence, clip in enumerate(clips, start=1):
        clip_id = str(clip["clip_id"])
        contract = contracts[clip_id]
        duration = float(clip["duration_seconds"])
        board_key = "storyboard-" + clip_id.lower()
        board = spec["asset_catalog"][board_key]
        board.update({
            "storyboard_mode": MODE,
            "standalone_picture_name": "the four ordered 2D animation starting images",
            "standalone_picture_description": (
                "Read the 2x2 planning sheet once in this order: top-left, top-right, "
                "bottom-left, bottom-right. These are the full-screen starting images "
                "for Shots 1, 2, 3, and 4. Never render the combined sheet, borders, or labels."
            ),
            "retention_marker": "fully_preserved",
            "retention_description": (
                "Use the four approved 2D starting images in order without reproducing the combined sheet"
            ),
        })
        board["storyboard_beats"] = [
            clean_storyboard_beat(str(value))
            for value in board.get("storyboard_beats") or []
        ]
        contract["beats"] = [
            {**row, "description": clean_storyboard_beat(str(row["description"]))}
            for row in contract["beats"]
        ]
        contract.update({
            "storyboard_mode": MODE,
            "incoming_bridge": "",
            "outgoing_bridge": "",
        })
        for variant in ("A", "D", "E"):
            starts = shot_starts(duration, variant)
            contract["candidate_plans"][variant] = {
                "emphasis": {
                    "A": "balanced timing for the same four 2D actions",
                    "D": "faster opening timing for the same four 2D actions",
                    "E": "compressed middle timing for the same four 2D actions",
                }[variant],
                "shots": [
                    {
                        "camera": (
                            f"{START_STATES[clip_id]} {action}"
                            if index == 1 else action
                        ),
                        "panel_index": index,
                        "panel_position": POSITIONS[index - 1],
                        "beat_ids": [f"P{index}"],
                        **({} if index == 1 else {"start_seconds": starts[index - 2]}),
                    }
                    for index, action in enumerate(ACTIONS[clip_id], start=1)
                ],
            }

        for variant in clip["prompt_variants"]:
            variant_id = str(variant["variant_id"])
            variant["label"] = f"후보 {variant_id} · 동일 행동/시간 변형"
            variant["rationale"] = {
                "A": "동일한 네 행동을 균형 시간으로 배치",
                "D": "동일한 네 행동의 초반 간격을 단축",
                "E": "동일한 네 행동의 중간 변화를 압축",
            }[variant_id]
        clip.update({
            "sequence": sequence,
            "status": "pending_user_prompt_review",
            "semantic_review": "pending_user_2d_temporal_prompt_review",
            "prompt_base": {
                "summary": SUMMARIES[clip_id],
                "style_opening": [
                    "High-detail hand-drawn 2D cel animation; each Shot uses one full-screen storyboard image and only the short action written after it; never render a reference-sheet background"
                ],
                "overall_soundscape": "Only sounds directly caused by the four written Shot actions.",
                "non_diegetic_music": "None.",
            },
            "storyboard_review_contract": {
                "picture_id": int(contract["storyboard_picture_id"]),
                "storyboard_mode": MODE,
                "storyboard_shots": [1, 2, 3, 4],
                "model_delegated_shots": [],
                "panel_to_shot": "top-left_to_1_top-right_to_2_bottom-left_to_3_bottom-right_to_4",
                "timing_source": "variant_specific_shot_start_ratios",
            },
            "authoring_notes": (
                "Approved rebuild_v2 2D storyboard only. Four images become four Shots. "
                "A/D/E action wording is identical; only Shot start times differ. No queue or video generation."
            ),
        })
        clip["action_scene_contract"]["storyboard_mode"] = MODE
        clip["action_scene_contract"]["storyboard_picture_id"] = int(
            contract["storyboard_picture_id"]
        )

    spec.update({
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · 2D Temporal Storyboard A/D/E V4",
        "description": "Approved rebuild_v2 2D boards become four concise timed Shots with no delegated entry or exit Shot.",
        "source_policy": "rebuild_v2_approved_2d_storyboards_only",
        "build_script": "scripts/build_ep00_2d_temporal_storyboard_ade_v4.py",
        "event_contracts_file": CONTRACTS_PATH.name,
        "clips": clips,
        "generation_blocked": False,
        "replacement_project_ids": [],
        "review_decision": "pending_user_2d_temporal_prompt_review_no_queue_no_video",
    })
    events["project_id"] = PROJECT_ID
    events["clips"] = contracts
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
