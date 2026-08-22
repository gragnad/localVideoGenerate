#!/usr/bin/env python3
from __future__ import annotations

"""Append the supplied ten V2 review clips to the existing EP00 V7 project."""

import hashlib
import json
import os
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

PROJECT_ID = "RaisingaDragonSeason01_EP00_CINEMATIC_LIVEACTION_H3_R2V_V7"
PROJECT = ROOT / "prompt_projects" / PROJECT_ID
SCENE = PROJECT / "EP00-CONTINUOUS"
PRODUCTION = ROOT / "projects/RaisingaDragonSeason01/ep00_cinematic_liveaction_production_v6"
SOURCE = PRODUCTION / "EP00_H3_R2V_REVISED_CLIPS_ADDENDUM_V2.md"
COMMAND = PRODUCTION / "EP00_CODEX_ADD_REVISED_CLIPS_COMMAND_V2.md"
BACKUP_RELATIVE = Path("source/revision_backups/EP00_REVISED_CLIPS_ADDENDUM_V2_PREAPPLY")
BACKUP = PROJECT / BACKUP_RELATIVE
SOURCE_COPY = PROJECT / "source/EP00_H3_R2V_REVISED_CLIPS_ADDENDUM_V2.source.md"
REPORT = PROJECT / "ADDENDUM_V2_VALIDATION_REPORT.json"

LUA = "H3_LUA_KOREAN_IDOL_PONYTAIL_LONG_LEG_CINEMATIC_LIVEACTION_IDENTITY_V3.png"
KING = "H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png"
SPEAR = "H3_LUA_SPEAR_PROP_HQ_V3_CINEMATIC_PROP_V1.png"
SHIELD = "FX_EP00_FLOATING_CURRENT_SHIELD_CINEMATIC_LIVEACTION_V1.png"
MASTER = "BG_EP00_ABYSS_ALTAR_CONNECTED_CHANNEL_CONVERGENCE_MASTER_CINEMATIC_LIVEACTION_V3.png"
ROLES = {
    LUA: ("lua_identity_v3", "Lua Korean idol ponytail long-leg identity V3"),
    KING: ("abyss_king_identity", "Human-scale Abyss King identity"),
    SPEAR: ("lua_spear_prop", "Lua spear prop"),
    SHIELD: ("floating_current_shield", "Ground-disconnected floating current shield"),
    MASTER: ("abyss_altar_connected_channel_convergence_master_v3", "EP00 connected-channel central-convergence Abyss Altar master V3"),
}
ASSET_PATHS = {name: PROJECT / "assets/shared" / name for name in ROLES}

CLIPS = [
    ("EP00_C04_V2", 23, 6.5, [LUA, MASTER], {"variant_of": "EP00_C04"}),
    ("EP00_C05_V2", 24, 8.5, [LUA, SHIELD, MASTER], {"variant_of": "EP00_C05"}),
    ("EP00_C08_V2", 25, 7.5, [KING, LUA, SPEAR, MASTER], {"variant_of": "EP00_C08"}),
    ("EP00_C12_V2", 26, 6.5, [LUA, MASTER], {"variant_of": "EP00_C12"}),
    ("EP00_C13_V2", 27, 7.5, [KING, MASTER], {"variant_of": "EP00_C13"}),
    ("EP00_C14_V2", 28, 8.5, [KING, LUA, MASTER], {"variant_of": "EP00_C14"}),
    ("EP00_C15_V2", 29, 7.5, [LUA, MASTER], {"variant_of": "EP00_C15"}),
    ("EP00_C16_V2", 30, 5.5, [KING, MASTER], {"variant_of": "EP00_C16"}),
    ("EP00_C16_01_V2", 31, 5.5, [LUA, MASTER], {"insert_after": "EP00_C16_V2", "insert_before": "EP00_C17"}),
    ("EP00_C21_C22_V2", 32, 10.5, [LUA, KING, MASTER], {"combines": ["EP00_C21", "EP00_C22"]}),
]
EXPECTED_IDS = [row[0] for row in CLIPS]
EXPECTED = {row[0]: row for row in CLIPS}
SECTIONS = ["subject_definitions", "summary", "retention_analysis", "detailed_description", "overall_soundscape", "non_diegetic_music"]
CLIP_ID_PATTERN = "(?:" + "|".join(re.escape(value) for value in EXPECTED_IDS) + ")"
CLIP_RE = re.compile(
    rf"^## (?P<clip_id>{CLIP_ID_PATTERN}) — (?P<title>.+?)\s*$"
    rf"(?P<body>.*?)(?=^## {CLIP_ID_PATTERN} — |^## 4\.|\Z)",
    re.M | re.S,
)
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


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_rows() -> list[dict[str, object]]:
    rows = []
    for match in CLIP_RE.finditer(SOURCE.read_text(encoding="utf-8")):
        clip_id, body = match.group("clip_id"), match.group("body")
        if clip_id not in EXPECTED:
            raise ValueError(f"Unexpected addendum clip: {clip_id}")
        duration_match, prompt_match = DURATION_RE.search(body), PROMPT_RE.search(body)
        if not duration_match or not prompt_match:
            raise ValueError(f"Incomplete addendum clip: {clip_id}")
        indexed = sorted((int(index), name) for index, name in INPUT_RE.findall(body))
        if [index for index, _ in indexed] != list(range(1, len(indexed) + 1)):
            raise ValueError(f"Non-contiguous Picture order: {clip_id}")
        names = [name for _, name in indexed]
        _id, sequence, expected_duration, expected_names, relation = EXPECTED[clip_id]
        duration = float(duration_match.group(1))
        if duration != expected_duration or names != expected_names:
            raise ValueError(f"Command/source mismatch: {clip_id}: duration={duration}, inputs={names}")
        prompt = prompt_match.group(1)
        validation = h3_prompt_contract.validate_prompt(prompt, duration_seconds=duration)
        if list(validation.section_names) != SECTIONS or validation.warnings:
            raise ValueError(f"Section validation mismatch: {clip_id}: {validation.as_dict()}")
        dialogue = [value.strip() for value in DIALOGUE_RE.findall(prompt)]
        expected_dialogue = ["붙잡아."] if clip_id == "EP00_C12_V2" else []
        if dialogue != expected_dialogue:
            raise ValueError(f"Dialogue mismatch: {clip_id}: {dialogue}")
        summary = SUMMARY_RE.search(prompt)
        rows.append({
            "clip_id": clip_id, "sequence": sequence, "title": match.group("title").strip(),
            "duration_seconds": duration, "asset_names": names, "relation": relation,
            "video_prompt": prompt, "summary": summary.group(1).strip() if summary else "",
            "required_dialogue": dialogue, "prompt_sha256": sha_text(prompt),
            "strict_contract_validation": validation.as_dict(),
        })
    if [row["clip_id"] for row in rows] != EXPECTED_IDS:
        raise ValueError(f"Addendum clip order mismatch: {[row['clip_id'] for row in rows]}")
    if sum(float(row["duration_seconds"]) for row in rows) != 74.0:
        raise ValueError("Supplemental duration is not 74.0 seconds")
    return rows


def preflight() -> tuple[dict, dict, list[dict[str, object]], dict[str, str]]:
    if not PROJECT.is_dir():
        raise FileNotFoundError(PROJECT)
    for path in (SOURCE, COMMAND, PROJECT / "manifest.json", PROJECT / "asset_mapping.json", PROJECT / "PROMPT_VALIDATION_REPORT.json", PROJECT / "ASSET_CHECK_REPORT.md"):
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(path)
    if BACKUP.exists() or SOURCE_COPY.exists() or REPORT.exists():
        raise FileExistsError("Addendum V2 output or backup already exists")
    collisions = [clip_id for clip_id in EXPECTED_IDS if (SCENE / f"{clip_id}.md").exists()]
    if collisions:
        raise FileExistsError("New clip collision: " + ", ".join(collisions))
    manifest = json.loads((PROJECT / "manifest.json").read_text(encoding="utf-8"))
    mapping = json.loads((PROJECT / "asset_mapping.json").read_text(encoding="utf-8"))
    if manifest.get("project_id") != PROJECT_ID:
        raise ValueError("Project ID mismatch")
    facts = manifest.get("build_facts") or {}
    if (facts.get("clip_count"), facts.get("candidate_entry_count"), facts.get("total_duration_seconds")) != (22, 66, 165.0):
        raise ValueError(f"Canonical build facts mismatch: {facts}")
    for flag in ("queue_authorized", "video_generation_authorized", "queue_registration_performed", "video_generation_performed", "candidate_selection_performed", "upscale_performed"):
        if manifest.get(flag) is not False:
            raise ValueError(f"Project state flag is not false: {flag}")
    canonical_paths = [SCENE / f"EP00_C{i:02d}.md" for i in range(1, 23)]
    if not all(path.is_file() for path in canonical_paths) or len(mapping) != 22:
        raise ValueError("Canonical clips or mapping are incomplete")
    overview = h3_prompt_projects.project_clips(ROOT, PROJECT_ID)
    if len(overview["clips"]) != 22 or not all(clip["ready"] for clip in overview["clips"]):
        raise ValueError("Canonical project loader preflight failed")
    for path in ASSET_PATHS.values():
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(path)
    original_hashes = {path.name: sha_path(path) for path in canonical_paths}
    return manifest, mapping, parse_rows(), original_hashes


def apply() -> dict[str, object]:
    manifest, mapping, rows, original_hashes = preflight()
    stage = PROJECT / f".addendum-v2-building-{secrets.token_hex(4)}"
    stage.mkdir()
    committed_new_clips: list[Path] = []
    metadata_replaced = False
    try:
        backup_stage = stage / BACKUP_RELATIVE
        backup_stage.mkdir(parents=True)
        metadata_hashes = {}
        for name in ("manifest.json", "asset_mapping.json", "PROMPT_VALIDATION_REPORT.json", "ASSET_CHECK_REPORT.md"):
            original = PROJECT / name
            shutil.copy2(original, backup_stage / name)
            metadata_hashes[name] = sha_path(original)
        write_json(backup_stage / "METADATA_SHA256_BEFORE_ADDENDUM_V2.json", metadata_hashes)
        (backup_stage / "ORIGINAL_CLIP_SHA256_BEFORE_ADDENDUM_V2.txt").write_text("".join(f"{digest}  {name}\n" for name, digest in sorted(original_hashes.items())), encoding="utf-8")

        source_stage = stage / SOURCE_COPY.name
        shutil.copy2(SOURCE, source_stage)
        new_mapping = dict(mapping)
        validations = []
        clip_stage = stage / "clips"
        clip_stage.mkdir()
        for row in rows:
            clip_id, prompt = str(row["clip_id"]), str(row["video_prompt"])
            references = []
            for picture_index, asset_name in enumerate(row["asset_names"], start=1):
                role, label = ROLES[str(asset_name)]
                references.append({"picture_index": picture_index, "role": role, "label": label, "description": "", "instruction_en": "", "reference_kind": "visual_reference", "required": True, "source_path": f"assets/shared/{asset_name}"})
            new_mapping[clip_id] = references
            variants = [{"variant_id": candidate, "label": f"Candidate {candidate} · supplied addendum original", "rationale": "Exact duplicate of the supplied addendum prompt; no derivation.", "video_prompt": prompt} for candidate in ("A", "D", "E")]
            payload = {
                "schema_version": 2, "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
                "workflow": h3_prompt_projects.WORKFLOW, "project_id": PROJECT_ID,
                "scene_id": "EP00-CONTINUOUS", "clip_id": clip_id, "source_clip_id": clip_id,
                "sequence": row["sequence"], "status": "pending_user_prompt_review",
                "duration_seconds": row["duration_seconds"], "title": row["title"],
                "video_prompt": prompt, "prompt_variants": variants, "references": references,
                "canonical_source_lineage": [SOURCE.name],
                "locked_rule_id": "EP00_CINEMATIC_LIVEACTION_R2V_V7_ADDENDUM_V2_EXACT",
                "summary": row["summary"], "required_dialogue": row["required_dialogue"],
                "dialogue_lock_version": "EP00_CINEMATIC_LIVEACTION_V7_ADDENDUM_V2",
                "source_prompt_sha256": row["prompt_sha256"],
                "candidate_policy": "A=D=E; exact supplied prompt",
                "scene_type": "user_supplied_revision_clip", "semantic_review": "not_performed",
                **row["relation"],
            }
            path = clip_stage / f"{clip_id}.md"
            path.write_text(f"# {clip_id} · {row['title']} · MiniMax H3 R2V\n\n## Machine Payload\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n", encoding="utf-8")
            loaded = h3_prompt_projects.extract_payload(path.read_text(encoding="utf-8"))
            hashes = {item["variant_id"]: sha_text(item["video_prompt"]) for item in loaded["prompt_variants"]}
            if loaded["video_prompt"] != prompt or any(value != row["prompt_sha256"] for value in hashes.values()):
                raise ValueError(f"Serialized prompt mismatch: {clip_id}")
            validations.append({"clip_id": clip_id, "duration_seconds": row["duration_seconds"], "picture_names": list(row["asset_names"]), "source_prompt_sha256": row["prompt_sha256"], "serialized_prompt_sha256": sha_text(loaded["video_prompt"]), "candidate_prompt_sha256": hashes, "six_section_order_valid": True, "passthrough_valid": True, "local_strict_contract_validation": row["strict_contract_validation"]})
        if any(new_mapping[key] != mapping[key] for key in mapping):
            raise ValueError("Existing asset mapping entry changed in staging")
        mapping_stage = stage / "asset_mapping.json"
        write_json(mapping_stage, new_mapping)

        new_manifest = json.loads(json.dumps(manifest))
        new_manifest["build_facts"].update({"clip_count": 32, "candidate_entry_count": 96, "unique_prompt_count": 32, "total_duration_seconds": 239.0, "canonical_clip_count": 22, "canonical_duration_seconds": 165.0, "supplemental_clip_count": 10, "supplemental_duration_seconds": 74.0, "project_local_asset_count": 5, "missing_asset_count": 0, "keyframe_or_i2v_instruction_count": 0})
        new_manifest.update({"supplemental_revision_policy": "keep_originals_and_append_v2_review_clips", "supplemental_revision_source": SOURCE.name, "final_edit_selection_performed": False})
        lineage = list(new_manifest.get("canonical_source_lineage") or [])
        for name in (SOURCE.name, COMMAND.name):
            if name not in lineage:
                lineage.append(name)
        new_manifest["canonical_source_lineage"] = lineage
        manifest_stage = stage / "manifest.json"
        write_json(manifest_stage, new_manifest)

        strict_errors = sum(len(row["strict_contract_validation"]["errors"]) for row in rows)
        report = {
            "schema_version": 1, "project_id": PROJECT_ID, "valid": True,
            "validation_mode": "exact_user_supplied_passthrough_addendum",
            "source_document": SOURCE.name, "source_document_sha256": sha_path(SOURCE),
            "canonical_clip_count": 22, "canonical_clip_sha256_unchanged_count": 22,
            "supplemental_clip_count": 10, "supplemental_duration_seconds": 74.0,
            "catalog_clip_count": 32, "catalog_total_duration_seconds": 239.0,
            "candidate_entry_count": 96, "project_local_asset_count": 5,
            "new_asset_count": 0, "linked_reference_count": sum(len(row["asset_names"]) for row in rows),
            "six_section_order_error_count": 0, "local_strict_contract_error_count": strict_errors,
            "local_strict_contract_errors_are_advisory_for_passthrough": True,
            "dialogue_tag_count": 1, "keyframe_or_i2v_input_count": 0,
            "queue_registration_performed": False, "video_generation_performed": False,
            "candidate_selection_performed": False, "upscale_performed": False,
            "final_edit_selection_performed": False,
            "backup_path": str(BACKUP_RELATIVE), "metadata_sha256_before": metadata_hashes,
            "canonical_clip_sha256_before": original_hashes, "clips": validations,
        }
        report_stage = stage / REPORT.name
        write_json(report_stage, report)

        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        os.replace(backup_stage, BACKUP)
        os.replace(source_stage, SOURCE_COPY)
        for row in rows:
            target = SCENE / f"{row['clip_id']}.md"
            os.replace(clip_stage / target.name, target)
            committed_new_clips.append(target)
        os.replace(mapping_stage, PROJECT / "asset_mapping.json")
        os.replace(manifest_stage, PROJECT / "manifest.json")
        metadata_replaced = True
        os.replace(report_stage, REPORT)
    except Exception:
        for path in committed_new_clips:
            path.unlink(missing_ok=True)
        SOURCE_COPY.unlink(missing_ok=True)
        REPORT.unlink(missing_ok=True)
        if metadata_replaced and BACKUP.is_dir():
            for name in ("manifest.json", "asset_mapping.json"):
                shutil.copy2(BACKUP / name, PROJECT / name)
        if BACKUP.is_dir():
            shutil.rmtree(BACKUP)
        shutil.rmtree(stage, ignore_errors=True)
        raise
    shutil.rmtree(stage, ignore_errors=True)
    return {"project_id": PROJECT_ID, "project_path": str(PROJECT), "canonical_clip_count": 22, "supplemental_clip_count": 10, "supplemental_duration_seconds": 74.0, "catalog_clip_count": 32, "catalog_total_duration_seconds": 239.0, "new_asset_count": 0, "reused_asset_count": 5, "backup_path": str(BACKUP), "validation_report": str(REPORT), "queue_registration_performed": False, "video_generation_performed": False}


if __name__ == "__main__":
    print(json.dumps(apply(), ensure_ascii=False, indent=2))
