#!/usr/bin/env python3
from __future__ import annotations

"""Assemble the supplied EP01 cinematic live-action V1 R2V package verbatim."""

import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402

PROJECT_ID = "RaisingaDragonSeason01_EP01_CINEMATIC_LIVEACTION_H3_R2V_V1"
PROJECT_TITLE = "Raising a Dragon EP01 · Cinematic Live-Action R2V V1"
PROJECT_ROOT = ROOT / "projects/RaisingaDragonSeason01"
PRODUCTION = PROJECT_ROOT / "ep01_cinematic_liveaction_production_v1"
SOURCE = PRODUCTION / "EP01_H3_R2V_PROMPT_DOCUMENT_CINEMATIC_LIVEACTION_V1.md"
COMMAND = PRODUCTION / "EP01_CODEX_PROJECT_ASSET_LINK_COMMAND_CINEMATIC_LIVEACTION_V1.md"
SPATIAL_RULES = PROJECT_ROOT / "BACKGROUND_SPATIAL_LANDMARK_COMPOSITION_RULES_V1.md"

LUA = "H3_LUA_KOREAN_IDOL_PONYTAIL_LONG_LEG_CINEMATIC_LIVEACTION_IDENTITY_V3.png"
MIR = "H3_YOUNG_MIR_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png"
FISHERMAN = "H3_OLD_FISHERMAN_IDENTITY_HQ_V1_CINEMATIC_LIVEACTION_V1.png"
VILLAGER = "H3_SKEPTICAL_VILLAGER_IDENTITY_HQ_V1_CINEMATIC_LIVEACTION_V1.png"
SPEAR = "H3_LUA_SPEAR_PROP_HQ_V3_CINEMATIC_PROP_V1.png"
SLEEPWEAR = "WARDROBE_EP01_LUA_SLEEPWEAR_CINEMATIC_LIVEACTION_V1.png"
MIRROR = "PROP_EP01_LUA_HAND_MIRROR_CINEMATIC_LIVEACTION_V1.png"
STORM = "BG_EP01_STORM_OPEN_SEA_SURFACE_MASTER_CINEMATIC_LIVEACTION_V1.png"
ABYSS = "BG_EP01_OPEN_ABYSS_VERTICAL_CURRENT_SPACE_MASTER_CINEMATIC_LIVEACTION_V2.png"
RUINED = "BG_EP01_RUINED_BLUE_DRAGON_PALACE_MASTER_CINEMATIC_LIVEACTION_V1.png"
INTACT = "BG_EP01_MEMORY_INTACT_BLUE_DRAGON_PALACE_MASTER_CINEMATIC_LIVEACTION_V1.png"
HEARTSTONE = "BG_EP01_MEMORY_HEARTSTONE_SANCTUM_MASTER_CINEMATIC_LIVEACTION_V2.png"
ASSEMBLY = "BG_EP01_MEMORY_DRAGON_ASSEMBLY_COURT_MASTER_CINEMATIC_LIVEACTION_V2.png"
BEDROOM = "BG_EP01_LUA_SEASIDE_BEDROOM_MASTER_CINEMATIC_LIVEACTION_V1.png"
VILLAGE = "BG_EP01_POST_STORM_COASTAL_VILLAGE_MASTER_CINEMATIC_LIVEACTION_V1.png"
BREAKWATER = "BG_EP01_BREAKWATER_REPAIR_AND_DEEP_WATER_MASTER_CINEMATIC_LIVEACTION_V2.png"
SHADOW_STAGE = "SHADOW_EP01_KOREAN_COASTAL_PUPPET_STAGE_STYLE_MASTER_V1.png"
SHADOW_CHARACTER = "SHADOW_EP01_CHARACTER_SILHOUETTE_IDENTITY_SHEET_V2.png"
SHADOW_MARITIME = "SHADOW_EP01_MARITIME_ENVIRONMENT_PROP_SILHOUETTE_SHEET_V1.png"

ASSETS = {
    LUA: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/01_characters/identity_sheets/{LUA}",
    MIR: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v1_working/01_characters/mir/{MIR}",
    FISHERMAN: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v1_working/01_characters/identity_sheets/{FISHERMAN}",
    VILLAGER: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v1_working/01_characters/identity_sheets/{VILLAGER}",
    SPEAR: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v1_working/03_props/{SPEAR}",
    SLEEPWEAR: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/03_wardrobe/scenario_extensions/EP01/{SLEEPWEAR}",
    MIRROR: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/03_props/scenario_extensions/EP01/{MIRROR}",
    STORM: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP01/S01_STORM_OCEAN/{STORM}",
    ABYSS: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP01/S01_OPEN_ABYSS/{ABYSS}",
    RUINED: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP01/S01_RUINED_DRAGON_PALACE/{RUINED}",
    INTACT: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP01/S01_MEMORY_INTACT_PALACE/{INTACT}",
    HEARTSTONE: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP01/S01_MEMORY_HEARTSTONE_SANCTUM/{HEARTSTONE}",
    ASSEMBLY: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP01/S01_MEMORY_DRAGON_ASSEMBLY/{ASSEMBLY}",
    BEDROOM: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP01/S02_LUA_BEDROOM/{BEDROOM}",
    VILLAGE: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP01/S02_STORM_DAMAGED_VILLAGE/{VILLAGE}",
    BREAKWATER: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/04_backgrounds/scenario_extensions/EP01/S02_BREAKWATER_FISHING_POINT/{BREAKWATER}",
    SHADOW_STAGE: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/06_stylized_sequences/EP01/SHADOW_PLAY/{SHADOW_STAGE}",
    SHADOW_CHARACTER: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/06_stylized_sequences/EP01/SHADOW_PLAY/{SHADOW_CHARACTER}",
    SHADOW_MARITIME: PROJECT_ROOT / f"asset_sheets_cinematic_liveaction_v2_working/06_stylized_sequences/EP01/SHADOW_PLAY/{SHADOW_MARITIME}",
}

ROLES = {
    LUA: ("lua_identity_v3", "Lua cinematic live-action identity V3"),
    MIR: ("young_mir_identity", "Young Mir cinematic creature identity"),
    FISHERMAN: ("old_fisherman_identity", "Old fisherman identity"),
    VILLAGER: ("skeptical_villager_identity", "Skeptical villager identity"),
    SPEAR: ("lua_spear_prop", "Lua spear prop"),
    SLEEPWEAR: ("lua_sleepwear_wardrobe", "Lua sleepwear wardrobe"),
    MIRROR: ("lua_hand_mirror_prop", "Lua hand mirror prop"),
    STORM: ("ep01_storm_open_sea_master", "EP01 storm open sea master"),
    ABYSS: ("ep01_open_abyss_master_v2", "EP01 open abyss master V2"),
    RUINED: ("ep01_ruined_blue_dragon_palace_master", "EP01 ruined blue dragon palace master"),
    INTACT: ("ep01_memory_intact_blue_dragon_palace_master", "EP01 intact palace memory master"),
    HEARTSTONE: ("ep01_memory_heartstone_sanctum_master_v2", "EP01 heartstone sanctum master V2"),
    ASSEMBLY: ("ep01_memory_dragon_assembly_court_master_v2", "EP01 dragon assembly court master V2"),
    BEDROOM: ("ep01_lua_seaside_bedroom_master", "EP01 Lua seaside bedroom master"),
    VILLAGE: ("ep01_post_storm_coastal_village_master", "EP01 post-storm village master"),
    BREAKWATER: ("ep01_breakwater_repair_and_deep_water_master_v2", "EP01 breakwater master V2"),
    SHADOW_STAGE: ("ep01_shadow_stage_style_master", "EP01 practical shadow-play stage style"),
    SHADOW_CHARACTER: ("ep01_shadow_character_silhouette_identity_v2", "EP01 shadow character silhouettes V2"),
    SHADOW_MARITIME: ("ep01_shadow_maritime_environment_prop", "EP01 shadow maritime environment and props"),
}

NEW_ASSET_PROMPTS = {
    SLEEPWEAR: "Create a production-quality cinematic live-action wardrobe reference for Lua's coastal bedroom scenes. Show one coherent modest Korean maritime-fantasy sleepwear set: a soft off-white linen wrap-front sleeping tunic with subtle desaturated blue-gray edge binding, paired loose ankle-length trousers, practical handcrafted seams, slightly worn but clean natural fabric, no embroidery, no insignia, no armor and no modern elastic sportswear. Present the complete outfit clearly on a neutral headless tailor form in a simple three-quarter product view against a quiet medium-gray studio background. Premium physically photographed textile detail, realistic folds, weave and stitching, restrained coastal palette, no person, no head, no face, no hands, no jewelry, no footwear, no bed, no room, no text, no logo, no labels, no collage, no fantasy glow.",
    MIRROR: "Create a production-quality cinematic live-action prop reference of one palm-sized oval hand mirror for a modest Korean coastal maritime-fantasy village. The mirror has a short dark weathered wood handle, a narrow hand-forged bronze rim, subtly irregular handmade construction and clear realistic glass. Show the single complete object in a clean three-quarter product view against a quiet medium-gray studio background, with enough side angle to read the handle-to-frame connection and thickness. The glass reflects only a neutral soft gray studio gradient. Premium physically photographed wood grain, aged bronze and glass detail, practical believable scale, no person, no hand, no face or eye reflected in the glass, no duplicate mirror, no ornate royal decoration, no magic glow, no text, no logo, no labels, no collage.",
}

SCENES = [
    ("EP01-S01-ABYSS-RUINS", 1, 20, 145.0),
    ("EP01-S02-VILLAGE-BREAKWATER", 21, 43, 197.0),
    ("EP01-S03-SHADOW-MEMORY", 44, 51, 97.5),
    ("EP01-S04-CAVE-CONVERSATION", 52, 59, 79.5),
]
SECTIONS = ["subject_definitions", "summary", "retention_analysis", "detailed_description", "overall_soundscape", "non_diegetic_music"]
CLIP_RE = re.compile(r"^## (?P<clip_id>EP01_C\d{2}) — (?P<title>.+?)\s*$" r"(?P<body>.*?)(?=^## EP01_C\d{2} — |^# Scene |\Z)", re.M | re.S)
DURATION_RE = re.compile(r"\*\*Target duration:\*\*\s*([0-9.]+) seconds")
INPUT_RE = re.compile(r"^- `<Picture (\d+)>` `([^`]+)`\s*$", re.M)
PROMPT_RE = re.compile(r"```text\n(.*?)\n```", re.S)
SUMMARY_RE = re.compile(r"^summary:\s*\n(.*?)(?=^retention_analysis:)", re.M | re.S)
DIALOGUE_RE = re.compile(r"<d>\[Korean\]\s*(.*?)</d>", re.S)


def sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"Unreadable PNG: {path}")
    return struct.unpack(">II", header[16:24])


def scene_for(number: int) -> tuple[str, int]:
    for scene_id, start, end, _duration in SCENES:
        if start <= number <= end:
            return scene_id, number - start + 1
    raise ValueError(f"Clip outside scene ranges: {number}")


def parse_rows() -> list[dict[str, object]]:
    source_text = SOURCE.read_text(encoding="utf-8")
    rows = []
    for match in CLIP_RE.finditer(source_text):
        body = match.group("body")
        duration_match, prompt_match = DURATION_RE.search(body), PROMPT_RE.search(body)
        if not duration_match or not prompt_match:
            raise ValueError(f"Incomplete clip: {match.group('clip_id')}")
        clip_id = match.group("clip_id")
        number = int(clip_id[-2:])
        indexed = sorted((int(index), name) for index, name in INPUT_RE.findall(body))
        if [index for index, _name in indexed] != list(range(1, len(indexed) + 1)):
            raise ValueError(f"Non-contiguous Picture order: {clip_id}")
        names = [name for _index, name in indexed]
        if not names or len(names) > 4 or any(name not in ASSETS for name in names):
            raise ValueError(f"Unapproved Picture input: {clip_id}: {names}")
        duration, prompt = float(duration_match.group(1)), prompt_match.group(1)
        validation = h3_prompt_contract.validate_prompt(prompt, duration_seconds=duration)
        if list(validation.section_names) != SECTIONS:
            raise ValueError(f"Six-section order mismatch: {clip_id}: {validation.section_names}")
        if prompt.lower().count("[reference generation]") != 1:
            raise ValueError(f"Reference-generation marker mismatch: {clip_id}")
        if re.search(r"\[keyframe completion\]", prompt, re.I):
            raise ValueError(f"Keyframe marker found: {clip_id}")
        summary_match = SUMMARY_RE.search(prompt)
        scene_id, scene_sequence = scene_for(number)
        rows.append({
            "clip_id": clip_id,
            "title": match.group("title").strip(),
            "sequence": number,
            "scene_id": scene_id,
            "scene_sequence": scene_sequence,
            "duration_seconds": duration,
            "asset_names": names,
            "video_prompt": prompt,
            "summary": summary_match.group(1).strip() if summary_match else "",
            "required_dialogue": [value.strip() for value in DIALOGUE_RE.findall(prompt)],
            "prompt_sha256": sha_text(prompt),
            "strict_contract_validation": validation.as_dict(),
        })
    expected_ids = [f"EP01_C{index:02d}" for index in range(1, 60)]
    if [row["clip_id"] for row in rows] != expected_ids:
        raise ValueError("Clip IDs are not EP01_C01 through EP01_C59")
    if source_text.count("```text\n") != 59:
        raise ValueError("Source text-code-block count is not 59")
    if abs(sum(float(row["duration_seconds"]) for row in rows) - 519.0) > 0.0001:
        raise ValueError("Duration total is not 519.0")
    prompt_text = "\n".join(str(row["video_prompt"]) for row in rows)
    if prompt_text.count("<d>") != 46 or prompt_text.count("</d>") != 46:
        raise ValueError("Dialogue tag count is not 46 open and 46 close")
    if len(DIALOGUE_RE.findall(prompt_text)) != 46:
        raise ValueError("Not every dialogue tag retains [Korean]")
    for scene_id, start, end, expected_duration in SCENES:
        scene_rows = [row for row in rows if row["scene_id"] == scene_id]
        if len(scene_rows) != end - start + 1:
            raise ValueError(f"Scene clip-count mismatch: {scene_id}")
        if abs(sum(float(row["duration_seconds"]) for row in scene_rows) - expected_duration) > 0.0001:
            raise ValueError(f"Scene duration mismatch: {scene_id}")
    return rows


def build() -> dict[str, object]:
    destination = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    if destination.exists():
        raise FileExistsError(f"Existing project is not overwritten: {PROJECT_ID}")
    for path in (SOURCE, COMMAND, SPATIAL_RULES, *ASSETS.values()):
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(path)
    asset_dimensions = {name: png_dimensions(path) for name, path in ASSETS.items()}
    rows = parse_rows()
    used_assets = {name for row in rows for name in row["asset_names"]}
    if used_assets != set(ASSETS):
        raise ValueError(f"Approved asset set mismatch: missing={set(ASSETS) - used_assets}")
    if any(SLEEPWEAR in row["asset_names"] for row in rows if row["clip_id"] not in {"EP01_C21", "EP01_C22", "EP01_C23"}):
        raise ValueError("Sleepwear connected outside C21-C23")
    if [row["clip_id"] for row in rows if MIRROR in row["asset_names"]] != ["EP01_C23"]:
        raise ValueError("Hand mirror must be connected only to C23")
    shadow_names = {SHADOW_STAGE, SHADOW_CHARACTER, SHADOW_MARITIME}
    if any(shadow_names & set(row["asset_names"]) for row in rows if not 43 <= int(str(row["clip_id"])[-2:]) <= 51):
        raise ValueError("Shadow-play asset connected outside C43-C51")
    if any("CAVE" in name.upper() for row in rows if int(str(row["clip_id"])[-2:]) >= 52 for name in row["asset_names"]):
        raise ValueError("Cave Picture connected to Scene 04")

    prompt_text = "\n".join(str(row["video_prompt"]) for row in rows)
    forbidden_inputs = {
        "keyframe_completion": len(re.findall(r"\[keyframe completion\]", prompt_text, re.I)),
        "start_frame": len(re.findall(r"\bstart frame\b", prompt_text, re.I)),
        "first_frame": len(re.findall(r"\bfirst frame\b", prompt_text, re.I)),
        "last_frame": len(re.findall(r"\blast frame\b", prompt_text, re.I)),
        "i2v_fl2v_l2v": len(re.findall(r"\b(?:I2V|FL2V|L2V)\b", prompt_text)),
    }
    if any(forbidden_inputs.values()):
        raise ValueError(f"Forbidden timeline input found: {forbidden_inputs}")

    base = h3_prompt_projects.projects_root(ROOT)
    base.mkdir(parents=True, exist_ok=True)
    staging = base / f".{PROJECT_ID}.building-{secrets.token_hex(4)}"
    staging.mkdir()
    try:
        strict_errors = sum(len(row["strict_contract_validation"]["errors"]) for row in rows)
        manifest = {
            "schema_version": 2,
            "project_kind": h3_prompt_projects.PROJECT_KIND,
            "project_id": PROJECT_ID,
            "title": PROJECT_TITLE,
            "description": "Exact EP01 cinematic live-action V1 passthrough assembly with four independent R2V scenes.",
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
            "asset_storage": "project_local_shared",
            "source_policy": "exact_supplied_prompt_and_input_order",
            "canonical_source_lineage": [SOURCE.name, COMMAND.name, SPATIAL_RULES.name],
            "locked_rule_id": "EP01_CINEMATIC_LIVEACTION_R2V_V1_EXACT_ASSEMBLY",
            "assembly_script": "scripts/assemble_ep01_cinematic_liveaction_h3_r2v_v1.py",
            "candidate_policy": "A=D=E; exact supplied prompt",
            "review_status": "pending_user_prompt_review",
            "build_facts": {
                "scene_count": 4,
                "clip_count": 59,
                "candidate_entry_count": 177,
                "unique_prompt_count": 59,
                "total_duration_seconds": 519.0,
                "project_local_asset_count": 19,
                "existing_approved_asset_count": 17,
                "newly_generated_approved_asset_count": 2,
                "missing_asset_count": 0,
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
        shutil.copy2(SOURCE, source_dir / "EP01_H3_R2V_PROMPT_DOCUMENT_CINEMATIC_LIVEACTION_V1.source.md")
        shared = staging / "assets/shared"
        shared.mkdir(parents=True)
        copied_assets = []
        for name, original in ASSETS.items():
            copy = shared / name
            shutil.copy2(original, copy)
            original_hash, copy_hash = sha_path(original), sha_path(copy)
            if original_hash != copy_hash:
                raise ValueError(f"Asset hash mismatch: {name}")
            width, height = asset_dimensions[name]
            copied_assets.append({
                "name": name,
                "original_path": str(original),
                "project_path": f"assets/shared/{name}",
                "bytes": original.stat().st_size,
                "width": width,
                "height": height,
                "sha256": original_hash,
                "hash_match": True,
                "asset_origin": "newly_generated_approved" if name in NEW_ASSET_PROMPTS else "existing_approved",
            })

        mapping, validations = {}, []
        for row in rows:
            clip_id, prompt = str(row["clip_id"]), str(row["video_prompt"])
            scene_dir = staging / str(row["scene_id"])
            scene_dir.mkdir(exist_ok=True)
            references = []
            for picture_index, asset_name in enumerate(row["asset_names"], start=1):
                role, label = ROLES[str(asset_name)]
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
            variants = [{
                "variant_id": candidate,
                "label": f"Candidate {candidate} · supplied original",
                "rationale": "Exact duplicate of the supplied prompt; no derivation.",
                "video_prompt": prompt,
            } for candidate in ("A", "D", "E")]
            payload = {
                "schema_version": 2,
                "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
                "workflow": h3_prompt_projects.WORKFLOW,
                "project_id": PROJECT_ID,
                "scene_id": row["scene_id"],
                "clip_id": clip_id,
                "source_clip_id": clip_id,
                "sequence": row["sequence"],
                "scene_sequence": row["scene_sequence"],
                "status": "pending_user_prompt_review",
                "duration_seconds": row["duration_seconds"],
                "title": row["title"],
                "video_prompt": prompt,
                "prompt_variants": variants,
                "references": references,
                "canonical_source_lineage": [SOURCE.name],
                "locked_rule_id": "EP01_CINEMATIC_LIVEACTION_R2V_V1_EXACT_ASSEMBLY",
                "summary": row["summary"],
                "required_dialogue": row["required_dialogue"],
                "dialogue_lock_version": "EP01_CINEMATIC_LIVEACTION_V1",
                "source_prompt_sha256": row["prompt_sha256"],
                "candidate_policy": "A=D=E; exact supplied prompt",
                "scene_type": "user_supplied_prompt_import",
                "semantic_review": "not_performed",
            }
            clip_path = scene_dir / f"{clip_id}.md"
            clip_path.write_text(
                f"# {clip_id} · {row['title']} · MiniMax H3 R2V\n\n## Machine Payload\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n",
                encoding="utf-8",
            )
            loaded = h3_prompt_projects.extract_payload(clip_path.read_text(encoding="utf-8"))
            candidate_hashes = {item["variant_id"]: sha_text(item["video_prompt"]) for item in loaded["prompt_variants"]}
            if loaded["video_prompt"] != prompt or any(value != row["prompt_sha256"] for value in candidate_hashes.values()):
                raise ValueError(f"Serialized prompt mismatch: {clip_id}")
            validations.append({
                "clip_id": clip_id,
                "scene_id": row["scene_id"],
                "duration_seconds": row["duration_seconds"],
                "picture_names": list(row["asset_names"]),
                "source_prompt_sha256": row["prompt_sha256"],
                "serialized_prompt_sha256": sha_text(loaded["video_prompt"]),
                "candidate_prompt_sha256": candidate_hashes,
                "six_section_order_valid": True,
                "passthrough_valid": True,
                "local_strict_contract_validation": row["strict_contract_validation"],
            })

        (staging / "asset_mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report_lines = [
            "# EP01 Cinematic Live-Action R2V V1 Asset Check Report",
            "",
            "- Connected project-local assets: 19",
            "- Existing approved assets copied: 17",
            "- Newly generated and visually approved assets: 2",
            "- Missing assets: 0",
            "- Source/copy SHA-256 mismatches: 0",
            "- Forbidden assets connected: 0",
            "",
            "## Newly generated production assets",
            "",
        ]
        for name in (SLEEPWEAR, MIRROR):
            item = next(asset for asset in copied_assets if asset["name"] == name)
            visual = (
                "PASS — coherent upper/lower sleepwear set on a headless tailor form; practical linen construction; no prohibited identity, text or logo"
                if name == SLEEPWEAR else
                "PASS — one coherent oval mirror with readable wood handle, bronze connection and neutral glass reflection; no prohibited person, text or duplicate"
            )
            report_lines.extend([
                f"### `{name}`",
                "",
                f"- Generation prompt: {NEW_ASSET_PROMPTS[name]}",
                f"- Approved source: `{item['original_path']}`",
                f"- Resolution: {item['width']} × {item['height']}",
                f"- SHA-256: `{item['sha256']}`",
                f"- Visual review: {visual}",
                "",
            ])
        report_lines.extend(["## All connected assets", ""])
        report_lines.extend(
            f"- `{item['name']}` — {item['width']}×{item['height']} — `{item['sha256']}` — source/copy match"
            for item in copied_assets
        )
        report_lines.append("")
        (staging / "ASSET_CHECK_REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")

        report = {
            "schema_version": 3,
            "project_id": PROJECT_ID,
            "valid": True,
            "validation_mode": "exact_user_supplied_passthrough",
            "source_document": SOURCE.name,
            "source_document_sha256": sha_path(SOURCE),
            "scene_counts": {scene_id: end - start + 1 for scene_id, start, end, _duration in SCENES},
            "scene_durations": {scene_id: duration for scene_id, _start, _end, duration in SCENES},
            "clip_count": 59,
            "candidate_entry_count": 177,
            "unique_prompt_count": 59,
            "total_duration_seconds": 519.0,
            "source_text_code_block_count": 59,
            "six_section_order_error_count": 0,
            "local_strict_contract_error_count": strict_errors,
            "local_strict_contract_errors_are_advisory_for_passthrough": True,
            "reference_generation_marker_count": 59,
            "dialogue_open_tag_count": 46,
            "dialogue_close_tag_count": 46,
            "korean_dialogue_count": 46,
            "keyframe_or_i2v_instruction_counts": forbidden_inputs,
            "asset_copy_count": 19,
            "asset_sha256_match_count": 19,
            "existing_approved_asset_count": 17,
            "newly_generated_approved_asset_count": 2,
            "forbidden_asset_connection_count": 0,
            "sleepwear_connection_clip_ids": [row["clip_id"] for row in rows if SLEEPWEAR in row["asset_names"]],
            "hand_mirror_connection_clip_ids": [row["clip_id"] for row in rows if MIRROR in row["asset_names"]],
            "shadow_asset_scope_valid": True,
            "scene_04_cave_picture_count": 0,
            "start_last_keyframe_file_count": 0,
            "queue_registration_performed": False,
            "video_generation_performed": False,
            "candidate_selection_performed": False,
            "upscale_performed": False,
            "assets": copied_assets,
            "clips": validations,
        }
        (staging / "PROMPT_VALIDATION_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    projects = h3_prompt_projects.list_projects(ROOT)["projects"]
    loaded_project = next((item for item in projects if item["project_id"] == PROJECT_ID), None)
    if not loaded_project:
        raise ValueError("Project loader did not discover the assembled project")
    loaded_clips = h3_prompt_projects.project_clips(ROOT, PROJECT_ID)
    if len(loaded_clips["clips"]) != 59:
        raise ValueError("Project loader did not load 59 clips")
    return {
        "project_id": PROJECT_ID,
        "project_path": str(destination),
        "scene_count": 4,
        "clip_count": 59,
        "total_duration_seconds": 519.0,
        "asset_count": 19,
        "existing_approved_asset_count": 17,
        "newly_generated_approved_asset_count": 2,
        "asset_sha256_mismatch_count": 0,
        "forbidden_asset_connection_count": 0,
        "local_strict_contract_error_count": strict_errors,
        "loader_clip_count": len(loaded_clips["clips"]),
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
