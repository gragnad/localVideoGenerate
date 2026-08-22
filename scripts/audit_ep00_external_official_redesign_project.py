from __future__ import annotations

"""Audit the imported external EP00 official-format redesign project."""

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_external_official_redesign_project as build  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    source_bytes = build.ATTACHMENT.read_bytes()
    source_prompts = build.extract_external_prompts(source_bytes.decode("utf-8"))
    assert len(source_prompts) == 5
    expected_prompts = []
    expected_insertions = []
    for prompt in source_prompts:
        patched, count = build.apply_minimal_subject_contract(prompt)
        expected_prompts.append(patched)
        expected_insertions.append(count)
    assert expected_insertions == [1, 3, 2, 2, 2]

    directory = h3_prompt_projects.project_dir(ROOT, build.PROJECT_ID)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["build_facts"]["clip_count"] == 5
    assert manifest["build_facts"]["prompt_count"] == 5
    assert manifest["build_facts"]["minimal_subject_tag_insertions"] == 10
    assert manifest["dialogue_clip_count"] == 2
    assert manifest["dialogue_line_count"] == 2
    assert manifest["queue_registration_performed"] is False
    assert manifest["video_generation_performed"] is False
    assert digest(directory / "source/EXTERNAL_PROMPTS_SOURCE.source.txt") == digest(build.ATTACHMENT)

    project = h3_prompt_projects.project_clips(ROOT, build.PROJECT_ID)
    assert len(project["clips"]) == 5
    total_shots = 0
    total_asset_copies = 0
    for index, clip in enumerate(project["clips"], start=1):
        assert clip["clip_id"] == f"EP00-EXT-R2V-C{index:02d}"
        assert clip["ready"], (clip["clip_id"], clip["errors"])
        assert clip["prompt_variants"] == []
        assert clip["video_prompt"] == expected_prompts[index - 1]
        assert clip["required_dialogue"] == build.DIALOGUE[index - 1]
        report = h3_prompt_contract.validate_prompt(
            clip["video_prompt"], duration_seconds=15.0, require_shot_timestamps=True
        )
        assert report.valid and report.shot_count == 3
        total_shots += report.shot_count
        expected_picture_count = 4 if index <= 2 else 3
        assert len(clip["references"]) == expected_picture_count
        assert [row["picture_index"] for row in clip["references"]] == list(
            range(1, expected_picture_count + 1)
        )
        assert all(row["linked"] for row in clip["references"])
        assert all(row["reference_kind"] == "visual_reference" for row in clip["references"])
        for reference, (_role, _label, source_asset) in zip(
            clip["references"], build.ASSETS[:expected_picture_count], strict=True
        ):
            assert digest(directory / str(reference["source_path"])) == digest(source_asset)
            total_asset_copies += 1

    assert total_shots == 15
    assert total_asset_copies == 17
    report_payload = {
        "status": "PASS",
        "project_id": build.PROJECT_ID,
        "external_source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "clip_count": 5,
        "prompt_count": 5,
        "shot_count": 15,
        "prompt_variants_created": 0,
        "model_facing_change": "Only ten required <Subject 1> insertions before first untagged Lua mentions.",
        "minimal_subject_tag_insertions_by_clip": expected_insertions,
        "all_other_external_prompt_text_preserved": True,
        "picture_counts_by_clip": [4, 4, 3, 3, 3],
        "project_local_asset_copy_count": total_asset_copies,
        "storyboard_picture_count": 0,
        "dialogue_line_count": 2,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    review = build.SOURCE_DIR / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "EP00_EXTERNAL_OFFICIAL_REDESIGN_AUDIT_V1.json").write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (review / "EP00_EXTERNAL_OFFICIAL_REDESIGN_AUDIT_V1.md").write_text(
        "# EP00 External Official-Format Redesign Audit V1\n\n"
        "- Result: PASS\n"
        "- Five external prompts imported as five independent R2V clips; no A/D/E variants created\n"
        "- Fifteen original timed Shots preserved\n"
        "- The only model-facing edits are ten required `<Subject 1>` insertions before untagged Lua mentions\n"
        "- All other external prompt prose, timing, dialogue, soundscape, and music fields are unchanged\n"
        "- Picture counts are 4, 4, 3, 3, 3 with seventeen project-local asset copies\n"
        "- Lua, Deep Sea King, chamber, and cyan-effect files match their source hashes\n"
        "- No storyboard Picture, queue registration, or video generation\n",
        encoding="utf-8",
    )
    print(json.dumps(report_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
