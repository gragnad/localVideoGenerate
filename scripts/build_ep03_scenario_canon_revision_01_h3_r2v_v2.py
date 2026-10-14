#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "RaisingaDragonSeason01_EP03_SCENARIO_CANON_REVISION_01_H3_R2V_V2"
DESTINATION = ROOT / "prompt_projects" / PROJECT_ID
PRODUCTION_ROOT = ROOT / "projects" / "RaisingaDragonSeason01"
PROMPT_ROOT = PRODUCTION_ROOT / "EP03_H3_PROMPTS_V2"
SOURCE_ASSET_ROOT = (
    ROOT
    / "prompt_projects"
    / "RaisingaDragonSeason01_EP03_SCENARIO_CANON_REVISION_01_H3_R2V_V1"
    / "assets"
)
SCENARIO = Path(
    "/home/nalstudio/.codex/attachments/41140e6e-b4fc-4341-9194-983292307f03/"
    "EP03_Scenario_Canon_Revision_01.md"
)
CONTRACT = "h3_user_supplied_passthrough_v5"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


ASSETS = {
    "coast": {
        "path": "backgrounds/rocky_coastal_battlefield.png",
        "sha256": "14c030f07ee8de62f444791ea761ae2dc2bf8fbfa4c961bcca6888fa0eaf3310",
        "role": "environment",
        "label": "기존 해안 전장",
        "description": "Wet black coastal battlefield used to reconstruct the dark cliff-side ink pocket.",
    },
    "extended_coast": {
        "path": "backgrounds/ink_pocket_to_high_outer_slab_v1.png",
        "sha256": "85fcdbd366e5ef09f3a4fc2be08a0222ef9131020f77f5f15def26a22728f6dd",
        "role": "environment",
        "label": "안쪽 먹물 포켓에서 높은 외부 돌판까지의 확장 해안",
        "description": "Connected inner pocket, open rock neck, higher outer slab, shallow channel, and seaward light.",
    },
    "lua": {
        "path": "identity/lua_identity.png",
        "sha256": "39ed907bef745979498402e73326a47a24977f6d3ab6ba4e37bc5970b4b10034",
        "role": "character_identity",
        "label": "루아 실사 정체성",
        "description": "Approved photorealistic Lua identity, face, body proportions, wet coastal clothing, and ponytail.",
    },
    "mir_bruised": {
        "path": "conditions/young_mir_left_flank_black_bruise_replacement_v2.png",
        "sha256": "6432d61e375601055ae0668796b45ec654e8170c8e6c43fb2287aa2f677e57c0",
        "role": "character_state_identity",
        "label": "왼쪽 옆구리 멍 상태 미르",
        "description": "Approved young Mir identity with the existing black bruise behind the anatomical left foreleg.",
    },
    "jellyfish": {
        "path": "creatures/black_jellyfish_common_type.png",
        "sha256": "d2f440b470624b0aca84843e47481368e3a101d08fc0ce8488e102e9e9472a84",
        "role": "creature_type",
        "label": "검은 해파리 공통 유형",
        "description": "Common black-liquid jellyfish type with a single teal eye, flexible tentacles, and approximate combat scale.",
    },
    "harpoon": {
        "path": "props/lua_145cm_harpoon.png",
        "sha256": "9cc102bbbb1dc1c7fe7b4d31655b38f280b84ec57edadfa06aa734477a0719a5",
        "role": "prop",
        "label": "루아 145cm 작살",
        "description": "Approved continuous 145-centimeter harpoon with practical shaft, forged point, and side blade.",
    },
    "sigil": {
        "path": "effects/lua_right_hand_back_dragon_tide_sigil_v1.png",
        "sha256": "bf6a10e26d7bd2d9afa8c970568a38cfaf476bd6f7c586f19f2212fe30cb9cb0",
        "role": "event_detail",
        "label": "루아 오른손등 용·파도 문양",
        "description": "Approved event-only cyan sigil design and anatomical placement on the back of Lua's right hand.",
    },
    "anchor_c07": {
        "path": "anchors/ANC_EP03_C07_TENTACLE_CUT_FIRST_CONTACT_V2.png",
        "sha256": "616262d9f10daa8f697b6b0427aeb472f195f9f9767759fa7e2acdef09086d75",
        "role": "single_event_anchor",
        "label": "C07 옆날 최초 접촉 사건 앵커",
        "description": "One reached event frame; preserve only hand spacing, side-blade contact, compressed tentacle, and blade-to-scale clearance.",
    },
    "anchor_c14": {
        "path": "anchors/ANC_EP03_C14_REAR_PAW_TENSION_HOLD_V1.png",
        "sha256": "37d7fca2810927b01e8270c92be870d20f073f07c26f6922d41f49cc9114af93",
        "role": "single_event_anchor",
        "label": "C14 뒷발 지지·장력 사건 앵커",
        "description": "One reached event frame for Mir's rear-claw support, jaw-to-root tension, and exposed eye.",
    },
    "anchor_c16": {
        "path": "anchors/ANC_EP03_C16_EYE_FIRST_CONTACT_V1.png",
        "sha256": "53ebd2e0f21e898f8b0ec9e8601fccfd847e8b660c18daee2c2acea84709d38e",
        "role": "single_event_anchor",
        "label": "C16 눈 최초 접촉 사건 앵커",
        "description": "One reached event frame for the harpoon-eye axis and first localized compression of the teal surface.",
    },
}


REFERENCE_REASONS = {
    "coast": "이 클립의 절벽 아래 먹물 포켓과 젖은 현무암 공간을 유지한다.",
    "extended_coast": "이 클립의 포켓·바위목·높은 외부 돌판 공간 관계를 유지한다.",
    "lua": "이 클립에서 루아의 승인된 실사 정체성을 유지한다.",
    "mir_bruised": "이 클립에서 어린 미르의 정체성과 기존 왼쪽 옆구리 멍 상태를 유지한다.",
    "jellyfish": "이 클립에서 공통 적의 액체 재질·단일 눈·실루엣을 유지한다.",
    "harpoon": "이 클립에서 단일 145cm 작살의 형상과 필요한 그립 관계를 유지한다.",
    "sigil": "C06 통증 사건에서만 오른손등 문양의 선과 위치를 유지한다.",
    "anchor_c07": "C07 지정 순간의 양손·옆날·촉수·미르 비늘 사이 접촉 기하만 부분 보존한다.",
    "anchor_c14": "C14 지정 순간의 뒷발 지지와 턱–촉수 장력을 유지한다.",
    "anchor_c16": "C16 지정 순간의 작살–눈 최초 접촉 축을 유지한다.",
}


CLIPS = {
    "C01": ("EP03-S01-INK-FOG", 9, ["coast", "lua", "harpoon"]),
    "C02": ("EP03-S01-INK-FOG", 8, ["coast", "mir_bruised", "jellyfish"]),
    "C03": ("EP03-S01-INK-FOG", 8, ["coast", "lua", "mir_bruised", "jellyfish"]),
    "C04": ("EP03-S01-INK-FOG", 8, ["coast", "lua", "harpoon"]),
    "C05": ("EP03-S01-INK-FOG", 8, ["coast", "mir_bruised", "jellyfish"]),
    "C06": ("EP03-S01-INK-FOG", 6, ["coast", "lua", "harpoon", "sigil"]),
    "C07": ("EP03-S02-FIRST-RESCUE", 11, ["coast", "lua", "mir_bruised", "jellyfish", "harpoon", "anchor_c07"]),
    "C08": ("EP03-S02-FIRST-RESCUE", 10, ["extended_coast", "lua", "mir_bruised", "harpoon"]),
    "C09": ("EP03-S02-FIRST-RESCUE", 7, ["extended_coast", "jellyfish"]),
    "C10": ("EP03-S03-HOLD-THE-MOMENT", 8, ["extended_coast", "mir_bruised", "jellyfish"]),
    "C11": ("EP03-S03-HOLD-THE-MOMENT", 6, ["extended_coast", "lua", "harpoon"]),
    "C12": ("EP03-S03-HOLD-THE-MOMENT", 4, ["extended_coast", "jellyfish"]),
    "C13": ("EP03-S03-HOLD-THE-MOMENT", 5, ["extended_coast", "lua", "jellyfish", "harpoon"]),
    "C14": ("EP03-S03-HOLD-THE-MOMENT", 4, ["extended_coast", "mir_bruised", "jellyfish", "anchor_c14"]),
    "C15": ("EP03-S03-HOLD-THE-MOMENT", 4, ["extended_coast", "lua", "harpoon"]),
    "C16": ("EP03-S03-HOLD-THE-MOMENT", 8, ["extended_coast", "lua", "jellyfish", "harpoon", "anchor_c16"]),
    "C17": ("EP03-S04-JELLYFISH-DEFEAT", 4, ["extended_coast", "mir_bruised", "jellyfish"]),
    "C18": ("EP03-S04-JELLYFISH-DEFEAT", 8, ["extended_coast", "lua", "jellyfish", "harpoon"]),
    "C19": ("EP03-S05-AFTERMATH", 7, ["extended_coast"]),
    "C20": ("EP03-S05-AFTERMATH", 10, ["extended_coast", "lua", "mir_bruised", "harpoon"]),
    "C21": ("EP03-S05-AFTERMATH", 5, ["extended_coast"]),
}


TITLES = {
    "C01": "발밑에서 시작하는 수색",
    "C02": "촉수를 물고 버티는 미르",
    "C03": "루아가 발견한 검은 자국",
    "C04": "아까는 됐잖아",
    "C05": "몸을 감아 들어 올리는 촉수",
    "C06": "오른손등으로 전해진 통증",
    "C07": "팽팽한 고리를 베어 푼다",
    "C08": "바람이 들어오는 틈으로",
    "C09": "따라 나오는 청록색 눈",
    "C10": "붙잡은 촉수가 눈을 돌린다",
    "C11": "눈을 본 뒤 그립을 좁힌다",
    "C12": "높이 세운 촉수의 하강 공격",
    "C13": "머리 위를 지난 끝이 돌을 찍는다",
    "C14": "끌려간 발을 걸어 눈을 붙잡는다",
    "C15": "발에서 손까지 이어지는 찌르기",
    "C16": "눈에 닿은 힘이 몸 전체를 흔든다",
    "C17": "턱에 걸린 힘이 풀린다",
    "C18": "검은 몸이 물방울로 풀린다",
    "C19": "검은 자국의 빛도 꺼진다",
    "C20": "이번엔 잡았다",
    "C21": "전투의 끝",
}


SOURCE_DOCUMENTS = {
    SCENARIO: "EP03_Scenario_Canon_Revision_01.md",
    PRODUCTION_ROOT / "EP03_H3_INHERITANCE_AND_DIRECTION_BRIEF_V2.md": "EP03_H3_INHERITANCE_AND_DIRECTION_BRIEF_V2.md",
    PRODUCTION_ROOT / "EP03_H3_ASSETS_V1" / "EP03_ASSET_AUDIT_V1.md": "EP03_ASSET_AUDIT_V1.md",
    PRODUCTION_ROOT / "EP03_H3_ASSETS_V1" / "ASSET_MANIFEST.json": "EP03_ASSET_MANIFEST_V1.json",
    PROMPT_ROOT / "REFERENCE_MAP_V2.md": "REFERENCE_MAP_V2.md",
    PROMPT_ROOT / "VALIDATION_REPORT_V2.md": "PROMPT_VALIDATION_REPORT_V2.md",
}


def validate_sources() -> None:
    required = list(SOURCE_DOCUMENTS)
    required.extend(PROMPT_ROOT / f"EP03_{clip}.md" for clip in CLIPS)
    required.extend(SOURCE_ASSET_ROOT / str(asset["path"]) for asset in ASSETS.values())
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing EP03 V2 sources: " + ", ".join(missing))
    for asset_key, asset in ASSETS.items():
        source = SOURCE_ASSET_ROOT / str(asset["path"])
        actual = sha256_file(source)
        if actual != asset["sha256"]:
            raise ValueError(f"{asset_key}: approved asset hash mismatch: {actual}")


def references_for(asset_keys: list[str]) -> list[dict[str, object]]:
    references = []
    for picture_index, asset_key in enumerate(asset_keys, start=1):
        asset = ASSETS[asset_key]
        instruction = "Use this Picture only for the declared project role."
        if asset_key == "anchor_c07":
            instruction = "Use only the declared contact geometry; preserve Picture 1 as the dominant dark location and lighting."
        references.append(
            {
                "picture_index": picture_index,
                "asset_key": asset_key,
                "role": asset["role"],
                "label": asset["label"],
                "description": asset["description"],
                "instruction_en": instruction,
                "reference_reason": REFERENCE_REASONS[asset_key],
                "reference_kind": "visual_reference",
                "required": True,
                "source_path": f"assets/{asset['path']}",
            }
        )
    return references


def validate_prompt(prompt: str, expected_count: int, clip_id: str) -> None:
    sections = re.findall(
        r"^(subject_definitions|summary|retention_analysis|detailed_description|overall_soundscape|non_diegetic_music):\s*$",
        prompt,
        re.MULTILINE,
    )
    expected_sections = [
        "subject_definitions",
        "summary",
        "retention_analysis",
        "detailed_description",
        "overall_soundscape",
        "non_diegetic_music",
    ]
    if sections != expected_sections:
        raise ValueError(f"{clip_id}: invalid six-section order: {sections}")
    picture_ids = sorted({int(value) for value in re.findall(r"<Picture (\d+)>", prompt)})
    if picture_ids != list(range(1, expected_count + 1)):
        raise ValueError(f"{clip_id}: Picture labels {picture_ids} do not match 1..{expected_count}")


def build() -> dict[str, object]:
    if DESTINATION.exists():
        raise FileExistsError(f"Existing project is preserved: {DESTINATION}")
    validate_sources()
    staging = DESTINATION.parent / f".{PROJECT_ID}.building-{secrets.token_hex(4)}"
    staging.mkdir(parents=True)
    try:
        copied_assets = []
        for asset_key, asset in ASSETS.items():
            source = SOURCE_ASSET_ROOT / str(asset["path"])
            target = staging / "assets" / str(asset["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied_assets.append(
                {
                    "asset_key": asset_key,
                    "source_path": str(source),
                    "project_path": target.relative_to(staging).as_posix(),
                    "sha256": sha256_file(target),
                    "approved_sha256": asset["sha256"],
                    "hash_verified": sha256_file(target) == asset["sha256"],
                }
            )

        source_dir = staging / "source"
        source_dir.mkdir()
        for source, target_name in SOURCE_DOCUMENTS.items():
            shutil.copy2(source, source_dir / target_name)
        source_prompt_dir = source_dir / "prompts"
        source_prompt_dir.mkdir()
        shutil.copy2(PROMPT_ROOT / "README.md", source_prompt_dir / "README.md")

        clip_bindings: dict[str, list[dict[str, object]]] = {}
        prompt_rows = []
        scene_counts: dict[str, int] = {}
        total_duration = 0.0
        for sequence, (clip, (scene_id, duration, asset_keys)) in enumerate(CLIPS.items(), start=1):
            clip_id = f"EP03_{clip}"
            prompt_path = PROMPT_ROOT / f"{clip_id}.md"
            prompt = prompt_path.read_text(encoding="utf-8").strip()
            validate_prompt(prompt, len(asset_keys), clip_id)
            references = references_for(asset_keys)
            clip_bindings[clip_id] = references
            scene_counts[scene_id] = scene_counts.get(scene_id, 0) + 1
            total_duration += float(duration)
            shutil.copy2(prompt_path, source_prompt_dir / prompt_path.name)
            prompt_hash = sha256_bytes(prompt.encode("utf-8"))
            payload = {
                "schema_version": 2,
                "prompt_contract_version": CONTRACT,
                "workflow": "h3_r2v_production",
                "project_id": PROJECT_ID,
                "scene_id": scene_id,
                "clip_id": clip_id,
                "source_clip_id": clip_id,
                "sequence": sequence,
                "scene_sequence": scene_counts[scene_id],
                "status": "ready",
                "duration_seconds": float(duration),
                "title": TITLES[clip],
                "video_prompt": prompt,
                "references": references,
                "reference_mode": "single_event_anchor" if clip in {"C07", "C14", "C16"} else "basic_full_reference_r2v",
                "source_prompt_document": f"source/prompts/{prompt_path.name}",
                "source_prompt_sha256": prompt_hash,
                "video_prompt_sha256": prompt_hash,
                "canonical_source_lineage": [
                    "source/EP03_Scenario_Canon_Revision_01.md",
                    "source/EP03_H3_INHERITANCE_AND_DIRECTION_BRIEF_V2.md",
                    "source/REFERENCE_MAP_V2.md",
                ],
                "queue_authorized": False,
                "video_generation_authorized": False,
            }
            clip_dir = staging / scene_id
            clip_dir.mkdir(parents=True, exist_ok=True)
            clip_markdown = (
                f"# {clip_id} · {TITLES[clip]} · MiniMax H3 R2V V2\n\n"
                "## Machine Payload\n\n```json\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
            (clip_dir / f"{clip_id}.md").write_text(clip_markdown, encoding="utf-8")
            prompt_rows.append(
                {
                    "clip_id": clip_id,
                    "scene_id": scene_id,
                    "duration_seconds": float(duration),
                    "reference_mode": payload["reference_mode"],
                    "picture_count": len(references),
                    "picture_indexes": list(range(1, len(references) + 1)),
                    "source_prompt_sha256": prompt_hash,
                    "six_section_order_valid": True,
                    "picture_labels_match": True,
                    "background_is_picture_1": asset_keys[0] in {"coast", "extended_coast"},
                }
            )

        manifest = {
            "schema_version": 2,
            "project_kind": "h3_r2v_production",
            "project_id": PROJECT_ID,
            "title": "Raising a Dragon EP03 · Scenario Canon Revision 01 · H3 R2V V2",
            "description": "Twenty-one independently rewritten EP03 V2 clips with verified project-local assets, the event-only C06 sigil, three approved single-event anchors, and the extended coast from C08 onward.",
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": CONTRACT,
            "asset_storage": "project_local_verified_full_reference_assets",
            "source_policy": "EP03 Scenario Canon Revision 01, EP03 inheritance brief V2, latest user approvals, H3 production canon V2, and hash-verified approved assets only",
            "canonical_source_lineage": [
                "source/EP03_Scenario_Canon_Revision_01.md",
                "source/EP03_H3_INHERITANCE_AND_DIRECTION_BRIEF_V2.md",
                "source/EP03_ASSET_AUDIT_V1.md",
                "source/EP03_ASSET_MANIFEST_V1.json",
                "source/REFERENCE_MAP_V2.md",
                "source/PROMPT_VALIDATION_REPORT_V2.md",
            ],
            "build_script": "scripts/build_ep03_scenario_canon_revision_01_h3_r2v_v2.py",
            "review_status": "ready_for_user_generation_authorization",
            "queue_authorized": False,
            "video_generation_authorized": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
            "video_candidate_selection_performed": False,
            "image_asset_selection_performed": True,
            "build_facts": {
                "scene_count": len(scene_counts),
                "clip_count": len(CLIPS),
                "basic_r2v_clip_count": len(CLIPS) - 3,
                "single_event_anchor_clip_count": 3,
                "project_local_asset_count": len(ASSETS),
                "total_duration_seconds": total_duration,
                "queue_entry_count": 0,
            },
            "scene_counts": scene_counts,
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (staging / "asset_mapping.json").write_text(
            json.dumps({"schema_version": 2, "project_id": PROJECT_ID, "clip_bindings": clip_bindings, "assets": copied_assets}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (staging / "PROMPT_CONNECTION_REPORT.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "project_id": PROJECT_ID,
                    "clip_count": len(prompt_rows),
                    "missing_assets": [],
                    "asset_hash_mismatches": [],
                    "picture_sequence_errors": [],
                    "background_priority_errors": [],
                    "prompt_rows": prompt_rows,
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        report_lines = [
            "# EP03 H3 R2V V2 프로젝트 생성·연결 보고서",
            "",
            f"- 프로젝트: `{PROJECT_ID}`",
            f"- 클립: {len(CLIPS)}개 / 씬: {len(scene_counts)}개 / 총 길이: {total_duration:g}초",
            f"- 프로젝트 로컬 승인 자산: {len(ASSETS)}개 / 해시 일치: {sum(row['hash_verified'] for row in copied_assets)}개",
            "- C06 오른손등 문양: 기존 승인 자산을 C06에만 연결",
            "- 단일 사건 앵커: C07 V2, C14 V1, C16 V1에만 연결",
            "- 배경: C01~C07 기존 해안, C08~C21 확장 해안",
            "- C07 앵커: 접촉 기하만 부분 보존하고 Picture 1의 어두운 포켓을 우선",
            "- Picture 번호: 모든 클립 1번부터 연속, 실제 장소가 Picture 1",
            "- 영상 생성·큐 등록: 실행하지 않음",
            "",
            "## 프로젝트 로컬 자산",
            "",
        ]
        report_lines.extend(f"- `{row['project_path']}` — `{row['sha256']}`" for row in copied_assets)
        (source_dir / "PROJECT_BUILD_AND_CONNECTION_REPORT_V2.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        staging.rename(DESTINATION)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        "project_id": PROJECT_ID,
        "project_path": str(DESTINATION),
        "scene_count": len(scene_counts),
        "clip_count": len(CLIPS),
        "asset_count": len(ASSETS),
        "total_duration_seconds": total_duration,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
