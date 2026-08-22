from __future__ import annotations

"""Import the user-authored EP01 S01/S02 H3 prompts without rewriting them."""

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
    "/home/nalstudio/.codex/attachments/ce6d6cac-a329-44b9-b478-8251854820c1"
)
S01_DOCUMENT = ATTACHMENT_DIR / "EP01_S01_H3_R2V_Prompt_Document_V3_OFFICIAL_GUIDE.md"
S02_DOCUMENT = ATTACHMENT_DIR / "EP01_S02_H3_R2V_Prompt_Document_V3_OFFICIAL_GUIDE.md"
ASSET_GUIDE = ATTACHMENT_DIR / "EP01_S02_Codex_Asset_Execution_Guide.md"

PROJECT_ID = "RaisingaDragonSeason01_EP01_S01_S02_USER_H3_R2V_PACKAGE_V1"
PROJECT_TITLE = "Raising a Dragon EP01 · S01/S02 User H3 R2V Package V1"
SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep01_user_prompt_package_v1"
LIBRARY = ROOT / "projects" / "RaisingaDragonSeason01" / "asset_sheets_master_v1"
GENERATED = SOURCE_DIR / "generated_backgrounds"

ASSET_PATHS = {
    "H3_YOUNG_MIR_IDENTITY_HQ_V2.png": LIBRARY / "01_characters/H3_YOUNG_MIR_IDENTITY_HQ_V2.png",
    "BG_EP01_S01_STORM_OCEAN_SURFACE.png": LIBRARY / "04_backgrounds/EP01_MASTER/BG_EP01_S01_STORM_OCEAN_SURFACE.png",
    "BG_EP01_S01_UNDERWATER_DESCENT.png": LIBRARY / "04_backgrounds/EP01_MASTER/BG_EP01_S01_UNDERWATER_DESCENT.png",
    "BG_EP01_S01_MIR_RUIN_CHAMBER.png": LIBRARY / "04_backgrounds/EP01_MASTER/BG_EP01_S01_MIR_RUIN_CHAMBER.png",
    "BG_EP01_S01_COLLAPSED_RUINS.png": LIBRARY / "04_backgrounds/EP01_MASTER/BG_EP01_S01_COLLAPSED_RUINS.png",
    "HEARTSTONE_CHAMBER_ENVIRONMENT_V1.png": LIBRARY / "04_backgrounds/EP00/HEARTSTONE_CHAMBER_ENVIRONMENT_V1.png",
    "H3_LUA_BASE_IDENTITY_HQ_V2.png": LIBRARY / "01_characters/H3_LUA_BASE_IDENTITY_HQ_V2.png",
    "H3_OLD_FISHERMAN_IDENTITY_HQ_V1.png": LIBRARY / "01_characters/H3_OLD_FISHERMAN_IDENTITY_HQ_V1.png",
    "H3_LUA_SPEAR_PROP_HQ_V3.png": LIBRARY / "03_props/H3_LUA_SPEAR_PROP_HQ_V3.png",
    "H3_SKEPTICAL_VILLAGER_IDENTITY_HQ_V1.png": LIBRARY / "01_characters/H3_SKEPTICAL_VILLAGER_IDENTITY_HQ_V1.png",
    "H3_SHADOW_FISH_IDENTITY_HQ_V4.png": LIBRARY / "02_enemies/H3_SHADOW_FISH_IDENTITY_HQ_V4.png",
    "BG_EP01_S02_VILLAGE_MASTER.png": LIBRARY / "04_backgrounds/EP01_MASTER/BG_EP01_S02_VILLAGE_MASTER.png",
    "BG_EP01_S02_FISHERMAN_WARNING_AREA.png": LIBRARY / "04_backgrounds/EP01_MASTER/BG_EP01_S02_FISHERMAN_WARNING_AREA.png",
    "BG_EP01_S02_LUA_BEDROOM_MORNING.png": GENERATED / "BG_EP01_S02_LUA_BEDROOM_MORNING.png",
    "BG_EP01_S02_BREAKWATER_LOWER_DEEP_WATER.png": GENERATED / "BG_EP01_S02_BREAKWATER_LOWER_DEEP_WATER.png",
}

ASSET_ROLES = {
    "H3_YOUNG_MIR_IDENTITY_HQ_V2.png": ("young_mir_identity", "Young Mir identity sheet"),
    "BG_EP01_S01_STORM_OCEAN_SURFACE.png": ("storm_ocean_surface", "EP01 S01 storm ocean surface"),
    "BG_EP01_S01_UNDERWATER_DESCENT.png": ("underwater_descent", "EP01 S01 underwater descent"),
    "BG_EP01_S01_MIR_RUIN_CHAMBER.png": ("mir_ruin_chamber", "EP01 S01 Mir ruin chamber"),
    "BG_EP01_S01_COLLAPSED_RUINS.png": ("collapsed_ruins", "EP01 S01 collapsed ruins"),
    "HEARTSTONE_CHAMBER_ENVIRONMENT_V1.png": ("heartstone_chamber", "Heartstone chamber environment"),
    "H3_LUA_BASE_IDENTITY_HQ_V2.png": ("lua_identity", "Lua base identity sheet"),
    "H3_OLD_FISHERMAN_IDENTITY_HQ_V1.png": ("old_fisherman_identity", "Old Fisherman identity sheet"),
    "H3_LUA_SPEAR_PROP_HQ_V3.png": ("lua_spear_prop", "Lua spear prop sheet"),
    "H3_SKEPTICAL_VILLAGER_IDENTITY_HQ_V1.png": ("skeptical_villager_identity", "Working villager identity sheet"),
    "H3_SHADOW_FISH_IDENTITY_HQ_V4.png": ("shadow_fish_identity", "Shadow fish identity sheet"),
    "BG_EP01_S02_VILLAGE_MASTER.png": ("village_master", "EP01 S02 village master background"),
    "BG_EP01_S02_FISHERMAN_WARNING_AREA.png": ("fisherman_warning_area", "EP01 S02 fisherman warning area"),
    "BG_EP01_S02_LUA_BEDROOM_MORNING.png": ("lua_bedroom_morning", "EP01 S02 Lua bedroom morning background"),
    "BG_EP01_S02_BREAKWATER_LOWER_DEEP_WATER.png": ("breakwater_lower_deep_water", "EP01 S02 lower breakwater deep-water background"),
}

CLIP_RE = re.compile(
    r"^## (?P<clip_id>EP01_C\d{2}) — (?P<title>.+?)\s*$"
    r"(?P<body>.*?)(?=^## EP01_C\d{2} — |^# 5\.|\Z)",
    re.MULTILINE | re.DOTALL,
)
DURATION_RE = re.compile(r"\*\*Target duration:\*\*\s*([0-9.]+) seconds")
INPUT_RE = re.compile(r"^- `<Picture (\d+)>` `([^`]+)`\s*$", re.MULTILINE)
PROMPT_RE = re.compile(r"```text\s*\n(.*?)\n```", re.DOTALL)
SUMMARY_RE = re.compile(r"^summary:\s*\n(.*?)(?=^retention_analysis:)", re.MULTILINE | re.DOTALL)
DIALOGUE_RE = re.compile(r"<d>\[Korean\]\s*(.*?)</d>", re.DOTALL)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_document(path: Path, expected_ids: list[str], scene_id: str) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    rows: list[dict[str, object]] = []
    for match in CLIP_RE.finditer(text):
        body = match.group("body")
        duration = DURATION_RE.search(body)
        prompt = PROMPT_RE.search(body)
        if not duration or not prompt:
            raise ValueError(f"Incomplete clip block: {match.group('clip_id')}")
        inputs = sorted(
            [(int(index), name) for index, name in INPUT_RE.findall(body)],
            key=lambda row: row[0],
        )
        if [index for index, _ in inputs] != list(range(1, len(inputs) + 1)):
            raise ValueError(f"Non-contiguous Picture order: {match.group('clip_id')}")
        prompt_text = prompt.group(1)
        summary = SUMMARY_RE.search(prompt_text)
        rows.append({
            "clip_id": match.group("clip_id"),
            "title": match.group("title").strip(),
            "scene_id": scene_id,
            "duration_seconds": float(duration.group(1)),
            "asset_names": [name for _, name in inputs],
            "video_prompt": prompt_text,
            "summary": summary.group(1).strip() if summary else match.group("title").strip(),
            "required_dialogue": [line.strip() for line in DIALOGUE_RE.findall(prompt_text)],
            "source_prompt_sha256": digest(prompt_text),
            "source_document": path.name,
        })
    if [str(row["clip_id"]) for row in rows] != expected_ids:
        raise ValueError(f"Unexpected clip sequence in {path.name}")
    return rows


def prompt_rows() -> list[dict[str, object]]:
    return [
        *parse_document(S01_DOCUMENT, [f"EP01_C{i:02d}" for i in range(1, 13)], "EP01-S01"),
        *parse_document(S02_DOCUMENT, [f"EP01_C{i:02d}" for i in range(13, 27)], "EP01-S02"),
    ]


def asset_check_report() -> str:
    reused = [name for name in ASSET_PATHS if name not in {
        "BG_EP01_S02_LUA_BEDROOM_MORNING.png",
        "BG_EP01_S02_BREAKWATER_LOWER_DEEP_WATER.png",
    }]
    return "\n".join([
        "# EP01 S01/S02 Asset Check Report",
        "",
        "## Result",
        "",
        "- Ready status: S01/S02 H3 R2V project ready",
        f"- Verified and reused assets: {len(reused)}",
        "- Newly generated project backgrounds: 2",
        "- Missing or unresolved assets: 0",
        "",
        "## Verified reusable assets",
        "",
        *[f"- `{name}` — content visually checked; connected as approved reference" for name in reused],
        "",
        "## Newly generated assets",
        "",
        "- `BG_EP01_S02_LUA_BEDROOM_MORNING.png` — C13, C14",
        "- `BG_EP01_S02_BREAKWATER_LOWER_DEEP_WATER.png` — C17, C18, C19",
        "",
        "## Intentionally prompt-directed elements",
        "",
        "- C20–C22 shadow-puppet memories use the supplied character references and prompt-defined paper-theater transformation.",
        "- Underwater turbidity, currents, reflections, sediment, black corruption, and S02 cave eyelines remain prompt-directed effects.",
        "",
    ])


def build() -> dict[str, object]:
    destination = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    if destination.exists():
        raise FileExistsError(f"Existing projects are not overwritten: {PROJECT_ID}")
    for path in (S01_DOCUMENT, S02_DOCUMENT, ASSET_GUIDE, *ASSET_PATHS.values()):
        if not path.is_file():
            raise FileNotFoundError(path)

    rows = prompt_rows()
    used_names = {name for row in rows for name in row["asset_names"]}
    if used_names != set(ASSET_PATHS):
        raise ValueError(f"Asset mapping mismatch: {sorted(set(ASSET_PATHS) ^ used_names)}")

    base = h3_prompt_projects.projects_root(ROOT)
    base.mkdir(parents=True, exist_ok=True)
    staging = base / f".{PROJECT_ID}.building-{secrets.token_hex(4)}"
    staging.mkdir()
    try:
        lineage = [S01_DOCUMENT.name, S02_DOCUMENT.name, ASSET_GUIDE.name]
        manifest = {
            "schema_version": 2,
            "project_kind": h3_prompt_projects.PROJECT_KIND,
            "project_id": PROJECT_ID,
            "title": PROJECT_TITLE,
            "description": "Exact import of the user-supplied EP01 S01 and S02 Full-Reference H3 R2V prompts with verified and generated project-local assets.",
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
            "asset_storage": "project_local_shared",
            "source_policy": "user_prompt_exact_asset_guide_verified",
            "canonical_source_lineage": lineage,
            "locked_rule_id": "EP01_S01_S02_USER_PROMPTS_UNCHANGED_V1",
            "import_script": "scripts/import_ep01_s01_s02_h3_r2v_prompt_package.py",
            "candidate_policy": "A_equals_D_equals_E_exactly",
            "review_status": "pending_user_prompt_review",
            "build_facts": {
                "scene_count": 2,
                "s01_clip_count": 12,
                "s02_clip_count": 14,
                "clip_count": 26,
                "candidate_entry_count": 78,
                "unique_prompt_count": 26,
                "verified_reused_asset_count": 13,
                "generated_background_count": 2,
                "missing_asset_count": 0,
            },
            "queue_authorized": False,
            "video_generation_authorized": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        source_dir = staging / "source"
        source_dir.mkdir()
        for path in (S01_DOCUMENT, S02_DOCUMENT, ASSET_GUIDE):
            shutil.copy2(path, source_dir / f"{path.stem}.source.txt")

        shared_dir = staging / "assets" / "shared"
        shared_dir.mkdir(parents=True)
        for name, path in ASSET_PATHS.items():
            shutil.copy2(path, shared_dir / name)

        mapping: dict[str, list[dict[str, object]]] = {}
        for sequence, row in enumerate(rows, start=1):
            clip_id = str(row["clip_id"])
            prompt = str(row["video_prompt"])
            variants = [{
                "variant_id": candidate,
                "label": f"Candidate {candidate} · user-supplied original",
                "rationale": "Exact duplicate of the user-supplied prompt; no derivation.",
                "video_prompt": prompt,
            } for candidate in ("A", "D", "E")]
            references = []
            for picture_index, asset_name in enumerate(row["asset_names"], start=1):
                role, label = ASSET_ROLES[str(asset_name)]
                references.append({
                    "picture_index": picture_index,
                    "role": role,
                    "label": label,
                    "description": "",
                    "instruction_en": "",
                    "reference_kind": "visual_reference",
                    "required": True,
                    "source_path": f"assets/shared/{asset_name}",
                })
            mapping[clip_id] = references
            payload = {
                "schema_version": 2,
                "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
                "workflow": h3_prompt_projects.WORKFLOW,
                "project_id": PROJECT_ID,
                "scene_id": row["scene_id"],
                "clip_id": clip_id,
                "source_clip_id": clip_id,
                "sequence": sequence,
                "status": "pending_user_prompt_review",
                "duration_seconds": row["duration_seconds"],
                "title": row["title"],
                "video_prompt": prompt,
                "prompt_variants": variants,
                "references": references,
                "canonical_source_lineage": [row["source_document"], ASSET_GUIDE.name],
                "locked_rule_id": "EP01_S01_S02_USER_PROMPTS_UNCHANGED_V1",
                "summary": row["summary"],
                "required_dialogue": row["required_dialogue"],
                "dialogue_lock_version": "USER_SUPPLIED_EP01_H3_DIALOGUE_V1",
                "source_prompt_sha256": row["source_prompt_sha256"],
                "candidate_policy": "A=D=E; exact user-supplied prompt",
                "scene_type": "user_supplied_prompt_import",
                "semantic_review": "not_performed",
            }
            scene_dir = staging / str(row["scene_id"])
            scene_dir.mkdir(exist_ok=True)
            markdown = (
                f"# {clip_id} · {row['title']} · MiniMax H3 R2V\n\n"
                "## Machine Payload\n\n```json\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
            (scene_dir / f"{clip_id}.md").write_text(markdown, encoding="utf-8")

        (staging / "asset_mapping.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (staging / "ASSET_CHECK_REPORT.md").write_text(
            asset_check_report(), encoding="utf-8"
        )
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(S01_DOCUMENT, SOURCE_DIR / S01_DOCUMENT.name)
    shutil.copy2(S02_DOCUMENT, SOURCE_DIR / S02_DOCUMENT.name)
    shutil.copy2(ASSET_GUIDE, SOURCE_DIR / ASSET_GUIDE.name)
    return {
        "project_id": PROJECT_ID,
        "project_path": str(destination),
        "scene_count": 2,
        "clip_count": len(rows),
        "candidate_entry_count": len(rows) * 3,
        "candidate_policy": "A_equals_D_equals_E_exactly",
        "verified_reused_asset_count": 13,
        "generated_background_count": 2,
        "missing_asset_count": 0,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
