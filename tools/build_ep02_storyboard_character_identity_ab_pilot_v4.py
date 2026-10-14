from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import h3_prompt_projects


SOURCE_PROJECT_ID = "RaisingaDragonSeason01_EP02_H3_R2V_6P_ACTION_TRAIL_PILOT_V3"
SOURCE_PROJECT_DIR = ROOT / "prompt_projects" / SOURCE_PROJECT_ID
SOURCE_SCENE_ID = "EP02-SB6-ACTION-TRAIL-PILOT-V3"

PROJECT_ID = "RaisingaDragonSeason01_EP02_H3_R2V_6P_CHARACTER_IDENTITY_AB_PILOT_V4"
PROJECT_DIR = ROOT / "prompt_projects" / PROJECT_ID
SCENE_ID = "EP02-SB6-CHARACTER-IDENTITY-AB-PILOT-V4"

SPEC_SOURCE = (
    ROOT
    / "projects"
    / "RaisingaDragonSeason01"
    / "ep02_storyboard_character_identity_ab_pilot_v4"
    / "EP02_STORYBOARD_CHARACTER_IDENTITY_AB_PILOT_V4_SPEC.md"
)
LUA_SOURCE = (
    ROOT
    / "projects"
    / "RaisingaDragonSeason01"
    / "asset_sheets_cinematic_liveaction_v2_working"
    / "01_characters"
    / "identity_sheets"
    / "H3_LUA_BASE_STATE_KOREAN_IDOL_PONYTAIL_LONG_LEG_CINEMATIC_LIVEACTION_IDENTITY_V1.png"
)
MIR_SOURCE = (
    ROOT
    / "prompt_projects"
    / "RaisingaDragonSeason01_EP01_CINEMATIC_LIVEACTION_H3_R2V_V4"
    / "assets"
    / "shared"
    / "H3_YOUNG_MIR_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png"
)

LUA_NAME = LUA_SOURCE.name
MIR_NAME = MIR_SOURCE.name

PILOTS = [
    {
        "pair_id": "P01_MIR_FOREPAW",
        "seed": 2608315101,
        "source_clip": "EP02_SB6_V3_P01_MIR_FOREPAW_ACTION_TRAIL",
        "storyboard": "EP02_SB6_V3_P01_MIR_FOREPAW_ACTION_TRAIL_STORYBOARD.png",
        "title": "미르 오른쪽 앞발 공격",
        "identity_subjects": {
            1: "- <Subject 1>: Young Mir as shown in <Picture 2>, preserving his compact blue-white quadrupedal body, youthful face, paired horns, connected four-legged anatomy, long tail, cyan repaired tail crystal, and established height of about 50 centimeters."
        },
        "identity_references": ["mir"],
    },
    {
        "pair_id": "P02_LUA_AWAKENED_CUT",
        "seed": 2608316202,
        "source_clip": "EP02_SB6_V3_P02_LUA_AWAKENED_CUT_ACTION_TRAIL",
        "storyboard": "EP02_SB6_V3_P02_LUA_AWAKENED_CUT_ACTION_TRAIL_STORYBOARD.png",
        "title": "루아 각성 공중 절단",
        "identity_subjects": {
            1: "- <Subject 1>: Lua as shown in <Picture 2>, preserving her Korean facial identity, athletic natural proportions, 165-centimeter height, black high ponytail, navy sleeveless wrap outfit, red waist sash, and black boots.",
            2: "- <Subject 2>: Young Mir as shown in <Picture 3>, preserving his compact blue-white quadrupedal body, youthful face, paired horns, connected four-legged anatomy, long tail, cyan repaired tail crystal, and established height of about 50 centimeters.",
        },
        "identity_references": ["lua", "mir"],
    },
    {
        "pair_id": "P03_MIR_HEADBUTT",
        "seed": 2608316903,
        "source_clip": "EP02_SB6_V3_P03_MIR_HEADBUTT_ACTION_TRAIL",
        "storyboard": "EP02_SB6_V3_P03_MIR_HEADBUTT_ACTION_TRAIL_STORYBOARD.png",
        "title": "미르 공중 박치기",
        "identity_subjects": {
            1: "- <Subject 1>: Lua as shown in <Picture 2>, preserving her Korean facial identity, 165-centimeter height, black high ponytail, navy sleeveless wrap outfit, red waist sash, and clearly readable right shoulder as Mir's launch point.",
            2: "- <Subject 2>: Young Mir as shown in <Picture 3>, preserving his compact blue-white quadrupedal body, youthful face, paired horns, connected four-legged anatomy, long tail, cyan repaired tail crystal, and established height of about 50 centimeters.",
        },
        "identity_references": ["lua", "mir"],
    },
]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_payload(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if not match:
        raise ValueError(f"Machine Payload를 찾을 수 없습니다: {path}")
    return json.loads(match.group(1))


def replace_subject_lines(prompt: str, replacements: dict[int, str]) -> str:
    output = prompt
    for subject_index, line in replacements.items():
        pattern = rf"(?m)^- <Subject {subject_index}>:.*$"
        output, count = re.subn(pattern, line, output, count=1)
        if count != 1:
            raise ValueError(f"Subject {subject_index} 정의 교체 실패")
    return output


def section(prompt: str, name: str, next_name: str | None) -> str:
    start = prompt.index(f"{name}:\n")
    if next_name is None:
        return prompt[start:]
    end = prompt.index(f"\n{next_name}:\n", start)
    return prompt[start:end]


def identity_reference(picture_index: int, identity: str) -> dict:
    if identity == "lua":
        return {
            "picture_index": picture_index,
            "role": "lua_identity_reference",
            "label": "루아 정체성 참조",
            "description": "Lua character identity reference for face, proportions, hair, and costume.",
            "instruction_en": "Picture %d defines Lua's facial identity, natural proportions, black ponytail, navy outfit, red sash, and black boots; Picture 1 defines the shot composition, placement, scale, and action." % picture_index,
            "reference_kind": "visual_reference",
            "required": True,
            "source_path": f"assets/identity/{LUA_NAME}",
        }
    if identity == "mir":
        return {
            "picture_index": picture_index,
            "role": "young_mir_identity_reference",
            "label": "어린 미르 정체성 참조",
            "description": "Young Mir identity reference for face, horns, scales, quadrupedal anatomy, and crystal tail.",
            "instruction_en": "Picture %d defines Young Mir's face, horns, blue-white scales, connected quadrupedal anatomy, long tail, and cyan crystal tip; Picture 1 defines the shot composition, placement, scale, and action." % picture_index,
            "reference_kind": "visual_reference",
            "required": True,
            "source_path": f"assets/identity/{MIR_NAME}",
        }
    raise ValueError(identity)


def main() -> None:
    if PROJECT_DIR.exists():
        raise FileExistsError(f"새 파일럿 프로젝트 경로가 이미 존재합니다: {PROJECT_DIR}")

    scene_dir = PROJECT_DIR / SCENE_ID
    storyboard_dir = PROJECT_DIR / "assets" / "storyboards"
    identity_dir = PROJECT_DIR / "assets" / "identity"
    source_dir = PROJECT_DIR / "source"
    scene_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)
    identity_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)

    shutil.copy2(Path(__file__), source_dir / Path(__file__).name)
    shutil.copy2(SPEC_SOURCE, source_dir / SPEC_SOURCE.name)
    shutil.copy2(LUA_SOURCE, identity_dir / LUA_NAME)
    shutil.copy2(MIR_SOURCE, identity_dir / MIR_NAME)

    audit_rows = []
    pair_audits = []
    sequence = 0

    for pilot in PILOTS:
        source_md = SOURCE_PROJECT_DIR / SOURCE_SCENE_ID / f"{pilot['source_clip']}.md"
        source_payload = read_payload(source_md)
        base_prompt = str(source_payload["video_prompt"])
        source_storyboard = (
            SOURCE_PROJECT_DIR / "assets" / "storyboards" / pilot["storyboard"]
        )
        shutil.copy2(source_storyboard, storyboard_dir / pilot["storyboard"])

        prompts = {
            "A": base_prompt,
            "B": replace_subject_lines(base_prompt, pilot["identity_subjects"]),
        }
        if section(prompts["A"], "summary", "retention_analysis") != section(
            prompts["B"], "summary", "retention_analysis"
        ):
            raise ValueError(f"{pilot['pair_id']}: summary 통제 실패")
        if section(prompts["A"], "retention_analysis", "detailed_description") != section(
            prompts["B"], "retention_analysis", "detailed_description"
        ):
            raise ValueError(f"{pilot['pair_id']}: retention 통제 실패")
        if section(prompts["A"], "detailed_description", "overall_soundscape") != section(
            prompts["B"], "detailed_description", "overall_soundscape"
        ):
            raise ValueError(f"{pilot['pair_id']}: detailed_description 통제 실패")

        b_subject_definitions = section(prompts["B"], "subject_definitions", "summary")
        b_non_subject = prompts["B"][prompts["B"].index("summary:\n"):]
        expected_identity_labels = {
            f"<Picture {index}>"
            for index in range(2, 2 + len(pilot["identity_references"]))
        }
        for label in expected_identity_labels:
            if b_subject_definitions.count(label) != 1:
                raise ValueError(f"{pilot['pair_id']}: {label} Subject 정의 횟수 오류")
            if label in b_non_subject:
                raise ValueError(f"{pilot['pair_id']}: {label}이 Subject 정의 밖에 반복됨")

        storyboard_reference = dict(source_payload["references"][0])
        storyboard_reference.update({
            "picture_index": 1,
            "role": "complete_six_panel_storyboard",
            "label": "시간순 6패널 스토리보드",
            "description": "Six-panel storyboard defining temporal order, composition, placement, relative scale, action, environment, and lighting.",
            "instruction_en": "Picture 1 defines the six-stage shot order, compositions, camera viewpoints, subject placement, relative scale, actions, environment, and lighting.",
            "reference_kind": "storyboard",
            "source_path": f"assets/storyboards/{pilot['storyboard']}",
        })

        for condition in ("A", "B"):
            sequence += 1
            condition_label = (
                "스토리보드 단독"
                if condition == "A"
                else "스토리보드 + 캐릭터 정체성"
            )
            clip_id = f"EP02_SB6_V4_{pilot['pair_id']}_{condition}"
            references = [dict(storyboard_reference)]
            if condition == "B":
                references.extend(
                    identity_reference(index, identity)
                    for index, identity in enumerate(
                        pilot["identity_references"], start=2
                    )
                )
            prompt = prompts[condition]
            payload = {
                "schema_version": 2,
                "prompt_contract_version": source_payload["prompt_contract_version"],
                "workflow": h3_prompt_projects.WORKFLOW,
                "project_id": PROJECT_ID,
                "scene_id": SCENE_ID,
                "clip_id": clip_id,
                "source_clip_id": source_payload.get("source_clip_id"),
                "sequence": sequence,
                "scene_sequence": sequence,
                "status": "pending_user_pilot_review",
                "duration_seconds": 12.0,
                "title": f"{pilot['title']} · {condition_label}",
                "video_prompt": prompt,
                "references": references,
                "source_prompt_sha256": sha256_text(prompt),
                "bound_prompt_sha256": sha256_text(prompt),
                "video_prompt_sha256": sha256_text(prompt),
                "candidate_policy": "single_prompt_single_candidate_fixed_pair_seed",
                "scene_type": "storyboard_character_identity_ab_pilot_v4",
                "comparison_pair_id": pilot["pair_id"],
                "comparison_condition": condition,
                "recommended_fixed_seed": pilot["seed"],
                "reference_role_policy": (
                    "storyboard_controls_all"
                    if condition == "A"
                    else "storyboard_controls_shots_identity_pictures_define_subjects"
                ),
                "runtime_effects": source_payload.get("runtime_effects", []),
                "required_dialogue": source_payload.get("required_dialogue", []),
            }
            markdown = (
                f"# {clip_id} — {payload['title']}\n\n"
                "## Machine Payload\n```json\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
            (scene_dir / f"{clip_id}.md").write_text(markdown, encoding="utf-8")
            audit_rows.append({
                "clip_id": clip_id,
                "pair_id": pilot["pair_id"],
                "condition": condition,
                "recommended_fixed_seed": pilot["seed"],
                "reference_count": len(references),
                "video_prompt_sha256": sha256_text(prompt),
            })

        pair_audits.append({
            "pair_id": pilot["pair_id"],
            "recommended_fixed_seed": pilot["seed"],
            "same_summary": True,
            "same_retention_analysis": True,
            "same_detailed_description": True,
            "same_soundscape_and_music": (
                section(prompts["A"], "overall_soundscape", None)
                == section(prompts["B"], "overall_soundscape", None)
            ),
            "identity_labels_scoped_to_subject_definitions": True,
        })

    manifest = {
        "schema_version": 2,
        "project_kind": h3_prompt_projects.PROJECT_KIND,
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon EP02 · Storyboard + Character Identity A/B Pilot V4",
        "description": "Controlled A/B pilot comparing storyboard-only references with role-separated Lua and Mir identity references.",
        "clip_schema": "h3_r2v_clip_v2",
        "prompt_contract_version": "h3_user_supplied_passthrough_v5",
        "asset_storage": "project_local_storyboards_and_identity_references",
        "source_policy": "v3_action_trail_prompts_with_reference_role_isolation",
        "review_status": "pending_user_pilot_review",
        "queue_authorized": False,
        "video_generation_authorized": False,
        "queue_registration_performed": False,
        "video_generation_performed": False,
        "candidate_selection_performed": False,
        "upscale_performed": False,
        "build_facts": {
            "scene_count": 1,
            "pair_count": 3,
            "clip_count": 6,
            "condition_a_storyboard_only": 3,
            "condition_b_identity_augmented": 3,
            "scale_relationship_reference_count": 0,
            "negative_prompt_field_count": 0,
            "candidate_prompt_variants": 0,
            "queue_entry_count": 0,
        },
        "scene_counts": {SCENE_ID: 6},
    }
    (PROJECT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (PROJECT_DIR / "AB_REFERENCE_CONTROL_AUDIT.json").write_text(
        json.dumps({
            "status": "PASS",
            "project_id": PROJECT_ID,
            "policy": "Picture 1 controls storyboard structure; identity Pictures are cited once inside Subject definitions.",
            "pairs": pair_audits,
            "clips": audit_rows,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    loaded = h3_prompt_projects.project_clips(ROOT, PROJECT_ID)
    loader_rows = []
    for row in loaded.get("clips", []):
        clip = h3_prompt_projects.load_clip(ROOT, PROJECT_ID, row["clip_id"])
        references = clip.get("references", [])
        loader_rows.append({
            "clip_id": clip["clip_id"],
            "ready": clip.get("ready", False),
            "reference_count": len(references),
            "linked_reference_count": sum(bool(ref.get("linked")) for ref in references),
            "reference_errors": [
                ref.get("asset_error")
                for ref in references
                if ref.get("asset_error")
            ],
        })
    loader_pass = (
        len(loader_rows) == 6
        and all(
            row["ready"]
            and row["reference_count"] == row["linked_reference_count"]
            and not row["reference_errors"]
            for row in loader_rows
        )
    )
    (PROJECT_DIR / "LOADER_READINESS_AUDIT.json").write_text(
        json.dumps({
            "status": "PASS" if loader_pass else "FAIL",
            "project_id": PROJECT_ID,
            "clip_count": len(loader_rows),
            "clips": loader_rows,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not loader_pass:
        raise ValueError("V4 파일럿 로더 검수 실패")

    (PROJECT_DIR / "BUILD_REPORT.md").write_text(
        "# EP02 Storyboard + Character Identity A/B Pilot V4 Build Report\n\n"
        "- 프로젝트 생성: 완료\n"
        "- A/B Pair: 3개\n"
        "- 클립: 6개\n"
        "- 스토리보드 연결: 완료\n"
        "- 루아·미르 정체성 역할 분리 연결: 완료\n"
        "- 크기 관계 자산: 연결하지 않음\n"
        "- 로더 검수: PASS\n"
        "- 큐 등록 및 영상 생성: 실행하지 않음\n",
        encoding="utf-8",
    )
    print(PROJECT_DIR)


if __name__ == "__main__":
    main()
