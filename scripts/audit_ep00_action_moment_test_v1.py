from __future__ import annotations

"""Audit the three-clip EP00 instantaneous action-keyshot test project."""

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_projects  # noqa: E402
import h3_prompt_contract  # noqa: E402


PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_ACTION_MOMENT_TEST_V1"
EXPECTED_CLIPS = ["EP00-TM01", "EP00-TM02", "EP00-TM03"]
EXPECTED_TIMES = {
    "A": [None, 1.5, 3.0, 4.5],
    "D": [None, 1.1, 2.3, 3.7],
    "E": [None, 0.8, 1.9, 3.1],
}
FORBIDDEN_OUTSIDE_BOARD_EVENTS = {
    "EP00-TM01": ("gripping the spear shaft", "hand closure on the shaft"),
    "EP00-TM02": ("right hand returning", "hands occupy both routes"),
    "EP00-TM03": ("spear out of reach", "sliding away", "distant spear slide"),
}
SUMMARY_REQUIRED = {
    "EP00-TM01": ("already pressed", "compresses", "restores its shape", "finishes the recoil"),
    "EP00-TM02": ("already touches", "shield and clothing tear", "completes a half-turn", "two fingers remain locked"),
    "EP00-TM03": ("already has its palm against", "scales flash white", "hits the wet floor", "leaves her hand"),
}
SUMMARY_FORBIDDEN = {
    "EP00-TM01": ("closes three steps", "thrusts once"),
    "EP00-TM02": ("runs for the briefly opened channel", "receives only a fingertip graze"),
    "EP00-TM03": ("spear out of reach",),
}
PROMPT_FORBIDDEN_PREBOARD = {
    "EP00-TM01": ("accelerating wet footfalls", "shaft acceleration", "follows the thrust"),
    "EP00-TM02": ("fast wet steps", "thin air cut", "stops on the graze"),
    "EP00-TM03": ("fast aerial wake", "palm contact"),
}
PROMPT_REQUIRED_AUDIO = {
    "EP00-TM01": ("compression thud", "elastic restoration pulse", "recoil through wood"),
    "EP00-TM02": ("continuous cloth graze", "staggered footstep", "wooden grip creak"),
    "EP00-TM03": ("downward palm-pressure rush", "stone impact", "wooden spear slipping free"),
}


def main() -> int:
    directory = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    project = h3_prompt_projects.project_clips(ROOT, PROJECT_ID)
    clips = list(project["clips"])

    assert [row["clip_id"] for row in clips] == EXPECTED_CLIPS
    assert manifest["build_facts"] == {
        "clip_count": 3,
        "prompt_count": 9,
        "total_duration_seconds": 18.0,
    }
    assert manifest["queue_authorized"] is False
    assert manifest["video_generation_authorized"] is False
    assert manifest["queue_registration_performed"] is False
    assert manifest["video_generation_performed"] is False

    for clip in clips:
        assert clip["ready"], clip["errors"]
        assert clip["duration_seconds"] == 6.0
        assert len(clip["references"]) == 5
        board = clip["references"][4]
        assert board["picture_index"] == 5
        assert board["reference_kind"] == "storyboard"
        assert board["storyboard_panel_count"] == 4
        assert board["storyboard_mode"] == h3_prompt_projects.FOUR_SHOT_ACTION_STORYBOARD_MODE
        assert len(board["storyboard_beats"]) == 4
        assert all((directory / row["source_path"]).is_file() for row in clip["references"])

        variants = list(clip["prompt_variants"])
        assert [row["variant_id"] for row in variants] == ["A", "D", "E"]
        variant_shot_bodies = []
        for variant in variants:
            prompt = variant["video_prompt"]
            summary = prompt.split("\n\nsummary:\n", 1)[1].split(
                "\n\nretention_analysis:\n", 1
            )[0]
            assert all(value in summary for value in SUMMARY_REQUIRED[clip["clip_id"]])
            assert not any(value in summary for value in SUMMARY_FORBIDDEN[clip["clip_id"]])
            shots = list(h3_prompt_contract.SHOT_RE.finditer(variant["detailed_description"]))
            assert len(shots) == 4
            bodies = [row.group(4).strip() for row in shots]
            variant_shot_bodies.append(bodies)
            actual_times = [
                None if row.group(2) is None else int(row.group(2)) * 60 + float(row.group(3))
                for row in shots
            ]
            assert actual_times == EXPECTED_TIMES[variant["variant_id"]]
            assert prompt.count(" At 00:") == 3
            assert "Action timing:" not in prompt
            assert "EP00-" not in prompt
            for index, (shot_text, position) in enumerate(zip(
                bodies,
                ("top-left", "top-right", "bottom-left", "bottom-right"),
                strict=True,
            ), start=1):
                if index == 1:
                    assert "Use the top-left action image from <Picture 5>" in shot_text
                    assert "as the full-screen starting state for Shot 1." in shot_text
                else:
                    assert f"Use only the {position} action image from <Picture 5>" in shot_text
                    assert f"as full-screen Shot {index}." in shot_text
                assert "2x2" not in shot_text.lower()
                assert "grid" not in shot_text.lower()
                assert len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", shot_text)) <= 50
                assert "cut" not in shot_text.lower()
                assert "next shot" not in shot_text.lower()
                for subject_match in re.finditer(r"<Subject \d+>", shot_text):
                    assert shot_text[subject_match.end():].startswith(", the ")
            assert not any(
                name in prompt
                for name in ("Lua", "LuaSpear", "AbyssKing", "Abyss King")
            )
            assert not any(
                event in prompt
                for event in FORBIDDEN_OUTSIDE_BOARD_EVENTS[clip["clip_id"]]
            )
            assert not any(
                event in prompt
                for event in PROMPT_FORBIDDEN_PREBOARD[clip["clip_id"]]
            )
            assert all(
                event in prompt
                for event in PROMPT_REQUIRED_AUDIO[clip["clip_id"]]
            )
            if clip["clip_id"] == "EP00-TM01":
                assert "drives into" not in bodies[0]
        assert variant_shot_bodies[0] == variant_shot_bodies[1] == variant_shot_bodies[2]

    print(json.dumps({
        "status": "PASS",
        "project_id": PROJECT_ID,
        "clip_count": len(clips),
        "prompt_count": sum(len(row["prompt_variants"]) for row in clips),
        "ready_count": sum(1 for row in clips if row["ready"]),
        "queue_registration_performed": manifest["queue_registration_performed"],
        "video_generation_performed": manifest["video_generation_performed"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
