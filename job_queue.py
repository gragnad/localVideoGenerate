from __future__ import annotations

import fcntl
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
ACTIVE_STATUSES = {
    "preparing",
    "uploading",
    "building",
    "submitting",
    "comfy_queued",
    "submitted",
    "running",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


@contextmanager
def queue_claim_lock(jobs_root: Path):
    jobs_root.mkdir(parents=True, exist_ok=True)
    lock_path = jobs_root / ".queue-claim.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def status_path(job_dir: Path) -> Path:
    return job_dir / "status.json"


def request_path(job_dir: Path) -> Path:
    return job_dir / "request.json"


def manifest_path(job_dir: Path) -> Path:
    return job_dir / "manifest.json"


def update_status(job_dir: Path, status: str, **fields: Any) -> dict[str, Any]:
    current = read_json(status_path(job_dir), {}) or {}
    current.update(fields)
    current["job_id"] = job_dir.name
    current["status"] = status
    current["updated_at"] = now_iso()
    atomic_write_json(status_path(job_dir), current)
    return current


def load_job(job_dir: Path) -> dict[str, Any]:
    request = read_json(request_path(job_dir), {}) or {}
    manifest = read_json(manifest_path(job_dir), {}) or {}
    status = read_json(status_path(job_dir), {}) or {}
    if not status and manifest.get("status"):
        status = {
            "job_id": job_dir.name,
            "status": manifest.get("status"),
            "stage": manifest.get("status"),
            "updated_at": (
                manifest.get("completed_at")
                or manifest.get("failed_at")
                or manifest.get("updated_at")
                or manifest.get("created_at")
            ),
            "outputs": manifest.get("outputs") or [],
        }
    return {
        "job_id": job_dir.name,
        "job_dir": str(job_dir),
        "request": request,
        "status": status,
        "manifest": manifest,
    }


def list_jobs(jobs_root: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not jobs_root.exists():
        return []
    directories = [path for path in jobs_root.iterdir() if path.is_dir()]
    directories.sort(key=lambda path: path.name, reverse=True)
    if limit is not None:
        directories = directories[:limit]
    return [load_job(path) for path in directories]


def find_next_queued_job(jobs_root: Path) -> Path | None:
    if not jobs_root.exists():
        return None
    candidates: list[Path] = []
    for job_dir in jobs_root.iterdir():
        if not job_dir.is_dir():
            continue
        status = read_json(status_path(job_dir), {}) or {}
        if status.get("status") == "queued":
            candidates.append(job_dir)
    def queue_key(path: Path) -> tuple[str, int, str]:
        request = read_json(request_path(path), {}) or {}
        return (
            str(request.get("created_at") or ""),
            int(request.get("candidate_index") or request.get("queue_order") or 0),
            path.name,
        )

    candidates.sort(key=queue_key)
    return candidates[0] if candidates else None


def claim_next_queued_job(jobs_root: Path, worker_pid: int) -> Path | None:
    """Atomically select and claim one queued job."""
    with queue_claim_lock(jobs_root):
        job_dir = find_next_queued_job(jobs_root)
        if job_dir is None:
            return None
        status = read_json(status_path(job_dir), {}) or {}
        if status.get("status") != "queued":
            return None
        update_status(
            job_dir,
            "preparing",
            stage="worker가 작업을 가져왔습니다",
            worker_pid=worker_pid,
            progress=0.01,
        )
        return job_dir
