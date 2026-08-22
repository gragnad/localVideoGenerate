from __future__ import annotations

"""Import the externally authored EP00 H3 prompts as a new R2V project.

The external prose remains authoritative. The only model-facing edits insert
<Subject 1> before a Shot's first untagged Lua mention when required by the
local H3 contract. Assets are copied into project-local Picture slots.
"""

import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402


ATTACHMENT = Path(
    "/home/nalstudio/.codex/attachments/885e10d9-ea24-4d15-a813-2dec5ca3f5dc/"
    "〈용 키우기〉 EP00 H3 R2V 공식 형식 재설계 — 오프닝·첫 번째 충돌.md"
)
SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_external_official_redesign_new"
PROJECT_ID = "RaisingaDragonSeason01_EP00_EXTERNAL_H3_OFFICIAL_REDESIGN_R2V_V1"
SCENE_ID = "EP00-EXT-R2V"

ASSETS = (
    (
        "lua_character_reference",
        "Lua character reference",
        ROOT / "projects/RaisingaDragonSeason01/rebuild_v2/designs_hq_v1/h3_identity_sheets/H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2.png",
    ),
    (
        "deep_sea_king_character_reference",
        "Deep Sea King character reference",
        ROOT / "projects/RaisingaDragonSeason01/rebuild_v2/designs_hq_v1/h3_identity_sheets/H3_ABYSS_KING_IDENTITY_HQ_V2.png",
    ),
    (
        "heartstone_altar_chamber_environment_reference",
        "Heartstone altar chamber environment reference",
        ROOT / "projects/RaisingaDragonSeason01/rebuild_v2/action_moment_test_v1/images/HEARTSTONE_CHAMBER_ENVIRONMENT_V1.png",
    ),
    (
        "cyan_current_and_water_effect_reference",
        "cyan current and water-effect reference",
        ROOT / "projects/RaisingaDragonSeason01/Dragon_Language_Current_Shield_Effects.png",
    ),
)

CLIP_TITLES = (
    "끊기는 수로와 첫 공격 예고",
    "손목 위 회피와 뒤늦은 충격",
    "세 걸음의 창 돌진",
    "놓지 않는 손과 지렛대",
    "두 번의 충돌과 뒤바뀐 공간",
)
DIALOGUE = (
    ["혼자서도 여기까지 왔구나."],
    [],
    [],
    ["놓아라."],
    [],
)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_text(value: str) -> str:
    return digest_bytes(value.encode("utf-8"))


def extract_external_prompts(text: str) -> list[str]:
    prompts = re.findall(r"### H3 R2V Prompt\n\n```text\n(.*?)\n```", text, re.DOTALL)
    if len(prompts) != 5:
        raise ValueError(f"Expected five external H3 prompts, found {len(prompts)}")
    return prompts


def apply_minimal_subject_contract(prompt: str) -> tuple[str, int]:
    marker = "detailed_description:\n"
    start = prompt.index(marker) + len(marker)
    end = prompt.index("\noverall_soundscape:\n")
    detail = prompt[start:end]
    insertion_count = 0

    def patch_shot(match: re.Match[str]) -> str:
        nonlocal insertion_count
        whole = match.group(0)
        body = match.group(4)
        lua_position = body.find("Lua")
        tag_position = body.find("<Subject 1>")
        if lua_position >= 0 and (tag_position < 0 or tag_position > lua_position):
            offset = match.start(4) - match.start(0) + lua_position
            whole = whole[:offset] + "<Subject 1> " + whole[offset:]
            insertion_count += 1
        return whole

    patched_detail = h3_prompt_contract.SHOT_RE.sub(patch_shot, detail)
    return prompt[:start] + patched_detail + prompt[end:], insertion_count


def prompt_summary(prompt: str) -> str:
    return prompt.split("\nsummary:\n", 1)[1].split("\nretention_analysis:\n", 1)[0].strip()


def build() -> dict[str, object]:
    destination = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    if destination.exists():
        raise FileExistsError(f"Existing projects are not overwritten: {PROJECT_ID}")
    if not ATTACHMENT.is_file():
        raise FileNotFoundError(ATTACHMENT)
    for _role, _label, path in ASSETS:
        if not path.is_file():
            raise FileNotFoundError(path)

    source_bytes = ATTACHMENT.read_bytes()
    source_text = source_bytes.decode("utf-8")
    external_prompts = extract_external_prompts(source_text)
    prepared: list[dict[str, object]] = []
    total_insertions = 0
    for index, external_prompt in enumerate(external_prompts, start=1):
        model_prompt, insertion_count = apply_minimal_subject_contract(external_prompt)
        report = h3_prompt_contract.validate_prompt(
            model_prompt,
            duration_seconds=15.0,
            require_shot_timestamps=True,
            allow_four_shots=False,
        )
        if not report.valid or report.shot_count != 3:
            raise ValueError(
                f"External Clip {index:02d} failed H3 validation: "
                + "; ".join(issue.message for issue in report.errors)
            )
        total_insertions += insertion_count
        prepared.append({
            "external_prompt": external_prompt,
            "model_prompt": model_prompt,
            "insertion_count": insertion_count,
            "external_sha256": digest_text(external_prompt),
            "model_sha256": digest_text(model_prompt),
        })

    base = h3_prompt_projects.projects_root(ROOT)
    base.mkdir(parents=True, exist_ok=True)
    staging = base / f".{PROJECT_ID}.building-{secrets.token_hex(4)}"
    staging.mkdir()
    try:
        manifest = {
            "schema_version": 2,
            "project_kind": h3_prompt_projects.PROJECT_KIND,
            "project_id": PROJECT_ID,
            "title": "Raising a Dragon EP00 · External Official-Format Redesign R2V V1",
            "description": "Five externally authored H3 R2V prompts with project-local Lua, Deep Sea King, chamber, and cyan-effect assets.",
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": h3_prompt_contract.CONTRACT_VERSION,
            "asset_storage": "project_local",
            "source_policy": "external_prompt_authoritative_minimal_subject_tag_fix_only",
            "canonical_source_lineage": [ATTACHMENT.name],
            "external_source_sha256": digest_bytes(source_bytes),
            "locked_rule_id": "EP00_EXTERNAL_OFFICIAL_REDESIGN_R2V_V1",
            "build_script": "scripts/build_ep00_external_official_redesign_project.py",
            "dialogue_lock_version": "EP00_EXTERNAL_PROMPT_DIALOGUE_LOCK_V1",
            "dialogue_clip_count": 2,
            "dialogue_line_count": 2,
            "scene_types": ["external_prompt"],
            "generation_blocked": False,
            "replacement_project_ids": [],
            "review_status": "pending_user_prompt_review",
            "build_facts": {
                "clip_count": 5,
                "prompt_count": 5,
                "total_duration_seconds": 75.0,
                "external_prompt_count": 5,
                "minimal_subject_tag_insertions": total_insertions,
            },
            "queue_authorized": False,
            "video_generation_authorized": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        source_copy_dir = staging / "source"
        source_copy_dir.mkdir()
        shutil.copy2(ATTACHMENT, source_copy_dir / "EXTERNAL_PROMPTS_SOURCE.source.txt")

        clip_dir = staging / SCENE_ID
        clip_dir.mkdir()
        for index, row in enumerate(prepared, start=1):
            clip_id = f"EP00-EXT-R2V-C{index:02d}"
            picture_count = 4 if index <= 2 else 3
            references = []
            for picture_index, (role, label, source) in enumerate(ASSETS[:picture_count], start=1):
                relative = f"assets/{clip_id}/picture_{picture_index}.png"
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                references.append({
                    "picture_index": picture_index,
                    "role": role,
                    "label": label,
                    "description": "",
                    "instruction_en": "",
                    "reference_kind": "visual_reference",
                    "required": True,
                    "source_path": relative,
                })
            payload = {
                "schema_version": 2,
                "prompt_contract_version": h3_prompt_contract.CONTRACT_VERSION,
                "workflow": h3_prompt_projects.WORKFLOW,
                "project_id": PROJECT_ID,
                "scene_id": SCENE_ID,
                "clip_id": clip_id,
                "sequence": index,
                "status": "pending_user_prompt_review",
                "duration_seconds": 15.0,
                "title": CLIP_TITLES[index - 1],
                "video_prompt": row["model_prompt"],
                "prompt_variants": [],
                "references": references,
                "canonical_source_lineage": [ATTACHMENT.name],
                "locked_rule_id": "EP00_EXTERNAL_OFFICIAL_REDESIGN_R2V_V1",
                "source_shot_id": f"external-r2v-clip-{index:02d}",
                "summary": prompt_summary(str(row["model_prompt"])),
                "required_dialogue": DIALOGUE[index - 1],
                "dialogue_lock_version": "EP00_EXTERNAL_PROMPT_DIALOGUE_LOCK_V1",
                "external_prompt_source_sha256": row["external_sha256"],
                "model_prompt_sha256": row["model_sha256"],
                "minimal_subject_tag_insertions": row["insertion_count"],
                "external_prompt_preservation_policy": "exact_except_required_first_subject_tag_insertions",
                "scene_type": "external_prompt",
                "semantic_review": "pending_user_prompt_review",
            }
            markdown = (
                f"# {clip_id} · {CLIP_TITLES[index - 1]} · MiniMax H3 R2V\n\n"
                "## Machine Payload\n\n```json\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
            (clip_dir / f"{clip_id}.md").write_text(markdown, encoding="utf-8")

        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    overview = h3_prompt_projects.project_clips(ROOT, PROJECT_ID)
    invalid = [clip for clip in overview["clips"] if not clip["ready"]]
    if invalid:
        raise RuntimeError(f"Published project validation failed: {invalid[0]['clip_id']}: {invalid[0]['errors']}")

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ATTACHMENT, SOURCE_DIR / "EXTERNAL_PROMPTS_SOURCE.md")
    provenance = {
        "project_id": PROJECT_ID,
        "external_source": str(ATTACHMENT),
        "external_source_sha256": digest_bytes(source_bytes),
        "clip_count": 5,
        "minimal_subject_tag_insertions": total_insertions,
        "model_facing_changes": "Only <Subject 1> insertions before first untagged Lua mentions in Shots.",
        "assets": [str(path) for _role, _label, path in ASSETS],
    }
    (SOURCE_DIR / "EP00_EXTERNAL_OFFICIAL_REDESIGN_PROVENANCE_V1.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "project_id": PROJECT_ID,
        "project_path": str(destination),
        "clip_count": len(overview["clips"]),
        "ready_count": sum(1 for clip in overview["clips"] if clip["ready"]),
        "prompt_count": 5,
        "minimal_subject_tag_insertions": total_insertions,
    }


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
