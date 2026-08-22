from __future__ import annotations

"""Audit the current 2D EP00 temporal storyboard prompts without rendering."""

import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
import build_ep00_2d_temporal_storyboard_ade_v4 as build  # noqa: E402


BANNED = (
    "Action timing:",
    "Continue inherited momentum",
    "incoming action axis",
    "accumulated exit state",
    "next panel",
    "next Shot",
    "cut to Shot",
    "storyboards_ep00_action_v2",
    "3D",
    "LuaSpear",
    "AbyssKing",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def section(prompt: str, name: str, next_name: str | None) -> str:
    body = prompt.split(f"\n\n{name}:\n", 1)[1]
    return body if next_name is None else body.split(f"\n\n{next_name}:\n", 1)[0]


def main() -> int:
    directory = h3_prompt_projects.project_dir(ROOT, build.PROJECT_ID)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    payload = h3_prompt_projects.project_clips(ROOT, build.PROJECT_ID)
    clips = list(payload["clips"])
    assert len(clips) == 14
    assert manifest["queue_registration_performed"] is False
    assert manifest["video_generation_performed"] is False

    for clip in clips:
        clip_id = str(clip["clip_id"])
        assert clip["ready"], (clip_id, clip["errors"])
        assert clip["status"] == "pending_user_prompt_review"
        board = next(row for row in clip["references"] if row["reference_kind"] == "storyboard")
        assert board["storyboard_mode"] == build.MODE
        source_name = f"{clip_id.replace('-', '_')}_STORYBOARD_V2.png"
        source_path = build.SOURCE_DIR / "storyboards_v2" / "ep00" / source_name
        copied_path = directory / str(board["source_path"])
        assert source_path.is_file()
        assert digest(source_path) == digest(copied_path)

        variants = clip["prompt_variants"]
        assert [row["variant_id"] for row in variants] == ["A", "D", "E"]
        bodies_by_variant: list[list[str]] = []
        starts_by_variant: list[tuple[float | None, ...]] = []
        for variant in variants:
            prompt = str(variant["video_prompt"])
            assert not any(value.lower() in prompt.lower() for value in BANNED)
            summary = section(prompt, "summary", "retention_analysis")
            assert summary.removeprefix("[reference generation] ") == build.SUMMARIES[clip_id]
            assert section(prompt, "overall_soundscape", "non_diegetic_music") == (
                "Only sounds directly caused by the four written Shot actions."
            )
            assert section(prompt, "non_diegetic_music", None) == "None."
            matches = list(h3_prompt_contract.SHOT_RE.finditer(variant["detailed_description"]))
            assert len(matches) == 4
            bodies = [row.group(4).strip() for row in matches]
            bodies_by_variant.append(bodies)
            starts = tuple(
                None if row.group(2) is None else int(row.group(2)) * 60 + float(row.group(3))
                for row in matches
            )
            starts_by_variant.append(starts)
            assert starts[0] is None
            assert list(starts[1:]) == sorted(starts[1:])
            picture_id = int(board["picture_index"])
            for index, (body, position) in enumerate(zip(bodies, build.POSITIONS, strict=True), start=1):
                expected = (
                    f"Use the top-left action image from <Picture {picture_id}> as the full-screen starting state for Shot 1."
                    if index == 1
                    else f"Use only the {position} action image from <Picture {picture_id}> as full-screen Shot {index}."
                )
                assert expected in body
                assert "grid" not in body.lower()
                assert "panel" not in body.lower()
                assert len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", body)) <= 75
        assert bodies_by_variant[0] == bodies_by_variant[1] == bodies_by_variant[2]
        assert len(set(starts_by_variant)) == 3

    print(json.dumps({
        "status": "PASS",
        "project_id": build.PROJECT_ID,
        "lineage": "rebuild_v2 approved high-detail 2D cel animation",
        "clip_count": len(clips),
        "prompt_count": sum(len(row["prompt_variants"]) for row in clips),
        "storyboard_hash_matches": len(clips),
        "ready_count": sum(1 for row in clips if row["ready"]),
        "queue_registration_performed": manifest["queue_registration_performed"],
        "video_generation_performed": manifest["video_generation_performed"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
