#!/usr/bin/env python3
from __future__ import annotations

"""Post-assembly audit for the EP00 cinematic live-action R2V V2 project."""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_projects  # noqa: E402
from scripts import import_ep00_cinematic_liveaction_h3_r2v_v2 as builder  # noqa: E402


def main() -> int:
    project = h3_prompt_projects.project_dir(ROOT, builder.PROJECT_ID)
    report_path = project / "PROMPT_VALIDATION_REPORT.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    source_rows = {str(row["clip_id"]): row for row in builder.prompt_rows()}
    project_data = h3_prompt_projects.project_clips(ROOT, builder.PROJECT_ID)
    clips = project_data["clips"]
    errors: list[str] = []
    reference_count = 0
    linked_count = 0
    for clip in clips:
        clip_id = str(clip["clip_id"])
        source = source_rows.get(clip_id)
        if not source:
            errors.append(f"unknown clip: {clip_id}")
            continue
        if not clip.get("ready"):
            errors.append(f"not ready: {clip_id}: {clip.get('errors')}")
        if str(clip.get("video_prompt") or "") != str(source["video_prompt"]):
            errors.append(f"source prompt mismatch: {clip_id}")
        variants = clip.get("prompt_variants") or []
        if len(variants) != 3 or [row.get("variant_id") for row in variants] != ["A", "D", "E"]:
            errors.append(f"candidate set mismatch: {clip_id}")
        if any(str(row.get("video_prompt") or "") != str(source["video_prompt"]) for row in variants):
            errors.append(f"candidate text mismatch: {clip_id}")
        expected_names = list(source["asset_names"])
        references = clip.get("references") or []
        reference_count += len(references)
        linked_count += sum(bool(row.get("linked")) for row in references)
        actual_names = [Path(str(row.get("source_path") or "")).name for row in references]
        if actual_names != expected_names:
            errors.append(f"Picture order mismatch: {clip_id}")
        if [int(row.get("picture_index") or 0) for row in references] != list(range(1, len(references) + 1)):
            errors.append(f"Picture index mismatch: {clip_id}")

    asset_hash_matches = 0
    for name, source_path in builder.ASSET_PATHS.items():
        copied = project / "assets/shared" / name
        if not copied.is_file():
            errors.append(f"missing copied asset: {name}")
            continue
        if builder.digest_bytes(source_path) != builder.digest_bytes(copied):
            errors.append(f"asset hash mismatch: {name}")
            continue
        asset_hash_matches += 1

    manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))
    block_reason = h3_prompt_projects.project_generation_block_reason(ROOT, builder.PROJECT_ID)
    if block_reason:
        errors.append(f"unexpected generation block: {block_reason}")
    if manifest.get("queue_registration_performed") or manifest.get("video_generation_performed"):
        errors.append("queue or video generation was unexpectedly performed")

    postassembly = {
        "valid": not errors,
        "project_clips_count": len(clips),
        "ready_clip_count": sum(bool(clip.get("ready")) for clip in clips),
        "scene_count": len(project_data["scenes"]),
        "total_duration_seconds": round(sum(float(clip.get("duration_seconds") or 0) for clip in clips), 3),
        "reference_count": reference_count,
        "linked_reference_count": linked_count,
        "asset_copy_count": len(builder.ASSET_PATHS),
        "asset_sha256_match_count": asset_hash_matches,
        "prompt_source_match_count": sum(str(clip.get("video_prompt") or "") == str(source_rows[str(clip["clip_id"])]["video_prompt"]) for clip in clips),
        "candidate_a_d_e_exact_match_clip_count": sum(
            len(clip.get("prompt_variants") or []) == 3
            and all(str(row.get("video_prompt") or "") == str(source_rows[str(clip["clip_id"])]["video_prompt"]) for row in clip.get("prompt_variants") or [])
            for clip in clips
        ),
        "project_generation_block_reason": block_reason,
        "queue_registration_performed": bool(manifest.get("queue_registration_performed")),
        "video_generation_performed": bool(manifest.get("video_generation_performed")),
        "errors": errors,
    }
    report["postassembly_audit"] = postassembly
    report["valid"] = bool(report.get("valid")) and postassembly["valid"]
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(postassembly, ensure_ascii=False, indent=2))
    return 0 if postassembly["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
