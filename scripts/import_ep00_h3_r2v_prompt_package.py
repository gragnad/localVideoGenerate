from __future__ import annotations

"""Import the user-authored 13-clip EP00 H3 package without rewriting prompts."""

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


PROMPT_DOCUMENT = Path(
    "/home/nalstudio/.codex/attachments/f380bd51-e649-4399-b0dd-f6df5b5c1f9e/EP00_H3_R2V_Prompt_Document.md"
)
EXECUTION_GUIDE = Path(
    "/home/nalstudio/.codex/attachments/c3dbd6a3-1fad-44e6-b8a2-7b710f588aac/EP00_Codex_Project_Execution_Guide.md"
)
PROJECT_ID = "RaisingaDragonSeason01_EP00_USER_H3_R2V_PACKAGE_V1"
SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_user_prompt_package_v1"
LOCK_ID = "EP00_USER_H3_PROMPT_PACKAGE_UNCHANGED_V1"
PROJECT_TITLE = "Raising a Dragon EP00 · User H3 R2V Package V1"
PROJECT_DESCRIPTION = "Direct import of thirteen user-authored prompts with execution-guide asset mapping and three generated continuity backgrounds."
IMPORT_SCRIPT = "scripts/import_ep00_h3_r2v_prompt_package.py"
DURATIONS = {f"C{index:02d}": 15.0 for index in range(1, 14)}
EXPECTED_CLIP_IDS = [f"C{index:02d}" for index in range(1, 14)]
PROMPT_SECTION_MARKER = "## 11. Complete H3 R2V Prompts"
NEW_BACKGROUND_GENERATION_COUNT = 3
REUSED_BACKGROUND_COUNT = 0
ADDITIONAL_SOURCE_FILES: list[Path] = []
PROMPT_OVERRIDES: dict[str, str] = {}

LIBRARY = ROOT / "projects" / "RaisingaDragonSeason01" / "asset_sheets_master_v1"
ASSETS = {
    "lua": LIBRARY / "01_characters/H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2.png",
    "king": LIBRARY / "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2.png",
    "spear": LIBRARY / "03_props/H3_LUA_SPEAR_PROP_HQ_V3.png",
    "shield": LIBRARY / "05_effects/EP00/Current_Shield_IRREGULAR_CURVED_REFERENCE_SHEET_V4.png",
    "ribbon": LIBRARY / "05_effects/EP00/Moving_Current_Ribbon_REFERENCE_SHEET_V3.png",
    "master": SOURCE_DIR / "generated_backgrounds/BG_EP00_S01_ABYSS_ALTAR_MASTER.png",
    "damaged": SOURCE_DIR / "generated_backgrounds/BG_EP00_S01_ABYSS_ALTAR_DAMAGED.png",
    "final": SOURCE_DIR / "generated_backgrounds/BG_EP00_S01_ABYSS_ALTAR_FINAL_DAMAGE.png",
}
ASSET_LABELS = {
    "lua": ("lua_identity", "Lua Complete Scales identity sheet"),
    "king": ("abyss_king_identity", "Abyss King identity sheet"),
    "spear": ("lua_spear_prop", "Lua spear prop sheet"),
    "shield": ("irregular_curved_shield", "Irregular curved current shield reference"),
    "ribbon": ("moving_current_ribbon", "Moving current ribbon reference"),
    "master": ("abyss_altar_master", "EP00 Abyss Altar MASTER background"),
    "damaged": ("abyss_altar_damaged", "EP00 Abyss Altar DAMAGED background"),
    "final": ("abyss_altar_final_damage", "EP00 Abyss Altar FINAL_DAMAGE background"),
}

CLIP_ASSETS = {
    "C01": ["lua", "king", "spear", "master"],
    "C02": ["lua", "king", "spear", "master"],
    "C03": ["lua", "king", "spear", "master"],
    "C04": ["lua", "king", "spear", "master"],
    "C05": ["lua", "king", "spear", "master", "shield"],
    "C06": ["lua", "king", "spear", "damaged", "shield"],
    "C07": ["lua", "king", "spear", "damaged"],
    "C08": ["lua", "king", "spear", "damaged"],
    "C09": ["lua", "king", "spear", "damaged"],
    "C10": ["lua", "king", "spear", "damaged", "ribbon"],
    "C11": ["lua", "king", "spear", "damaged"],
    "C12": ["lua", "king", "spear", "final"],
    "C13": ["lua", "king", "final"],
}

CLIP_RE = re.compile(
    r"^### Clip (?P<clip_id>C\d{2}) — (?P<title>.+?)\s*$\n\n"
    r"(?P<prompt>subject_definitions:\n.*?^non_diegetic_music:\n.*?)(?=\n\n---(?:\n|\Z))",
    re.MULTILINE | re.DOTALL,
)
SUMMARY_RE = re.compile(r"^summary:\s*\n(.*?)(?=^retention_analysis:)", re.MULTILINE | re.DOTALL)
DIALOGUE_RE = re.compile(r"<d>\[Korean\]\s*(.*?)</d>", re.DOTALL)


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prompt_rows() -> list[dict[str, object]]:
    text = PROMPT_DOCUMENT.read_text(encoding="utf-8")
    prompt_section = text[text.index(PROMPT_SECTION_MARKER) :]
    rows = []
    for match in CLIP_RE.finditer(prompt_section):
        clip_id = match.group("clip_id")
        prompt = PROMPT_OVERRIDES.get(clip_id, match.group("prompt"))
        summary = SUMMARY_RE.search(prompt)
        rows.append({
            "clip_id": clip_id,
            "title": match.group("title").strip(),
            "prompt": prompt,
            "prompt_sha256": digest_text(prompt),
            "summary": summary.group(1).strip() if summary else match.group("title").strip(),
            "required_dialogue": [line.strip() for line in DIALOGUE_RE.findall(prompt)],
        })
    if [row["clip_id"] for row in rows] != EXPECTED_CLIP_IDS:
        raise ValueError("The prompt document did not yield the expected clip sequence")
    return rows


def build() -> dict[str, object]:
    destination = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    if destination.exists():
        raise FileExistsError(f"Existing projects are not overwritten: {PROJECT_ID}")
    for path in (PROMPT_DOCUMENT, EXECUTION_GUIDE, *ADDITIONAL_SOURCE_FILES, *ASSETS.values()):
        if not path.is_file():
            raise FileNotFoundError(path)

    rows = prompt_rows()
    base = h3_prompt_projects.projects_root(ROOT)
    base.mkdir(parents=True, exist_ok=True)
    staging = base / f".{PROJECT_ID}.building-{secrets.token_hex(4)}"
    staging.mkdir()
    try:
        manifest = {
            "schema_version": 2,
            "project_kind": h3_prompt_projects.PROJECT_KIND,
            "project_id": PROJECT_ID,
            "title": PROJECT_TITLE,
            "description": PROJECT_DESCRIPTION,
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
            "asset_storage": "project_local_shared",
            "source_policy": "user_prompt_exact_execution_guide_assets_only",
            "canonical_source_lineage": [
                PROMPT_DOCUMENT.name,
                EXECUTION_GUIDE.name,
                *[path.name for path in ADDITIONAL_SOURCE_FILES],
            ],
            "locked_rule_id": LOCK_ID,
            "import_script": IMPORT_SCRIPT,
            "candidate_policy": "A_equals_D_equals_E_exactly",
            "review_status": "pending_user_prompt_review",
            "build_facts": {
                "clip_count": len(rows),
                "candidate_entry_count": len(rows) * 3,
                "unique_prompt_count": len(rows),
                "approved_library_asset_count": 5,
                "new_background_generation_count": NEW_BACKGROUND_GENERATION_COUNT,
                "reused_background_count": REUSED_BACKGROUND_COUNT,
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
        shutil.copy2(PROMPT_DOCUMENT, source_dir / f"{PROMPT_DOCUMENT.stem}.source.txt")
        shutil.copy2(EXECUTION_GUIDE, source_dir / f"{EXECUTION_GUIDE.stem}.source.txt")
        for path in ADDITIONAL_SOURCE_FILES:
            shutil.copy2(path, source_dir / f"{path.stem}.source.txt")

        shared_dir = staging / "assets" / "shared"
        shared_dir.mkdir(parents=True)
        copied_assets = {}
        for key, path in ASSETS.items():
            relative = f"assets/shared/{path.name}"
            shutil.copy2(path, staging / relative)
            copied_assets[key] = relative

        scene_dir = staging / "EP00-CONTINUOUS"
        scene_dir.mkdir()
        for sequence, row in enumerate(rows, start=1):
            clip_id = f"EP00_{row['clip_id']}"
            prompt = str(row["prompt"])
            variants = [
                {
                    "variant_id": candidate,
                    "label": f"Candidate {candidate} · user-supplied original",
                    "rationale": "Exact duplicate of the user-supplied prompt; no derivation.",
                    "video_prompt": prompt,
                }
                for candidate in ("A", "D", "E")
            ]
            references = []
            for picture_index, asset_key in enumerate(CLIP_ASSETS[str(row["clip_id"])], start=1):
                role, label = ASSET_LABELS[asset_key]
                references.append({
                    "picture_index": picture_index,
                    "role": role,
                    "label": label,
                    "description": "",
                    "instruction_en": "",
                    "reference_kind": "visual_reference",
                    "required": True,
                    "source_path": copied_assets[asset_key],
                })
            payload = {
                "schema_version": 2,
                "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
                "workflow": h3_prompt_projects.WORKFLOW,
                "project_id": PROJECT_ID,
                "scene_id": "EP00-CONTINUOUS",
                "clip_id": clip_id,
                "source_clip_id": row["clip_id"],
                "sequence": sequence,
                "status": "pending_user_prompt_review",
                "duration_seconds": DURATIONS[str(row["clip_id"])],
                "title": row["title"],
                "video_prompt": prompt,
                "prompt_variants": variants,
                "references": references,
                "canonical_source_lineage": [
                    PROMPT_DOCUMENT.name,
                    EXECUTION_GUIDE.name,
                    *[path.name for path in ADDITIONAL_SOURCE_FILES],
                ],
                "locked_rule_id": LOCK_ID,
                "summary": row["summary"],
                "required_dialogue": row["required_dialogue"],
                "dialogue_lock_version": "USER_SUPPLIED_EP00_H3_DIALOGUE_V1",
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
    shutil.copy2(PROMPT_DOCUMENT, SOURCE_DIR / PROMPT_DOCUMENT.name)
    shutil.copy2(EXECUTION_GUIDE, SOURCE_DIR / EXECUTION_GUIDE.name)
    for path in ADDITIONAL_SOURCE_FILES:
        shutil.copy2(path, SOURCE_DIR / path.name)
    return {
        "project_id": PROJECT_ID,
        "project_path": str(destination),
        "clip_count": len(rows),
        "candidate_entry_count": len(rows) * 3,
        "candidate_policy": "A_equals_D_equals_E_exactly",
        "approved_library_asset_count": 5,
        "new_background_generation_count": NEW_BACKGROUND_GENERATION_COUNT,
        "reused_background_count": REUSED_BACKGROUND_COUNT,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
