from __future__ import annotations

"""Persistent opt-in AI review queue for H3 candidate-selection videos."""

import os
from pathlib import Path
from typing import Any

from job_queue import (
    atomic_write_json,
    now_iso,
    queue_claim_lock,
    read_json,
    update_status,
)


REVIEW_SCHEMA_VERSION = "candidate_qwen38_story_continuity_v3"
ACTIVE_STATUSES = {"queued", "preparing", "reviewing", "cancel_requested"}
CLAIMED_STATUSES = {"claimed", "preparing", "reviewing"}
COMPLETED_STATUSES = {"completed"}


def queue_root(root: Path) -> Path:
    return root / "runtime/h3/candidate_review_queue"


def settings_path(root: Path) -> Path:
    return root / "runtime/h3/candidate_review_settings.json"


def worker_status_path(root: Path) -> Path:
    return root / "runtime/model_test_review_worker_status.json"


def settings(root: Path) -> dict[str, Any]:
    payload = read_json(settings_path(root), {}) or {}
    return {
        "enabled": bool(payload.get("enabled")),
        "updated_at": payload.get("updated_at"),
        "review_schema_version": REVIEW_SCHEMA_VERSION,
    }


def _visible_candidate_sets(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    base = root / "runtime/h3/candidate_sets"
    if not base.exists():
        return []
    rows: list[tuple[Path, dict[str, Any]]] = []
    for directory in base.iterdir():
        if not directory.is_dir():
            continue
        payload = read_json(directory / "candidate_set.json", {}) or {}
        if (
            not payload
            or payload.get("deleted")
            or payload.get("deleted_at")
            or payload.get("status") == "deleted"
            or payload.get("render_purpose") == "resolution_rerender"
        ):
            continue
        rows.append((directory, payload))
    return rows


def _deleted_candidate_set_ids(root: Path) -> set[str]:
    base = root / "runtime/h3/candidate_sets"
    if not base.exists():
        return set()
    deleted: set[str] = set()
    for directory in base.iterdir():
        if not directory.is_dir():
            continue
        payload = read_json(directory / "candidate_set.json", {}) or {}
        if (
            payload.get("deleted")
            or payload.get("deleted_at")
            or payload.get("status") == "deleted"
        ):
            deleted.add(str(payload.get("candidate_set_id") or directory.name))
    return deleted


def _completed_candidate(
    root: Path, candidate_set_id: str, job_id: str
) -> dict[str, Any] | None:
    job_dir = root / "runtime/h3/jobs" / job_id
    request = read_json(job_dir / "request.json", {}) or {}
    status = read_json(job_dir / "status.json", {}) or {}
    manifest = read_json(job_dir / "manifest.json", {}) or {}
    if (
        status.get("status") != "completed"
        or str(request.get("candidate_set_id") or "") != candidate_set_id
        or request.get("render_purpose") == "resolution_rerender"
    ):
        return None
    video_path = Path(
        str(manifest.get("local_video_path") or status.get("local_video_path") or "")
    )
    if not video_path.is_file():
        return None
    output_sha256 = str(manifest.get("output_sha256") or "").strip()
    if not output_sha256:
        return None
    return {
        "request": request,
        "status": status,
        "manifest": manifest,
        "video_path": video_path,
        "output_sha256": output_sha256,
    }


def _review_id(job_id: str, output_sha256: str) -> str:
    return (
        f"candidate_review_{job_id}_{output_sha256[:12]}_"
        f"{REVIEW_SCHEMA_VERSION}"
    )


def sync_enabled_reviews(root: Path) -> dict[str, Any]:
    """Queue each newly completed 04-candidate video while the toggle is on."""
    retire_deleted_candidate_set_reviews(root)
    current = settings(root)
    if not current["enabled"]:
        return {**current, "queued_count": 0}
    queued: list[str] = []
    base = queue_root(root)
    with queue_claim_lock(base):
        for _set_dir, candidate_set in _visible_candidate_sets(root):
            set_id = str(candidate_set.get("candidate_set_id") or "")
            for job_id_value in candidate_set.get("candidate_job_ids") or []:
                job_id = str(job_id_value or "").strip()
                completed = _completed_candidate(root, set_id, job_id)
                if not completed:
                    continue
                review_id = _review_id(job_id, completed["output_sha256"])
                directory = base / review_id
                if (directory / "request.json").is_file():
                    previous = read_json(directory / "status.json", {}) or {}
                    if str(previous.get("status") or "") == "cancelled":
                        update_status(
                            directory,
                            "queued",
                            stage="로컬 후보 AI 검수 재개 대기",
                            progress=0,
                            cancel_requested=False,
                            cancelled_at=None,
                            error=None,
                            requeued_at=now_iso(),
                        )
                        queued.append(review_id)
                    continue
                created = now_iso()
                generation_request = completed["request"]
                request = {
                    "schema_version": 1,
                    "review_schema_version": REVIEW_SCHEMA_VERSION,
                    "review_id": review_id,
                    "queue_name": "candidate_ai_review",
                    "job_type": "candidate_ai_review",
                    "candidate_set_id": set_id,
                    "generation_job_id": job_id,
                    "candidate_index": generation_request.get("candidate_index"),
                    "prompt_variant_id": generation_request.get("prompt_variant_id"),
                    "output_sha256": completed["output_sha256"],
                    "created_at": created,
                }
                atomic_write_json(directory / "request.json", request)
                atomic_write_json(
                    directory / "status.json",
                    {
                        "job_id": review_id,
                        "status": "queued",
                        "stage": "로컬 후보 AI 검수 대기",
                        "progress": 0,
                        "created_at": created,
                        "updated_at": created,
                    },
                )
                queued.append(review_id)
    return {**current, "queued_count": len(queued), "queued_review_ids": queued}


def set_enabled(root: Path, enabled: bool) -> dict[str, Any]:
    updated = now_iso()
    atomic_write_json(
        settings_path(root),
        {
            "schema_version": 1,
            "enabled": bool(enabled),
            "review_schema_version": REVIEW_SCHEMA_VERSION,
            "updated_at": updated,
        },
    )
    cancelled = 0
    if enabled:
        result = sync_enabled_reviews(root)
        return {**result, "enabled": True, "cancelled_count": 0}
    base = queue_root(root)
    if base.exists():
        with queue_claim_lock(base):
            for directory in base.iterdir():
                if not directory.is_dir():
                    continue
                status = read_json(directory / "status.json", {}) or {}
                value = str(status.get("status") or "")
                if value == "queued":
                    update_status(
                        directory,
                        "cancelled",
                        stage="후보 AI 검수 비활성화로 대기 작업 취소",
                        cancelled_at=updated,
                    )
                    cancelled += 1
                elif value in {"preparing", "reviewing"}:
                    update_status(
                        directory,
                        "cancel_requested",
                        stage="후보 AI 검수 비활성화 · 현재 작업 종료 대기",
                        cancel_requested=True,
                        cancelled_at=updated,
                    )
                    cancelled += 1
    return {
        **settings(root),
        "enabled": False,
        "queued_count": 0,
        "cancelled_count": cancelled,
    }


def retire_candidate_set_reviews(
    root: Path, candidate_set_id: str,
) -> dict[str, Any]:
    """Cancel and hide unfinished reviews when their candidate set is deleted."""
    set_id = str(candidate_set_id or "").strip()
    cancelled = 0
    cancel_requested = 0
    preserved = 0
    retired_ids: list[str] = []
    stamp = now_iso()
    base = queue_root(root)
    if not base.exists():
        return {
            "cancelled_count": 0,
            "cancel_requested_count": 0,
            "preserved_completed_count": 0,
            "retired_review_ids": [],
        }

    with queue_claim_lock(base):
        for directory in base.iterdir():
            if not directory.is_dir():
                continue
            request = read_json(directory / "request.json", {}) or {}
            if str(request.get("candidate_set_id") or "") != set_id:
                continue
            status = read_json(directory / "status.json", {}) or {}
            value = str(status.get("status") or "")
            if value in COMPLETED_STATUSES:
                preserved += 1
                continue
            if status.get("hidden_from_state"):
                continue

            common = {
                "candidate_set_deleted": True,
                "candidate_set_deleted_at": stamp,
                "hidden_from_state": True,
                "hidden_at": stamp,
                "status_before_candidate_set_delete": value,
            }
            if value in CLAIMED_STATUSES or value == "cancel_requested":
                update_status(
                    directory,
                    "cancel_requested",
                    stage="후보군 삭제 · 현재 AI 검수 종료 대기",
                    cancel_requested=True,
                    cancel_requested_at=stamp,
                    **common,
                )
                cancel_requested += 1
            else:
                update_status(
                    directory,
                    "cancelled",
                    stage="후보군 삭제로 미완료 AI 검수 취소",
                    cancel_requested=False,
                    cancelled_at=stamp,
                    **common,
                )
                cancelled += 1
            retired_ids.append(directory.name)

    return {
        "cancelled_count": cancelled,
        "cancel_requested_count": cancel_requested,
        "preserved_completed_count": preserved,
        "retired_review_ids": retired_ids,
    }


def retire_deleted_candidate_set_reviews(root: Path) -> dict[str, int]:
    """Reconcile unfinished reviews left by candidate sets deleted previously."""
    total = {
        "cancelled_count": 0,
        "cancel_requested_count": 0,
        "preserved_completed_count": 0,
    }
    for set_id in _deleted_candidate_set_ids(root):
        result = retire_candidate_set_reviews(root, set_id)
        for key in total:
            total[key] += int(result.get(key) or 0)
    return total


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def recover_orphaned_reviews(root: Path, worker_pid: int) -> dict[str, int]:
    """Requeue current reviews and retire active reviews from older rubrics."""
    base = queue_root(root)
    recovered = 0
    cancelled = 0
    if not base.exists():
        return {"recovered_count": 0, "cancelled_count": 0}
    with queue_claim_lock(base):
        for directory in base.iterdir():
            if not directory.is_dir():
                continue
            request = read_json(directory / "request.json", {}) or {}
            status = read_json(directory / "status.json", {}) or {}
            value = str(status.get("status") or "")
            if (
                request.get("review_schema_version") != REVIEW_SCHEMA_VERSION
                and value in ACTIVE_STATUSES | CLAIMED_STATUSES
            ):
                update_status(
                    directory,
                    "cancelled",
                    stage="이전 검수 기준 작업 보존 · 최신 기준으로 재등록",
                    worker_pid=None,
                    cancel_requested=False,
                    cancelled_at=now_iso(),
                )
                cancelled += 1
                continue
            owner = int(status.get("worker_pid") or 0)
            if value not in CLAIMED_STATUSES or owner == worker_pid or _pid_alive(owner):
                continue
            if status.get("cancel_requested") or not settings(root)["enabled"]:
                update_status(
                    directory,
                    "cancelled",
                    stage="후보 AI 검수 비활성화 · 중단 작업 정리",
                    worker_pid=None,
                    cancelled_at=now_iso(),
                )
                cancelled += 1
            else:
                update_status(
                    directory,
                    "queued",
                    stage="검수 Worker 재시작 후 자동 복구 대기",
                    progress=0,
                    worker_pid=None,
                    recovered_at=now_iso(),
                    error=None,
                )
                recovered += 1
    return {"recovered_count": recovered, "cancelled_count": cancelled}


def list_reviews(
    root: Path, *, include_legacy: bool = False, include_hidden: bool = False,
) -> list[dict[str, Any]]:
    """Return current-schema reviews; legacy rows remain on disk as history."""
    base = queue_root(root)
    if not base.exists():
        return []
    deleted_set_ids = _deleted_candidate_set_ids(root)
    rows = []
    for directory in base.iterdir():
        if not directory.is_dir():
            continue
        request = read_json(directory / "request.json", {}) or {}
        if (
            not include_legacy
            and request.get("review_schema_version") != REVIEW_SCHEMA_VERSION
        ):
            continue
        status = read_json(directory / "status.json", {}) or {}
        deleted_unfinished = (
            str(request.get("candidate_set_id") or "") in deleted_set_ids
            and str(status.get("status") or "") not in COMPLETED_STATUSES
        )
        if not include_hidden and (
            status.get("hidden_from_state") or deleted_unfinished
        ):
            continue
        report = read_json(directory / "report.json", {}) or {}
        rows.append(
            {
                "review_id": directory.name,
                "candidate_set_id": request.get("candidate_set_id"),
                "generation_job_id": request.get("generation_job_id"),
                "candidate_index": request.get("candidate_index"),
                "prompt_variant_id": request.get("prompt_variant_id"),
                "output_sha256": request.get("output_sha256"),
                "review_schema_version": request.get("review_schema_version"),
                "status": status,
                "report": report,
                "created_at": request.get("created_at"),
            }
        )
    return sorted(rows, key=lambda row: str(row.get("created_at") or ""), reverse=True)


def _latest_reviews(root: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for review in list_reviews(root):
        job_id = str(review.get("generation_job_id") or "")
        if job_id and job_id not in latest:
            latest[job_id] = review
    return latest


def candidate_set_summaries(root: Path) -> list[dict[str, Any]]:
    latest = _latest_reviews(root)
    summaries: list[dict[str, Any]] = []
    for _directory, candidate_set in _visible_candidate_sets(root):
        job_ids = [str(value) for value in candidate_set.get("candidate_job_ids") or []]
        generation_statuses = {
            job_id: str(
                (
                    read_json(root / "runtime/h3/jobs" / job_id / "status.json", {})
                    or {}
                ).get("status")
                or "missing"
            )
            for job_id in job_ids
        }
        terminal_generation_statuses = {
            "completed", "failed", "cancelled", "stopped", "missing"
        }
        review_target_count = sum(
            value == "completed" for value in generation_statuses.values()
        )
        generation_terminal = all(
            value in terminal_generation_statuses
            for value in generation_statuses.values()
        )
        reviews = [latest[job_id] for job_id in job_ids if job_id in latest]
        completed = [
            row for row in reviews
            if str((row.get("status") or {}).get("status") or "") == "completed"
        ]
        active = [
            row for row in reviews
            if str((row.get("status") or {}).get("status") or "") in ACTIVE_STATUSES
        ]
        failed = [
            row for row in reviews
            if str((row.get("status") or {}).get("status") or "") == "failed"
        ]
        ranked = sorted(
            completed,
            key=lambda row: float((row.get("report") or {}).get("overall_score") or 0),
            reverse=True,
        )
        ranking = [
            {
                "rank": index,
                "job_id": row.get("generation_job_id"),
                "candidate_index": row.get("candidate_index"),
                "prompt_variant_id": row.get("prompt_variant_id"),
                "overall_score": (row.get("report") or {}).get("overall_score"),
                "verdict": (row.get("report") or {}).get("verdict"),
            }
            for index, row in enumerate(ranked, start=1)
        ]
        feedback_rows = []
        for row in ranked:
            report = row.get("report") or {}
            feedback = str(report.get("revision_feedback_ko") or "").strip()
            if not feedback:
                continue
            label = row.get("prompt_variant_id") or row.get("candidate_index") or "-"
            scores = report.get("scores") or {}
            if report.get("rubric_version") == "candidate_story_continuity_v3":
                feedback_rows.append(
                    f"후보 {label} · 연출 {scores.get('scenario_realization', '-')}"
                    f" · 이전 연결 {scores.get('incoming_continuity', '-')}"
                    f" · 다음 연결 {scores.get('outgoing_continuity', '-')}: {feedback}"
                )
            else:
                feedback_rows.append(f"후보 {label}: {feedback}")
        if active:
            status = "reviewing"
        elif failed:
            status = "completed_with_failures" if completed else "failed"
        elif (
            job_ids
            and generation_terminal
            and len(completed) == review_target_count
        ):
            status = "completed"
        elif len(completed) == review_target_count and review_target_count:
            status = "watching"
        elif completed:
            status = "partial"
        else:
            status = "not_started"
        summaries.append(
            {
                "candidate_set_id": candidate_set.get("candidate_set_id"),
                "status": status,
                "candidate_count": len(job_ids),
                "review_target_count": review_target_count,
                "reviewed_count": len(completed),
                "active_count": len(active),
                "failed_count": len(failed),
                "ranking": ranking,
                "ai_revision_feedback": "\n".join(feedback_rows),
            }
        )
    return summaries


def state(root: Path) -> dict[str, Any]:
    return {
        **settings(root),
        "reviews": list_reviews(root),
        "candidate_sets": candidate_set_summaries(root),
        "worker": read_json(worker_status_path(root), {}) or {},
    }
