from __future__ import annotations

"""Import the user-authored EP00 V4 H3 prompts without rewriting them."""

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
    "/home/nalstudio/.codex/attachments/fc768089-9ded-4048-8b38-fa190eae4f7e/"
    "EP00_H3_R2V_Prompt_Document_V4_OFFICIAL_GUIDE.md"
)
PROJECT_ID = "RaisingaDragonSeason01_EP00_USER_H3_R2V_PACKAGE_V4"
PROJECT_TITLE = "Raising a Dragon EP00 · User H3 R2V Package V4"
SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_user_prompt_package_v4"
LIBRARY = ROOT / "projects" / "RaisingaDragonSeason01" / "asset_sheets_master_v1"

ASSET_PATHS = {
    "H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2.png":
        LIBRARY / "01_characters/H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2.png",
    "H3_ABYSS_KING_IDENTITY_HQ_V2.png":
        LIBRARY / "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2.png",
    "H3_LUA_SPEAR_PROP_HQ_V3.png":
        LIBRARY / "03_props/H3_LUA_SPEAR_PROP_HQ_V3.png",
    "Current_Shield_IRREGULAR_CURVED_REFERENCE_SHEET_V4.png":
        LIBRARY / "05_effects/EP00/Current_Shield_IRREGULAR_CURVED_REFERENCE_SHEET_V4.png",
    "Moving_Current_Ribbon_REFERENCE_SHEET_V3.png":
        LIBRARY / "05_effects/EP00/Moving_Current_Ribbon_REFERENCE_SHEET_V3.png",
    "BG_EP00_S01_ABYSS_ALTAR_MASTER.png":
        LIBRARY / "04_backgrounds/EP00_ABYSS_ALTAR_V2_BLACK_RAIN/BG_EP00_S01_ABYSS_ALTAR_MASTER.png",
    "BG_EP00_S01_ABYSS_ALTAR_DAMAGED.png":
        LIBRARY / "04_backgrounds/EP00_ABYSS_ALTAR_V2_BLACK_RAIN/BG_EP00_S01_ABYSS_ALTAR_DAMAGED.png",
    "BG_EP00_S01_ABYSS_ALTAR_FINAL_DAMAGE.png":
        LIBRARY / "04_backgrounds/EP00_ABYSS_ALTAR_V2_BLACK_RAIN/BG_EP00_S01_ABYSS_ALTAR_FINAL_DAMAGE.png",
}

ASSET_ROLES = {
    "H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2.png": ("lua_identity", "Lua Complete Scales identity sheet"),
    "H3_ABYSS_KING_IDENTITY_HQ_V2.png": ("abyss_king_identity", "Abyss King identity sheet"),
    "H3_LUA_SPEAR_PROP_HQ_V3.png": ("lua_spear_prop", "Lua spear prop sheet"),
    "Current_Shield_IRREGULAR_CURVED_REFERENCE_SHEET_V4.png": ("irregular_curved_shield", "Irregular curved current shield reference"),
    "Moving_Current_Ribbon_REFERENCE_SHEET_V3.png": ("moving_current_ribbon", "Moving current ribbon reference"),
    "BG_EP00_S01_ABYSS_ALTAR_MASTER.png": ("abyss_altar_master", "EP00 Abyss Altar MASTER background"),
    "BG_EP00_S01_ABYSS_ALTAR_DAMAGED.png": ("abyss_altar_damaged", "EP00 Abyss Altar DAMAGED background"),
    "BG_EP00_S01_ABYSS_ALTAR_FINAL_DAMAGE.png": ("abyss_altar_final_damage", "EP00 Abyss Altar FINAL_DAMAGE background"),
}

CLIP_RE = re.compile(
    r"^## (?P<clip_id>EP00_C\d{2}) — (?P<title>.+?)\s*$"
    r"(?P<body>.*?)(?=^## EP00_C\d{2} — |^# 6\.|\Z)",
    re.MULTILINE | re.DOTALL,
)
DURATION_RE = re.compile(r"\*\*Target duration:\*\*\s*([0-9.]+) seconds")
INPUT_RE = re.compile(r"^- `<Picture (\d+)>` `([^`]+)`\s*$", re.MULTILINE)
PROMPT_RE = re.compile(r"```text\s*\n(.*?)\n```", re.DOTALL)
SUMMARY_RE = re.compile(r"^summary:\s*\n(.*?)(?=^retention_analysis:)", re.MULTILINE | re.DOTALL)
DIALOGUE_RE = re.compile(r"<d>\[Korean\]\s*(.*?)</d>", re.DOTALL)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prompt_rows() -> list[dict[str, object]]:
    text = PROMPT_DOCUMENT.read_text(encoding="utf-8")
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
            "duration_seconds": float(duration.group(1)),
            "asset_names": [name for _, name in inputs],
            "video_prompt": prompt_text,
            "summary": summary.group(1).strip() if summary else match.group("title").strip(),
            "required_dialogue": [line.strip() for line in DIALOGUE_RE.findall(prompt_text)],
            "source_prompt_sha256": digest(prompt_text),
        })
    expected = [f"EP00_C{index:02d}" for index in range(1, 26)]
    if [str(row["clip_id"]) for row in rows] != expected:
        raise ValueError("The V4 prompt document did not yield EP00_C01 through EP00_C25")
    return rows


def asset_check_report() -> str:
    return "\n".join([
        "# EP00 V4 Asset Check Report",
        "",
        "## Result",
        "",
        "- Ready status: EP00 V4 H3 R2V project ready",
        "- Verified and reused project assets: 8",
        "- Newly generated assets: 0",
        "- Missing or unresolved assets: 0",
        "- Picture order source: the user-supplied V4 document for each clip",
        "",
        "## Connected assets",
        "",
        *[f"- `{name}` — connected as an approved project-local reference" for name in ASSET_PATHS],
        "",
        "## Import policy",
        "",
        "- Every prompt body is imported verbatim from the supplied document.",
        "- Candidates A, D, and E contain the same supplied prompt; no local derivation was performed.",
        "- No queue registration or video generation was performed.",
        "",
    ])


def build() -> dict[str, object]:
    destination = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    if destination.exists():
        raise FileExistsError(f"Existing projects are not overwritten: {PROJECT_ID}")
    for path in (PROMPT_DOCUMENT, *ASSET_PATHS.values()):
        if not path.is_file():
            raise FileNotFoundError(path)

    rows = prompt_rows()
    used_names = {str(name) for row in rows for name in row["asset_names"]}
    if used_names != set(ASSET_PATHS):
        raise ValueError(f"Asset mapping mismatch: {sorted(set(ASSET_PATHS) ^ used_names)}")

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
            "description": "Exact import of the user-supplied EP00 V4 Full-Reference H3 R2V prompts with approved project-local assets.",
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
            "asset_storage": "project_local_shared",
            "source_policy": "user_prompt_exact_document_picture_order",
            "canonical_source_lineage": [PROMPT_DOCUMENT.name],
            "locked_rule_id": "EP00_USER_H3_PROMPT_PACKAGE_UNCHANGED_V4",
            "import_script": "scripts/import_ep00_h3_r2v_prompt_package_v4.py",
            "candidate_policy": "A_equals_D_equals_E_exactly",
            "review_status": "pending_user_prompt_review",
            "build_facts": {
                "scene_count": 1,
                "clip_count": 25,
                "candidate_entry_count": 75,
                "unique_prompt_count": 25,
                "verified_reused_asset_count": 8,
                "generated_asset_count": 0,
                "missing_asset_count": 0,
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

        shared_dir = staging / "assets" / "shared"
        shared_dir.mkdir(parents=True)
        for name, path in ASSET_PATHS.items():
            shutil.copy2(path, shared_dir / name)

        scene_dir = staging / "EP00-CONTINUOUS"
        scene_dir.mkdir()
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
                "scene_id": "EP00-CONTINUOUS",
                "clip_id": clip_id,
                "source_clip_id": clip_id,
                "sequence": sequence,
                "status": "pending_user_prompt_review",
                "duration_seconds": row["duration_seconds"],
                "title": row["title"],
                "video_prompt": prompt,
                "prompt_variants": variants,
                "references": references,
                "canonical_source_lineage": [PROMPT_DOCUMENT.name],
                "locked_rule_id": "EP00_USER_H3_PROMPT_PACKAGE_UNCHANGED_V4",
                "summary": row["summary"],
                "required_dialogue": row["required_dialogue"],
                "dialogue_lock_version": "USER_SUPPLIED_EP00_H3_DIALOGUE_V4",
                "source_prompt_sha256": row["source_prompt_sha256"],
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

        (staging / "asset_mapping.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "ASSET_CHECK_REPORT.md").write_text(asset_check_report(), encoding="utf-8")
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROMPT_DOCUMENT, SOURCE_DIR / PROMPT_DOCUMENT.name)
    return {
        "project_id": PROJECT_ID,
        "project_path": str(destination),
        "scene_count": 1,
        "clip_count": len(rows),
        "candidate_entry_count": len(rows) * 3,
        "candidate_policy": "A_equals_D_equals_E_exactly",
        "verified_reused_asset_count": 8,
        "generated_asset_count": 0,
        "missing_asset_count": 0,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
