from __future__ import annotations

"""Audit the independent EP00 reader-action V2 project without queuing video."""

import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_reader_action_v2_new_project as build  # noqa: E402
from scripts.ep00_reader_action_v2_project_data import CLIPS, DIALOGUE_LOCK  # noqa: E402


BANNED = (
    "Action timing:",
    "next panel",
    "next Shot",
    "cut to Shot",
    "transition to the next",
    "LuaSpear",
    "AbyssKing",
    "EP00V2-",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"not PNG: {path}")
    return struct.unpack(">II", data[16:24])


def section(prompt: str, name: str, next_name: str) -> str:
    return prompt.split(f"\n\n{name}:\n", 1)[1].split(f"\n\n{next_name}:\n", 1)[0]


def main() -> int:
    source = build.SOURCE_DIR / "EP00_READER_SCREENPLAY_ACTION_REVISION_V2.md"
    assert digest(source) == build.SOURCE_SHA256
    assert len(CLIPS) == 28
    assert sum(len(row["panels"]) for row in CLIPS) == 112
    assert len(DIALOGUE_LOCK) == 7

    inventory_path = build.SOURCE_DIR / "EP00_V2_STORYBOARD_INVENTORY_V1.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert inventory["count"] == 28
    expected_files = {
        str(clip["clip_id"]): build.SOURCE_DIR / "storyboards" / (
            str(clip["clip_id"]).replace("-", "_") + "_STORYBOARD_V1.png"
        )
        for clip in CLIPS
    }
    for item in inventory["items"]:
        path = expected_files[str(item["clip_id"])]
        assert path.is_file()
        assert digest(path) == item["sha256"]
        width, height = png_size(path)
        assert width == 1672 and height in {940, 941}
        assert path.stat().st_size > 1_000_000

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

    expected_by_clip = {
        str(clip["clip_id"]): [str(row["line"]) for row in clip["dialogue"]]
        for clip in CLIPS
    }
    source_by_clip = {str(clip["clip_id"]): clip for clip in CLIPS}
    project = h3_prompt_projects.project_clips(ROOT, build.PROJECT_ID)
    clips = list(project["clips"])
    assert len(clips) == 28

    dialogue_occurrences = 0
    word_max = 0
    for clip in clips:
        clip_id = str(clip["clip_id"])
        source_clip = source_by_clip[clip_id]
        assert clip["ready"], (clip_id, clip["errors"])
        assert clip["required_dialogue"] == expected_by_clip[clip_id]
        assert clip["storyboard_review_contract"]["storyboard_shots"] == [1, 2, 3, 4]
        assert clip["storyboard_review_contract"]["model_delegated_shots"] == []
        assert len(clip["references"]) == 4
        picture4 = next(row for row in clip["references"] if row["picture_index"] == 4)
        project_board = directory / str(picture4["source_path"])
        assert digest(project_board) == digest(expected_files[clip_id])

        variants = clip["prompt_variants"]
        assert [row["variant_id"] for row in variants] == ["A", "D", "E"]
        bodies_by_variant: list[list[str]] = []
        starts_by_variant: list[tuple[float | None, ...]] = []
        for variant in variants:
            prompt = str(variant["video_prompt"])
            lower = prompt.lower()
            assert not any(value.lower() in lower for value in BANNED), clip_id
            assert lower.count("2x2") == 1
            actual_dialogue = [
                line.strip()
                for language, line in h3_prompt_contract.DIALOGUE_RE.findall(prompt)
                if language == "Korean"
            ]
            assert actual_dialogue == expected_by_clip[clip_id]
            dialogue_occurrences += len(actual_dialogue)
            summary = section(prompt, "summary", "retention_analysis")
            assert summary.removeprefix("[reference generation] ") == source_clip["summary"]

            matches = list(h3_prompt_contract.SHOT_RE.finditer(variant["detailed_description"]))
            assert len(matches) == 4
            bodies = [match.group(4).strip() for match in matches]
            starts = tuple(
                None if match.group(2) is None else int(match.group(2)) * 60 + float(match.group(3))
                for match in matches
            )
            assert starts[0] is None
            assert list(starts[1:]) == sorted(starts[1:])
            for index, (body, position) in enumerate(zip(bodies, build.POSITIONS, strict=True), start=1):
                assert f"<Picture 4>" in body
                assert position in body
                assert "2x2" not in body.lower()
                assert "grid" not in body.lower()
                assert "panel" not in body.lower()
                count = len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", body))
                word_max = max(word_max, count)
                assert count <= 90, (clip_id, index, count)
            assert all(tag in bodies[0] for tag in ("<Subject 1>", "<Subject 2>", "<Subject 3>"))
            bodies_by_variant.append(bodies)
            starts_by_variant.append(starts)
        assert bodies_by_variant[0] == bodies_by_variant[1] == bodies_by_variant[2]
        assert len(set(starts_by_variant)) == 3

    assert dialogue_occurrences == 21
    result: dict[str, Any] = {
        "status": "PASS",
        "project_id": build.PROJECT_ID,
        "source_sha256": build.SOURCE_SHA256,
        "clip_count": 28,
        "storyboard_count": 28,
        "panel_count": 112,
        "prompt_count": 84,
        "dialogue_clip_count": 4,
        "dialogue_line_count": 7,
        "dialogue_occurrences_across_A_D_E": dialogue_occurrences,
        "max_shot_english_word_count": word_max,
        "a_d_e_actions_identical_timing_only": True,
        "storyboard_copy_hash_match": True,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    report_json = build.SOURCE_DIR / "review" / "EP00_V2_PROJECT_AUDIT_V1.json"
    report_md = build.SOURCE_DIR / "review" / "EP00_V2_PROJECT_AUDIT_V1.md"
    report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_md.write_text(
        "# EP00 Reader Action V2 Project Audit V1\n\n"
        "- Result: PASS\n"
        "- 28 clips / 28 storyboards / 112 panels / 84 A-D-E prompts\n"
        "- Seven canonical dialogue lines preserved once per candidate (21 total occurrences)\n"
        "- Four storyboard panels map one-to-one to four timed Shots; no delegated entry or exit Shot\n"
        "- A/D/E use identical Shot actions and dialogue; only Shot start times differ\n"
        "- No Action timing field, next-panel instruction, internal clip ID, LuaSpear, or AbyssKing token in model prompts\n"
        "- Queue registration and video generation were not performed\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
