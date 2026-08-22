from __future__ import annotations

"""Manual, batch-free queue for model-test AI reviews."""

import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

import benchmark_jobs
import engine_scheduler
import h3_queue
import model_test_registry
from job_queue import atomic_write_json, now_iso, read_json, update_status


def queue_root(root: Path) -> Path:
    return root / "runtime/model_test_review_queue"


def completed_generation_job_ids(root: Path, session_id: str) -> list[str]:
    with model_test_registry.open_registry(root) as connection:
        rows = connection.execute(
            """SELECT r.job_id FROM test_session_runs sr
                 JOIN generation_runs r ON r.run_id=sr.run_id
                 JOIN test_session_cases sc
                   ON sc.session_id=sr.session_id
                  AND sc.case_version_id=sr.case_version_id
                WHERE sr.session_id=? AND r.status='completed'
                ORDER BY sc.ordering,sr.repetition,r.job_id""", (session_id,),
        ).fetchall()
    job_ids = []
    for row in rows:
        job_id = str(row["job_id"])
        try:
            h3_queue.resolve_job_dir(root, job_id)
            job_ids.append(job_id)
        except FileNotFoundError:
            continue
    return job_ids


def session_generation_job_ids(root: Path, session_id: str) -> list[str]:
    """Return every persisted H3 job for a session, including queued/running jobs."""
    with model_test_registry.open_registry(root) as connection:
        rows = connection.execute(
            """SELECT r.job_id FROM test_session_runs sr
                 JOIN generation_runs r ON r.run_id=sr.run_id
                 JOIN test_session_cases sc
                   ON sc.session_id=sr.session_id
                  AND sc.case_version_id=sr.case_version_id
                WHERE sr.session_id=?
                ORDER BY sc.ordering,sr.repetition,r.job_id""",
            (session_id,),
        ).fetchall()
    job_ids = []
    for row in rows:
        job_id = str(row["job_id"] or "").strip()
        if not job_id:
            continue
        try:
            h3_queue.resolve_job_dir(root, job_id)
            job_ids.append(job_id)
        except FileNotFoundError:
            continue
    return job_ids


def _latest_failed_review_job_ids(root: Path, session_id: str) -> list[str]:
    """Return only failed items from the latest terminal partial review."""
    for directory in sorted(queue_root(root).glob("review_*"), reverse=True):
        request = read_json(directory / "request.json", {}) or {}
        if request.get("session_id") != session_id:
            continue
        status = read_json(directory / "status.json", {}) or {}
        if status.get("status") not in {"completed_with_failures", "failed"}:
            continue
        summary = read_json(directory / "summary.json", {}) or {}
        return [
            str(item.get("job_id") or "").strip()
            for item in (summary.get("errors") or [])
            if isinstance(item, dict) and str(item.get("job_id") or "").strip()
        ]
    return []


def resolved_generation_job_ids(root: Path, request: dict[str, Any]) -> list[str]:
    """Resolve completed videos while preserving an explicit failed-only retry."""
    completed = completed_generation_job_ids(root, str(request.get("session_id") or ""))
    if request.get("target_scope") != "latest_failed_reviews":
        return completed
    requested = {
        str(job_id).strip()
        for job_id in (request.get("generation_job_ids") or [])
        if str(job_id).strip()
    }
    return [job_id for job_id in completed if job_id in requested]


def enqueue(root: Path, session_id: str) -> dict[str, Any]:
    session_id = str(session_id or "").strip()
    if not session_id:
        raise ValueError("테스트 세션 ID가 필요합니다.")
    with model_test_registry.open_registry(root) as connection:
        session = connection.execute("SELECT session_id FROM test_sessions WHERE session_id=?", (session_id,)).fetchone()
        if not session:
            raise FileNotFoundError("테스트 세션을 찾을 수 없습니다.")
    all_job_ids = session_generation_job_ids(root, session_id)
    if not all_job_ids:
        raise RuntimeError("먼저 모델 테스트를 H3 생성 큐에 등록하세요.")
    for directory in queue_root(root).glob("review_*"):
        request = read_json(directory / "request.json", {}) or {}
        status = read_json(directory / "status.json", {}) or {}
        if request.get("session_id") == session_id and status.get("status") in {
            "queued", "preparing", "reviewing", "cancel_requested",
        }:
            return {**request, "status": status.get("status"), "already_queued": True}
    failed_job_ids = set(_latest_failed_review_job_ids(root, session_id))
    job_ids = [job_id for job_id in all_job_ids if job_id in failed_job_ids]
    target_scope = "latest_failed_reviews" if job_ids else "session_completed_at_execution"
    if not job_ids:
        job_ids = all_job_ids
    queue_id = f"review_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(3)}"
    directory = queue_root(root) / queue_id
    created = now_iso()
    request = {"schema_version": 1, "queue_id": queue_id, "queue_name": "model_test_review", "job_type": "model_test_ai_review", "session_id": session_id, "generation_job_ids": job_ids, "target_scope": target_scope, "created_at": created}
    stage = "H3·ComfyUI 생성 큐 완료 후 AI 검수 대기" if (engine_scheduler.h3_generation_pending(root) or engine_scheduler.comfy_work_active()) else "수동 AI 검수 Worker 대기"
    atomic_write_json(directory / "request.json", request)
    atomic_write_json(directory / "status.json", {"queue_id": queue_id, "status": "queued", "stage": stage, "progress": 0, "created_at": created, "updated_at": created})
    benchmark_jobs.set_session_review_status(root, [session_id], "ai_review_queued")
    return {**request, "status": "queued", "queued_count": len(job_ids)}


def list_queue(root: Path) -> list[dict[str, Any]]:
    base = queue_root(root)
    if not base.exists():
        return []
    entries = [
        {
            "request": read_json(path / "request.json", {}) or {},
            "status": read_json(path / "status.json", {}) or {},
        }
        for path in base.iterdir() if path.is_dir()
    ]
    return sorted(
        entries,
        key=lambda item: str((item.get("request") or {}).get("created_at") or ""),
        reverse=True,
    )


def cancel(root: Path, session_id: str) -> dict[str, Any]:
    session_id = str(session_id or "").strip()
    for directory in sorted(queue_root(root).glob("review_*"), reverse=True):
        request = read_json(directory / "request.json", {}) or {}
        status = read_json(directory / "status.json", {}) or {}
        if request.get("session_id") != session_id or status.get("status") not in {"queued", "preparing", "reviewing"}:
            continue
        active = status.get("status") != "queued"
        update_status(directory, "cancel_requested" if active else "cancelled", stage="사용자 검수 중단 요청", cancel_requested=True, cancelled_at=now_iso())
        benchmark_jobs.set_session_review_status(
            root,
            [session_id],
            "review_cancel_requested" if active else "review_cancelled",
        )
        return {"session_id": session_id, "queue_id": directory.name, "cancelled_review_count": len(request.get("generation_job_ids") or []), "cancel_requested": active}
    return {"session_id": session_id, "already_stopped": True, "cancelled_review_count": 0}
