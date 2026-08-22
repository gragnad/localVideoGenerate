from __future__ import annotations

"""Build A/D/E variants from the authoritative external EP00 prompts.

A is the minimally contract-corrected external prompt verbatim. D and E add
one candidate-direction sentence to the detailed-description preamble while
leaving every Shot body, timestamp, action, dialogue, and outcome unchanged.
"""

import json
from pathlib import Path
import secrets
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402
from scripts import build_ep00_external_official_redesign_project as source  # noqa: E402


SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_external_official_redesign_ade_new"
PROJECT_ID = "RaisingaDragonSeason01_EP00_EXTERNAL_H3_OFFICIAL_REDESIGN_R2V_ADE_V2"

D_DIRECTION = (
    "Candidate D preserves every written event, Shot time, subject placement, dialogue, and outcome, "
    "while biasing the existing camera plan toward lower or more oblique viewpoints, stronger lateral "
    "parallax, and more forceful physical camera energy."
)
E_DIRECTION = (
    "Candidate E preserves every written event, Shot time, subject placement, dialogue, and outcome, "
    "while biasing the existing camera plan toward stronger foreground depth, compressed perspective, "
    "and tighter spatial pressure."
)


def derive_candidate(prompt: str, direction: str) -> str:
    marker = "detailed_description:\n"
    start = prompt.index(marker) + len(marker)
    first_shot = prompt.index("\n\n[Shot 1]", start)
    preamble = prompt[start:first_shot].rstrip()
    return prompt[:start] + preamble + "\n" + direction + prompt[first_shot:]


def build() -> dict[str, object]:
    destination = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    if destination.exists():
        raise FileExistsError(f"Existing projects are not overwritten: {PROJECT_ID}")
    source_bytes = source.ATTACHMENT.read_bytes()
    external_prompts = source.extract_external_prompts(source_bytes.decode("utf-8"))
    prepared = []
    total_tag_insertions = 0
    for index, external_prompt in enumerate(external_prompts, start=1):
        candidate_a, insertion_count = source.apply_minimal_subject_contract(external_prompt)
        candidate_d = derive_candidate(candidate_a, D_DIRECTION)
        candidate_e = derive_candidate(candidate_a, E_DIRECTION)
        for variant_id, prompt in (("A", candidate_a), ("D", candidate_d), ("E", candidate_e)):
            report = h3_prompt_contract.validate_prompt(
                prompt,
                duration_seconds=15.0,
                require_shot_timestamps=True,
                allow_four_shots=False,
            )
            if not report.valid or report.shot_count != 3:
                raise ValueError(
                    f"External Clip {index:02d} candidate {variant_id} failed validation: "
                    + "; ".join(issue.message for issue in report.errors)
                )
        total_tag_insertions += insertion_count
        prepared.append({
            "A": candidate_a,
            "D": candidate_d,
            "E": candidate_e,
            "tag_insertions": insertion_count,
            "external_sha256": source.digest_text(external_prompt),
        })

    base = h3_prompt_projects.projects_root(ROOT)
    base.mkdir(parents=True, exist_ok=True)
    staging = base / f".{PROJECT_ID}.building-{secrets.token_hex(4)}"
    staging.mkdir()
    try:
        manifest = {
            "schema_version": 2,
            "project_kind": h3_prompt_projects.PROJECT_KIND,
            "project_id": PROJECT_ID,
            "title": "Raising a Dragon EP00 · External Official-Format R2V A/D/E V2",
            "description": "A preserves each external prompt; D and E derive camera direction from the same prompt without changing Shot events.",
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": h3_prompt_contract.CONTRACT_VERSION,
            "asset_storage": "project_local",
            "source_policy": "external_prompt_A_authoritative_D_E_camera_only_derivations",
            "canonical_source_lineage": [source.ATTACHMENT.name],
            "external_source_sha256": source.digest_bytes(source_bytes),
            "locked_rule_id": "EP00_EXTERNAL_OFFICIAL_REDESIGN_R2V_ADE_V2",
            "build_script": "scripts/build_ep00_external_official_redesign_ade_project.py",
            "dialogue_lock_version": "EP00_EXTERNAL_PROMPT_DIALOGUE_LOCK_V1",
            "dialogue_clip_count": 2,
            "dialogue_line_count": 2,
            "scene_types": ["external_prompt_ade"],
            "generation_blocked": False,
            "replacement_project_ids": [],
            "review_status": "pending_user_prompt_review",
            "build_facts": {
                "clip_count": 5,
                "prompt_count": 15,
                "total_duration_seconds": 75.0,
                "candidate_ids": ["A", "D", "E"],
                "minimal_subject_tag_insertions_in_A_sources": total_tag_insertions,
            },
            "queue_authorized": False,
            "video_generation_authorized": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        source_copy_dir = staging / "source"
        source_copy_dir.mkdir()
        shutil.copy2(source.ATTACHMENT, source_copy_dir / "EXTERNAL_PROMPTS_SOURCE.source.txt")

        clip_dir = staging / source.SCENE_ID
        clip_dir.mkdir()
        for index, row in enumerate(prepared, start=1):
            clip_id = f"EP00-EXT-R2V-C{index:02d}"
            picture_count = 4 if index <= 2 else 3
            references = []
            for picture_index, (role, label, source_asset) in enumerate(
                source.ASSETS[:picture_count], start=1
            ):
                relative = f"assets/{clip_id}/picture_{picture_index}.png"
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_asset, target)
                references.append({
                    "picture_index": picture_index,
                    "role": role,
                    "label": label,
                    "description": "",
                    "instruction_en": "",
                    "reference_kind": "visual_reference",
                    "required": True,
                    "source_path": relative,
                })
            variants = [
                {
                    "variant_id": "A",
                    "label": "Candidate A · external original",
                    "rationale": "Authoritative external prompt with only required first Subject-tag insertions.",
                    "video_prompt": row["A"],
                },
                {
                    "variant_id": "D",
                    "label": "Candidate D · lower and oblique physical camera",
                    "rationale": "Original Shot plan with lower or oblique viewpoints, lateral parallax, and stronger physical camera energy.",
                    "video_prompt": row["D"],
                },
                {
                    "variant_id": "E",
                    "label": "Candidate E · compressed spatial pressure",
                    "rationale": "Original Shot plan with stronger foreground depth, compressed perspective, and tighter spatial pressure.",
                    "video_prompt": row["E"],
                },
            ]
            payload = {
                "schema_version": 2,
                "prompt_contract_version": h3_prompt_contract.CONTRACT_VERSION,
                "workflow": h3_prompt_projects.WORKFLOW,
                "project_id": PROJECT_ID,
                "scene_id": source.SCENE_ID,
                "clip_id": clip_id,
                "sequence": index,
                "status": "pending_user_prompt_review",
                "duration_seconds": 15.0,
                "title": source.CLIP_TITLES[index - 1],
                "video_prompt": row["A"],
                "prompt_variants": variants,
                "references": references,
                "canonical_source_lineage": [source.ATTACHMENT.name],
                "locked_rule_id": "EP00_EXTERNAL_OFFICIAL_REDESIGN_R2V_ADE_V2",
                "source_shot_id": f"external-r2v-clip-{index:02d}",
                "summary": source.prompt_summary(str(row["A"])),
                "required_dialogue": source.DIALOGUE[index - 1],
                "dialogue_lock_version": "EP00_EXTERNAL_PROMPT_DIALOGUE_LOCK_V1",
                "external_prompt_source_sha256": row["external_sha256"],
                "minimal_subject_tag_insertions": row["tag_insertions"],
                "candidate_policy": {
                    "A": "external original after required Subject-tag insertions",
                    "D": "A plus one camera-direction preamble sentence only",
                    "E": "A plus one camera-direction preamble sentence only",
                },
                "scene_type": "external_prompt_ade",
                "semantic_review": "pending_user_prompt_review",
            }
            markdown = (
                f"# {clip_id} · {source.CLIP_TITLES[index - 1]} · MiniMax H3 R2V A/D/E\n\n"
                "## Machine Payload\n\n```json\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
            (clip_dir / f"{clip_id}.md").write_text(markdown, encoding="utf-8")
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
    }


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
