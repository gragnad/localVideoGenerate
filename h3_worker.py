from __future__ import annotations

"""Dedicated worker for the batch-free H3 production queue."""

import hashlib
import json
import os
import signal
import time
import traceback
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from comfy_client import ComfyClient
from engine_switch import ensure_comfy_engine
import benchmark_jobs
import engine_scheduler
import h3_queue
from job_queue import atomic_write_json, now_iso, read_json, update_status
from remote_render_power import Config as RemoteRenderPowerConfig
from remote_render_power import RemoteRenderPowerManager


ROOT = Path(os.environ.get("VIDEO_ENGINE_ROOT", Path.home() / "local-ai/video-engine"))
PATHS = h3_queue.roots(ROOT)
POLL_SECONDS = float(os.environ.get("H3_WORKER_POLL_SECONDS", "2"))
TIMEOUT_SECONDS = float(os.environ.get("H3_JOB_TIMEOUT_SECONDS", str(8 * 60 * 60)))
WORKER_LANE = str(os.environ.get("H3_WORKER_LANE") or "local_generation").strip()
if WORKER_LANE not in {"windows_candidate", "local_generation"}:
    raise ValueError(f"지원하지 않는 H3 Worker 큐 레인입니다: {WORKER_LANE}")
WORKER_LABEL = (
    "Windows 후보 Worker"
    if WORKER_LANE == "windows_candidate"
    else "로컬 생성 Worker"
)
WORKER_STATUS_PATH = (
    PATHS["windows_candidate_worker_status"]
    if WORKER_LANE == "windows_candidate"
    else PATHS["worker_status"]
)
STOP_REQUESTED = False
REMOTE_RENDER_POWER = RemoteRenderPowerManager(
    RemoteRenderPowerConfig.from_env()
    if WORKER_LANE == "windows_candidate"
    else None,
    root=ROOT,
)


class H3JobCancelled(RuntimeError):
    pass


def _active_tracking_status(job_dir: Path, fallback: str = "comfy_queued") -> str:
    """Keep a submitted prompt active while ComfyUI is temporarily unresponsive."""
    value = str((read_json(job_dir / "status.json", {}) or {}).get("status") or "")
    if value in {"submitted", "comfy_queued", "running"}:
        return value
    return fallback


def _record_comfy_poll_delay(
    job_dir: Path,
    *,
    label: str,
    prompt_id: str,
    elapsed: float,
    exc: requests.RequestException,
) -> None:
    status = _active_tracking_status(job_dir)
    update_status(
        job_dir,
        status,
        stage=f"{label} ComfyUI 응답 지연 · 같은 작업 재확인",
        prompt_id=prompt_id,
        elapsed_seconds=round(elapsed, 1),
        last_poll_error=f"{type(exc).__name__}: {exc}",
        last_poll_error_at=now_iso(),
    )
    _worker_status("busy", current_job_id=job_dir.name, stage="comfy_poll_retry")


def _wait_for_comfy_submission_slot(
    job_dir: Path,
    client: ComfyClient,
    *,
    label: str,
) -> None:
    """Do not add another prompt while the target ComfyUI already has work."""
    while True:
        _raise_if_cancel_requested(job_dir, client)
        if STOP_REQUESTED:
            raise RuntimeError("H3 Worker 종료 요청으로 작업을 중단했습니다.")
        try:
            queue = client.get_queue()
        except requests.RequestException as exc:
            update_status(
                job_dir,
                "preparing",
                stage=f"{label} ComfyUI 큐 확인 지연 · 제출 보류",
                last_poll_error=f"{type(exc).__name__}: {exc}",
                last_poll_error_at=now_iso(),
            )
            _worker_status(
                "busy", current_job_id=job_dir.name, stage="comfy_queue_check_retry"
            )
            time.sleep(POLL_SECONDS)
            continue
        running = len(list(queue.get("queue_running") or []))
        pending = len(list(queue.get("queue_pending") or []))
        if running + pending == 0:
            return
        update_status(
            job_dir,
            "preparing",
            stage=f"{label} ComfyUI 기존 작업 완료 대기",
            message=f"실행 {running}개 · 대기 {pending}개가 끝날 때까지 새 요청을 보내지 않습니다.",
            comfy_running_count=running,
            comfy_pending_count=pending,
        )
        _worker_status(
            "busy", current_job_id=job_dir.name, stage="waiting_for_comfy_slot"
        )
        time.sleep(POLL_SECONDS)


def _stop(_signum: int, _frame: Any) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True


def _worker_status(state: str, **fields: Any) -> None:
    payload = read_json(WORKER_STATUS_PATH, {}) or {}
    payload.update(fields)
    payload.update(
        state=state,
        pid=os.getpid(),
        queue_lane=WORKER_LANE,
        worker_label=WORKER_LABEL,
        updated_at=now_iso(),
    )
    atomic_write_json(WORKER_STATUS_PATH, payload)


def _queue_position(queue: dict[str, Any], prompt_id: str) -> tuple[str, int | None]:
    def contains(entry: Any) -> bool:
        if isinstance(entry, (list, tuple)):
            return any(str(value) == prompt_id for value in entry[:3])
        return isinstance(entry, dict) and str(entry.get("prompt_id")) == prompt_id
    if any(contains(row) for row in queue.get("queue_running") or []):
        return "running", 0
    for index, row in enumerate(queue.get("queue_pending") or [], start=1):
        if contains(row):
            return "comfy_queued", index
    return "submitted", None


WINDOWS_COMFY_URL = "http://100.78.202.37:8189"
LOCAL_HOSTNAMES = {"", "127.0.0.1", "localhost", "::1"}


def _ensure_client(request: dict[str, Any]) -> ComfyClient:
    lane = str(request.get("queue_lane") or "").strip()
    comfy_url = str(request.get("comfy_url") or "").strip().rstrip("/")

    if lane == "windows_candidate":
        # Windows lane: must resolve to the approved Windows address.
        if not comfy_url:
            comfy_url = WINDOWS_COMFY_URL
        hostname = str(urlparse(comfy_url).hostname or "").lower()
        if hostname in LOCAL_HOSTNAMES:
            raise ValueError(
                f"Windows 후보 작업에 로컬 주소({hostname})가 지정되었습니다. "
                f"Windows ComfyUI({WINDOWS_COMFY_URL})를 사용하세요."
            )
        client = ComfyClient(comfy_url)
        if REMOTE_RENDER_POWER.manages(comfy_url):
            REMOTE_RENDER_POWER.ensure_comfy(client)
        else:
            client.health()
        return client

    # Non-Windows lanes keep the previous behaviour.
    comfy_url = comfy_url or "http://127.0.0.1:8188"
    client = ComfyClient(comfy_url)
    if REMOTE_RENDER_POWER.manages(comfy_url):
        REMOTE_RENDER_POWER.ensure_comfy(client)
        return client
    try:
        client.health()
    except Exception:
        hostname = str(urlparse(comfy_url).hostname or "").lower()
        if hostname not in LOCAL_HOSTNAMES:
            raise
        ensure_comfy_engine()
        client.health()
    return client


def _raise_if_cancel_requested(
    job_dir: Path,
    client: ComfyClient | None = None,
    prompt_id: str = "",
) -> None:
    status = read_json(job_dir / "status.json", {}) or {}
    if not status.get("cancel_requested"):
        return
    if client is not None and prompt_id:
        try:
            client.cancel_prompt(prompt_id)
        except Exception:
            pass
    raise H3JobCancelled("사용자가 H3 큐 그룹을 강제정지했습니다.")


def process_video_upscale(job_dir: Path, request: dict[str, Any]) -> None:
    """Upload one Spark result and run the fixed Windows RTX/RIFE workflow."""
    source = Path(str(request.get("source_video_path") or ""))
    if not source.is_file():
        raise FileNotFoundError(f"Spark 업스케일 원본 영상이 없습니다: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != str(request.get("source_output_sha256") or ""):
        raise ValueError("Spark 업스케일 원본 영상 해시가 변경되었습니다.")

    workflow = read_json(job_dir / "workflow_api.json", {}) or {}
    loader = workflow.get("7") or {}
    output_node = workflow.get("8") or {}
    if loader.get("class_type") != "VHS_LoadVideo":
        raise ValueError("Windows 업스케일 영상 입력 노드가 올바르지 않습니다.")
    if (
        output_node.get("class_type") != "VHS_VideoCombine"
        or str((output_node.get("inputs") or {}).get("format") or "")
        != "video/h264-mp4"
    ):
        raise ValueError("Windows 업스케일 H264 출력 노드가 올바르지 않습니다.")

    started = time.monotonic()
    update_status(
        job_dir,
        "preparing",
        stage="Windows RTX 1080p·60fps 업스케일 준비",
        started_at=now_iso(),
        progress=0.02,
    )
    client = _ensure_client(request)
    _raise_if_cancel_requested(job_dir, client)
    update_status(
        job_dir,
        "uploading",
        stage="Spark 결과 영상을 Windows ComfyUI에 업로드",
        progress=0.08,
    )
    uploaded = client.upload_input(
        filename=source.name,
        content=source.read_bytes(),
        subfolder=f"h3_upscale_jobs/{job_dir.name}",
        overwrite=True,
    )
    uploaded_value = "/".join(
        part.strip("/")
        for part in (uploaded.get("subfolder"), uploaded.get("name"))
        if str(part or "").strip("/")
    )
    workflow["7"]["inputs"]["video"] = uploaded_value
    atomic_write_json(job_dir / "workflow_api_runtime.json", workflow)
    manifest = read_json(job_dir / "manifest.json", {}) or {}
    manifest.update(
        status="built",
        uploads=[
            {
                "source_path": str(source),
                "sha256": request.get("source_output_sha256"),
                "comfy_response": uploaded,
            }
        ],
        updated_at=now_iso(),
    )
    atomic_write_json(job_dir / "manifest.json", manifest)

    _raise_if_cancel_requested(job_dir, client)
    update_status(
        job_dir,
        "submitting",
        stage="Windows RTX/RIFE 워크플로우 제출",
        progress=0.18,
    )
    _wait_for_comfy_submission_slot(job_dir, client, label="Windows 1080p·60fps 업스케일")
    response = client.queue_prompt(workflow)
    prompt_id = str(response["prompt_id"])
    atomic_write_json(job_dir / "queue_response.json", response)
    manifest.update(status="queued", prompt_id=prompt_id, updated_at=now_iso())
    atomic_write_json(job_dir / "manifest.json", manifest)
    update_status(
        job_dir,
        "comfy_queued",
        stage="Windows 1080p·60fps 업스케일 큐 대기",
        prompt_id=prompt_id,
        progress=0.20,
    )

    last_write = 0.0
    while True:
        _raise_if_cancel_requested(job_dir, client, prompt_id)
        if STOP_REQUESTED:
            raise RuntimeError("H3 Worker 종료 요청으로 작업을 중단했습니다.")
        elapsed = time.monotonic() - started
        if elapsed > TIMEOUT_SECONDS:
            raise TimeoutError("Windows 업스케일이 제한 시간 안에 완료되지 않았습니다.")
        try:
            history = client.get_history(prompt_id)
        except requests.RequestException as exc:
            _record_comfy_poll_delay(
                job_dir,
                label="Windows 1080p·60fps 업스케일",
                prompt_id=prompt_id,
                elapsed=elapsed,
                exc=exc,
            )
            time.sleep(POLL_SECONDS)
            continue
        if prompt_id in history:
            client._raise_on_execution_error(history[prompt_id])
            outputs = client.extract_output_files(history, prompt_id)
            if not outputs:
                raise RuntimeError("업스케일 워크플로우는 완료됐지만 영상 출력이 없습니다.")
            atomic_write_json(job_dir / "history.json", history)
            output = outputs[0]
            suffix = Path(str(output.get("filename") or "video.mp4")).suffix or ".mp4"
            source_set_id = str(request.get("source_candidate_set_id") or "ungrouped")
            local_path = (
                PATHS["outputs"] / "upscales" / source_set_id
                / f"{job_dir.name}{suffix}"
            )
            client.download_file_to_path(output, str(local_path))
            elapsed = time.monotonic() - started
            output_sha256 = hashlib.sha256(local_path.read_bytes()).hexdigest()
            manifest.update(
                status="completed",
                outputs=outputs,
                local_video_path=str(local_path),
                output_sha256=output_sha256,
                generation_seconds=round(elapsed, 3),
                output_codec="h264",
                output_width=int((request.get("target_resolution") or {}).get("width") or 1920),
                output_height=int((request.get("target_resolution") or {}).get("height") or 1080),
                output_fps=60,
                completed_at=now_iso(),
                updated_at=now_iso(),
            )
            atomic_write_json(job_dir / "manifest.json", manifest)
            update_status(
                job_dir,
                "completed",
                stage="Windows 1080p·60fps 업스케일 완료",
                message="H264 업스케일 영상 저장 완료",
                progress=1.0,
                outputs=outputs,
                local_video_path=str(local_path),
                elapsed_seconds=round(elapsed, 1),
                completed_at=now_iso(),
            )
            REMOTE_RENDER_POWER.touch()
            return
        if time.monotonic() - last_write >= 2:
            try:
                state, position = _queue_position(client.get_queue(), prompt_id)
            except Exception:
                state, position = "running", None
            update_status(
                job_dir,
                state,
                stage=(
                    "Windows RTX VSR·RIFE 업스케일 실행 중"
                    if state == "running"
                    else "Windows 1080p·60fps 업스케일 큐 대기"
                ),
                prompt_id=prompt_id,
                queue_position=position,
                progress=0.30 if state == "running" else 0.20,
                elapsed_seconds=round(elapsed, 1),
            )
            _worker_status("busy", current_job_id=job_dir.name, stage=state)
            last_write = time.monotonic()
        time.sleep(POLL_SECONDS)


def process_job(job_dir: Path) -> None:
    request = read_json(job_dir / "request.json", {}) or {}
    job_type = str(request.get("job_type") or "")
    generation_mode = str(request.get("generation_mode") or "r2v").lower()
    benchmark_job_types = {"h3_r2v_benchmark", "h3_model_benchmark"}
    is_benchmark = job_type in benchmark_job_types
    supported_job_types = {"h3_r2v_generate", "h3_video_upscale", *benchmark_job_types}
    if job_type not in supported_job_types or request.get("queue_name") != "h3_generation":
        raise ValueError("H3 생성 큐 작업이 아닙니다.")
    _raise_if_cancel_requested(job_dir)
    if job_type == "h3_video_upscale":
        process_video_upscale(job_dir, request)
        return
    workflow = read_json(job_dir / "workflow_api.json", {}) or {}
    if not workflow:
        raise ValueError("컴파일된 H3 워크플로우가 없습니다.")
    started = time.monotonic()
    label = "H3 R2V 테스트" if job_type == "h3_r2v_benchmark" else "H3 모델 테스트" if is_benchmark else f"H3 {generation_mode.upper()} 생성"
    reference_label = "시작 이미지" if generation_mode == "i2v" else "Picture"
    update_status(job_dir, "preparing", stage=f"{label} 준비", started_at=now_iso(), progress=0.02)
    client = _ensure_client(request)
    _raise_if_cancel_requested(job_dir, client)
    uploaded = []
    references = list(
        request.get("media_references") or request.get("references") or []
    )
    patches = list(request.get("reference_patches") or [])
    if len(references) != len(patches):
        raise ValueError("H3 미디어 참조와 실행 바인딩 개수가 다릅니다.")
    subfolder = f"h3_jobs/{job_dir.name}"
    for index, (reference, patch) in enumerate(zip(references, patches), start=1):
        _raise_if_cancel_requested(job_dir, client)
        media_type = str(
            patch.get("media_type") or reference.get("media_type") or "image"
        ).lower()
        if media_type not in {"image", "video"}:
            raise ValueError("지원하지 않는 H3 미디어 참조 유형입니다.")
        item_label = "액션 비디오" if media_type == "video" else reference_label
        source = Path(str(reference.get("source_path") or ""))
        if not source.is_file():
            raise FileNotFoundError(f"{item_label} 파일을 찾을 수 없습니다.")
        content = source.read_bytes()
        if hashlib.sha256(content).hexdigest() != reference.get("sha256"):
            raise ValueError(f"{item_label} 파일 해시가 변경되었습니다.")
        update_status(job_dir, "uploading", stage=f"{label} {item_label} 업로드 {index}/{len(references)}", progress=0.03 + 0.12 * index / len(references))
        upload = client.upload_input if media_type == "video" else client.upload_image
        result = upload(
            filename=source.name,
            content=content,
            subfolder=subfolder,
            overwrite=True,
        )
        node = workflow.get(str(patch.get("node_id") or ""))
        input_name = str(patch.get("input") or "")
        if not node or input_name not in dict(node.get("inputs") or {}):
            raise ValueError(f"{item_label} 실행 바인딩이 유효하지 않습니다.")
        value = "/".join(part.strip("/") for part in (result.get("subfolder"), result.get("name")) if str(part or "").strip("/"))
        node["inputs"][input_name] = value
        uploaded.append({**reference, "comfy_response": result})
    atomic_write_json(job_dir / "workflow_api_runtime.json", workflow)
    manifest = read_json(job_dir / "manifest.json", {}) or {}
    manifest.update(status="built", uploads=uploaded, updated_at=now_iso())
    atomic_write_json(job_dir / "manifest.json", manifest)
    _raise_if_cancel_requested(job_dir, client)
    update_status(job_dir, "submitting", stage=f"{label} ComfyUI 큐 제출", progress=0.18)
    _wait_for_comfy_submission_slot(job_dir, client, label=label)
    response = client.queue_prompt(workflow)
    prompt_id = str(response["prompt_id"])
    atomic_write_json(job_dir / "queue_response.json", response)
    manifest.update(status="queued", prompt_id=prompt_id, updated_at=now_iso())
    atomic_write_json(job_dir / "manifest.json", manifest)
    update_status(job_dir, "comfy_queued", stage=f"{label} ComfyUI 큐 대기", prompt_id=prompt_id, progress=0.20)
    _raise_if_cancel_requested(job_dir, client, prompt_id)
    last_write = 0.0
    while True:
        _raise_if_cancel_requested(job_dir, client, prompt_id)
        if STOP_REQUESTED:
            raise RuntimeError("H3 Worker 종료 요청으로 작업을 중단했습니다.")
        elapsed = time.monotonic() - started
        if elapsed > TIMEOUT_SECONDS:
            raise TimeoutError("H3 생성이 제한 시간 안에 완료되지 않았습니다.")
        try:
            history = client.get_history(prompt_id)
        except requests.RequestException as exc:
            _record_comfy_poll_delay(
                job_dir,
                label=label,
                prompt_id=prompt_id,
                elapsed=elapsed,
                exc=exc,
            )
            time.sleep(POLL_SECONDS)
            continue
        if prompt_id in history:
            client._raise_on_execution_error(history[prompt_id])
            outputs = client.extract_output_files(history, prompt_id)
            if not outputs:
                raise RuntimeError("H3 워크플로우는 완료됐지만 영상 출력이 없습니다.")
            atomic_write_json(job_dir / "history.json", history)
            output = outputs[0]
            suffix = Path(str(output.get("filename") or "video.mp4")).suffix or ".mp4"
            output_group = str(request.get("candidate_set_id") or request.get("test_queue_id") or "ungrouped")
            local_path = PATHS["outputs"] / output_group / f"{job_dir.name}{suffix}"
            client.download_file_to_path(output, str(local_path))
            elapsed = time.monotonic() - started
            output_sha256 = hashlib.sha256(local_path.read_bytes()).hexdigest()
            manifest.update(status="completed", outputs=outputs, local_video_path=str(local_path), output_sha256=output_sha256, generation_seconds=round(elapsed, 3), completed_at=now_iso(), updated_at=now_iso())
            atomic_write_json(job_dir / "manifest.json", manifest)
            update_status(job_dir, "completed", stage=f"{label} 완료", message="테스트 영상 저장 완료" if is_benchmark else "후보 영상 저장 완료", progress=1.0, outputs=outputs, local_video_path=str(local_path), elapsed_seconds=round(elapsed, 1), completed_at=now_iso())
            if is_benchmark:
                benchmark_jobs.record_result(
                    ROOT,
                    request,
                    status="completed",
                    generation_seconds=elapsed,
                    output_path=str(local_path),
                    output_sha256=output_sha256,
                    outputs=outputs,
                )
                h3_queue.reconcile_test_queues(ROOT, str(request["test_queue_id"]))
            else:
                h3_queue.reconcile(ROOT, str(request["candidate_set_id"]))
            REMOTE_RENDER_POWER.touch()
            return
        if time.monotonic() - last_write >= 2:
            try:
                state, position = _queue_position(client.get_queue(), prompt_id)
            except Exception:
                state, position = "running", None
            update_status(job_dir, state, stage=f"{label} 실행 중" if state == "running" else f"{label} ComfyUI 큐 대기", prompt_id=prompt_id, queue_position=position, progress=0.30 if state == "running" else 0.20, elapsed_seconds=round(elapsed, 1))
            _worker_status("busy", current_job_id=job_dir.name, stage=state)
            last_write = time.monotonic()
        time.sleep(POLL_SECONDS)


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    PATHS["jobs"].mkdir(parents=True, exist_ok=True)
    _worker_status("idle", current_job_id=None, started_at=now_iso())
    while not STOP_REQUESTED:
        job_dir, blocked_by = engine_scheduler.claim_generation(
            ROOT,
            os.getpid(),
            lane=WORKER_LANE,
        )
        if job_dir is None:
            stage = (
                "외부 Qwen 엔진 사용 종료 후 H3 큐 재개"
                if blocked_by == "review"
                else f"{WORKER_LABEL} 큐 대기"
            )
            _worker_status("idle", current_job_id=None, stage=stage)
            if WORKER_LANE == "windows_candidate":
                try:
                    if REMOTE_RENDER_POWER.maybe_hibernate():
                        _worker_status(
                            "idle",
                            current_job_id=None,
                            stage="Windows 후보 렌더 PC 최대절전 요청 완료",
                            last_hibernate_confirmed_at=now_iso(),
                            power_error=None,
                        )
                except Exception as exc:
                    _worker_status(
                        "idle",
                        current_job_id=None,
                        stage="Windows 후보 렌더 PC 최대절전 요청 실패",
                        power_error=f"{type(exc).__name__}: {exc}",
                        last_hibernate_failed_at=now_iso(),
                    )
                    REMOTE_RENDER_POWER.touch()
            time.sleep(POLL_SECONDS)
            continue
        try:
            _worker_status("busy", current_job_id=job_dir.name, stage="preparing")
            process_job(job_dir)
        except H3JobCancelled as exc:
            request = read_json(job_dir / "request.json", {}) or {}
            stamp = now_iso()
            update_status(
                job_dir,
                "cancelled",
                stage="H3 큐 그룹 강제정지 완료",
                message=str(exc),
                cancel_requested=True,
                cancelled_at=stamp,
                progress=0.0,
            )
            manifest = read_json(job_dir / "manifest.json", {}) or {}
            manifest.update(status="cancelled", cancel_requested=True, cancelled_at=stamp, updated_at=stamp)
            atomic_write_json(job_dir / "manifest.json", manifest)
            if request.get("job_type") in {"h3_r2v_benchmark", "h3_model_benchmark"}:
                benchmark_jobs.record_result(ROOT, request, status="cancelled", error=str(exc))
                if request.get("test_queue_id"):
                    h3_queue.reconcile_test_queues(ROOT, str(request["test_queue_id"]))
            elif request.get("candidate_set_id"):
                h3_queue.reconcile(ROOT, str(request["candidate_set_id"]))
            REMOTE_RENDER_POWER.touch()
        except Exception as exc:
            request = read_json(job_dir / "request.json", {}) or {}
            failed_stage = (
                "Windows 1080p·60fps 업스케일 실패"
                if request.get("job_type") == "h3_video_upscale"
                else "H3 생성 실패"
            )
            update_status(job_dir, "failed", stage=failed_stage, error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc(), failed_at=now_iso())
            if request.get("job_type") in {"h3_r2v_benchmark", "h3_model_benchmark"}:
                benchmark_jobs.record_result(ROOT, request, status="failed", error=f"{type(exc).__name__}: {exc}")
                if request.get("test_queue_id"):
                    h3_queue.reconcile_test_queues(ROOT, str(request["test_queue_id"]))
            elif request.get("candidate_set_id"):
                h3_queue.reconcile(ROOT, str(request["candidate_set_id"]))
            REMOTE_RENDER_POWER.touch()
    _worker_status("stopped", current_job_id=None, stopped_at=now_iso())


if __name__ == "__main__":
    main()
