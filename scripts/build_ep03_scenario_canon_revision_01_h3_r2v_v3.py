#!/usr/bin/env python3
"""Package the approved EP03 V3 prompts; never submit generation jobs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import h3_prompt_projects

PROJECT_ID = "RaisingaDragonSeason01_EP03_SCENARIO_CANON_REVISION_01_H3_R2V_V3"
DEST = ROOT / "prompt_projects" / PROJECT_ID
PRODUCTION = ROOT / "projects/RaisingaDragonSeason01"
PROMPTS = PRODUCTION / "EP03_H3_PROMPTS_V3"
SCENARIO = Path("/home/nalstudio/.codex/attachments/41140e6e-b4fc-4341-9194-983292307f03/EP03_Scenario_Canon_Revision_01.md")
VALIDATOR = Path("/home/nalstudio/.codex/skills/minimax-h3-basic-production-director-raising-a-dragon/scripts/validate_h3_production.py")
SCENES = {"S1": "EP03-S01-INK-FOG", "S2": "EP03-S02-FIRST-RESCUE", "S3": "EP03-S03-HOLD-THE-MOMENT", "S4": "EP03-S04-JELLYFISH-DEFEAT"}
ROLES = {"coast": "environment", "extended_coast": "environment", "lua": "character_identity", "mir_bruised": "character_state_identity", "jellyfish": "creature_type", "harpoon": "prop", "sigil": "event_detail", "anchor_c07": "single_event_anchor", "anchor_c14": "single_event_anchor", "anchor_c16": "single_event_anchor"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    if DEST.exists():
        raise FileExistsError(f"Existing project preserved: {DEST}")
    plan = json.loads((PROMPTS / "REFERENCE_MAP_V3.json").read_text())
    audit = json.loads((PROMPTS / "VALIDATION_RESULTS_V3.json").read_text())
    expected = {c["clip_id"]: c for c in audit["clips"]}
    assert len(plan["clips"]) == len(expected) == 21
    for asset in plan["assets"]:
        assert digest(Path(asset["path"])) == asset["sha256"], asset["asset_key"]
    for clip in plan["clips"]:
        assert digest(PROMPTS / clip["prompt_file"]) == expected[clip["clip_id"]]["sha256"], clip["clip_id"]
    titles = dict(re.findall(r"^## (EP03_C\d+)\. (.+)$", SCENARIO.read_text(), re.M))
    assert len(titles) == 21
    # A temporary packaging root allows the normal UI loader to verify the new ID.
    staging_root = Path(tempfile.mkdtemp(prefix="ep03-v3-build-"))
    project = staging_root / "prompt_projects" / PROJECT_ID
    source = project / "source"
    source.mkdir(parents=True)
    shutil.copytree(PROMPTS, source / "prompts")
    for path in [SCENARIO, PRODUCTION / "EP03_H3_INHERITANCE_AND_DIRECTION_BRIEF_V2.md", PRODUCTION / "H3_R2V_PRODUCTION_CANON_V2.md", PRODUCTION / "EP03_H3_ASSETS_V1/EP03_ASSET_AUDIT_V1.md"]:
        shutil.copy2(path, source / path.name)
    shutil.copy2(PRODUCTION / "EP03_H3_ASSETS_V1/ASSET_MANIFEST.json", source / "EP03_ASSET_MANIFEST_V1.json")
    assets = {}
    for asset in plan["assets"]:
        origin = Path(asset["path"])
        local = Path("assets") / origin.parent.name / origin.name
        target = project / local
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
        assert digest(target) == asset["sha256"]
        assets[asset["asset_key"]] = {**asset, "source_path": str(origin), "project_path": local.as_posix(), "hash_verified": True}
    scene_counts, bindings = {}, {}
    lineage = ["source/EP03_Scenario_Canon_Revision_01.md", "source/H3_R2V_PRODUCTION_CANON_V2.md", "source/EP03_H3_INHERITANCE_AND_DIRECTION_BRIEF_V2.md", "source/prompts/DIRECTION_NOTES_V3.md", "source/prompts/REFERENCE_MAP_V3.json"]
    for sequence, clip in enumerate(plan["clips"], 1):
        cid = clip["clip_id"]
        sid = SCENES[clip["story_scene"]]
        scene_counts[sid] = scene_counts.get(sid, 0) + 1
        prompt = (PROMPTS / clip["prompt_file"]).read_text().strip()
        refs = []
        for row in clip["references"]:
            key = row["asset_key"]
            refs.append({"picture_index": row["picture_index"], "asset_key": key, "role": ROLES[key], "label": key, "description": row["reference_reason"], "reference_reason": row["reference_reason"], "instruction_en": "Apply the scope and priority stated in the V3 subject definitions and retention analysis.", "reference_kind": "visual_reference", "required": True, "source_path": assets[key]["project_path"]})
        assert sorted(set(map(int, re.findall(r"<Picture (\d+)>", prompt)))) == [r["picture_index"] for r in refs]
        assert refs[0]["role"] == "environment"
        bindings[cid] = refs
        payload = {"schema_version": 2, "prompt_contract_version": "h3_user_supplied_passthrough_v5", "workflow": "h3_r2v_production", "project_id": PROJECT_ID, "scene_id": sid, "clip_id": cid, "source_clip_id": cid, "sequence": sequence, "scene_sequence": scene_counts[sid], "status": "ready", "title": titles[cid], "duration_seconds": clip["duration_seconds"], "edit_target_seconds": clip["edit_target_seconds"], "video_prompt": prompt, "references": refs, "reference_mode": clip["reference_mode"], "source_prompt_document": "source/prompts/" + clip["prompt_file"], "source_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "source_file_sha256": digest(PROMPTS / clip["prompt_file"]), "video_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "canonical_source_lineage": lineage, "queue_authorized": False, "video_generation_authorized": False}
        directory = project / sid
        directory.mkdir(exist_ok=True)
        (directory / (cid + ".md")).write_text(f"# {cid} · {titles[cid]} · H3 R2V V3\n\n## Machine Payload\n\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    facts = {"scene_count": len(scene_counts), "clip_count": 21, "shot_count": sum(c["shot_count"] for c in audit["clips"]), "project_local_asset_count": len(assets), "reference_binding_count": sum(map(len, bindings.values())), "basic_r2v_clip_count": 18, "single_event_anchor_clip_count": 3, "total_duration_seconds": sum(c["duration_seconds"] for c in plan["clips"]), "edit_target_seconds": sum(c["edit_target_seconds"] for c in plan["clips"]), "queue_entry_count": 0}
    write_json(project / "manifest.json", {"schema_version": 2, "project_kind": "h3_r2v_production", "project_id": PROJECT_ID, "title": "Raising a Dragon EP03 · 이번에는 놓치지 않는다 · H3 R2V V3", "description": "Approved V3 prompts, four story scenes, project-local verified references and three event anchors.", "clip_schema": "h3_r2v_clip_v2", "prompt_contract_version": "h3_user_supplied_passthrough_v5", "canonical_source_lineage": lineage, "asset_storage": "project_local_verified_full_reference_assets", "build_script": "scripts/build_ep03_scenario_canon_revision_01_h3_r2v_v3.py", "review_status": "ready_for_user_generation_authorization", "queue_authorized": False, "video_generation_authorized": False, "queue_registration_performed": False, "video_generation_performed": False, "scene_counts": scene_counts, "build_facts": facts})
    write_json(project / "asset_mapping.json", {"schema_version": 2, "project_id": PROJECT_ID, "assets": list(assets.values()), "clip_bindings": bindings})
    validation = subprocess.run([sys.executable, str(VALIDATOR), "project", str(project)], capture_output=True, text=True, check=True)
    report = json.loads(validation.stdout)
    assert report["valid"]
    loaded = h3_prompt_projects.project_clips(staging_root, PROJECT_ID)
    assert len(loaded["clips"]) == 21 and all(c["ready"] for c in loaded["clips"])
    for c in loaded["clips"]:
        assert c["video_prompt"] == (PROMPTS / (c["clip_id"] + ".md")).read_text().strip()
        assert all(r["linked"] for r in c["references"])
    # Store final paths in the validation evidence, then publish the verified package.
    report = json.loads(json.dumps(report).replace(str(project), str(DEST)))
    write_json(project / "PROJECT_VALIDATION_V3.json", {"structure": report, "loader_ready_count": 21, "all_prompts_match_v3": True, "all_asset_hashes_match": True, "build_facts": facts})
    (project / "README.md").write_text("# EP03 H3 R2V V3 프로젝트\n\nV3 프롬프트 21개를 원문 네 장면 구조로 연결했다. 생성 계획 148초, 편집 목표 146초이며 C12·C15만 생성 최소 길이 4초를 적용한다.\n\n승인 자산 10개와 Picture 연결 69개를 검증했다. 공식 구조 오류·경고 0, UI 로더 준비 완료 21/21.\n\nC06 문양, C07·C14·C16 사건 앵커와 C08 이후 확장 배경을 연결했다. 앵커의 한계와 부분 보존 범위는 [연출 기록](source/prompts/DIRECTION_NOTES_V3.md)에 있다.\n\n[검증 결과](PROJECT_VALIDATION_V3.json) · [자산 연결](asset_mapping.json) · [프롬프트 합본](source/prompts/EP03_H3_PROMPTS_V3_ALL.md)\n\nsource/prompts의 실행 상태 문장은 프롬프트 작성 시점의 보관 기록이다. 현재 프로젝트 생성은 완료했으며 영상 생성·큐 등록은 수행하지 않았다.\n", encoding="utf-8")
    assert not DEST.exists()
    # Same-workspace staging is unnecessary; move handles /tmp on a separate device.
    shutil.move(str(project), str(DEST))
    print(json.dumps({"project_path": str(DEST), **facts, "loader_ready_count": 21}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()
