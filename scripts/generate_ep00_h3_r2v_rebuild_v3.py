#!/usr/bin/env python3
from __future__ import annotations

"""Generate EP00 H3 R2V V3 with sheet references for every non-background asset."""

import copy
import json
from pathlib import Path

import generate_ep00_h3_r2v_rebuild_v2 as v2


ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = ROOT / "projects" / "RaisingaDragonSeason01"
PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_REBUILD_V3"
CONTRACTS_PATH = PROJECT_DIR / "EP00_H3_R2V_REBUILD_V3_EVENT_CONTRACTS.json"
SPEC_PATH = PROJECT_DIR / "EP00_H3_R2V_REBUILD_V3_SPEC.json"


SHEET_OVERRIDES = {
    "lua_awakened": {
        "role": "lua_awakened_multiview_identity_sheet",
        "label": "완전 각성 루아 다중 시점 캐릭터 시트",
        "description": "동일한 완전 각성 루아의 정면·측면·후면·얼굴 세부 시트",
        "copy_from": "reference_sheets_ep00_v3/characters/Lua_Awakened_REFERENCE_SHEET_V3.png",
        "sheet_instruction": (
            "Use this Picture only as one multi-view character identity sheet. All four "
            "panels describe the same single Lua and must not become a panel layout, "
            "multiple people, alternate costumes, or simultaneous authored views in the scene"
        ),
    },
    "abyss_king": {
        "role": "abyss_king_multiview_identity_sheet",
        "label": "심해왕 전신 다중 시점 캐릭터 시트",
        "description": "동일한 심해왕의 정면·측면·후면·상반신 세부 시트",
        "copy_from": "reference_sheets_ep00_v3/enemies/Deep_Sea_King_Full_Reference_NEUTRAL_V2.png",
        "sheet_instruction": (
            "Use this Picture only as one multi-view enemy identity sheet. All four panels "
            "describe the same single connected body and must not become a panel layout, "
            "duplicate enemies, extra bodies, or simultaneous authored views in the scene"
        ),
    },
    "dragon_spear": {
        "role": "physical_spear_multiview_prop_sheet",
        "label": "루아의 물리 창 다중 시점 소품 시트",
        "description": "동일한 물리 창의 전체 길이·회전 시점·돌날 세부 시트",
        "copy_from": "reference_sheets_ep00_v3/props/Dragon_Spear_REFERENCE_SHEET_V3.png",
        "sheet_instruction": (
            "Use this Picture only as one multi-view prop design sheet. Every panel defines "
            "the same single spear and must not become multiple weapons, a panel layout, "
            "or simultaneous authored views in the scene"
        ),
    },
    "heartstone": {
        "role": "inactive_heartstone_multiview_prop_sheet",
        "label": "비활성 해심석 다중 시점 소품 시트",
        "description": "동일한 해심석과 받침의 정면·측면·후면·표면 세부 시트",
        "copy_from": "reference_sheets_ep00_v3/props/Heartstone_REFERENCE_SHEET_V3.png",
        "sheet_instruction": (
            "Use this Picture only as one multi-view prop design sheet. All panels define "
            "the same single fixed Heartstone and pedestal and must not become multiple "
            "crystals, a panel layout, or simultaneous authored views in the scene"
        ),
    },
    "wrist_mark": {
        "role": "dragon_heart_mark_multiview_detail_sheet",
        "label": "용심 손목 문양 다중 시점 디테일 시트",
        "description": "동일한 손목 문양의 손등 회전 시점과 문양 세부 시트",
        "copy_from": "reference_sheets_ep00_v3/details/Dragon_Heart_Wrist_Mark_REFERENCE_SHEET_V3.png",
        "sheet_instruction": (
            "Use this Picture only as one multi-view body-attached detail sheet. Every panel "
            "defines the same single mark on Lua's same wrist and must not become duplicate "
            "hands, a floating emblem, a panel layout, or simultaneous authored views"
        ),
    },
    "current_shield": {
        "role": "irregular_curved_current_shield_multiview_effect_sheet",
        "label": "불규칙 곡면 물방패 다중 시점·상태 시트",
        "description": "승인된 단일 불규칙 곡면 물막의 정면·측면·압박·가장자리 파열 시트",
        "copy_from": "reference_sheets_ep00_v3/effects/Current_Shield_IRREGULAR_CURVED_REFERENCE_SHEET_V4.png",
        "sheet_instruction": (
            "Use this Picture only as one multi-view and multi-state effect design sheet. "
            "Every panel defines a view or authored pressure state of the same single "
            "irregular curved shield and must not become multiple shields or a panel layout"
        ),
    },
    "dragon_language": {
        "role": "dragon_word_water_pattern_multiview_effect_sheet",
        "label": "용언 수면 문양 다중 시점·단계 시트",
        "description": "동일한 청백색 수면 문양의 시점·확장·가장자리 소멸 단계 시트",
        "copy_from": "reference_sheets_ep00_v3/effects/Dragon_Language_Effect_REFERENCE_SHEET_V1.png",
        "sheet_instruction": (
            "Use this Picture only as one multi-view and multi-phase effect design sheet. "
            "Every panel defines a view or authored phase of the same single water-surface "
            "pattern and must not become multiple patterns or a panel layout"
        ),
    },
}


def _asset_catalog() -> dict:
    catalog = copy.deepcopy(v2.ASSET_CATALOG)
    for key, override in SHEET_OVERRIDES.items():
        sheet_instruction = override["sheet_instruction"]
        replacement = {name: value for name, value in override.items() if name != "sheet_instruction"}
        catalog[key].update(replacement)
        catalog[key]["subject_description"] = (
            catalog[key]["subject_description"].rstrip(".") + ". " + sheet_instruction
        )
        catalog[key]["retention_description"] = (
            catalog[key]["retention_description"].rstrip(".")
            + ". Preserve one scene instance derived from the sheet rather than its panel layout"
        )
    # The only non-sheet reference is the environment/background anchor.
    catalog["heartstone_chamber"].update({
        "role": "heartstone_chamber_background_anchor",
        "label": "해심석 방 배경 원본",
        "description": "시트 변환 대상이 아닌 원형 수중 궁전 배경·공간 앵커",
    })
    return catalog


def _spec() -> dict:
    clips = []
    for sequence, row in enumerate(v2.CLIP_ROWS, start=1):
        clips.append({
            "scene_id": row["scene_id"],
            "clip_id": row["clip_id"],
            "sequence": sequence,
            "duration_seconds": row["duration"],
            "references": row["references"],
            "prompt_base": {
                "summary": row["summary"],
                "style_opening": [row["style"]],
                "overall_soundscape": row["sound"],
                "non_diegetic_music": row["music"],
            },
            "prompt_variants": [
                {
                    "variant_id": variant_id,
                    "label": label,
                    "rationale": rationale,
                    "prompt_spec": {},
                }
                for variant_id, label, rationale in (
                    ("A", "공간 인과", f"{row['clip_id']} 사건의 준비·실행·접촉·결과를 넓은 공간 축과 종료 상태로 증명"),
                    ("B", "신체 역학", f"{row['clip_id']} 사건의 동일 beat를 전신 움직임과 물리 접촉 중심으로 구성"),
                    ("C", "인지와 압력", f"{row['clip_id']} 사건의 동일 beat를 루아의 판단, 압력 변화와 다음 상태 단서 중심으로 구성"),
                )
            ],
            "scenario_ko": f"승인된 {row['source_shot_id']} 한 Shot의 사건만 사용한다.",
            "review_intent_ko": (
                "A/B/C가 같은 사건 beat를 같은 순서로 한 번씩 사용하고, 비배경 "
                "Picture의 여러 패널을 장면 속 복수 개체로 만들지 않는지 검수한다."
            ),
            "authoring_notes": [
                "기존 EP00 V1 사건과 뿌리 공격을 사용하지 않는다.",
                "심해왕은 두 팔과 두 손만 사용하고 루아의 약 3배 높이를 유지한다.",
                "HeartstoneChamber 배경 외 모든 Picture는 다중 시점·상태 시트를 사용한다.",
                "큐 등록과 영상 생성은 이 프로젝트 생성 범위에 포함하지 않는다.",
            ],
        })
    return {
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon Season 01 · EP00 H3 R2V Rebuild V3 · Sheet References",
        "description": (
            "승인된 140초 EP00의 14개 H3 R2V Clip과 A/B/C 후보를 유지하면서, "
            "배경 공간을 제외한 캐릭터·적·무기·고정 소품·손목 디테일·물방패·용언 "
            "효과를 모두 다중 시점 또는 다중 상태 참조 시트로 연결한다. 기존 V2는 "
            "보존하며 큐 등록과 영상 생성은 하지 않는다."
        ),
        "event_contracts_file": CONTRACTS_PATH.name,
        "asset_catalog": _asset_catalog(),
        "clips": clips,
    }


def main() -> int:
    contracts = v2._build_contracts()
    spec = _spec()
    CONTRACTS_PATH.write_text(
        json.dumps(contracts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    SPEC_PATH.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "project_id": PROJECT_ID,
        "contracts": str(CONTRACTS_PATH),
        "spec": str(SPEC_PATH),
        "clip_count": len(v2.CLIP_ROWS),
        "duration_seconds": sum(float(row["duration"]) for row in v2.CLIP_ROWS),
        "sheet_assets": sorted(SHEET_OVERRIDES),
        "background_assets": ["heartstone_chamber"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
