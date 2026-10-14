from __future__ import annotations

"""Coordinate local H3 generation with external clients that lease the shared vLLM engine."""

import json
import os
import uuid
from pathlib import Path
from typing import Any, Literal
from urllib.error import URLError
from urllib.request import urlopen

from job_queue import atomic_write_json, claim_next_queued_job, now_iso, queue_claim_lock, read_json


H3_PENDING_STATUSES = {
    "queued",
    "claimed",
    "preparing",
    "uploading",
    "building",
    "submitting",
    "submitted",
    "comfy_queued",
    "running",
}
GenerationLane = Literal["windows_candidate", "local_generation"]


def _external_review_lease_path(root: Path) -> Path:
    return root / "runtime/engine_scheduler/external_review_lease.json"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def external_review_active(root: Path) -> bool:
    """True while an out-of-queue client, such as Scene Director, owns vLLM."""
    lease_path = _external_review_lease_path(root)
    lease = read_json(lease_path, {}) or {}
    if not lease:
        return False
    if _pid_alive(int(lease.get("pid") or 0)):
        return True
    try:
        lease_path.unlink(missing_ok=True)
    except OSError:
        pass
    return False


def claim_external_review(
    root: Path,
    worker_pid: int,
    owner: str,
) -> tuple[str | None, Literal["generation", "review"] | None]:
    """Reserve the shared local inference engine for an external review client."""
    scheduler_root = root / "runtime/engine_scheduler"
    scheduler_root.mkdir(parents=True, exist_ok=True)
    with queue_claim_lock(scheduler_root):
        if h3_generation_pending(root) or comfy_work_active():
            return None, "generation"
        if external_review_active(root):
            return None, "review"
        lease_id = uuid.uuid4().hex
        atomic_write_json(
            _external_review_lease_path(root),
            {
                "lease_id": lease_id,
                "pid": int(worker_pid),
                "owner": owner,
                "claimed_at": now_iso(),
            },
        )
        return lease_id, None


def release_external_review(root: Path, lease_id: str) -> None:
    scheduler_root = root / "runtime/engine_scheduler"
    with queue_claim_lock(scheduler_root):
        lease_path = _external_review_lease_path(root)
        lease = read_json(lease_path, {}) or {}
        if lease.get("lease_id") == lease_id:
            lease_path.unlink(missing_ok=True)


def generation_lane(request: dict[str, Any]) -> GenerationLane:
    """Route production candidates to Windows and all other H3 work locally."""
    explicit = str(request.get("queue_lane") or "").strip()
    if explicit in {"windows_candidate", "local_generation"}:
        return explicit  # type: ignore[return-value]
    if request.get("render_purpose") == "resolution_rerender":
        return "local_generation"
    if request.get("candidate_set_id") or request.get("job_type") == "h3_r2v_generate":
        return "windows_candidate"
    return "local_generation"


def _has_status(
    root: Path,
    statuses: set[str],
    *,
    lane: GenerationLane | None = None,
) -> bool:
    if not root.exists():
        return False
    for directory in root.iterdir():
        if not directory.is_dir():
            continue
        status = read_json(directory / "status.json", {}) or {}
        request = read_json(directory / "request.json", {}) or {}
        if (
            str(status.get("status") or "") in statuses
            and (lane is None or generation_lane(request) == lane)
        ):
            return True
    return False


def h3_generation_pending(
    root: Path,
    lane: GenerationLane = "local_generation",
) -> bool:
    return _has_status(
        root / "runtime/h3/jobs",
        H3_PENDING_STATUSES,
        lane=lane,
    )


def model_review_active(root: Path) -> bool:
    return external_review_active(root)


def comfy_work_active(comfy_url: str | None = None) -> bool:
    """Return true only when ComfyUI reports running or pending prompts."""
    base = str(
        comfy_url
        or os.environ.get("COMFY_URL")
        or "http://127.0.0.1:8188"
    ).rstrip("/")
    try:
        with urlopen(f"{base}/queue", timeout=0.75) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    return bool(
        list(payload.get("queue_running") or [])
        or list(payload.get("queue_pending") or [])
    )


def claim_generation(
    root: Path,
    worker_pid: int,
    lane: GenerationLane = "local_generation",
) -> tuple[Path | None, Literal["review"] | None]:
    """Claim one lane; only local generation shares its engine with external vLLM clients."""
    if lane not in {"windows_candidate", "local_generation"}:
        raise ValueError(f"지원하지 않는 생성 큐 레인입니다: {lane}")
    scheduler_root = root / "runtime/engine_scheduler"
    with queue_claim_lock(scheduler_root):
        if lane == "local_generation" and model_review_active(root):
            return None, "review"
        return (
            claim_next_queued_job(
                root / "runtime/h3/jobs",
                worker_pid,
                request_filter=lambda request: generation_lane(request) == lane,
            ),
            None,
        )
