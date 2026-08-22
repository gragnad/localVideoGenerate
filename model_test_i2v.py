from __future__ import annotations

"""Project-authored MiniMax H3 first-frame I2V benchmark suites."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import h3_prompt_projects
import model_test_assets


SCENE_SUITE_PREFIX = "h3_scene_i2v_"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def project_scene_suite_id(project_id: str, scene_id: str) -> str:
    digest = hashlib.sha256(f"{project_id}\0{scene_id}".encode("utf-8")).hexdigest()[:20]
    return f"{SCENE_SUITE_PREFIX}{digest}_v1"


def is_i2v_suite_id(suite_id: str) -> bool:
    return str(suite_id or "").startswith(SCENE_SUITE_PREFIX)


def registered_project_targets(root: Path) -> list[dict[str, Any]]:
    """Return the newest I2V scene registration for each project and scene."""
    targets: dict[tuple[str, str], tuple[tuple[str, str, str], dict[str, Any]]] = {}
    base = root / "runtime/h3/project_test_sets"
    if not base.is_dir():
        return []
    for path in base.glob("*/project_test_set.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("deleted") or payload.get("deleted_at") or payload.get("status") == "deleted":
            continue
        try:
            schema_version = int(payload.get("schema_version") or 1)
        except (TypeError, ValueError):
            schema_version = 1
        if schema_version < 3 or str(payload.get("generation_mode") or "").lower() != "i2v":
            continue
        if str(payload.get("scope") or "") != "scene":
            continue
        project_id = str(payload.get("project_id") or "").strip()
        scene_id = str(payload.get("scene_id") or "").strip()
        if not project_id or not scene_id:
            continue
        raw_clip_ids = payload.get("clip_ids")
        if not isinstance(raw_clip_ids, list):
            raw_clip_ids = [
                row.get("clip_id")
                for row in (payload.get("clips") or [])
                if isinstance(row, dict)
            ]
        clip_ids = list(dict.fromkeys(
            str(value or "").strip() for value in raw_clip_ids if str(value or "").strip()
        ))
        target = {
            "project_id": project_id,
            "scene_id": scene_id,
            "clip_ids": clip_ids,
            "schema_version": schema_version,
            "generation_mode": "i2v",
            "project_test_set_id": str(payload.get("project_test_set_id") or path.parent.name),
        }
        rank = (
            str(payload.get("created_at") or payload.get("updated_at") or ""),
            str(payload.get("updated_at") or payload.get("created_at") or ""),
            target["project_test_set_id"],
        )
        key = (project_id, scene_id)
        current = targets.get(key)
        if current is None or rank > current[0]:
            targets[key] = (rank, target)
    return [targets[key][1] for key in sorted(targets)]


def _project_reference_path(project_dir: Path, source_path: str) -> Path:
    base = project_dir.resolve()
    path = (base / str(source_path or "")).resolve()
    if base not in path.parents or not path.is_file():
        raise FileNotFoundError(f"H3 I2V 시작 이미지를 찾을 수 없습니다: {source_path}")
    return path


def _case_ids(project_id: str, clip_id: str) -> tuple[str, str]:
    project_token = hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:12]
    clip_token = re.sub(r"[^a-z0-9]+", "_", clip_id.lower()).strip("_")
    case_id = f"h3_i2v_project_{project_token}_{clip_token}"
    return case_id, f"{case_id}_v1"


def _asset_signature(
    project_dir: Path, asset: dict[str, Any] | None
) -> tuple[dict[str, Any] | None, int]:
    if not asset:
        return None, 0
    signature = {
        "role": asset.get("role"),
        "label": asset.get("label"),
        "description": asset.get("description"),
        "source_path": asset.get("source_path"),
        "linked": asset.get("linked"),
    }
    if not asset.get("linked"):
        return signature, 0
    path = _project_reference_path(project_dir, str(asset.get("source_path") or ""))
    stat = path.stat()
    signature.update(size_bytes=stat.st_size, modified_ns=stat.st_mtime_ns)
    return signature, 1


def ensure_project_scene_suite(
    root: Path,
    connection,
    project_id: str,
    scene_id: str,
    clip_ids: list[str],
) -> dict[str, Any] | None:
    """Expose one registered I2V scene with its authored start/last frames."""
    project_dir = h3_prompt_projects.project_dir(root, project_id)
    if not project_dir.is_dir():
        return None
    overview = h3_prompt_projects.project_clips(root, project_id)
    if overview.get("generation_mode") != "i2v":
        return None
    clips_by_id = {
        str(clip.get("clip_id") or ""): clip
        for clip in overview.get("clips") or []
        if str(clip.get("scene_id") or "") == scene_id
    }
    clips = [clips_by_id[clip_id] for clip_id in clip_ids if clip_id in clips_by_id]
    if not clips:
        return None
    project = next(
        (
            row for row in h3_prompt_projects.list_projects(root).get("projects") or []
            if row.get("project_id") == project_id
        ),
        {"title": project_id},
    )
    signature_rows = []
    expected_links = 0
    for clip in clips:
        start = clip.get("start_image") or (clip.get("references") or [{}])[0]
        last = clip.get("last_image")
        start_signature, start_links = _asset_signature(project_dir, start)
        last_signature, last_links = _asset_signature(project_dir, last)
        expected_links += start_links + last_links
        signature_rows.append({
            "scene_id": clip.get("scene_id"),
            "clip_id": clip.get("clip_id"),
            "sequence": clip.get("sequence"),
            "duration_seconds": clip.get("duration_seconds"),
            "video_prompt": clip.get("video_prompt"),
            "start_image": start_signature,
            "last_image": last_signature,
        })
    suite_id = project_scene_suite_id(project_id, scene_id)
    definition_sha = _sha({
        "suite_id": suite_id,
        "project_id": project_id,
        "scene_id": scene_id,
        "clips": signature_rows,
    })
    current = connection.execute(
        "SELECT definition_sha256 FROM benchmark_suites WHERE suite_id=?", (suite_id,)
    ).fetchone()
    case_count = connection.execute(
        "SELECT COUNT(*) count FROM suite_cases WHERE suite_id=? AND enabled=1", (suite_id,)
    ).fetchone()["count"] if current else 0
    linked_count = connection.execute(
        """SELECT COUNT(*) count FROM benchmark_case_assets a
             JOIN suite_cases s ON s.case_version_id=a.case_version_id
            WHERE s.suite_id=? AND s.enabled=1""",
        (suite_id,),
    ).fetchone()["count"] if current else 0
    if (
        current
        and current["definition_sha256"] == definition_sha
        and int(case_count) == len(clips)
        and int(linked_count) == expected_links
    ):
        connection.execute("UPDATE benchmark_suites SET active=1 WHERE suite_id=?", (suite_id,))
        return {
            "suite_id": suite_id,
            "project_id": project_id,
            "scene_id": scene_id,
            "case_count": len(clips),
            "asset_count": expected_links,
            "changed": False,
        }

    title = str(project.get("title") or project_id)
    name = f"{title} · {scene_id} 씬 I2V · {project_id}"
    description = (
        f"02 H3 I2V 생성 프로젝트의 {scene_id} 씬을 클립별 원본 프롬프트와 "
        "시작 이미지 그대로 검증한다."
    )
    connection.execute(
        """INSERT INTO benchmark_suites
               (suite_id,name,version,description,tier,definition_sha256,active)
           VALUES (?,?,1,?,'project_validation',?,1)
           ON CONFLICT(suite_id) DO UPDATE SET name=excluded.name,version=excluded.version,
               description=excluded.description,tier=excluded.tier,
               definition_sha256=excluded.definition_sha256,active=1""",
        (suite_id, name, description, definition_sha),
    )
    connection.execute("DELETE FROM suite_cases WHERE suite_id=?", (suite_id,))
    for ordering, clip in enumerate(clips, start=1):
        clip_id = str(clip["clip_id"])
        case_id, case_version_id = _case_ids(project_id, clip_id)
        start = clip.get("start_image") or (clip.get("references") or [{}])[0]
        last = clip.get("last_image")
        intent_ko = (
            f"{scene_id}의 {clip_id} 클립을 프로젝트 시작 이미지와 원본 프롬프트로 재현한다. "
            f"{str(clip.get('review_intent_ko') or '').strip()}"
        ).strip()
        duration = float(clip.get("duration_seconds") or 5)
        contract = {
            "input_mode": "i2v_fixed_anchor",
            "source_project_id": project_id,
            "source_scene_id": scene_id,
            "source_clip_id": clip_id,
            "required_events": ["원본 H3 I2V 프롬프트의 사건 순서와 종료 상태를 재현"],
            "forbidden_failures": [
                "시작 이미지의 인물·배경·구도 무시",
                "행동 순서 누락",
                "시각적 정체성 또는 공간의 급격한 변경",
                "의도하지 않은 장면 전환",
            ],
            "scoring_dimensions": [
                "scenario_comprehension", "prompt_adherence", "motion_physics",
                "character_identity", "scene_continuity", "camera_direction",
                "visual_temporal_quality",
            ],
            "generation": {
                "target_seconds": duration,
                "frame_count": int(round(duration * 24)) + 1,
                "fps": 24,
                "width": 832,
                "height": 480,
            },
            "parameters": {},
            "dialogue": [],
        }
        case_title = f"{clip_id} · {title}"
        prompt = str(clip.get("video_prompt") or "")
        definition = {"title": case_title, "intent_ko": intent_ko, "contract": contract, "prompt": prompt}
        connection.execute(
            """INSERT INTO benchmark_cases
                   (case_id,title,intent_ko,intent_json,category,tags_json,source_kind)
               VALUES (?,?,?,?,?,?,'h3_prompt_project')
               ON CONFLICT(case_id) DO UPDATE SET title=excluded.title,intent_ko=excluded.intent_ko,
                   intent_json=excluded.intent_json,category=excluded.category,tags_json=excluded.tags_json""",
            (
                case_id, case_title, intent_ko, _json(contract), "i2v_project_clip",
                _json(["minimax_h3", "i2v", "project_validation", project_id, scene_id]),
            ),
        )
        connection.execute(
            """INSERT INTO benchmark_case_versions
                   (case_version_id,case_id,version,title,intent_ko,category,tier,contract_json,definition_sha256)
               VALUES (?,?,1,?,?,?,'project_validation',?,?)
               ON CONFLICT(case_version_id) DO UPDATE SET title=excluded.title,
                   intent_ko=excluded.intent_ko,category=excluded.category,tier=excluded.tier,
                   contract_json=excluded.contract_json,definition_sha256=excluded.definition_sha256""",
            (
                case_version_id, case_id, case_title, intent_ko, "i2v_project_clip",
                _json(contract), _sha(definition),
            ),
        )
        connection.execute(
            """INSERT OR REPLACE INTO benchmark_case_prompts
                   (case_version_id,language,prompt_kind,prompt_text,prompt_sha256)
               VALUES (?,'en','canonical',?,?)""",
            (case_version_id, prompt, hashlib.sha256(prompt.encode("utf-8")).hexdigest()),
        )
        connection.execute("DELETE FROM benchmark_case_assets WHERE case_version_id=?", (case_version_id,))
        connection.execute("DELETE FROM benchmark_case_asset_requirements WHERE case_version_id=?", (case_version_id,))
        connection.execute(
            """INSERT INTO benchmark_case_asset_requirements
                   (case_version_id,role,kind,minimum_count,description)
               VALUES (?,'reference_image','image',1,?)""",
            (case_version_id, f"I2V 시작 이미지 · {start.get('label') or '첫 프레임'}"),
        )
        if start.get("linked"):
            asset_path = _project_reference_path(project_dir, str(start.get("source_path") or ""))
            model_test_assets.save_and_link(root, connection, {
                "case_version_id": case_version_id,
                "role": "reference_image",
                "upload_path": str(asset_path),
                "original_name": asset_path.name,
            })
        if last:
            connection.execute(
                """INSERT INTO benchmark_case_asset_requirements
                       (case_version_id,role,kind,minimum_count,description)
                   VALUES (?,'last_reference_image','image',1,?)""",
                (
                    case_version_id,
                    f"FFLF 종료 이미지 · {last.get('label') or '마지막 프레임'}",
                ),
            )
            if last.get("linked"):
                asset_path = _project_reference_path(
                    project_dir, str(last.get("source_path") or "")
                )
                model_test_assets.save_and_link(root, connection, {
                    "case_version_id": case_version_id,
                    "role": "last_reference_image",
                    "upload_path": str(asset_path),
                    "original_name": asset_path.name,
                })
        connection.execute(
            "INSERT INTO suite_cases(suite_id,case_version_id,ordering,enabled) VALUES (?,?,?,1)",
            (suite_id, case_version_id, ordering),
        )
    connection.commit()
    return {
        "suite_id": suite_id,
        "project_id": project_id,
        "scene_id": scene_id,
        "case_count": len(clips),
        "asset_count": expected_links,
        "changed": True,
    }


def ensure_registered_project_suites(root: Path, connection) -> list[dict[str, Any]]:
    connection.execute(
        "UPDATE benchmark_suites SET active=0 WHERE suite_id GLOB ?",
        (f"{SCENE_SUITE_PREFIX}*",),
    )
    results = []
    for target in registered_project_targets(root):
        result = ensure_project_scene_suite(
            root,
            connection,
            str(target["project_id"]),
            str(target["scene_id"]),
            list(target.get("clip_ids") or []),
        )
        if result:
            result["project_test_set_id"] = target["project_test_set_id"]
            results.append(result)
    return results
