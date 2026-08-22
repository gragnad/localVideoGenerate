from __future__ import annotations

"""Import user-authored EP00 R2V prompts without generating or rewriting them."""

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


ATTACHMENT_DIR = Path(
    "/home/nalstudio/.codex/attachments/9d7bfef7-1c24-4076-9404-6d4fc2c523b4"
)
SOURCE_FILES = [
    ATTACHMENT_DIR / "EP00_Opening_R2V_Clips.md",
    ATTACHMENT_DIR / "EP00_Scene01_First_Collision_R2V.md",
    ATTACHMENT_DIR / "EP00_Scene02_Hands_Close_The_Path_R2V.md",
    ATTACHMENT_DIR / "EP00_Scene03_Between_Forces_R2V.md",
    ATTACHMENT_DIR / "EP00_Scene04_Almost_Open_Path_R2V.md",
    ATTACHMENT_DIR / "EP00_Scene05_Before_Second_Heartbeat_R2V.md",
]

PROJECT_ID = "RaisingaDragonSeason01_EP00_USER_SUPPLIED_R2V_V1"
SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_user_supplied_r2v_v1"
LOCK_ID = "EP00_USER_SUPPLIED_PROMPTS_UNCHANGED_V1"

ASSETS = [
    (
        "lua_identity",
        "Lua identity sheet",
        ROOT
        / "projects/RaisingaDragonSeason01/rebuild_v2/designs_hq_v1/h3_identity_sheets/H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2.png",
    ),
    (
        "deep_sea_king_identity",
        "Deep Sea King identity sheet",
        ROOT
        / "projects/RaisingaDragonSeason01/rebuild_v2/designs_hq_v1/h3_identity_sheets/H3_ABYSS_KING_IDENTITY_HQ_V2.png",
    ),
    (
        "heartstone_chamber",
        "Heartstone altar chamber environment",
        ROOT
        / "projects/RaisingaDragonSeason01/rebuild_v2/action_moment_test_v1/images/HEARTSTONE_CHAMBER_ENVIRONMENT_V1.png",
    ),
    (
        "cyan_current_effect",
        "Approved cyan current and water-shield effect language",
        ROOT / "projects/RaisingaDragonSeason01/Dragon_Language_Current_Shield_Effects.png",
    ),
]

CLIP_RE = re.compile(
    r"^# R2V Clip\s+(?P<source_id>\S+)\s+—\s+(?P<title>.+?)\s*$"
    r"(?P<header>.*?)"
    r"^\*\*권장 길이:\*\*\s*(?P<minimum>\d+)\s*[–-]\s*(?P<maximum>\d+)\s*sec\s*$"
    r"(?P<body>.*?)"
    r"^```text\s*\n(?P<prompt>.*?)\n```",
    re.MULTILINE | re.DOTALL,
)
PICTURE_RE = re.compile(r"<Picture\s+(\d+)>")
DIALOGUE_RE = re.compile(r"<d>\[Korean\]\s*(.*?)</d>", re.DOTALL)
SUMMARY_RE = re.compile(r"^summary:\s*\n(.*?)(?=^retention_analysis:)", re.MULTILINE | re.DOTALL)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def import_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for scene_index, path in enumerate(SOURCE_FILES):
        text = path.read_text(encoding="utf-8")
        expected_count = len(re.findall(r"^# R2V Clip\s+", text, re.MULTILINE))
        matches = list(CLIP_RE.finditer(text))
        if len(matches) != expected_count:
            raise ValueError(f"Could not import every clip from {path.name}: {len(matches)}/{expected_count}")
        scene_id = "EP00-OPENING" if scene_index == 0 else f"EP00-SCENE-{scene_index:02d}"
        for match in matches:
            prompt = match.group("prompt")
            picture_ids = sorted({int(value) for value in PICTURE_RE.findall(prompt)})
            if not picture_ids or picture_ids[-1] > len(ASSETS):
                raise ValueError(f"Unsupported Picture requirement in {match.group('source_id')}: {picture_ids}")
            summary_match = SUMMARY_RE.search(prompt)
            rows.append({
                "scene_id": scene_id,
                "source_file": path,
                "source_id": match.group("source_id"),
                "title": match.group("title").strip(),
                "duration_seconds": float(match.group("maximum")),
                "recommended_duration": f"{match.group('minimum')}–{match.group('maximum')} sec",
                "prompt": prompt,
                "prompt_sha256": sha256_text(prompt),
                "picture_count": picture_ids[-1],
                "required_dialogue": [value.strip() for value in DIALOGUE_RE.findall(prompt)],
                "summary": summary_match.group(1).strip() if summary_match else match.group("title").strip(),
            })
    return rows


def build() -> dict[str, object]:
    destination = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    if destination.exists():
        raise FileExistsError(f"Existing projects are not overwritten: {PROJECT_ID}")
    for path in SOURCE_FILES:
        if not path.is_file():
            raise FileNotFoundError(path)
    for _role, _label, path in ASSETS:
        if not path.is_file():
            raise FileNotFoundError(path)

    rows = import_rows()
    base = h3_prompt_projects.projects_root(ROOT)
    base.mkdir(parents=True, exist_ok=True)
    staging = base / f".{PROJECT_ID}.building-{secrets.token_hex(4)}"
    staging.mkdir()
    try:
        manifest = {
            "schema_version": 2,
            "project_kind": h3_prompt_projects.PROJECT_KIND,
            "project_id": PROJECT_ID,
            "title": "Raising a Dragon EP00 · User-Supplied R2V Prompts V1",
            "description": "Direct import of the six user-supplied EP00 prompt documents with no prompt generation, rewriting, or candidate derivation.",
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
            "asset_storage": "project_local_shared",
            "source_policy": "user_supplied_prompt_text_unchanged",
            "canonical_source_lineage": [path.name for path in SOURCE_FILES],
            "locked_rule_id": LOCK_ID,
            "import_script": "scripts/import_ep00_user_supplied_r2v_project.py",
            "candidate_policy": "A_equals_D_equals_E_exactly",
            "review_status": "pending_user_prompt_review",
            "build_facts": {
                "source_document_count": len(SOURCE_FILES),
                "clip_count": len(rows),
                "candidate_entry_count": len(rows) * 3,
                "unique_prompt_count": len(rows),
                "shared_asset_count": len(ASSETS),
                "new_asset_generation_count": 0,
            },
            "queue_authorized": False,
            "video_generation_authorized": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        source_dir = staging / "source"
        source_dir.mkdir()
        for path in SOURCE_FILES:
            shutil.copy2(path, source_dir / f"{path.stem}.source.txt")

        shared_assets = staging / "assets" / "shared"
        shared_assets.mkdir(parents=True)
        asset_paths: list[str] = []
        for picture_index, (_role, _label, path) in enumerate(ASSETS, start=1):
            relative = f"assets/shared/picture_{picture_index}.png"
            shutil.copy2(path, staging / relative)
            asset_paths.append(relative)

        for sequence, row in enumerate(rows, start=1):
            scene_dir = staging / str(row["scene_id"])
            scene_dir.mkdir(exist_ok=True)
            clip_id = f"EP00-{str(row['source_id']).replace('C', 'C')}"
            prompt = str(row["prompt"])
            variants = [
                {
                    "variant_id": variant_id,
                    "label": f"Candidate {variant_id} · user-supplied original",
                    "rationale": "Exact duplicate of the user-supplied prompt; no derivation.",
                    "video_prompt": prompt,
                }
                for variant_id in ("A", "D", "E")
            ]
            references = []
            for picture_index in range(1, int(row["picture_count"]) + 1):
                role, label, _path = ASSETS[picture_index - 1]
                references.append({
                    "picture_index": picture_index,
                    "role": role,
                    "label": label,
                    "description": "",
                    "instruction_en": "",
                    "reference_kind": "visual_reference",
                    "required": True,
                    "source_path": asset_paths[picture_index - 1],
                })
            payload = {
                "schema_version": 2,
                "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
                "workflow": h3_prompt_projects.WORKFLOW,
                "project_id": PROJECT_ID,
                "scene_id": row["scene_id"],
                "clip_id": clip_id,
                "source_clip_id": row["source_id"],
                "sequence": sequence,
                "status": "pending_user_prompt_review",
                "duration_seconds": row["duration_seconds"],
                "recommended_duration": row["recommended_duration"],
                "title": row["title"],
                "video_prompt": prompt,
                "prompt_variants": variants,
                "references": references,
                "canonical_source_lineage": [Path(str(row["source_file"])).name],
                "locked_rule_id": LOCK_ID,
                "summary": row["summary"],
                "required_dialogue": row["required_dialogue"],
                "dialogue_lock_version": "USER_SUPPLIED_PROMPT_DIALOGUE_V1",
                "source_prompt_sha256": row["prompt_sha256"],
                "candidate_policy": "A=D=E; exact user-supplied prompt",
                "scene_type": "user_supplied_prompt_import",
                "semantic_review": "not_performed",
            }
            markdown = (
                f"# {clip_id} · {row['title']} · MiniMax H3 R2V\n\n"
                "## Machine Payload\n\n```json\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
            (scene_dir / f"{clip_id}.md").write_text(markdown, encoding="utf-8")
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    for path in SOURCE_FILES:
        shutil.copy2(path, SOURCE_DIR / path.name)
    return {
        "project_id": PROJECT_ID,
        "project_path": str(destination),
        "source_document_count": len(SOURCE_FILES),
        "clip_count": len(rows),
        "candidate_entry_count": len(rows) * 3,
        "candidate_policy": "A_equals_D_equals_E_exactly",
        "shared_asset_count": len(ASSETS),
        "new_asset_generation_count": 0,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
