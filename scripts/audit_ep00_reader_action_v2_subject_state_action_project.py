from __future__ import annotations

"""Audit EP00 V2 Subject → State → Action project V3."""

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_reader_action_v2_subject_state_action_project as build  # noqa: E402
from scripts import build_ep00_reader_action_v2_clean_bgfx_dialogue_project as clean  # noqa: E402
from scripts.ep00_reader_action_v2_project_data import CLIPS, DIALOGUE_LOCK  # noqa: E402


def main() -> int:
    expected_by_clip = {
        str(clip["clip_id"]): [str(row["line"]) for row in clip["dialogue"]]
        for clip in CLIPS
    }
    for row in clean.INTERNAL_MONOLOGUE:
        expected_by_clip[str(row["clip_id"])].append(str(row["line"]))
    all_lines = [str(row["line"]) for row in DIALOGUE_LOCK] + [
        str(row["line"]) for row in clean.INTERNAL_MONOLOGUE
    ]

    directory = h3_prompt_projects.project_dir(ROOT, build.PROJECT_ID)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["build_facts"]["clip_count"] == 28
    assert manifest["build_facts"]["prompt_count"] == 84
    assert manifest["dialogue_line_count"] == 11
    assert manifest["queue_registration_performed"] is False
    assert manifest["video_generation_performed"] is False

    project = h3_prompt_projects.project_clips(ROOT, build.PROJECT_ID)
    occurrences = {line: 0 for line in all_lines}
    total_shots = 0
    four_picture_clips = 0
    five_picture_clips = 0
    for clip in project["clips"]:
        clip_id = str(clip["clip_id"])
        assert clip["ready"], (clip_id, clip["errors"])
        assert all(row["reference_kind"] != "storyboard" for row in clip["references"])
        assert all(row["linked"] for row in clip["references"])
        assert len(clip["references"]) in (4, 5)
        four_picture_clips += len(clip["references"]) == 4
        five_picture_clips += len(clip["references"]) == 5
        contract = clip["action_scene_contract"]
        assert contract["storyboard_mode"] == build.MODE
        background_id = int(contract["background_picture_id"])
        effect_id = int(contract["effect_picture_id"])
        assert [background_id, effect_id] == [len(clip["references"]) - 1, len(clip["references"])]
        assert clip["required_dialogue"] == expected_by_clip[clip_id]

        for variant in clip["prompt_variants"]:
            prompt = str(variant["video_prompt"])
            assert "Starting composition:" not in prompt
            assert "Following action:" not in prompt
            assert "Continuity in:" not in prompt
            assert "End on the resulting physical state" not in prompt
            actual_dialogue = [
                line.strip()
                for language, line in h3_prompt_contract.DIALOGUE_RE.findall(prompt)
                if language == "Korean"
            ]
            assert actual_dialogue == expected_by_clip[clip_id]
            for line in actual_dialogue:
                occurrences[line] += 1
            shots = list(h3_prompt_contract.SHOT_RE.finditer(variant["detailed_description"]))
            assert len(shots) == 4
            total_shots += 4
            for shot_number, shot in enumerate(shots, start=1):
                body = shot.group(4).strip()
                assert body.startswith(("<Subject ", "<Picture ")), (clip_id, variant["variant_id"], shot_number)
                assert body.count("Starting state:") == 1
                assert body.count("Action:") == 1
                header, remainder = body.split("Starting state:", 1)
                state, action = remainder.split("Action:", 1)
                assert re.search(r"<(?:Subject|Picture) \d+>,\s+the\s+[^.;]+", header)
                assert f"<Picture {background_id}>" in header
                assert f"<Picture {effect_id}>" in header
                assert state.strip() and action.strip()
                assert not re.search(r"<Subject \d+>,\s+the\s+[^.;]+", action)
                for brief in build.SUBJECT_BRIEFS.values():
                    assert body.count(brief) <= 1

    assert len(project["clips"]) == 28
    assert four_picture_clips == 3 and five_picture_clips == 25
    assert total_shots == 336
    assert all(value == 3 for value in occurrences.values()), occurrences

    report = {
        "status": "PASS",
        "project_id": build.PROJECT_ID,
        "clip_count": 28,
        "prompt_count": 84,
        "shot_count": total_shots,
        "shot_order": "Relevant Subject/Picture tag + one short description -> Starting state -> Action -> assigned dialogue",
        "subject_description_repeated_in_action": False,
        "continuity_preamble_before_subject": False,
        "storyboard_picture_count": 0,
        "clips_with_four_relevant_pictures": four_picture_clips,
        "clips_with_five_relevant_pictures": five_picture_clips,
        "total_script_line_count": 11,
        "script_line_occurrences_across_A_D_E": sum(occurrences.values()),
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    review = build.SOURCE_DIR / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "EP00_V2_SUBJECT_STATE_ACTION_AUDIT_V3.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (review / "EP00_V2_SUBJECT_STATE_ACTION_AUDIT_V3.md").write_text(
        "# EP00 V2 Subject → State → Action Audit V3\n\n"
        "- Result: PASS\n"
        "- New project: 28 clips / 84 prompts / 336 Shots\n"
        "- Every Shot starts with a relevant Subject tag and one short description, or a relevant Picture tag when no Subject is visible\n"
        "- Starting state follows the Subject block; Action follows the state without repeating Subject descriptions\n"
        "- No continuity preamble appears before the Subject tag\n"
        "- Background and conditional effect assets are linked in every clip; unused spear assets are omitted from three clips\n"
        "- No storyboard Picture is used\n"
        "- Seven spoken lines and four internal-monologue lines are preserved (33 A/D/E occurrences)\n"
        "- Queue registration and video generation were not performed\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
