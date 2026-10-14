from __future__ import annotations

"""MiniMax H3 reference-to-video benchmark suites.

These cases are intentionally separate from the model-neutral and fixed-anchor
I2V suites.  Picture ordering is part of each immutable case contract.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import h3_prompt_projects
import model_test_assets

ACTION_SUITE_ID = "minimax_h3_r2v_action_stress_v1"
ACTION_V2_SUITE_ID = "minimax_h3_r2v_action_stress_v2"
TURN_SUITE_ID = "minimax_h3_r2v_turn_taking_v1"
DRAGON_SEASON_1_SUITE_ID = "raising_a_dragon_season01_h3_r2v_v1"
DRAGON_SEASON_1_PROJECT_ID = "RaisingaDragonSeason01_H3_OFFICIAL"
PROJECT_SUITE_PREFIX = "h3_project_r2v_"
SCENE_SUITE_PREFIX = "h3_scene_r2v_"
R2V_SUITE_IDS = frozenset({ACTION_SUITE_ID, ACTION_V2_SUITE_ID, TURN_SUITE_ID, DRAGON_SEASON_1_SUITE_ID})
R2V_WORKFLOW_FILENAME = "(basic)video_minimax_h3_r2v_api.json"
R2V_PINT8_WORKFLOW_FILENAME = "(basic)video_minimax_h3_r2v_pint8_api.json"
R2V_UPDATE_ATTN_WORKFLOW_FILENAME = (
    "(basic)video_minimax_h3_r2v_updateAttn_api.json"
)
R2V_INT8_TURBO_WORKFLOW_FILENAME = (
    "(basic)video_minimax_h3_r2v_int8_turbo_api.json"
)
R2V_DEFAULT_WORKFLOW_FILENAME = R2V_INT8_TURBO_WORKFLOW_FILENAME
R2V_WORKFLOW_FILENAMES = frozenset({
    R2V_WORKFLOW_FILENAME,
    R2V_PINT8_WORKFLOW_FILENAME,
    R2V_UPDATE_ATTN_WORKFLOW_FILENAME,
    R2V_INT8_TURBO_WORKFLOW_FILENAME,
})
R2V_TEST_RESOLUTIONS = frozenset({
    (608, 352), (736, 416), (832, 480), (1280, 736),
})


def project_suite_id(project_id: str) -> str:
    """Return a stable R2V suite ID without changing the legacy Official suite."""
    project_id = str(project_id or "").strip()
    if project_id == DRAGON_SEASON_1_PROJECT_ID:
        return DRAGON_SEASON_1_SUITE_ID
    digest = hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:20]
    return f"{PROJECT_SUITE_PREFIX}{digest}"


def project_scene_suite_id(project_id: str, scene_id: str) -> str:
    """Return a stable suite ID for one selected scene in an H3 project."""
    identity = f"{str(project_id or '').strip()}\0{str(scene_id or '').strip()}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return f"{SCENE_SUITE_PREFIX}{digest}"


def is_r2v_suite_id(suite_id: str) -> bool:
    suite_id = str(suite_id or "")
    return (
        suite_id in R2V_SUITE_IDS
        or suite_id.startswith(PROJECT_SUITE_PREFIX)
        or suite_id.startswith(SCENE_SUITE_PREFIX)
    )


def is_r2v_workflow_filename(filename: str) -> bool:
    return str(filename or "") in R2V_WORKFLOW_FILENAMES


def _ref(label_ko: str, instruction_en: str) -> dict[str, str]:
    return {"label_ko": label_ko, "instruction_en": instruction_en}


CASES: list[dict[str, Any]] = [
    {
        "short_id": "rs01", "title": "R-S01 · 초고속 돌진", "category": "r2v_high_speed_action", "tier": "stress", "duration": 6,
        "intent_ko": "캐릭터가 전력 질주하며 적의 공격을 피하고 화면을 빠르게 가로지른다.",
        "scene_en": "The protagonist sprints at full speed across the action space, narrowly evades one clearly visible enemy attack, and exits the opposite side without a cut.",
        "video_summary_en": "The protagonist crosses the action space in three consecutive shots: she accelerates into a full sprint, narrowly evades one clearly visible enemy attack, then recovers her speed and exits on the opposite side.",
        "video_soundscape_en": "Rapid grounded footsteps, controlled breathing and cloth movement continue across the three shots. A sharp incoming attack rush and a brief foot skid punctuate the dodge; no impact, unrelated voice or narration is heard.",
        "refs": [_ref("주인공 캐릭터 시트", "defines protagonist identity, anatomy, costume and carried prop only"), _ref("액션 공간 배경", "defines environment geometry, traversal path and fixed landmarks only"), _ref("액션 구도 스토리보드", "defines camera composition, sprint direction and dodge trajectory only")],
        "required": ["전력 질주", "공격 위치 확인 후 회피", "화면을 연속적으로 가로지름"],
        "forbidden": ["팔다리 붕괴", "얼굴 변경", "무기·소품 소실", "시간축 떨림", "장면 컷 전환"],
    },
    {
        "short_id": "rs02", "title": "R-S02 · 점프·회전·착지", "category": "r2v_high_speed_action", "tier": "stress", "duration": 7,
        "intent_ko": "캐릭터가 공중으로 뛰어올라 몸을 한 번 회전한 뒤 안정적으로 착지한다.",
        "scene_en": "The protagonist runs two steps, jumps upward, completes exactly one readable body rotation in the air, lands on both feet, absorbs the impact, and stabilizes.",
        "refs": [_ref("주인공 캐릭터 시트", "defines protagonist identity, body proportions, costume and hair only"), _ref("도약 공간 배경", "defines ground plane, obstacle clearance and landing area only"), _ref("점프 구도 스토리보드", "defines takeoff pose, one rotation axis and landing composition only")],
        "required": ["도약 준비", "한 번의 공중 회전", "양발 착지", "착지 충격 흡수"],
        "forbidden": ["신체 방향 역전", "중간 프레임 인체 붕괴", "착지 순간이동", "의상·머리카락 변경"],
    },
    {
        "short_id": "rs03", "title": "R-S03 · 100배 크기의 적", "category": "r2v_extreme_scale", "tier": "stress", "duration": 5,
        "intent_ko": "인간을 1로 보았을 때 약 100배 크기의 적과 작은 인간 캐릭터가 같은 공간에서 대치한다.",
        "scene_en": "In one wide shot, preserve a human-scale protagonist at scale 1 and one enemy approximately 100 times larger in the same continuous environment. Reveal enough of the giant body and environmental contact to prove scale; do not fake scale with a normal-sized subject close to camera.",
        "refs": [_ref("인간 캐릭터 시트", "defines the small human protagonist identity and true human scale only"), _ref("초거대 적 디자인", "defines one giant enemy anatomy, silhouette and surface design only"), _ref("스케일 배경", "defines architecture, ground plane and landmarks that make the 100-to-1 scale measurable"), _ref("거대 스케일 스토리보드", "defines wide composition and relative positions only")],
        "required": ["약 100대 1 크기 대비", "거대 적의 환경 접촉", "작은 인간의 식별 가능성", "동일 공간 원근"],
        "forbidden": ["일반 크기 적의 근접 촬영", "크기 비율 붕괴", "괴수 전체 구조 변경", "두 존재의 공간 분리"],
    },
    {
        "short_id": "rs04", "title": "R-S04 · 거대한 공격 회피", "category": "r2v_extreme_scale", "tier": "stress", "duration": 7,
        "intent_ko": "초거대 적의 손이나 발이 내려오고 작은 캐릭터가 옆으로 빠르게 회피한다.",
        "scene_en": "A colossal limb descends toward the small protagonist. The contact point remains readable; the protagonist performs one fast lateral dodge before impact, and the giant limb strikes the ground at the original position.",
        "refs": [_ref("작은 주인공 시트", "defines protagonist identity and human scale only"), _ref("초거대 적 디자인", "defines the same giant enemy and colossal limb anatomy only"), _ref("전투 공간 배경", "defines ground, scale landmarks and impact area only"), _ref("회피 스토리보드", "defines limb trajectory, dodge direction and impact composition only")],
        "required": ["거대 신체 하강", "충돌 전 측면 회피", "원래 위치에 충돌", "스케일 유지"],
        "forbidden": ["회피 전 충돌", "캐릭터 순간이동", "거대 신체 구조 붕괴", "배경 교체"],
    },
    {
        "short_id": "rs05", "title": "R-S05 · 다수 적 포위", "category": "r2v_multi_subject", "tier": "stress", "duration": 6,
        "intent_ko": "주인공 한 명이 설정된 수의 적에게 둘러싸이며 각 개체와 위치 관계가 유지된다.",
        "scene_en": "One protagonist stands at the center while exactly {enemy_count} distinct enemies spread into a readable surrounding formation. Keep the protagonist identifiable and every enemy as a separate body; hold the spatial relationship through the end.",
        "refs": [_ref("주인공 캐릭터 시트", "defines the single protagonist identity only"), _ref("적 디자인 레퍼런스", "defines the shared enemy design; instantiate separate complete enemies without fusion"), _ref("전투 공간 배경", "defines arena geometry and available surrounding positions only"), _ref("포위 구도 스토리보드", "defines formation and protagonist position only")],
        "required": ["주인공 한 명 유지", "정확히 {enemy_count}명의 적", "적 개체 분리", "포위 위치 관계"],
        "forbidden": ["적 신체 융합", "주인공 복제", "적 누락·과잉", "화면 복잡도에 따른 배경 붕괴"],
        "parameters": {"enemy_count": {"type": "integer", "default": 5, "minimum": 3, "maximum": 10, "label_ko": "적 숫자"}},
    },
    {
        "short_id": "rs06", "title": "R-S06 · 군중 속 이동", "category": "r2v_multi_subject", "tier": "stress", "duration": 7,
        "intent_ko": "주인공이 복잡한 시장 군중 사이를 빠르게 지나간다.",
        "scene_en": "The protagonist moves quickly through a dense market crowd along one continuous route, becomes partially occluded by multiple people, then emerges with the same face, costume and direction.",
        "refs": [_ref("주인공 캐릭터 시트", "defines the protagonist identity and costume only"), _ref("군중 시장 배경", "defines crowd density, market geometry and travel route only"), _ref("이동 스토리보드", "defines camera, occlusion points and exit direction only")],
        "required": ["군중 사이 연속 이동", "부분 가림", "가림 뒤 동일 인물 복원", "동선 충돌 회피"],
        "forbidden": ["주인공 교체", "군중 신체 융합", "배경 공간 변경", "이동 방향 도약"],
    },
    {
        "short_id": "rs07", "title": "R-S07 · 보호 상호작용", "category": "r2v_interaction", "tier": "stress", "duration": 6,
        "intent_ko": "주인공이 작은 존재를 몸과 팔로 감싸 보호하며 뒤로 물러난다.",
        "scene_en": "The protector wraps both arms around the smaller being without fusion, turns their own body into a shield, and takes two careful backward steps while maintaining readable fear and protection.",
        "refs": [_ref("보호자 캐릭터 시트", "defines protector identity, anatomy and costume only"), _ref("작은 캐릭터·생물 시트", "defines the smaller protected being identity and scale only"), _ref("보호 공간 배경", "defines ground, retreat path and threat direction only"), _ref("보호 자세 스토리보드", "defines arm placement, body shielding and camera composition only")],
        "required": ["두 정체성 유지", "팔로 감싸는 접촉", "몸으로 가림", "함께 뒤로 이동"],
        "forbidden": ["신체 융합", "작은 존재 소실", "손·팔 관통", "감정과 행동 불일치"],
    },
    {
        "short_id": "rs08", "title": "R-S08 · 긴 무기 상호작용", "category": "r2v_prop_action", "tier": "stress", "duration": 6,
        "intent_ko": "주인공이 긴 창이나 검을 빠르게 휘둘러 적의 공격을 막는다.",
        "scene_en": "The protagonist grips one long weapon with both hands, swings it through one continuous arc, and blocks one incoming enemy attack at a clear contact point. Preserve exact weapon length, shape and ownership.",
        "refs": [_ref("주인공 캐릭터 시트", "defines protagonist identity and costume only"), _ref("긴 무기 디자인", "defines the single weapon length, shape and material only"), _ref("적 공격 이미지", "defines the incoming attack source and direction only"), _ref("방어 스토리보드", "defines grip, swing arc and contact composition only")],
        "required": ["양손과 무기 연결", "연속 휘두르기", "명확한 접촉", "동일 무기 유지"],
        "forbidden": ["무기 증식·소멸", "무기 길이 변화", "손 관통", "접촉 없는 방어"],
    },
    {
        "short_id": "rs09", "title": "R-S09 · 저조도 폭우와 번개", "category": "r2v_vfx_environment", "tier": "stress", "duration": 6,
        "intent_ko": "폭우와 번개가 이어지는 어두운 밤에 캐릭터가 적과 대치한다.",
        "scene_en": "At night in heavy rain, the protagonist faces one enemy. Two lightning flashes briefly illuminate the same faces and silhouettes while rain and darkness remain spatially coherent.",
        "refs": [_ref("주인공 캐릭터 시트", "defines protagonist identity and silhouette only"), _ref("야간 폭우 배경", "defines dark environment, rain direction and fixed landmarks only"), _ref("저조도 스토리보드", "defines confrontation positions and lightning composition only")],
        "required": ["저조도 얼굴 유지", "실루엣 분리", "연속적인 비 방향", "번개에 따른 광원 변화"],
        "forbidden": ["비로 인한 신체 붕괴", "번개 때 얼굴 교체", "배경과 주체 융합", "프레임 깜빡임"],
    },
    {
        "short_id": "rs10", "title": "R-S10 · 화염·연기·파편", "category": "r2v_vfx_environment", "tier": "stress", "duration": 6,
        "intent_ko": "불길과 연기, 날리는 파편 사이에서 캐릭터가 앞으로 이동한다.",
        "scene_en": "The protagonist advances through dense fire, drifting smoke and falling debris. Effects may occlude parts of the body but the same character, route and lighting response must persist.",
        "refs": [_ref("주인공 캐릭터 시트", "defines protagonist identity, anatomy and costume only"), _ref("화염·연기 공간", "defines environment, effect sources and travel path only"), _ref("이동 스토리보드", "defines camera, occlusion and forward motion only")],
        "required": ["효과 속 전진", "가림 뒤 캐릭터 복원", "광원 반응", "파편 낙하"],
        "forbidden": ["연기와 신체 융합", "시간축 깜빡임", "캐릭터 소실", "파편 무작위 증식"],
    },
    {
        "short_id": "rs11", "title": "R-S11 · 비정형 괴수·촉수", "category": "r2v_creature_structure", "tier": "stress", "duration": 7,
        "intent_ko": "복수의 촉수를 가진 괴물이 공간을 채우고 캐릭터가 공격을 피한다.",
        "scene_en": "One non-humanoid monster fills much of the confined space. Multiple tentacles remain connected to the same body; exactly one tentacle attacks and the protagonist performs one readable dodge.",
        "refs": [_ref("주인공 캐릭터 시트", "defines protagonist identity and scale only"), _ref("비정형 괴수 디자인", "defines one monster body, tentacle roots and surface design only"), _ref("좁은 공간 배경", "defines boundaries, depth and occupancy only"), _ref("대치 스토리보드", "defines monster placement, attack tentacle and dodge direction only")],
        "required": ["괴수 기본 디자인 유지", "촉수와 몸통 연결", "한 촉수 공격", "캐릭터 회피"],
        "forbidden": ["촉수 무작위 증식", "괴수 몸통 소실", "캐릭터와 촉수 융합", "공간 경계 붕괴"],
    },
    {
        "short_id": "rs12", "title": "R-S12 · 환경 붕괴", "category": "r2v_environment_destruction", "tier": "stress", "duration": 8,
        "intent_ko": "바닥이 갈라지고 벽이 무너지며 캐릭터가 균형을 잡고 탈출한다.",
        "scene_en": "The floor cracks first, then one wall collapses and debris falls. The protagonist loses balance, recovers, and escapes along the only clear route while the environment changes continuously around them.",
        "refs": [_ref("주인공 캐릭터 시트", "defines protagonist identity and anatomy only"), _ref("정상 상태 배경", "defines the intact initial architecture and escape route only"), _ref("붕괴 스토리보드", "defines crack origin, wall collapse, debris direction and escape composition only")],
        "required": ["바닥 균열", "벽 붕괴", "균형 회복", "탈출", "사건 순서 유지"],
        "forbidden": ["붕괴 전 탈출", "캐릭터 위치 도약", "파편과 인체 융합", "전체 배경 순간 교체"],
    },
]


def _dual(short_id: str, title: str, intent: str, scene: str, required: list[str], forbidden: list[str], duration: int = 7, weapon: bool = False) -> dict[str, Any]:
    refs = [
        _ref("캐릭터 A 시트", "defines Character A identity, anatomy, costume and role only"),
        _ref("캐릭터 B 시트", "defines Character B identity, anatomy, costume and role only"),
        _ref("행동 공간 배경", "defines environment geometry, paths and fixed landmarks only"),
        _ref("2인 액션 스토리보드", "defines positions, trajectories, contact timing and camera composition only"),
    ]
    if weapon:
        refs.append(_ref("무기·소품 디자인", "defines the single shared or carried prop shape, scale and material only"))
    result = {"short_id": short_id, "title": title, "category": "r2v_two_character_action", "tier": "stress", "duration": duration, "intent_ko": intent, "scene_en": scene, "refs": refs, "required": required, "forbidden": forbidden}
    if short_id == "rd06":
        result["dialogue"] = [
            {"speaker": "A", "line_ko": "뒤로 물러서!"},
            {"speaker": "B", "line_ko": "이번엔 내가 막을게!"},
        ]
    return result


CASES.extend([
    _dual("rd01", "R-D01 · 교차 이동과 방향 전환", "두 캐릭터가 반대편에서 달려와 충돌 직전에 비켜 지나간 뒤 서로를 바라본다.", "Character A and Character B run from opposite sides, evade each other at the crossing point without contact, continue past, then both turn to look back while keeping identities and directions.", ["반대 방향 접근", "충돌 없는 교차", "통과 후 방향 전환", "두 얼굴·의상 유지"], ["순간 위치 교환", "교차 시 신체 융합", "캐릭터 복제", "이동 방향 도약"], 7),
    _dual("rd02", "R-D02 · 공격·방어·반격", "A가 공격하고 B가 막은 뒤 B가 반격하며 A가 피한다.", "Character A attacks exactly once, Character B blocks at a visible contact point, then Character B counterattacks exactly once and Character A evades backward. Preserve roles and event order.", ["A의 선제 공격", "B의 방어 접촉", "B의 한 번의 반격", "A의 후퇴 회피"], ["공격 순서 변경", "접촉 없는 결과", "역할 교환", "무기 복제"], 8, True),
    _dual("rd03", "R-D03 · 투척과 포착", "A가 소품 하나를 B에게 던지고 B가 받은 뒤 다시 보여준다.", "Character A throws one prop along a visible arc. Character B catches that same prop with both hands and holds it up. Ownership changes exactly once and the prop never duplicates.", ["A의 투척", "연속 궤적", "B의 양손 포착", "소유권 한 번 변경"], ["소품 복제·소멸", "접촉 없는 소유권 변경", "손 관통", "인물 역할 혼합"], 7, True),
    _dual("rd04", "R-D04 · 등 맞댄 협동 방어", "두 캐릭터가 등을 맞대고 서로 다른 방향의 공격에 각각 대응한다.", "The two characters stand back-to-back and defend against separate off-screen threats in opposite directions. Each performs one independent defensive action while maintaining body contact and identity.", ["등을 맞댄 자세", "반대 방향 주시", "독립된 방어 행동", "두 정체성 유지"], ["신체 융합", "행동 방향 혼합", "한 인물 소실", "동작 완전 동기화"], 7),
    _dual("rd05", "R-D05 · 추격과 추월", "A가 앞에서 달리고 B가 뒤에서 추격하다 옆으로 이동해 추월한다.", "Character A runs ahead while Character B pursues from behind. Character B accelerates, moves to one side, overtakes Character A, and finishes clearly in front without a cut.", ["앞뒤 관계", "B의 가속", "측면 추월", "추월 후 위치 역전"], ["순간 위치 교환", "가림 뒤 인물 교체", "지면 접촉 소실", "배경 방향 역전"], 8),
    _dual("rd06", "R-D06 · 대사와 협동 액션", "A가 공격을 막으며 경고하고 B가 대답한 뒤 이동해 반격한다.", "Character A blocks an incoming attack and says exactly once in natural Korean, ‘뒤로 물러서!’ Character B replies exactly once, ‘이번엔 내가 막을게!’ then moves laterally and counterattacks. Keep speaker, lips, gaze and action roles distinct.", ["A의 방어와 정확한 대사", "B의 정확한 응답", "B의 측면 이동", "B의 반격"], ["화자 교환", "대사 중복·누락", "공격 역할 혼합", "립싱크 중 행동 붕괴"], 9, True),
])


def _turn_case(count: int, dialogue: list[tuple[str, str]], duration: int) -> dict[str, Any]:
    refs = [_ref(f"캐릭터 {chr(65 + index)} 시트", f"defines Character {chr(65 + index)} identity, face, costume and fixed speaking position only") for index in range(count)]
    refs.extend([
        _ref("대화 공간 배경", "defines the shared semicircle staging, ground and fixed landmarks only"),
        _ref("다인 대화 스토리보드", "defines left-to-right positions, gaze handoff and a mostly locked camera only"),
    ])
    lines = " ".join(f"Character {speaker} says exactly once in natural Korean, ‘{line}’" for speaker, line in dialogue)
    return {
        "short_id": f"rt{count:02d}", "title": f"R-T{count:02d} · {count}인 티키타카", "category": "r2v_turn_taking", "tier": "stress" if count >= 4 else "diagnostic", "duration": duration,
        "intent_ko": f"서로 다른 {count}명이 정해진 순서로 한 번씩 짧게 말하며 시선과 반응을 다음 화자에게 넘긴다.",
        "scene_en": f"Stage exactly {count} distinct characters in a readable semicircle with a locked or extremely slow camera. {lines}. Preserve exact speaker order, identity, position and non-speakers' closed mouths. After the last line, Character A gives one silent nod.",
        "refs": refs,
        "required": [f"정확히 {count}명 유지", "지정된 화자 순서", "각 인물 한 번만 발화", "다음 화자를 향한 시선", "마지막 뒤 A의 무언 반응"],
        "forbidden": ["화자 교환", "대사 누락·중복", "말하지 않는 인물의 립싱크", "인물 융합·복제", "후반 화자 소실"],
        "dialogue": [{"speaker": speaker, "line_ko": line} for speaker, line in dialogue],
    }


CASES.extend([
    _turn_case(2, [("A", "준비됐어?"), ("B", "응, 바로 시작하자.")], 7),
    _turn_case(3, [("A", "모두 준비됐어?"), ("B", "나는 준비됐어."), ("C", "그럼 지금 출발하자.")], 9),
    _turn_case(4, [("A", "왼쪽을 확인해."), ("B", "왼쪽은 안전해."), ("C", "오른쪽도 이상 없어."), ("D", "좋아, 앞으로 가자.")], 11),
    _turn_case(5, [("A", "상황을 보고해."), ("B", "입구는 열렸어."), ("C", "뒤쪽은 조용해."), ("D", "장비도 준비됐어."), ("E", "그럼 출발하자.")], 13),
    _turn_case(6, [("A", "모두 위치를 확인해."), ("B", "나는 왼쪽이야."), ("C", "나는 중앙에 있어."), ("D", "오른쪽도 준비됐어."), ("E", "후방은 안전해."), ("F", "좋아, 작전을 시작하자.")], 15),
])


GENRE_ASSIGNMENTS = {
    "rd03": "live_action", "rd04": "live_action",
    "rd05": "hand_drawn_2d", "rd06": "hand_drawn_2d",
    "rt02": "live_action", "rt03": "live_action",
    "rt04": "hand_drawn_2d", "rt05": "hand_drawn_2d", "rt06": "hand_drawn_2d",
}
for _case in CASES:
    _style = GENRE_ASSIGNMENTS.get(_case["short_id"])
    if _style:
        _case["visual_style"] = _style
        _case["title"] += " · " + ("실사" if _style == "live_action" else "2D 애니메이션")


def _genre_case(short_id: str, title: str, style: str, intent: str, scene: str, refs: list[dict[str, str]], required: list[str], forbidden: list[str], duration: int = 7) -> dict[str, Any]:
    return {
        "short_id": short_id, "title": title, "visual_style": style,
        "category": "r2v_live_action_style" if style == "live_action" else "r2v_hand_drawn_2d_style",
        "tier": "stress", "duration": duration, "intent_ko": intent, "scene_en": scene,
        "refs": refs, "required": required, "forbidden": forbidden,
    }


CASES.extend([
    _genre_case(
        "rl01", "R-L01 · 실사 얼굴·피부·손 접촉", "live_action",
        "실사 인물 두 명이 가까운 구도에서 악수하고 작은 금속 열쇠를 전달하는 동안 얼굴·피부·손 구조를 유지한다.",
        "In a close live-action two-shot, Character A and Character B make eye contact, complete one natural handshake, then Character A places one small metal key into Character B's open palm. Keep both real human faces, skin texture and finger anatomy stable.",
        [_ref("캐릭터 A 배우 레퍼런스 시트", "defines live-action Actor A face, hair, body, wardrobe and skin tone only"), _ref("캐릭터 B 배우 레퍼런스 시트", "defines live-action Actor B face, hair, body, wardrobe and skin tone only"), _ref("금속 열쇠 소품 디자인", "defines one practical metal key shape and material only"), _ref("실내 실사 촬영 배경", "defines a practical interior set, blocking space and natural lighting only"), _ref("악수·전달 구도 스토리보드", "defines close two-shot framing, hand contact and key transfer only")],
        ["두 실사 얼굴 유지", "자연스러운 피부 질감", "정확한 악수 접촉", "열쇠 소유권 한 번 변경"],
        ["얼굴 미용 필터화·교체", "왁스 같은 피부", "손가락 융합", "열쇠 복제·관통"], 7,
    ),
    _genre_case(
        "rl02", "R-L02 · 실사 고속 이동·모션 블러", "live_action",
        "실사 인물이 골목을 빠르게 달리며 카메라 앞을 통과할 때 자연스러운 모션 블러와 얼굴·신체 구조를 동시에 유지한다.",
        "A live-action runner accelerates through a daylight alley, crosses close to the moving camera, then decelerates beside a fixed doorway. Produce physically plausible directional motion blur while preserving the same real face, limbs, wardrobe and environment.",
        [_ref("실사 주인공 배우 시트", "defines the live-action runner identity, wardrobe and anatomy only"), _ref("낮 골목 실사 배경", "defines practical alley geometry, fixed doorway and running path only"), _ref("추적 촬영 스토리보드", "defines camera travel, close crossing and deceleration composition only")],
        ["실사 얼굴·의상 유지", "방향성 모션 블러", "지면 접촉", "고정 출입구 유지"],
        ["프레임 보간 유령상", "얼굴 녹음", "팔다리 중복", "배경 휘어짐·교체"], 7,
    ),
    _genre_case(
        "rl03", "R-L03 · 실사 VFX와 실제 조명 결합", "live_action",
        "야간 실사 장면에서 에너지 효과가 점화되며 인물과 실제 세트에 일관된 반사광과 그림자를 만든다.",
        "In a live-action night set, the protagonist raises one practical metal device. A contained blue energy arc ignites only between its two electrodes, casting coherent blue light and moving shadows on the real face, hands, wet floor and nearby wall.",
        [_ref("실사 주인공 배우 시트", "defines live-action actor identity, wardrobe and skin only"), _ref("야간 실사 세트 배경", "defines practical wet set, wall and motivated base lighting only"), _ref("에너지 장치 디자인", "defines one practical two-electrode metal device only"), _ref("VFX 조명 구도 스토리보드", "defines effect position, reflected light surfaces and camera composition only")],
        ["전극 사이 효과 부착", "얼굴·손 반사광", "세트 그림자 반응", "실사 재질 유지"],
        ["효과 위치 이탈", "피부와 VFX 융합", "주변광 반응 누락", "CG 애니메이션풍 전환"], 7,
    ),
    _genre_case(
        "ra01", "R-A01 · 2D 선화·색면 일관성", "hand_drawn_2d",
        "정통 2D 캐릭터가 고개와 몸을 돌리고 손을 뻗는 동안 선 굵기, 얼굴 작화와 셀 색면을 유지한다.",
        "In authentic hand-drawn 2D animation, the character turns the head, rotates the torso, reaches one hand forward, then settles into a clean profile pose. Preserve the exact line weight, facial construction, flat color shapes and cel-shadow boundaries.",
        [_ref("2D 주인공 설정 시트", "defines the hand-drawn character turnaround, face construction, costume shapes and color model only"), _ref("2D 실내 배경", "defines the painted 2D environment, perspective and color script only"), _ref("2D 포즈 전환 스토리보드", "defines the ordered head, torso and hand poses only")],
        ["선 굵기 유지", "얼굴 작화 유지", "색면 경계 유지", "정면에서 측면 포즈 연결"],
        ["선화 떨림", "얼굴 비례 변경", "색 번짐", "3D 렌더링풍 전환"], 6,
    ),
    _genre_case(
        "ra02", "R-A02 · 2D 과장 액션·스미어 복원", "hand_drawn_2d",
        "2D 캐릭터가 과장된 검 휘두르기를 수행하며 짧은 스미어 프레임 뒤 원래 디자인으로 정확히 복원된다.",
        "In authentic hand-drawn 2D action animation, the character anticipates, swings one sword through a fast exaggerated arc with one brief intentional smear, hits a clear stop pose, and immediately returns to the exact on-model design.",
        [_ref("2D 액션 캐릭터 설정 시트", "defines on-model 2D anatomy, costume, face and color model only"), _ref("2D 검 디자인 시트", "defines one sword silhouette, length and color only"), _ref("2D 액션 배경", "defines a painted action stage and ground plane only"), _ref("2D 스미어 액션 스토리보드", "defines anticipation, swing arc, one smear and stop pose only")],
        ["예비 동작", "의도적인 단일 스미어", "명확한 정지 포즈", "원래 작화 복원"],
        ["지속적인 신체 왜곡", "검 증식", "선화 붕괴", "스미어 뒤 다른 캐릭터"], 6,
    ),
    _genre_case(
        "ra03", "R-A03 · 2D 멀티플레인 패럴랙스", "hand_drawn_2d",
        "2D 캐릭터 두 명의 대화 중 카메라가 천천히 횡이동하며 전경·중경·후경 레이어의 패럴랙스와 평면 작화를 유지한다.",
        "In authentic hand-drawn 2D animation, Character A and Character B exchange one silent reaction while the camera pans slowly sideways. Move foreground, midground and background painted layers at distinct parallax rates without turning either character into a 3D model.",
        [_ref("2D 캐릭터 A 설정 시트", "defines Character A line art, face, costume shapes and color model only"), _ref("2D 캐릭터 B 설정 시트", "defines Character B line art, face, costume shapes and color model only"), _ref("2D 멀티플레인 배경", "defines separated foreground, midground and background painted layers only"), _ref("2D 패럴랙스 구도 스토리보드", "defines character blocking, lateral pan and layer motion only")],
        ["두 2D 정체성 유지", "세 레이어 속도 차이", "부드러운 횡이동", "평면 셀 작화 유지"],
        ["레이어 동시 이동", "공간 찌그러짐", "캐릭터 3D화", "선화·색면 깜빡임"], 8,
    ),
])


# Actual H3 video-input shot beats.  These are deliberately separate from
# storyboard_beat_contract(), which belongs to the R2V reviewer contract.
VIDEO_SHOT_BEATS: dict[str, list[str]] = {
    "rs01": [
        "A wide low-angle lateral view establishes the full traversal path. She enters at the opening position and scale, leans forward and accelerates into a full sprint in the established screen direction with grounded alternating foot contact. The camera tracks beside her at matching speed while the fixed landmarks slide past coherently.",
        "A tighter dynamic tracking view keeps her complete silhouette and the attack path readable together. One clearly visible enemy strike enters along the planned trajectory; she notices it before contact, redirects momentum through one planted foot and performs one fast lateral dodge as the attack passes through the exact space she has just vacated.",
        "A wider follow view shows her plant the dodging foot, recover balance and return immediately to full speed. The camera eases its tracking rate so the fixed landmarks prove continuous travel rather than teleportation or reversal. She crosses the remaining action space and exits through the opposite edge at the planned final position.",
    ],
    "rs02": [
        "She takes exactly two accelerating steps, lowers her center of gravity and loads both legs for the jump while the camera holds the referenced takeoff composition.",
        "She drives upward from the marked takeoff point; both feet leave the ground cleanly and her arms initiate the single planned rotation without changing her identity or scale.",
        "At the apex she completes exactly one readable rotation around the storyboard axis, with coherent limb spacing, costume follow-through and no second spin.",
        "She returns upright, lands on both feet in the referenced landing area, bends knees and hips to absorb impact, then settles into a stable final pose.",
    ],
    "rs03": [
        "A very wide composition establishes the human-scale protagonist at scale 1 and the colossal titan at approximately 100-to-1 scale inside the same measurable environment.",
        "The titan's immense feet and lower body remain in physical contact with architecture and ground landmarks, proving that its scale is structural rather than a foreground perspective trick.",
        "The camera reframes without collapsing scale so the small protagonist remains identifiable by face, teal jacket and ochre scarf while a substantial portion of the titan remains visible.",
        "The final wide composition holds both subjects in one coherent depth field with unchanged proportions, stable landmarks and an unmistakable 100-to-1 relationship.",
    ],
    "rs04": [
        "The colossal titan's monolithic limb begins descending toward the small protagonist, with the intended ground contact point and extreme scale readable in the same composition.",
        "The limb accelerates downward while the protagonist recognizes the threat, plants one foot and launches one fast lateral dodge before any contact occurs.",
        "The titan's limb strikes the protagonist's original position with a heavy ground impact as the protagonist clears the contact area without teleportation or intersection.",
        "Dust settles around the impact point while the protagonist holds the safe lateral position and the titan, environment landmarks and extreme scale remain unchanged.",
    ],
    "rs05": [
        "Exactly one protagonist stands at the center of the arena while the first complete enemies enter the surrounding positions indicated by the storyboard.",
        "Exactly {enemy_count} separate obsidian-armored enemies spread outward into the planned formation; each keeps a complete body, angular helmet and crimson sash without fusion.",
        "The camera reveals the full ring clearly enough to count every enemy while preserving one central protagonist and the arena's fixed spatial axes.",
        "The formation settles and holds through the ending composition: one protagonist, exactly {enemy_count} distinct enemies and unchanged relative positions with no duplication or omission.",
    ],
    "rs06": [
        "The protagonist enters the dense market route at speed, identifiable by the short dark braid, teal jacket and ochre scarf against the stable stalls and crowd flow.",
        "Several separate crowd members pass across the foreground and partially occlude her while her feet, route and original screen direction continue behind them.",
        "The occlusion becomes deepest at the planned crossing point, but intermittent views of the same teal jacket, scarf and silhouette maintain her identity and trajectory.",
        "She emerges from the crowd with the same face, braid, costume and direction, avoids body collisions and exits along the route marked by the final storyboard composition.",
    ],
    "rs07": [
        "The protector and the dog-sized ice-blue dragon hatchling occupy separate readable silhouettes as the threat direction and backward retreat path are established.",
        "The protector places both arms around the hatchling with anatomically clear hand and arm contact, keeping the hatchling's horns, wings and tail crystal unobstructed enough to identify it.",
        "She rotates her teal-jacketed body between the threat and the hatchling, forming a shield while both subjects remain distinct and express fear and protection.",
        "Still holding the same hatchling safely, the protector takes exactly two careful backward steps along the referenced route without fusion, penetration or identity change.",
    ],
    "rs08": [
        "The protagonist establishes a firm two-handed grip on the single long ashwood spear, with its steel leaf tip, brass rings and blue wrap fully connected to her hands.",
        "She drives the same spear through one continuous defensive arc; the weapon keeps its exact length, rigid silhouette, material and ownership as the camera follows the motion.",
        "The spear meets the obsidian-armored attacker's hooked blade at one clear contact point, with both complete weapons and both hand connections readable at impact.",
        "The protagonist holds the completed block with the same spear in both hands while the attacker remains separate and no weapon duplicates, shortens or disappears.",
    ],
    "rs09": [
        "At night in heavy rain, the protagonist and one enemy hold separate confrontation silhouettes while fixed landmarks and a single coherent rain direction establish the dark space.",
        "The first lightning flash briefly reveals the protagonist's same face, short braid, teal jacket and ochre scarf and the enemy's unchanged silhouette without bleaching the environment.",
        "Darkness returns smoothly; rain continues along the same direction and both subjects remain fixed in depth and screen position rather than flickering or merging.",
        "A second distinct lightning flash illuminates the same faces, silhouettes and wet landmarks from a coherent source, then resolves into the planned low-light ending composition.",
    ],
    "rs10": [
        "The teal-jacketed protagonist advances into the fire-and-smoke corridor along the referenced route as orange firelight begins reacting across her face, scarf and costume.",
        "Drifting smoke crosses the frame and partially hides her, but glimpses of the same short braid, teal jacket and ochre scarf continue along one uninterrupted trajectory.",
        "She emerges through a brighter fire zone with coherent changing highlights and shadows on the same body and costume while flames remain attached to environmental sources.",
        "Falling debris crosses around her without body fusion; she keeps moving forward and reaches the final storyboard position with identity, route and lighting response intact.",
    ],
    "rs11": [
        "The confined environment reveals one deep-indigo non-humanoid monster with one armored core and six clearly rooted tentacles, while the teal-jacketed protagonist holds a separate dodge-ready position.",
        "The camera shows the tentacle roots remaining connected to the same compact body as the monster fills the space without multiplying or losing its core.",
        "Exactly one tentacle launches along the referenced attack path; the other rooted tentacles remain attached and the protagonist reads the incoming direction before contact.",
        "The protagonist performs one clean dodge into the planned safe position while the attacking tentacle passes by and remains connected to the unchanged monster body.",
    ],
    "rs12": [
        "The intact architecture and only clear escape route are established around the teal-jacketed protagonist; the floor then develops its first visible crack at the storyboard origin.",
        "The crack spreads before one wall collapses in the planned direction, releasing separate debris while the protagonist loses balance without changing position discontinuously.",
        "She plants a foot, recovers balance and turns toward the still-readable escape route as masonry continues falling around rather than through her body.",
        "She escapes along that route while the damaged environment evolves continuously and reaches the final composition only after the floor crack, wall collapse and recovery have occurred in order.",
    ],
    "rd01": [
        "Character A in the brick-red jacket and Character B in the cobalt-blue coat run from opposite sides toward the same visible crossing point with stable identities and directions.",
        "At the crossing point both make small complementary evasive adjustments and pass without contact, body fusion, identity exchange or instantaneous position swapping.",
        "They continue beyond each other in their original travel directions, keeping complete silhouettes, stable faces and the environment's fixed screen axis.",
        "After creating clear separation, both slow and turn their heads to look back at one another while their costumes, positions and post-crossing directions remain unambiguous.",
    ],
    "rd02": [
        "Character A in brick red performs exactly one initial attack with the single ashwood spear while Character B in cobalt blue braces in the separate defensive role.",
        "Character B blocks that attack at one visible physical contact point; both weapons, hands and bodies remain complete and their roles do not exchange.",
        "After the block resolves, Character B performs exactly one counterattack along the planned trajectory while Character A recognizes the reversal.",
        "Character A evades backward into the referenced ending position as Character B completes the counterattack, preserving the attack-block-counterattack-evade order and the single prop.",
    ],
    "rd03": [
        "Character A in the brick-red jacket holds the single red leather pouch with brass ring, draws the throwing arm back and releases it exactly once toward Character B.",
        "The same compact red pouch follows one visible uninterrupted arc through the environment, with no duplicate appearing in either character's hands.",
        "Character B in the cobalt-blue coat tracks the pouch and catches that exact object with both anatomically complete hands at the planned contact point.",
        "Character B raises and displays the same red pouch while Character A's hands remain empty, proving one ownership change with unchanged shape, scale and material.",
    ],
    "rd04": [
        "Character A in brick red and Character B in cobalt blue establish a stable back-to-back stance with readable body contact and opposite gaze directions.",
        "Character A performs one independent defensive response toward the threat on her side while Character B maintains back contact and watches the opposite side.",
        "Character B performs a different defensive response toward the opposite threat while Character A holds her completed pose; their motions do not mirror or synchronize artificially.",
        "Both settle back-to-back in the ending composition with separate limbs, unchanged faces and costumes, maintained contact and clearly opposed defensive directions.",
    ],
    "rd05": [
        "Character A in brick red runs clearly ahead while Character B in cobalt blue pursues from behind along the same painted ground direction.",
        "Character B increases cadence and closes the distance without changing identity, ground contact or the environment's screen direction.",
        "Character B moves to one side and passes Character A through a readable lateral overtaking path rather than swapping positions instantaneously.",
        "Character B finishes clearly in front and Character A remains behind, with both on-model 2D designs and the reversed front-back relationship held in the final composition.",
    ],
    "rd06": [
        "Character A in the brick-red jacket holds the single spear in a connected block and, as <Subject 1> (S1), warns exactly once, <d>[Korean] 뒤로 물러서!</d> Her lips close immediately after the line.",
        "Character B in the cobalt-blue coat looks toward Character A and, as <Subject 2> (S2), replies exactly once, <d>[Korean] 이번엔 내가 막을게!</d> Only Character B's lips move, then close.",
        "With both mouths closed, Character B moves laterally along the established screen direction while Character A keeps the separate defensive contact and the single spear remains unchanged.",
        "Character B performs one readable counterattack and ends in the active position while Character A holds the distinct defensive pose; speakers, gaze, action roles and props never exchange.",
    ],
    "rl01": [
        "The real Character A in brick red and real Character B in cobalt blue share a close two-shot, make natural eye contact and retain authentic skin texture and facial asymmetry.",
        "They complete one natural handshake with five distinct fingers on each visible hand, coherent palm contact and no fused or penetrating anatomy.",
        "Character A presents the single worn iron key and places it into Character B's open palm while both faces and hands remain stable in the practical interior light.",
        "Character B closes the fingers around and displays the same round-bowed iron key as Character A releases it, completing exactly one ownership change without duplication.",
    ],
    "rl02": [
        "The live-action runner with the short dark braid, teal jacket and ochre scarf accelerates along the daylight alley with firm foot contact and the fixed doorway visible ahead.",
        "She crosses close to the moving camera at peak speed, producing physically directional motion blur while the same real face, limbs and wardrobe remain structurally coherent.",
        "The camera continues its planned travel as she passes, then she begins a grounded deceleration without ghost images, duplicated limbs or warped alley geometry.",
        "She stops beside the same fixed doorway in the final composition, with natural skin, unchanged costume, correct anatomy and all practical landmarks preserved.",
    ],
    "rl03": [
        "In the practical wet night set, the live-action protagonist with short dark braid and teal jacket raises the single dark-steel two-electrode device in both readable hands.",
        "A contained blue energy arc ignites only between the device's two copper electrodes, remaining attached to them without spreading onto her skin or the set.",
        "The blue arc casts synchronized reflected light across her unchanged real face, fingers and wardrobe while the practical base lighting and wet materials remain photorealistic.",
        "Moving blue shadows and reflections travel coherently across the wet floor and nearby wall as the same device, actor and practical set resolve in the final composition.",
    ],
    "ra01": [
        "The on-model 2D protagonist begins front-facing in the painted interior, preserving the short dark braid, teal costume shapes, exact facial construction and stable line weight.",
        "She turns her head first and then rotates the torso, with clean in-between drawings, unchanged flat colors and cel-shadow boundaries that follow the ordered storyboard pose.",
        "She extends one complete hand forward while the face, costume contours and painted perspective remain stable without line boil, color bleeding or 3D volume drift.",
        "She settles into the clean profile pose shown by the final storyboard frame, fully restored on-model with the same line weight, color shapes and facial proportions.",
    ],
    "ra02": [
        "The on-model 2D fighter in teal establishes a strong anticipation pose while gripping the single dark-blue sword with gold guard and red-wrapped handle.",
        "The fighter releases one fast exaggerated swing and the same sword travels through the planned arc, using exactly one brief intentional smear drawing.",
        "The smear resolves immediately into a crisp stop pose with one sword, complete hands and readable line art rather than persistent body distortion.",
        "The fighter returns to the exact reference design with stable face, costume, flat colors and sword silhouette while holding the final storyboard composition.",
    ],
    "ra03": [
        "The on-model 2D Character A in brick red and Character B in cobalt blue hold separate positions inside the three-layer painted environment and exchange an initial silent look.",
        "A slow sideways camera pan begins; foreground, midground and background layers move at clearly different parallax rates while both characters retain flat cel construction.",
        "Character B gives one silent reaction toward Character A as the lateral pan continues smoothly, with stable line art, color shapes and layer boundaries.",
        "Character A returns a distinct silent reaction and the pan settles on the final composition, preserving both 2D identities and three separate painted depth layers without 3D conversion.",
    ],
}



ACTION_V2_ENVIRONMENT_DESCRIPTIONS: dict[str, str] = {
    "rs01": "the sunset-lit ruined stone terrace with a broad path, broken columns and a standing arch",
    "rs02": "the elevated sunlit stone platform with a rectangular landing surface, open edges and distant mountains",
    "rs03": "the vast ruined valley with cliff walls, monumental structures and a broad measurable ground plane",
    "rs04": "the circular cracked stone battlefield with a central impact area and fractured paving",
    "rs05": "the circular stone arena with one central mark and five surrounding floor markers",
    "rs06": "the narrow crowded market lane with stalls, awnings and a continuous route into depth",
    "rs07": "the dark circular chamber with a round floor motif, multiple entrances and an open retreat path",
    "rs09": "the rain-soaked night causeway with reflective stone, distant towers, warm braziers and blue lightning",
    "rs10": "the burning industrial corridor with wet central rails, fires on both sides, overhead smoke, collapsed beams, rubble and a distant illuminated archway",
    "rs11": "the enclosed teal-lit chamber with a central walkway, reflective surfaces and a circular illuminated platform",
    "rs12": "the intact arched stone hall with side alcoves, a continuous floor and one bright exit in the distance",
    "rd01": "the ruined crossing space with opposing paths and a clear central intersection",
    "rd02": "the long sunlit combat walkway with a straight axis, pale paving and colored lane markings",
    "rd03": "the open live-action concrete terrace with an unobstructed throwing lane and distant green horizon",
    "rd04": "the roofless ruined courtyard with a flat center and opposite threat directions",
    "rd05": "the hand-drawn coastal promenade with parallel lanes, a stone wall and water",
    "rd06": "the hand-drawn sunlit courtyard with a flat action area, broken walls and arched openings",
    "rl01": "the sparse daylight room with a left window, central table and chairs and open doorways",
    "rl02": "the narrow sunlit stone alley with strong shadows, a blue door and a clear depth axis",
    "rl03": "the dark wet industrial set with a reflective floor and practical blue side lighting",
    "ra01": "the painted interior with a wooden floor, left window, central door and right shelves",
    "ra02": "the painted circular stone plaza with ruined arches, bright sky and distant coast",
    "ra03": "the painted terrace with foreground foliage, a midground platform and distant sunset mountains",
}

ACTION_V2_VIDEO_SHOT_BEATS: dict[str, list[str]] = {
    "rs01": [
        "<Subject 1>, the long-dark-braided woman in the teal field jacket and ochre scarf from <Picture 1>, enters <Subject 2>, the sunset-lit ruined stone terrace from <Picture 2>, from screen left. She leans forward and accelerates into a full sprint toward screen right. Her boots maintain alternating ground contact as the camera tracks beside her, and the broken columns move consistently behind her.",
        "The cut picks up her sprint mid-stride in a closer lateral tracking view without resetting her position or speed. The same long braid, teal jacket and ochre scarf remain visible as one fast spear-like projectile enters from screen right along a clear horizontal path. She sees it before contact, plants her left boot and makes one sharp lateral dodge toward the far side of the terrace. The projectile passes through the exact space she has just vacated.",
        "Continuing directly from the dodge, she transfers her weight through the planted foot, regains balance and returns to full speed. The camera widens and gradually slows while she advances toward the standing arch. The same broken columns and stone path remain behind her in their original order as she exits through the far side of the terrace.",
    ],
    "rs02": [
        "One continuous full-body wide shot follows the long-dark-braided protagonist along the platform. She takes exactly two accelerating steps, pushes from both feet, completes exactly one forward somersault around a horizontal pitch axis, lands with both boots together, bends her knees and hips to absorb impact and settles without a second rotation. The camera tracks gently without cutting or losing her hands or feet.",
    ],
    "rs03": [
        "A very wide low-angle composition places the long-dark-braided human beside a doorway-sized structure while the basalt titan stands in the same valley. Its feet contact the ground near monumental architecture, proving an approximately one-hundred-to-one scale relationship.",
        "The camera cranes upward and widens while retaining the tiny teal-jacketed protagonist and revealing the titan's monolithic arms, broken crown-like head and amber fissures against repeated architectural levels.",
    ],
    "rs04": [
        "A high wide view places the long-dark-braided protagonist near the center of the cracked battlefield and the titan's monolithic hand directly above one visible contact area.",
        "As the hand descends, she plants her left boot and performs one lateral dodge toward screen right before contact. The camera keeps her body and original contact area together.",
        "The hand strikes the exact place she vacated. Dust and small fragments rise as she lands safely at screen right and steadies herself.",
    ],
    "rs05": [
        "A high wide shot establishes one long-dark-braided protagonist on the central mark and five empty surrounding markers.",
        "Exactly five separate obsidian-armored soldiers enter and stop with one complete body on each marker as the camera cranes slightly upward.",
        "The five soldiers turn inward and hold a ring that clearly shows one central protagonist and exactly five distinct enemies.",
    ],
    "rs06": [
        "One continuous forward tracking shot follows the long-dark-braided protagonist into the market lane. Separate crowd members progressively obscure her boots, torso and face, but the same long braid, teal jacket and ochre scarf remain intermittently visible along one uninterrupted path until she emerges with the same face, costume and direction.",
    ],
    "rs07": [
        "A medium-wide shot establishes the long-dark-braided protector and ice-blue dragon hatchling separately in the circular chamber, with the threat at the left entrance and retreat toward screen right.",
        "She places her left arm around the hatchling's chest and right arm behind its back, keeping both hands clear of the cyan wings, then turns her torso between the threat and hatchling.",
        "Holding the same hatchling, she takes exactly two backward steps toward screen right while the camera tracks with both distinct bodies.",
    ],
    "rs08": [
        "A medium-wide view establishes the protagonist holding the single ashwood spear with both hands while the obsidian-armored attacker faces her with one hooked blade.",
        "She drives the same spear through one defensive arc from low left to high right as the attacker swings toward her. The camera follows the spear tip while both hand connections remain visible.",
        "The spear tip and hooked blade meet at one clear contact point. The camera pushes in briefly and holds as the protagonist completes the block with the spear still in her possession.",
    ],
    "rs09": [
        "One continuous static wide shot holds the long-dark-braided protagonist on the left and one dark armored enemy silhouette on the right across the wet causeway. Heavy rain falls coherently. A first blue lightning flash reveals the same face, costume and enemy outline; darkness returns without position changes, then a second flash illuminates the same towers, braziers and subjects.",
    ],
    "rs10": [
        "A rear three-quarter wide shot follows the long-dark-braided protagonist from the foreground along the wet rails toward the distant archway while fires on both sides cast moving orange light.",
        "A closer rear-side view stays on the same axis as smoke rises, rolls overhead and descends across her boots, torso and face. The same braid, teal jacket and scarf remain intermittently visible until she emerges.",
        "A wider follow view shows fragments fall from a damaged overhead beam behind her and beside the rails only after she passes beneath it. The camera cranes upward as she continues toward the archway.",
    ],
    "rs11": [
        "A wide view establishes the protagonist beside one indigo monster in the teal-lit chamber. A slight camera arc shows one armored core and exactly six turquoise-marked tentacles rooted to it.",
        "Exactly one front tentacle launches across the walkway while the other five remain connected and she plants one foot toward the incoming path.",
        "She makes one lateral dodge as the tentacle crosses her previous position and remains connected. The camera keeps her landing, attacking tentacle and unchanged core together.",
    ],
    "rs12": [
        "A wide shot establishes the protagonist in the intact hall and the bright exit in depth. A crack begins near her left boot and spreads toward the left wall.",
        "The left wall collapses only after the crack reaches it. Falling stones make her lose balance; she plants her right boot and recovers in place.",
        "She turns and runs toward the bright arch along the open central floor while a rear tracking view retains the collapsed wall and original crack behind her.",
    ],
    "rd01": [
        "One continuous high medium-wide shot holds the central intersection. Long-dark-braided Character A runs left to right while blond Character B runs right to left. A shifts to the far side and B to the near side at the center, they pass without contact, continue to clear separation and turn their heads back while their bodies remain oriented in the original directions.",
    ],
    "rd02": [
        "A medium-wide view establishes Character A as sole owner of the ashwood spear while unarmed Character B faces her on the straight walkway.",
        "Character A makes one thrust. Character B steps outside the tip and deflects the wooden shaft once with the left forearm at a visible contact point; the spear remains in A's hands.",
        "Character B makes one right-leg counter-kick. Character A withdraws the same spear and takes one backward evasive step without changing ownership or screen direction.",
    ],
    "rd03": [
        "A continuous live-action two-shot places Character A left and Character B right. A holds the red leather pouch by its brass ring, swings once and releases it left to right while the camera shows the full arc and both actors' hands.",
        "Character B catches the same pouch once between both hands and raises it with the brass ring visible while Character A's hands remain empty.",
    ],
    "rd04": [
        "A wide live-action shot establishes Character A and Character B back-to-back in the roofless courtyard, facing separate threats from the left and right openings as the camera makes a slow quarter orbit.",
        "One staff strike enters left and A blocks once with crossed forearms while a separate low strike enters right and B evades with one backward lean. They keep back contact and finish facing opposite directions.",
    ],
    "rd05": [
        "One continuous hand-drawn wide tracking shot follows the coastal promenade. Character A runs ahead near the wall while Character B pursues, accelerates into the water-side lane, draws level and passes completely ahead. The wall, water and lane markings continue in one stable direction.",
    ],
    "rd06": [
        "A medium hand-drawn shot places Character A in front and Character B behind holding the single spear. A blocks one blade entering from screen left and says, <d>[Korean] 뒤로 물러서!</d> Only A's lips move and close.",
        "Character B keeps the spear, replies, <d>[Korean] 이번엔 내가 막을게!</d> closes the mouth and steps toward screen right while A silently withdraws.",
        "Character B drives the same spear forward in one counterattack. The camera pans with it while A stays behind and both 2D identities remain stable.",
    ],
    "rl01": [
        "A realistic medium two-shot shows Character A holding the iron key in the right hand and Character B extending an empty left palm across the table.",
        "A close-up shows A lower the long shaft into B's palm with the round bow and three asymmetrical teeth visible; A releases only as B's fingers close.",
        "A medium two-shot shows A's empty hand withdrawn and B alone lifting the same key into the window light.",
    ],
    "rl02": [
        "One continuous photorealistic front three-quarter tracking shot follows the long-dark-braided protagonist running from the alley depth toward the camera as it retreats. Her face, teal jacket and scarf remain readable while natural blur affects pumping limbs, nearby walls and background shadows; the blue door moves continuously behind her.",
    ],
    "rl03": [
        "A realistic medium shot establishes the protagonist holding the inactive dark-steel device with both copper electrodes visible.",
        "A contained blue arc ignites only between the electrodes as the camera pushes in on the device, complete hands and natural face.",
        "The arc casts synchronized blue light across fingers, jacket, face, wet floor and wall while the camera eases back to reveal the reflections.",
    ],
    "ra01": [
        "One continuous static hand-drawn medium shot shows the long-dark-braided protagonist front-facing. She turns her head right, rotates shoulders and torso, extends the right hand and settles into right profile while the braid, teal costume, face, line weight, flat colors and cel shadows remain stable.",
    ],
    "ra02": [
        "One continuous static hand-drawn medium-wide shot shows the long-dark-braided teal fighter in the circular plaza with the single dark-blue sword, gold guard and red grip. She anticipates, makes one fast diagonal swing with one brief smear, resolves into a crisp stop pose and returns fully on-model without a cut.",
    ],
    "ra03": [
        "One continuous hand-drawn wide shot places Character A and Character B on the midground terrace. The camera pans slowly left to right without cutting: foreground leaves move fastest, terrace and characters move moderately and distant mountains move slightly. B glances at A, then A returns one glance while line art and colors remain stable.",
    ],
}

def _is_storyboard_reference(item: dict[str, str]) -> bool:
    return (
        "스토리보드" in str(item.get("label_ko") or "")
        or "storyboard" in str(item.get("instruction_en") or "").lower()
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def case_id(short_id: str) -> str:
    return f"minimax_h3_r2v_{short_id}"


def case_version_id(short_id: str) -> str:
    return f"{case_id(short_id)}_v1"


def action_v2_case_id(short_id: str) -> str:
    return f"minimax_h3_r2v_action_text_shots_{short_id}"


def action_v2_case_version_id(short_id: str) -> str:
    return f"{action_v2_case_id(short_id)}_v2"


def action_v2_cases() -> list[dict[str, Any]]:
    """Clone the 24 action cases without changing the immutable v1 definitions."""
    return [
        {
            **case,
            "refs": [
                dict(item) for item in case["refs"]
                if not _is_storyboard_reference(item)
            ],
            "forbidden": [
                item for item in case["forbidden"]
                if str(item).strip() != "장면 컷 전환"
            ],
            "storyboard_free": True,
        }
        for case in CASES
        if not str(case["short_id"]).startswith("rt")
    ]


def _default_scene_text(case: dict[str, Any]) -> str:
    defaults = {
        name: definition.get("default")
        for name, definition in dict(case.get("parameters") or {}).items()
    }
    try:
        return str(case["scene_en"]).format_map(defaults)
    except (KeyError, ValueError):
        return str(case["scene_en"])


def _reference_subject(label: str, case: dict[str, Any] | None = None) -> str:
    short_id = str((case or {}).get("short_id") or "")
    if "금속 열쇠" in label:
        return "one small antique iron key with a round bow, three asymmetrical teeth and a worn satin-metal surface"
    if "에너지 장치" in label:
        return "one handheld dark-steel device with two exposed copper electrodes, a leather grip and no active energy effect"
    if "2D 검" in label:
        return "one hand-drawn straight sword with a dark blue blade, gold oval guard, red wrapped grip and a fixed clean silhouette"
    if short_id == "rd03" and "무기·소품" in label:
        return "one palm-sized red leather throwing pouch with a brass ring, dark stitched edge and an unmistakable compact silhouette"
    if "긴 무기" in label or "무기·소품" in label:
        return "one long ashwood spear with a dark steel leaf-shaped tip, two brass grip rings, a blue leather hand wrap and precisely measurable proportions"
    if "적 공격 이미지" in label:
        return "one lean obsidian-armored attacker with a hooked short blade held in one clearly readable attack-ready pose"
    if "작은 캐릭터·생물" in label:
        return "a dog-sized ice-blue dragon hatchling with pearlescent scales, two short charcoal horns, translucent cyan wings, bright blue eyes and a teardrop-shaped tail crystal"
    if "초거대 적" in label:
        return "one colossal basalt titan with a crown-like broken stone head, long monolithic arms, glowing amber fissures and an unmistakable asymmetrical silhouette"
    if "비정형 괴수" in label or "촉수" in label:
        return "one non-humanoid deep-sea monster with a compact armored core, six clearly rooted tentacles, dark indigo skin and bioluminescent turquoise markings"
    if "적 디자인" in label:
        return "one lean obsidian-armored enemy soldier with a closed angular helmet, crimson waist sash, segmented black armor and one hooked short blade"
    if "캐릭터 F" in label:
        return "Character F, a tall older woman with silver braided hair, a white-gray field coat, black gloves and a hexagonal copper brooch"
    if "캐릭터 E" in label:
        return "Character E, a short young man with curly auburn hair, a purple cloak, tan trousers and a round brass shoulder clasp"
    if "캐릭터 D" in label:
        return "Character D, a broad middle-aged woman with a shaved-side hairstyle, a forest-green tunic, dark leather belt and square silver earrings"
    if "캐릭터 C" in label:
        return "Character C, a slender young woman with long black hair in a low ponytail, a mustard-yellow vest, cream shirt and red wrist wraps"
    if "캐릭터 B" in label:
        return "Character B, a young man with light brown skin, short wavy blond hair, a cobalt-blue long coat, gray trousers and one silver ear cuff"
    if "캐릭터 A" in label:
        return "Character A, a young woman with warm brown skin, a short dark braid, a fitted brick-red jacket, black trousers, sturdy boots and an ochre scarf"
    if any(token in label for token in ("주인공", "인간 캐릭터", "보호자")):
        return "the protagonist, a young woman with warm brown skin, a short dark braid, a fitted teal field jacket, ochre scarf, charcoal trousers and sturdy brown boots"
    return "one visually distinctive subject with a fixed face, silhouette, color palette and material design"


def _visual_style_prompt(case: dict[str, Any]) -> str:
    style = str(case.get("visual_style") or "stylized_3d")
    if style == "live_action":
        return "Photorealistic live-action cinema with believable human skin, practical wardrobe and sets, physically based materials, natural lens response and no animation rendering."
    if style == "hand_drawn_2d":
        return "Authentic hand-drawn 2D animation with stable clean line art, deliberate line weight, flat color model, controlled cel shading and painted backgrounds; no 3D CGI rendering."
    return "Premium stylized 3D animated-feature design, cinematic but physically readable, high material detail, consistent proportions, no photoreal celebrity likeness."


def _video_style_instruction(case: dict[str, Any]) -> str:
    style = str(case.get("visual_style") or "stylized_3d")
    if style == "live_action":
        return "Render the complete video as photorealistic live-action cinema. Preserve real human skin, practical materials, natural motion blur and physically coherent lighting; never drift into animation or CGI character styling."
    if style == "hand_drawn_2d":
        return "Render the complete video as authentic hand-drawn 2D animation. Preserve line art, flat color shapes, cel-shadow boundaries and painted-background language; never drift into 3D CGI or photorealism."
    return "Preserve the premium stylized 3D animated-feature visual language shown by the references."


def _character_appeal_prompt(case: dict[str, Any], label: str) -> str:
    style = str(case.get("visual_style") or "stylized_3d")
    if "작은 캐릭터·생물" in label:
        return (
            "Give the creature an immediately charming, endearing screen presence, "
            "with bright expressive eyes, a clean memorable silhouette and premium character-design appeal."
        )
    if style == "live_action":
        return (
            "Cast a naturally attractive, charismatic and cinematic-looking person with distinctive, "
            "harmonious facial features and confident screen presence. Preserve authentic pores, age cues "
            "and human asymmetry; no beauty-filter skin, cosmetic face reshaping, celebrity likeness or glamour retouching."
        )
    if style == "hand_drawn_2d":
        return (
            "Make the character visually appealing, elegant and charismatic, with an expressive face, "
            "graceful shape language, a stylish costume silhouette and a memorable animation-lead design; "
            "avoid a generic doll face or excessive ornamental detail."
        )
    return (
        "Make the character visually appealing, charismatic and heroically stylish, with an expressive face, "
        "harmonious features, a confident silhouette and polished animated-feature character appeal; "
        "avoid a generic doll face, exaggerated glamour makeup or photoreal celebrity likeness."
    )


def _shared_asset_candidate_key(case: dict[str, Any], item: dict[str, str]) -> str:
    label = str(item.get("label_ko") or "")
    style = str(case.get("visual_style") or "stylized_3d")
    character = re.search(r"캐릭터 ([A-F])(?: |$)", label)
    if character:
        return f"{style}_character_{character.group(1).lower()}"
    if (
        any(token in label for token in ("주인공", "인간 캐릭터", "보호자"))
        and "작은 캐릭터·생물" not in label
    ):
        return f"{style}_protagonist"
    if "초거대 적 디자인" in label:
        return f"{style}_colossal_enemy"
    return ""


def shared_asset_key(case: dict[str, Any], item: dict[str, str]) -> str:
    """Return a global key only when the same identity is used by 2+ slots."""
    key = _shared_asset_candidate_key(case, item)
    if not key:
        return ""
    occurrences = sum(
        1
        for candidate_case in CASES
        for candidate_item in candidate_case["refs"]
        if _shared_asset_candidate_key(candidate_case, candidate_item) == key
    )
    return key if occurrences > 1 else ""


def _storyboard_panel_count(case: dict[str, Any]) -> int:
    if str(case.get("short_id") or "").startswith("rt"):
        return min(7, max(3, len(case.get("dialogue") or []) + 1))
    return min(4, max(3, len(case.get("required") or [])))


def reference_image_prompt(case: dict[str, Any], item: dict[str, str], picture_index: int) -> str:
    label = str(item["label_ko"])
    scene = _default_scene_text(case)
    style = _visual_style_prompt(case)
    if "시트" in label or "캐릭터" in label and "스토리보드" not in label:
        subject = _reference_subject(label, case)
        return " ".join([
            f"Create one clean 16:9 character reference sheet for <Picture {picture_index}> ({label}).",
            style,
            f"Subject: {subject}.",
            _character_appeal_prompt(case, label),
            "Use four clearly separated views on one neutral warm-gray canvas: full-body front view, full-body left profile, full-body rear view, and a large face close-up.",
            "The subject must have exactly the same face, hair, costume, colors, body proportions and accessories in every view.",
            "Use a relaxed, confident neutral standing pose and a pleasant natural expression, with even studio lighting, complete hands and feet, no action, no environment, no extra character, no text and no watermark.",
        ])
    if "스토리보드" in label or "구도" in label or "자세" in label:
        panel_count = _storyboard_panel_count(case)
        layout = "one horizontal row" if panel_count <= 4 else "a clean two-row reading grid"
        return " ".join([
            f"Create one clean 16:9 multi-panel cinematic storyboard sheet for <Picture {picture_index}> ({label}).",
            style,
            f"Visualize this exact story moment: {scene}",
            f"Create exactly {panel_count} sequential panels in {layout}, read left to right and then top to bottom.",
            "Each panel represents the next chronological action beat, not an alternate design: establish the opening state, develop the action and contact or dialogue handoff, then show the required ending state.",
            "Keep the same character identities, costumes, props, environment geometry, screen direction and scale across every panel.",
            "Make subject placement, gaze, travel path, contact point and camera viewpoint immediately readable in each panel.",
            "Use clean narrow gutters only; no captions, panel numbers, arrows, motion diagrams, speech bubbles, decorative collage, text or watermark.",
        ])
    if "배경" in label or "공간" in label:
        crowd_rule = "Include anonymous background crowd members as separate complete silhouettes, but do not include the named protagonist." if "군중" in label else "No character, creature, foreground actor or human silhouette."
        composition_rule = (
            "Wide establishing composition, coherent perspective, readable lighting direction, no text, no watermark; use one unified environment plate with no panel layout."
            if case.get("storyboard_free")
            else "Wide establishing composition, coherent perspective, readable lighting direction, no text, no watermark, no storyboard panels."
        )
        return " ".join([
            f"Create one clean 16:9 environment reference plate for <Picture {picture_index}> ({label}).",
            style,
            f"Build the environment required by this scene: {scene}",
            "Show stable ground geometry, clear depth, fixed landmarks, entrances, exits, collision areas and an unobstructed action path.",
            crowd_rule,
            composition_rule,
        ])
    subject = _reference_subject(label, case)
    return " ".join([
        f"Create one clean 16:9 design reference sheet for <Picture {picture_index}> ({label}).",
        style,
        f"Primary design: {subject}.",
        f"The design must support this scene without showing the whole scene itself: {scene}",
        "Show a primary three-quarter view, a side silhouette, a rear silhouette and one close detail of the defining shape or material on a neutral background.",
        "Keep one exact design with measurable proportions and no alternate variants, no unrelated character, no environment, no text and no watermark.",
    ])


def _subject_records(case: dict[str, Any]) -> list[tuple[int, int, dict[str, str]]]:
    records = []
    subject_number = 0
    for picture_index, item in enumerate(case["refs"], start=1):
        if _is_storyboard_reference(item):
            continue
        subject_number += 1
        records.append((subject_number, picture_index, item))
    return records


def _is_environment_reference(label: str) -> bool:
    return "배경" in label or "공간" in label


def _subject_definition(case: dict[str, Any], subject_number: int, picture_index: int, item: dict[str, str]) -> str:
    label = str(item["label_ko"])
    role = str(item["instruction_en"]).strip().rstrip(".").removeprefix("defines ").removesuffix(" only")
    if case.get("storyboard_free"):
        short_id = str(case.get("short_id") or "")
        if _is_environment_reference(label):
            environment = ACTION_V2_ENVIRONMENT_DESCRIPTIONS.get(short_id)
            if environment:
                return f"<Subject {subject_number}> is {environment}, as shown in <Picture {picture_index}>."
        if short_id == "ra02" and subject_number == 1:
            subject = "a hand-drawn young woman with warm brown skin, a long dark side braid draped over one shoulder, a fitted teal jacket, an ochre scarf, charcoal trousers and brown boots"
        elif "캐릭터 A" in label:
            subject = "Character A, a young woman with warm brown skin, a long dark side braid draped over one shoulder, a fitted brick-red jacket, an ochre scarf, dark trousers and sturdy brown boots"
        elif "캐릭터 B" in label:
            subject = "Character B, a young man with light brown skin, short wavy blond hair, a cobalt-blue long coat, gray trousers, brown boots and one small silver ear cuff"
        elif any(token in label for token in ("주인공", "인간 캐릭터", "보호자")):
            subject = "the protagonist, a young woman with warm brown skin, a long dark side braid draped over one shoulder, a fitted teal field jacket, an ochre scarf, charcoal trousers and sturdy brown boots"
        else:
            subject = _reference_subject(label, case)
        return f"<Subject {subject_number}> is {subject}, as shown in <Picture {picture_index}>; preserve {role}."
    if _is_environment_reference(label):
        return (
            f"<Subject {subject_number}> is the visible environment shown in <Picture {picture_index}>, "
            f"with {role}."
        )
    return (
        f"<Subject {subject_number}> is {_reference_subject(label, case)}, as shown in <Picture {picture_index}>; "
        f"preserve {role}."
    )


def _subject_number_for_label(case: dict[str, Any], *tokens: str) -> int | None:
    for subject_number, _picture_index, item in _subject_records(case):
        label = str(item["label_ko"])
        if any(token in label for token in tokens):
            return subject_number
    return None


def _text_with_subject_labels(case: dict[str, Any], text: str) -> str:
    scene = str(text)
    for letter in "ABCDEF":
        subject_number = _subject_number_for_label(case, f"캐릭터 {letter}")
        if subject_number is not None:
            scene = re.sub(
                rf"\b(?:Character|Actor) {letter}\b",
                f"<Subject {subject_number}>",
                scene,
            )
    protagonist = _subject_number_for_label(case, "주인공", "인간 캐릭터")
    if protagonist is not None:
        scene = re.sub(r"\b[Tt]he protagonist\b", f"<Subject {protagonist}>", scene)
    protector = _subject_number_for_label(case, "보호자")
    if protector is not None:
        scene = re.sub(r"\b[Tt]he protector\b", f"<Subject {protector}>", scene)
    smaller = _subject_number_for_label(case, "작은 캐릭터·생물")
    if smaller is not None:
        scene = re.sub(r"\bthe smaller being\b", f"<Subject {smaller}>", scene, flags=re.IGNORECASE)
    return scene


def _scene_with_subject_labels(case: dict[str, Any]) -> str:
    scene = str(case.get("video_summary_en") or case["scene_en"])
    if len(_video_shots(case)) > 1:
        scene = re.sub(r"\s+without a cut\b", "", scene, flags=re.IGNORECASE)
        scene = re.sub(r"^In one wide shot,\s*", "Across the planned shot sequence, ", scene)
    return _text_with_subject_labels(case, scene)


def _storyboard_picture_index(case: dict[str, Any]) -> int:
    return next(
        index for index, item in enumerate(case["refs"], start=1)
        if _is_storyboard_reference(item)
    )


def _ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _shot_timestamp(case: dict[str, Any], index: int, count: int) -> str:
    seconds = float(case["duration"]) * index / count
    minutes = int(seconds // 60)
    remaining = seconds - minutes * 60
    return f"{minutes:02d}:{remaining:06.3f}"


def _dialogue_video_shot_beats(case: dict[str, Any]) -> list[str]:
    dialogue = _dialogue_entries(case)
    beats = []
    for speaker, line in dialogue:
        subject_number = ord(speaker) - ord("A") + 1
        next_subject = (subject_number % len(dialogue)) + 1
        beats.append(
            f"<Subject {subject_number}> (S{subject_number}) turns the eyes toward <Subject {next_subject}> "
            f"and says exactly once, <d>[Korean] {line}</d> Only this speaker's lips move; the mouth closes "
            "immediately after the line while every other character remains silent in the fixed position."
        )
    beats.append(
        "After the final line, every mouth remains closed and <Subject 1> gives one small readable silent nod. "
        "No character changes position, repeats dialogue or produces an unidentified voice."
    )
    return beats


def _video_shot_beats(case: dict[str, Any]) -> list[str]:
    short_id = str(case.get("short_id") or "")
    if short_id.startswith("rt"):
        return _dialogue_video_shot_beats(case)
    if case.get("storyboard_free"):
        return list(ACTION_V2_VIDEO_SHOT_BEATS.get(short_id) or [])
    return list(VIDEO_SHOT_BEATS.get(short_id) or [])


def _video_shots(case: dict[str, Any]) -> list[dict[str, str]]:
    explicit = list(case.get("video_shots") or [])
    short_id = str(case.get("short_id") or "")
    if explicit and short_id not in VIDEO_SHOT_BEATS:
        return explicit
    beats = _video_shot_beats(case)
    storyboard_free = bool(case.get("storyboard_free"))
    panel_count = len(beats) if storyboard_free else _storyboard_panel_count(case)
    if len(beats) != panel_count:
        raise ValueError(
            f"{case.get('short_id')}: video shot count {len(beats)} does not match planned shot count {panel_count}"
        )
    picture_index = None if storyboard_free else _storyboard_picture_index(case)
    shots = []
    for index, beat in enumerate(beats, start=1):
        if storyboard_free:
            composition = ""
        elif index == 1:
            composition = (
                f"The opening composition follows the 1st storyboard frame in <Picture {picture_index}>."
            )
        else:
            composition = (
                f"The cut follows the {_ordinal(index)} storyboard frame in <Picture {picture_index}>; "
                "identity, scale, screen direction and spatial continuity carry over from the preceding shot."
            )
        shots.append({
            "at": "" if index == 1 else _shot_timestamp(case, index - 1, panel_count),
            "description_en": " ".join(part for part in (composition, beat) if part),
        })
    return shots


def _shot_labels(case: dict[str, Any]) -> list[str]:
    shots = _video_shots(case)
    return [f"[Shot {index}]" for index in range(1, len(shots) + 1)] or ["[Shot 1]"]


def _shot_list_text(shot_labels: list[str]) -> str:
    if len(shot_labels) == 1:
        return shot_labels[0]
    if len(shot_labels) == 2:
        return f"{shot_labels[0]} and {shot_labels[1]}"
    return f"{', '.join(shot_labels[:-1])}, and {shot_labels[-1]}"


def _explicit_video_shot_lines(case: dict[str, Any]) -> list[str]:
    lines = []
    for index, shot in enumerate(_video_shots(case), start=1):
        timestamp = str(shot.get("at") or "").strip()
        prefix = f"[Shot {index}]" if index == 1 else f"[Shot {index}] At {timestamp},"
        description = _text_with_subject_labels(case, str(shot["description_en"]))
        subject_context = _natural_shot_subject_context(case, index, description)
        if index > 1:
            subject_context = subject_context[0].lower() + subject_context[1:]
        parts = [prefix]
        is_action_v2 = bool(case.get("storyboard_free"))
        short_id = str(case.get("short_id") or "")
        if not is_action_v2 or (index == 1 and short_id != "rs01"):
            parts.append(subject_context)
        parts.append(description)
        camera_cue = _shot_camera_cue(case, index, description)
        if camera_cue:
            parts.append(camera_cue)
        parts.append(_shot_sound_cue(case, description))
        lines.append(" ".join(parts))
    return lines


def _subject_narrative_descriptor(case: dict[str, Any], item: dict[str, str], later_shot: bool) -> str:
    label = str(item["label_ko"])
    same = "the same " if later_shot else "a "
    if _is_environment_reference(label):
        if case.get("storyboard_free"):
            environment = ACTION_V2_ENVIRONMENT_DESCRIPTIONS.get(str(case.get("short_id") or ""))
            if environment:
                return "the same referenced environment" if later_shot else environment
        return (
            "the same environment and fixed landmarks"
            if later_shot else "the referenced environment with stable geometry and fixed landmarks"
        )
    if "금속 열쇠" in label:
        return "the same round-bowed iron key" if later_shot else "a single worn iron key with a round bow and three asymmetrical teeth"
    if "에너지 장치" in label:
        return "the same two-electrode device" if later_shot else "a single dark-steel device with two copper electrodes"
    if "2D 검" in label:
        return "the same dark-blue sword" if later_shot else "a single dark-blue sword with a gold guard and red-wrapped grip"
    if str(case.get("short_id") or "") == "rd03" and "무기·소품" in label:
        return "the same red leather pouch" if later_shot else "a single red leather pouch with a brass ring"
    if "긴 무기" in label or "무기·소품" in label:
        return "the same long ashwood spear" if later_shot else "a single long ashwood spear with a steel leaf tip and blue hand wrap"
    if "적 공격 이미지" in label:
        return "the same obsidian-armored attacker" if later_shot else "an obsidian-armored attacker carrying one hooked blade"
    if "작은 캐릭터·생물" in label:
        return "the same ice-blue dragon hatchling" if later_shot else "an ice-blue dragon hatchling with charcoal horns and cyan wings"
    if "초거대 적" in label:
        return "the same basalt titan with amber fissures" if later_shot else "a colossal basalt titan with amber fissures and monolithic arms"
    if "비정형 괴수" in label or "촉수" in label:
        return "the same six-tentacled indigo monster" if later_shot else "an indigo monster with an armored core and six rooted tentacles"
    if "적 디자인" in label:
        return "the same obsidian-armored enemy" if later_shot else "an obsidian-armored enemy with an angular helmet and crimson sash"
    character_anchors = {
        "A": ("a woman with a short dark braid and brick-red jacket", "the same woman in the brick-red jacket"),
        "B": ("a man with wavy blond hair and a cobalt-blue coat", "the same man in the cobalt-blue coat"),
        "C": ("a woman with a long black ponytail and mustard vest", "the same woman in the mustard vest"),
        "D": ("a broad woman with shaved-side hair and a forest-green tunic", "the same woman in the forest-green tunic"),
        "E": ("a short man with curly auburn hair and a purple cloak", "the same man in the purple cloak"),
        "F": ("a tall older woman with a silver braid and white-gray coat", "the same older woman in the white-gray coat"),
    }
    match = re.search(r"캐릭터 ([A-F])(?: |$)", label)
    if match:
        if case.get("storyboard_free") and match.group(1) == "A":
            return "the same long-dark-braided woman in the brick-red jacket" if later_shot else "a long-dark-braided woman in a brick-red jacket and ochre scarf"
        first, later = character_anchors[match.group(1)]
        return later if later_shot else first
    if any(token in label for token in ("주인공", "인간 캐릭터", "보호자")):
        if case.get("storyboard_free"):
            return "the same teal-jacketed woman with a long dark side braid" if later_shot else "a long-dark-braided woman in a teal field jacket and ochre scarf"
        return (
            "the same teal-jacketed woman with a short dark braid"
            if later_shot else "a short-dark-braided woman in a teal field jacket and ochre scarf"
        )
    if case.get("storyboard_free") and str(case.get("short_id") or "") == "ra02":
        return "the same hand-drawn teal-jacketed woman with a long dark side braid" if later_shot else "a hand-drawn long-dark-braided woman in a teal jacket and ochre scarf"
    return "the same visually distinctive subject" if later_shot else "a visually distinctive subject with a stable silhouette, colors and materials"


def _natural_shot_subject_context(case: dict[str, Any], shot_index: int, description: str) -> str:
    records = _subject_records(case)
    environments = [row for row in records if _is_environment_reference(str(row[2]["label_ko"]))]
    visible = [row for row in records if row not in environments]
    dialogue = _dialogue_entries(case)
    if dialogue and str(case.get("short_id") or "").startswith("rt") and shot_index > 1:
        if shot_index <= len(dialogue):
            speaker = ord(dialogue[shot_index - 1][0]) - ord("A") + 1
            next_speaker = (speaker % len(dialogue)) + 1
            selected = {speaker, next_speaker}
        else:
            selected = {1}
        visible = [row for row in visible if row[0] in selected]
    elif shot_index > 1:
        mentioned = {
            int(value) for value in re.findall(r"<Subject (\d+)>", description)
        }
        non_character = {
            subject_number
            for subject_number, _picture_index, item in visible
            if not any(
                token in str(item["label_ko"])
                for token in ("캐릭터", "주인공", "인간", "보호자", "배우")
            )
        }
        selected = mentioned | non_character
        if not selected and visible:
            selected.add(visible[0][0])
        visible = [row for row in visible if row[0] in selected]
    phrases = [
        f"<Subject {subject_number}>, {_subject_narrative_descriptor(case, item, shot_index > 1)}"
        for subject_number, _picture_index, item in visible
    ]
    if not phrases:
        subject_clause = "the referenced subjects"
    elif len(phrases) == 1:
        subject_clause = phrases[0]
    elif len(phrases) == 2:
        subject_clause = f"{phrases[0]}, and {phrases[1]}"
    else:
        subject_clause = f"{', '.join(phrases[:-1])}, and {phrases[-1]}"
    action = "The opening composition establishes" if shot_index == 1 else "The new composition re-establishes"
    if environments:
        env_number, _picture_index, env_item = environments[0]
        env = f"<Subject {env_number}>, {_subject_narrative_descriptor(case, env_item, shot_index > 1)}"
        return f"{action} {subject_clause} within {env}."
    return f"{action} {subject_clause} in their planned positions."


def _shot_camera_cue(case: dict[str, Any], shot_index: int, description: str) -> str:
    text = description.lower()
    if "the camera " in text:
        return ""
    short_id = str(case.get("short_id") or "")
    if short_id.startswith("rt"):
        return "The camera holds a static medium close-up for the duration of this shot."
    if short_id in {"rs01", "rs02", "rs06", "rd01", "rd05", "rl02"}:
        return "The camera follows the movement with a tracking shot at fast speed."
    if short_id in {"rs03", "rs05", "rs09", "rd04", "ra03"}:
        return "The camera holds a static wide shot so the spatial relationships remain readable."
    if short_id in {"rs08", "rd02", "rd03", "rl01"}:
        return "The camera pushes in with small amplitude at normal speed toward the interaction point."
    if short_id in {"rs10", "rl03"}:
        return "The camera tracks forward at slow speed while keeping the lighting changes visible."
    if short_id in {"rs12", "rs11", "rs04", "rs07"}:
        return "The camera tracks laterally with small amplitude while preserving the action path."
    if short_id in {"ra01", "ra02"}:
        return "The camera holds a static medium shot so the drawn pose changes remain readable."
    if case.get("storyboard_free"):
        return "The camera holds a static medium shot at the viewpoint specified by this shot description."
    return "The camera holds a static medium shot at the viewpoint established by the storyboard."


def _shot_sound_cue(case: dict[str, Any], description: str) -> str:
    text = description.lower()
    if "<d>[korean]" in text:
        return "Quiet location tone and subtle clothing movement sit beneath the single synchronized Korean voice."
    cues = []
    if any(token in text for token in ("run", "sprint", "step", "foot", "land", "dodge")):
        cues.extend(["grounded footsteps", "breathing and cloth movement"])
    if any(token in text for token in ("attack", "block", "strike", "spear", "sword", "impact", "counterattack", "catch")):
        cues.append("directional movement swishes")
        if not any(token in text for token in ("passes through", "without contact", "before contact")):
            cues.append("synchronized contact or impact sound when contact occurs")
    if any(token in text for token in ("rain", "lightning")):
        cues.extend(["heavy rain", "thunder aligned with visible lightning"])
    if any(token in text for token in ("fire", "smoke")):
        cues.extend(["fire crackle", "moving air through smoke"])
    if any(token in text for token in ("debris", "crack", "collapse", "masonry")):
        cues.extend(["cracking structure", "falling debris"])
    if "crowd" in text or "market" in text:
        cues.append("spatially coherent market and crowd ambience")
    if any(token in text for token in ("device", "energy arc", "electrode")):
        cues.append("a contained electrical buzz attached to the device")
    if not cues:
        return "Coherent location ambience accompanies the subtle visible movement."
    joined = ", ".join(dict.fromkeys(cues))
    return "Audible details include " + joined + ", synchronized with the visible action."


def _shot_subject_context(case: dict[str, Any]) -> list[str]:
    lines = []
    for subject_number, _picture_index, item in _subject_records(case):
        label = str(item["label_ko"])
        role = str(item["instruction_en"]).strip().rstrip(".").removeprefix("defines ").removesuffix(" only")
        if _is_environment_reference(label):
            lines.append(f"The action takes place within <Subject {subject_number}>, retaining {role}.")
        else:
            appearance = _reference_subject(label, case)
            lines.append(f"<Subject {subject_number}> appears as {appearance}, retaining {role}.")
    return lines


def _soundscape(case: dict[str, Any]) -> str:
    if case.get("video_soundscape_en"):
        return str(case["video_soundscape_en"])
    scene = str(case["scene_en"]).lower()
    sounds = []
    if _dialogue_entries(case):
        sounds.extend(["clean synchronized Korean voices", "quiet room or location tone", "subtle clothing movement"])
    if any(token in scene for token in ("run", "sprint", "step", "dodge", "jump", "land")):
        sounds.extend(["grounded footsteps", "breathing and cloth movement"])
    if any(token in scene for token in ("attack", "block", "weapon", "sword", "contact", "counterattack")):
        sounds.extend(["movement swishes", "precise contact and impact sounds"])
    if "rain" in scene or "lightning" in scene:
        sounds.extend(["heavy rain", "distant thunder synchronized with the lightning"])
    if any(token in scene for token in ("fire", "smoke", "debris")):
        sounds.extend(["fire crackle", "airborne debris and falling fragments"])
    if any(token in scene for token in ("crack", "collapse")):
        sounds.extend(["cracking masonry", "falling rubble"])
    if "crowd" in scene:
        sounds.append("a spatially coherent crowd murmur")
    if not sounds:
        sounds.extend(["coherent environmental ambience", "physically synchronized movement and contact sounds"])
    sentence = ", ".join(dict.fromkeys(sounds)).replace("korean", "Korean")
    return sentence[0].upper() + sentence[1:] + ". No unrelated voices or narration."


def storyboard_beat_contract(case: dict[str, Any]) -> list[dict[str, Any]]:
    panel_count = _storyboard_panel_count(case)
    dialogue = _dialogue_entries(case)
    beats = []
    if dialogue:
        for panel_index, (speaker, line_ko) in enumerate(dialogue, start=1):
            subject_index = ord(speaker) - ord("A") + 1
            beats.append({
                "panel_index": panel_index,
                "beat_kind": "dialogue",
                "importance": "core",
                "subject_index": subject_index,
                "speaker_id": f"S{subject_index}",
                "line_ko": line_ko,
                "expectation_en": f"Subject {subject_index} speaks once and hands the gaze to the next speaker.",
            })
        for panel_index in range(len(dialogue) + 1, panel_count):
            beats.append({
                "panel_index": panel_index,
                "beat_kind": "post_dialogue_action",
                "importance": "core",
                "expectation_en": "All mouths stay closed while the prompted physical response continues.",
            })
        ending = (
            "Subject 2 completes the counterattack while Subject 1 holds the defensive end pose."
            if str(case.get("short_id") or "") == "rd06"
            else "All mouths close, positions stay fixed and Subject 1 completes one readable nod."
        )
        beats.append({
            "panel_index": panel_count,
            "beat_kind": "ending",
            "importance": "core",
            "expectation_en": ending,
        })
        return beats
    beats.append({
        "panel_index": 1,
        "beat_kind": "opening",
        "importance": "core",
        "expectation_en": "Establish the referenced opening composition, placement, scale, camera and pre-action state.",
    })
    if panel_count == 4:
        beats.extend([
            {
                "panel_index": 2,
                "beat_kind": "action_onset",
                "importance": "supporting",
                "expectation_en": "Initiate the first causal motion without reversing screen direction.",
            },
            {
                "panel_index": 3,
                "beat_kind": "key_interaction",
                "importance": "core",
                "expectation_en": "Show the referenced key interaction, contact, reversal or consequence.",
            },
        ])
    else:
        beats.append({
            "panel_index": 2,
            "beat_kind": "key_interaction",
            "importance": "core",
            "expectation_en": "Show the referenced central action, interaction or turning point.",
        })
    beats.append({
        "panel_index": panel_count,
        "beat_kind": "ending",
        "importance": "core",
        "expectation_en": "Reach the referenced resolved ending composition through continuous motion without a cut.",
    })
    return beats


def _dialogue_entries(case: dict[str, Any]) -> list[tuple[str, str]]:
    entries = []
    for item in case.get("dialogue") or []:
        if isinstance(item, dict):
            entries.append((str(item.get("speaker") or ""), str(item.get("line_ko") or "")))
        else:
            speaker, line = item
            entries.append((str(speaker), str(line)))
    return entries


def _dialogue_execution_lines(case: dict[str, Any]) -> list[str]:
    dialogue = _dialogue_entries(case)
    if not dialogue:
        return []
    if str(case.get("short_id") or "") == "rd06":
        return [
            "<Subject 1> (Character A) blocks one incoming attack while <Subject 2> (Character B) remains behind and ready to move.",
            "<Subject 1> (S1) maintains the defensive contact and warns exactly once, <d>[Korean] 뒤로 물러서!</d> The lips close immediately after the line while the block remains physically connected.",
            "<Subject 2> (S2) looks toward <Subject 1> and replies exactly once, <d>[Korean] 이번엔 내가 막을게!</d> Only <Subject 2>'s lips move during this response.",
            "After speaking, <Subject 2> closes the mouth, moves laterally along the established screen direction and performs one readable counterattack while <Subject 1> keeps the separate defensive role.",
        ]
    character_count = len(dialogue)
    lines = [
        f"Exactly {character_count} distinct characters hold readable fixed positions in a semicircle. "
        "The camera remains locked or moves extremely slowly."
    ]
    for index, (speaker, line) in enumerate(dialogue, start=1):
        subject_number = ord(speaker) - ord("A") + 1
        next_subject = (subject_number % len(dialogue)) + 1
        lines.append(
            f"<Subject {subject_number}> (S{subject_number}) turns the eyes toward <Subject {next_subject}> "
            f"and says once, <d>[Korean] {line}</d> Only this speaker's lips move; close them after the line."
        )
    lines.append(
        "After the last spoken line, every speaker remains silent and <Subject 1> gives one small, clearly readable nod. "
        "Do not add narration, overlapping speech, repeated dialogue or an unidentified voice."
    )
    return lines


def canonical_prompt(case: dict[str, Any]) -> str:
    subject_definitions = []
    retention_lines = []
    subject_labels = []
    storyboard_lines = []
    storyboard_labels = []
    storyboard_indexes = []
    shot_labels = _shot_labels(case)
    shot_list = _shot_list_text(shot_labels)
    for index, item in enumerate(case["refs"], start=1):
        instruction = str(item["instruction_en"]).strip().rstrip(".")
        reference_role = instruction.removeprefix("defines ").removesuffix(" only")
        if _is_storyboard_reference(item):
            storyboard_labels.append(f"<Picture {index}>")
            storyboard_indexes.append(index)
            storyboard_lines.append(
                f"<Picture {index}> is the storyboard reference for {shot_list}, defining "
                f"{reference_role} and the progression from the opening state "
                "to the resolved ending."
            )
            retention_lines.append(
                f"<Picture {index}> ({shot_list} storyboard structure): fully_preserved - "
                "Preserve its viewpoint, blocking, screen direction, action timing and ending composition."
            )
            continue
        subject_number = len(subject_labels) + 1
        subject_labels.append(f"<Subject {subject_number}>")
        subject_definitions.append(_subject_definition(case, subject_number, index, item))
        retention_lines.append(
            f"<Subject {subject_number}> (appears in {shot_list}): fully_preserved - "
            f"Preserve {reference_role}."
        )
    scene = _scene_with_subject_labels(case)
    storyboard_reference = storyboard_labels[0] if storyboard_labels else ""
    summary = f"[reference generation] {scene}"
    if storyboard_reference:
        summary += f" The viewpoint, staging and temporal progression follow {storyboard_reference}."
    dialogue_lines = _dialogue_execution_lines(case)
    shot_lines = dialogue_lines or [scene]
    storyboard_direction = (
        f"The viewpoint, subject placement, screen direction, action timing and ending composition follow "
        f"<Picture {storyboard_indexes[0]}>."
        if storyboard_indexes else ""
    )
    explicit_shot_lines = _explicit_video_shot_lines(case)
    if explicit_shot_lines:
        detailed_lines = explicit_shot_lines
    else:
        detailed_lines = [
            "[Shot 1] The entire event unfolds as one continuous shot with stable identity, spatial continuity and physical causality.",
            *_shot_subject_context(case),
            storyboard_direction,
            *shot_lines,
            "Movement connects naturally from the established opening state to the resolved final composition without a cut.",
        ]
    return "\n".join([
        "subject_definitions:",
        *subject_definitions,
        *storyboard_lines,
        "",
        "summary:",
        summary,
        "",
        "retention_analysis:",
        *retention_lines,
        "",
        "detailed_description:",
        _video_style_instruction(case),
        *detailed_lines,
        "",
        "overall_soundscape:",
        _soundscape(case),
        "",
        "non_diegetic_music:",
        "N/A",
    ])


def _requirement_label(description: str) -> str:
    return str(description or "").partition("·")[2].strip()


def _sync_reference_asset_roles(connection, case_version: str, refs: list[dict[str, str]]) -> None:
    desired_roles = {
        str(item["label_ko"]): f"reference_image_{index}"
        for index, item in enumerate(refs, start=1)
    }
    rows = connection.execute(
        """SELECT link.asset_id,link.role,link.ordering,requirement.description
           FROM benchmark_case_assets link
           LEFT JOIN benchmark_case_asset_requirements requirement
             ON requirement.case_version_id=link.case_version_id
            AND requirement.role=link.role
           WHERE link.case_version_id=?""",
        (case_version,),
    ).fetchall()
    moves = []
    for row in rows:
        label = _requirement_label(row["description"])
        desired_role = desired_roles.get(label)
        if desired_role == row["role"]:
            continue
        if desired_role is None:
            if _is_storyboard_reference({"label_ko": label, "instruction_en": ""}):
                connection.execute(
                    "DELETE FROM benchmark_case_assets WHERE case_version_id=? AND role=? AND ordering=?",
                    (case_version, row["role"], row["ordering"]),
                )
            continue
        temporary_role = f"__r2v_reference_sync_{len(moves) + 1}"
        connection.execute(
            """UPDATE benchmark_case_assets SET role=?
               WHERE case_version_id=? AND role=? AND ordering=?""",
            (temporary_role, case_version, row["role"], row["ordering"]),
        )
        moves.append((temporary_role, desired_role, row["ordering"]))
    for temporary_role, desired_role, ordering in moves:
        connection.execute(
            """UPDATE benchmark_case_assets SET role=?
               WHERE case_version_id=? AND role=? AND ordering=?""",
            (desired_role, case_version, temporary_role, ordering),
        )


def _reference_slot_contract(case: dict[str, Any], item: dict[str, str], index: int) -> dict[str, Any]:
    base = {
        "role": f"reference_image_{index}",
        "picture_index": index,
        **item,
        "reference_kind": "storyboard" if _is_storyboard_reference(item) else "visual_reference",
    }
    if not case.get("storyboard_free"):
        base.update({
            "storyboard_panel_count": _storyboard_panel_count(case) if _is_storyboard_reference(item) else None,
            "storyboard_reading_order": "left_to_right_then_top_to_bottom" if _is_storyboard_reference(item) else None,
            "storyboard_beats": storyboard_beat_contract(case) if _is_storyboard_reference(item) else [],
        })
    base.update({
        "shared_asset_key": shared_asset_key(case, item) or None,
        "image_generation_prompt": reference_image_prompt(case, item, index),
    })
    return base


def _prompt_only_shot_guidance(case: dict[str, Any]) -> list[dict[str, Any]]:
    if not case.get("storyboard_free"):
        return []
    return [
        {
            "shot_index": index,
            "at": str(shot.get("at") or "opening"),
            "description_en": _text_with_subject_labels(case, str(shot["description_en"])),
        }
        for index, shot in enumerate(_video_shots(case), start=1)
    ]


def ensure_suites(connection) -> None:
    action_cases = [case for case in CASES if not case["short_id"].startswith("rt")]
    action_cases = sorted(action_cases, key=lambda case: {"stylized_3d": 0, "live_action": 1, "hand_drawn_2d": 2}.get(str(case.get("visual_style") or "stylized_3d"), 9))
    action_v2 = sorted(action_v2_cases(), key=lambda case: {"stylized_3d": 0, "live_action": 1, "hand_drawn_2d": 2}.get(str(case.get("visual_style") or "stylized_3d"), 9))
    suite_defs = [
        (ACTION_SUITE_ID, 1, "MiniMax H3 R2V 액션 스트레스", "등록 완료 3D 기준 뒤에 실사와 정통 2D 장르 테스트를 분리해 진단한다.", action_cases, False),
        (ACTION_V2_SUITE_ID, 2, "MiniMax H3 R2V 액션 스트레스", "스토리보드 이미지 없이 캐릭터·배경·소품 참조와 텍스트 멀티샷 계획만으로 동일한 24개 액션을 진단한다.", action_v2, True),
        (TURN_SUITE_ID, 1, "MiniMax H3 R2V 티키타카 스트레스", "2명부터 6명까지 화자 순환의 안정 한계를 측정한다.", [case for case in CASES if case["short_id"].startswith("rt")], False),
    ]
    for suite_id, suite_version, name, description, cases, is_action_v2 in suite_defs:
        definition = {"suite_id": suite_id, "cases": [case["short_id"] for case in cases]}
        connection.execute(
            """INSERT OR IGNORE INTO benchmark_suites
               (suite_id,name,version,description,tier,definition_sha256)
               VALUES (?,?,?,?,'model_specific_stress',?)""",
            (suite_id, name, suite_version, description, _sha(definition)),
        )
        connection.execute(
            "UPDATE benchmark_suites SET name=?,version=?,description=?,definition_sha256=?,active=1 WHERE suite_id=?",
            (name, suite_version, description, _sha(definition), suite_id),
        )
        connection.execute("DELETE FROM suite_cases WHERE suite_id=?", (suite_id,))
        for ordering, case in enumerate(cases, start=1):
            cid = action_v2_case_id(case["short_id"]) if is_action_v2 else case_id(case["short_id"])
            cvid = action_v2_case_version_id(case["short_id"]) if is_action_v2 else case_version_id(case["short_id"])
            parameters = dict(case.get("parameters") or {})
            contract = {
                "input_mode": "h3_r2v_multi_reference",
                "visual_style": str(case.get("visual_style") or "stylized_3d"),
                "reference_slots": [
                    _reference_slot_contract(case, item, index)
                    for index, item in enumerate(case["refs"], start=1)
                ],
                "prompt_only_shot_guidance": _prompt_only_shot_guidance(case),
                "required_events": case["required"],
                "forbidden_failures": case["forbidden"],
                "scoring_dimensions": [case["category"], "reference_adherence", "prompt_adherence", "temporal_quality"],
                "generation": {"target_seconds": case["duration"], "fps": 24, "width": 832, "height": 480},
                "parameters": parameters,
                "dialogue": list(case.get("dialogue") or []),
            }
            if is_action_v2:
                contract["shot_plan_source"] = "prompt_only_text"
            definition = {"title": case["title"], "intent_ko": case["intent_ko"], "contract": contract, "prompt": canonical_prompt(case)}
            tags = ["minimax_h3", "r2v", case["tier"]]
            if is_action_v2:
                tags.append("no_storyboard")
            connection.execute(
                """INSERT OR IGNORE INTO benchmark_cases
                   (case_id,title,intent_ko,intent_json,category,tags_json,source_kind)
                   VALUES (?,?,?,?,?,?,'minimax_h3_r2v_benchmark')""",
                (cid, case["title"], case["intent_ko"], _json(contract), case["category"], _json(tags)),
            )
            connection.execute(
                "UPDATE benchmark_cases SET title=?,intent_ko=?,intent_json=?,category=?,tags_json=? WHERE case_id=?",
                (case["title"], case["intent_ko"], _json(contract), case["category"], _json(tags), cid),
            )
            connection.execute(
                """INSERT OR IGNORE INTO benchmark_case_versions
                   (case_version_id,case_id,version,title,intent_ko,category,tier,contract_json,definition_sha256)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (cvid, cid, suite_version, case["title"], case["intent_ko"], case["category"], case["tier"], _json(contract), _sha(definition)),
            )
            connection.execute(
                "UPDATE benchmark_case_versions SET title=?,intent_ko=?,category=?,tier=?,contract_json=?,definition_sha256=? WHERE case_version_id=?",
                (case["title"], case["intent_ko"], case["category"], case["tier"], _json(contract), _sha(definition), cvid),
            )
            prompt = canonical_prompt(case)
            connection.execute(
                """INSERT OR REPLACE INTO benchmark_case_prompts
                   (case_version_id,language,prompt_kind,prompt_text,prompt_sha256)
                   VALUES (?,'en','canonical',?,?)""",
                (cvid, prompt, hashlib.sha256(prompt.encode("utf-8")).hexdigest()),
            )
            _sync_reference_asset_roles(connection, cvid, case["refs"])
            connection.execute("DELETE FROM benchmark_case_asset_requirements WHERE case_version_id=?", (cvid,))
            for index, item in enumerate(case["refs"], start=1):
                connection.execute(
                    """INSERT INTO benchmark_case_asset_requirements
                       (case_version_id,role,kind,minimum_count,description)
                       VALUES (?,?, 'image',1,?)""",
                    (cvid, f"reference_image_{index}", f"<Picture {index}> · {item['label_ko']}"),
                )
            connection.execute(
                "INSERT INTO suite_cases(suite_id,case_version_id,ordering,enabled) VALUES (?,?,?,1)",
                (suite_id, cvid, ordering),
            )


def _project_case_ids(project_id: str, clip_id: str) -> tuple[str, str]:
    token = re.sub(r"[^a-z0-9]+", "_", str(clip_id or "").lower()).strip("_")
    if project_id == DRAGON_SEASON_1_PROJECT_ID:
        case_id = f"raising_dragon_s01_{token}"
    else:
        project_token = hashlib.sha256(str(project_id).encode("utf-8")).hexdigest()[:12]
        case_id = f"h3_project_{project_token}_{token}"
    return case_id, f"{case_id}_v1"


def _project_reference_path(project_dir: Path, source_path: str) -> Path:
    base = project_dir.resolve()
    path = (base / str(source_path or "")).resolve()
    if base not in path.parents or not path.is_file():
        raise FileNotFoundError(f"H3 프로젝트 Picture를 찾을 수 없습니다: {source_path}")
    return path


def registered_project_targets(root: Path) -> list[dict[str, Any]]:
    """Return the newest registration for each project/scope pair.

    Schema 1 records predate scoped registrations and therefore continue to
    mean the complete live project.  Schema 2 records pin suite membership to
    the clip IDs captured when the user registered the test set.
    """
    targets: dict[tuple[str, str | None], tuple[tuple[str, str, str], dict[str, Any]]] = {}
    base = root / "runtime/h3/project_test_sets"
    if base.is_dir():
        for path in base.glob("*/project_test_set.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if (
                payload.get("deleted")
                or payload.get("deleted_at")
                or payload.get("status") == "deleted"
            ):
                continue
            project_id = str(payload.get("project_id") or "").strip()
            if not project_id:
                continue
            try:
                schema_version = int(payload.get("schema_version") or 1)
            except (TypeError, ValueError):
                schema_version = 1
            generation_mode = (
                str(payload.get("generation_mode") or "r2v").strip().lower()
                if schema_version >= 3
                else "r2v"
            )
            if generation_mode != "r2v":
                continue
            scope = str(payload.get("scope") or "project") if schema_version >= 2 else "project"
            scene_id = (
                str(payload.get("scene_id") or "").strip() or None
                if scope == "scene"
                else None
            )
            clip_ids: list[str] | None = None
            if schema_version >= 2:
                raw_clip_ids = payload.get("clip_ids")
                if not isinstance(raw_clip_ids, list):
                    raw_clip_ids = [
                        row.get("clip_id")
                        for row in (payload.get("clips") or [])
                        if isinstance(row, dict)
                    ]
                clip_ids = list(dict.fromkeys(
                    str(value or "").strip()
                    for value in raw_clip_ids
                    if str(value or "").strip()
                ))
            target = {
                "project_id": project_id,
                "scene_id": scene_id,
                "clip_ids": clip_ids,
                "schema_version": schema_version,
                "generation_mode": "r2v",
                "project_test_set_id": str(payload.get("project_test_set_id") or path.parent.name),
            }
            rank = (
                str(payload.get("created_at") or payload.get("updated_at") or ""),
                str(payload.get("updated_at") or payload.get("created_at") or ""),
                str(payload.get("project_test_set_id") or path.parent.name),
            )
            key = (project_id, scene_id)
            current = targets.get(key)
            if current is None or rank > current[0]:
                targets[key] = (rank, target)
    return [
        targets[key][1]
        for key in sorted(targets, key=lambda row: (row[0], row[1] or ""))
    ]


# Kept as a private compatibility alias for callers predating deletion support.
_registered_project_targets = registered_project_targets


def ensure_project_suite(
    root: Path,
    connection,
    project_id: str,
    scene_id: str | None = None,
    clip_ids: list[str] | None = None,
) -> dict[str, Any] | None:
    """Expose one authored H3 project as a project-specific R2V benchmark suite.

    The canonical video prompt is copied byte-for-byte from each project clip,
    while Picture assets are content-addressed into the evaluation asset store.
    No generation job or H3 production queue item is created here.
    """
    project_id = str(project_id or "").strip()
    scene_id = str(scene_id or "").strip() or None
    suite_id = (
        project_scene_suite_id(project_id, scene_id)
        if scene_id
        else project_suite_id(project_id)
    )
    project_dir = h3_prompt_projects.project_dir(root, project_id)
    if not project_dir.is_dir():
        return None
    overview = h3_prompt_projects.project_clips(root, project_id)
    clips = list(overview.get("clips") or [])
    if scene_id:
        clips = [
            clip for clip in clips
            if str(clip.get("scene_id") or "") == scene_id
        ]
    if clip_ids is not None:
        clips_by_id = {
            str(clip.get("clip_id") or ""): clip
            for clip in clips
        }
        clips = [
            clips_by_id[clip_id]
            for clip_id in clip_ids
            if clip_id in clips_by_id
        ]
    if not clips:
        return None
    project = next(
        (row for row in h3_prompt_projects.list_projects(root).get("projects") or [] if row.get("project_id") == project_id),
        {"title": project_id},
    )
    signature_rows = []
    expected_links = 0
    for clip in clips:
        refs = []
        for row in clip.get("references") or []:
            asset_signature: dict[str, Any] = {
                "picture_index": row.get("picture_index"),
                "role": row.get("role"),
                "label": row.get("label"),
                "description": row.get("description"),
                "source_path": row.get("source_path"),
                "linked": row.get("linked"),
            }
            if row.get("linked"):
                path = _project_reference_path(project_dir, str(row.get("source_path") or ""))
                stat = path.stat()
                asset_signature.update(size_bytes=stat.st_size, modified_ns=stat.st_mtime_ns)
                expected_links += 1
            refs.append(asset_signature)
        signature_rows.append({
            "scene_id": clip.get("scene_id"), "clip_id": clip.get("clip_id"),
            "sequence": clip.get("sequence"), "duration_seconds": clip.get("duration_seconds"),
            "video_prompt": clip.get("video_prompt"), "references": refs,
        })
    definition_sha = _sha({"suite_id": suite_id, "project_id": project_id, "clips": signature_rows})
    current = connection.execute(
        "SELECT definition_sha256 FROM benchmark_suites WHERE suite_id=?",
        (suite_id,),
    ).fetchone()
    case_count = connection.execute(
        "SELECT COUNT(*) count FROM suite_cases WHERE suite_id=? AND enabled=1",
        (suite_id,),
    ).fetchone()["count"] if current else 0
    linked_count = connection.execute(
        """SELECT COUNT(*) count FROM benchmark_case_assets a
           JOIN suite_cases s ON s.case_version_id=a.case_version_id
           WHERE s.suite_id=? AND s.enabled=1""",
        (suite_id,),
    ).fetchone()["count"] if current else 0
    if current and current["definition_sha256"] == definition_sha and int(case_count) == len(clips) and int(linked_count) == expected_links:
        connection.execute(
            "UPDATE benchmark_suites SET active=1 WHERE suite_id=?",
            (suite_id,),
        )
        return {
            "suite_id": suite_id,
            "project_id": project_id,
            "scene_id": scene_id,
            "case_count": len(clips),
            "asset_count": expected_links,
            "changed": False,
        }

    if scene_id:
        name = f"{project.get('title') or project_id} · {scene_id} 씬 · {project_id}"
    elif project_id == DRAGON_SEASON_1_PROJECT_ID:
        name = "용 키우기 시즌 1 · 전체 씬·클립"
    else:
        name = f"{project.get('title') or project_id} · 전체 씬·클립 · {project_id}"
    scene_count = len({str(clip.get("scene_id") or "") for clip in clips})
    description = (
        f"01 H3 생성 프로젝트의 {scene_id} 씬과 전체 클립을 "
        "원본 프롬프트·Picture 구성 그대로 검증한다."
        if scene_id
        else f"01 H3 생성 프로젝트의 {scene_count}개 씬과 전체 클립을 원본 프롬프트·Picture 구성 그대로 검증한다."
    )
    connection.execute(
        """INSERT INTO benchmark_suites
           (suite_id,name,version,description,tier,definition_sha256,active)
           VALUES (?,?,1,?,'project_validation',?,1)
           ON CONFLICT(suite_id) DO UPDATE SET name=excluded.name,version=excluded.version,
           description=excluded.description,tier=excluded.tier,
           definition_sha256=excluded.definition_sha256,active=1""",
        (suite_id, name, description, definition_sha),
    )
    connection.execute("DELETE FROM suite_cases WHERE suite_id=?", (suite_id,))
    for ordering, clip in enumerate(clips, start=1):
        case_id, case_version_id = _project_case_ids(project_id, str(clip["clip_id"]))
        references = list(clip.get("references") or [])
        reference_slots = [{
            "picture_index": index,
            "role": f"reference_image_{index}",
            "label_ko": str(row.get("label") or row.get("role") or f"Picture {index}"),
            "description_en": str(row.get("description") or ""),
            "instruction_en": str(row.get("instruction_en") or ""),
            "reference_kind": str(row.get("reference_kind") or "visual_reference"),
            "source_project_path": str(row.get("source_path") or ""),
            "image_generation_prompt": "",
            **(
                {
                    "storyboard_panel_count": int(row.get("storyboard_panel_count") or 0),
                    "storyboard_reading_order": str(row.get("storyboard_reading_order") or ""),
                    "storyboard_beats": list(row.get("storyboard_beats") or []),
                }
                if str(row.get("reference_kind") or "") == "storyboard"
                else {}
            ),
        } for index, row in enumerate(references, start=1)]
        storyboard_review = dict(clip.get("storyboard_review_contract") or {})
        storyboard_slots = [
            row for row in reference_slots
            if row.get("reference_kind") == "storyboard"
        ]
        storyboard_beats = [
            beat
            for slot in storyboard_slots
            for beat in (slot.get("storyboard_beats") or [])
            if isinstance(beat, dict)
        ]
        required_events = [
            str(beat.get("required_state_ko") or beat.get("description_ko") or "").strip()
            for beat in storyboard_beats
            if str(beat.get("required_state_ko") or beat.get("description_ko") or "").strip()
        ] or ["원본 H3 프롬프트의 사건 순서, 인물 역할과 종료 상태를 재현"]
        forbidden_failures = [
            str(value).strip()
            for value in (storyboard_review.get("hard_failures") or [])
            if str(value).strip()
        ] or ["참조 캐릭터 정체성 변경", "배경·소품 불연속", "행동 순서 누락", "의도하지 않은 장면 전환"]
        intent_ko = (
            f"{clip['scene_id']}의 {clip['clip_id']} 클립을 프로젝트 원본 프롬프트와 참조 이미지로 재현한다. "
            f"{str(clip.get('review_intent_ko') or '').strip()}"
        ).strip()
        contract = {
            "input_mode": "h3_r2v_multi_reference",
            "visual_style": "stylized_3d",
            "source_project_id": project_id,
            "source_scene_id": clip["scene_id"],
            "source_clip_id": clip["clip_id"],
            "reference_slots": reference_slots,
            "shot_plan_source": (
                "storyboard_reference_and_canonical_prompt"
                if storyboard_slots else "canonical_prompt_text"
            ),
            "required_events": required_events,
            "forbidden_failures": forbidden_failures,
            "scoring_dimensions": (
                ["storyboard_adherence", "panel_sequence_fidelity", "camera_path_transition", "action_flow", "action_pacing", "event_execution", "emotional_progression", "character_identity", "visual_temporal_quality"]
                if storyboard_slots
                else ["scenario_comprehension", "prompt_adherence", "motion_physics", "character_identity", "scene_continuity", "camera_direction", "visual_temporal_quality"]
            ),
            "storyboard_review_contract": storyboard_review,
            "prompt_only_shot_guidance": [
                {
                    "shot_index": int(beat.get("panel_index") or index),
                    "description_ko": str(beat.get("required_state_ko") or beat.get("description_ko") or ""),
                }
                for index, beat in enumerate(storyboard_beats, start=1)
            ],
            "generation": {"target_seconds": float(clip["duration_seconds"]), "fps": 24, "width": 832, "height": 480},
            "parameters": {},
            "dialogue": [],
        }
        title = f"{clip['clip_id']} · {project.get('title') or '용 키우기 시즌 1'}"
        prompt = str(clip["video_prompt"])
        definition = {"title": title, "intent_ko": intent_ko, "contract": contract, "prompt": prompt}
        tags = ["minimax_h3", "r2v", "project_validation", project_id, str(clip["scene_id"])]
        connection.execute(
            """INSERT INTO benchmark_cases
               (case_id,title,intent_ko,intent_json,category,tags_json,source_kind)
               VALUES (?,?,?,?,? ,?,'h3_prompt_project')
               ON CONFLICT(case_id) DO UPDATE SET title=excluded.title,intent_ko=excluded.intent_ko,
               intent_json=excluded.intent_json,category=excluded.category,tags_json=excluded.tags_json""",
            (case_id, title, intent_ko, _json(contract), "r2v_project_clip", _json(tags)),
        )
        connection.execute(
            """INSERT INTO benchmark_case_versions
               (case_version_id,case_id,version,title,intent_ko,category,tier,contract_json,definition_sha256)
               VALUES (?,?,1,?,?,?,'project_validation',?,?)
               ON CONFLICT(case_version_id) DO UPDATE SET title=excluded.title,intent_ko=excluded.intent_ko,
               category=excluded.category,tier=excluded.tier,contract_json=excluded.contract_json,
               definition_sha256=excluded.definition_sha256""",
            (case_version_id, case_id, title, intent_ko, "r2v_project_clip", _json(contract), _sha(definition)),
        )
        connection.execute(
            """INSERT OR REPLACE INTO benchmark_case_prompts
               (case_version_id,language,prompt_kind,prompt_text,prompt_sha256)
               VALUES (?,'en','canonical',?,?)""",
            (case_version_id, prompt, hashlib.sha256(prompt.encode("utf-8")).hexdigest()),
        )
        connection.execute("DELETE FROM benchmark_case_assets WHERE case_version_id=?", (case_version_id,))
        connection.execute("DELETE FROM benchmark_case_asset_requirements WHERE case_version_id=?", (case_version_id,))
        for index, row in enumerate(references, start=1):
            role = f"reference_image_{index}"
            connection.execute(
                """INSERT INTO benchmark_case_asset_requirements
                   (case_version_id,role,kind,minimum_count,description)
                   VALUES (?,?,'image',1,?)""",
                (case_version_id, role, f"<Picture {index}> · {row.get('label') or row.get('role') or role}"),
            )
            if row.get("linked"):
                asset_path = _project_reference_path(project_dir, str(row.get("source_path") or ""))
                model_test_assets.save_and_link(root, connection, {
                    "case_version_id": case_version_id,
                    "role": role,
                    "upload_path": str(asset_path),
                    "original_name": asset_path.name,
                })
        connection.execute(
            "INSERT INTO suite_cases(suite_id,case_version_id,ordering,enabled) VALUES (?,?,?,1)",
            (suite_id, case_version_id, ordering),
        )
    connection.commit()
    return {
        "suite_id": suite_id,
        "project_id": project_id,
        "scene_id": scene_id,
        "case_count": len(clips),
        "asset_count": expected_links,
        "changed": True,
    }


def ensure_dragon_season_1_suite(root: Path, connection) -> dict[str, Any] | None:
    """Keep the original Official project suite and its IDs backward compatible."""
    return ensure_project_suite(root, connection, DRAGON_SEASON_1_PROJECT_ID)


def ensure_registered_project_suites(root: Path, connection) -> list[dict[str, Any]]:
    """Synchronize project-wide and scene-scoped H3 test registrations."""
    connection.execute(
        "UPDATE benchmark_suites SET active=0 "
        "WHERE suite_id GLOB ? OR suite_id GLOB ?",
        (f"{PROJECT_SUITE_PREFIX}*", f"{SCENE_SUITE_PREFIX}*"),
    )
    results = []
    for target in registered_project_targets(root):
        project_id = str(target["project_id"])
        scene_id = target.get("scene_id")
        if project_id == DRAGON_SEASON_1_PROJECT_ID and scene_id is None:
            continue
        result = ensure_project_suite(
            root,
            connection,
            project_id,
            scene_id,
            target.get("clip_ids"),
        )
        if result:
            result["project_test_set_id"] = target["project_test_set_id"]
            results.append(result)
    return results
