#!/usr/bin/env python3
from __future__ import annotations

"""Import the approved EP00 cinematic live-action V2 Full-Reference R2V package."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
import re
import secrets
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract  # noqa: E402
import h3_prompt_projects  # noqa: E402


PROJECT_ID = "RaisingaDragonSeason01_EP00_CINEMATIC_LIVEACTION_H3_R2V_V2"
PROJECT_TITLE = "Raising a Dragon EP00 · Cinematic Live-Action Full-Reference R2V V2"
PROJECT_ROOT = ROOT / "projects/RaisingaDragonSeason01"
PROMPT_DOCUMENT = PROJECT_ROOT / "ep00_cinematic_liveaction_production_v1/EP00_H3_R2V_PROMPT_DOCUMENT_CINEMATIC_LIVEACTION_V2.md"
COMMAND_DOCUMENT = PROJECT_ROOT / "ep00_cinematic_liveaction_production_v1/EP00_CODEX_ADDITIONAL_ASSET_GENERATION_COMMAND_V2.md"
LIBRARY = PROJECT_ROOT / "asset_sheets_cinematic_liveaction_v1_working"
ASSET_MANIFEST = LIBRARY / "manifests/EP00_ISOLATED_R2V_ASSET_MANIFEST_V2.json"
APPROVAL_GATE = LIBRARY / "manifests/EP00_ISOLATED_R2V_ASSET_APPROVAL_GATE_V2.md"

ASSET_PATHS = {
    "H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2_CINEMATIC_LIVEACTION_V3.png":
        LIBRARY / "01_characters/identity_sheets/H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2_CINEMATIC_LIVEACTION_V3.png",
    "H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png":
        LIBRARY / "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png",
    "H3_LUA_SPEAR_PROP_HQ_V3_CINEMATIC_PROP_V1.png":
        LIBRARY / "03_props/H3_LUA_SPEAR_PROP_HQ_V3_CINEMATIC_PROP_V1.png",
    "Current_Shield_IRREGULAR_CURVED_REFERENCE_SHEET_V4_CINEMATIC_FX_V1.png":
        LIBRARY / "05_effects/reference_sheets/EP00/Current_Shield_IRREGULAR_CURVED_REFERENCE_SHEET_V4_CINEMATIC_FX_V1.png",
    "BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V2.png":
        LIBRARY / "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V2.png",
    "BG_EP00_ABYSS_ALTAR_DAMAGED_CINEMATIC_LIVEACTION_V2.png":
        LIBRARY / "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_DAMAGED_CINEMATIC_LIVEACTION_V2.png",
    "BG_EP00_ABYSS_ALTAR_FINAL_DAMAGE_CINEMATIC_LIVEACTION_V2.png":
        LIBRARY / "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_FINAL_DAMAGE_CINEMATIC_LIVEACTION_V2.png",
    "FX_EP00_BLACK_SPHERE_ISOLATED_R2V_REFERENCE_V2.png":
        LIBRARY / "05_effects/reference_sheets/EP00/isolated_r2v_v2/FX_EP00_BLACK_SPHERE_ISOLATED_R2V_REFERENCE_V2.png",
    "FX_EP00_BLACK_RAIN_ISOLATED_R2V_REFERENCE_V2.png":
        LIBRARY / "05_effects/reference_sheets/EP00/isolated_r2v_v2/FX_EP00_BLACK_RAIN_ISOLATED_R2V_REFERENCE_V2.png",
    "FX_EP00_BLACK_PURSUIT_SPIKES_ISOLATED_R2V_REFERENCE_V2.png":
        LIBRARY / "05_effects/reference_sheets/EP00/isolated_r2v_v2/FX_EP00_BLACK_PURSUIT_SPIKES_ISOLATED_R2V_REFERENCE_V2.png",
    "FX_EP00_MOVING_CURRENT_ISOLATED_R2V_REFERENCE_V2.png":
        LIBRARY / "05_effects/reference_sheets/EP00/isolated_r2v_v2/FX_EP00_MOVING_CURRENT_ISOLATED_R2V_REFERENCE_V2.png",
}

ASSET_ROLES = {
    "H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2_CINEMATIC_LIVEACTION_V3.png": ("lua_identity", "Lua complete right-side scales identity"),
    "H3_ABYSS_KING_IDENTITY_HQ_V2_CINEMATIC_CREATURE_V1.png": ("abyss_king_identity", "Human-scale Abyss King identity"),
    "H3_LUA_SPEAR_PROP_HQ_V3_CINEMATIC_PROP_V1.png": ("lua_spear_prop", "Lua weathered harpoon prop"),
    "Current_Shield_IRREGULAR_CURVED_REFERENCE_SHEET_V4_CINEMATIC_FX_V1.png": ("irregular_curved_shield", "Irregular curved water-pressure shield"),
    "BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V2.png": ("abyss_altar_master", "EP00 Abyss Altar MASTER clean environment"),
    "BG_EP00_ABYSS_ALTAR_DAMAGED_CINEMATIC_LIVEACTION_V2.png": ("abyss_altar_damaged", "EP00 Abyss Altar DAMAGED clean environment"),
    "BG_EP00_ABYSS_ALTAR_FINAL_DAMAGE_CINEMATIC_LIVEACTION_V2.png": ("abyss_altar_final_damage", "EP00 Abyss Altar FINAL DAMAGE clean environment"),
    "FX_EP00_BLACK_SPHERE_ISOLATED_R2V_REFERENCE_V2.png": ("black_sphere_isolated", "Isolated dense black sphere material"),
    "FX_EP00_BLACK_RAIN_ISOLATED_R2V_REFERENCE_V2.png": ("black_rain_isolated", "Isolated black-rain membrane and droplet material"),
    "FX_EP00_BLACK_PURSUIT_SPIKES_ISOLATED_R2V_REFERENCE_V2.png": ("black_pursuit_spikes_isolated", "Exactly three isolated black pursuit spikes"),
    "FX_EP00_MOVING_CURRENT_ISOLATED_R2V_REFERENCE_V2.png": ("moving_current_isolated", "Isolated pressured seawater material"),
}

GENERATED_NAMES = {
    "BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V2.png",
    "BG_EP00_ABYSS_ALTAR_DAMAGED_CINEMATIC_LIVEACTION_V2.png",
    "BG_EP00_ABYSS_ALTAR_FINAL_DAMAGE_CINEMATIC_LIVEACTION_V2.png",
    "FX_EP00_BLACK_SPHERE_ISOLATED_R2V_REFERENCE_V2.png",
    "FX_EP00_BLACK_RAIN_ISOLATED_R2V_REFERENCE_V2.png",
    "FX_EP00_BLACK_PURSUIT_SPIKES_ISOLATED_R2V_REFERENCE_V2.png",
    "FX_EP00_MOVING_CURRENT_ISOLATED_R2V_REFERENCE_V2.png",
}

CLIP_RE = re.compile(
    r"^## (?P<clip_id>EP00_C\d{2}) — (?P<title>.+?)\s*$"
    r"(?P<body>.*?)(?=^## EP00_C\d{2} — |^## 4\.|\Z)",
    re.MULTILINE | re.DOTALL,
)
DURATION_RE = re.compile(r"\*\*Target duration:\*\*\s*([0-9.]+) seconds")
INPUT_RE = re.compile(r"^- `<Picture (\d+)>` `([^`]+)`\s*$", re.MULTILINE)
PROMPT_RE = re.compile(r"```text\n(.*?)\n```", re.DOTALL)
SUMMARY_RE = re.compile(r"^summary:\s*\n(.*?)(?=^retention_analysis:)", re.MULTILINE | re.DOTALL)
DIALOGUE_RE = re.compile(r"<d>\[Korean\]\s*(.*?)</d>", re.DOTALL)


def digest_bytes(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prompt_rows() -> list[dict[str, object]]:
    text = PROMPT_DOCUMENT.read_text(encoding="utf-8")
    rows: list[dict[str, object]] = []
    for match in CLIP_RE.finditer(text):
        body = match.group("body")
        duration = DURATION_RE.search(body)
        prompt = PROMPT_RE.search(body)
        if not duration or not prompt:
            raise ValueError(f"Incomplete clip block: {match.group('clip_id')}")
        inputs = sorted([(int(index), name) for index, name in INPUT_RE.findall(body)])
        if [index for index, _name in inputs] != list(range(1, len(inputs) + 1)):
            raise ValueError(f"Non-contiguous Picture order: {match.group('clip_id')}")
        prompt_text = prompt.group(1)
        report = h3_prompt_contract.validate_prompt(
            prompt_text,
            duration_seconds=float(duration.group(1)),
            allow_four_shots=True,
        )
        if not report.valid:
            raise h3_prompt_contract.PromptContractError(report)
        summary = SUMMARY_RE.search(prompt_text)
        rows.append({
            "clip_id": match.group("clip_id"),
            "title": match.group("title").strip(),
            "duration_seconds": float(duration.group(1)),
            "asset_names": [name for _index, name in inputs],
            "video_prompt": prompt_text,
            "summary": summary.group(1).strip() if summary else match.group("title").strip(),
            "required_dialogue": [line.strip() for line in DIALOGUE_RE.findall(prompt_text)],
            "source_prompt_sha256": digest_text(prompt_text),
            "validation": report.as_dict(),
        })
    expected = [f"EP00_C{index:02d}" for index in range(1, 26)]
    if [str(row["clip_id"]) for row in rows] != expected:
        raise ValueError("The V2 source did not yield EP00_C01 through EP00_C25")
    if round(sum(float(row["duration_seconds"]) for row in rows), 3) != 133.5:
        raise ValueError("The V2 duration total is not 133.5 seconds")
    return rows


def asset_check_report(copied: list[dict[str, object]]) -> str:
    return "\n".join([
        "# EP00 Cinematic Live-Action R2V V2 Asset Check Report",
        "",
        "## Result",
        "",
        "- Ready status: 25 clips assembled with project-local Full-Reference assets",
        "- Approved reused assets: 4",
        "- Approved newly generated isolated/clean assets: 7",
        "- Total copied assets: 11",
        "- Missing assets: 0",
        "- Source/copy SHA-256 mismatches: 0",
        "- Picture order source: supplied V2 document only",
        "",
        "## Connected assets",
        "",
        *[f"- `{row['name']}` — `{row['sha256']}`" for row in copied],
        "",
        "## Execution boundary",
        "",
        "- Prompt wording was not rewritten or generated locally.",
        "- Candidate A/D/E contain the same supplied prompt.",
        "- No queue registration, video generation, candidate selection or upscale was performed.",
        "",
    ])


def update_asset_approval(project_path: Path) -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    manifest = json.loads(ASSET_MANIFEST.read_text(encoding="utf-8"))
    manifest["user_approval"] = {
        "status": "approved",
        "recorded_at": now,
        "evidence": "User message: 좋아 승인하고 다음으로 진행해줘",
    }
    manifest["project_assembly"] = {
        "project_id": PROJECT_ID,
        "status": "completed",
        "project_created": True,
        "project_path": str(project_path),
        "picture_linking_performed": True,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    for asset in manifest.get("assets", []):
        asset["approval_status"] = "approved"
        asset["connection_status"] = "connected_project_local_copy"
    ASSET_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = [
        f"| {asset['asset_id']} | `{asset['relative_path']}` | approved | connected |"
        for asset in manifest.get("assets", [])
    ]
    APPROVAL_GATE.write_text("\n".join([
        "# EP00 Isolated R2V Asset Approval Gate V2",
        "",
        "## 승인 결과",
        "",
        f"- 전체 상태: `approved`",
        f"- 승인 기록: `{now}`",
        f"- 연결 프로젝트: `{PROJECT_ID}`",
        "- Picture 연결: 프로젝트 로컬 복사본으로 완료",
        "- 큐·영상 생성: 미실행",
        "",
        "| ID | 파일 | 사용자 승인 | 연결 |",
        "| --- | --- | --- | --- |",
        *rows,
        "",
    ]), encoding="utf-8")


def build() -> dict[str, object]:
    destination = h3_prompt_projects.project_dir(ROOT, PROJECT_ID)
    if destination.exists():
        raise FileExistsError(f"Existing projects are not overwritten: {PROJECT_ID}")
    for path in (PROMPT_DOCUMENT, COMMAND_DOCUMENT, ASSET_MANIFEST, *ASSET_PATHS.values()):
        if not path.is_file():
            raise FileNotFoundError(path)
    approval = json.loads(ASSET_MANIFEST.read_text(encoding="utf-8"))
    current = str(approval.get("user_approval", {}).get("status") or "")
    if current not in {"pending_user_approval", "approved"}:
        raise ValueError(f"Unexpected asset approval status: {current}")

    rows = prompt_rows()
    used_names = {str(name) for row in rows for name in row["asset_names"]}
    if used_names != set(ASSET_PATHS):
        raise ValueError(f"Asset mapping mismatch: {sorted(set(ASSET_PATHS) ^ used_names)}")
    source_text = PROMPT_DOCUMENT.read_text(encoding="utf-8")
    forbidden_counts = {
        "keyframe_completion": len(re.findall(r"\[keyframe completion\]", source_text, re.IGNORECASE)),
        "picture_time_alignment": len(re.findall(r"<Picture \d+>\s+at\s+00:", source_text, re.IGNORECASE)),
        "first_frame_instruction": len(re.findall(r"\bfirst frame\b", "\n".join(str(row["video_prompt"]) for row in rows), re.IGNORECASE)),
        "last_frame_instruction": len(re.findall(r"\blast frame\b", "\n".join(str(row["video_prompt"]) for row in rows), re.IGNORECASE)),
    }
    if any(forbidden_counts.values()):
        raise ValueError(f"Forbidden frame instruction found: {forbidden_counts}")

    base = h3_prompt_projects.projects_root(ROOT)
    base.mkdir(parents=True, exist_ok=True)
    staging = base / f".{PROJECT_ID}.building-{secrets.token_hex(4)}"
    staging.mkdir()
    try:
        manifest = {
            "schema_version": 2,
            "project_kind": h3_prompt_projects.PROJECT_KIND,
            "project_id": PROJECT_ID,
            "title": PROJECT_TITLE,
            "description": "Exact import of the supplied EP00 cinematic live-action V2 Full-Reference H3 R2V prompts with approved project-local assets.",
            "clip_schema": "h3_r2v_clip_v2",
            "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
            "asset_storage": "project_local_shared",
            "source_policy": "user_prompt_exact_document_picture_order",
            "canonical_source_lineage": [PROMPT_DOCUMENT.name, COMMAND_DOCUMENT.name],
            "locked_rule_id": "EP00_CINEMATIC_LIVEACTION_FULL_REFERENCE_R2V_V2",
            "import_script": "scripts/import_ep00_cinematic_liveaction_h3_r2v_v2.py",
            "candidate_policy": "A_equals_D_equals_E_exactly",
            "review_status": "pending_user_prompt_review",
            "build_facts": {
                "scene_count": 1,
                "clip_count": 25,
                "candidate_entry_count": 75,
                "unique_prompt_count": 25,
                "verified_reused_asset_count": 4,
                "approved_generated_asset_count": 7,
                "project_local_asset_count": 11,
                "missing_asset_count": 0,
                "total_duration_seconds": 133.5,
                "keyframe_instruction_count": 0,
            },
            "queue_authorized": False,
            "video_generation_authorized": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        source_dir = staging / "source"
        source_dir.mkdir()
        shutil.copy2(PROMPT_DOCUMENT, source_dir / "EP00_H3_R2V_PROMPT_DOCUMENT_CINEMATIC_LIVEACTION_V2.source.txt")

        shared_dir = staging / "assets/shared"
        shared_dir.mkdir(parents=True)
        copied_assets: list[dict[str, object]] = []
        for name, source in ASSET_PATHS.items():
            target = shared_dir / name
            shutil.copy2(source, target)
            source_hash = digest_bytes(source)
            target_hash = digest_bytes(target)
            if source_hash != target_hash:
                raise ValueError(f"Asset copy SHA-256 mismatch: {name}")
            copied_assets.append({
                "name": name,
                "source_path": str(source),
                "project_path": f"assets/shared/{name}",
                "sha256": source_hash,
                "origin": "approved_generated_v2" if name in GENERATED_NAMES else "approved_reused",
            })

        scene_dir = staging / "EP00-CONTINUOUS"
        scene_dir.mkdir()
        mapping: dict[str, list[dict[str, object]]] = {}
        validation_rows: list[dict[str, object]] = []
        for sequence, row in enumerate(rows, start=1):
            clip_id = str(row["clip_id"])
            prompt = str(row["video_prompt"])
            variants = [{
                "variant_id": candidate,
                "label": f"Candidate {candidate} · supplied original",
                "rationale": "Exact duplicate of the supplied prompt; no local derivation.",
                "video_prompt": prompt,
            } for candidate in ("A", "D", "E")]
            references = []
            for picture_index, asset_name in enumerate(row["asset_names"], start=1):
                role, label = ASSET_ROLES[str(asset_name)]
                references.append({
                    "picture_index": picture_index,
                    "role": role,
                    "label": label,
                    "description": "",
                    "instruction_en": "",
                    "reference_kind": "visual_reference",
                    "required": True,
                    "source_path": f"assets/shared/{asset_name}",
                })
            mapping[clip_id] = references
            payload = {
                "schema_version": 2,
                "prompt_contract_version": h3_prompt_contract.PASSTHROUGH_CONTRACT_VERSION,
                "workflow": h3_prompt_projects.WORKFLOW,
                "project_id": PROJECT_ID,
                "scene_id": "EP00-CONTINUOUS",
                "clip_id": clip_id,
                "source_clip_id": clip_id,
                "sequence": sequence,
                "status": "pending_user_prompt_review",
                "duration_seconds": row["duration_seconds"],
                "title": row["title"],
                "video_prompt": prompt,
                "prompt_variants": variants,
                "references": references,
                "canonical_source_lineage": [PROMPT_DOCUMENT.name],
                "locked_rule_id": "EP00_CINEMATIC_LIVEACTION_FULL_REFERENCE_R2V_V2",
                "summary": row["summary"],
                "required_dialogue": row["required_dialogue"],
                "dialogue_lock_version": "USER_SUPPLIED_EP00_CINEMATIC_LIVEACTION_DIALOGUE_V2",
                "source_prompt_sha256": row["source_prompt_sha256"],
                "candidate_policy": "A=D=E; exact supplied prompt",
                "scene_type": "user_supplied_prompt_import",
                "semantic_review": "not_performed",
            }
            markdown = (
                f"# {clip_id} · {row['title']} · MiniMax H3 R2V\n\n"
                "## Machine Payload\n\n```json\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
            clip_path = scene_dir / f"{clip_id}.md"
            clip_path.write_text(markdown, encoding="utf-8")
            loaded = h3_prompt_projects.extract_payload(clip_path.read_text(encoding="utf-8"))
            if str(loaded["video_prompt"]) != prompt:
                raise ValueError(f"Prompt byte mismatch after clip serialization: {clip_id}")
            if any(str(variant["video_prompt"]) != prompt for variant in loaded["prompt_variants"]):
                raise ValueError(f"Candidate prompt mismatch: {clip_id}")
            validation_rows.append({
                "clip_id": clip_id,
                "duration_seconds": row["duration_seconds"],
                "picture_count": len(references),
                "source_prompt_sha256": row["source_prompt_sha256"],
                "serialized_prompt_sha256": digest_text(str(loaded["video_prompt"])),
                "candidate_prompt_hashes": {variant["variant_id"]: digest_text(str(variant["video_prompt"])) for variant in loaded["prompt_variants"]},
                "contract_validation": row["validation"],
                "byte_equal_to_source": True,
            })

        (staging / "asset_mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (staging / "ASSET_CHECK_REPORT.md").write_text(asset_check_report(copied_assets), encoding="utf-8")
        validation_report = {
            "schema_version": 2,
            "project_id": PROJECT_ID,
            "source_document": PROMPT_DOCUMENT.name,
            "source_document_sha256": digest_bytes(PROMPT_DOCUMENT),
            "valid": True,
            "scene_count": 1,
            "clip_count": 25,
            "candidate_entry_count": 75,
            "unique_prompt_count": 25,
            "total_duration_seconds": 133.5,
            "reference_generation_summary_count": sum(str(row["video_prompt"]).count("[reference generation]") for row in rows),
            "required_dialogue_line_count": sum(len(row["required_dialogue"]) for row in rows),
            "forbidden_instruction_counts": forbidden_counts,
            "asset_copy_count": len(copied_assets),
            "asset_sha256_match_count": len(copied_assets),
            "clips": validation_rows,
        }
        (staging / "PROMPT_VALIDATION_REPORT.json").write_text(json.dumps(validation_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    update_asset_approval(destination)
    return {
        "project_id": PROJECT_ID,
        "project_path": str(destination),
        "scene_count": 1,
        "clip_count": 25,
        "candidate_entry_count": 75,
        "unique_prompt_count": 25,
        "total_duration_seconds": 133.5,
        "project_local_asset_count": 11,
        "approved_reused_asset_count": 4,
        "approved_generated_asset_count": 7,
        "keyframe_instruction_count": 0,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
