from __future__ import annotations

"""Audit EP00 V2 described-object behavior project V5."""

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_reader_action_v2_described_object_behavior_project as build  # noqa: E402
from scripts import build_ep00_reader_action_v2_clean_bgfx_dialogue_project as clean  # noqa: E402
from scripts.ep00_reader_action_v2_project_data import CLIPS, DIALOGUE_LOCK  # noqa: E402


OBJECT_TAG_RE = re.compile(r"<(Subject|Picture) (\d+)>\s+the\s+", re.IGNORECASE)


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
            assert not any(
                label in prompt
                for label in ("Starting state:", "Starting composition:", "Following action:", "Behavior:")
            )
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
                    assert segment.endswith(".") or "<d>[Korean]" in segment
                    if tag.group(1).lower() == "subject":
                        subject_id = int(tag.group(2))
                        expected_description = build.DESCRIPTIONS[subject_id].removeprefix("the ")
                        assert segment.lower().startswith(expected_description.lower())

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
        "object_order": "tag -> short description -> current state -> same object's behavior",
        "all_descriptions_grouped_before_actions": False,
        "comma_or_colon_immediately_after_object_tag": False,
        "state_action_behavior_labels_used": False,
        "storyboard_picture_count": 0,
        "total_script_line_count": 11,
        "script_line_occurrences_across_A_D_E": sum(occurrences.values()),
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    review = build.SOURCE_DIR / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "EP00_V2_DESCRIBED_OBJECT_BEHAVIOR_AUDIT_V5.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (review / "EP00_V2_DESCRIBED_OBJECT_BEHAVIOR_AUDIT_V5.md").write_text(
        "# EP00 V2 Described Object State and Behavior Audit V5\n\n"
        "- Result: PASS\n"
        "- New project: 28 clips / 84 prompts / 336 Shots\n"
        "- Each object unit follows tag, short description, current state, and that object's behavior\n"
        "- One object unit finishes before the next object begins\n"
        "- No comma or colon immediately after an object tag and no State/Action/Behavior label\n"
        "- Object descriptions are not grouped separately from actions\n"
        "- Background and effect assets remain object-specific units\n"
        "- No storyboard Picture; all eleven script lines are preserved\n"
        "- Queue registration and video generation were not performed\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
