from __future__ import annotations

"""Add five user-supplied revisions as V2 clips to the existing EP00 V3 project."""

import copy
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_projects  # noqa: E402
from scripts import import_ep00_h3_r2v_prompt_package as importer  # noqa: E402
from scripts import import_ep00_h3_r2v_prompt_package_v3 as v3  # noqa: E402


def main() -> int:
    v3.configure()
    directory = h3_prompt_projects.project_dir(ROOT, importer.PROJECT_ID)
    original_rows = {str(row["clip_id"]): row for row in importer.prompt_rows()}
    importer.PROMPT_OVERRIDES = v3.revision_prompts()
    revised_rows = {str(row["clip_id"]): row for row in importer.prompt_rows()}
    importer.PROMPT_OVERRIDES = {}

    def references(asset_keys: list[str]) -> list[dict[str, object]]:
        rows = []
        for picture_index, asset_key in enumerate(asset_keys, start=1):
            role, label = importer.ASSET_LABELS[asset_key]
            asset_name = importer.ASSETS[asset_key].name
            rows.append({
                "picture_index": picture_index,
                "role": role,
                "label": label,
                "description": "",
                "instruction_en": "",
                "reference_kind": "visual_reference",
                "required": True,
                "source_path": f"assets/shared/{asset_name}",
            })
        return rows

    def apply_prompt(
        payload: dict[str, object],
        row: dict[str, object],
        asset_keys: list[str],
        *,
        revised: bool,
    ) -> None:
        prompt = str(row["prompt"])
        payload["video_prompt"] = prompt
        payload["summary"] = row["summary"]
        payload["required_dialogue"] = row["required_dialogue"]
        payload["source_prompt_sha256"] = row["prompt_sha256"]
        payload["references"] = references(asset_keys)
        rationale = (
            "Exact duplicate of the user-supplied revised prompt; no derivation."
            if revised
            else "Exact duplicate of the user-supplied prompt; no derivation."
        )
        label_suffix = "user-supplied revision V2" if revised else "user-supplied original"
        for variant in payload["prompt_variants"]:
            variant["label"] = f"Candidate {variant['variant_id']} · {label_suffix}"
            variant["video_prompt"] = prompt
            variant["rationale"] = rationale

    def write_clip(path: Path, payload: dict[str, object]) -> None:
        markdown = (
            f"# {payload['clip_id']} · {payload['title']} · MiniMax H3 R2V\n\n"
            "## Machine Payload\n\n```json\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
            + "\n```\n"
        )
        path.write_text(markdown, encoding="utf-8")

    for source_id in v3.REVISION_IDS:
        base_clip_id = f"EP00_{source_id}"
        versioned_clip_id = f"{base_clip_id}_V2"
        base_path = directory / "EP00-CONTINUOUS" / f"{base_clip_id}.md"
        base_payload = h3_prompt_projects.extract_payload(base_path.read_text(encoding="utf-8"))

        # Restore and preserve the original V3 clip even if an earlier run replaced it.
        apply_prompt(base_payload, original_rows[source_id], importer.CLIP_ASSETS[source_id], revised=False)
        base_payload["canonical_source_lineage"] = [
            importer.PROMPT_DOCUMENT.name,
            importer.EXECUTION_GUIDE.name,
        ]
        base_payload["clip_version"] = 1
        base_payload["superseded_by_clip_id"] = versioned_clip_id
        for key in ("revision_source", "supersedes_clip_id"):
            base_payload.pop(key, None)
        write_clip(base_path, base_payload)

        versioned_payload = copy.deepcopy(base_payload)
        versioned_payload["clip_id"] = versioned_clip_id
        versioned_payload["clip_version"] = 2
        versioned_payload["supersedes_clip_id"] = base_clip_id
        versioned_payload.pop("superseded_by_clip_id", None)
        versioned_payload["canonical_source_lineage"] = [
            importer.PROMPT_DOCUMENT.name,
            importer.EXECUTION_GUIDE.name,
            v3.REVISION_DOCUMENT.name,
        ]
        versioned_payload["revision_source"] = v3.REVISION_DOCUMENT.name
        apply_prompt(
            versioned_payload,
            revised_rows[source_id],
            v3.REVISION_CLIP_ASSETS[source_id],
            revised=True,
        )
        write_clip(
            directory / "EP00-CONTINUOUS" / f"{versioned_clip_id}.md",
            versioned_payload,
        )

    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if v3.REVISION_DOCUMENT.name not in manifest["canonical_source_lineage"]:
        manifest["canonical_source_lineage"].append(v3.REVISION_DOCUMENT.name)
    versioned_clip_ids = [f"EP00_{clip_id}_V2" for clip_id in v3.REVISION_IDS]
    superseded_clip_ids = [f"EP00_{clip_id}" for clip_id in v3.REVISION_IDS]
    manifest["revision_source"] = v3.REVISION_DOCUMENT.name
    manifest.pop("revised_clip_ids", None)
    manifest["versioned_clip_ids"] = versioned_clip_ids
    manifest["superseded_clip_ids"] = superseded_clip_ids
    manifest["revision_script"] = "scripts/apply_ep00_v3_clip_revisions.py"
    manifest["build_facts"].pop("revised_clip_count", None)
    manifest["build_facts"]["base_clip_count"] = len(importer.EXPECTED_CLIP_IDS)
    manifest["build_facts"]["versioned_revision_count"] = len(v3.REVISION_IDS)
    manifest["build_facts"]["clip_count"] = len(importer.EXPECTED_CLIP_IDS) + len(v3.REVISION_IDS)
    manifest["build_facts"]["candidate_entry_count"] = manifest["build_facts"]["clip_count"] * 3
    manifest["build_facts"]["unique_prompt_count"] = manifest["build_facts"]["clip_count"]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    project_source = directory / "source" / f"{v3.REVISION_DOCUMENT.stem}.source.txt"
    shutil.copy2(v3.REVISION_DOCUMENT, project_source)
    shutil.copy2(v3.REVISION_DOCUMENT, importer.SOURCE_DIR / v3.REVISION_DOCUMENT.name)
    print(json.dumps({
        "project_id": importer.PROJECT_ID,
        "base_clip_count": len(importer.EXPECTED_CLIP_IDS),
        "versioned_clip_ids": versioned_clip_ids,
        "candidate_policy": "A_equals_D_equals_E_exactly",
        "c10_v2_picture_order": v3.REVISION_CLIP_ASSETS["C10"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
