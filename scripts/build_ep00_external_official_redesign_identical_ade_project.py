from __future__ import annotations

"""Build EP00 candidates where A, D, and E use the same authoritative prompt."""

import json
from pathlib import Path
import secrets
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_external_official_redesign_ade_project as previous  # noqa: E402
from scripts import build_ep00_external_official_redesign_project as source  # noqa: E402


SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_external_official_redesign_identical_ade_new"
PROJECT_ID = "RaisingaDragonSeason01_EP00_EXTERNAL_H3_OFFICIAL_REDESIGN_R2V_IDENTICAL_ADE_V3"
LOCK_ID = "EP00_EXTERNAL_OFFICIAL_REDESIGN_R2V_IDENTICAL_ADE_V3"


def build() -> dict[str, object]:
    destination = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    if destination.exists():
        raise FileExistsError(f"Existing projects are not overwritten: {PROJECT_ID}")

    previous_dir = h3_prompt_projects.project_dir(ROOT, previous.PROJECT_ID)
    if not previous_dir.is_dir():
        raise FileNotFoundError(f"Required source project is missing: {previous.PROJECT_ID}")

    base = h3_prompt_projects.projects_root(ROOT)
    staging = base / f".{PROJECT_ID}.building-{secrets.token_hex(4)}"
    shutil.copytree(previous_dir, staging)
    try:
        manifest_path = staging / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update({
            "project_id": PROJECT_ID,
            "title": "Raising a Dragon EP00 · External Official-Format R2V Identical A/D/E V3",
            "description": "A, D, and E all use the same authoritative external prompt without candidate derivation.",
            "source_policy": "external_prompt_A_authoritative_A_D_E_identical",
            "locked_rule_id": LOCK_ID,
            "build_script": "scripts/build_ep00_external_official_redesign_identical_ade_project.py",
            "scene_types": ["external_prompt_identical_candidates"],
        })
        manifest["build_facts"]["candidate_prompt_relationship"] = "A_equals_D_equals_E"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        for path in sorted(staging.glob("**/EP00-EXT-R2V-C*.md")):
            payload = h3_prompt_projects.extract_payload(path.read_text(encoding="utf-8"))
            candidate_a = next(
                row["video_prompt"] for row in payload["prompt_variants"] if row["variant_id"] == "A"
            )
            payload["project_id"] = PROJECT_ID
            payload["video_prompt"] = candidate_a
            payload["locked_rule_id"] = LOCK_ID
            payload["scene_type"] = "external_prompt_identical_candidates"
            payload["candidate_policy"] = {
                "A": "authoritative external prompt after required Subject-tag insertions",
                "D": "exact duplicate of A; no derivation",
                "E": "exact duplicate of A; no derivation",
            }
            for row in payload["prompt_variants"]:
                row["video_prompt"] = candidate_a
                if row["variant_id"] == "A":
                    row["label"] = "Candidate A · authoritative external prompt"
                    row["rationale"] = "Authoritative external prompt with only required first Subject-tag insertions."
                else:
                    row["label"] = f"Candidate {row['variant_id']} · same as A"
                    row["rationale"] = "Exact duplicate of Candidate A with no camera or content derivation."
            markdown = (
                f"# {payload['clip_id']} · {payload['title']} · MiniMax H3 R2V Identical A/D/E\n\n"
                "## Machine Payload\n\n```json\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
            path.write_text(markdown, encoding="utf-8")

        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    overview = h3_prompt_projects.project_clips(ROOT, PROJECT_ID)
    invalid = [clip for clip in overview["clips"] if not clip["ready"]]
    if invalid:
        raise RuntimeError(f"Published project validation failed: {invalid[0]['clip_id']}: {invalid[0]['errors']}")

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source.ATTACHMENT, SOURCE_DIR / "EXTERNAL_PROMPTS_SOURCE.md")
    return {
        "project_id": PROJECT_ID,
        "project_path": str(destination),
        "clip_count": len(overview["clips"]),
        "ready_count": sum(1 for clip in overview["clips"] if clip["ready"]),
        "prompt_count": 15,
        "candidate_ids": ["A", "D", "E"],
        "candidate_prompt_relationship": "A_equals_D_equals_E",
    }


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
