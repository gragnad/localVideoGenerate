from __future__ import annotations

"""Audit EP00 V2 per-object state and behavior project V4."""

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_reader_action_v2_object_behavior_project as build  # noqa: E402
from scripts import build_ep00_reader_action_v2_clean_bgfx_dialogue_project as clean  # noqa: E402
from scripts.ep00_reader_action_v2_project_data import CLIPS, DIALOGUE_LOCK  # noqa: E402


OBJECT_TAG_RE = re.compile(r"<(Subject|Picture) (\d+)>\s+(?!\()")


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
    object_units = 0
    for clip in project["clips"]:
        clip_id = str(clip["clip_id"])
        assert clip["ready"], (clip_id, clip["errors"])
        assert all(row["reference_kind"] != "storyboard" for row in clip["references"])
        assert all(row["linked"] for row in clip["references"])
        contract = clip["action_scene_contract"]
        assert contract["storyboard_mode"] == build.MODE
        background_id = int(contract["background_picture_id"])
        effect_id = int(contract["effect_picture_id"])
        assert clip["required_dialogue"] == expected_by_clip[clip_id]

        for variant in clip["prompt_variants"]:
            prompt = str(variant["video_prompt"])
            assert "Starting state:" not in prompt
            assert "Starting composition:" not in prompt
            assert "Following action:" not in prompt
            assert "Behavior:" not in prompt
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
                assert body.startswith(("<Subject ", "<Picture "))
                assert f"<Picture {background_id}>" in body
                assert f"<Picture {effect_id}>" in body
                assert ".." not in body
                tags = list(OBJECT_TAG_RE.finditer(body))
                assert tags
                object_units += len(tags)
                for index, tag in enumerate(tags):
                    end = tags[index + 1].start() if index + 1 < len(tags) else len(body)
                    segment = body[tag.end():end].strip()
                    assert segment
                    assert not re.match(r"^[,:;\-]", segment)
                    assert not segment.startswith(("the injured young", "the towering connected", "the single weathered"))
                    assert segment.endswith(".") or "<d>[Korean]" in segment

    assert len(project["clips"]) == 28
    assert total_shots == 336
    assert all(value == 3 for value in occurrences.values()), occurrences
    report = {
        "status": "PASS",
        "project_id": build.PROJECT_ID,
        "clip_count": 28,
        "prompt_count": 84,
        "shot_count": total_shots,
        "object_unit_count": object_units,
        "shot_format": "Object tag -> that object's state and behavior -> next object tag",
        "comma_or_colon_immediately_after_object_tag": False,
        "identity_description_repeated_in_shots": False,
        "shared_starting_state_or_action_block": False,
        "storyboard_picture_count": 0,
        "total_script_line_count": 11,
        "script_line_occurrences_across_A_D_E": sum(occurrences.values()),
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    review = build.SOURCE_DIR / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "EP00_V2_OBJECT_BEHAVIOR_AUDIT_V4.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (review / "EP00_V2_OBJECT_BEHAVIOR_AUDIT_V4.md").write_text(
        "# EP00 V2 Object State and Behavior Audit V4\n\n"
        "- Result: PASS\n"
        "- New project: 28 clips / 84 prompts / 336 Shots\n"
        "- Each object tag is immediately followed by that object's state and behavior\n"
        "- No comma, colon, dash, identity re-description, or Behavior label follows an object tag\n"
        "- One object unit finishes before the next object tag begins\n"
        "- Background and effect Pictures also carry their own state/behavior\n"
        "- No shared Starting-state or Action block and no storyboard Picture\n"
        "- Seven spoken lines and four internal-monologue lines are preserved\n"
        "- Queue registration and video generation were not performed\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
