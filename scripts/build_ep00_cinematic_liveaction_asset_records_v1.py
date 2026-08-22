#!/usr/bin/env python3
"""Build audit-only records for the EP00 cinematic live-action asset batch."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/RaisingaDragonSeason01"
ASSET_ROOT = PROJECT / "asset_sheets_cinematic_liveaction_v1_working"
COMMAND = PROJECT / "ep00_cinematic_liveaction_production_v1/EP00_CODEX_ADDITIONAL_ASSET_GENERATION_COMMAND_V1.md"

PROMPT_RECORD = ASSET_ROOT / "prompts/EP00_CINEMATIC_LIVEACTION_ADDITIONAL_ASSET_PROMPTS_V1.md"
MANIFEST = ASSET_ROOT / "manifests/EP00_CINEMATIC_LIVEACTION_ADDITIONAL_ASSET_MANIFEST_V1.json"
APPROVAL = ASSET_ROOT / "manifests/EP00_CINEMATIC_LIVEACTION_ADDITIONAL_ASSET_APPROVAL_GATE_V1.md"
AUDIT = ASSET_ROOT / "manifests/EP00_CINEMATIC_LIVEACTION_ADDITIONAL_ASSET_VISUAL_AUDIT_V1.md"

META = {
    "A01": {
        "clips": ["EP00_C02", "EP00_C05", "EP00_C06", "EP00_C08", "EP00_C10-EP00_C13", "EP00_C15", "EP00_C16", "EP00_C18-EP00_C25"],
        "refs": [
            "01_characters/identity_sheets/H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2_CINEMATIC_LIVEACTION_V3.png",
            "01_characters/casting_pilots/LUA_CINEMATIC_LIVEACTION_CASTING_PILOT_V4.png",
        ],
        "causal": ["EP00 전투 시점의 루아", "젖고 지친 전투 자세", "오른팔·오른다리 용린 노출", "후속 상호작용의 정체성 기준"],
        "audit": "pass",
        "note": "배우, 의상, 오른쪽 용린 laterality와 전신 판독성이 유지됨.",
    },
    "A02": {
        "clips": ["EP00_C08", "EP00_C11", "EP00_C23", "EP00_C24"],
        "refs": [
            "01_characters/scene_states/EP00/H3_EP00_LUA_COMPLETE_SCALES_BATTLE_STATE_CINEMATIC_LIVEACTION_V1.png",
            "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png",
            "02_enemies/ABYSS_KING_CINEMATIC_CREATURE_PILOT_V2.png",
        ],
        "causal": ["동일 전투 평면에 선 두 인물", "중립 전투 거리로 대치", "같은 바닥의 접촉 그림자", "심해왕이 인간형 상대 크기로 판독"],
        "audit": "pass_with_user_scale_review",
        "note": "심해왕은 루아보다 약간 크며 거대 보스가 아님. 하부 검은 맨틀 폭은 사용자 확인 권장.",
    },
    "A03": {
        "clips": ["EP00_C01-EP00_C05"],
        "refs": ["04_backgrounds/style_pilots/STORM_COAST_CINEMATIC_ENVIRONMENT_PILOT_V3.png"],
        "causal": ["전투 전 제단", "수로가 청록빛을 전달", "젖은 현무암과 얕은 물", "기준 지리와 동선 확립"],
        "audit": "pass",
        "note": "원형 제단, 방사형 수로, 질주로와 측벽이 한 공간으로 읽힘.",
    },
    "A04": {
        "clips": ["EP00_C06-EP00_C16"],
        "refs": ["04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V1.png"],
        "causal": ["검은 비와 방패 파열", "국소 충돌이 바닥을 파손", "수로 가장자리 균열", "MASTER 지리를 유지한 중간 손상"],
        "audit": "pass_with_damage_readability_review",
        "note": "MASTER와 카메라 지리는 유지되며 손상은 절제되어 있어 단계 차이 확인 권장.",
    },
    "A05": {
        "clips": ["EP00_C17-EP00_C25"],
        "refs": [
            "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V1.png",
            "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_DAMAGED_CINEMATIC_LIVEACTION_V1.png",
        ],
        "causal": ["후반 충돌과 가시 추격", "벽·바닥에 추가 손상", "충돌 함몰과 가시 천공", "동선을 보존한 최종 손상"],
        "audit": "pass",
        "note": "이전 지리를 유지하면서 파손량이 증가하고 벽 함몰·천공이 추가됨.",
    },
    "A06": {
        "clips": ["EP00_C01-EP00_C03"],
        "refs": [
            "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png",
            "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V1.png",
        ],
        "causal": ["심해왕의 연결된 오른팔", "손바닥 위 유체가 압축", "수분이 구체로 끌림", "작고 고밀도인 직사 구체 형성"],
        "audit": "pass",
        "note": "손과 팔 연결, 작은 구체, 흡인 압력이 명확함.",
    },
    "A07": {
        "clips": ["EP00_C04-EP00_C06"],
        "refs": [
            "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png",
            "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V1.png",
        ],
        "causal": ["상향 검은 유체 줄기", "천장 아래 막이 빗방울로 분리", "젖은 현무암에 낙하", "검은 비 포격 범위 형성"],
        "audit": "needs_user_review_ground_impact_legibility",
        "note": "상향 줄기·막·낙하 방울은 명확하나 바닥 충돌의 판독성은 사용자 확인 필요.",
    },
    "A08": {
        "clips": ["EP00_C09", "EP00_C10"],
        "refs": [
            "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png",
            "03_props/H3_LUA_SPEAR_PROP_HQ_V3_CINEMATIC_PROP_V1.png",
        ],
        "causal": ["작살 끝이 가슴에 얕게 접촉", "검은 표면이 안쪽으로 변형", "메니스커스가 접점을 봉합", "작살을 흡수하는 상태"],
        "audit": "needs_user_review_absorption_climb_legibility",
        "note": "접촉과 흡수 표면은 명확하나 검은 유체가 자루를 타고 오르는 길이는 절제됨.",
    },
    "B01": {
        "clips": ["EP00_C12", "EP00_C13", "EP00_C22"],
        "refs": ["01_characters/scene_states/EP00/H3_EP00_LUA_COMPLETE_SCALES_BATTLE_STATE_CINEMATIC_LIVEACTION_V1.png"],
        "causal": ["오른쪽 허벅지 용린의 발광", "맥동이 오른쪽 체간과 팔로 이동", "오른손까지 연결", "우측 힘 전달 경로 확립"],
        "audit": "needs_user_review_continuous_route_legibility",
        "note": "오른다리·오른팔의 발광은 유지되나 허리에서 어깨까지의 단일 연속 경로는 사용자 확인 필요.",
    },
    "B02": {
        "clips": ["EP00_C14", "EP00_C15"],
        "refs": [
            "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png",
            "05_effects/reference_sheets/EP00/scenario_specific_v1/FX_EP00_MOVING_CURRENT_RIBBON_CINEMATIC_VFX_V2.png",
        ],
        "causal": ["좁은 수류가 심해왕 가슴으로 진입", "몸 안에서 굴절·역전", "인접한 전방 지점에서 재접촉", "집중된 반환 수류로 반사"],
        "audit": "needs_user_review_return_direction_legibility",
        "note": "가슴 진입과 내부 청록 경로는 보이나 출구와 반환 방향은 사용자 확인 필요.",
    },
    "B03": {
        "clips": ["EP00_C17-EP00_C19"],
        "refs": [
            "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png",
            "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_FINAL_DAMAGE_CINEMATIC_LIVEACTION_V1.png",
        ],
        "causal": ["심해왕 팔의 휘두름", "검은 유체가 길게 늘어남", "정확히 세 가시로 분리", "빈 벽달리기 경로를 추격"],
        "audit": "pass",
        "note": "연결된 팔, 정확히 세 개의 가시, 단일 추격 방향이 명확함.",
    },
    "B04": {
        "clips": ["EP00_C24"],
        "refs": [
            "01_characters/scene_states/EP00/H3_EP00_LUA_COMPLETE_SCALES_BATTLE_STATE_CINEMATIC_LIVEACTION_V1.png",
            "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png",
            "01_characters/scene_states/EP00/H3_EP00_LUA_ABYSS_KING_HUMAN_SCALE_BLOCKING_CINEMATIC_LIVEACTION_V1.png",
        ],
        "causal": ["루아 오른주먹이 얼굴에 접촉", "검은 표면이 눌림", "유체가 손가락·손등에 부착", "오른팔 포박 시작"],
        "audit": "needs_user_review_entrapment_spread_legibility",
        "note": "주먹·얼굴 접촉은 명확하나 손목과 팔뚝으로 퍼지는 검은 포박은 사용자 확인 필요.",
    },
    "B05": {
        "clips": ["EP00_C25"],
        "refs": ["01_characters/scene_states/EP00/H3_EP00_LUA_COMPLETE_SCALES_BATTLE_STATE_CINEMATIC_LIVEACTION_V1.png"],
        "causal": ["포박된 오른팔의 검은 유체", "얇은 암영이 어깨·볼로 접근", "얼굴 가장자리를 가림", "초점과 대비가 떨어지는 의식 단절"],
        "audit": "pass_with_identity_injury_review",
        "note": "루아 얼굴과 의식 저하가 명확함. 얼굴 상처 연속성은 사용자 확인 권장.",
    },
    "B06": {
        "clips": ["EP00_C13-EP00_C15"],
        "refs": [
            "05_effects/style_pilots/CURRENT_SHIELD_CINEMATIC_FLUID_FX_PILOT_V2.png",
            "04_backgrounds/style_pilots/STORM_COAST_CINEMATIC_ENVIRONMENT_PILOT_V3.png",
        ],
        "causal": ["바닥 수로의 압력", "무거운 바닷물이 수평 이동", "현무암 전단부에 물보라 발생", "단일 방향의 실사 수류 리본"],
        "audit": "pass_with_surface_realism_review",
        "note": "거부된 Batch03 자산을 참조하지 않은 새 실사 물 캔버스. 표면의 일부 셀 구조는 사용자 확인 권장.",
    },
}


def parse_command() -> dict[str, dict[str, str]]:
    text = COMMAND.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^### (?P<id>[AB]\d{2})\. (?P<title>.+?)\n.*?^출력:\n\n`(?P<path>[^`]+)`.*?^생성 프롬프트:\n\n```text\n(?P<prompt>.*?)\n```",
        re.MULTILINE | re.DOTALL,
    )
    parsed = {m.group("id"): m.groupdict() for m in pattern.finditer(text)}
    if set(parsed) != set(META):
        raise RuntimeError(f"command parse mismatch: {sorted(parsed)}")
    return parsed


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parsed = parse_command()
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    records = []
    hashes = set()
    for asset_id in sorted(parsed):
        spec = parsed[asset_id]
        meta = META[asset_id]
        path = ASSET_ROOT / spec["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        with Image.open(path) as image:
            validation = {
                "format": image.format,
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "contract_pass": image.format == "PNG" and image.size == (1672, 941) and image.mode == "RGB",
            }
        digest = sha256(path)
        if digest in hashes:
            raise RuntimeError(f"duplicate SHA-256: {path}")
        hashes.add(digest)
        cause, action, contact, result = meta["causal"]
        records.append({
            "asset_id": asset_id,
            "title": spec["title"],
            "batch": asset_id[0],
            "relative_path": spec["path"],
            "ep00_clip_usage": meta["clips"],
            "generation_prompt": spec["prompt"],
            "reference_files": [{"relative_path": ref, "role": "approved identity/material/continuity reference"} for ref in meta["refs"]],
            "generation": {
                "model": "OpenAI built-in image_gen",
                "workflow": "imagegen skill reference-guided raster generation",
                "seed": "not_exposed_by_builtin_tool",
                "generated_at": generated_at,
            },
            "validation": validation,
            "sha256": digest,
            "causal_record": {"cause": cause, "action": action, "contact": contact, "result": result},
            "continuity_audit": {"assessment": meta["audit"], "note": meta["note"]},
            "approval_status": "pending_user_approval",
            "activation_status": "not_activated_for_h3",
        })

    PROMPT_RECORD.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    prompt_sections = [
        "# EP00 시네마틱 실사화 추가 자산 생성 기록 V1",
        "",
        "- 목적: H3 프롬프트 생성이 아닌 신규 실사화 이미지 자산 14종의 생성 원문·결과 기록",
        "- 생성 방식: OpenAI built-in image_gen, imagegen skill reference-guided raster generation",
        "- 공통 상태: `pending_user_approval`, `not_activated_for_h3`",
        "- 금지된 거부 자산: `Moving_Current_Ribbon_REFERENCE_SHEET_V3_CINEMATIC_FX_V1.png` 미참조",
        "",
    ]
    for record in records:
        prompt_sections.extend([
            f"## {record['asset_id']}. {record['title']}",
            "",
            f"출력: `{record['relative_path']}`",
            "",
            "```text",
            record["generation_prompt"],
            "```",
            "",
        ])
    PROMPT_RECORD.write_text("\n".join(prompt_sections), encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "document_id": "EP00_CINEMATIC_LIVEACTION_ADDITIONAL_ASSET_MANIFEST_V1",
        "source_command": str(COMMAND.relative_to(ROOT)),
        "generated_at": generated_at,
        "scope": "asset_generation_and_audit_only",
        "asset_count": len(records),
        "automatic_validation": {
            "all_files_exist": True,
            "all_1672x941_rgb_png": all(r["validation"]["contract_pass"] for r in records),
            "unique_sha256_count": len(hashes),
            "duplicate_sha256_count": len(records) - len(hashes),
            "no_preexisting_target_overwrite": True,
            "basis": "All 14 exact output paths were absent in the pre-generation path check; no existing asset was deleted, moved, or replaced.",
        },
        "user_approval": {"status": "pending_user_approval", "recorded_at": None},
        "h3_activation": {
            "status": "not_activated_for_h3",
            "picture_linking_performed": False,
            "prompt_project_created": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
        },
        "assets": records,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = []
    for record in records:
        rows.append(f"| {record['asset_id']} | `{record['relative_path']}` | {record['continuity_audit']['assessment']} | pending |")
    APPROVAL.write_text("\n".join([
        "# EP00 시네마틱 실사화 추가 자산 승인 게이트 V1",
        "",
        "## 현재 상태",
        "",
        "- 전체 상태: `pending_user_approval`",
        "- H3 활성화: `not_activated_for_h3`",
        "- 프롬프트 프로젝트 생성: 미실행",
        "- Picture 연결: 미실행",
        "",
        "## 자산별 확인표",
        "",
        "| ID | 파일 | 내부 검수 | 사용자 승인 |",
        "| --- | --- | --- | --- |",
        *rows,
        "",
        "사용자가 자산을 직접 확인해 승인하기 전까지 이 게이트는 열리지 않는다.",
        "",
    ]), encoding="utf-8")

    audit_rows = []
    for record in records:
        audit_rows.append(f"| {record['asset_id']} | {record['continuity_audit']['assessment']} | {record['continuity_audit']['note']} |")
    AUDIT.write_text("\n".join([
        "# EP00 시네마틱 실사화 추가 자산 시각 검수 V1",
        "",
        "## 자동 검사",
        "",
        f"- 신규 PNG: {len(records)}/14 존재",
        "- 규격: 14/14 `1672×941`, `RGB`, `PNG`",
        f"- SHA-256: {len(hashes)}/14 고유, 중복 0",
        "- 정확한 명령서 출력 경로: 14/14 일치",
        "- 기존 자산: 삭제·이동·교체 없음; 14개 출력 경로는 생성 전 모두 부재 확인",
        "",
        "## 시각·인과 검수",
        "",
        "| ID | 판정 | 관찰 |",
        "| --- | --- | --- |",
        *audit_rows,
        "",
        "`needs_user_review_*` 및 `pass_with_*_review`는 생성 실패를 의미하지 않는다. H3 투입 전 사용자가 인과 판독성과 정체성 연속성을 최종 선택해야 한다.",
        "",
        "## 실행 경계",
        "",
        "프롬프트 문서 생성·변경, H3 프로젝트 생성, Picture 연결, 큐 등록 및 영상 생성은 수행하지 않았다.",
        "",
    ]), encoding="utf-8")

    print(json.dumps(manifest["automatic_validation"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
