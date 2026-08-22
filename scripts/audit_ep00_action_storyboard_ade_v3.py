from __future__ import annotations

"""Fail-closed audit for the separated EP00 action prompt project."""

import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_projects


ACTION_PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_ACTION_STORYBOARD_ADE_V3"
STORY_PROJECT_ID = "RaisingaDragonSeason01_EP01_H3_R2V_STORYBOARD_ADE_V3"
OLD_PROJECT_ID = "RaisingaDragonSeason01_EP00_EP01_H3_R2V_STORYBOARD_ADE_V2"


def payloads(project_id: str) -> list[dict[str, Any]]:
    directory = h3_prompt_projects.project_dir(ROOT, project_id)
    return [
        h3_prompt_projects.extract_payload(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*/*.md"))
    ]


def main() -> int:
    action_manifest = h3_prompt_projects.project_manifest(ROOT, ACTION_PROJECT_ID)
    story_manifest = h3_prompt_projects.project_manifest(ROOT, STORY_PROJECT_ID)
    old_manifest = h3_prompt_projects.project_manifest(ROOT, OLD_PROJECT_ID)
    action_clips = payloads(ACTION_PROJECT_ID)
    story_clips = payloads(STORY_PROJECT_ID)
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append((name, bool(passed), detail))

    variants = [
        (clip, variant)
        for clip in action_clips
        for variant in clip.get("prompt_variants") or []
    ]
    check(
        "separated_counts",
        len(action_clips) == 14 and len(story_clips) == 42 and len(variants) == 42,
        f"EP00={len(action_clips)}, EP01={len(story_clips)}, EP00 prompts={len(variants)}",
    )
    check(
        "action_manifest_route",
        action_manifest.get("prompt_profile") == h3_prompt_projects.ACTION_PROMPT_PROFILE
        and action_manifest.get("prompt_generator") == h3_prompt_projects.ACTION_PROMPT_GENERATOR
        and action_manifest.get("generation_blocked") is False,
        "EP00 manifest uses the dedicated action route",
    )
    check(
        "all_action_clips_routed",
        all(not h3_prompt_projects.action_scene_routing_errors(clip) for clip in action_clips),
        "14/14 clips satisfy action_scene_contract_v1",
    )
    check(
        "action_contract_shape",
        all(
            len((clip.get("action_scene_contract") or {}).get("speed_profiles") or []) == 4
            and len((clip.get("action_scene_contract") or {}).get("motion_links") or []) == 3
            and str((clip.get("action_scene_contract") or {}).get("environmental_proof") or "").strip()
            for clip in action_clips
        ),
        "every clip has four speed profiles, three motion links, and environmental proof",
    )
    check(
        "prompt_length",
        all(len(str(variant.get("video_prompt") or "")) <= 7000 for _clip, variant in variants),
        f"max={max(len(str(variant.get('video_prompt') or '')) for _clip, variant in variants)}",
    )
    check(
        "four_action_timings",
        all(str(variant.get("video_prompt") or "").count("Action timing:") == 4 for _clip, variant in variants),
        "each A/D/E prompt has one action timing per Shot",
    )
    forbidden = re.compile(
        r"Keep the camera static|truck slowly|push slowly|slow short arc|then settle|single-frame composition",
        re.IGNORECASE,
    )
    check(
        "no_generic_ep01_camera_template",
        all(not forbidden.search(str(variant.get("video_prompt") or "")) for _clip, variant in variants),
        "old static/slow/settle templates absent",
    )
    forbidden_grid = re.compile(
        r"\b(?:2x2|grid|quadrant|top-left|top-right|bottom-left|bottom-right|panel)\b",
        re.IGNORECASE,
    )
    check(
        "shot_text_grid_free",
        all(
            not forbidden_grid.search(
                h3_prompt_projects.extract_detailed_description(
                    str(variant.get("video_prompt") or "")
                )
            )
            for _clip, variant in variants
        ),
        "planning layout vocabulary remains outside detailed Shot text",
    )
    check(
        "partial_storyboard_retention",
        all(
            re.search(r"<Picture \d+> \(appears in .*\): partially_preserved", str(clip.get("video_prompt") or ""))
            for clip in action_clips
        ),
        "storyboards are planning references, not fully preserved footage",
    )
    check(
        "project_ready",
        all(
            clip.get("ready")
            for clip in h3_prompt_projects.project_clips(ROOT, ACTION_PROJECT_ID)["clips"]
        ),
        "14/14 action clips pass H3 loading and contract validation",
    )
    check(
        "ep01_general_route",
        story_manifest.get("prompt_profile") == "h3_storyboard_scene_v1"
        and story_manifest.get("prompt_generator") == "h3_storyboard_prompt_generator_v1"
        and all(clip.get("scene_type") == "narrative" for clip in story_clips),
        "EP01 remains on its separate narrative route",
    )
    check(
        "old_combined_blocked",
        old_manifest.get("generation_blocked") is True
        and old_manifest.get("replacement_project_ids")
        == [ACTION_PROJECT_ID, STORY_PROJECT_ID],
        "old combined project is read-only and points to both replacements",
    )
    check(
        "no_generation_side_effect",
        action_manifest.get("queue_registration_performed") is False
        and action_manifest.get("video_generation_performed") is False
        and story_manifest.get("queue_registration_performed") is False
        and story_manifest.get("video_generation_performed") is False,
        "project build did not queue or render video",
    )

    report = {
        "passed": all(passed for _name, passed, _detail in checks),
        "passed_count": sum(1 for _name, passed, _detail in checks if passed),
        "check_count": len(checks),
        "checks": [
            {"name": name, "passed": passed, "detail": detail}
            for name, passed, detail in checks
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
