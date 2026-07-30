#!/usr/bin/env python3
"""Apply standalone generation prompts to RaisingaDragonSeason01 EP01 Director project."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import director_prompt_projects as dpp
from scripts.director_generation_specs_ep01 import (
    BACKGROUND_IMAGE_GENERATION,
    LOCATION_META,
    REFERENCE_PATHS,
    SEGMENT_BEATS,
    build_generation_prompt,
)

PROJECT_ID = "RaisingaDragonSeason01"
PROJECT_DIR = ROOT / "director_prompt_projects" / PROJECT_ID
REGISTRY_PATH = PROJECT_DIR / "location_registry.json"

# Re-export reference path constants for downstream tooling.
REF_PATHS = REFERENCE_PATHS

FORBIDDEN_RE = re.compile(
    r"Picture\s+\d+|(?:CHAR|ENTITY|PROP)_[A-Z0-9_]+|Specify screen positions",
    re.I,
)
CAMERA_MOVE_RE = re.compile(
    r"camera\s+(moves|tilts|continues|pans|tracks|pulls|pushes|dolly|drifts|shudders|follows)",
    re.I,
)


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def merge_location_registry(registry: dict[str, Any]) -> dict[str, Any]:
    locations = dict(registry.get("locations") or {})
    for loc_id, bg_spec in BACKGROUND_IMAGE_GENERATION.items():
        entry = dict(locations.get(loc_id) or {})
        if loc_id in LOCATION_META:
            entry.update(LOCATION_META[loc_id])
        elif not entry:
            entry = {
                "location_id": loc_id,
                "background_id": bg_spec["suggested_filename"].replace(".png", ""),
                "display_name": loc_id.replace("LOC_", "").replace("_", " ").title(),
            }
        entry["image_generation"] = {
            "generation_prompt": bg_spec["generation_prompt"],
            "negative_prompt": bg_spec["negative_prompt"],
            "suggested_filename": bg_spec["suggested_filename"],
            "source_path": entry.get("image_generation", {}).get("source_path"),
            "review_status": "pending",
            "review_notes": [],
            "sha256": None,
        }
        locations[loc_id] = entry
    registry["locations"] = locations
    return registry


def render_markdown(summary: str, payload: dict[str, Any]) -> str:
    return (
        f"# Director Prompt: {payload['clip_id']}\n\n"
        f"## Summary\n\n{summary}\n\n"
        "## Machine Payload\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n"
    )


def extract_summary(markdown: str, clip_id: str) -> str:
    match = re.search(r"## Summary\s*\n\s*\n(.+?)\n\n##", markdown, re.S)
    return match.group(1).strip() if match else f"Director prompt for {clip_id}."


def apply_clip(markdown_path: Path) -> tuple[dict[str, Any], list[str]]:
    markdown = markdown_path.read_text(encoding="utf-8")
    payload = dpp.extract_machine_payload(markdown)
    clip_id = str(payload.get("clip_id") or "")
    issues: list[str] = []

    for segment in payload.get("segments") or []:
        seg_id = str(segment.get("segment_id") or "")
        key = (clip_id, seg_id)
        beat = SEGMENT_BEATS.get(key)
        if beat is None:
            issues.append(f"missing beat: {clip_id}/{seg_id}")
            continue

        scene = dict(segment.get("scene_image") or {})
        generation_prompt = build_generation_prompt(beat)
        refs = list(beat.get("reference_paths") or [])
        # Ensure spear reference whenever spear is described or listed as visible prop.
        spear_path = REFERENCE_PATHS["spear"]
        visible_props = segment.get("visible_props") or []
        if (
            ("PROP_LUA_SPEAR" in visible_props or "fishing spear" in generation_prompt.lower())
            and spear_path not in refs
            and "spear" in generation_prompt.lower()
        ):
            refs.append(spear_path)
        # Deduplicate while preserving order
        deduped_refs: list[str] = []
        seen: set[str] = set()
        for path in refs:
            if path not in seen:
                seen.add(path)
                deduped_refs.append(path)
        refs = deduped_refs

        neg = beat.get("negative_prompt") or ""
        # Deduplicate comma-separated negative tokens
        neg_parts = []
        seen_neg: set[str] = set()
        for part in [p.strip() for p in neg.split(",") if p.strip()]:
            key = part.lower()
            if key not in seen_neg:
                seen_neg.add(key)
                neg_parts.append(part)
        # Ensure Lua+Mir negatives when both appear
        if "Lua" in generation_prompt and "Young Mir" in generation_prompt:
            for extra in (
                "dragon wings horns scales or tail on Lua",
                "human hair clothing arms or legs on Young Mir",
                "merged Lua and Young Mir",
                "duplicate Lua",
                "duplicate Young Mir",
            ):
                if extra.lower() not in seen_neg:
                    neg_parts.append(extra)
                    seen_neg.add(extra.lower())

        scene["generation_prompt"] = generation_prompt
        scene["background_id"] = beat["background_id"]
        scene["reference_paths"] = refs
        scene["negative_prompt"] = ", ".join(neg_parts)
        scene["source_path"] = None
        scene["sha256"] = None
        scene["review_status"] = "pending"
        scene["status"] = "missing"
        segment["scene_image"] = scene

        if FORBIDDEN_RE.search(generation_prompt):
            issues.append(f"forbidden token in {clip_id}/{seg_id}")
        if CAMERA_MOVE_RE.search(generation_prompt):
            issues.append(f"camera move in {clip_id}/{seg_id}")
        if not beat.get("background_id"):
            issues.append(f"missing background_id {clip_id}/{seg_id}")
        if "reference_paths" not in beat:
            issues.append(f"missing reference_paths key {clip_id}/{seg_id}")

    review = dict(payload.get("prompt_review") or {})
    review["image_prompts_valid"] = True
    review["status"] = "approved"
    notes = [str(n) for n in review.get("review_notes") or []]
    notes = [n for n in notes if "standalone generation prompts" not in n]
    notes.append(
        "scene_image.generation_prompt set as standalone English prompts with "
        "background_id, reference_paths, and negative_prompt per segment."
    )
    review["review_notes"] = notes
    payload["prompt_review"] = review
    payload["status"] = "awaiting_scene_images"

    summary = extract_summary(markdown, clip_id)
    updated = render_markdown(summary, payload)
    markdown_path.write_text(updated, encoding="utf-8")
    return payload, issues


def audit(registry: dict[str, Any], segment_checks: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []

    bg_with_prompt = 0
    for loc_id, loc in (registry.get("locations") or {}).items():
        ig = (loc or {}).get("image_generation") or {}
        if ig.get("generation_prompt"):
            bg_with_prompt += 1
    if bg_with_prompt != 11:
        issues.append(f"background generation_prompt count={bg_with_prompt}, expected 11")

    if "LOC_EP01_COASTAL_CAVE_TOWARD_MOUTH" not in registry.get("locations", {}):
        issues.append("cave toward mouth location missing")

    if len(segment_checks) != 89:
        issues.append(f"segment count={len(segment_checks)}, expected 89")

    for row in segment_checks:
        cid = row["clip_id"]
        sid = row["segment_id"]
        if not row.get("generation_prompt"):
            issues.append(f"missing generation_prompt {cid}/{sid}")
        if not row.get("background_id"):
            issues.append(f"missing background_id {cid}/{sid}")
        if row.get("reference_paths") is None:
            issues.append(f"missing reference_paths {cid}/{sid}")
        gp = row.get("generation_prompt") or ""
        if FORBIDDEN_RE.search(gp):
            issues.append(f"forbidden token {cid}/{sid}")
        if "Specify screen positions" in gp:
            issues.append(f"meta instruction {cid}/{sid}")
        if CAMERA_MOVE_RE.search(gp):
            issues.append(f"camera move {cid}/{sid}")

    return issues


def main() -> int:
    registry = merge_location_registry(load_registry())
    REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    all_issues: list[str] = []
    segment_checks: list[dict[str, Any]] = []
    clip_count = 0

    for markdown_path in sorted(PROJECT_DIR.rglob("*.md")):
        payload, issues = apply_clip(markdown_path)
        clip_count += 1
        all_issues.extend(issues)
        clip_id = payload.get("clip_id")
        for segment in payload.get("segments") or []:
            scene = segment.get("scene_image") or {}
            segment_checks.append(
                {
                    "clip_id": clip_id,
                    "segment_id": segment.get("segment_id"),
                    "generation_prompt": scene.get("generation_prompt"),
                    "background_id": scene.get("background_id"),
                    "reference_paths": scene.get("reference_paths"),
                }
            )

    audit_issues = audit(registry, segment_checks)
    all_issues.extend(audit_issues)

    print("=== Apply Director Generation Prompts EP01 ===")
    print(f"Background groups with generation_prompt: {sum(1 for loc in registry['locations'].values() if (loc.get('image_generation') or {}).get('generation_prompt'))}")
    print(f"Cave toward mouth added: {'LOC_EP01_COASTAL_CAVE_TOWARD_MOUTH' in registry['locations']}")
    print(f"Clips updated: {clip_count}")
    print(f"Segments processed: {len(segment_checks)}")
    print(f"Audit issues: {len(all_issues)}")
    if all_issues:
        for issue in all_issues[:30]:
            print(f"  - {issue}")
        if len(all_issues) > 30:
            print(f"  ... and {len(all_issues) - 30} more")
        return 1

    # samples
    sample_bg = BACKGROUND_IMAGE_GENERATION["LOC_EP01_COASTAL_CAVE_TOWARD_MOUTH"]["generation_prompt"]
    sample_keys = [("SC01-001_01", "SEG01"), ("SC01-003_09", "SEG04")]
    print("\n--- Sample background prompt ---")
    print(sample_bg[:400] + "...")
    print("\n--- Sample segment prompts ---")
    for key in sample_keys:
        beat = SEGMENT_BEATS[key]
        gp = build_generation_prompt(beat)
        print(f"{key[0]}/{key[1]} ({len(gp.split())} words):")
        print(gp[:350] + "...")
        print()

    print("Files written:")
    print(f"  - {REGISTRY_PATH}")
    print(f"  - {PROJECT_DIR}/**/*.md ({clip_count} clips)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
