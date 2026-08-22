from __future__ import annotations

"""Coordinate exclusive H3 generation and model-test review engine use."""

import json
import os
from pathlib import Path
from typing import Any, Literal
from urllib.error import URLError
from urllib.request import urlopen

from job_queue import claim_next_queued_job, queue_claim_lock, read_json


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
REVIEW_ACTIVE_STATUSES = {
    "claimed",
    "preparing",
    "reviewing",
    "cancel_requested",
}
GenerationLane = Literal["windows_candidate", "local_generation"]


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
    return _has_status(
        root / "runtime/model_test_review_queue",
        REVIEW_ACTIVE_STATUSES,
    ) or _has_status(
        root / "runtime/h3/candidate_review_queue",
        REVIEW_ACTIVE_STATUSES,
    )


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
    """Claim one lane; only local generation shares its engine with review."""
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


def claim_review(
    root: Path,
    worker_pid: int,
) -> tuple[Path | None, Literal["generation"] | None]:
    """Claim local review without waiting for independent Windows candidates."""
    scheduler_root = root / "runtime/engine_scheduler"
    with queue_claim_lock(scheduler_root):
        if h3_generation_pending(root) or comfy_work_active():
            return None, "generation"
        candidate = claim_next_queued_job(
            root / "runtime/h3/candidate_review_queue",
            worker_pid,
        )
        if candidate is not None:
            return candidate, None
        return (
            claim_next_queued_job(
                root / "runtime/model_test_review_queue",
                worker_pid,
            ),
            None,
        )
