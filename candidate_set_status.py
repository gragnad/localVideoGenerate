from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from job_queue import atomic_write_json, now_iso, read_json


TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled"}
LOCKED_CANDIDATE_SET_STATUSES = {
    "selected",
    "final_review_queued",
    "completed",
    "final_review_failed",
}


def _safe_id(value: object, label: str) -> str:
    item_id = str(value or "").strip()
    if (
        not item_id
        or Path(item_id).name != item_id
        or item_id in {".", ".."}
    ):
        raise ValueError(f"허용되지 않는 {label} ID입니다.")
    return item_id


def _candidate_set_path(engine_root: Path, candidate_set_id: str) -> Path:
    return (
        Path(engine_root)
        / "runtime"
        / "candidate_sets"
        / _safe_id(candidate_set_id, "후보군")
        / "candidate_set.json"
    )


def _job_status(engine_root: Path, job_id: str) -> tuple[str, dict[str, Any]]:
    job_dir = Path(engine_root) / "jobs" / _safe_id(job_id, "작업")
    status = read_json(job_dir / "status.json", {}) or {}
    manifest = read_json(job_dir / "manifest.json", {}) or {}
    name = str(status.get("status") or manifest.get("status") or "missing")
    return name, status


def reconcile_candidate_set(
    engine_root: Path,
    candidate_set_id: str,
) -> dict[str, Any]:
    path = _candidate_set_path(engine_root, candidate_set_id)
    payload = read_json(path, {}) or {}
    if not payload:
        raise FileNotFoundError(f"후보군을 찾을 수 없습니다: {candidate_set_id}")
    if str(payload.get("status") or "") in LOCKED_CANDIDATE_SET_STATUSES:
        return payload

    job_ids = [
        str(value)
        for value in payload.get("candidate_job_ids") or []
        if str(value).strip()
    ]
    status_rows = [_job_status(engine_root, job_id) for job_id in job_ids]
    statuses = [name for name, _ in status_rows]
    counts = Counter(statuses)
    all_terminal = bool(job_ids) and len(statuses) == len(job_ids) and all(
        status in TERMINAL_JOB_STATUSES for status in statuses
    )

    if all_terminal and counts["completed"]:
        derived_status = "awaiting_candidate_selection"
    elif all_terminal:
        derived_status = "generation_failed"
    else:
        derived_status = "generating"

    updates = {
        "status": derived_status,
        "candidate_status_counts": dict(sorted(counts.items())),
        "completed_candidate_count": counts["completed"],
        "failed_candidate_count": counts["failed"],
        "cancelled_candidate_count": counts["cancelled"],
        "candidate_jobs_terminal": all_terminal,
    }
    if all_terminal:
        timestamps = [
            str(status.get("completed_at") or status.get("updated_at") or "")
            for _, status in status_rows
        ]
        completed_at = max((value for value in timestamps if value), default=now_iso())
        updates["generation_completed_at"] = (
            payload.get("generation_completed_at") or completed_at
        )

    if all(payload.get(key) == value for key, value in updates.items()):
        return payload
    payload.update(updates, updated_at=now_iso())
    atomic_write_json(path, payload)
    return payload


def reconcile_candidate_sets(
    engine_root: Path,
    candidate_set_ids: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    root = Path(engine_root) / "runtime" / "candidate_sets"
    if candidate_set_ids is None:
        ids = [
            path.parent.name
            for path in root.glob("*/candidate_set.json")
            if path.is_file()
        ]
    else:
        ids = [str(value) for value in candidate_set_ids if str(value).strip()]
    return [
        reconcile_candidate_set(engine_root, candidate_set_id)
        for candidate_set_id in ids
    ]
