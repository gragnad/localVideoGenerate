from __future__ import annotations

"""Audit EP00 action-revision V2 prompt mapping without generating video."""

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
import build_ep00_2d_action_revision_v2_ade_v5 as build  # noqa: E402


BANNED = (
    "Action timing:",
    "Continue inherited momentum",
    "next panel",
    "next Shot",
    "cut to Shot",
    "storyboards_ep00_action_v2",
    "LuaSpear",
    "AbyssKing",
)


REQUIRED_EVENT_TEXT = {
    "EP00-S05-C01": ("water wedge", "every chamber channel ignites"),
    "EP00-S05-C02": ("liquefies only the left wrist", "reforms as one left hand", "flipping the fighter"),
    "EP00-S05-C03": ("circular water bursts", "hits two channel lips", "outer ring inward"),
    "EP00-S06-C02": ("heartbeat stops", "look separately", "cover the full frame"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def section(prompt: str, name: str, next_name: str | None) -> str:
    body = prompt.split(f"\n\n{name}:\n", 1)[1]
    return body if next_name is None else body.split(f"\n\n{next_name}:\n", 1)[0]


def main() -> int:
    source_path = build.SOURCE_DIR / build.SOURCE_SCREENPLAY
    assert digest(source_path) == build.SOURCE_SHA256
    spec = json.loads(build.SPEC_PATH.read_text(encoding="utf-8"))
    assert set(spec["stale_storyboard_clips"]) == build.STALE_STORYBOARD_CLIPS
    assert spec["generation_blocked"] is True
    assert spec["dialogue_clip_count"] == 4
    assert spec["dialogue_line_count"] == 7

    directory = h3_prompt_projects.project_dir(ROOT, build.PROJECT_ID)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["generation_blocked"] is True
    assert manifest["queue_registration_performed"] is False
    assert manifest["video_generation_performed"] is False
    clips = list(h3_prompt_projects.project_clips(ROOT, build.PROJECT_ID)["clips"])
    assert len(clips) == 14

    total_dialogue = 0
    for clip in clips:
        clip_id = str(clip["clip_id"])
        assert clip["ready"], (clip_id, clip["errors"])
        assert clip["status"] == "prompt_review_only_generation_blocked"
        expected_dialogue = build.DIALOGUE_BY_CLIP.get(clip_id, [])
        assert clip["required_dialogue"] == expected_dialogue
        total_dialogue += len(expected_dialogue)
        variants = clip["prompt_variants"]
        assert [row["variant_id"] for row in variants] == ["A", "D", "E"]
        shot_bodies: list[list[str]] = []
        shot_starts: list[tuple[float | None, ...]] = []
        for variant in variants:
            prompt = str(variant["video_prompt"])
            assert not any(value.lower() in prompt.lower() for value in BANNED)
            actual_dialogue = [line for _language, line in h3_prompt_contract.DIALOGUE_RE.findall(prompt)]
            assert actual_dialogue == expected_dialogue
            summary = section(prompt, "summary", "retention_analysis")
            assert summary.removeprefix("[reference generation] ") == build.SUMMARIES[clip_id]
            matches = list(h3_prompt_contract.SHOT_RE.finditer(variant["detailed_description"]))
            assert len(matches) == 4
            bodies = [row.group(4).strip() for row in matches]
            shot_bodies.append(bodies)
            starts = tuple(
                None if row.group(2) is None else int(row.group(2)) * 60 + float(row.group(3))
                for row in matches
            )
            shot_starts.append(starts)
            assert starts[0] is None
            assert list(starts[1:]) == sorted(starts[1:])
            for index, (body, position) in enumerate(zip(bodies, build.source.POSITIONS, strict=True), start=1):
                assert position in body
                assert "grid" not in body.lower()
                assert "panel" not in body.lower()
                assert len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", body)) <= 105
            full_description = " ".join(bodies)
            for required in REQUIRED_EVENT_TEXT.get(clip_id, ()):
                assert required.lower() in full_description.lower()
        assert shot_bodies[0] == shot_bodies[1] == shot_bodies[2]
        assert len(set(shot_starts)) == 3

    assert total_dialogue == 7
    print(json.dumps({
        "status": "PASS",
        "project_id": build.PROJECT_ID,
        "source_sha256": build.SOURCE_SHA256,
        "clip_count": len(clips),
        "prompt_count": sum(len(row["prompt_variants"]) for row in clips),
        "dialogue_clip_count": 4,
        "dialogue_line_count": total_dialogue,
        "stale_storyboard_count": len(build.STALE_STORYBOARD_CLIPS),
        "generation_blocked": manifest["generation_blocked"],
        "queue_registration_performed": manifest["queue_registration_performed"],
        "video_generation_performed": manifest["video_generation_performed"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
