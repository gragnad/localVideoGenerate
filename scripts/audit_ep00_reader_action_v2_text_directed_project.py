from __future__ import annotations

"""Audit the non-storyboard EP00 V2 text-directed project."""

import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_reader_action_v2_text_directed_project as build  # noqa: E402
from scripts.ep00_reader_action_v2_project_data import CLIPS, DIALOGUE_LOCK  # noqa: E402


BANNED = (
    "Action timing:",
    "2x2",
    "grid",
    "panel",
    "next Shot",
    "next panel",
    "LuaSpear",
    "AbyssKing",
    "EP00V2-",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def section(prompt: str, name: str, next_name: str) -> str:
    return prompt.split(f"\n\n{name}:\n", 1)[1].split(f"\n\n{next_name}:\n", 1)[0]


def action_part(body: str) -> str:
    value = body.split("Following action:", 1)[1].strip()
    return value.split(" End on the resulting physical state", 1)[0].strip()


def main() -> int:
    source = build.SOURCE_DIR / "EP00_READER_SCREENPLAY_ACTION_REVISION_V2.md"
    assert digest(source) == build.SOURCE_SHA256
    assert len(CLIPS) == 28 and len(DIALOGUE_LOCK) == 7
    background_source = (
        build.SOURCE_DIR
        / "../rebuild_v2/action_moment_test_v1/images/HEARTSTONE_CHAMBER_ENVIRONMENT_V1.png"
    ).resolve()
    effect_source = (build.SOURCE_DIR / "../Dragon_Language_Current_Shield_Effects.png").resolve()
    assert background_source.is_file() and effect_source.is_file()

    directory = h3_prompt_projects.project_dir(ROOT, build.PROJECT_ID)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["build_facts"]["clip_count"] == 28
    assert manifest["build_facts"]["prompt_count"] == 84
    assert manifest["dialogue_clip_count"] == 4
    assert manifest["dialogue_line_count"] == 7
    assert manifest["queue_authorized"] is False
    assert manifest["video_generation_authorized"] is False
    assert manifest["queue_registration_performed"] is False
    assert manifest["video_generation_performed"] is False

    source_by_clip = {str(row["clip_id"]): row for row in CLIPS}
    project = h3_prompt_projects.project_clips(ROOT, build.PROJECT_ID)
    clips = list(project["clips"])
    assert len(clips) == 28
    dialogue_occurrences = 0
    maximum_shot_words = 0
    for clip in clips:
        clip_id = str(clip["clip_id"])
        source_clip = source_by_clip[clip_id]
        expected_dialogue = [str(row["line"]) for row in source_clip["dialogue"]]
        assert clip["ready"], (clip_id, clip["errors"])
        assert clip["required_dialogue"] == expected_dialogue
        assert len(clip["references"]) == 5
        assert all(row["reference_kind"] != "storyboard" for row in clip["references"])
        assert [row["picture_index"] for row in clip["references"]] == [1, 2, 3, 4, 5]
        assert clip["references"][3]["role"] == "heartstone_chamber_environment"
        assert clip["references"][4]["role"] == "ep00_cyan_current_and_shield_effect_language"
        assert digest(directory / clip["references"][3]["source_path"]) == digest(background_source)
        assert digest(directory / clip["references"][4]["source_path"]) == digest(effect_source)
        assert clip["action_requirements"]["storyboard_picture_used"] is False
        assert clip["action_requirements"]["background_picture_id"] == 4
        assert clip["action_requirements"]["effect_picture_id"] == 5
        assert clip["action_requirements"]["background_and_effect_assets_required"] is True
        assert clip["action_requirements"]["delegated_shots"] == []

        variants = clip["prompt_variants"]
        assert [row["variant_id"] for row in variants] == ["A", "D", "E"]
        actions_by_variant: list[list[str]] = []
        starts_by_variant: list[tuple[float | None, ...]] = []
        compositions_by_variant: list[list[str]] = []
        for variant in variants:
            prompt = str(variant["video_prompt"])
            lower = prompt.lower()
            assert not any(value.lower() in lower for value in BANNED), (clip_id, variant["variant_id"])
            actual_dialogue = [
                line.strip()
                for language, line in h3_prompt_contract.DIALOGUE_RE.findall(prompt)
                if language == "Korean"
            ]
            assert actual_dialogue == expected_dialogue
            dialogue_occurrences += len(actual_dialogue)
            summary = section(prompt, "summary", "retention_analysis")
            assert summary.removeprefix("[reference generation] ") == source_clip["summary"]
            assert prompt.count("<Picture 4>") >= 5
            assert prompt.count("<Picture 5>") >= 5
            assert "the Heartstone altar chamber environment" in prompt
            assert "the approved cyan current and shield effect language" in prompt

            shots = list(h3_prompt_contract.SHOT_RE.finditer(variant["detailed_description"]))
            assert len(shots) == 4
            bodies = [shot.group(4).strip() for shot in shots]
            starts = tuple(
                None if shot.group(2) is None else int(shot.group(2)) * 60 + float(shot.group(3))
                for shot in shots
            )
            assert starts[0] is None and list(starts[1:]) == sorted(starts[1:])
            compositions: list[str] = []
            actions: list[str] = []
            for number, body in enumerate(bodies, start=1):
                assert body.count("Starting composition:") == 1
                assert body.count("Following action:") == 1
                composition = body.split("Starting composition:", 1)[1].split("Following action:", 1)[0].strip()
                action = action_part(body)
                assert "<Picture 4>" in composition
                assert "<Picture 5>" in composition
                assert "only for an effect explicitly named in this Shot" in composition
                assert "do not add an unrequested effect" in composition
                composition_context = composition.split(". ", 1)[0]
                action_context = action.split(". ", 1)[0]
                composition_subjects = {
                    int(value) for value in re.findall(r"<Subject (\d+)>", composition_context)
                }
                action_subjects = {
                    int(value) for value in re.findall(r"<Subject (\d+)>", action_context)
                }
                assert composition_subjects
                assert composition_subjects == action_subjects
                for subject_id in composition_subjects:
                    brief = build.SUBJECT_BRIEFS[subject_id]
                    assert brief in composition_context
                    assert brief in action_context
                assert len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", composition)) >= 6
                assert len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", action)) >= 4
                word_count = len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", body))
                maximum_shot_words = max(maximum_shot_words, word_count)
                assert word_count <= 145, (clip_id, variant["variant_id"], number, word_count)
                compositions.append(composition)
                actions.append(action)
            compositions_by_variant.append(compositions)
            actions_by_variant.append(actions)
            starts_by_variant.append(starts)

        assert actions_by_variant[0] == actions_by_variant[1] == actions_by_variant[2]
        assert compositions_by_variant[0] != compositions_by_variant[1]
        assert compositions_by_variant[0] != compositions_by_variant[2]
        assert all("oblique or low viewpoint" in value for value in compositions_by_variant[1])
        assert all("foreground depth and compressed perspective" in value for value in compositions_by_variant[2])
        assert len(set(starts_by_variant)) == 3

    assert dialogue_occurrences == 21

    # Adding the text-directed mode must not make the adjacent storyboard
    # project unreadable.
    storyboard_project = h3_prompt_projects.project_clips(
        ROOT,
        "RaisingaDragonSeason01_EP00_READER_ACTION_V2_H3_R2V_STORYBOARD_ADE_V1",
    )
    assert len(storyboard_project["clips"]) == 28
    assert all(row["ready"] for row in storyboard_project["clips"])

    result: dict[str, Any] = {
        "status": "PASS",
        "project_id": build.PROJECT_ID,
        "source_sha256": build.SOURCE_SHA256,
        "clip_count": 28,
        "prompt_count": 84,
        "reference_pictures_per_clip": 5,
        "storyboard_picture_count": 0,
        "mandatory_background_picture_id": 4,
        "mandatory_effect_picture_id": 5,
        "background_and_effect_asset_copies": 56,
        "shots_with_background_and_effect_links": 336,
        "shot_count_per_prompt": 4,
        "starting_composition_count_per_prompt": 4,
        "following_action_count_per_prompt": 4,
        "dialogue_clip_count": 4,
        "dialogue_line_count": 7,
        "dialogue_occurrences_across_A_D_E": dialogue_occurrences,
        "candidate_A": "neutral readable composition",
        "candidate_D": "oblique or low viewpoint",
        "candidate_E": "foreground depth and compressed perspective",
        "actions_and_dialogue_identical_across_A_D_E": True,
        "maximum_shot_english_word_count": maximum_shot_words,
        "adjacent_storyboard_project_regression_check": "PASS",
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    report_json = build.SOURCE_DIR / "review" / "EP00_V2_TEXT_DIRECTED_AUDIT_V1.json"
    report_md = build.SOURCE_DIR / "review" / "EP00_V2_TEXT_DIRECTED_AUDIT_V1.md"
    report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_md.write_text(
        "# EP00 Reader Action V2 Text-Directed Audit V1\n\n"
        "- Result: PASS\n"
        "- 28 clips / 84 A-D-E prompts / four timed Shots per prompt\n"
        "- No storyboard Picture is attached; Pictures 1-3 hold identities, Picture 4 fixes the chamber background, and Picture 5 fixes the approved effect language\n"
        "- Picture 4 and Picture 5 are explicitly linked in all 336 Shots across A/D/E; Picture 5 produces only an effect explicitly named by that Shot\n"
        "- Every Shot contains one substantive Starting composition and one Following action\n"
        "- A is neutral, D uses oblique or low viewpoints, and E uses foreground depth with compressed perspective\n"
        "- Actions and seven canonical dialogue lines stay identical across A/D/E\n"
        "- No Action timing field, grid/panel instruction, internal clip ID, LuaSpear, or AbyssKing token appears in model prompts\n"
        "- The adjacent storyboard project still loads all 28 clips as ready\n"
        "- Queue registration and video generation were not performed\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
