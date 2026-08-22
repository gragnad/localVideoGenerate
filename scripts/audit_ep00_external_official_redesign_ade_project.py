from __future__ import annotations

"""Audit the external EP00 A/D/E project and camera-only derivations."""

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_external_official_redesign_ade_project as build  # noqa: E402
from scripts import build_ep00_external_official_redesign_project as source  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shot_plan(prompt: str) -> str:
    """Return the complete timed Shot section, excluding candidate preamble."""

    detailed = prompt.index("detailed_description:")
    return prompt[prompt.index("[Shot 1]", detailed) :]


def main() -> int:
    source_bytes = source.ATTACHMENT.read_bytes()
    external_prompts = source.extract_external_prompts(source_bytes.decode("utf-8"))
    assert len(external_prompts) == 5

    expected_a: list[str] = []
    expected_insertions: list[int] = []
    for prompt in external_prompts:
        patched, count = source.apply_minimal_subject_contract(prompt)
        expected_a.append(patched)
        expected_insertions.append(count)
    assert expected_insertions == [1, 3, 2, 2, 2]

    directory = h3_prompt_projects.project_dir(ROOT, build.PROJECT_ID)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_policy"] == "external_prompt_A_authoritative_D_E_camera_only_derivations"
    assert manifest["build_facts"]["clip_count"] == 5
    assert manifest["build_facts"]["prompt_count"] == 15
    assert manifest["build_facts"]["candidate_ids"] == ["A", "D", "E"]
    assert manifest["build_facts"]["minimal_subject_tag_insertions_in_A_sources"] == 10
    assert manifest["queue_registration_performed"] is False
    assert manifest["video_generation_performed"] is False
    assert digest(directory / "source/EXTERNAL_PROMPTS_SOURCE.source.txt") == digest(source.ATTACHMENT)

    project = h3_prompt_projects.project_clips(ROOT, build.PROJECT_ID)
    assert len(project["clips"]) == 5
    total_variant_shots = 0
    total_asset_copies = 0
    for index, clip in enumerate(project["clips"], start=1):
        assert clip["clip_id"] == f"EP00-EXT-R2V-C{index:02d}"
        assert clip["ready"], (clip["clip_id"], clip["errors"])
        variants = {row["variant_id"]: row["video_prompt"] for row in clip["prompt_variants"]}
        assert list(variants) == ["A", "D", "E"]
        assert variants["A"] == expected_a[index - 1]
        assert clip["video_prompt"] == variants["A"]
        assert variants["D"] == build.derive_candidate(variants["A"], build.D_DIRECTION)
        assert variants["E"] == build.derive_candidate(variants["A"], build.E_DIRECTION)
        assert shot_plan(variants["A"]) == shot_plan(variants["D"]) == shot_plan(variants["E"])
        assert clip["required_dialogue"] == source.DIALOGUE[index - 1]

        for variant_id in ("A", "D", "E"):
            prompt = variants[variant_id]
            report = h3_prompt_contract.validate_prompt(
                prompt, duration_seconds=15.0, require_shot_timestamps=True
            )
            assert report.valid and report.shot_count == 3
            for line in clip["required_dialogue"]:
                assert line in prompt
            total_variant_shots += report.shot_count

        expected_picture_count = 4 if index <= 2 else 3
        assert len(clip["references"]) == expected_picture_count
        assert [row["picture_index"] for row in clip["references"]] == list(
            range(1, expected_picture_count + 1)
        )
        assert all(row["linked"] for row in clip["references"])
        for reference, (_role, _label, source_asset) in zip(
            clip["references"], source.ASSETS[:expected_picture_count], strict=True
        ):
            assert digest(directory / str(reference["source_path"])) == digest(source_asset)
            total_asset_copies += 1

    assert total_variant_shots == 45
    assert total_asset_copies == 17
    report_payload = {
        "status": "PASS",
        "project_id": build.PROJECT_ID,
        "external_source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "clip_count": 5,
        "candidate_ids": ["A", "D", "E"],
        "prompt_count": 15,
        "source_shot_plan_count": 15,
        "variant_shot_occurrence_count": 45,
        "candidate_A_external_text_preserved_except_required_subject_tags": True,
        "minimal_subject_tag_insertions_by_clip": expected_insertions,
        "candidate_D_E_camera_preamble_only": True,
        "shot_bodies_timestamps_actions_dialogue_outcomes_identical_across_A_D_E": True,
        "picture_counts_by_clip": [4, 4, 3, 3, 3],
        "project_local_asset_copy_count": total_asset_copies,
        "storyboard_picture_count": 0,
        "dialogue_line_count": 2,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    review = build.SOURCE_DIR / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "EP00_EXTERNAL_OFFICIAL_REDESIGN_ADE_AUDIT_V2.json").write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (review / "EP00_EXTERNAL_OFFICIAL_REDESIGN_ADE_AUDIT_V2.md").write_text(
        "# EP00 External Official-Format A/D/E Audit V2\n\n"
        "- Result: PASS\n"
        "- Candidate A preserves each external prompt, except ten required first `<Subject 1>` insertions\n"
        "- Candidate D and E each add exactly one camera-direction sentence before Shot 1\n"
        "- All fifteen source Shot bodies, timestamps, subject placement, actions, dialogue, and outcomes are identical across A/D/E\n"
        "- Five clips contain fifteen prompts and forty-five validated variant-Shot occurrences\n"
        "- Picture counts are 4, 4, 3, 3, 3 with seventeen project-local asset copies\n"
        "- No storyboard Picture, queue registration, or video generation\n",
        encoding="utf-8",
    )
    print(json.dumps(report_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
