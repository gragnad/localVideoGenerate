from __future__ import annotations

"""Build three EP00 single-clip action-keyshot tests.

The project is intentionally separate from the current 14-clip EP00 action
project. Each clip separates delegated entry, one storyboard-only fast-action
Shot, and a delegated outgoing continuity event. The 2x2 sheet controls only
the four instantaneous action key views inside Shot 2.
"""

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_project_builder  # noqa: E402
import h3_prompt_projects  # noqa: E402


SOURCE_DIR = (
    ROOT
    / "projects"
    / "RaisingaDragonSeason01"
    / "rebuild_v2"
    / "action_moment_test_v1"
)
SPEC_PATH = SOURCE_DIR / "EP00_H3_R2V_ACTION_MOMENT_TEST_V1_SPEC.json"
PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_ACTION_MOMENT_TEST_V1"
STORYBOARD_MODE = h3_prompt_projects.FOUR_SHOT_ACTION_STORYBOARD_MODE


IDENTITY_ASSETS: dict[str, dict[str, Any]] = {
    "heartstone-chamber": {
        "role": "heartstone_chamber_environment",
        "label": "Heartstone Chamber environment plate",
        "copy_from": "images/HEARTSTONE_CHAMBER_ENVIRONMENT_V1.png",
        "subject_id": 1,
        "subject_name": "the submerged circular stone arena",
        "subject_description": (
            "One vast circular submerged stone arena with "
            "a wet concentric floor, shallow water, carved radial channels carrying restrained "
            "cyan light, a raised central dais, dark monumental arches, and one stable action "
            "axis. Preserve topology, scale, contact plane, channel routes, light direction, "
            "and full-screen 16:9 depth; never reproduce a reference-sheet background."
        ),
        "retention_description": (
            "Preserve the circular chamber topology, wet floor, radial channels, central dais, "
            "scale, light direction, and action axis"
        ),
    },
    "lua-complete": {
        "role": "lua_complete_identity",
        "label": "Blue-scaled young spear fighter identity sheet",
        "copy_from": "../designs_hq_v1/h3_identity_sheets/H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2.png",
        "subject_id": 2,
        "subject_name": "the blue-scaled young spear fighter",
        "subject_description": (
            "One blue-scaled athletic young spear fighter with warm tan "
            "skin, blue-grey eyes, asymmetric ink-navy short hair with a sea-teal underlayer, "
            "unchanged sleeveless navy fishing clothes and red-brown sash, with real overlapping "
            "blue dragon plates covering the entire right arm and only the right leg from ankle "
            "through exposed thigh. Preserve one person, exact face, clothing, scale limits, "
            "fatigue, injury, and gaze toward the actual threat; never reproduce the source sheet."
        ),
        "retention_description": (
            "Preserve one young fighter with exact identity, fishing clothes, right-arm and right-leg scale "
            "boundaries, fatigue, and current injury"
        ),
    },
    "abyss-king": {
        "role": "abyss_king_identity",
        "label": "Towering black liquid-stone humanoid identity sheet",
        "copy_from": "../designs_hq_v1/h3_identity_sheets/H3_ABYSS_KING_IDENTITY_HQ_V2.png",
        "subject_id": 3,
        "subject_name": "the towering black liquid-stone humanoid",
        "subject_description": (
            "One towering humanoid abyss entity approximately three times the young fighter's "
            "height, with a stable black liquid-stone body, restrained cyan channel lines, a "
            "crown-like head silhouette, exactly two continuous arms and hands, and minimal "
            "movement. Preserve the three-to-one scale relation; never invent armour, weapons, "
            "a human face, extra limbs, or a reference-sheet background."
        ),
        "retention_description": (
            "Preserve one towering black humanoid with exactly two hands, stable body, crown "
            "silhouette, cyan lines, and three-to-one scale relation to the young fighter"
        ),
    },
    "spear": {
        "role": "lua_spear_prop",
        "label": "Weathered wooden spear identity sheet",
        "copy_from": "../designs_hq_v1/h3_prop_sheets/H3_LUA_SPEAR_PROP_HQ_V3.png",
        "subject_id": 4,
        "subject_name": "the weathered wooden spear",
        "subject_description": (
            "One fixed-length weathered wooden spear with the approved dark metal head, "
            "downward barb, bindings, grip, scratches, and rear ring. Preserve one rigid weapon, "
            "its scale, orientation, and ownership until the described action changes possession; "
            "never duplicate, reverse, resize, bend like rubber, or reproduce the source sheet."
        ),
        "retention_marker": "partially_preserved",
        "retention_description": (
            "Preserve one spear with exact geometry, material, scale, orientation, grip, and the "
            "described ownership or separation state"
        ),
    },
}


CLIPS: list[dict[str, Any]] = [
    {
        "clip_id": "EP00-TM01",
        "title_ko": "몸통 찌르기와 붙잡힌 창",
        "summary": (
            "<Subject 4>, the wooden spear, is already pressed into <Subject 3>, the towering "
            "black humanoid; its torso compresses, ripples, restores its shape, and forces the "
            "spear backward before <Subject 2>, the blue-scaled spear fighter, finishes the recoil."
        ),
        "scenario_ko": (
            "루아가 세 걸음으로 접근해 창을 찌른다. 검은 가슴은 함몰과 파동만 남기고 "
            "상처 없이 복원된다. 밀려나는 창 자루 중간을 심해왕의 왼손이 붙잡는다."
        ),
        "board_file": "EP00_TM01_SPEAR_IMPACT_ACTION_BOARD_V1.png",
        "storyboard_picture_name": "the fast spear-thrust action storyboard",
        "storyboard_action": (
            "The blue-scaled spear fighter <Subject 2> makes one fast spear thrust into the "
            "towering black humanoid <Subject 3> and recoils"
        ),
        "viewpoints": [
            "dynamic low side medium view that reads the blue-scaled fighter's full committed thrust",
            "tight impact insert where the spear point is visibly buried into and depressing the black torso surface",
            "reverse three-quarter medium view that reads the rebound through the fighter's body",
            "tight full-body reaction view that reads the fighter completing the recoil follow-through",
        ],
        "setup": (
            "The blue-scaled spear fighter <Subject 2> closes the three steps toward the towering "
            "black humanoid <Subject 3> with the wooden spear <Subject 4> held low."
        ),
        "beats": [
            "The blue-scaled spear fighter <Subject 2> drives the wooden spear <Subject 4> forward with rear foot, hip, shoulder, and both hands aligned in one sharp kinetic chain.",
            "The metal spearhead visibly sinks into a deep elastic crater in the towering black humanoid <Subject 3> without piercing through or making a wound; the surface wraps around the stopped head and concentric waves race outward.",
            "The black surface restores its original shape and pushes the wooden spear <Subject 4> back with no wound while the cyan channel beneath the towering black humanoid <Subject 3> remains dark; the blue-scaled fighter <Subject 2> absorbs the recoil.",
            "The blue-scaled fighter <Subject 2> completes the immediate recoil follow-through with the same wooden spear <Subject 4> still in both hands, rear foot skidding once as the rigid shaft clears the restored torso; the towering black humanoid <Subject 3> has not yet reached for it.",
        ],
        "shot_actions": [
            "<Subject 3>, the towering black liquid-stone humanoid, has <Subject 4>, the wooden spear, pressed into its torso. The torso compresses further around the spearhead.",
            "<Subject 3>, the towering black humanoid, restores its rippling torso and forces <Subject 4>, the wooden spear, backward.",
            "Across <Subject 1>, the submerged arena, recoil travels through <Subject 2>, the blue-scaled spear fighter, while she keeps <Subject 4>, the wooden spear, in both hands.",
            "<Subject 2>, the blue-scaled spear fighter, finishes the recoil and settles with <Subject 4>, the wooden spear, in both hands.",
        ],
        "outgoing_event": (
            "After Shot 2, the towering black humanoid <Subject 3> closes its left hand around "
            "the middle of the recoiling wooden spear <Subject 4>."
        ),
        "incoming_bridge": (
            "A full-screen view of the submerged stone arena <Subject 1> shows the blue-scaled "
            "spear fighter <Subject 2> three steps from the towering black humanoid <Subject 3> "
            "with the wooden spear <Subject 4> held low."
        ),
        "outgoing_bridge": (
            "In the submerged stone arena <Subject 1>, the towering black humanoid <Subject 3> "
            "catches the middle of the wooden spear <Subject 4> while the blue-scaled spear "
            "fighter <Subject 2> keeps the rear grip."
        ),
        "environmental_proof": (
            "Concentric waves travel across the black torso while the channel below remains dark."
        ),
        "soundscape": (
            "A low compression thud around the embedded spearhead, black-surface ripples, an "
            "elastic restoration pulse, recoil through wood, and one settling foot scrape."
        ),
        "music": (
            "A compact low-string pulse rises with the compression and cuts off after the recoil."
        ),
    },
    {
        "clip_id": "EP00-TM02",
        "title_ko": "손끝 스침과 닫히는 길",
        "summary": (
            "<Subject 3>, the towering black humanoid, already touches <Subject 2>, the blue-scaled "
            "fighter, at the shoulder; its fingertips continue across her, her shield and clothing "
            "tear, she completes a half-turn, and only two fingers remain locked around "
            "<Subject 4>, the wooden spear."
        ),
        "scenario_ko": (
            "루아가 열린 수로로 달리지만 심해왕의 왼손가락 끝이 어깨를 스친다. 몸이 "
            "반 바퀴 돌아가고 방패와 손목이 손상된다. 오른손은 다시 수로를 누르러 간다."
        ),
        "board_file": "EP00_TM02_GRAZE_ACTION_BOARD_V1.png",
        "storyboard_picture_name": "the fast fingertip-graze action storyboard",
        "storyboard_action": (
            "The towering black humanoid <Subject 3> grazes the blue-scaled spear fighter "
            "<Subject 2> once; she turns and loses feeling in her wooden spear <Subject 4> grip"
        ),
        "viewpoints": [
            "shoulder-level close medium view that reads the fingertips at the instant of grazing contact",
            "directional profile insert that reads the cloth and water-shield edge tearing along the force line",
            "fast profile reaction view that reads the fighter's forced half-turn",
            "tight hand-and-wrist insert that reads the numb wrist and two locked fingers on the spear",
        ],
        "setup": (
            "The blue-scaled spear fighter <Subject 2> runs toward the open route with the wooden "
            "spear <Subject 4> and twists away from the towering black humanoid <Subject 3>."
        ),
        "beats": [
            "The fingertips of the towering black humanoid <Subject 3> make one shallow grazing contact across the blue-scaled fighter <Subject 2>, not a direct blow or deep wound.",
            "The grazing force rotates the blue-scaled fighter <Subject 2> half a turn and tears the edge of her existing water shield and clothing along the same force direction.",
            "The blue-scaled fighter <Subject 2> completes the forced half-turn and staggers one immediate step along the same force direction as torn water and cloth trail from the struck shoulder.",
            "Sensation cuts out through the blue-scaled fighter <Subject 2>'s right wrist and exactly two fingers remain locked around the wooden spear <Subject 4> while the other fingers fail to close; stop at this direct action result before the towering black humanoid <Subject 3> begins another move.",
        ],
        "shot_actions": [
            "<Subject 3>, the towering black humanoid, has its fingertips touching <Subject 2>, the blue-scaled fighter, at the shoulder. The fingertips continue across the shoulder.",
            "<Subject 2>, the blue-scaled fighter, loses the edge of her water shield and clothing as the tear travels through them.",
            "In <Subject 1>, the submerged arena, <Subject 2>, the blue-scaled fighter, completes the half-turn and staggers one step.",
            "<Subject 2>, the blue-scaled fighter, cannot close her other fingers while two remain locked around <Subject 4>, the wooden spear.",
        ],
        "outgoing_event": (
            "After Shot 2, the blue-scaled fighter <Subject 2>'s shield fails to reform as the "
            "towering black humanoid <Subject 3>'s "
            "right hand returns toward the open cyan route."
        ),
        "incoming_bridge": (
            "A full-screen view of the submerged stone arena <Subject 1> shows the blue-scaled "
            "spear fighter <Subject 2> holding the wooden spear <Subject 4> before an open route "
            "as the towering black humanoid <Subject 3> blocks the side lane."
        ),
        "outgoing_bridge": (
            "In the submerged stone arena <Subject 1>, the blue-scaled spear fighter <Subject 2> "
            "holds the wooden spear <Subject 4> while the towering black humanoid <Subject 3> "
            "returns its right hand toward the open route."
        ),
        "environmental_proof": (
            "The shield edge tears in the force direction, large droplets fall, and the open cyan "
            "route is visibly about to be covered again."
        ),
        "soundscape": (
            "A continuous cloth graze, a tearing water sheet, a short turning rush, one staggered "
            "footstep, a wrist nerve crackle, and a wooden grip creak."
        ),
        "music": (
            "A narrow string tone holds through the continuing graze, breaks with the tear, and "
            "leaves one low note under the numb hand."
        ),
    },
    {
        "clip_id": "EP00-TM03",
        "title_ko": "손바닥 내리찍기와 무장 해제",
        "summary": (
            "<Subject 3>, the towering black humanoid, already has its palm against <Subject 2>, "
            "the falling blue-scaled fighter; the palm continues downward, her scales flash white, "
            "she hits the wet floor and rebounds once, and <Subject 4>, the wooden spear, leaves her hand."
        ),
        "scenario_ko": (
            "심해왕이 창을 축으로 루아를 넘긴 뒤 손을 놓고 같은 오른손을 편다. 낙하하는 "
            "루아를 손바닥으로 내리찍어 바닥에 충돌시키고 창을 멀리 이탈시킨다."
        ),
        "board_file": "EP00_TM03_PALM_SLAM_ACTION_BOARD_V1.png",
        "storyboard_picture_name": "the fast downward-palm action storyboard",
        "storyboard_action": (
            "The towering black humanoid <Subject 3> drives the falling blue-scaled spear fighter "
            "<Subject 2> into the floor with one right-palm strike, ending at the immediate bounce"
        ),
        "viewpoints": [
            "low diagonal medium view that reads the open palm covering the fighter and driving downward",
            "tight attached-contact insert on the palm, scaled arm, and white-cyan flash",
            "high three-quarter impact view that reads the lowered floor ring and circular water burst",
            "tight floor-level follow-through that reads one body bounce and the spear just breaking free",
        ],
        "setup": (
            "The towering black humanoid <Subject 3> rotates the wooden spear <Subject 4> and "
            "carries the blue-scaled spear fighter <Subject 2> over its axis."
        ),
        "beats": [
            "The open right palm of the towering black humanoid <Subject 3> covers the falling blue-scaled fighter <Subject 2> across her side and scaled right arm in one attached-hand contact.",
            "The blue-scaled fighter <Subject 2>'s right-side scales flash white at contact as the force transfers sharply downward with no pause or suspended pose.",
            "The blue-scaled fighter <Subject 2> strikes the wet stone floor of the submerged arena <Subject 1>; the outer ring drops slightly and shallow water bursts outward in one circular wave.",
            "The blue-scaled fighter <Subject 2> completes one short impact bounce as the wooden spear <Subject 4> breaks free from her locked fingers and only begins its floorward motion; stop before the weapon travels away or the cyan routes change.",
        ],
        "shot_actions": [
            "<Subject 3>, the towering black humanoid, has its palm against <Subject 2>, the falling blue-scaled fighter. The palm continues downward.",
            "<Subject 2>, the blue-scaled fighter, flashes white across her blue scales as the palm drives her downward.",
            "<Subject 2>, the blue-scaled fighter, hits <Subject 1>, the submerged arena floor; the water ring expands and her body rebounds.",
            "<Subject 2>, the blue-scaled fighter, lands after one bounce as <Subject 4>, the wooden spear, fully leaves her hand.",
        ],
        "outgoing_event": (
            "After Shot 2, the wooden spear <Subject 4> hits a channel lip and slides to the far "
            "side of the submerged arena <Subject 1> while the cyan routes dim."
        ),
        "incoming_bridge": (
            "A full-screen view of the submerged stone arena <Subject 1> shows the towering black "
            "humanoid <Subject 3> holding the wooden spear <Subject 4> with the blue-scaled spear "
            "fighter <Subject 2> caught on its axis."
        ),
        "outgoing_bridge": (
            "Across the submerged stone arena <Subject 1>, the wooden spear <Subject 4> slides "
            "beyond the blue-scaled spear fighter <Subject 2> while the towering black humanoid "
            "<Subject 3> remains upright."
        ),
        "environmental_proof": (
            "The floor ring settles lower, one circular water burst travels outward, and the cyan "
            "routes extinguish toward the fallen blue-scaled fighter."
        ),
        "soundscape": (
            "A heavy downward palm-pressure rush, a white-scale crack, a stone impact, an outward "
            "water burst, one body bounce, and the wooden spear slipping free."
        ),
        "music": (
            "A sub-bass swell follows the downward pressure, lands with the floor strike, and "
            "decays under the body bounce."
        ),
    },
]


def board_asset(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "single_clip_action_keyshot_storyboard",
        "label": f"{row['title_ko']} ordered action keyshot board",
        "copy_from": f"images/{row['board_file']}",
        "reference_kind": "storyboard",
        "storyboard_mode": STORYBOARD_MODE,
        "storyboard_panel_count": 4,
        "storyboard_reading_order": "top-left, top-right, bottom-left, bottom-right",
        "storyboard_beats": [
            f"Key view {index} — {viewpoint}: {beat}"
            for index, (viewpoint, beat) in enumerate(
                zip(row["viewpoints"], row["beats"]), start=1
            )
        ],
        "standalone_picture_name": row["storyboard_picture_name"],
        "standalone_picture_description": (
            "Its top-left, top-right, bottom-left, and bottom-right action images become "
            "full-screen Shots 1, 2, 3, and 4 respectively; never render the planning layout."
        ),
        "retention_shots": [1, 2, 3, 4],
        "retention_marker": "partially_preserved",
        "retention_description": (
            "Use the four instantaneous action key views in depicted viewpoint and shot order "
            "without reproducing the planning sheet"
        ),
    }


def event_contract(row: dict[str, Any]) -> dict[str, Any]:
    action_beats = [
        {"beat_id": f"C{index}", "description": description}
        for index, description in enumerate(row["beats"], start=1)
    ]
    timings = {
        "A": (None, 1.5, 3.0, 4.5),
        "D": (None, 1.1, 2.3, 3.7),
        "E": (None, 0.8, 1.9, 3.1),
    }
    return {
        "shared_event": row["summary"],
        "bridge_in_id": f"{row['clip_id']}_IN",
        "bridge_out_id": f"{row['clip_id']}_OUT",
        "boundary_policy": "referenced_cut",
        "source_shot_ids": [row["clip_id"]],
        "incoming_reference_subjects": [1, 2, 3, 4],
        "outgoing_reference_subjects": [1, 2, 3, 4],
        "incoming_bridge": "",
        "outgoing_bridge": "",
        "storyboard_required": True,
        "storyboard_picture_id": 5,
        "storyboard_panel_count": 4,
        "storyboard_reading_order": "top-left, top-right, bottom-left, bottom-right",
        "storyboard_mode": STORYBOARD_MODE,
        "beats": action_beats,
        "candidate_plans": {
            variant_id: {
                "emphasis": {
                    "A": "evenly timed four-panel action progression",
                    "D": "faster opening four-panel action progression",
                    "E": "compressed impact-first four-panel action progression",
                }[variant_id],
                "shots": [
                    {
                        "camera": action,
                        "panel_index": index,
                        "panel_position": ("top-left", "top-right", "bottom-left", "bottom-right")[index - 1],
                        "beat_ids": [f"C{index}"],
                        **({} if start is None else {"start_seconds": start}),
                    }
                    for index, (action, start) in enumerate(
                        zip(row["shot_actions"], timings[variant_id], strict=True), start=1
                    )
                ],
            }
            for variant_id in ("A", "D", "E")
        },
    }


def clip_spec(row: dict[str, Any], sequence: int) -> dict[str, Any]:
    board_key = f"board-{row['clip_id'].lower()}"
    return {
        "scene_id": "EP00-ACTION-MOMENT-TEST",
        "clip_id": row["clip_id"],
        "sequence": sequence,
        "source_shot_id": row["clip_id"],
        "duration_seconds": 6.0,
        "status": "action_moment_test_ready",
        "references": [
            "heartstone-chamber",
            "lua-complete",
            "abyss-king",
            "spear",
            board_key,
        ],
        "prompt_base": {
            "summary": row["summary"],
            "style_opening": [
                "Original high-detail 2D cel action with grounded anatomy, readable silhouettes, and clear physical response.",
                "Use the four storyboard action images as four consecutive full-screen Shots; never render a planning layout, split screen, text, duplicate characters, or a reference-sheet background.",
            ],
            "overall_soundscape": row["soundscape"],
            "non_diegetic_music": row["music"],
        },
        "event_contract": event_contract(row),
        "prompt_variants": [{
            "variant_id": variant_id,
            "label": f"후보 {variant_id}",
            "rationale": {
                "A": "안정적인 모델 위임 진입·종료 사이에서 동일한 액션 보드를 검증",
                "D": "트래킹 진입·짧은 종료 팔로우 사이에서 동일한 액션 보드를 검증",
                "E": "역동적 모델 위임 재구도 사이에서 동일한 액션 보드를 검증",
            }[variant_id],
            "prompt_spec": {},
        } for variant_id in ("A", "D", "E")],
        "canonical_source_lineage": [
            "EP00_READER_SCREENPLAY_ACTION_REVISION_V2.md (user attachment)",
            "action_moment_test_v1/EP00_ACTION_MOMENT_TEST_PLAN_V1.md",
            "H3_R2V_SCENARIO_AUTHORING_GUIDE.md",
            "JJK_MANGA_TO_ANIME_R2V_DIRECTION_RESEARCH_V1.md",
        ],
        "locked_rule_id": "EP00_ACTION_MOMENT_TEST_PLAN_V1",
        "continuity_in": f"{row['clip_id']}_IN",
        "continuity_out": f"{row['clip_id']}_OUT",
        "scenario_ko": row["scenario_ko"],
        "required_dialogue": [],
        "action_requirements": {
            "checkpoint_count": 4,
            "storyboard_scope": "all_four_timed_action_shots",
        },
        "review_intent_ko": (
            "스토리보드 네 화면을 시간값이 있는 네 개의 전체 화면 액션 Shot으로 직접 "
            "연결하고 각 Shot에는 짧은 행동만 쓰는 실험"
        ),
        "storyboard_review_contract": {
            "picture_id": 5,
            "storyboard_mode": STORYBOARD_MODE,
            "storyboard_shots": [1, 2, 3, 4],
            "model_delegated_shots": [],
            "panel_to_shot": "top-left_to_1_top-right_to_2_bottom-left_to_3_bottom-right_to_4",
            "visual_asset_status": "generated_for_test_pending_user_video_review",
        },
        "scene_type": h3_prompt_projects.ACTION_SCENE_TYPE,
        "prompt_profile": h3_prompt_projects.ACTION_PROMPT_PROFILE,
        "prompt_generator": h3_prompt_projects.ACTION_PROMPT_GENERATOR,
        "action_scene_contract": {
            "version": h3_prompt_projects.ACTION_SCENE_CONTRACT_VERSION,
            "storyboard_mode": STORYBOARD_MODE,
            "phase": row["clip_id"].lower(),
            "speed_profiles": list(row["beats"]),
            "motion_links": [
                "decisive action flows directly into contact with no pose reset",
                "contact force continues into the physical effect and receiver reaction",
                "the receiver reaction ends on only the immediate physical follow-through",
            ],
            "environmental_proof": row["environmental_proof"],
        },
        "authoring_notes": (
            "This experimental clip maps the four storyboard images directly to four timed action "
            "Shots. A/D/E keep the actions invariant and vary only their start times. No queue or "
            "video generation is performed."
        ),
        "visual_review": "generated_test_assets_connected_pending_user_video_review",
        "semantic_review": "internal_prompt_audit_passed",
    }


def build_spec() -> dict[str, Any]:
    catalog = dict(IDENTITY_ASSETS)
    for row in CLIPS:
        catalog[f"board-{row['clip_id'].lower()}"] = board_asset(row)
    return {
        "schema_version": 2,
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · Instant Action Keyshot Test V1",
        "description": (
            "Three independent six-second tests. Each storyboard's four ordered action images map "
            "directly to four timed, full-screen action Shots with concise action text."
        ),
        "source_policy": "user_ep00_reader_screenplay_v2_single_clip_action_keyshot_test_only",
        "build_script": "scripts/build_ep00_action_moment_test_v1.py",
        "prompt_profile": h3_prompt_projects.ACTION_PROMPT_PROFILE,
        "prompt_generator": h3_prompt_projects.ACTION_PROMPT_GENERATOR,
        "generation_blocked": False,
        "replacement_project_ids": [],
        "review_decision": "test_project_ready_no_queue_no_video",
        "canonical_source_lineage": [
            "EP00_READER_SCREENPLAY_ACTION_REVISION_V2.md (user attachment)",
            "action_moment_test_v1/EP00_ACTION_MOMENT_TEST_PLAN_V1.md",
        ],
        "locked_rule_id": "EP00_ACTION_MOMENT_TEST_PLAN_V1",
        "asset_catalog": catalog,
        "clips": [clip_spec(row, index) for index, row in enumerate(CLIPS, start=1)],
    }


def main() -> int:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    spec = build_spec()
    SPEC_PATH.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = h3_prompt_project_builder.build_project(ROOT, SPEC_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
