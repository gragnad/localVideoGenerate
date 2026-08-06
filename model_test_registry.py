from __future__ import annotations

"""Model-neutral benchmark registry and test-session planning."""

import hashlib
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import evaluation_db
import model_test_assets
import model_test_r2v
import workflow_adapter

PROFILE_KINDS = {"official_baseline", "controlled_variant", "optimized_variant"}
DEFAULT_TEST_RESOLUTION = {"width": 768, "height": 432}
TEST_RESOLUTION_PRESETS = (
    (512, 288), (768, 432), (832, 480), (960, 544), (1024, 576),
    (1280, 704), (1344, 768), (1536, 864),
)
DEFAULT_SUITE_ID = "video_model_diagnostic_v1"
I2V_SUITE_ID = "video_model_diagnostic_i2v_fixed_anchor_v1"
DEFAULT_CASES = [
    ("empty_environment", "캐릭터 없는 환경", "environment", "smoke", "빈 공간의 구조와 조명을 유지하며 카메라가 천천히 전진한다.", ["캐릭터가 생성되지 않는다", "공간 구조가 유지된다"], ["인물의 임의 출현", "배경 구조의 순간 변경"]),
    ("single_identity", "단일 캐릭터 정체성", "character_identity", "diagnostic", "한 캐릭터가 고개를 돌리고 몇 걸음 이동하는 동안 외형과 의상을 유지한다.", ["얼굴과 의상 유지", "자연스러운 신체 이동"], ["외형 교체", "팔다리 변형"]),
    ("two_subject_separation", "두 캐릭터 구분", "character_identity", "diagnostic", "서로 다른 두 캐릭터가 떨어져 서서 각자 한 번씩 반응한다.", ["두 정체성 구분", "위치와 역할 유지"], ["얼굴·의상 혼합", "복제 또는 누락"]),
    ("reference_following", "이미지 참조 반영", "reference_adherence", "diagnostic", "참조 이미지의 피사체, 의상, 주요 색상과 비율을 영상에서 유지한다.", ["주요 참조 특징 유지"], ["참조 특징 소실", "종족 또는 연령 변경"]),
    ("ground_contact", "낙상과 지면 접촉", "motion_physics", "diagnostic", "달리던 인물이 미끄러져 무게중심을 잃고 바닥에 손을 짚은 뒤 일어난다.", ["발과 지면 접촉", "무게중심 붕괴", "충돌 반응"], ["공중 부양", "충돌 없는 이동"]),
    ("hand_prop_contact", "손과 소품 상호작용", "interaction", "diagnostic", "인물이 탁자 위 물건을 손으로 집어 들어 형태와 소유 관계를 유지한다.", ["손과 물건 접촉", "물건 형태 유지"], ["손 관통", "소품 흡수·소실"]),
    ("two_subject_handoff", "두 인물 간 물건 전달", "interaction", "stress", "첫 인물이 물건을 건네고 두 번째 인물이 받아 든다.", ["소유자가 한 번만 변경", "전달 순서 유지"], ["소품 복제", "접촉 없는 순간 이동"]),
    ("camera_action", "카메라 이동과 행동", "camera_direction", "diagnostic", "카메라가 천천히 측면 이동하는 동안 인물이 목표물을 발견하고 몸을 돌린다.", ["카메라와 행동 구분", "피사체 추적 유지"], ["과도한 카메라 가속", "행동 누락"]),
    ("anchor_start", "시작 앵커 충실도", "reference_adherence", "diagnostic", "시작 이미지의 구도와 공간 배치를 유지한 채 피사체가 자연스럽게 움직이기 시작한다.", ["첫 장면의 구도·배치 유지", "자연스러운 초기 동작"], ["시작 이미지 무시", "첫 프레임의 급격한 구도 변경"]),
    ("spatial_continuity", "공간과 장면 연속성", "scene_continuity", "diagnostic", "같은 공간 안에서 전경에서 후경으로 이동하며 출입구와 주요 소품 위치를 유지한다.", ["공간 배치 유지", "이동 경로 연속"], ["배경 교체", "출입구 방향 역전"]),
    ("occlusion_return", "가림 뒤 정체성 유지", "character_identity", "stress", "인물이 기둥 뒤로 잠시 가려졌다가 다시 나타난다. 얼굴, 의상, 신체 비율과 진행 방향을 유지한다.", ["가림 전후 정체성 유지", "진행 방향 유지"], ["다른 인물로 교체", "의상·얼굴 변화"]),
    ("lighting_material", "조명·재질 연속성", "visual_temporal_quality", "diagnostic", "한 공간에서 카메라가 천천히 움직이는 동안 금속 소품과 젖은 바닥의 재질, 방향성 조명을 안정적으로 유지한다.", ["재질과 반사 유지", "조명 방향 유지"], ["질감 깜빡임", "재질·조명 급변"]),
    ("korean_dialogue", "한국어 대사와 화자", "dialogue_audio", "diagnostic", "두 인물이 차례로 짧은 한국어 대사를 말하며 화자와 입 모양을 구분한다.", ["자연스러운 한국어", "화자 순서 유지"], ["다른 언어", "대사 중복·화자 혼합"]),
    ("prop_persistence", "특수 소품 유지", "background_props", "diagnostic", "독특한 소품을 든 인물이 이동하는 동안 소품의 형태, 재질과 소유 관계를 유지한다.", ["소품 정체성 유지"], ["소품 변형·복제·소실"]),
    ("entry_exit", "인물 등장·퇴장", "scene_continuity", "stress", "한 인물이 화면 왼쪽에서 들어와 중앙의 다른 인물에게 다가간 뒤, 두 번째 인물이 화면 오른쪽으로 퇴장한다.", ["등장·퇴장 순서", "두 인물의 역할 유지"], ["인물 복제·누락", "출현 위치 도약"]),
    ("long_temporal", "15~20초 장기 연속성", "visual_temporal_quality", "stress", "하나의 공간에서 발견, 접근, 상호작용, 반응의 네 사건을 순서대로 연결한다.", ["사건 순서 유지", "장기 외형과 공간 유지"], ["사건 순서 변경", "후반 품질 붕괴"]),
    ("action_level_1", "액션 강도 1 · 절제된 제스처", "motion_physics", "diagnostic", "인물이 제자리에서 몸을 돌리고 손을 뻗어 가까운 목표물을 가리킨 뒤 자연스럽게 자세를 안정시킨다.", ["느린 방향 전환", "손·시선·몸의 일치", "안정된 종료 자세"], ["손가락·팔 왜곡", "불필요한 순간 이동", "과도한 카메라 이동"]),
    ("action_level_2", "액션 강도 2 · 빠른 접근과 정지", "motion_physics", "diagnostic", "인물이 짧은 거리를 빠르게 달려 목표물 앞에서 감속하고 두 발로 균형 있게 멈춘다.", ["가속·감속 구분", "발의 지면 접촉", "정지 후 균형"], ["공중 미끄러짐", "발 위치 도약", "충돌 없는 급정지"]),
    ("action_level_3", "액션 강도 3 · 도약과 착지", "motion_physics", "stress", "인물이 낮은 장애물을 향해 달려가 한 번 도약하고 양발로 착지한 뒤 앞으로 두 걸음 더 이동한다.", ["도약 준비", "공중 궤적", "양발 착지와 후속 이동"], ["신체 관통", "착지 없는 부양", "팔다리·발 형태 붕괴"]),
    ("action_level_4", "액션 강도 4 · 2인 회피 액션", "interaction", "stress", "서로 다른 두 인물이 같은 공간에서 한 명은 앞으로 돌진하고 다른 한 명은 옆으로 피한다. 서로 충돌하지 않고 각자의 정체성과 진행 방향을 유지한다.", ["두 인물 구분", "회피 타이밍", "충돌 없는 교차", "각자 진행 방향 유지"], ["인물 융합", "복제·누락", "접촉 없는 위치 교환"]),
    ("action_level_5", "액션 강도 5 · 연속 고속 액션", "motion_physics", "stress", "한 인물이 목표물을 발견한 뒤 달리기, 낮은 장애물 도약, 착지, 짧은 미끄러짐, 균형 회복의 다섯 동작을 한 연속 쇼트로 수행한다.", ["다섯 동작 순서", "속도 변화", "지면·장애물 접촉", "회복 동작"], ["동작 순서 붕괴", "장면 컷 전환", "공중 부양", "후반 신체·배경 붕괴"]),
    ("vfx_particles", "VFX · 연기·먼지·입자", "vfx_effects", "diagnostic", "인물이 마른 지면을 강하게 밟으면 접촉 지점에서 먼지가 발생해 바깥으로 퍼지고 중력에 따라 가라앉는다.", ["발과 지면의 접촉 후 입자 발생", "접촉점에서 바깥으로 확산", "시간에 따른 소멸과 침전"], ["행동 전 효과 발생", "입자 발생 위치 이탈", "먼지의 고체화·복제", "캐릭터·배경 정체성 붕괴"]),
    ("vfx_elemental", "VFX · 원소 효과와 주변광", "vfx_effects", "diagnostic", "인물이 금속 지팡이를 들면 끝부분에 푸른 불꽃이 점화되고 얼굴·손·바닥에 푸른빛이 반사된다.", ["지팡이 끝에서 불꽃 점화", "불꽃의 지속적인 부착", "주변 표면의 푸른 반사광"], ["잘못된 위치에서 점화", "불꽃이 손이나 신체로 융합", "주변광 반응 누락", "불꽃 형태의 프레임별 급변"]),
    ("vfx_impact", "VFX · 충돌·충격파·파편", "vfx_effects", "stress", "인물이 망치로 금이 간 돌을 한 번 내려치면 접촉 순간 작은 충격파와 돌 파편이 발생하고 파편이 바닥으로 떨어진다.", ["망치와 돌의 명확한 접촉", "접촉 직후 충격파 발생", "파편의 바깥 방향 이동과 낙하"], ["접촉 전 폭발", "파편의 순간이동·무한 복제", "충격 없는 파괴", "의도하지 않은 장면 전환"]),
    ("vfx_energy_attachment", "VFX · 에너지 부착과 가림", "vfx_effects", "stress", "인물이 빛나는 에너지 구체를 두 손 사이에 유지한 채 몸을 돌린다. 구체는 손 사이에 고정되고 팔에 잠시 가려진 뒤 다시 나타난다.", ["두 손 사이의 에너지 위치 유지", "몸 회전 중 크기·색상 유지", "가림 뒤 동일한 효과 복원"], ["에너지가 신체와 분리되어 표류", "효과 복제·색상 변경", "가림 뒤 소실", "손과 팔의 변형"]),
    ("vfx_weather", "VFX · 비·안개·환경 효과", "vfx_effects", "stress", "비가 내리는 안개 낀 골목에서 인물이 천천히 걸어간다. 빗방울은 인물과 젖은 바닥에 반응하고 안개 뒤에서도 공간 구조가 유지된다.", ["지속적인 강우 방향", "의상·바닥의 젖음과 반사", "안개 속 인물과 공간 유지"], ["비가 장면 중 갑자기 멈춤", "빗방울이 화면에 고정", "안개로 인한 배경 교체", "인물 정체성 붕괴"]),
    ("attribute_binding", "속성 귀속과 역할 분리", "character_identity", "stress", "빨간 재킷을 입고 금색 열쇠를 든 인물과 파란 코트를 입고 은색 책을 든 인물이 각자의 색상·소품·위치를 유지하며 차례로 움직인다.", ["인물별 의상 색상 유지", "열쇠와 책의 소유자 유지", "두 인물의 행동 순서 구분"], ["의상 색상 교환", "소품 소유자 교환", "인물·소품 융합", "복제 또는 누락"]),
    ("environment_reaction", "행동에 따른 환경 반응", "motion_physics", "diagnostic", "인물이 얕은 물웅덩이를 한 걸음 세게 밟으면 발 접촉 지점에서 물이 튀고 원형 잔물결이 퍼지며 젖은 발자국이 남는다.", ["발과 수면의 접촉", "접촉 후 물 튀김과 잔물결", "이동 경로에 젖은 발자국 유지"], ["접촉 전 물 반응", "발과 무관한 위치의 물 튀김", "잔물결의 역방향 진행", "지면·발 관통"]),
    ("emotional_acting", "감정 연기와 신체 표현", "prompt_detail_omission", "diagnostic", "침착하던 인물이 멀리서 위험을 발견하고 두려움을 느낀다. 시선, 얼굴 표정, 호흡, 어깨와 뒷걸음질이 같은 감정 변화를 순서대로 표현한다.", ["시선으로 위험 발견", "표정·호흡·자세의 감정 일치", "감정에 따른 자연스러운 뒷걸음질"], ["표정만 기계적으로 변경", "서로 모순되는 얼굴과 자세", "감정 변화 누락", "과장된 신체 왜곡"]),
    ("state_persistence", "발생한 상태의 지속성", "scene_continuity", "stress", "인물의 흰 소매에 붉은 페인트 한 방울이 떨어져 얼룩이 생긴다. 인물이 팔을 돌리고 걸어가도 같은 소매의 같은 위치에 얼룩이 유지된다.", ["페인트 접촉 후 얼룩 생성", "같은 소매와 위치에 얼룩 유지", "움직임 중 색상·크기 유지"], ["접촉 전 얼룩 출현", "얼룩 소실·이동·복제", "반대쪽 소매로 상태 이동", "의상 전체 색상 변경"]),
    ("scale_perspective", "크기·원근과 비율 유지", "scene_continuity", "diagnostic", "인물이 전경에서 멀리 있는 문까지 걸어간 뒤 다시 카메라 쪽으로 돌아온다. 원근에 따른 화면 크기만 변하고 신체 비율과 문 크기는 유지된다.", ["이동 거리에 따른 자연스러운 크기 변화", "신체 비율 유지", "문과 공간의 고정된 크기·위치"], ["거리와 무관한 크기 변화", "신체 비율 변형", "배경 구조 확대·축소", "인물 순간이동"]),
    ("offscreen_return", "화면 밖 퇴장과 복귀", "character_identity", "stress", "독특한 의상과 소품을 가진 한 인물이 화면 오른쪽으로 완전히 퇴장했다가 잠시 뒤 같은 오른쪽에서 다시 들어온다.", ["완전한 화면 밖 퇴장", "동일 방향에서 자연스러운 복귀", "얼굴·의상·소품의 동일성 유지"], ["화면 안에서 순간 소실", "다른 인물로 복귀", "소품·의상 변경", "반대 방향에서 순간 등장"]),
    ("dialogue_action", "한국어 대사 중 행동 수행", "dialogue_audio", "stress", "한 인물이 상대를 바라보며 걸어가서 컵을 집어 들고 자연스러운 한국어로 ‘이건 내가 가져갈게.’라고 말한다. 행동과 발화가 겹쳐도 화자와 컵이 유지된다.", ["걷기·컵 집기·발화의 자연스러운 병행", "정확한 한국어 대사와 화자", "시선·입 모양·손 동작의 역할 유지"], ["행동 중 대사 누락", "다른 언어 또는 화자 혼합", "컵 복제·소실", "립싱크와 행동의 급격한 중단"]),
    ("style_persistence", "영상화 중 화풍 유지", "visual_temporal_quality", "stress", "스타일화된 3D 애니메이션 앵커의 캐릭터가 걸으며 몸을 돌린다. 조형, 셰이딩, 색상 팔레트와 렌더링 스타일을 영상 끝까지 유지한다.", ["캐릭터 조형과 셰이딩 유지", "색상 팔레트와 재질 스타일 유지", "움직임 중 동일한 렌더링 품질"], ["실사·저품질 3D 등 다른 화풍으로 변화", "프레임별 셰이딩 변화", "후반 디테일 붕괴", "캐릭터 디자인 단순화"]),
    ("scenario_level_1", "시나리오 1단계 · 발견과 선택", "scenario_comprehension", "diagnostic", "빈 기차역에 들어온 배달원이 바닥의 붉은 봉투를 발견하고 멈춘다. 주변을 살핀 뒤 봉투를 집어 들고 닫힌 문을 경계하며 바라본다.", ["배달원의 공간 진입", "붉은 봉투 발견과 정지", "주변 확인 후 봉투 집기", "닫힌 문을 바라보며 종료"], ["발견 전 봉투 집기", "봉투 복제·소실", "사건 순서 변경", "결말 행동 누락"]),
    ("scenario_level_2", "시나리오 2단계 · 실수와 복구", "scenario_comprehension", "diagnostic", "작업자가 주전자로 파란 컵에 물을 붓다가 일부를 바닥에 쏟는다. 컵을 탁자에 내려놓고 천을 집어 젖은 바닥을 닦아 물기를 줄인다.", ["주전자를 들어 컵에 물 붓기", "바닥에 일부 물 쏟기", "컵을 탁자에 내려놓기", "천을 집어 바닥 닦기", "젖은 상태가 감소하며 종료"], ["행동 전 물 쏟아짐", "컵·주전자·천 복제 또는 소실", "바닥을 닦기 전 건조", "복구 행동 누락"]),
    ("scenario_level_3", "시나리오 3단계 · 열쇠 전달과 망설임", "scenario_comprehension", "stress", "빨간 재킷의 배달원이 금색 열쇠를 들고 파란 코트의 관리인에게 다가간다. 관리인은 처음에는 받지 않는다. 배달원이 한국어로 ‘이 열쇠를 꼭 전해 달라고 했어요.’라고 말하면 관리인이 망설인 뒤 열쇠를 받는다.", ["두 인물의 외형과 역할 구분", "배달원의 접근과 관리인의 초기 거절", "배달원의 정확한 한국어 대사", "관리인의 망설임 후 수락", "열쇠 소유자의 한 번의 변경"], ["인물·의상·역할 혼합", "대사 화자 변경", "열쇠 복제·순간이동", "거절 없이 즉시 수락", "전달 결말 누락"]),
    ("scenario_level_4", "시나리오 4단계 · 증기 기관실의 위기", "scenario_comprehension", "stress", "붉은 경고등이 깜빡이는 기관실에서 젊은 조수와 나이 든 기술자가 기계를 점검한다. 파이프가 흔들린 뒤 증기가 터진다. 조수가 뒤로 물러서며 한국어로 ‘압력이 너무 높아요!’라고 외친다. 기술자는 얼굴을 가리고 밸브로 이동해 레버를 내린다. 증기와 경고등이 안정되고 두 사람은 안도한다.", ["두 인물의 위치와 역할 유지", "파이프 흔들림 후 해당 위치에서 증기 발생", "조수의 후퇴와 정확한 대사", "기술자의 밸브 접근과 레버 조작", "조작 후 증기 감소와 경고등 안정", "두 인물의 안도 반응"], ["레버 조작 전 위기 자동 해결", "증기의 잘못된 발생 위치", "조수와 기술자의 행동·대사 혼합", "환경 상태 변화 누락", "후반 정체성·공간 붕괴"]),
    ("scenario_level_5", "시나리오 5단계 · 붕괴하는 연구실 탈출", "scenario_comprehension", "stress", "붉은 재킷 기술자는 제어 레버 앞에 있고 파란 코트 구조대원은 다친 노란 조끼 작업자를 부축한다. 경고등이 붉어지고 불꽃과 작은 파편이 떨어진다. 기술자가 한국어로 ‘문이 닫히기 전에 먼저 나가!’라고 외치며 레버를 당겨 왼쪽 방호문을 연다. 증기가 세 사람을 잠시 가린다. 구조대원과 부상자가 먼저 탈출하고 기술자가 마지막으로 나간 뒤 방호문이 닫히기 시작하며 빈 연구실이 남는다.", ["세 인물의 외형·역할·부상 상태 유지", "경고등 변화와 불꽃·파편 발생", "기술자의 정확한 대사와 레버 조작", "레버 조작 후 왼쪽 방호문 열림", "증기 가림 뒤 세 인물 정체성 복원", "구조대원과 부상자의 우선 탈출", "기술자의 마지막 탈출", "방호문이 닫히며 빈 공간으로 종료"], ["세 인물 융합·복제·누락", "부상자 상태 소실", "대사·레버 역할 교환", "문이 원인 없이 열림", "가림 뒤 인물 교체", "탈출 순서 변경", "결말 전 장면 붕괴"]),
]


CASE_TARGET_SECONDS = {
    "empty_environment": 5,
    "single_identity": 5,
    "two_subject_separation": 6,
    "reference_following": 5,
    "ground_contact": 8,
    "hand_prop_contact": 6,
    "two_subject_handoff": 8,
    "camera_action": 6,
    "anchor_start": 5,
    "spatial_continuity": 8,
    "occlusion_return": 7,
    "lighting_material": 6,
    "korean_dialogue": 8,
    "prop_persistence": 6,
    "entry_exit": 8,
    "long_temporal": 20,
    "action_level_1": 5,
    "action_level_2": 6,
    "action_level_3": 8,
    "action_level_4": 8,
    "action_level_5": 10,
    "vfx_particles": 6,
    "vfx_elemental": 6,
    "vfx_impact": 7,
    "vfx_energy_attachment": 7,
    "vfx_weather": 8,
    "attribute_binding": 8,
    "environment_reaction": 7,
    "emotional_acting": 8,
    "state_persistence": 8,
    "scale_perspective": 10,
    "offscreen_return": 9,
    "dialogue_action": 10,
    "style_persistence": 8,
    "scenario_level_1": 8,
    "scenario_level_2": 10,
    "scenario_level_3": 12,
    "scenario_level_4": 16,
    "scenario_level_5": 20,
}


def _case_generation(short_id: str) -> dict[str, int]:
    seconds = CASE_TARGET_SECONDS[short_id]
    return {"target_seconds": seconds, "frame_count": seconds * 24 + 1}


CANONICAL_PROMPTS_EN = {
    "empty_environment": "A completely empty architectural environment with no people or animals. The camera slowly moves forward while the layout, lighting and object positions remain stable.",
    "single_identity": "One distinct character turns their head and walks several steps. Preserve the same face, body proportions, hairstyle and clothing throughout the shot.",
    "two_subject_separation": "Two visually distinct characters stand apart and react one at a time. Preserve each identity, costume, position and role without merging or duplication.",
    "reference_following": "Animate the provided reference subject while preserving the exact identity, clothing, primary colors, proportions and defining visual features.",
    "ground_contact": "A running character slips, loses their center of gravity, plants one hand on the ground after impact, then pushes back up with visible weight and contact.",
    "hand_prop_contact": "A character reaches toward an object on a table, closes their fingers around it, lifts it, and keeps its shape and ownership stable.",
    "two_subject_handoff": "The first character extends one object, the second character makes hand contact and receives it. Ownership changes exactly once and the object never duplicates.",
    "camera_action": "The camera makes a slow lateral move while one character notices a target and turns toward it. Keep the subject framed and separate camera motion from body motion.",
    "anchor_start": "Begin from the provided anchor composition. Preserve the same camera angle, spatial layout, subject placement and visual identity while the subject begins one natural small movement.",
    "spatial_continuity": "In one continuous environment, a character moves from foreground to background. Preserve the doorway direction, landmarks, props and traversed path.",
    "occlusion_return": "A character passes briefly behind a pillar and reappears. Preserve the exact face, clothing, body proportions and direction of travel before and after the occlusion.",
    "lighting_material": "The camera slowly moves through one space while preserving directional lighting, a metallic prop and a wet floor. Keep material response, reflections and light direction stable.",
    "korean_dialogue": "Two characters speak one short line each in natural Korean, in order. Keep the active speaker, voice and lip movement clearly assigned to the correct character.",
    "prop_persistence": "A character carries a distinctive prop while moving. Preserve the prop owner, shape, material, scale and count for the entire shot.",
    "entry_exit": "One character enters from frame left and approaches a second character at center. The second character then exits frame right. Preserve the order, identities and screen directions.",
    "long_temporal": "In one continuous 15 to 20 second shot, connect four ordered events: discovery, approach, interaction and reaction. Preserve identity, space and causality through the ending.",
    "action_level_1": "A character makes one controlled action: turns in place, reaches toward a nearby target, points at it, then settles into a stable stance. Keep hand, gaze and body direction coordinated.",
    "action_level_2": "A character runs a short distance toward a target, visibly decelerates, and stops with both feet balanced on the ground. Show clear acceleration, braking and weight transfer.",
    "action_level_3": "A character runs toward a low obstacle, performs one jump, lands on both feet, then takes two forward steps. Preserve takeoff, airborne trajectory, landing impact and follow-through.",
    "action_level_4": "Two visually distinct characters perform a coordinated dodge. The first rushes forward while the second steps sideways to avoid them. Keep identities, directions, timing and non-contact separation clear.",
    "action_level_5": "In one continuous shot, a character performs five ordered high-energy actions: notices a target, runs, jumps a low obstacle, lands and slides briefly, then regains balance. Preserve causality, ground contact and identity through the end.",
    "vfx_particles": "A character forcefully stamps one foot onto dry ground. Only after contact, a dust plume originates exactly beneath the foot, expands outward, then loses energy and settles under gravity. Preserve the character and environment without cuts.",
    "vfx_elemental": "A character raises a metal staff. A controlled blue flame ignites only at the staff tip, remains attached there, flickers coherently, and casts blue light onto the face, hands and floor.",
    "vfx_impact": "A character strikes one cracked stone once with a hammer. At the exact contact moment, a small shockwave and stone fragments burst outward, then the fragments fall and land with gravity. Keep one continuous shot.",
    "vfx_energy_attachment": "A character holds one glowing energy sphere between both hands while turning their torso. Keep the sphere attached between the hands with stable size and color; it is briefly occluded by an arm and reappears unchanged.",
    "vfx_weather": "A character walks slowly through one rainy, foggy alley. Keep the rain direction continuous, show droplets reacting to the character and wet ground, preserve wet reflections, and retain the same spatial layout through the fog.",
    "attribute_binding": "Two distinct people act one at a time. Person A wears a red jacket and holds one gold key. Person B wears a blue coat and holds one silver book. Preserve each costume color, prop owner, identity and position without swapping or merging.",
    "environment_reaction": "A character steps forcefully into one shallow puddle. After foot contact, water splashes from the contact point, circular ripples expand outward, and wet footprints remain along the next steps.",
    "emotional_acting": "A calm character notices danger in the distance and becomes afraid. Express the transition coherently through gaze, facial tension, breathing, raised shoulders and one cautious backward step, in that order.",
    "state_persistence": "One drop of red paint lands on the white sleeve and creates a distinct stain. As the character rotates the arm and walks, preserve the same stain on the same sleeve at the same location, size and color.",
    "scale_perspective": "A character walks from the foreground to a distant doorway, then returns toward the camera. Change apparent size only according to perspective while preserving body proportions, doorway scale and the fixed environment.",
    "offscreen_return": "One character with a distinctive costume and prop fully exits frame right, remains off screen briefly, then re-enters from the same right edge. Preserve the exact face, costume, body proportions and prop.",
    "dialogue_action": "A character looks toward another person, walks to a table, picks up one cup, and says in natural Korean, ‘이건 내가 가져갈게.’ Keep the same speaker, lip movement, gaze, hand contact and cup ownership while speech overlaps the action.",
    "style_persistence": "Animate the provided stylized 3D character walking and turning. Preserve the exact character design, stylized proportions, shader treatment, material detail, color palette and premium animated-feature rendering style through the final frame.",
    "scenario_level_1": "In one continuous shot inside an empty train station, a courier enters, notices one red envelope on the floor, stops, looks around, picks up the envelope, then ends by watching a closed door with caution. Preserve the event order and the single envelope.",
    "scenario_level_2": "In one continuous shot, a worker lifts a kettle and pours water into one blue cup, accidentally spills some water onto the floor, places the cup back on the table, picks up a cloth, and wipes the puddle until the wet area visibly decreases. Preserve every prop and state transition.",
    "scenario_level_3": "A courier in a red jacket approaches a keeper in a blue coat while holding one gold key. The keeper initially refuses to reach for it. The courier says in natural Korean, ‘이 열쇠를 꼭 전해 달라고 했어요.’ After a visible hesitation, the keeper accepts the key. Ownership changes exactly once.",
    "scenario_level_4": "In one continuous shot inside an engine room with flashing red warning lights, a young assistant and an older technician inspect a machine. A pipe shakes, then steam bursts only from that pipe. The assistant steps back and shouts in natural Korean, ‘압력이 너무 높아요!’ The technician shields their face, reaches the valve and pulls the lever. Only after the lever moves, the steam subsides, the warning light stabilizes, and both people show relief.",
    "scenario_level_5": "In one continuous 20-second shot inside a failing laboratory, a red-jacket engineer stands at a control lever while a blue-coated rescuer supports an injured worker in a yellow vest. Warning lights turn red as sparks and small debris fall. The engineer shouts in natural Korean, ‘문이 닫히기 전에 먼저 나가!’ and pulls the lever, causing the left blast door to open. Steam briefly occludes all three people. Preserve all identities after the occlusion. The rescuer leads the injured worker out first, the engineer exits last, then the blast door begins closing and the empty laboratory remains.",
}

I2V_ANCHOR_DESCRIPTIONS = {
    "empty_environment": "인물·동물이 없는 빈 공간 전경. 출입구와 주요 구조물이 명확한 시작 이미지",
    "single_identity": "한 캐릭터의 얼굴·헤어·의상·전신 비율이 명확한 시작 이미지",
    "two_subject_separation": "외형과 의상이 확실히 다른 두 캐릭터가 떨어져 서 있는 시작 이미지",
    "reference_following": "정체성·의상·주요 색상·전신 비율을 비교할 기준 이미지",
    "ground_contact": "한 캐릭터가 달리거나 미끄러지기 직전이며 지면이 선명한 시작 이미지",
    "hand_prop_contact": "한 캐릭터의 손과 탁자 위 단일 소품이 모두 보이는 시작 이미지",
    "two_subject_handoff": "서로 다른 두 인물과 첫 인물이 들고 있는 단일 소품이 보이는 시작 이미지",
    "camera_action": "한 캐릭터와 그 캐릭터가 발견할 목표물이 함께 보이는 시작 이미지",
    "anchor_start": "시작 구도·카메라 각도·피사체 위치·공간 배치가 명확한 기준 앵커 이미지",
    "spatial_continuity": "전경의 캐릭터, 후경 출입구와 고정 랜드마크가 함께 보이는 시작 이미지",
    "occlusion_return": "한 캐릭터, 가림용 기둥, 가림 전후 진행 방향이 함께 보이는 시작 이미지",
    "lighting_material": "금속 소품, 젖은 바닥, 방향성 조명이 모두 보이는 단일 공간 시작 이미지",
    "korean_dialogue": "서로 다른 두 캐릭터의 얼굴과 입이 잘 보이는 미디엄 투샷 시작 이미지",
    "prop_persistence": "한 캐릭터가 형태·재질이 독특한 소품 하나를 들고 있는 시작 이미지",
    "entry_exit": "외형이 다른 두 캐릭터와 왼쪽·중앙·오른쪽 이동 경로가 보이는 시작 이미지",
    "long_temporal": "캐릭터, 발견 대상과 이동 가능한 하나의 공간이 함께 보이는 시작 이미지",
    "action_level_1": "한 캐릭터, 가까운 목표물, 손·시선·몸 방향이 명확한 미디엄샷 시작 이미지",
    "action_level_2": "한 캐릭터, 짧은 달리기 경로와 목표물, 평평한 바닥이 보이는 전신 시작 이미지",
    "action_level_3": "한 캐릭터, 낮은 장애물, 도약 전 접근 경로와 착지 바닥이 함께 보이는 전신 시작 이미지",
    "action_level_4": "외형이 확실히 다른 두 캐릭터와 서로 교차하지 않는 전진·측면 회피 경로가 보이는 와이드 시작 이미지",
    "action_level_5": "한 캐릭터, 발견 대상, 낮은 장애물, 달리기·착지·미끄러짐이 가능한 연속 경로가 보이는 와이드 시작 이미지",
    "vfx_particles": "한 캐릭터의 전신과 마른 흙바닥의 발 접촉 지점이 선명하고, 시작 시 먼지 효과는 아직 없는 와이드 이미지",
    "vfx_elemental": "한 캐릭터가 꺼진 금속 지팡이를 들고 있으며 지팡이 끝·얼굴·손·바닥이 함께 보이는 어두운 미디엄 전신 이미지",
    "vfx_impact": "한 캐릭터, 들린 망치, 금이 간 돌과 주변의 깨끗한 바닥이 함께 보이며 아직 충돌하지 않은 와이드 이미지",
    "vfx_energy_attachment": "한 캐릭터가 빈 두 손을 마주 보고 있으며 손·팔·얼굴이 명확하고 시작 시 에너지 효과가 없는 미디엄 이미지",
    "vfx_weather": "한 캐릭터와 깊이감 있는 골목, 젖기 전 의상과 바닥 구조가 명확하며 비·안개 효과가 아직 없는 와이드 이미지",
    "attribute_binding": "빨간 재킷과 금색 열쇠의 인물 A, 파란 코트와 은색 책의 인물 B가 떨어져 서 있고 전신·소품이 모두 선명한 와이드 이미지",
    "environment_reaction": "한 캐릭터의 전신, 한쪽 발 앞의 얕은 물웅덩이, 다음 이동 경로가 함께 보이고 수면이 아직 고요한 이미지",
    "emotional_acting": "침착한 중립 표정의 한 캐릭터와 멀리 있는 위험 대상이 함께 보이며 얼굴·눈·어깨·손이 선명한 미디엄 이미지",
    "state_persistence": "깨끗한 흰 소매를 입은 한 캐릭터와 소매 위에 떨어지기 직전의 붉은 페인트 한 방울이 함께 보이는 미디엄 이미지",
    "scale_perspective": "전경의 전신 캐릭터, 멀리 있는 문, 바닥의 원근선과 고정 랜드마크가 명확한 깊은 와이드 이미지",
    "offscreen_return": "독특한 의상과 단일 소품을 가진 한 캐릭터가 화면 중앙에 서 있고 오른쪽 출입 경로가 비어 있는 전신 이미지",
    "dialogue_action": "한 캐릭터의 얼굴과 입, 상대 인물, 이동 경로, 탁자 위 단일 컵이 모두 보이는 미디엄 와이드 이미지",
    "style_persistence": "고품질 스타일화 3D 애니메이션 캐릭터의 전신, 명확한 셰이딩·재질·색상 팔레트와 이동 공간이 보이는 기준 이미지",
    "scenario_level_1": "빈 기차역 와이드샷. 입구의 배달원, 바닥의 단일 붉은 봉투, 후경의 닫힌 문과 이동 경로가 동시에 명확한 시작 이미지",
    "scenario_level_2": "한 작업자, 손잡이가 있는 주전자, 탁자 위 단일 파란 컵, 접힌 천과 아직 마른 바닥이 모두 보이는 미디엄 와이드 시작 이미지",
    "scenario_level_3": "금색 열쇠를 든 빨간 재킷 배달원과 빈손의 파란 코트 관리인이 떨어져 서 있으며 얼굴·손·전신이 구분되는 와이드 시작 이미지",
    "scenario_level_4": "기관실 와이드샷. 젊은 조수와 나이 든 기술자, 온전한 파이프, 밸브 레버, 붉은 경고등과 이동 경로가 보이며 증기는 아직 없는 시작 이미지",
    "scenario_level_5": "연구실 와이드샷. 제어 레버 앞의 빨간 재킷 기술자, 다친 노란 조끼 작업자를 부축하는 파란 코트 구조대원, 닫힌 왼쪽 방호문, 경고등과 천장 설비가 모두 구분되고 VFX는 아직 없는 시작 이미지",
}

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, label: str, *, required: bool = True, maximum: int = 4000) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"{label}을(를) 입력하세요.")
    if len(result) > maximum:
        raise ValueError(f"{label}은(는) {maximum}자 이하여야 합니다.")
    return result


def _session_resolution(data: dict[str, Any]) -> tuple[int | None, int | None]:
    raw = data.get("resolution")
    if raw in (None, ""):
        return None, None
    if not isinstance(raw, dict):
        raise ValueError("테스트 해상도 형식이 올바르지 않습니다.")
    try:
        width = int(raw.get("width"))
        height = int(raw.get("height"))
    except (TypeError, ValueError) as exc:
        raise ValueError("테스트 해상도의 가로·세로는 숫자여야 합니다.") from exc
    if not (32 <= width <= 4096 and 32 <= height <= 4096):
        raise ValueError("테스트 해상도는 가로·세로 각각 32~4096이어야 합니다.")
    if width % 16 or height % 16:
        raise ValueError("테스트 해상도는 가로·세로 모두 16의 배수여야 합니다.")
    return width, height


def _validated_case_settings(contract_json: str, raw: Any) -> dict[str, Any]:
    contract = json.loads(contract_json or "{}")
    definitions = dict(contract.get("parameters") or {})
    raw_values = dict(raw or {}) if isinstance(raw, dict) else {}
    unknown = set(raw_values) - set(definitions)
    if unknown:
        raise ValueError("지원하지 않는 케이스 설정입니다: " + ", ".join(sorted(unknown)))
    result: dict[str, Any] = {}
    for name, definition in definitions.items():
        value = raw_values.get(name, definition.get("default"))
        if definition.get("type") == "integer":
            try:
                value = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{definition.get('label_ko') or name}은(는) 정수여야 합니다.") from exc
            minimum = int(definition.get("minimum", value))
            maximum = int(definition.get("maximum", value))
            if value < minimum or value > maximum:
                raise ValueError(f"{definition.get('label_ko') or name}은(는) {minimum}~{maximum}이어야 합니다.")
        result[name] = value
    return result


def _token(value: Any, label: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "").strip()).strip("_.-").lower()
    if not result:
        raise ValueError(f"{label}을(를) 입력하세요.")
    return result[:100]


def _sync_suite_case_order(connection: sqlite3.Connection, suite_id: str, suffix: str) -> None:
    """Backfill inserted cases and repair ordering after a suite definition expands.

    Existing suites may already occupy all consecutive order values.  Move them
    out of the way first so newly inserted cases can be placed between them.
    Session-specific ordering is stored separately and is intentionally untouched.
    """
    connection.execute("UPDATE suite_cases SET ordering=ordering+1000 WHERE suite_id=?", (suite_id,))
    for ordering, (short_id, *_rest) in enumerate(DEFAULT_CASES, 1):
        case_version_id = f"benchmark_{short_id}{suffix}"
        connection.execute(
            "INSERT OR IGNORE INTO suite_cases(suite_id,case_version_id,ordering) VALUES (?,?,?)",
            (suite_id, case_version_id, ordering),
        )
        connection.execute(
            "UPDATE suite_cases SET ordering=? WHERE suite_id=? AND case_version_id=?",
            (ordering, suite_id, case_version_id),
        )


def ensure_default_suite(connection: sqlite3.Connection) -> None:
    definition = {"name": "비디오 모델 공통 진단", "version": 1, "cases": DEFAULT_CASES}
    connection.execute(
        """INSERT OR IGNORE INTO benchmark_suites
           (suite_id,name,version,description,tier,definition_sha256)
           VALUES (?,? ,1,?,'diagnostic',?)""",
        (DEFAULT_SUITE_ID, "비디오 모델 공통 진단", "새 비디오 모델의 주요 능력을 공식 워크플로우로 빠르게 파악한다.", _sha(definition)),
    )
    for order, (short_id, title, category, tier, intent, required, forbidden) in enumerate(DEFAULT_CASES, 1):
        case_id = f"benchmark_{short_id}"
        case_version_id = f"{case_id}_v1"
        generation = _case_generation(short_id)
        contract = {"required_events": required, "forbidden_failures": forbidden, "scoring_dimensions": [category, "prompt_adherence", "temporal_quality"], "generation": generation}
        definition = {"title": title, "category": category, "tier": tier, "intent_ko": intent, "contract": contract}
        connection.execute(
            """INSERT OR IGNORE INTO benchmark_cases
               (case_id,title,intent_ko,intent_json,category,tags_json,source_kind)
               VALUES (?,?,?,?,?,?,'canonical_benchmark')""",
            (case_id, title, intent, _json(contract), category, _json([tier, category])),
        )
        connection.execute(
            """INSERT OR IGNORE INTO benchmark_case_versions
               (case_version_id,case_id,version,title,intent_ko,category,tier,contract_json,definition_sha256)
               VALUES (?,?,1,?,?,?,?,?,?)""",
            (case_version_id, case_id, title, intent, category, tier, _json(contract), _sha(definition)),
        )
        connection.execute(
            """UPDATE benchmark_cases
               SET title=?,intent_ko=?,intent_json=?,category=?,tags_json=? WHERE case_id=?""",
            (title, intent, _json(contract), category, _json([tier, category]), case_id),
        )
        connection.execute(
            """UPDATE benchmark_case_versions
               SET title=?,intent_ko=?,category=?,tier=?,contract_json=?,definition_sha256=?
               WHERE case_version_id=?""",
            (title, intent, category, tier, _json(contract), _sha(definition), case_version_id),
        )
        connection.execute(
            "INSERT OR IGNORE INTO suite_cases(suite_id,case_version_id,ordering) VALUES (?,?,?)",
            (DEFAULT_SUITE_ID, case_version_id, order),
        )
        canonical_prompt = CANONICAL_PROMPTS_EN[short_id]
        connection.execute(
            "INSERT OR IGNORE INTO benchmark_case_prompts(case_version_id,language,prompt_kind,prompt_text,prompt_sha256) VALUES (?,'en','canonical',?,?)",
            (case_version_id, canonical_prompt, hashlib.sha256(canonical_prompt.encode("utf-8")).hexdigest()),
        )
        if short_id == "reference_following":
            connection.execute(
                "INSERT OR IGNORE INTO benchmark_case_asset_requirements(case_version_id,role,kind,minimum_count,description) VALUES (?,'reference_image','image',1,'정체성 비교용 참조 이미지')",
                (case_version_id,),
            )
    _sync_suite_case_order(connection, DEFAULT_SUITE_ID, "_v1")


def ensure_i2v_suite(connection: sqlite3.Connection) -> None:
    definition = {
        "name": "비디오 모델 공통 진단 · I2V 고정 앵커",
        "version": 1,
        "input_mode": "i2v_fixed_anchor",
        "cases": DEFAULT_CASES,
    }
    connection.execute(
        """INSERT OR IGNORE INTO benchmark_suites
           (suite_id,name,version,description,tier,definition_sha256)
           VALUES (?,? ,1,?,'diagnostic',?)""",
        (
            I2V_SUITE_ID,
            "비디오 모델 공통 진단 · I2V 고정 앵커",
            "각 케이스마다 내용 해시로 고정된 시작 이미지를 사용해 I2V 모델을 비교한다.",
            _sha(definition),
        ),
    )
    for order, (short_id, title, category, tier, intent, required, forbidden) in enumerate(DEFAULT_CASES, 1):
        case_id = f"benchmark_{short_id}"
        case_version_id = f"{case_id}_i2v_v1"
        generation = _case_generation(short_id)
        contract = {
            "required_events": required,
            "forbidden_failures": forbidden,
            "scoring_dimensions": [category, "prompt_adherence", "temporal_quality"],
            "input_mode": "i2v_fixed_anchor",
            "generation": generation,
        }
        case_definition = {
            "title": title,
            "category": category,
            "tier": tier,
            "intent_ko": intent,
            "contract": contract,
            "anchor_description": I2V_ANCHOR_DESCRIPTIONS[short_id],
        }
        connection.execute(
            """INSERT OR IGNORE INTO benchmark_case_versions
               (case_version_id,case_id,version,title,intent_ko,category,tier,contract_json,definition_sha256)
               VALUES (?,?,2,?,?,?,?,?,?)""",
            (case_version_id, case_id, title, intent, category, tier, _json(contract), _sha(case_definition)),
        )
        connection.execute(
            """UPDATE benchmark_case_versions
               SET title=?,intent_ko=?,category=?,tier=?,contract_json=?,definition_sha256=?
               WHERE case_version_id=?""",
            (title, intent, category, tier, _json(contract), _sha(case_definition), case_version_id),
        )
        connection.execute(
            "INSERT OR IGNORE INTO suite_cases(suite_id,case_version_id,ordering) VALUES (?,?,?)",
            (I2V_SUITE_ID, case_version_id, order),
        )
        canonical_prompt = CANONICAL_PROMPTS_EN[short_id]
        connection.execute(
            "INSERT OR IGNORE INTO benchmark_case_prompts(case_version_id,language,prompt_kind,prompt_text,prompt_sha256) VALUES (?,'en','canonical',?,?)",
            (case_version_id, canonical_prompt, hashlib.sha256(canonical_prompt.encode("utf-8")).hexdigest()),
        )
        connection.execute(
            """INSERT OR IGNORE INTO benchmark_case_asset_requirements
               (case_version_id,role,kind,minimum_count,description)
               VALUES (?,'reference_image','image',1,?)""",
            (case_version_id, I2V_ANCHOR_DESCRIPTIONS[short_id]),
        )
    _sync_suite_case_order(connection, I2V_SUITE_ID, "_i2v_v1")


def open_registry(root: Path) -> sqlite3.Connection:
    connection = evaluation_db.connect(root / evaluation_db.DEFAULT_DB_PATH)
    evaluation_db.initialize(connection)
    ensure_default_suite(connection)
    ensure_i2v_suite(connection)
    model_test_r2v.ensure_suites(connection)
    connection.commit()
    return connection


def register_model(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    provider = _text(data.get("provider"), "제작사", maximum=200)
    family = _text(data.get("family"), "모델 제품군", maximum=200)
    display_name = _text(data.get("display_name"), "모델 이름", maximum=200)
    version = _text(data.get("version"), "모델 버전", required=False, maximum=100)
    model_id = _token(data.get("model_id") or f"{provider}_{family}_{version or display_name}", "모델 ID")
    with open_registry(root) as connection:
        connection.execute(
            """INSERT INTO models(model_id,provider,family,display_name,version,modality,source_url,license_name,capabilities_json)
               VALUES (?,?,?,?,?,'video',?,?,?)
               ON CONFLICT(model_id) DO UPDATE SET provider=excluded.provider,family=excluded.family,
               display_name=excluded.display_name,version=excluded.version,source_url=excluded.source_url,
               license_name=excluded.license_name,capabilities_json=excluded.capabilities_json""",
            (model_id, provider, family, display_name, version or None, _text(data.get("source_url"), "공식 출처", required=False, maximum=1000) or None, _text(data.get("license_name"), "라이선스", required=False, maximum=200) or None, _json(dict(data.get("capabilities") or {}))),
        )
    return {"model_id": model_id}


def available_workflows(workflow_dir: Path) -> list[dict[str, Any]]:
    rows = []
    if not workflow_dir.is_dir():
        return rows
    for path in sorted(workflow_dir.glob("*.json"), key=lambda item: item.name.lower()):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except (OSError, json.JSONDecodeError):
            continue
        workflow_format = "comfyui_ui" if isinstance(payload, dict) and isinstance(payload.get("nodes"), list) else "comfyui_api"
        rows.append({"filename": path.name, "sha256": digest, "workflow_format": workflow_format})
    return rows


def register_workflow(root: Path, workflow_dir: Path, data: dict[str, Any]) -> dict[str, Any]:
    model_id = _text(data.get("model_id"), "모델")
    raw_filename = _text(data.get("workflow_filename"), "워크플로우 파일")
    filename = Path(raw_filename).name
    if filename != raw_filename or not filename.lower().endswith(".json"):
        raise ValueError("허용되지 않는 워크플로우 파일입니다.")
    base = workflow_dir.expanduser().resolve()
    path = (base / filename).resolve()
    if base not in path.parents or not path.is_file():
        raise ValueError("워크플로우 폴더에서 파일을 찾을 수 없습니다.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("유효한 JSON 워크플로우가 아닙니다.") from exc
    kind = str(data.get("profile_kind") or "official_baseline")
    if kind not in PROFILE_KINDS:
        raise ValueError("워크플로우 유형이 올바르지 않습니다.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    workflow_format = "comfyui_ui" if isinstance(payload, dict) and isinstance(payload.get("nodes"), list) else "comfyui_api"
    profile_id = f"workflow_{hashlib.sha256(f'{model_id}:{kind}:{digest}'.encode()).hexdigest()[:24]}"
    with open_registry(root) as connection:
        if not connection.execute("SELECT 1 FROM models WHERE model_id=?", (model_id,)).fetchone():
            raise ValueError("등록된 모델을 찾을 수 없습니다.")
        connection.execute(
            """INSERT OR IGNORE INTO workflow_profiles
               (workflow_profile_id,model_id,name,profile_kind,workflow_filename,workflow_path,
                workflow_sha256,workflow_format,defaults_json,source_url,notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (profile_id, model_id, _text(data.get("name") or filename, "워크플로우 이름", maximum=200), kind, filename, str(path), digest, workflow_format, _json(dict(data.get("defaults") or {})), _text(data.get("source_url"), "공식 출처", required=False, maximum=1000) or None, _text(data.get("notes"), "메모", required=False)),
        )
    return {"workflow_profile_id": profile_id, "workflow_sha256": digest, "workflow_format": workflow_format}


def create_session(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    model_id = _text(data.get("model_id"), "모델")
    workflow_profile_id = _text(data.get("workflow_profile_id"), "워크플로우")
    adapter_id = _text(data.get("adapter_id"), "워크플로우 어댑터")
    suite_id = _text(data.get("suite_id") or DEFAULT_SUITE_ID, "테스트 세트")
    try:
        repetitions = int(data.get("repetitions") or 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("반복 횟수는 숫자여야 합니다.") from exc
    if repetitions < 1 or repetitions > 10:
        raise ValueError("반복 횟수는 1~10이어야 합니다.")
    output_width, output_height = _session_resolution(data)
    now = datetime.now().astimezone().isoformat()
    session_id = f"test_{datetime.now():%Y%m%d_%H%M%S}_{hashlib.sha256(f'{model_id}:{workflow_profile_id}:{now}'.encode()).hexdigest()[:4]}"
    with open_registry(root) as connection:
        profile = connection.execute("SELECT model_id,workflow_filename FROM workflow_profiles WHERE workflow_profile_id=?", (workflow_profile_id,)).fetchone()
        model = connection.execute("SELECT provider,family,display_name,version FROM models WHERE model_id=?", (model_id,)).fetchone()
        if output_width and model:
            identity = " ".join(str(model[key] or "") for key in ("provider", "family", "display_name", "version")).lower()
            if "minimax" in identity and re.search(r"(^|[^a-z0-9])h3([^a-z0-9]|$)", identity):
                if output_width % 32 or output_height % 32:
                    raise ValueError("MiniMax H3 테스트 해상도는 가로·세로 모두 32의 배수여야 합니다.")
        if suite_id in model_test_r2v.R2V_SUITE_IDS:
            if not model or "minimax" not in identity or not re.search(r"(^|[^a-z0-9])h3([^a-z0-9]|$)", identity):
                raise ValueError("R2V 전용 테스트 세트는 MiniMax H3 모델만 사용할 수 있습니다.")
            if (output_width, output_height) != (832, 480):
                raise ValueError("MiniMax H3 R2V 테스트는 고정 해상도 832×480을 사용합니다.")
        if not profile:
            raise ValueError("등록된 워크플로우를 찾을 수 없습니다.")
        if profile["model_id"] != model_id:
            raise ValueError("워크플로우가 선택한 모델에 속하지 않습니다.")
        if suite_id in model_test_r2v.R2V_SUITE_IDS and profile["workflow_filename"] != model_test_r2v.R2V_WORKFLOW_FILENAME:
            raise ValueError("R2V 전용 테스트는 MiniMax H3 R2V 워크플로우를 선택해야 합니다.")
        adapter = connection.execute("SELECT workflow_profile_id FROM workflow_adapters WHERE adapter_id=?", (adapter_id,)).fetchone()
        if not adapter or adapter["workflow_profile_id"] != workflow_profile_id:
            raise ValueError("검증된 워크플로우 어댑터가 선택한 프로필과 일치하지 않습니다.")
        if not connection.execute("SELECT 1 FROM benchmark_suites WHERE suite_id=? AND active=1", (suite_id,)).fetchone():
            raise ValueError("활성 테스트 세트를 찾을 수 없습니다.")
        connection.execute("INSERT INTO test_sessions(session_id,suite_id,model_id,workflow_profile_id,adapter_id,repetitions,output_width,output_height,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (session_id, suite_id, model_id, workflow_profile_id, adapter_id, repetitions, output_width, output_height, _text(data.get("notes"), "세션 메모", required=False), now, now))
        cases = connection.execute("""SELECT s.case_version_id,s.ordering,v.contract_json FROM suite_cases s JOIN benchmark_case_versions v ON v.case_version_id=s.case_version_id WHERE s.suite_id=? AND s.enabled=1 ORDER BY s.ordering""", (suite_id,)).fetchall()
        requested_case_settings = data.get("case_settings") or {}
        if not isinstance(requested_case_settings, dict):
            raise ValueError("케이스 설정 형식이 올바르지 않습니다.")
        for row in cases:
            settings = _validated_case_settings(row["contract_json"], requested_case_settings.get(row["case_version_id"]))
            connection.execute("INSERT INTO test_session_cases(session_id,case_version_id,ordering,planned_runs,settings_json) VALUES (?,?,?,?,?)", (session_id, row["case_version_id"], row["ordering"], repetitions, _json(settings)))
    return {"session_id": session_id, "status": "planned", "case_count": len(cases), "planned_run_count": len(cases) * repetitions, "resolution": {"width": output_width, "height": output_height} if output_width else None}



def create_followup_session(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    source_session_id = _text(data.get("source_session_id"), "원본 테스트 세션")
    raw_case_ids = data.get("case_version_ids") or []
    if not isinstance(raw_case_ids, list):
        raise ValueError("재시험 케이스 목록 형식이 올바르지 않습니다.")
    case_ids = list(dict.fromkeys(str(value or "").strip() for value in raw_case_ids if str(value or "").strip()))
    if not case_ids:
        raise ValueError("재시험할 케이스를 한 개 이상 선택하세요.")
    try:
        repetitions = int(data.get("repetitions") or 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("반복 횟수는 숫자여야 합니다.") from exc
    if repetitions < 1 or repetitions > 10:
        raise ValueError("반복 횟수는 1~10이어야 합니다.")
    now = datetime.now().astimezone().isoformat()
    with open_registry(root) as connection:
        source = connection.execute(
            "SELECT * FROM test_sessions WHERE session_id=?", (source_session_id,)
        ).fetchone()
        if not source:
            raise FileNotFoundError("원본 테스트 세션을 찾을 수 없습니다.")
        available = {
            row["case_version_id"]: dict(row)
            for row in connection.execute(
                "SELECT case_version_id,ordering,settings_json FROM test_session_cases WHERE session_id=?",
                (source_session_id,),
            )
        }
        invalid = [case_id for case_id in case_ids if case_id not in available]
        if invalid:
            raise ValueError(f"원본 세션에 없는 케이스입니다: {', '.join(invalid)}")
        session_id = (
            f"test_{datetime.now():%Y%m%d_%H%M%S}_retest_"
            f"{hashlib.sha256(f'{source_session_id}:{case_ids}:{now}'.encode()).hexdigest()[:4]}"
        )
        notes = _text(data.get("notes"), "후속 세션 메모", required=False)
        connection.execute(
            """INSERT INTO test_sessions(
                   session_id,suite_id,model_id,workflow_profile_id,adapter_id,status,
                   repetitions,output_width,output_height,notes,created_at,updated_at
               ) VALUES (?,?,?,?,?,'planned',?,?,?,?,?,?)""",
            (
                session_id,
                source["suite_id"],
                source["model_id"],
                source["workflow_profile_id"],
                source["adapter_id"],
                repetitions,
                source["output_width"],
                source["output_height"],
                notes,
                now,
                now,
            ),
        )
        for ordering, case_id in enumerate(
            sorted(case_ids, key=lambda value: int(available[value]["ordering"])), start=1
        ):
            connection.execute(
                """INSERT INTO test_session_cases(
                       session_id,case_version_id,ordering,status,planned_runs,settings_json
                   ) VALUES (?,?,?,'planned',?,?)""",
                (session_id, case_id, ordering, repetitions, available[case_id]["settings_json"]),
            )
        reason = _text(data.get("reason") or "targeted_retest", "재시험 사유", maximum=500)
        connection.execute(
            "INSERT INTO test_session_lineage(child_session_id,parent_session_id,reason,created_at) VALUES (?,?,?,?)",
            (session_id, source_session_id, reason, now),
        )
        connection.commit()
    return {
        "session_id": session_id,
        "source_session_id": source_session_id,
        "status": "planned",
        "case_count": len(case_ids),
        "planned_run_count": len(case_ids) * repetitions,
    }

def _is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _restore_staged_paths(moved: list[tuple[Path, Path]]) -> None:
    for original, staged in reversed(moved):
        if not staged.exists():
            continue
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged), str(original))


def delete_session(root: Path, session_id: str) -> dict[str, Any]:
    """Remove a terminal test session and its dedicated local artifacts."""
    session_id = _text(session_id, "테스트 세션 ID", maximum=200)
    active_statuses = {"queued", "preparing", "uploading", "submitting", "comfy_queued", "running"}
    root = root.resolve()
    jobs_root = (root / "jobs").resolve()
    batches_root = (root / "runtime" / "batches").resolve()
    comfy_output_root = Path(
        os.environ.get("COMFY_OUTPUT_DIR", str(Path.home() / "ai-workspace/apps/ComfyUI/output"))
    ).expanduser().resolve()
    moved: list[tuple[Path, Path]] = []
    trash_root: Path | None = None
    with open_registry(root) as connection:
        try:
            session = connection.execute("SELECT status FROM test_sessions WHERE session_id=?", (session_id,)).fetchone()
            if not session:
                return {
                    "session_id": session_id,
                    "deleted_run_count": 0,
                    "deleted_review_count": 0,
                    "deleted_job_count": 0,
                    "deleted_output_count": 0,
                    "deleted_batch_count": 0,
                    "files_preserved": False,
                    "already_deleted": True,
                }
            children = [row[0] for row in connection.execute(
                "SELECT child_session_id FROM test_session_lineage WHERE parent_session_id=? ORDER BY child_session_id", (session_id,)
            )]
            if children:
                raise RuntimeError("후속 재시험 세션이 연결된 이력은 먼저 후속 세션부터 삭제하세요: " + ", ".join(children))
            runs = [dict(row) for row in connection.execute(
                """SELECT r.run_id,r.job_id,r.status,r.output_path,r.settings_json
                   FROM test_session_runs sr JOIN generation_runs r ON r.run_id=sr.run_id
                   WHERE sr.session_id=?""",
                (session_id,),
            )]
            active = [row["run_id"] for row in runs if str(row["status"]) in active_statuses]
            if str(session["status"]) in active_statuses or active:
                raise RuntimeError("실행 중이거나 큐 대기 중인 테스트 세션은 삭제할 수 없습니다. 먼저 작업 종료 후 삭제하세요.")

            batch_row = connection.execute(
                "SELECT batch_id FROM test_session_batches WHERE session_id=?", (session_id,)
            ).fetchone()
            targets: set[Path] = set()
            job_dirs: set[Path] = set()
            output_files: set[Path] = set()
            for run in runs:
                job_id = str(run.get("job_id") or "").strip()
                if job_id:
                    if Path(job_id).name != job_id:
                        raise RuntimeError(f"안전하지 않은 job ID가 기록되어 삭제를 중단했습니다: {job_id}")
                    job_dir = (jobs_root / job_id).resolve()
                    if not _is_within(job_dir, jobs_root):
                        raise RuntimeError(f"허용되지 않은 job 경로라 삭제를 중단했습니다: {job_dir}")
                    job_dirs.add(job_dir)
                recorded_outputs: list[str] = []
                if run.get("output_path"):
                    recorded_outputs.append(str(run["output_path"]))
                try:
                    settings = json.loads(run.get("settings_json") or "{}")
                except (TypeError, json.JSONDecodeError):
                    settings = {}
                for output in settings.get("outputs") or []:
                    if not isinstance(output, dict):
                        continue
                    if output.get("local_path"):
                        recorded_outputs.append(str(output["local_path"]))
                    elif str(output.get("type") or "output") == "output" and output.get("filename"):
                        recorded_outputs.append(str(comfy_output_root / str(output.get("subfolder") or "") / str(output["filename"])))
                for raw_path in recorded_outputs:
                    path = Path(raw_path).expanduser().resolve()
                    if not (_is_within(path, comfy_output_root) or _is_within(path, jobs_root)):
                        raise RuntimeError(f"허용되지 않은 출력 경로라 삭제를 중단했습니다: {path}")
                    output_files.add(path)

            targets.update(job_dirs)
            targets.update(output_files)
            batch_dir: Path | None = None
            if batch_row:
                batch_id = str(batch_row["batch_id"] or "").strip()
                if Path(batch_id).name != batch_id:
                    raise RuntimeError(f"안전하지 않은 batch ID가 기록되어 삭제를 중단했습니다: {batch_id}")
                batch_dir = (batches_root / batch_id).resolve()
                if not _is_within(batch_dir, batches_root):
                    raise RuntimeError(f"허용되지 않은 batch 경로라 삭제를 중단했습니다: {batch_dir}")
                targets.add(batch_dir)

            existing = sorted((path for path in targets if path.exists()), key=lambda path: len(path.parts))
            independent = [path for path in existing if not any(parent in path.parents for parent in existing)]
            trash_root = root / "runtime" / "model_test_delete_trash" / (
                f"{session_id}_{datetime.now():%Y%m%d_%H%M%S_%f}"
            )
            trash_root.mkdir(parents=True, exist_ok=False)
            for index, original in enumerate(independent):
                staged = trash_root / f"{index:04d}" / original.name
                staged.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(original), str(staged))
                moved.append((original, staged))

            run_ids = [str(row["run_id"]) for row in runs]
            review_count = 0
            if run_ids:
                placeholders = ",".join("?" for _ in run_ids)
                review_count = int(connection.execute(f"SELECT COUNT(*) FROM reviews WHERE run_id IN ({placeholders})", run_ids).fetchone()[0])
                connection.execute(f"DELETE FROM capability_scores WHERE review_version_id IN (SELECT review_version_id FROM reviews WHERE run_id IN ({placeholders}))", run_ids)
                connection.execute(f"DELETE FROM reviews WHERE run_id IN ({placeholders})", run_ids)
            connection.execute("DELETE FROM test_sessions WHERE session_id=?", (session_id,))
            if run_ids:
                placeholders = ",".join("?" for _ in run_ids)
                connection.execute(f"DELETE FROM generation_runs WHERE run_id IN ({placeholders})", run_ids)
            connection.commit()
        except Exception:
            connection.rollback()
            _restore_staged_paths(moved)
            if trash_root and trash_root.exists():
                shutil.rmtree(trash_root, ignore_errors=True)
            raise

    if trash_root and trash_root.exists():
        shutil.rmtree(trash_root)
    return {
        "session_id": session_id,
        "deleted_run_count": len(runs),
        "deleted_review_count": review_count,
        "deleted_job_count": sum(1 for path in job_dirs if path in existing),
        "deleted_output_count": sum(1 for path in output_files if path in existing and not any(job in path.parents for job in job_dirs)),
        "deleted_batch_count": int(bool(batch_dir and batch_dir in existing)),
        "files_preserved": False,
    }

def ensure_h3_r2v_adapter(root: Path, workflow_dir: Path) -> dict[str, Any] | None:
    workflow_path = workflow_dir / model_test_r2v.R2V_WORKFLOW_FILENAME
    if not workflow_path.is_file():
        return None
    with open_registry(root) as connection:
        candidates = [dict(row) for row in connection.execute(
            "SELECT model_id,provider,family,display_name,version FROM models"
        )]
    h3_models = []
    for model in candidates:
        identity = " ".join(str(model.get(key) or "") for key in ("provider", "family", "display_name", "version")).lower()
        if "minimax" in identity and re.search(r"(^|[^a-z0-9])h3([^a-z0-9]|$)", identity):
            h3_models.append(model)
    result = None
    for model in h3_models:
        profile = register_workflow(root, workflow_dir, {
            "model_id": model["model_id"],
            "workflow_filename": model_test_r2v.R2V_WORKFLOW_FILENAME,
            "name": "MiniMax H3 R2V API baseline",
            "profile_kind": "official_baseline",
            "notes": "10 모델 테스트 전용 다중 Reference-to-Video 기준 워크플로우",
        })
        with open_registry(root) as connection:
            result = workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": profile["workflow_profile_id"],
                "adapter_name": "MiniMax H3 R2V multi-reference",
                "adapter_version": "1",
                "bindings": {
                    "prompt": {"node_id": "138", "input": "value"},
                    "seed": {"node_id": "129", "input": "noise_seed"},
                    "width": {"node_id": "141", "input": "value"},
                    "height": {"node_id": "142", "input": "value"},
                    "duration_seconds": {"node_id": "132", "input": "value"},
                    "filename_prefix": {"node_id": "92", "input": "filename_prefix"},
                },
                "multi_reference": {
                    "conditioning_node_id": "136",
                    "input_prefix": "ref_images.ref_image_",
                    "loader_node_ids": ["139", "137"],
                    "loader_template_node_id": "137",
                    "loader_input": "image",
                    "max_slots": 9,
                },
                "defaults": {"width": 832, "height": 480, "fps": 24},
            })
    return result


def dashboard(root: Path, workflow_dir: Path) -> dict[str, Any]:
    ensure_h3_r2v_adapter(root, workflow_dir)
    with open_registry(root) as connection:
        models = [dict(row) for row in connection.execute("SELECT model_id,provider,family,display_name,version,checkpoint_sha256,source_url,license_name FROM models ORDER BY display_name")]
        workflows = [dict(row) for row in connection.execute("SELECT workflow_profile_id,model_id,name,profile_kind,workflow_filename,workflow_sha256,workflow_format,source_url,notes,created_at FROM workflow_profiles ORDER BY created_at DESC")]
        adapters = [dict(row) for row in connection.execute("SELECT adapter_id,workflow_profile_id,adapter_name,adapter_version,config_json,created_at FROM workflow_adapters ORDER BY created_at DESC")]
        for adapter in adapters:
            adapter["config"] = json.loads(adapter.pop("config_json"))
            adapter["input_mode"] = ("h3_r2v_multi_reference" if adapter["config"].get("multi_reference") else ("i2v" if "reference_image" in adapter["config"].get("bindings", {}) else "text_only"))
        suites = []
        for row in connection.execute(
            """SELECT * FROM benchmark_suites WHERE active=1
               ORDER BY CASE WHEN suite_id=? THEN 0 ELSE 1 END,version DESC""",
            (I2V_SUITE_ID,),
        ):
            suite = dict(row)
            if row["suite_id"] == I2V_SUITE_ID:
                suite["input_mode"] = "i2v_fixed_anchor"
            elif row["suite_id"] in model_test_r2v.R2V_SUITE_IDS:
                suite["input_mode"] = "h3_r2v_multi_reference"
            else:
                suite["input_mode"] = "mixed"
            suite["recommended"] = row["suite_id"] == I2V_SUITE_ID
            suite["cases"] = [dict(item) for item in connection.execute("""SELECT v.case_version_id,v.title,v.intent_ko,v.category,v.tier,v.contract_json,s.ordering FROM suite_cases s JOIN benchmark_case_versions v ON v.case_version_id=s.case_version_id WHERE s.suite_id=? AND s.enabled=1 ORDER BY s.ordering""", (row["suite_id"],))]
            for case in suite["cases"]:
                case["contract"] = json.loads(case.pop("contract_json"))
                case["prompts"] = [dict(item) for item in connection.execute(
                    """SELECT language,prompt_kind,prompt_text,prompt_sha256
                       FROM benchmark_case_prompts WHERE case_version_id=?
                       ORDER BY language,prompt_kind""",
                    (case["case_version_id"],),
                )]
                case["asset_requirements"] = [dict(item) for item in connection.execute(
                    """SELECT role,kind,minimum_count,description
                       FROM benchmark_case_asset_requirements WHERE case_version_id=?
                       ORDER BY role""",
                    (case["case_version_id"],),
                )]
            suites.append(suite)
        sessions = [dict(row) for row in connection.execute("""SELECT s.*,m.display_name model_name,w.name workflow_name,w.profile_kind,(SELECT COUNT(*) FROM test_session_cases c WHERE c.session_id=s.session_id) case_count FROM test_sessions s JOIN models m ON m.model_id=s.model_id JOIN workflow_profiles w ON w.workflow_profile_id=s.workflow_profile_id ORDER BY s.created_at DESC LIMIT 100""")]
        for session in sessions:
            batch_link = connection.execute(
                "SELECT batch_id,queued_at FROM test_session_batches WHERE session_id=?",
                (session["session_id"],),
            ).fetchone()
            session["batch_id"] = batch_link["batch_id"] if batch_link else None
            lineage = connection.execute(
                "SELECT parent_session_id,reason FROM test_session_lineage WHERE child_session_id=?",
                (session["session_id"],),
            ).fetchone()
            session["parent_session_id"] = lineage["parent_session_id"] if lineage else None
            session["retest_reason"] = lineage["reason"] if lineage else None
            session["resolution"] = (
                {"width": session["output_width"], "height": session["output_height"]}
                if session["output_width"] and session["output_height"] else None
            )
            counts = connection.execute(
                """SELECT COUNT(*) total,
                          SUM(CASE WHEN r.status='completed' THEN 1 ELSE 0 END) completed,
                          SUM(CASE WHEN r.status='failed' THEN 1 ELSE 0 END) failed
                   FROM test_session_runs sr JOIN generation_runs r ON r.run_id=sr.run_id
                   WHERE sr.session_id=?""",
                (session["session_id"],),
            ).fetchone()
            session["run_count"] = int(counts["total"] or 0)
            session["completed_run_count"] = int(counts["completed"] or 0)
            session["failed_run_count"] = int(counts["failed"] or 0)

        assets = model_test_assets.case_assets(connection)
        r2v_shared_asset_groups = model_test_assets.r2v_shared_groups(connection)
        asset_requirements = [dict(row) for row in connection.execute("SELECT case_version_id,role,kind,minimum_count,description FROM benchmark_case_asset_requirements ORDER BY case_version_id,role")]
    return {"schema_version": evaluation_db.SCHEMA_VERSION, "models": models, "workflows": workflows, "adapters": adapters, "case_assets": assets, "case_asset_requirements": asset_requirements, "r2v_shared_asset_groups": r2v_shared_asset_groups, "available_workflows": available_workflows(workflow_dir), "suites": suites, "sessions": sessions}
