from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from h3_prompt_projects import project_clips


PROJECT_IDS = (
    "RaisingaDragonSeason01_EP00_H3_R2V_V2",
    "RaisingaDragonSeason01_EP01_H3_R2V_V2",
)

EP00_WRIST_KEEP = {"EP00-S05-NC01"}
EP01_WRIST_KEEP = {
    "EP01-S03-NC07",
    "EP01-S03-NC09",
    "EP01-S04-NC04",
    "EP01-S05-NC05",
    "EP01-S05-NC08",
}

EP00_ROOT = "assets/reference_sheets_v3"
EP01_ROOT = "assets/reference_sheets_v3"

EP00_DEFAULTS = {
    "assets/Lua_Awakened_NEUTRAL_V2.png": f"{EP00_ROOT}/characters/Lua_Awakened_REFERENCE_SHEET_V3.png",
    "assets/spear_NEUTRAL_V2.png": f"{EP00_ROOT}/props/Dragon_Spear_REFERENCE_SHEET_V3.png",
    "assets/Dragon_Heart_Wrist_Mark_NEUTRAL_V2.png": f"{EP00_ROOT}/details/Dragon_Heart_Wrist_Mark_REFERENCE_SHEET_V3.png",
}

EP01_DEFAULTS = {
    "assets/Lua_NEUTRAL_V2.png": f"{EP01_ROOT}/characters/Lua_REFERENCE_SHEET_V3.png",
    "assets/YoungMir_NEUTRAL_V2.png": f"{EP01_ROOT}/creatures/Young_Mir_REFERENCE_SHEET_V3.png",
    "assets/old_fisherman_NEUTRAL_V2.png": f"{EP01_ROOT}/characters/Old_Fisherman_REFERENCE_SHEET_V3.png",
    "assets/villageChild01_NEUTRAL_V2.png": f"{EP01_ROOT}/characters/Village_Child_1_REFERENCE_SHEET_V3.png",
    "assets/village_child_2_NEUTRAL_V2.png": f"{EP01_ROOT}/characters/Village_Child_2_REFERENCE_SHEET_V3.png",
    "assets/village_adult1_NEUTRAL_V2.png": f"{EP01_ROOT}/characters/Village_Adult_1_REFERENCE_SHEET_V3.png",
    "assets/villager_adult2_NEUTRAL_V2.png": f"{EP01_ROOT}/characters/Village_Adult_2_REFERENCE_SHEET_V3.png",
    "assets/spear_NEUTRAL_V2.png": f"{EP01_ROOT}/props/Dragon_Spear_REFERENCE_SHEET_V3.png",
    "assets/BLACK_JELLYFISH_NEUTRAL_V2.png": f"{EP01_ROOT}/creatures/Black_Jellyfish_REFERENCE_SHEET_V3.png",
    "assets/Heartstone_NEUTRAL_V2.png": f"{EP01_ROOT}/props/Heartstone_REFERENCE_SHEET_V3.png",
    "assets/generated_v3/Dragon_Heart_Wrist_Mark_Lua_Child_NEUTRAL_V2.png": f"{EP01_ROOT}/details/Lua_Child_Wrist_Mark_REFERENCE_SHEET_V3.png",
    "assets/generated_v7/Lua_Mir_Scale_Held_NEUTRAL_V2.png": f"{EP01_ROOT}/relationships/Lua_Mir_HELD_REFERENCE_SHEET_V3.png",
    "assets/generated_v7/Lua_Mir_Scale_Separate_NEUTRAL_V2.png": f"{EP01_ROOT}/relationships/Lua_Mir_SEPARATE_REFERENCE_SHEET_V3.png",
}


def decision(project_id: str, clip_id: str, source_path: str) -> tuple[str, str, str]:
    if project_id.endswith("EP00_H3_R2V_V2"):
        if "Dragon_Heart_Wrist_Mark" in source_path:
            if clip_id in EP00_WRIST_KEEP:
                return (
                    "KEEP_AND_REBUILD_SHEET",
                    EP00_DEFAULTS[source_path],
                    "손목 높이 tracking close에서 문양 위치와 도안이 실제 화면 정보로 읽힌다.",
                )
            return (
                "REMOVE_REFERENCE_KEEP_TEXT",
                "—",
                "맥동·충전 행동은 필요하지만 문양 도안을 판독하는 close-up/insert가 아니다.",
            )
        if source_path.endswith("Dragon_Language_Current_Shield_Effects_NEUTRAL_V2.png"):
            if clip_id == "EP00-S02-NC01":
                return (
                    "KEEP_AND_REBUILD_SHEET",
                    f"{EP00_ROOT}/effects/Current_Ring_FLOOR_REFERENCE_SHEET_V3.png",
                    "실제 바닥 접촉 뒤 수평 원형 해류의 형태와 방향이 사건 결과의 핵심이다.",
                )
            if clip_id in {"EP00-S03-NC02", "EP00-S03-NC03"}:
                return (
                    "KEEP_AND_REBUILD_SHEET",
                    f"{EP00_ROOT}/effects/Current_Shield_VERTICAL_REFERENCE_SHEET_V3.png",
                    "공격점과 Lua 사이의 단일 수직 방어면 형태가 핵심 사건이다.",
                )
            return (
                "REMOVE_REFERENCE_KEEP_TEXT",
                "—",
                "형태 없는 이동 해류·창끝 압축은 Shot의 물리 서술로 충분하고 혼합 effect 시트가 방향을 오염시킨다.",
            )
        if source_path.endswith("Abyss_Hound_Full_Reference_NEUTRAL_V2.png"):
            return (
                "KEEP_AND_REBUILD_SHEET",
                "assets/enemies/Deep_Sea_King_Full_Reference_NEUTRAL_V2.png",
                "EP00의 적을 하나의 거대한 Deep Sea King으로 통일한다. 기존 꼬리·턱 액션은 같은 본체에 연결된 나뭇가지형 팔·손 공격으로 재해석한다.",
            )
        if source_path.endswith("Deep_Sea_King_Full_Reference_NEUTRAL_V2.png"):
            return (
                "KEEP_AND_REBUILD_SHEET",
                "assets/enemies/Deep_Sea_King_Full_Reference_NEUTRAL_V2.png",
                "Deep Sea King 전체 시트로 하나의 웅장한 본체, 고정된 거대 스케일, 본체에 연결된 나뭇가지형 팔과 뿌리 맨틀을 유지한다.",
            )
        return (
            "KEEP_AND_REBUILD_SHEET",
            EP00_DEFAULTS[source_path],
            "화면에서 정체성 또는 고유 소품 구조가 지속적으로 판독된다.",
        )

    if source_path.endswith("Dragon_Heart_Wrist_Mark_Lua_Child_NEUTRAL_V2.png"):
        if clip_id in EP01_WRIST_KEEP:
            return (
                "KEEP_AND_REBUILD_SHEET",
                EP01_DEFAULTS[source_path],
                "문양 생성·확인·접촉이 close-up 또는 insert에서 실제 도안 정보로 읽힌다.",
            )
        return (
            "REMOVE_REFERENCE_KEEP_TEXT",
            "—",
            "동기 맥동은 필요하지만 문양 도안을 읽는 close-up/insert가 아니므로 텍스트로 유지한다.",
        )
    if source_path.endswith("Lua_Eye_Cave_Reflection_V1.png"):
        return (
            "KEEP_AND_REBUILD_SHEET",
            source_path,
            "사건 정보를 담은 완성 eye/cave reflection insert 예외이며 시트로 변환하지 않고 원본을 유지한다.",
        )
    return (
        "KEEP_AND_REBUILD_SHEET",
        EP01_DEFAULTS[source_path],
        "화면에서 정확한 정체성, 고유 구조 또는 Lua·Mir의 상대 크기·접촉 관계가 판독된다.",
    )


def actual_shots(prompt: str, subject_index: int) -> str:
    match = re.search(
        rf"^<Subject {subject_index}> \((.*?)\):",
        prompt,
        flags=re.MULTILINE,
    )
    if not match:
        return "프롬프트 정의만 존재"
    value = match.group(1)
    shots = re.findall(r"\[Shot [^\]]+\]", value)
    return ", ".join(shots) if shots else value


def screen_size(prompt: str, subject_index: int) -> str:
    tag = f"<Subject {subject_index}>"
    shot_lines = [line for line in prompt.splitlines() if line.startswith("[Shot") and tag in line]
    sizes: list[str] = []
    for line in shot_lines:
        lowered = line.lower()
        for name in ("macro", "extreme insert", "insert", "close", "medium", "wide", "full"):
            if name in lowered and name not in sizes:
                sizes.append(name)
    return ", ".join(sizes) if sizes else "정의된 Shot 구도"


def build(project_id: str) -> None:
    project = ROOT / "prompt_projects" / project_id
    rows: list[str] = []
    counts = {
        "KEEP_AND_REBUILD_SHEET": 0,
        "REMOVE_REFERENCE_KEEP_TEXT": 0,
        "REMOVE_UNUSED": 0,
    }
    for clip in project_clips(ROOT, project_id)["clips"]:
        for reference in clip["references"]:
            source_path = str(reference.get("source_path") or "")
            if source_path.startswith("backgrounds/"):
                continue
            verdict, target, reason = decision(project_id, clip["clip_id"], source_path)
            counts[verdict] += 1
            current = f"Picture {reference['picture_index']} `{source_path}`"
            role = f"`{reference['role']}`"
            shots = actual_shots(clip["video_prompt"], reference["picture_index"])
            size = screen_size(clip["video_prompt"], reference["picture_index"])
            replacement = f"`{target}`" if target != "—" else "—"
            rows.append(
                f"| `{clip['clip_id']}` | {current} | {role} | {shots} | {size} | `{verdict}` | {replacement} | {reason} |"
            )

    episode = "EP00" if "EP00" in project_id else "EP01"
    text = f"""# {episode} Reference Requirement Audit V3

## 범위와 판정 원칙

- `{project_id}`의 모든 Clip Machine Payload와 Picture Plan을 파싱하고 Shot별 Subject 사용을 대조했다.
- 환경 Picture는 기존 공간 앵커로 유지하므로 아래 비환경 감사표의 판정 대상에서 제외했다. 연결 단계에서는 환경을 Picture 1부터 우선 배치한다.
- `Lua_Eye_Cave_Reflection_V1.png`은 의미 보존 insert 예외로서 경로를 유지한다. 표의 `KEEP_AND_REBUILD_SHEET`는 이 한 항목에 한해 “승인된 의미 예외 유지”를 뜻한다.
- 판정 집계: `KEEP_AND_REBUILD_SHEET` {counts['KEEP_AND_REBUILD_SHEET']} instance, `REMOVE_REFERENCE_KEEP_TEXT` {counts['REMOVE_REFERENCE_KEEP_TEXT']} instance, `REMOVE_UNUSED` {counts['REMOVE_UNUSED']} instance.

| Clip | 현재 Picture | 역할 | 실제 화면 사용 Shot | 화면 크기 | 판정 | 교체 시트 | 사유 |
| --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(rows)}
"""
    (project / "REFERENCE_REQUIREMENT_AUDIT_V3.md").write_text(text, encoding="utf-8")


def main() -> None:
    for project_id in PROJECT_IDS:
        build(project_id)


if __name__ == "__main__":
    main()
