from __future__ import annotations

import fcntl
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from job_queue import TERMINAL_STATUSES, atomic_write_json, now_iso, read_json


DEFAULT_AUTOMATION_SETTINGS: dict[str, Any] = {
    "schema_version": 1,
    "auto_review": True,
    "auto_modify": True,
    "auto_recheck": True,
    "max_modify_cycles": 1,
    "batch_idle_grace_seconds": 10,
}


def runtime_root(engine_root: Path) -> Path:
    return engine_root / "runtime"


def batches_root(engine_root: Path) -> Path:
    return runtime_root(engine_root) / "batches"


def automation_settings_path(engine_root: Path) -> Path:
    return runtime_root(engine_root) / "automation_settings.json"


def open_batch_path(engine_root: Path) -> Path:
    return runtime_root(engine_root) / "open_batch.json"


def batch_path(engine_root: Path, batch_id: str) -> Path:
    return batches_root(engine_root) / batch_id / "batch.json"


@contextmanager
def batch_lock(engine_root: Path) -> Iterator[None]:
    root = runtime_root(engine_root)
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "batch_manager.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def normalize_settings(payload: dict[str, Any] | None) -> dict[str, Any]:
    settings = dict(DEFAULT_AUTOMATION_SETTINGS)
    if payload:
        settings.update(payload)

    settings["schema_version"] = 1
    settings["auto_review"] = bool(settings.get("auto_review", True))
    settings["auto_modify"] = bool(settings.get("auto_modify", True))
    settings["auto_recheck"] = bool(settings.get("auto_recheck", True))
    settings["max_modify_cycles"] = max(
        0, min(2, int(settings.get("max_modify_cycles", 1)))
    )
    settings["batch_idle_grace_seconds"] = max(
        3, min(300, int(settings.get("batch_idle_grace_seconds", 10)))
    )

    if not settings["auto_review"]:
        settings["auto_modify"] = False
        settings["auto_recheck"] = False
    elif not settings["auto_modify"]:
        settings["auto_recheck"] = False

    return settings


def load_automation_settings(engine_root: Path) -> dict[str, Any]:
    path = automation_settings_path(engine_root)
    payload = read_json(path, {}) or {}
    settings = normalize_settings(payload)
    if not path.exists():
        settings["updated_at"] = now_iso()
        atomic_write_json(path, settings)
    return settings


def save_automation_settings(
    engine_root: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    settings = normalize_settings(payload)
    settings["updated_at"] = now_iso()
    atomic_write_json(automation_settings_path(engine_root), settings)
    return settings


def _new_batch_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"batch_{stamp}_{os.urandom(2).hex()}"


def _new_batch_payload(
    batch_id: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    created_at = now_iso()
    return {
        "schema_version": 1,
        "pipeline_version": "1.8.0",
        "batch_id": batch_id,
        "status": "open",
        "stage": "collecting_generation_jobs",
        "created_at": created_at,
        "updated_at": created_at,
        "sealed_at": None,
        "generation_completed_at": None,
        "idle_since_epoch": None,
        "job_ids": [],
        "generation_job_ids": [],
        "candidate_job_ids": [],
        "upscale_job_ids": [],
        "check_job_ids": [],
        "modify_job_ids": [],
        "automation": {
            "auto_review": settings["auto_review"],
            "auto_modify": settings["auto_modify"],
            "auto_recheck": settings["auto_recheck"],
            "max_modify_cycles": settings["max_modify_cycles"],
            "batch_idle_grace_seconds": settings["batch_idle_grace_seconds"],
        },
        "current_cycle": 0,
        "next_stage": "generation",
        "message": "생성 작업 등록을 기다리고 있습니다.",
    }


def load_open_batch(engine_root: Path) -> dict[str, Any] | None:
    pointer = read_json(open_batch_path(engine_root), {}) or {}
    batch_id = str(pointer.get("batch_id") or "").strip()
    if not batch_id:
        return None
    batch = read_json(batch_path(engine_root, batch_id), {}) or {}
    if not batch or batch.get("status") != "open":
        return None
    return batch


def get_or_create_open_batch(
    engine_root: Path,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with batch_lock(engine_root):
        existing = load_open_batch(engine_root)
        if existing is not None and not bool(existing.get("registration_closed")):
            return existing

        normalized = normalize_settings(
            settings if settings is not None else load_automation_settings(engine_root)
        )
        batch_id = _new_batch_id()
        payload = _new_batch_payload(batch_id, normalized)
        atomic_write_json(batch_path(engine_root, batch_id), payload)
        atomic_write_json(
            open_batch_path(engine_root),
            {
                "schema_version": 1,
                "batch_id": batch_id,
                "created_at": payload["created_at"],
            },
        )
        return payload


def create_new_open_batch(
    engine_root: Path,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create an independent FIFO batch and make it the registration pointer."""
    with batch_lock(engine_root):
        normalized = normalize_settings(
            settings if settings is not None else load_automation_settings(engine_root)
        )
        batch_id = _new_batch_id()
        payload = _new_batch_payload(batch_id, normalized)
        atomic_write_json(batch_path(engine_root, batch_id), payload)
        atomic_write_json(
            open_batch_path(engine_root),
            {
                "schema_version": 1,
                "batch_id": batch_id,
                "created_at": payload["created_at"],
            },
        )
        return payload

def attach_job_to_batch(
    engine_root: Path,
    batch_id: str,
    job_id: str,
    job_type: str,
) -> dict[str, Any]:
    with batch_lock(engine_root):
        path = batch_path(engine_root, batch_id)
        batch = read_json(path, {}) or {}
        if not batch:
            raise FileNotFoundError(f"배치 기록을 찾을 수 없습니다: {batch_id}")

        if job_type in {"generate", "candidate", "upscale"}:
            if batch.get("status") != "open" or bool(batch.get("registration_closed")):
                raise RuntimeError(f"생성 등록이 종료된 배치입니다: {batch_id}")

        job_ids = list(batch.get("job_ids") or [])
        if job_id not in job_ids:
            job_ids.append(job_id)
        batch["job_ids"] = job_ids

        key = {
            "generate": "generation_job_ids",
            "candidate": "candidate_job_ids",
            "upscale": "upscale_job_ids",
            "assemble": "assemble_job_ids",
            "check": "check_job_ids",
            "modify": "modify_job_ids",
        }.get(job_type)
        if key:
            typed_ids = list(batch.get(key) or [])
            if job_id not in typed_ids:
                typed_ids.append(job_id)
            batch[key] = typed_ids

        if job_type in {"candidate", "upscale", "assemble"}:
            generation_ids = list(batch.get("generation_job_ids") or [])
            if job_id not in generation_ids:
                generation_ids.append(job_id)
            batch["generation_job_ids"] = generation_ids

        if job_type in {"generate", "candidate", "upscale", "assemble"}:
            # 유예 시간 중 새 생성 작업이 등록되면 동일 배치에 포함합니다.
            batch["idle_since_epoch"] = None
            batch["stage"] = "collecting_generation_jobs"
            batch["next_stage"] = "generation"
            batch["message"] = (
                f"배치에 생성 작업 {len(batch.get('generation_job_ids') or [])}개가 "
                "등록되었습니다."
            )

        batch["updated_at"] = now_iso()
        atomic_write_json(path, batch)
        return batch


def find_batches_by_status(
    engine_root: Path,
    statuses: set[str],
    limit: int = 1000,
) -> list[dict[str, Any]]:
    return [
        item
        for item in list_batches(engine_root, limit=limit)
        if str(item.get("status") or "") in statuses
    ]


def batch_typed_jobs_are_terminal(
    jobs_root: Path,
    batch: dict[str, Any],
    key: str,
) -> bool:
    job_ids = list(batch.get(key) or [])
    if not job_ids:
        return False
    statuses = job_statuses_for_batch(jobs_root, batch)
    return all(statuses.get(job_id) in TERMINAL_STATUSES for job_id in job_ids)


def list_batches(engine_root: Path, limit: int = 100) -> list[dict[str, Any]]:
    root = batches_root(engine_root)
    if not root.exists():
        return []
    paths = sorted(
        (path / "batch.json" for path in root.iterdir() if path.is_dir()),
        reverse=True,
    )
    batches: list[dict[str, Any]] = []
    for path in paths[:limit]:
        payload = read_json(path, {}) or {}
        if payload:
            batches.append(payload)
    return batches


def load_batch(engine_root: Path, batch_id: str) -> dict[str, Any]:
    return read_json(batch_path(engine_root, batch_id), {}) or {}


def update_batch(
    engine_root: Path,
    batch_id: str,
    **fields: Any,
) -> dict[str, Any]:
    with batch_lock(engine_root):
        path = batch_path(engine_root, batch_id)
        payload = read_json(path, {}) or {}
        if not payload:
            raise FileNotFoundError(f"배치 기록을 찾을 수 없습니다: {batch_id}")
        payload.update(fields)
        payload["updated_at"] = now_iso()
        atomic_write_json(path, payload)
        return payload


def clear_open_batch_pointer(engine_root: Path, batch_id: str) -> None:
    with batch_lock(engine_root):
        pointer = read_json(open_batch_path(engine_root), {}) or {}
        if pointer.get("batch_id") == batch_id:
            try:
                open_batch_path(engine_root).unlink()
            except FileNotFoundError:
                pass


def job_statuses_for_batch(
    jobs_root: Path,
    batch: dict[str, Any],
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for job_id in batch.get("job_ids") or []:
        status = read_json(jobs_root / job_id / "status.json", {}) or {}
        statuses[job_id] = str(status.get("status") or "unknown")
    return statuses


def batch_generation_is_terminal(
    jobs_root: Path,
    batch: dict[str, Any],
) -> bool:
    generation_ids = list(batch.get("generation_job_ids") or [])
    if not generation_ids:
        return False
    statuses = job_statuses_for_batch(jobs_root, batch)
    return all(statuses.get(job_id) in TERMINAL_STATUSES for job_id in generation_ids)


def mark_batch_generation_complete(
    engine_root: Path,
    batch: dict[str, Any],
) -> dict[str, Any]:
    automation = batch.get("automation") or {}
    auto_review = bool(automation.get("auto_review", True))
    generation_job_ids = list(batch.get("generation_job_ids") or [])
    candidate_job_ids = set(batch.get("candidate_job_ids") or [])
    review_job_ids = [
        job_id for job_id in generation_job_ids if job_id not in candidate_job_ids
    ]

    if candidate_job_ids and not review_job_ids:
        status = "awaiting_candidate_selection"
        stage = "candidate_generation_complete"
        next_stage = "user_candidate_selection"
        message = "후보 생성이 완료되었습니다. 사용자가 최종 후보를 선택할 때까지 대기합니다."
    elif auto_review and review_job_ids:
        status = "ready_for_review_preparation"
        stage = "generation_batch_complete"
        next_stage = "contact_sheet"
        message = (
            "생성 배치가 완료되었습니다. 다음 단계에서 Contact Sheet 자동 생성과 "
            "엔진 전환을 연결합니다."
        )
    else:
        status = "completed_generation_only"
        stage = "completed"
        next_stage = "completed"
        message = "AI 검수가 비활성화되어 생성 배치만 완료했습니다."

    completed_at = now_iso()
    updated = update_batch(
        engine_root,
        str(batch["batch_id"]),
        status=status,
        stage=stage,
        next_stage=next_stage,
        generation_completed_at=completed_at,
        sealed_at=completed_at,
        idle_since_epoch=None,
        review_job_ids=review_job_ids,
        message=message,
    )
    clear_open_batch_pointer(engine_root, str(batch["batch_id"]))
    return updated
