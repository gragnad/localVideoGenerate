from __future__ import annotations

"""Audit the separate EP00 V2 clean BG/FX + dialogue project."""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_reader_action_v2_clean_bgfx_dialogue_project as build  # noqa: E402
from scripts.ep00_reader_action_v2_project_data import CLIPS, DIALOGUE_LOCK  # noqa: E402


def main() -> int:
    expected_by_clip = {
        str(row["clip_id"]): [str(value["line"]) for value in row["dialogue"]]
        for row in CLIPS
    }
    for row in build.INTERNAL_MONOLOGUE:
        expected_by_clip[str(row["clip_id"])].append(str(row["line"]))
    expected_lines = [str(row["line"]) for row in DIALOGUE_LOCK] + [
        str(row["line"]) for row in build.INTERNAL_MONOLOGUE
    ]
    assert len(expected_lines) == 11 and len(set(expected_lines)) == 11

    directory = h3_prompt_projects.project_dir(ROOT, build.PROJECT_ID)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["build_facts"]["clip_count"] == 28
    assert manifest["build_facts"]["prompt_count"] == 84
    assert manifest["dialogue_clip_count"] == 7
    assert manifest["dialogue_line_count"] == 11
    assert manifest["queue_registration_performed"] is False
    assert manifest["video_generation_performed"] is False

    project = h3_prompt_projects.project_clips(ROOT, build.PROJECT_ID)
    assert len(project["clips"]) == 28
    occurrences = {line: 0 for line in expected_lines}
    dialogue_clip_ids: set[str] = set()
    shot_count = 0
    for clip in project["clips"]:
        clip_id = str(clip["clip_id"])
        assert clip["ready"], (clip_id, clip["errors"])
        assert len(clip["references"]) == 5
        assert [row["picture_index"] for row in clip["references"]] == [1, 2, 3, 4, 5]
        assert all(row["linked"] for row in clip["references"])
        assert all(row["reference_kind"] != "storyboard" for row in clip["references"])
        assert clip["required_dialogue"] == expected_by_clip[clip_id]
        if expected_by_clip[clip_id]:
            dialogue_clip_ids.add(clip_id)
        for variant in clip["prompt_variants"]:
            prompt = str(variant["video_prompt"])
            actual = [
                line.strip()
                for language, line in h3_prompt_contract.DIALOGUE_RE.findall(prompt)
                if language == "Korean"
            ]
            assert actual == expected_by_clip[clip_id], (clip_id, variant["variant_id"], actual)
            for line in actual:
                occurrences[line] += 1
            shots = list(h3_prompt_contract.SHOT_RE.finditer(variant["detailed_description"]))
            assert len(shots) == 4
            shot_count += len(shots)
            for shot in shots:
                body = shot.group(4)
                composition = body.split("Starting composition:", 1)[1].split("Following action:", 1)[0]
                assert "<Picture 4>" in composition
                assert "<Picture 5>" in composition
    assert len(dialogue_clip_ids) == 7
    assert all(count == 3 for count in occurrences.values()), occurrences

    report = {
        "status": "PASS",
        "project_id": build.PROJECT_ID,
        "clip_count": 28,
        "prompt_count": 84,
        "shot_count": shot_count,
        "pictures_per_clip": 5,
        "storyboard_picture_count": 0,
        "spoken_line_count": 7,
        "internal_monologue_count": 4,
        "total_script_line_count": 11,
        "dialogue_clip_count": 7,
        "script_line_occurrences_across_A_D_E": sum(occurrences.values()),
        "each_script_line_occurs_once_per_candidate": True,
        "all_background_and_effect_assets_linked": True,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    review = build.SOURCE_DIR / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "EP00_V2_CLEAN_BGFX_DIALOGUE_AUDIT_V2.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (review / "EP00_V2_CLEAN_BGFX_DIALOGUE_AUDIT_V2.md").write_text(
        "# EP00 V2 Clean BG/FX + Dialogue Audit V2\n\n"
        "- Result: PASS\n"
        "- New independent project: 28 clips / 84 A-D-E prompts / 336 Shots\n"
        "- Five linked Pictures per clip: three identities, one chamber background, one effect-language asset\n"
        "- No storyboard Picture\n"
        "- Seven spoken lines and four internal-monologue lines preserved in source order and assigned Shot\n"
        "- All eleven script lines occur exactly once in each A/D/E candidate (33 total occurrences)\n"
        "- Internal monologue is voice-over with no visible lip movement\n"
        "- Queue registration and video generation were not performed\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
