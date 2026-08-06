from __future__ import annotations

"""Portable benchmark exports that omit local paths and redact secret-like text."""

import csv
import hashlib
import io
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import evaluation_db
from job_queue import now_iso
import model_test_registry

_SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|access[_-]?key|token|password|secret)(\s*[:=]\s*)([^\s,;]+)")


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _SECRET_PATTERN.sub(r"\1\2[REDACTED]", value)
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    return value


def _rows(connection, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(query, params)]


def _latest_reviews(connection) -> list[dict[str, Any]]:
    from model_test_reviews import effective_latest_reviews
    return sorted(effective_latest_reviews(connection), key=lambda row: row["run_id"])


def portable_payload(root: Path) -> dict[str, Any]:
    with model_test_registry.open_registry(root) as connection:
        reviews = _latest_reviews(connection)
        review_ids = [row["review_version_id"] for row in reviews]
        issues: list[dict[str, Any]] = []
        scores: list[dict[str, Any]] = []
        if review_ids:
            placeholders = ",".join("?" for _ in review_ids)
            issues = _rows(connection, f"SELECT * FROM review_issues WHERE review_version_id IN ({placeholders}) ORDER BY review_version_id,issue_id", tuple(review_ids))
            scores = _rows(connection, f"SELECT * FROM capability_scores WHERE review_version_id IN ({placeholders}) ORDER BY review_version_id,dimension", tuple(review_ids))
        payload = {
            "export_schema": "video_model_benchmark_portable_v1",
            "database_schema_version": evaluation_db.SCHEMA_VERSION,
            "exported_at": now_iso(),
            "models": _rows(connection, "SELECT model_id,provider,family,display_name,version,modality,checkpoint_sha256,source_url,license_name,capabilities_json,created_at FROM models ORDER BY model_id"),
            "model_runtimes": _rows(connection, "SELECT runtime_id,model_id,engine,engine_version,dtype,quantization,device_profile,created_at FROM model_runtimes ORDER BY runtime_id"),
            "benchmark_cases": _rows(connection, "SELECT * FROM benchmark_cases ORDER BY case_id"),
            "benchmark_case_versions": _rows(connection, "SELECT * FROM benchmark_case_versions ORDER BY case_id,version"),
            "benchmark_suites": _rows(connection, "SELECT * FROM benchmark_suites ORDER BY name,version"),
            "suite_cases": _rows(connection, "SELECT * FROM suite_cases ORDER BY suite_id,ordering"),
            "case_prompts": _rows(connection, "SELECT * FROM benchmark_case_prompts ORDER BY case_version_id,language,prompt_kind"),
            "assets": _rows(connection, "SELECT asset_id,kind,sha256,metadata_json,created_at FROM assets ORDER BY asset_id"),
            "workflow_profiles": _rows(connection, "SELECT workflow_profile_id,model_id,name,profile_kind,workflow_filename,workflow_sha256,workflow_format,source_url,notes,created_at FROM workflow_profiles ORDER BY workflow_profile_id"),
            "test_sessions": _rows(connection, "SELECT * FROM test_sessions ORDER BY created_at"),
            "test_session_lineage": _rows(connection, "SELECT * FROM test_session_lineage ORDER BY created_at"),
            "test_session_cases": _rows(connection, "SELECT * FROM test_session_cases ORDER BY session_id,ordering"),
            "test_session_runs": _rows(connection, "SELECT * FROM test_session_runs ORDER BY session_id,case_version_id,repetition"),
            "generation_runs": _rows(connection, """SELECT run_id,job_id,case_id,model_id,runtime_id,prompt_variant_id,
                workflow_kind,workflow_filename,workflow_sha256,seed_text,seed_mode,width,height,fps,frame_count,
                duration_seconds,generation_seconds,peak_gpu_memory_bytes,peak_system_memory_bytes,status,
                output_sha256,created_at FROM generation_runs ORDER BY created_at"""),
            "latest_reviews": reviews,
            "review_issues": issues,
            "capability_scores": scores,
            "prompt_policies": _rows(connection, "SELECT * FROM prompt_policies ORDER BY model_id,dimension,created_at"),
            "prompt_policy_scopes": _rows(connection, "SELECT * FROM prompt_policy_scopes ORDER BY policy_id"),
        }
    return _redact(payload)


def _csv_text(payload: dict[str, Any]) -> str:
    review_by_run = {row["run_id"]: row for row in payload["latest_reviews"]}
    scores_by_review: dict[str, list[float]] = {}
    for score in payload["capability_scores"]:
        scores_by_review.setdefault(score["review_version_id"], []).append(float(score["score"]))
    issue_count: dict[str, int] = {}
    for issue in payload["review_issues"]:
        issue_count[issue["review_version_id"]] = issue_count.get(issue["review_version_id"], 0) + 1
    session_by_run = {row["run_id"]: row for row in payload["test_session_runs"]}
    sessions = {row["session_id"]: row for row in payload["test_sessions"]}
    cases = {row["case_id"]: row for row in payload["benchmark_cases"]}
    models = {row["model_id"]: row for row in payload["models"]}
    stream = io.StringIO()
    fields = [
        "run_id", "session_id", "model_id", "model_name", "case_id", "case_title",
        "status", "workflow_kind", "workflow_filename", "seed", "width", "height", "fps",
        "frame_count", "generation_seconds", "peak_gpu_memory_bytes", "peak_system_memory_bytes",
        "verdict", "review_revision", "issue_count", "average_score",
    ]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for run in payload["generation_runs"]:
        link = session_by_run.get(run["run_id"], {})
        session = sessions.get(link.get("session_id"), {})
        review = review_by_run.get(run["run_id"], {})
        values = scores_by_review.get(review.get("review_version_id"), [])
        writer.writerow({
            "run_id": run["run_id"],
            "session_id": link.get("session_id", ""),
            "model_id": run["model_id"],
            "model_name": models.get(run["model_id"], {}).get("display_name", ""),
            "case_id": run["case_id"],
            "case_title": cases.get(run["case_id"], {}).get("title", ""),
            "status": run["status"],
            "workflow_kind": run.get("workflow_kind", ""),
            "workflow_filename": run.get("workflow_filename", ""),
            "seed": run.get("seed_text", ""),
            "width": run.get("width", ""),
            "height": run.get("height", ""),
            "fps": run.get("fps", ""),
            "frame_count": run.get("frame_count", ""),
            "generation_seconds": run.get("generation_seconds", ""),
            "peak_gpu_memory_bytes": run.get("peak_gpu_memory_bytes", ""),
            "peak_system_memory_bytes": run.get("peak_system_memory_bytes", ""),
            "verdict": review.get("verdict", ""),
            "review_revision": review.get("revision", ""),
            "issue_count": issue_count.get(review.get("review_version_id"), 0),
            "average_score": round(sum(values) / len(values), 3) if values else "",
        })
    return stream.getvalue()


def create_export(root: Path, export_format: str) -> dict[str, Any]:
    export_format = str(export_format or "json").lower()
    if export_format not in {"json", "csv"}:
        raise ValueError("내보내기는 json 또는 csv 형식만 지원합니다.")
    payload = portable_payload(root)
    if export_format == "json":
        content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        mime_type = "application/json; charset=utf-8"
    else:
        content = _csv_text(payload).encode("utf-8-sig")
        mime_type = "text/csv; charset=utf-8"
    digest = hashlib.sha256(content).hexdigest()
    export_dir = root / "runtime/evaluation/exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    filename = f"model_benchmark_{datetime.now():%Y%m%d_%H%M%S}_{digest[:8]}.{export_format}"
    path = export_dir / filename
    temporary = export_dir / f".{filename}.tmp"
    temporary.write_bytes(content)
    temporary.replace(path)
    return {
        "path": str(path),
        "filename": filename,
        "mime_type": mime_type,
        "sha256": digest,
        "size_bytes": len(content),
    }
