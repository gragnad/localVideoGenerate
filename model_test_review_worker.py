from __future__ import annotations

"""Worker for user-requested model-test AI reviews; no batch state machine."""

import os
import signal
import time
import traceback
from pathlib import Path
from typing import Any

import benchmark_jobs
import candidate_ai_reviewer
import candidate_review_queue
import engine_scheduler
import engine_switch
import h3_queue
from comfy_client import ComfyClient
from engine_switch import ensure_comfy_engine, ensure_vllm_engine
from job_queue import atomic_write_json, now_iso, read_json, update_status
import model_test_ai_reviewer
import model_test_r2v_ai_reviewer
import model_test_review_queue
import model_test_reviews
from review_workflow import find_primary_video_output


ROOT = Path(os.environ.get("VIDEO_ENGINE_ROOT", Path.home() / "local-ai/video-engine"))
QUEUE = model_test_review_queue.queue_root(ROOT)
STATUS = ROOT / "runtime/model_test_review_worker_status.json"
COMFY_OUTPUT = Path(os.environ.get("COMFY_OUTPUT_DIR", Path.home() / "ai-workspace/apps/ComfyUI/output"))
STOP = False


def _stop(_signum: int, _frame: Any) -> None:
    global STOP
    STOP = True


def _worker(state: str, **fields: Any) -> None:
    atomic_write_json(STATUS, {"state": state, "pid": os.getpid(), "updated_at": now_iso(), **fields})


def _mark_queued_reviews_waiting_for_generation() -> None:
    if not QUEUE.exists():
        return
    for directory in QUEUE.iterdir():
        if not directory.is_dir():
            continue
        status = read_json(directory / "status.json", {}) or {}
        if status.get("status") != "queued":
            continue
        stage = "H3·ComfyUI 생성 큐 완료 후 AI 검수 대기"
        if status.get("stage") != stage:
            update_status(directory, "queued", stage=stage)


def _local_video(queue_dir: Path, generation_job_id: str) -> Path:
    job_dir = h3_queue.resolve_job_dir(ROOT, generation_job_id)
    manifest = read_json(job_dir / "manifest.json", {}) or {}
    request = read_json(job_dir / "request.json", {}) or {}
    existing = Path(str(manifest.get("review_video_local_path") or ""))
    if existing.is_file():
        return existing
    generated = Path(str(manifest.get("local_video_path") or ""))
    if generated.is_file():
        return generated
    output = find_primary_video_output(list(manifest.get("outputs") or []))
    if not output:
        raise RuntimeError(f"검수 영상 출력 정보가 없습니다: {generation_job_id}")
    local = (COMFY_OUTPUT / str(output.get("subfolder") or "") / str(output.get("filename") or "")).resolve()
    if local.is_file():
        return local
    target = queue_dir / "videos" / f"{generation_job_id}{Path(str(output.get('filename') or '.mp4')).suffix or '.mp4'}"
    ComfyClient(str(request.get("comfy_url") or "http://127.0.0.1:8188")).download_file_to_path(output, str(target))
    return target


def process(queue_dir: Path) -> None:
    request = read_json(queue_dir / "request.json", {}) or {}
    queue_id, session_id = queue_dir.name, str(request.get("session_id") or "")
    generation_ids = model_test_review_queue.resolved_generation_job_ids(ROOT, request)
    if not generation_ids:
        raise RuntimeError("AI가 검수할 완료 모델 테스트 영상이 없습니다.")
    request.update(
        generation_job_ids=generation_ids,
        generation_job_ids_resolved_at=now_iso(),
    )
    atomic_write_json(queue_dir / "request.json", request)
    update_status(queue_dir, "preparing", stage="검수 영상 준비", progress=0.03)
    videos = {job_id: _local_video(queue_dir, job_id) for job_id in generation_ids}
    update_status(queue_dir, "preparing", stage="Qwen 검수 엔진 준비", progress=0.08)
    benchmark_jobs.set_session_review_status(ROOT, [session_id], "switching_to_qwen_review")
    ensure_vllm_engine()
    benchmark_jobs.set_session_review_status(ROOT, [session_id], "ai_reviewing")
    reports, errors = [], []
    for index, job_id in enumerate(generation_ids, start=1):
        queue_status = read_json(queue_dir / "status.json", {}) or {}
        if queue_status.get("cancel_requested"):
            ensure_comfy_engine()
            update_status(queue_dir, "cancelled", stage="사용자 요청으로 AI 검수 중단", reviewed_count=len(reports), failed_count=len(errors), cancelled_at=now_iso())
            benchmark_jobs.set_session_review_status(ROOT, [session_id], "review_cancelled")
            return
        if STOP:
            raise RuntimeError("검수 Worker 종료 요청으로 중단했습니다.")
        try:
            update_status(queue_dir, "reviewing", stage=f"AI 검수 {index}/{len(generation_ids)}", progress=0.1 + 0.85 * (index - 1) / max(1, len(generation_ids)), current_generation_job_id=job_id)
            job_dir = h3_queue.resolve_job_dir(ROOT, job_id)
            generation_request = read_json(job_dir / "request.json", {}) or {}
            is_r2v = str((generation_request.get("benchmark_contract") or {}).get("input_mode") or "") == "h3_r2v_multi_reference"
            reviewer = model_test_r2v_ai_reviewer if is_r2v else model_test_ai_reviewer
            report = reviewer.review_benchmark_video(video_path=videos[job_id], request=generation_request, review_queue_id=queue_id, job_id=job_id)
            report["reviewed_at"] = now_iso()
            report_path = queue_dir / "reports" / f"{job_id}.json"
            save = model_test_reviews.save_r2v_ai_review if is_r2v else model_test_reviews.save_ai_review
            saved = save(ROOT, str(generation_request.get("run_id") or ""), report["review"], source_path=str(report_path))
            report["review_revision"] = saved["review"]["revision"]
            atomic_write_json(report_path, report)
            generation_status = read_json(job_dir / "status.json", {}) or {}
            update_status(job_dir, str(generation_status.get("status") or "completed"), ai_review_status="completed", ai_review_queue_id=queue_id, ai_review_revision=report["review_revision"], ai_review_updated_at=now_iso())
            reports.append({"job_id": job_id, "report_path": str(report_path)})
        except Exception as exc:
            errors.append({"job_id": job_id, "error": f"{type(exc).__name__}: {exc}"})
    if (read_json(queue_dir / "status.json", {}) or {}).get("cancel_requested"):
        ensure_comfy_engine()
        update_status(queue_dir, "cancelled", stage="사용자 요청으로 AI 검수 중단", reviewed_count=len(reports), failed_count=len(errors), cancelled_at=now_iso())
        benchmark_jobs.set_session_review_status(ROOT, [session_id], "review_cancelled")
        return
    final = "completed" if not errors else ("completed_with_failures" if reports else "failed")
    atomic_write_json(queue_dir / "summary.json", {"queue_id": queue_id, "session_id": session_id, "reports": reports, "errors": errors, "completed_at": now_iso()})
    ensure_comfy_engine()
    update_status(queue_dir, final, stage="AI 검수 완료" if reports else "AI 검수 실패", progress=1.0, reviewed_count=len(reports), failed_count=len(errors), completed_at=now_iso())
    benchmark_jobs.set_session_review_status(ROOT, [session_id], "review_completed" if not errors else ("review_completed_with_failures" if reports else "ai_review_failed"))


def process_candidate(queue_dir: Path) -> None:
    queue_request = read_json(queue_dir / "request.json", {}) or {}
    review_id = queue_dir.name
    job_id = str(queue_request.get("generation_job_id") or "")
    job_dir = h3_queue.resolve_job_dir(ROOT, job_id)
    generation_request = read_json(job_dir / "request.json", {}) or {}
    generation_status = read_json(job_dir / "status.json", {}) or {}
    manifest = read_json(job_dir / "manifest.json", {}) or {}
    if generation_status.get("status") != "completed":
        raise RuntimeError("완료된 04 후보 영상만 AI 검수할 수 있습니다.")
    video_path = Path(
        str(manifest.get("local_video_path") or generation_status.get("local_video_path") or "")
    )
    if not video_path.is_file():
        raise FileNotFoundError(f"로컬 후보 영상이 없습니다: {video_path}")
    current = read_json(queue_dir / "status.json", {}) or {}
    if current.get("cancel_requested"):
        deleted = current.get("candidate_set_deleted")
        update_status(
            queue_dir,
            "cancelled",
            stage=(
                "후보군 삭제로 AI 검수 취소"
                if deleted else "후보 AI 검수 비활성화로 취소"
            ),
            cancelled_at=now_iso(),
        )
        return
    update_status(
        queue_dir,
        "preparing",
        stage="Qwen3.8 시각 검수 엔진 준비",
        progress=0.05,
    )
    ensure_vllm_engine()
    update_status(queue_dir, "reviewing", stage="후보 영상 AI 검수 중", progress=0.15)
    report = candidate_ai_reviewer.review_candidate_video(
        video_path=video_path,
        request=generation_request,
        review_id=review_id,
        job_id=job_id,
        root=ROOT,
    )
    current = read_json(queue_dir / "status.json", {}) or {}
    if current.get("cancel_requested"):
        deleted = current.get("candidate_set_deleted")
        update_status(
            queue_dir,
            "cancelled",
            stage=(
                "후보군 삭제로 AI 검수 결과 저장 취소"
                if deleted else "후보 AI 검수 비활성화로 결과 저장 취소"
            ),
            cancelled_at=now_iso(),
        )
        return
    report["reviewed_at"] = now_iso()
    atomic_write_json(queue_dir / "report.json", report)
    update_status(
        job_dir,
        "completed",
        candidate_ai_review_status="completed",
        candidate_ai_review_id=review_id,
        candidate_ai_review_score=report.get("overall_score"),
        candidate_ai_review_verdict=report.get("verdict"),
        candidate_ai_review_updated_at=now_iso(),
    )
    update_status(
        queue_dir,
        "completed",
        stage="후보 AI 검수 완료",
        progress=1.0,
        completed_at=now_iso(),
    )


def main() -> None:
    signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGINT, _stop)
    QUEUE.mkdir(parents=True, exist_ok=True)
    candidate_review_queue.recover_orphaned_reviews(ROOT, os.getpid())
    while not STOP:
        candidate_review_queue.sync_enabled_reviews(ROOT)
        directory, blocked_by = engine_scheduler.claim_review(ROOT, os.getpid())
        if directory is None:
            if blocked_by == "generation":
                _mark_queued_reviews_waiting_for_generation()
                _worker("idle", stage="H3·ComfyUI 생성 큐 완료 후 수동 검수 대기")
            else:
                enabled = candidate_review_queue.settings(ROOT)["enabled"]
                if not enabled and engine_switch.vllm_ready():
                    try:
                        ensure_comfy_engine()
                    except Exception as exc:
                        _worker(
                            "idle",
                            stage="후보 AI 검수 비활성화 · ComfyUI 복구 실패",
                            engine_error=f"{type(exc).__name__}: {exc}",
                        )
                        time.sleep(2)
                        continue
                _worker(
                    "idle",
                    stage=(
                        "04 후보 자동 AI 검수 활성 · 새 완료 영상 대기"
                        if enabled
                        else "수동 모델 테스트 검수 큐 대기"
                    ),
                )
            time.sleep(2); continue
        try:
            request = read_json(directory / "request.json", {}) or {}
            is_candidate = request.get("queue_name") == "candidate_ai_review"
            _worker(
                "busy",
                queue_id=directory.name,
                review_kind="candidate" if is_candidate else "model_test",
                stage="04 후보 AI 검수" if is_candidate else "모델 테스트 AI 검수",
            )
            if is_candidate:
                process_candidate(directory)
            else:
                process(directory)
        except Exception as exc:
            update_status(directory, "failed", stage="AI 검수 실패", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc(), failed_at=now_iso())
            request = read_json(directory / "request.json", {}) or {}
            if request.get("queue_name") == "candidate_ai_review":
                time.sleep(2)
            else:
                benchmark_jobs.set_session_review_status(ROOT, [str(request.get("session_id") or "")], "ai_review_failed")
    _worker("stopped")


if __name__ == "__main__":
    main()
