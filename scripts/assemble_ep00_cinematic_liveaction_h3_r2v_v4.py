#!/usr/bin/env python3
from __future__ import annotations

"""Assemble the supplied EP00 cinematic live-action V4 R2V package verbatim."""

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


PROJECT_ID = "RaisingaDragonSeason01_EP00_CINEMATIC_LIVEACTION_H3_R2V_V4"
PROJECT_TITLE = "Raising a Dragon EP00 · Cinematic Live-Action R2V V4"
PROJECT_ROOT = ROOT / "projects/RaisingaDragonSeason01"
PRODUCTION = PROJECT_ROOT / "ep00_cinematic_liveaction_production_v3"
SOURCE = PRODUCTION / "EP00_H3_R2V_PROMPT_DOCUMENT_CINEMATIC_LIVEACTION_V1.md"
COMMAND = PRODUCTION / "EP00_CODEX_PROJECT_ASSET_LINK_COMMAND_V4.md"
SHOT_PLAN = PRODUCTION / "EP00_SHOT_BEAT_PLAN_CINEMATIC_LIVEACTION_V1.md"

ASSETS = {
    "H3_LUA_KOREAN_IDOL_PONYTAIL_LONG_LEG_CINEMATIC_LIVEACTION_IDENTITY_V3.png": PROJECT_ROOT / "asset_sheets_cinematic_liveaction_v2_working/01_characters/identity_sheets/H3_LUA_KOREAN_IDOL_PONYTAIL_LONG_LEG_CINEMATIC_LIVEACTION_IDENTITY_V3.png",
    "H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png": PROJECT_ROOT / "asset_sheets_cinematic_liveaction_v1_working/02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png",
    "H3_LUA_SPEAR_PROP_HQ_V3_CINEMATIC_PROP_V1.png": PROJECT_ROOT / "asset_sheets_cinematic_liveaction_v1_working/03_props/H3_LUA_SPEAR_PROP_HQ_V3_CINEMATIC_PROP_V1.png",
    "FX_EP00_FLOATING_CURRENT_SHIELD_CINEMATIC_LIVEACTION_V1.png": PROJECT_ROOT / "asset_sheets_cinematic_liveaction_v2_working/05_effects/reference_sheets/EP00/FX_EP00_FLOATING_CURRENT_SHIELD_CINEMATIC_LIVEACTION_V1.png",
    "BG_EP00_ABYSS_ALTAR_SPATIAL_MASTER_CINEMATIC_LIVEACTION_V1.png": PROJECT_ROOT / "asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_SPATIAL_MASTER_CINEMATIC_LIVEACTION_V1.png",
    "BG_EP00_ABYSS_ALTAR_DAMAGED_AFTER_BLACK_RAIN_CINEMATIC_LIVEACTION_V1.png": PROJECT_ROOT / "asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_DAMAGED_AFTER_BLACK_RAIN_CINEMATIC_LIVEACTION_V1.png",
    "BG_EP00_ABYSS_ALTAR_FINAL_CHASE_DAMAGE_CINEMATIC_LIVEACTION_V1.png": PROJECT_ROOT / "asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_FINAL_CHASE_DAMAGE_CINEMATIC_LIVEACTION_V1.png",
}

ROLES = {
    "H3_LUA_KOREAN_IDOL_PONYTAIL_LONG_LEG_CINEMATIC_LIVEACTION_IDENTITY_V3.png": ("lua_identity_v3", "Lua Korean idol ponytail identity V3"),
    "H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png": ("abyss_king_identity", "Human-scale Abyss King identity"),
    "H3_LUA_SPEAR_PROP_HQ_V3_CINEMATIC_PROP_V1.png": ("lua_spear_prop", "Lua spear prop"),
    "FX_EP00_FLOATING_CURRENT_SHIELD_CINEMATIC_LIVEACTION_V1.png": ("floating_current_shield", "Floating current shield"),
    "BG_EP00_ABYSS_ALTAR_SPATIAL_MASTER_CINEMATIC_LIVEACTION_V1.png": ("abyss_altar_spatial_master", "Abyss Altar spatial master"),
    "BG_EP00_ABYSS_ALTAR_DAMAGED_AFTER_BLACK_RAIN_CINEMATIC_LIVEACTION_V1.png": ("abyss_altar_damaged_after_black_rain", "Abyss Altar damaged after black rain"),
    "BG_EP00_ABYSS_ALTAR_FINAL_CHASE_DAMAGE_CINEMATIC_LIVEACTION_V1.png": ("abyss_altar_final_chase_damage", "Abyss Altar final chase damage"),
}

LUA, KING, SPEAR, SHIELD, MASTER, DAMAGED, FINAL = (
    "H3_LUA_KOREAN_IDOL_PONYTAIL_LONG_LEG_CINEMATIC_LIVEACTION_IDENTITY_V3.png",
    "H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png",
    "H3_LUA_SPEAR_PROP_HQ_V3_CINEMATIC_PROP_V1.png",
    "FX_EP00_FLOATING_CURRENT_SHIELD_CINEMATIC_LIVEACTION_V1.png",
    "BG_EP00_ABYSS_ALTAR_SPATIAL_MASTER_CINEMATIC_LIVEACTION_V1.png",
    "BG_EP00_ABYSS_ALTAR_DAMAGED_AFTER_BLACK_RAIN_CINEMATIC_LIVEACTION_V1.png",
    "BG_EP00_ABYSS_ALTAR_FINAL_CHASE_DAMAGE_CINEMATIC_LIVEACTION_V1.png",
)

EXPECTED_INPUTS = {
    "EP00_C01": [KING, MASTER],
    "EP00_C02": [KING, LUA, MASTER],
    "EP00_C03": [KING, MASTER],
    "EP00_C04": [LUA, MASTER],
    "EP00_C05": [LUA, SHIELD, DAMAGED],
    "EP00_C06": [KING, DAMAGED],
    "EP00_C07": [LUA, KING, SPEAR, DAMAGED],
    "EP00_C08": [KING, LUA, SPEAR, DAMAGED],
    "EP00_C09": [KING, DAMAGED],
    "EP00_C10": [LUA, DAMAGED],
    "EP00_C11": [LUA, DAMAGED],
    "EP00_C12": [LUA, DAMAGED],
    "EP00_C13": [KING, DAMAGED],
    "EP00_C14": [KING, LUA, DAMAGED],
    "EP00_C15": [LUA, DAMAGED],
    "EP00_C16": [KING, DAMAGED],
    "EP00_C17": [LUA, DAMAGED],
    "EP00_C18": [LUA, DAMAGED],
    "EP00_C19": [LUA, FINAL],
    "EP00_C20": [LUA, FINAL],
    "EP00_C21": [LUA, KING, FINAL],
    "EP00_C22": [LUA, KING, FINAL],
}

EXPECTED_DIALOGUE = {
    "EP00_C01": ["혼자서도 여기까지 왔구나."],
    "EP00_C09": ["그저 여기 오지 않았다면 목숨을 잃지 않았을 것을…."],
    "EP00_C10": ["니가 마을을 부셨잖아!!!"],
    "EP00_C12": ["붙잡아!"],
}

CLIP_RE = re.compile(
    r"^## (?P<clip_id>EP00_C\d{2}) — (?P<title>.+?)\s*$"
    r"(?P<body>.*?)(?=^## EP00_C\d{2} — |^## 4\.|\Z)",
    re.MULTILINE | re.DOTALL,
)
DURATION_RE = re.compile(r"\*\*Target duration:\*\*\s*([0-9.]+) seconds")
INPUT_RE = re.compile(r"^- `<Picture (\d+)>` `([^`]+)`\s*$", re.MULTILINE)
PROMPT_RE = re.compile(r"```text\n(.*?)\n```", re.DOTALL)
SUMMARY_RE = re.compile(r"^summary:\s*\n(.*?)(?=^retention_analysis:)", re.MULTILINE | re.DOTALL)
DIALOGUE_RE = re.compile(r"<d>\[Korean\]\s*(.*?)</d>", re.DOTALL)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for match in CLIP_RE.finditer(SOURCE.read_text(encoding="utf-8")):
        body = match.group("body")
        duration_match = DURATION_RE.search(body)
        prompt_match = PROMPT_RE.search(body)
        if not duration_match or not prompt_match:
            raise ValueError(f"Incomplete source clip: {match.group('clip_id')}")
        clip_id = match.group("clip_id")
        input_rows = sorted((int(index), name) for index, name in INPUT_RE.findall(body))
        if [index for index, _ in input_rows] != list(range(1, len(input_rows) + 1)):
            raise ValueError(f"Non-contiguous Picture order: {clip_id}")
        asset_names = [name for _, name in input_rows]
        if asset_names != EXPECTED_INPUTS[clip_id]:
            raise ValueError(f"Picture order mismatch: {clip_id}: {asset_names}")
        duration = float(duration_match.group(1))
        prompt = prompt_match.group(1)
        validation = h3_prompt_contract.validate_prompt(prompt, duration_seconds=duration)
        if not validation.valid or validation.warnings:
            raise ValueError(f"Prompt validation failed: {clip_id}: {validation.as_dict()}")
        dialogue = [line.strip() for line in DIALOGUE_RE.findall(prompt)]
        if dialogue != EXPECTED_DIALOGUE.get(clip_id, []):
            raise ValueError(f"Dialogue mismatch: {clip_id}: {dialogue}")
        summary = SUMMARY_RE.search(prompt)
        rows.append({
            "clip_id": clip_id,
            "title": match.group("title").strip(),
            "duration_seconds": duration,
            "asset_names": asset_names,
            "video_prompt": prompt,
            "summary": summary.group(1).strip() if summary else match.group("title").strip(),
            "required_dialogue": dialogue,
            "prompt_sha256": sha256_text(prompt),
            "validation": validation.as_dict(),
        })
    if [row["clip_id"] for row in rows] != [f"EP00_C{i:02d}" for i in range(1, 23)]:
        raise ValueError("Source clip IDs are not EP00_C01 through EP00_C22")
    if sum(float(row["duration_seconds"]) for row in rows) != 165.0:
        raise ValueError("Total duration is not 165.0 seconds")
    return rows


def build() -> dict[str, object]:
    destination = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    if destination.exists():
        raise FileExistsError(f"Existing project is not overwritten: {PROJECT_ID}")
    for path in (SOURCE, COMMAND, SHOT_PLAN, *ASSETS.values()):
        if not path.is_file() or not path.stat().st_size:
            raise FileNotFoundError(path)
    rows = source_rows()
    if {name for row in rows for name in row["asset_names"]} != set(ASSETS):
        raise ValueError("The connected asset set is not the approved seven-asset set")
    prompt_text = "\n".join(str(row["video_prompt"]) for row in rows)
    forbidden = {
        "keyframe_completion": len(re.findall(r"\[keyframe completion\]", prompt_text, re.I)),
        "start_frame": len(re.findall(r"\bstart frame\b", prompt_text, re.I)),
        "first_frame": len(re.findall(r"\bfirst frame\b", prompt_text, re.I)),
        "last_frame": len(re.findall(r"\blast frame\b", prompt_text, re.I)),
        "i2v_fl2v_l2v": len(re.findall(r"\b(?:I2V|FL2V|L2V)\b", prompt_text)),
    }
    if any(forbidden.values()):
        raise ValueError(f"Forbidden instructions found: {forbidden}")

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
            "description": "Exact assembly of supplied EP00 cinematic live-action V4 Full-Reference H3 R2V prompts with seven approved existing assets.",
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
            "asset_storage": "project_local_shared",
            "source_policy": "exact_supplied_prompt_and_input_order",
            "canonical_source_lineage": [SOURCE.name, COMMAND.name, SHOT_PLAN.name],
            "locked_rule_id": "EP00_CINEMATIC_LIVEACTION_R2V_V4_EXACT_ASSEMBLY",
            "assembly_script": "scripts/assemble_ep00_cinematic_liveaction_h3_r2v_v4.py",
            "candidate_policy": "A=D=E; exact supplied prompt",
            "review_status": "pending_user_prompt_review",
            "build_facts": {
                "scene_count": 1, "clip_count": 22, "candidate_entry_count": 66,
                "unique_prompt_count": 22, "total_duration_seconds": 165.0,
                "project_local_asset_count": 7, "missing_asset_count": 0,
                "excluded_effect_asset_connection_count": 0,
                "keyframe_or_i2v_instruction_count": 0,
            },
            "queue_authorized": False,
            "video_generation_authorized": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
            "candidate_selection_performed": False,
            "upscale_performed": False,
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        source_dir = staging / "source"
        source_dir.mkdir()
        shutil.copy2(SOURCE, source_dir / "EP00_H3_R2V_PROMPT_DOCUMENT_CINEMATIC_LIVEACTION_V1.source.md")

        shared = staging / "assets/shared"
        shared.mkdir(parents=True)
        copied_assets = []
        for name, original in ASSETS.items():
            copy = shared / name
            shutil.copy2(original, copy)
            source_hash, copy_hash = sha256_path(original), sha256_path(copy)
            if source_hash != copy_hash:
                raise ValueError(f"Asset SHA-256 mismatch: {name}")
            copied_assets.append({"name": name, "original_path": str(original), "project_path": f"assets/shared/{name}", "sha256": source_hash, "hash_match": True})

        scene = staging / "EP00-CONTINUOUS"
        scene.mkdir()
        mapping: dict[str, list[dict[str, object]]] = {}
        validations = []
        for sequence, row in enumerate(rows, start=1):
            clip_id, prompt = str(row["clip_id"]), str(row["video_prompt"])
            references = []
            for picture_index, asset_name in enumerate(row["asset_names"], start=1):
                role, label = ROLES[str(asset_name)]
                references.append({
                    "picture_index": picture_index, "role": role, "label": label,
                    "description": "", "instruction_en": "", "reference_kind": "visual_reference",
                    "required": True, "source_path": f"assets/shared/{asset_name}",
                })
            mapping[clip_id] = references
            variants = [{
                "variant_id": candidate, "label": f"Candidate {candidate} · supplied original",
                "rationale": "Exact duplicate of the supplied prompt; no derivation.", "video_prompt": prompt,
            } for candidate in ("A", "D", "E")]
            payload = {
                "schema_version": 2,
                "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
                "workflow": h3_prompt_projects.WORKFLOW,
                "project_id": PROJECT_ID, "scene_id": "EP00-CONTINUOUS",
                "clip_id": clip_id, "source_clip_id": clip_id, "sequence": sequence,
                "status": "pending_user_prompt_review", "duration_seconds": row["duration_seconds"],
                "title": row["title"], "video_prompt": prompt, "prompt_variants": variants,
                "references": references, "canonical_source_lineage": [SOURCE.name],
                "locked_rule_id": "EP00_CINEMATIC_LIVEACTION_R2V_V4_EXACT_ASSEMBLY",
                "summary": row["summary"], "required_dialogue": row["required_dialogue"],
                "dialogue_lock_version": "EP00_CINEMATIC_LIVEACTION_V4",
                "source_prompt_sha256": row["prompt_sha256"],
                "candidate_policy": "A=D=E; exact supplied prompt",
                "scene_type": "user_supplied_prompt_import", "semantic_review": "not_performed",
            }
            clip_path = scene / f"{clip_id}.md"
            clip_path.write_text(f"# {clip_id} · {row['title']} · MiniMax H3 R2V\n\n## Machine Payload\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n", encoding="utf-8")
            loaded = h3_prompt_projects.extract_payload(clip_path.read_text(encoding="utf-8"))
            candidate_hashes = {str(v["variant_id"]): sha256_text(str(v["video_prompt"])) for v in loaded["prompt_variants"]}
            if str(loaded["video_prompt"]) != prompt or any(value != row["prompt_sha256"] for value in candidate_hashes.values()):
                raise ValueError(f"Serialized prompt mismatch: {clip_id}")
            validations.append({
                "clip_id": clip_id, "duration_seconds": row["duration_seconds"],
                "picture_names": list(row["asset_names"]),
                "source_prompt_sha256": row["prompt_sha256"],
                "serialized_prompt_sha256": sha256_text(str(loaded["video_prompt"])),
                "candidate_prompt_sha256": candidate_hashes,
                "contract_validation": row["validation"], "errors": [], "warnings": [],
            })

        (staging / "asset_mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (staging / "ASSET_CHECK_REPORT.md").write_text("\n".join([
            "# EP00 Cinematic Live-Action R2V V4 Asset Check Report", "",
            "- Connected project-local assets: 7", "- Missing assets: 0",
            "- Source/copy SHA-256 mismatches: 0", "- Excluded effect assets connected: 0",
            "- Newly generated image assets: 0", "",
            *[f"- `{item['name']}` — `{item['sha256']}`" for item in copied_assets], "",
        ]), encoding="utf-8")
        report = {
            "schema_version": 3, "project_id": PROJECT_ID, "valid": True,
            "source_document": SOURCE.name, "source_document_sha256": sha256_path(SOURCE),
            "clip_count": 22, "candidate_entry_count": 66, "unique_prompt_count": 22,
            "total_duration_seconds": 165.0, "prompt_validation_error_count": 0,
            "prompt_validation_warning_count": 0,
            "reference_generation_summary_count": sum(str(row["video_prompt"]).count("[reference generation]") for row in rows),
            "keyframe_or_i2v_instruction_counts": forbidden,
            "dialogue_tag_count": sum(len(row["required_dialogue"]) for row in rows),
            "c15_nonverbal_resonance_is_dialogue": False,
            "asset_copy_count": 7, "asset_sha256_match_count": 7,
            "excluded_effect_asset_connection_count": 0, "new_image_generation_count": 0,
            "queue_registration_performed": False, "video_generation_performed": False,
            "candidate_selection_performed": False, "upscale_performed": False,
            "clips": validations,
        }
        (staging / "PROMPT_VALIDATION_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "project_id": PROJECT_ID, "project_path": str(destination), "clip_count": 22,
        "total_duration_seconds": 165.0, "asset_count": 7, "missing_asset_count": 0,
        "asset_sha256_mismatch_count": 0, "prompt_validation_error_count": 0,
        "prompt_validation_warning_count": 0, "new_image_generation_count": 0,
        "queue_registration_performed": False, "video_generation_performed": False,
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
