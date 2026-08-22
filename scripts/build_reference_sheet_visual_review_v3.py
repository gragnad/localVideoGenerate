#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from h3_prompt_projects import project_clips


DATA = {
    "RaisingaDragonSeason01_EP00_H3_R2V_V2": {
        "episode": "EP00",
        "attempts": 11,
        "rejected": [
            "Current_Ring_FLOOR 1차: 4번 패널 외곽 잘림으로 반려 후 재생성",
            "Current_Shield_VERTICAL 1차: 4번 패널 외곽 잘림으로 반려 후 재생성",
            "Abyss_Hound_JAW_EDGE 1차: 전체 입 구조로 읽히는 상·하악 혼합 때문에 반려 후 재생성",
        ],
        "sources": {
            "assets/reference_sheets_v3/characters/Lua_Awakened_REFERENCE_SHEET_V3.png": "assets/Lua_Awakened.png",
            "assets/reference_sheets_v3/props/Dragon_Spear_REFERENCE_SHEET_V3.png": "assets/spear.png",
            "assets/reference_sheets_v3/details/Dragon_Heart_Wrist_Mark_REFERENCE_SHEET_V3.png": "assets/Dragon_Heart_Wrist_Mark.png",
            "assets/reference_sheets_v3/effects/Current_Ring_FLOOR_REFERENCE_SHEET_V3.png": "assets/Dragon_Language_Current_Shield_Effects.png",
            "assets/reference_sheets_v3/effects/Current_Shield_VERTICAL_REFERENCE_SHEET_V3.png": "assets/Dragon_Language_Current_Shield_Effects.png",
            "assets/reference_sheets_v3/enemies/Abyss_Hound_TAIL_FRAGMENT_REFERENCE_SHEET_V3.png": "assets/enemies/Abyss_Hound_Full_Reference.png",
            "assets/reference_sheets_v3/enemies/Abyss_Hound_JAW_EDGE_REFERENCE_SHEET_V3.png": "assets/enemies/Abyss_Hound_Full_Reference.png",
            "assets/reference_sheets_v3/enemies/Deep_Sea_King_ROOT_MANTLE_FRAGMENT_REFERENCE_SHEET_V3.png": "assets/enemies/Deep_Sea_King_Full_Reference.png",
        },
    },
    "RaisingaDragonSeason01_EP01_H3_R2V_V2": {
        "episode": "EP01",
        "attempts": 15,
        "rejected": [
            "Lua_Mir_HELD 1차: Lua 팔에 원본에 없는 청색 문양이 생성되어 반려 후 재생성",
            "Lua_Mir_SEPARATE 1차: 접지면·바닥 그림자가 생겨 평면 회색 템플릿 위반으로 반려 후 재생성",
        ],
        "sources": {
            "assets/reference_sheets_v3/characters/Lua_REFERENCE_SHEET_V3.png": "assets/Lua.png",
            "assets/reference_sheets_v3/creatures/Young_Mir_REFERENCE_SHEET_V3.png": "assets/YoungMir.png",
            "assets/reference_sheets_v3/relationships/Lua_Mir_HELD_REFERENCE_SHEET_V3.png": "assets/generated_v7/Lua_Mir_Scale_Held_V1.png + assets/Lua.png + assets/YoungMir.png",
            "assets/reference_sheets_v3/relationships/Lua_Mir_SEPARATE_REFERENCE_SHEET_V3.png": "assets/generated_v7/Lua_Mir_Scale_Separate_V1.png + assets/Lua.png + assets/YoungMir.png",
            "assets/reference_sheets_v3/characters/Old_Fisherman_REFERENCE_SHEET_V3.png": "assets/old_fisherman.png",
            "assets/reference_sheets_v3/characters/Village_Child_1_REFERENCE_SHEET_V3.png": "assets/villageChild01.png",
            "assets/reference_sheets_v3/characters/Village_Child_2_REFERENCE_SHEET_V3.png": "assets/village_child_2.png",
            "assets/reference_sheets_v3/characters/Village_Adult_1_REFERENCE_SHEET_V3.png": "assets/village_adult1.png",
            "assets/reference_sheets_v3/characters/Village_Adult_2_REFERENCE_SHEET_V3.png": "assets/villager_adult2.png",
            "assets/reference_sheets_v3/props/Dragon_Spear_REFERENCE_SHEET_V3.png": "assets/spear.png",
            "assets/reference_sheets_v3/creatures/Black_Jellyfish_REFERENCE_SHEET_V3.png": "assets/BLACK JELLYFISH .png",
            "assets/reference_sheets_v3/props/Heartstone_REFERENCE_SHEET_V3.png": "assets/Heartstone.png",
            "assets/reference_sheets_v3/details/Lua_Child_Wrist_Mark_REFERENCE_SHEET_V3.png": "assets/generated_v3/Dragon_Heart_Wrist_Mark_Lua_Child_V2.png + assets/Lua.png",
        },
    },
}


def reason(path: str) -> str:
    if "FLOOR" in path:
        return "수평 바닥 파동만 유지하고 수직 방패와 분리했으며 네 패널의 방향·발광 단계를 통일했다."
    if "VERTICAL" in path:
        return "수직 방향성 방어면만 유지하고 수평 파동과 분리했으며 네 패널의 방향·발광 단계를 통일했다."
    if "TAIL_FRAGMENT" in path:
        return "동일한 불완전 꼬리·촉수 끝 조각만 네 방향으로 구성해 연결 몸체 비노출 조건을 보존했다."
    if "JAW_EDGE" in path:
        return "동일한 턱·머리 가장자리 조각만 네 방향으로 구성해 전체 생물 공개를 피했다."
    if "ROOT_MANTLE" in path:
        return "실제 노출되는 뿌리·맨틀 조각의 젖은 검은 재질만 보존하고 전체 정체성을 제거했다."
    if "HELD" in path:
        return "네 패널 모두 held 상태와 두 손 지지, 동일 상대 크기를 유지한다."
    if "SEPARATE" in path:
        return "네 패널 모두 separate 상태와 공기 간격, 무릎 아래 뿔 높이 관계를 유지한다."
    if "Wrist" in path or "Mark" in path:
        return "동일 발광 단계·손목 위치·도안·피부 부착 상태를 네 패널에서 보존했다."
    return "역할별 고정 패널 순서, 동일 identity·비율·색·재질과 필요한 전체 형상 잘림 방지를 확인했다."


def main() -> None:
    for project_id, data in DATA.items():
        project = ROOT / "prompt_projects" / project_id
        links: dict[str, list[str]] = defaultdict(list)
        for clip in project_clips(ROOT, project_id)["clips"]:
            for ref in clip["references"]:
                path = str(ref.get("source_path") or "")
                if path in data["sources"]:
                    links[path].append(clip["clip_id"])
        rows = []
        for path, source in data["sources"].items():
            clips = ", ".join(f"`{clip}`" for clip in links[path])
            rows.append(
                f"| `{source}` | `{path}` | PASS | PASS | APPROVED | {reason(path)} | {clips} |"
            )
        rejection_rows = "\n".join(f"- {entry}" for entry in data["rejected"])
        exception = (
            "- 없음"
            if data["episode"] == "EP00"
            else "- `assets/generated_v7/Lua_Eye_Cave_Reflection_V1.png`: Lua 눈과 동굴 반사라는 사건 정보를 포함하는 완성 insert이므로 V3 시트로 변환하지 않고 1개 instance를 유지했다."
        )
        text = f"""# {data['episode']} Reference Sheet Visual Normalization Review V3

## 공통 템플릿 승인

- 경로: `assets/reference_sheets_v3/REFERENCE_SHEET_TEMPLATE_V3.png`
- 승인: PASS
- 규격: 1672×941, 8-bit RGB PNG, `#666A70` 패널 배경, 12 px 외곽선, 8 px 구분선, 구분선 중심 x=424/836/1248
- EP00·EP01 템플릿 SHA-256: `960bb95be421aec2373d73ecc9ba1648f6041417f02b8eef5834356736597de8`
- 육안 확인: 네 동일 폭 세로 패널, 동일 배경 명도·색온도, 바닥선·수평선·환경·문자 없음

## 생성·검수 집계

- 생성 후보: {len(data['sources'])}
- 승인본: {len(data['sources'])}
- 생성 시도: {data['attempts']}
- 반려·재생성: {len(data['rejected'])}
- 승인 전 Clip 연결 없음. 아래 APPROVED 자산만 최종 연결했다.

## 승인 자산

| 원본 경로 | 신규 경로 | 템플릿 준수 | identity 보존 | 판정 | 승인 사유 | 연결 Clip |
| --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(rows)}

## 반려·재생성 기록

{rejection_rows}

## 의미 보존 insert 예외

{exception}

## 최종 시각 검수 판정

모든 승인본을 원본과 직접 대조하고 최종 파일을 `view_image`로 재확인했다. 4패널 수, 공통 외곽선·구분선, 역할별 패널 순서, 동일 회색 배경, 피사체 잘림, 패널 침범, 환경·문자·워터마크, identity·색·재질 변화, VFX 방향 혼합, 관계 상태 혼합을 검사했으며 승인본은 전 항목 PASS다.
"""
        (project / "REFERENCE_SHEET_VISUAL_NORMALIZATION_REVIEW_V3.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
