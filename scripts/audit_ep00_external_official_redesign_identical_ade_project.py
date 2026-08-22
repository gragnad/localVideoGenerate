from __future__ import annotations

"""Audit that every EP00 V3 A/D/E candidate is exactly identical."""

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_external_official_redesign_identical_ade_project as build  # noqa: E402
from scripts import build_ep00_external_official_redesign_project as source  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    external_prompts = source.extract_external_prompts(source.ATTACHMENT.read_text(encoding="utf-8"))
    expected_a = [source.apply_minimal_subject_contract(prompt)[0] for prompt in external_prompts]
    directory = h3_prompt_projects.project_dir(ROOT, build.PROJECT_ID)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_policy"] == "external_prompt_A_authoritative_A_D_E_identical"
    assert manifest["build_facts"]["candidate_prompt_relationship"] == "A_equals_D_equals_E"
    assert manifest["queue_registration_performed"] is False
    assert manifest["video_generation_performed"] is False

    project = h3_prompt_projects.project_clips(ROOT, build.PROJECT_ID)
    assert len(project["clips"]) == 5
    asset_count = 0
    for index, clip in enumerate(project["clips"], start=1):
        assert clip["ready"], (clip["clip_id"], clip["errors"])
        variants = {row["variant_id"]: row["video_prompt"] for row in clip["prompt_variants"]}
        assert list(variants) == ["A", "D", "E"]
        assert variants["A"] == variants["D"] == variants["E"] == expected_a[index - 1]
        assert clip["video_prompt"] == variants["A"]
        for prompt in variants.values():
            report = h3_prompt_contract.validate_prompt(
                prompt, duration_seconds=15.0, require_shot_timestamps=True
            )
            assert report.valid and report.shot_count == 3
            for line in clip["required_dialogue"]:
                assert line in prompt
        expected_picture_count = 4 if index <= 2 else 3
        assert len(clip["references"]) == expected_picture_count
        for reference, (_role, _label, source_asset) in zip(
            clip["references"], source.ASSETS[:expected_picture_count], strict=True
        ):
            assert digest(directory / str(reference["source_path"])) == digest(source_asset)
            asset_count += 1
    assert asset_count == 17

    result = {
        "status": "PASS",
        "project_id": build.PROJECT_ID,
        "clip_count": 5,
        "prompt_count": 15,
        "candidate_ids": ["A", "D", "E"],
        "A_equals_D_equals_E_for_every_clip": True,
        "candidate_derivation_applied": False,
        "asset_copy_count": 17,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    review = build.SOURCE_DIR / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "EP00_EXTERNAL_OFFICIAL_REDESIGN_IDENTICAL_ADE_AUDIT_V3.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (review / "EP00_EXTERNAL_OFFICIAL_REDESIGN_IDENTICAL_ADE_AUDIT_V3.md").write_text(
        "# EP00 External Official-Format Identical A/D/E Audit V3\n\n"
        "- Result: PASS\n"
        "- A, D, and E are byte-for-byte identical within every clip\n"
        "- No D/E camera or content derivation was applied\n"
        "- Five clips, fifteen candidate entries, and seventeen linked project-local assets\n"
        "- Required dialogue remains present\n"
        "- No queue registration or video generation\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
