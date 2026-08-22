#!/usr/bin/env python3
"""Validate the authoritative Raising a Dragon Season 1 rebuild chain.

This is a read-only regression guard. It never generates images, prompts, queue
entries, or videos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


EPISODES = [f"EP{index:02d}" for index in range(11)]
ABILITY_FIELDS = {
    "activation_conditions",
    "visible_evidence",
    "range",
    "duration",
    "costs",
    "failure_modes",
    "counterplay",
    "forbidden_interpretations",
}
STATE_FIELDS = {
    "knowledge_in",
    "knowledge_out",
    "resource_in",
    "resource_out",
    "health_in",
    "health_out",
    "fatigue_in",
    "fatigue_out",
    "spatial_in",
    "spatial_out",
}
OFFICIAL_H3_SECTIONS = [
    "<subject_definitions>",
    "<summary>",
    "<retention_analysis>",
    "<detailed_description>",
    "<overall_soundscape>",
    "<non_diegetic_music>",
]
STAGE_1_7_CORE_FILES = [
    "SEASON01_REBUILD_V2_SOURCE_CLASSIFICATION.md",
    "SEASON01_REBUILD_V2_STORY_AUDIT.md",
    "SEASON01_STORY_BIBLE_V2.md",
    "SEASON01_CHARACTER_PERFORMANCE_SCREEN_GRAMMAR_V2.md",
    "SEASON01_VISUAL_DESIGN_BIBLE_V2.md",
    "H3_CHARACTER_REFERENCE_SHEET_STANDARD_V2.md",
    "SEASON01_ABILITY_RULE_CARDS_V2.json",
    "SEASON01_KNOWLEDGE_RESOURCE_STATE_MAP_V2.json",
    "SEASON01_CHARACTER_DESIGN_GENERATION_MANIFEST_V5.json",
    "SEASON01_H3_DESIGN_ASSET_LOCK_V5.json",
    "SEASON01_ANIMATION_ADAPTATION_BEAT_SHEETS_V2.md",
    "SEASON01_ANIMATION_ADAPTATION_BEAT_SHEET_LOCK_V2.json",
]

STORYBOARD_PRODUCTION_LOCK = "EP00_EP01_STORYBOARD_PRODUCTION_LOCK_V1.json"
STORYBOARD_ADE_PROJECT_ID = "RaisingaDragonSeason01_EP00_EP01_H3_R2V_STORYBOARD_ADE_V2"


class Audit:
    def __init__(self) -> None:
        self.checks = 0
        self.failures: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.failures.append(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, audit: Audit) -> dict[str, Any]:
    audit.require(path.is_file(), f"missing JSON: {path.name}")
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        audit.require(False, f"invalid JSON {path.name}: {exc}")
        return {}
    audit.require(isinstance(value, dict), f"JSON root must be an object: {path.name}")
    return value if isinstance(value, dict) else {}


def png_dimensions(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()[:24]
    if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def walk_asset_rows(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        path = value.get("path")
        digest = value.get("sha256")
        if isinstance(path, str) and isinstance(digest, str) and path.lower().endswith(".png"):
            yield value
        for child in value.values():
            yield from walk_asset_rows(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_asset_rows(child)


def validate_source_locks(root: Path, document: dict[str, Any], label: str, audit: Audit) -> None:
    rows = document.get("source_locks")
    audit.require(isinstance(rows, list) and bool(rows), f"{label}: source_locks missing")
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            audit.require(False, f"{label}: malformed source lock")
            continue
        rel = row.get("path")
        expected = row.get("sha256")
        path = root / str(rel)
        audit.require(path.is_file(), f"{label}: missing locked source {rel}")
        if path.is_file():
            audit.require(sha256(path) == expected, f"{label}: stale hash for {rel}")


def validate_stage_scope_and_artifacts(root: Path, audit: Audit) -> None:
    for filename in STAGE_1_7_CORE_FILES:
        audit.require((root / filename).is_file(), f"missing stage 1-7 core artifact: {filename}")

    classification_path = root / "SEASON01_REBUILD_V2_SOURCE_CLASSIFICATION.md"
    classification = classification_path.read_text(encoding="utf-8") if classification_path.is_file() else ""
    for grade in ("A등급", "B등급", "C등급", "D등급", "E등급"):
        audit.require(grade in classification, f"source classification missing {grade}")
    audit.require("기존 잠금 해제 결정" in classification, "source classification missing legacy lock-release decision")

    story_audit_path = root / "SEASON01_REBUILD_V2_STORY_AUDIT.md"
    story_audit = story_audit_path.read_text(encoding="utf-8") if story_audit_path.is_file() else ""
    for episode in EPISODES:
        audit.require(f"### {episode}" in story_audit, f"season story audit missing {episode}")
    audit.require("EP00 여섯 전투 국면 감사 계약" in story_audit, "story audit missing EP00 six-phase contract")

    bible_path = root / "SEASON01_STORY_BIBLE_V2.md"
    bible = bible_path.read_text(encoding="utf-8") if bible_path.is_file() else ""
    for episode in EPISODES:
        audit.require(episode in bible, f"story bible missing episode arc reference: {episode}")

    later_output_name = re.compile(r"EP(?:0[2-9]|10).*(?:STORYBOARD|H3[_-]?ADE|PROMPT)", re.IGNORECASE)
    forbidden_later_outputs = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and later_output_name.search(path.name)
    ]
    audit.require(
        not forbidden_later_outputs,
        f"EP02-EP10 must stop at stage 7, found downstream outputs: {forbidden_later_outputs}",
    )

    storyboard_manifest_path = root / "EP00_EP01_STORYBOARD_GENERATION_MANIFEST_V2.json"
    storyboard_manifest = load_json(storyboard_manifest_path, audit)
    approval_gate = storyboard_manifest.get("approval_gate", {})
    if isinstance(approval_gate, dict) and approval_gate.get("generation_allowed") is False:
        generated_storyboards = (
            [
                path
                for path in (root / "storyboards_v2").rglob("*.png")
                if "rejected" not in path.relative_to(root / "storyboards_v2").parts
            ]
            if (root / "storyboards_v2").exists()
            else []
        )
        prompt_output_roots = [root / name for name in ("h3_prompts_v2", "h3_ade_prompts_v2", "prompts_v2")]
        generated_prompts = [path for output_root in prompt_output_roots if output_root.exists() for path in output_root.rglob("*") if path.is_file()]
        audit.require(not generated_storyboards, "storyboard generation gate is closed but storyboard PNG outputs exist")
        audit.require(not generated_prompts, "prompt generation gate is closed but H3 prompt outputs exist")


def validate_screenplays_and_beats(root: Path, audit: Audit) -> None:
    source_scenes: dict[str, set[str]] = {}
    total_scenes = 0
    for episode in EPISODES:
        path = root / f"{episode}_NARRATIVE_SCREENPLAY_V2.md"
        audit.require(path.is_file(), f"missing screenplay: {path.name}")
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        numbers = re.findall(r"^## Scene (\d+)\.", text, flags=re.MULTILINE)
        ids = {f"{episode}-S{int(number):02d}" for number in numbers}
        audit.require(bool(ids), f"no scenes found: {path.name}")
        audit.require(len(ids) == len(numbers), f"duplicate scene number: {path.name}")
        source_scenes[episode] = ids
        total_scenes += len(ids)
    audit.require(total_scenes == 70, f"screenplay scene total must be 70, got {total_scenes}")

    beat_path = root / "SEASON01_ANIMATION_ADAPTATION_BEAT_SHEETS_V2.md"
    audit.require(beat_path.is_file(), "missing beat sheet")
    text = beat_path.read_text(encoding="utf-8") if beat_path.is_file() else ""
    rows: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if not re.match(r"^\| EP\d{2}-S\d{2}[A-C]? \|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append((cells[0] if cells else "", cells))
    ids = [row[0] for row in rows]
    audit.require(len(rows) == 94, f"beat row total must be 94, got {len(rows)}")
    audit.require(len(set(ids)) == 94, "beat IDs must be unique")
    for beat_id, cells in rows:
        audit.require(len(cells) == 6, f"beat row must have six cells: {beat_id}")
        audit.require(all(cells), f"beat row has an empty required cell: {beat_id}")
    covered: dict[str, set[str]] = {episode: set() for episode in EPISODES}
    for beat_id in ids:
        match = re.fullmatch(r"(EP\d{2}-S\d{2})[A-C]?", beat_id)
        audit.require(match is not None, f"malformed beat ID: {beat_id}")
        if match:
            covered[beat_id[:4]].add(match.group(1))
    for episode in EPISODES:
        audit.require(
            covered[episode] == source_scenes[episode],
            f"beat coverage mismatch for {episode}: expected {sorted(source_scenes[episode])}, got {sorted(covered[episode])}",
        )
    audit.require(len(covered["EP00"]) == 6, "EP00 must preserve exactly six combat phases")


def validate_rules_and_state(root: Path, audit: Audit) -> None:
    abilities = load_json(root / "SEASON01_ABILITY_RULE_CARDS_V2.json", audit)
    rules = abilities.get("rules")
    audit.require(isinstance(rules, list), "ability rules must be a list")
    if isinstance(rules, list):
        ids = [row.get("id") for row in rules if isinstance(row, dict)]
        audit.require(len(rules) == 14, f"ability rule total must be 14, got {len(rules)}")
        audit.require(len(set(ids)) == len(ids), "ability rule IDs must be unique")
        for row in rules:
            if isinstance(row, dict):
                audit.require(
                    ABILITY_FIELDS <= row.keys(),
                    f"ability rule missing fields: {row.get('id')}",
                )

    states = load_json(root / "SEASON01_KNOWLEDGE_RESOURCE_STATE_MAP_V2.json", audit)
    episodes = states.get("episodes")
    audit.require(isinstance(episodes, list), "state episodes must be a list")
    if isinstance(episodes, list):
        by_id = {row.get("episode"): row for row in episodes if isinstance(row, dict)}
        audit.require(set(by_id) == set(EPISODES), "state map must cover EP00 through EP10 exactly once")
        for episode in EPISODES:
            row = by_id.get(episode, {})
            audit.require(STATE_FIELDS <= row.keys(), f"state row missing fields: {episode}")


def validate_design_assets(root: Path, audit: Audit) -> None:
    manifest = load_json(root / "SEASON01_CHARACTER_DESIGN_GENERATION_MANIFEST_V5.json", audit)
    lock = load_json(root / "SEASON01_H3_DESIGN_ASSET_LOCK_V5.json", audit)
    prompt_source = manifest.get("major_prop_prompt_source")
    audit.require(
        prompt_source == "SEASON01_H3_MAJOR_PROP_GENERATION_PROMPTS_V4.md",
        "design manifest must use the corrected four-column major-prop prompt V4",
    )
    audit.require(
        isinstance(prompt_source, str) and (root / prompt_source).is_file(),
        "corrected major-prop prompt source is missing",
    )
    threat_lock = manifest.get("threat_generation_lock")
    audit.require(
        threat_lock == "SEASON01_H3_THREAT_REGENERATION_LOCK_V3.md",
        "design manifest must use the corrected threat-generation lock V3",
    )
    audit.require(
        isinstance(threat_lock, str) and (root / threat_lock).is_file(),
        "corrected threat-generation lock is missing",
    )
    mir_lock = manifest.get("mir_generation_lock")
    audit.require(
        mir_lock == "SEASON01_H3_MIR_REGENERATION_LOCK_V1.md",
        "design manifest must use the corrected Mir-generation lock V1",
    )
    audit.require(
        isinstance(mir_lock, str) and (root / mir_lock).is_file(),
        "corrected Mir-generation lock is missing",
    )
    identities = manifest.get("identity_candidates")
    props = manifest.get("prop_candidates")
    audit.require(isinstance(identities, list) and len(identities) == 16, "design manifest must have 16 identity candidates")
    audit.require(isinstance(props, list) and len(props) == 2, "design manifest must have two prop candidates")

    expected_identity_files = {
        Path(str(row.get("path", ""))).name for row in identities or [] if isinstance(row, dict)
    }
    actual_identity_files = {
        path.name for path in (root / "designs_hq_v1/h3_identity_sheets").glob("*.png")
    }
    audit.require(
        actual_identity_files == expected_identity_files,
        "active H3 identity folder must contain exactly the 16 manifest candidates; "
        f"extra={sorted(actual_identity_files - expected_identity_files)}, "
        f"missing={sorted(expected_identity_files - actual_identity_files)}",
    )
    expected_prop_files = {
        Path(str(row.get("path", ""))).name for row in props or [] if isinstance(row, dict)
    }
    actual_prop_files = {
        path.name for path in (root / "designs_hq_v1/h3_prop_sheets").glob("*.png")
    }
    audit.require(
        actual_prop_files == expected_prop_files,
        "active H3 prop folder must contain exactly the two manifest candidates; "
        f"extra={sorted(actual_prop_files - expected_prop_files)}, "
        f"missing={sorted(expected_prop_files - actual_prop_files)}",
    )

    seen: set[tuple[str, str]] = set()
    for document_name, document in (("design manifest", manifest), ("asset lock", lock)):
        for row in walk_asset_rows(document):
            key = (str(row["path"]), str(row["sha256"]))
            if key in seen:
                continue
            seen.add(key)
            path = root / key[0]
            audit.require(path.is_file(), f"{document_name}: missing asset {key[0]}")
            if not path.is_file():
                continue
            audit.require(sha256(path) == key[1], f"{document_name}: stale asset hash {key[0]}")
            dimensions = png_dimensions(path)
            audit.require(dimensions is not None, f"{document_name}: invalid PNG {key[0]}")
            if dimensions and "width" in row and "height" in row:
                audit.require(
                    dimensions == (int(row["width"]), int(row["height"])),
                    f"{document_name}: dimension mismatch {key[0]}",
                )

    active = lock.get("active_production_identity_assets")
    active_ids = {row.get("id") for row in active if isinstance(row, dict)} if isinstance(active, list) else set()
    required_identity_ids = set(manifest.get("required_identity_ids", []))
    audit.require(
        active_ids == required_identity_ids and len(active_ids) == 16,
        f"all 16 user-approved identity assets must be active, got {sorted(active_ids)}",
    )
    active_props = lock.get("active_production_prop_assets")
    active_prop_ids = {row.get("id") for row in active_props if isinstance(row, dict)} if isinstance(active_props, list) else set()
    required_prop_ids = set(manifest.get("required_prop_ids", []))
    audit.require(
        active_prop_ids == required_prop_ids and len(active_prop_ids) == 2,
        f"both user-approved major props must be active, got {sorted(active_prop_ids)}",
    )
    candidate_rows = [row for row in (identities or []) + (props or []) if isinstance(row, dict)]
    audit.require(
        all(row.get("status") == "approved-production-asset" for row in candidate_rows),
        "every required identity and prop candidate must be promoted after user approval",
    )
    audit.require(
        set(manifest.get("production_assets", [])) == required_identity_ids | required_prop_ids,
        "production_assets must contain all 18 approved identity and prop IDs",
    )
    audit.require(
        (root / "SEASON01_USER_APPROVAL_RECORD_20260817.md").is_file(),
        "missing user approval record for story and asset activation",
    )
    current_documents = {
        "design manifest": root / "SEASON01_CHARACTER_DESIGN_GENERATION_MANIFEST_V5.json",
        "asset lock": root / "SEASON01_H3_DESIGN_ASSET_LOCK_V5.json",
        "storyboard manifest": root / "EP00_EP01_STORYBOARD_GENERATION_MANIFEST_V2.json",
    }
    stale_asset_names = (
        "H3_BLACK_JELLYFISH_IDENTITY_HQ_V1.png",
        "H3_YOUNG_MIR_IDENTITY_HQ_V1.png",
        "H3_AWAKENED_MIR_IDENTITY_HQ_V1.png",
        "H3_SHADOW_FISH_IDENTITY_HQ_V3.png",
        "H3_LUA_SPEAR_PROP_HQ_V1.png",
        "H3_LUA_SPEAR_PROP_HQ_V2.png",
        "H3_MIR_SHELL_PROP_HQ_V2.png",
    )
    for document_name, document_path in current_documents.items():
        source = document_path.read_text(encoding="utf-8")
        for stale_name in stale_asset_names:
            audit.require(
                stale_name not in source,
                f"{document_name} still binds rejected asset {stale_name}",
            )
    forbidden_roots = tuple(str(value) for value in lock.get("forbidden_legacy_roots", []))
    for row in active or []:
        rel = str(row.get("path", ""))
        audit.require(not rel.startswith(forbidden_roots), f"active asset points into a forbidden legacy root: {rel}")


def validate_production_segmentation(root: Path, audit: Audit) -> None:
    path = root / "EP00_EP01_PRODUCTION_CLIP_SEGMENTATION_V2.md"
    audit.require(path.is_file(), "missing EP00/EP01 production segmentation")
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    rows: list[tuple[str, float, float, int]] = []
    for line in text.splitlines():
        if not re.match(r"^\| EP(?:00|01)-S\d{2}-C\d{2} \|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        audit.require(len(cells) == 5, f"malformed production clip row: {cells[0] if cells else line}")
        if len(cells) != 5:
            continue
        timing = re.fullmatch(r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)초", cells[2])
        audit.require(timing is not None, f"malformed timing: {cells[0]}")
        if timing:
            rows.append((cells[0], float(timing.group(1)), float(timing.group(2)), len(cells[3].split("→"))))
    counts = Counter(clip[:4] for clip, *_ in rows)
    target_totals = Counter()
    for clip, _, target, _ in rows:
        target_totals[clip[:4]] += target
    audit.require(len(rows) == 56, f"production clip total must be 56, got {len(rows)}")
    audit.require(len({row[0] for row in rows}) == 56, "production clip IDs must be unique")
    audit.require(counts == Counter({"EP00": 14, "EP01": 42}), f"production clip episode counts mismatch: {dict(counts)}")
    audit.require(abs(sum(row[1] for row in rows) - 602.0) < 1e-9, "source runtime must total 602 seconds")
    audit.require(abs(sum(row[2] for row in rows) - 574.0) < 1e-9, "target runtime must total 574 seconds")
    audit.require(abs(target_totals["EP00"] - 133.0) < 1e-9, "EP00 target runtime must remain 133 seconds")
    audit.require(120.0 <= target_totals["EP00"] <= 180.0, "EP00 target runtime must remain in the requested 2-3 minute range")
    audit.require(abs(target_totals["EP01"] - 441.0) < 1e-9, "EP01 target runtime must remain 441 seconds")
    for clip, source, target, panels in rows:
        audit.require(abs(source - 0.5 - target) < 1e-9, f"minus-0.5 timing regression: {clip}")
        audit.require(4.0 <= target <= 15.0, f"H3 target duration outside 4-15 seconds: {clip}")
        audit.require(panels == 4, f"production clip must have exactly four panel states: {clip}")


def validate_downstream_contracts(root: Path, audit: Audit) -> None:
    manifest = load_json(root / "EP00_EP01_STORYBOARD_GENERATION_MANIFEST_V2.json", audit)
    validate_source_locks(root, manifest, "storyboard overview manifest", audit)
    approval_gate = manifest.get("approval_gate", {})
    audit.require(approval_gate.get("generation_allowed") is True, "storyboard generation must be enabled after story and asset approval")
    for key in ("queue_allowed", "video_allowed"):
        audit.require(approval_gate.get(key) is False, f"{key} must remain false")
    audit.require(
        approval_gate.get("approval_evidence") == "SEASON01_USER_APPROVAL_RECORD_20260817.md",
        "storyboard generation gate must cite the user approval record",
    )
    scope = manifest.get("scope", {})
    audit.require(scope.get("production_clip_count") == 56, "storyboard manifest must lock 56 production clips")
    audit.require(scope.get("production_panel_count") == 224, "storyboard manifest must lock 224 production panels")

    contract_path = root / "EP00_EP01_H3_ADE_CONVERSION_CONTRACT_V2.md"
    audit.require(contract_path.is_file(), "missing H3 A/D/E conversion contract")
    text = contract_path.read_text(encoding="utf-8") if contract_path.is_file() else ""
    positions = [text.find(label) for label in OFFICIAL_H3_SECTIONS]
    audit.require(all(position >= 0 for position in positions), "H3 contract is missing an official section label")
    audit.require(positions == sorted(positions), "H3 official section labels are out of order")
    for required in (
        "정확히 네 개의 H3 Shot",
        "B, C 후보를 다시 만들지 않는다",
        "최대 9장",
        "timing-export-blocked",
        "큐 등록: `forbidden`",
        "영상 생성: `forbidden`",
    ):
        audit.require(required in text, f"H3 contract missing invariant: {required}")

    forbidden_phrases = {
        "SEASON01_CHARACTER_PERFORMANCE_SCREEN_GRAMMAR_V2.md": ["중립 턴어라운드만이 아니라 대기, 경계, 접촉, 회복, 피로와 선택 순간 포즈"],
        "H3_CHARACTER_ART_STYLE_LOCK_V3_HIGH_QUALITY.md": ["표정이 가능한 캐릭터는 중립·경계·분노·고통·회복처럼 얼굴 연기만 분리한다"],
        "SEASON01_CHARACTER_DESIGN_GENERATION_MANIFEST_V5.json": ["G2_MASTER_DESIGN"],
    }
    for filename, phrases in forbidden_phrases.items():
        source = (root / filename).read_text(encoding="utf-8")
        for phrase in phrases:
            audit.require(phrase not in source, f"stale sheet-drift rule remains in {filename}: {phrase}")

    beat_lock = load_json(root / "SEASON01_ANIMATION_ADAPTATION_BEAT_SHEET_LOCK_V2.json", audit)
    validate_source_locks(root, beat_lock, "beat sheet lock", audit)
    audit.require(
        beat_lock.get("downstream_use") == "approved-for-ep00-ep01-storyboard-generation-only",
        "beat sheet downstream approval gate does not record EP00/EP01 storyboard authorization",
    )


def validate_storyboard_production(root: Path, audit: Audit) -> None:
    lock = load_json(root / STORYBOARD_PRODUCTION_LOCK, audit)
    scope = lock.get("scope", {})
    audit.require(scope.get("expected_clip_count") == 56, "storyboard production lock must expect 56 clips")
    audit.require(scope.get("expected_panel_count") == 224, "storyboard production lock must expect 224 panels")
    status = lock.get("status", {})
    audit.require(
        status.get("ep00") == "user-approved-for-visual-prompt-conversion",
        "EP00 storyboard status must record user approval for visual prompt conversion",
    )
    audit.require(
        status.get("ep01") == "user-approved-for-visual-prompt-conversion",
        "EP01 storyboard status must record user approval for visual prompt conversion",
    )
    audit.require(
        status.get("h3_ade_conversion") == "generated-168-prompts-internal-validation-pass",
        "H3 A/D/E conversion must record the validated 168-prompt result",
    )
    audit.require(status.get("queue") == "forbidden", "storyboard lock must keep queue forbidden")
    audit.require(status.get("video_generation") == "forbidden", "storyboard lock must keep video generation forbidden")
    workspace = root.parents[2]
    prompt_project = workspace / "prompt_projects" / STORYBOARD_ADE_PROJECT_ID
    prompt_markdown = list(prompt_project.glob("EP*-S*/EP*-S*-C*.md"))
    manifest = load_json(prompt_project / "manifest.json", audit)
    facts = manifest.get("build_facts", {})
    audit.require(len(prompt_markdown) == 56, f"H3 A/D/E project must contain 56 Clip Markdown files, got {len(prompt_markdown)}")
    audit.require(
        facts.get("clip_count") == 56 and facts.get("prompt_count") == 168,
        "H3 A/D/E manifest must declare 56 clips and 168 prompts",
    )
    audit.require(
        all(manifest.get(key) is False for key in (
            "queue_authorized",
            "video_generation_authorized",
            "queue_registration_performed",
            "video_generation_performed",
        )),
        "H3 A/D/E prompt project must keep queue and video actions disabled",
    )
    audit.require(
        (root / "EP00_EP01_STORYBOARD_APPROVAL_RECORD_20260817.md").is_file(),
        "missing storyboard approval record for prompt conversion",
    )

    declared: dict[str, list[dict[str, Any]]] = {}
    for episode in ("ep00", "ep01"):
        rows = lock.get(f"{episode}_assets")
        audit.require(isinstance(rows, list), f"storyboard lock {episode}_assets must be a list")
        declared[episode] = [row for row in rows or [] if isinstance(row, dict)]
    audit.require(len(declared["ep00"]) == 14, f"EP00 storyboard lock must declare 14 clips, got {len(declared['ep00'])}")
    audit.require(len(declared["ep01"]) == 42, f"EP01 storyboard lock must declare 42 clips, got {len(declared['ep01'])}")
    audit.require(
        len(declared["ep00"]) + len(declared["ep01"]) == scope.get("expected_clip_count"),
        "storyboard production lock declared clip total differs from expected clip count",
    )
    audit.require(
        sum(row.get("panels", 0) for rows in declared.values() for row in rows) == scope.get("expected_panel_count"),
        "storyboard production lock declared panel total differs from expected panel count",
    )

    all_ids: list[str] = []
    for episode, rows in declared.items():
        row_paths: set[str] = set()
        for row in rows:
            clip_id = row.get("clip_id")
            rel = row.get("path")
            all_ids.append(str(clip_id))
            audit.require(isinstance(clip_id, str) and clip_id.startswith(episode.upper()), f"storyboard clip/episode mismatch: {clip_id}")
            audit.require(row.get("panels") == 4, f"storyboard must declare four panels: {clip_id}")
            audit.require(
                row.get("status") == "internal-review-pass-user-review-pending",
                f"storyboard generation-time review snapshot changed unexpectedly: {clip_id}",
            )
            path = root / str(rel)
            audit.require(path.is_file(), f"missing active storyboard: {rel}")
            if path.is_file():
                audit.require(sha256(path) == row.get("sha256"), f"stale storyboard hash: {rel}")
                dimensions = png_dimensions(path)
                audit.require(
                    dimensions == (row.get("width"), row.get("height")),
                    f"storyboard dimension/hash lock mismatch: {rel}",
                )
                if dimensions:
                    width, height = dimensions
                    audit.require(width == 1672 and height in (940, 941), f"storyboard native 16:9 output regression: {rel}")
            row_paths.add(str(rel))
        active_dir = root / "storyboards_v2" / episode
        active_paths = {
            path.relative_to(root).as_posix()
            for path in active_dir.glob("*.png")
        } if active_dir.is_dir() else set()
        audit.require(active_paths == row_paths, f"active {episode} storyboard folder differs from lock")
    audit.require(len(all_ids) == len(set(all_ids)), "storyboard clip IDs must be unique")

    segmentation = (root / "EP00_EP01_PRODUCTION_CLIP_SEGMENTATION_V2.md").read_text(encoding="utf-8")
    expected_ep00 = set(re.findall(r"^\| (EP00-S\d{2}-C\d{2}) \|", segmentation, flags=re.MULTILINE))
    expected_ep01 = set(re.findall(r"^\| (EP01-S\d{2}-C\d{2}) \|", segmentation, flags=re.MULTILINE))
    audit.require({row["clip_id"] for row in declared["ep00"]} == expected_ep00, "EP00 storyboard clip coverage mismatch")
    audit.require({row["clip_id"] for row in declared["ep01"]} == expected_ep01, "EP01 storyboard clip coverage mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "projects" / "RaisingaDragonSeason01" / "rebuild_v2",
        help="Path to the rebuild_v2 directory",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    audit = Audit()
    audit.require(root.is_dir(), f"rebuild root does not exist: {root}")
    if root.is_dir():
        validate_stage_scope_and_artifacts(root, audit)
        validate_screenplays_and_beats(root, audit)
        validate_rules_and_state(root, audit)
        validate_design_assets(root, audit)
        validate_production_segmentation(root, audit)
        validate_downstream_contracts(root, audit)
        validate_storyboard_production(root, audit)

    if audit.failures:
        print(f"FAIL: {len(audit.failures)} of {audit.checks} checks failed")
        for failure in audit.failures:
            print(f"- {failure}")
        return 1
    print(f"PASS: {audit.checks} checks")
    print("scope: EP00-EP10 stages 1-7; EP00-EP01 stages 8-9 complete")
    print("generation: storyboard=true prompt=true queue=false video=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
