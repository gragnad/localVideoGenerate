from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from batch_manager import (
    attach_job_to_batch,
    batch_generation_is_terminal,
    batch_typed_jobs_are_terminal,
    find_batches_by_status,
    load_open_batch,
    mark_batch_generation_complete,
    update_batch,
)
from comfy_client import ComfyAPIError, ComfyClient
import correction_policy
from engine_switch import (
    ensure_comfy_engine,
    ensure_vllm_engine,
    engine_snapshot,
)
from job_queue import (
    atomic_write_json,
    claim_next_queued_job,
    now_iso,
    read_json,
    update_status,
)
from review_workflow import (
    build_contact_sheet_workflow,
    comfy_video_path,
    find_primary_video_output,
)
from vllm_reviewer import review_video
from video_assembler import assemble_clips
from workflow_builder import SegmentSpec, build_retake_workflow, build_workflow


HOME = Path.home()
ENGINE_ROOT = Path(os.environ.get("VIDEO_ENGINE_ROOT", HOME / "local-ai/video-engine"))
JOBS_ROOT = ENGINE_ROOT / "jobs"
WORKER_STATUS = ENGINE_ROOT / "worker_status.json"
POLL_SECONDS = float(os.environ.get("VIDEO_WORKER_POLL_SECONDS", "2"))
COMFY_TIMEOUT_SECONDS = float(os.environ.get("VIDEO_JOB_TIMEOUT_SECONDS", str(8 * 60 * 60)))
DEFAULT_COMFY_START_TIMEOUT = float(os.environ.get("COMFY_START_TIMEOUT", "180"))
DEFAULT_WORKFLOW_DIR = Path(
    os.environ.get(
        "COMFY_WORKFLOW_DIR",
        HOME / "ai-workspace/apps/ComfyUI/user/default/workflows",
    )
).expanduser()
_REVIEW_TEMPLATE_ENV = os.environ.get("LTX_REVIEW_WORKFLOW_TEMPLATE", "").strip()
DEFAULT_REVIEW_TEMPLATE = Path(
    _REVIEW_TEMPLATE_ENV
    or DEFAULT_WORKFLOW_DIR / "(CH)Video_ContactSheet_API_fixed.json"
).expanduser()
CONTACT_SHEET_AUTOMATION_NOT_BEFORE = 0.0
DIRECT_VIDEO_PIPELINE_VERSION = "1.8.0"
LEGACY_CONTACT_SHEET_PIPELINE_VERSION = "1.7.0"
AUTO_RESTORE_COMFY_AFTER_REVIEW = (
    os.environ.get("AUTO_RESTORE_COMFY_AFTER_REVIEW", "true")
    .strip()
    .lower()
    not in {"0", "false", "no", "off"}
)

STOP_REQUESTED = False
LAST_BATCH_LOG_SIGNATURE: tuple[str, str, str] | None = None


def log_event(event: str, **fields: Any) -> None:
    payload = {
        "time": now_iso(),
        "event": event,
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def log_batch_state(batch: dict[str, Any] | None) -> None:
    global LAST_BATCH_LOG_SIGNATURE
    if not batch:
        signature = ("-", "-", "-")
        if signature != LAST_BATCH_LOG_SIGNATURE:
            log_event("batch_none")
            LAST_BATCH_LOG_SIGNATURE = signature
        return

    signature = (
        str(batch.get("batch_id") or "-"),
        str(batch.get("status") or "-"),
        str(batch.get("stage") or "-"),
    )
    if signature != LAST_BATCH_LOG_SIGNATURE:
        log_event(
            "batch_state",
            batch_id=signature[0],
            status=signature[1],
            stage=signature[2],
            next_stage=batch.get("next_stage"),
            message=batch.get("message"),
        )
        LAST_BATCH_LOG_SIGNATURE = signature


def handle_stop(signum: int, frame: Any) -> None:
    del signum, frame
    global STOP_REQUESTED
    STOP_REQUESTED = True


def write_worker_status(state: str, **fields: Any) -> None:
    payload = read_json(WORKER_STATUS, {}) or {}
    payload.update(fields)
    payload.update(
        {
            "state": state,
            "pid": os.getpid(),
            "updated_at": now_iso(),
        }
    )
    atomic_write_json(WORKER_STATUS, payload)


def run_comfy_start_script(script_path: Path) -> str:
    if not script_path.is_file():
        raise FileNotFoundError(f"ComfyUI 시작 스크립트를 찾을 수 없습니다: {script_path}")
    if not os.access(script_path, os.X_OK):
        raise PermissionError(f"ComfyUI 시작 스크립트에 실행 권한이 없습니다: {script_path}")

    completed = subprocess.run(
        [str(script_path)],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    output = "\n".join(
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part and part.strip()
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"ComfyUI 시작 스크립트 실패 (exit={completed.returncode})\n{output}"
        )
    return output or "ComfyUI 시작 스크립트 실행 완료"


def ensure_comfy_ready(request: dict[str, Any]) -> ComfyClient:
    comfy_url = str(request.get("comfy_url") or "http://127.0.0.1:8188")
    client = ComfyClient(comfy_url)
    try:
        client.health()
        return client
    except Exception:
        if not bool(request.get("auto_start_comfy", True)):
            raise

    update_status(
        Path(request["job_dir"]),
        "preparing",
        stage="엔진 전환 · ComfyUI 준비",
        message="vLLM이 실행 중이면 종료한 뒤 ComfyUI를 시작합니다.",
    )
    ensure_comfy_engine()
    client.health()
    return client


def queue_position(queue_payload: dict[str, Any], prompt_id: str) -> tuple[str, int | None]:
    running = queue_payload.get("queue_running") or []
    pending = queue_payload.get("queue_pending") or []

    def contains_prompt(entry: Any) -> bool:
        if isinstance(entry, (list, tuple)):
            return any(str(value) == prompt_id for value in entry[:3])
        if isinstance(entry, dict):
            return str(entry.get("prompt_id")) == prompt_id
        return False

    if any(contains_prompt(entry) for entry in running):
        return "running", 0
    for index, entry in enumerate(pending, start=1):
        if contains_prompt(entry):
            return "comfy_queued", index
    return "submitted", None


def process_generate_job(job_dir: Path) -> None:
    request = read_json(job_dir / "request.json", {}) or {}
    if not request:
        raise ValueError("request.json이 비어 있습니다.")
    request["job_dir"] = str(job_dir)
    request["job_id"] = job_dir.name

    update_status(
        job_dir,
        "preparing",
        stage="작업 준비",
        started_at=now_iso(),
        worker_pid=os.getpid(),
        progress=0.02,
    )
    client = ensure_comfy_ready(request)

    template_path = Path(request["template_path"]).expanduser()
    template = json.loads(template_path.read_text(encoding="utf-8"))
    if not isinstance(template, dict) or not template:
        raise ValueError("API 워크플로 템플릿이 비어 있습니다.")

    segments_request = request.get("segments") or []
    if not segments_request:
        raise ValueError("이미지 구간 정보가 없습니다.")

    comfy_subfolder = f"video_jobs/{job_dir.name}"
    segment_specs: list[SegmentSpec] = []
    upload_records: list[dict[str, Any]] = []
    total_uploads = len(segments_request)

    for index, segment in enumerate(segments_request, start=1):
        source_path = Path(segment["source_path"])
        content = source_path.read_bytes()
        stored_name = str(segment["stored_name"])
        write_worker_status(
            "busy",
            current_job=job_dir.name,
            stage=f"이미지 업로드 {index}/{total_uploads}",
        )
        update_status(
            job_dir,
            "uploading",
            stage=f"이미지 업로드 {index}/{total_uploads}",
            message=str(segment.get("original_name") or stored_name),
            progress=0.03 + (0.12 * index / total_uploads),
        )
        result = client.upload_image(
            filename=stored_name,
            content=content,
            subfolder=comfy_subfolder,
            overwrite=True,
        )
        upload_records.append(
            {
                "original_name": segment.get("original_name"),
                "stored_name": stored_name,
                "sha256": hashlib.sha256(content).hexdigest(),
                "comfy_response": result,
            }
        )
        segment_specs.append(
            SegmentSpec(
                image_name=result["name"],
                image_subfolder=result["subfolder"],
                prompt=str(segment["prompt"]),
                requested_seconds=float(segment["seconds"]),
                order=int(segment["order"]),
            )
        )

    retake_video_upload: dict[str, Any] | None = None
    retake_video_size = 0
    if str(request.get("pipeline_stage") or "") == "retake_generation":
        source_video_path = Path(str(request.get("retake_source_video_path") or ""))
        if not source_video_path.is_file():
            raise FileNotFoundError(
                f"부분 Retake 원본 영상을 찾지 못했습니다: {source_video_path}"
            )
        video_content = source_video_path.read_bytes()
        retake_video_size = len(video_content)
        update_status(
            job_dir,
            "uploading",
            stage="부분 Retake 원본 영상 업로드",
            message=source_video_path.name,
            progress=0.16,
        )
        retake_video_upload = client.upload_input(
            filename=source_video_path.name,
            content=video_content,
            subfolder=comfy_subfolder,
            overwrite=True,
        )

    update_status(
        job_dir,
        "building",
        stage="API 워크플로 구성",
        progress=0.17,
    )
    width = int(request["resolution"]["width"])
    height = int(request["resolution"]["height"])
    common_build_args = {
        "template": template,
        "segments": segment_specs,
        "global_prompt": str(request["global_prompt"]),
        "fps": int(request["fps"]),
        "seed": int(request["seed"]),
        "filename_prefix": str(request["filename_prefix"]),
        "target_total_seconds": request.get("target_total_seconds"),
        "width": width,
        "height": height,
    }
    if retake_video_upload is not None:
        workflow, summary = build_retake_workflow(
            **common_build_args,
            retake_video_name=str(retake_video_upload["name"]),
            retake_video_subfolder=str(retake_video_upload["subfolder"]),
            retake_video_size_bytes=retake_video_size,
            retake_video_duration_seconds=float(
                request.get("retake_source_duration_seconds") or 0.0
            ),
            retake_start_seconds=float(request["retake_start_seconds"]),
            retake_end_seconds=float(request["retake_end_seconds"]),
            retake_prompt=str(request["retake_corrections"]),
            retake_strength=float(request.get("retake_strength", 1.0)),
        )
    else:
        workflow, summary = build_workflow(**common_build_args)
    atomic_write_json(job_dir / "workflow_api_runtime.json", workflow)

    manifest = read_json(job_dir / "manifest.json", {}) or {}
    manifest.update(
        {
            "status": "built",
            "uploads": upload_records,
            "retake_video_upload": retake_video_upload,
            "workflow_summary": summary,
            "updated_at": now_iso(),
        }
    )
    atomic_write_json(job_dir / "manifest.json", manifest)

    update_status(
        job_dir,
        "submitting",
        stage="ComfyUI 큐 제출",
        progress=0.20,
    )
    queue_response = client.queue_prompt(workflow)
    prompt_id = str(queue_response["prompt_id"])
    atomic_write_json(job_dir / "queue_response.json", queue_response)

    manifest.update({"status": "queued", "prompt_id": prompt_id, "updated_at": now_iso()})
    atomic_write_json(job_dir / "manifest.json", manifest)
    update_status(
        job_dir,
        "comfy_queued",
        stage="ComfyUI 큐 대기",
        prompt_id=prompt_id,
        queue_position=None,
        progress=0.22,
    )

    started_wait = time.monotonic()
    last_status_write = 0.0
    while True:
        if STOP_REQUESTED:
            raise RuntimeError("worker 종료 요청으로 작업을 중단했습니다.")
        elapsed = time.monotonic() - started_wait
        if elapsed > COMFY_TIMEOUT_SECONDS:
            raise TimeoutError(
                f"ComfyUI 실행이 {COMFY_TIMEOUT_SECONDS:.0f}초 안에 완료되지 않았습니다."
            )

        history = client.get_history(prompt_id)
        if prompt_id in history:
            item = history[prompt_id]
            client._raise_on_execution_error(item)
            atomic_write_json(job_dir / "history.json", history)
            outputs = client.extract_output_files(history, prompt_id)
            manifest.update(
                {
                    "status": "completed",
                    "completed_at": now_iso(),
                    "outputs": outputs,
                    "updated_at": now_iso(),
                }
            )
            atomic_write_json(job_dir / "manifest.json", manifest)
            update_status(
                job_dir,
                "completed",
                stage="완료",
                message=f"결과 {len(outputs)}개",
                progress=1.0,
                elapsed_seconds=round(elapsed, 1),
                outputs=outputs,
                completed_at=now_iso(),
            )
            return

        now = time.monotonic()
        if now - last_status_write >= 2.0:
            try:
                queue = client.get_queue()
                state, position = queue_position(queue, prompt_id)
            except Exception:
                state, position = "running", None
            stage = "ComfyUI 실행 중" if state == "running" else "ComfyUI 큐 대기"
            write_worker_status(
                "busy",
                current_job=job_dir.name,
                stage=stage,
                elapsed_seconds=round(elapsed, 1),
            )
            update_status(
                job_dir,
                state,
                stage=stage,
                prompt_id=prompt_id,
                queue_position=position,
                progress=0.30 if state == "running" else 0.22,
                elapsed_seconds=round(elapsed, 1),
                message=(
                    "현재 실행 중"
                    if state == "running"
                    else (f"대기 순서 {position}" if position else "큐 상태 확인 중")
                ),
            )
            last_status_write = now
        time.sleep(POLL_SECONDS)



def process_contact_sheet_job(job_dir: Path) -> None:
    request = read_json(job_dir / "request.json", {}) or {}
    if not request:
        raise ValueError("request.json이 비어 있습니다.")
    request["job_dir"] = str(job_dir)
    request["job_id"] = job_dir.name

    update_status(
        job_dir,
        "preparing",
        stage="Contact Sheet 작업 준비",
        started_at=now_iso(),
        worker_pid=os.getpid(),
        progress=0.05,
    )
    client = ensure_comfy_ready(request)

    template_path = Path(request["template_path"]).expanduser()
    template = json.loads(template_path.read_text(encoding="utf-8"))
    if not isinstance(template, dict) or not template:
        raise ValueError("Contact Sheet API 워크플로가 비어 있습니다.")

    workflow, summary = build_contact_sheet_workflow(
        template=template,
        source_video_path=str(request["source_video_path"]),
        filename_prefix=str(request["filename_prefix"]),
    )
    atomic_write_json(job_dir / "workflow_api_runtime.json", workflow)

    manifest = read_json(job_dir / "manifest.json", {}) or {}
    manifest.update(
        {
            "status": "built",
            "workflow_summary": summary,
            "updated_at": now_iso(),
        }
    )
    atomic_write_json(job_dir / "manifest.json", manifest)

    update_status(
        job_dir,
        "submitting",
        stage="Contact Sheet ComfyUI 큐 제출",
        progress=0.15,
    )
    queue_response = client.queue_prompt(workflow)
    prompt_id = str(queue_response["prompt_id"])
    atomic_write_json(job_dir / "queue_response.json", queue_response)

    manifest.update(
        {
            "status": "queued",
            "prompt_id": prompt_id,
            "updated_at": now_iso(),
        }
    )
    atomic_write_json(job_dir / "manifest.json", manifest)
    update_status(
        job_dir,
        "comfy_queued",
        stage="Contact Sheet 큐 대기",
        prompt_id=prompt_id,
        progress=0.20,
    )

    started_wait = time.monotonic()
    last_status_write = 0.0
    while True:
        if STOP_REQUESTED:
            raise RuntimeError("worker 종료 요청으로 검수 작업을 중단했습니다.")
        elapsed = time.monotonic() - started_wait
        if elapsed > COMFY_TIMEOUT_SECONDS:
            raise TimeoutError(
                "Contact Sheet 생성이 제한 시간 안에 완료되지 않았습니다."
            )

        history = client.get_history(prompt_id)
        if prompt_id in history:
            item = history[prompt_id]
            client._raise_on_execution_error(item)
            atomic_write_json(job_dir / "history.json", history)
            outputs = client.extract_image_files(history, prompt_id)
            if not outputs:
                raise ComfyAPIError(
                    "Contact Sheet 실행은 완료됐지만 SaveImage 출력이 없습니다."
                )

            artifacts_dir = job_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            local_outputs: list[dict[str, Any]] = []
            for output_index, file_info in enumerate(outputs, start=1):
                suffix = Path(file_info["filename"]).suffix or ".png"
                local_path = artifacts_dir / f"contact_sheet_{output_index:02d}{suffix}"
                local_path.write_bytes(client.download_file(file_info))
                local_outputs.append(
                    {
                        **file_info,
                        "local_path": str(local_path),
                    }
                )

            manifest.update(
                {
                    "status": "completed",
                    "completed_at": now_iso(),
                    "outputs": local_outputs,
                    "contact_sheet_local_path": local_outputs[0]["local_path"],
                    "updated_at": now_iso(),
                }
            )
            outputs = local_outputs
            atomic_write_json(job_dir / "manifest.json", manifest)
            update_status(
                job_dir,
                "completed",
                stage="Contact Sheet 완료",
                message=f"검수 이미지 {len(outputs)}개",
                progress=1.0,
                elapsed_seconds=round(elapsed, 1),
                outputs=outputs,
                completed_at=now_iso(),
            )
            return

        now = time.monotonic()
        if now - last_status_write >= 2.0:
            try:
                queue = client.get_queue()
                state, position = queue_position(queue, prompt_id)
            except Exception:
                state, position = "running", None

            stage = (
                "Contact Sheet 생성 중"
                if state == "running"
                else "Contact Sheet 큐 대기"
            )
            write_worker_status(
                "busy",
                current_job=job_dir.name,
                current_batch=request.get("batch_id"),
                stage=stage,
                elapsed_seconds=round(elapsed, 1),
            )
            update_status(
                job_dir,
                state,
                stage=stage,
                prompt_id=prompt_id,
                queue_position=position,
                progress=0.50 if state == "running" else 0.20,
                elapsed_seconds=round(elapsed, 1),
                message=(
                    "현재 검수 이미지 생성 중"
                    if state == "running"
                    else (
                        f"대기 순서 {position}"
                        if position
                        else "큐 상태 확인 중"
                    )
                ),
            )
            last_status_write = now
        time.sleep(POLL_SECONDS)


def process_assemble_job(job_dir: Path) -> None:
    request = read_json(job_dir / "request.json", {}) or {}
    if not request:
        raise ValueError("합성 request.json이 비어 있습니다.")
    composition_id = str(request.get("composition_id") or "").strip()
    clips = list(request.get("clips") or [])
    if not clips:
        raise ValueError("합성할 클립이 없습니다.")
    fps = int(request.get("fps") or 24)
    update_status(
        job_dir,
        "running",
        stage="후보 클립 합성",
        started_at=now_iso(),
        worker_pid=os.getpid(),
        progress=0.1,
    )
    artifacts = job_dir / "artifacts"
    work_dir = artifacts / "assemble_work"
    output = artifacts / "assembled_master.mp4"
    summary = assemble_clips(
        clips=clips,
        output=output,
        work_dir=work_dir,
        fps=fps,
    )
    manifest = read_json(job_dir / "manifest.json", {}) or {}
    manifest.update(
        status="completed",
        completed_at=now_iso(),
        review_video_local_path=str(output),
        assembly_summary=summary,
        outputs=[
            {
                "filename": output.name,
                "subfolder": "",
                "type": "local",
                "local_path": str(output),
            }
        ],
        updated_at=now_iso(),
    )
    atomic_write_json(job_dir / "manifest.json", manifest)
    if composition_id:
        composition_path = ENGINE_ROOT / "runtime" / "compositions" / composition_id / "composition.json"
        payload = read_json(composition_path, {}) or {}
        if payload:
            payload.update(
                status="assembled",
                assembled_video_path=str(output),
                assembled_at=now_iso(),
                assembly_summary=summary,
            )
            payload["updated_at"] = now_iso()
            atomic_write_json(composition_path, payload)
    update_status(
        job_dir,
        "completed",
        stage="클립 합성 완료",
        message=f"합성 길이 {summary.get('duration_seconds', 0):.1f}초",
        progress=1.0,
        completed_at=now_iso(),
        outputs=manifest.get("outputs") or [],
    )


def process_job(job_dir: Path) -> None:
    request = read_json(job_dir / "request.json", {}) or {}
    job_type = str(request.get("job_type") or "generate")
    if job_type == "assemble":
        process_assemble_job(job_dir)
        return
    if job_type == "upscale":
        raise ValueError("업스케일/디테일 보강 작업은 더 이상 지원하지 않습니다.")
    if job_type in {"generate", "modify"}:
        process_generate_job(job_dir)
        return
    if job_type == "check" and request.get("check_type") == "contact_sheet":
        process_contact_sheet_job(job_dir)
        return
    raise ValueError(
        f"지원하지 않는 작업 유형입니다: job_type={job_type}, "
        f"check_type={request.get('check_type')}"
    )


def _batch_time_epoch(batch: dict[str, Any]) -> float:
    from datetime import datetime

    value = (
        batch.get("generation_completed_at")
        or batch.get("sealed_at")
        or batch.get("updated_at")
        or batch.get("created_at")
    )
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return 0.0


def _contact_sheet_job_id(parent_job_id: str) -> str:
    return f"{parent_job_id}__contact_sheet"


def _create_contact_sheet_job(
    *,
    batch: dict[str, Any],
    parent_job_id: str,
    template_path: Path,
) -> str:
    batch_id = str(batch["batch_id"])
    parent_dir = JOBS_ROOT / parent_job_id
    parent_manifest = read_json(parent_dir / "manifest.json", {}) or {}
    parent_request = read_json(parent_dir / "request.json", {}) or {}
    parent_status = read_json(parent_dir / "status.json", {}) or {}

    if parent_status.get("status") != "completed":
        raise RuntimeError(f"생성 작업이 완료 상태가 아닙니다: {parent_job_id}")

    video_info = find_primary_video_output(
        list(parent_manifest.get("outputs") or parent_status.get("outputs") or [])
    )
    if video_info is None:
        raise RuntimeError(f"생성 영상 출력 정보를 찾지 못했습니다: {parent_job_id}")

    job_id = _contact_sheet_job_id(parent_job_id)
    job_dir = JOBS_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    snapshot = job_dir / "selected_workflow_api.json"
    if not snapshot.exists():
        snapshot.write_bytes(template_path.read_bytes())

    source_path = comfy_video_path(video_info)
    filename_prefix = (
        f"review/batches/{batch_id}/{parent_job_id}/contact_sheet"
    )
    created_at = now_iso()

    request = {
        "schema_version": 2,
        "job_type": "check",
        "check_type": "contact_sheet",
        "pipeline_stage": "contact_sheet",
        "job_id": job_id,
        "batch_id": batch_id,
        "parent_job_id": parent_job_id,
        "root_job_id": parent_request.get("root_job_id") or parent_job_id,
        "job_dir": str(job_dir),
        "created_at": created_at,
        "template_path": str(snapshot),
        "workflow_source_path": str(template_path),
        "workflow_filename": template_path.name,
        "workflow_kind": "check",
        "workflow_kind_label": "검수 (CH)",
        "comfy_url": parent_request.get(
            "comfy_url",
            os.environ.get("COMFY_URL", "http://127.0.0.1:8188"),
        ),
        "comfy_public_url": parent_request.get(
            "comfy_public_url",
            os.environ.get("COMFY_PUBLIC_URL", ""),
        ),
        "comfy_start_script": parent_request.get(
            "comfy_start_script",
            str(HOME / "bin/ai-start-comfy"),
        ),
        "comfy_start_timeout": parent_request.get(
            "comfy_start_timeout",
            DEFAULT_COMFY_START_TIMEOUT,
        ),
        "auto_start_comfy": True,
        "source_video": video_info,
        "source_video_path": source_path,
        "filename_prefix": filename_prefix,
        "automation": dict(batch.get("automation") or {}),
        "attempt": 0,
    }
    manifest = {
        "schema_version": 2,
        "job_id": job_id,
        "batch_id": batch_id,
        "parent_job_id": parent_job_id,
        "job_type": "check",
        "check_type": "contact_sheet",
        "pipeline_stage": "contact_sheet",
        "created_at": created_at,
        "status": "queued",
        "workflow_source_path": str(template_path),
        "workflow_filename": template_path.name,
        "workflow_kind": "check",
        "workflow_kind_label": "검수 (CH)",
        "source_video": video_info,
        "source_video_path": source_path,
        "outputs": [],
    }

    atomic_write_json(job_dir / "request.json", request)
    atomic_write_json(job_dir / "manifest.json", manifest)
    update_status(
        job_dir,
        "queued",
        stage="Contact Sheet worker 대기",
        message=f"원본 생성 작업: {parent_job_id}",
        progress=0.0,
        created_at=created_at,
    )
    attach_job_to_batch(
        ENGINE_ROOT,
        batch_id=batch_id,
        job_id=job_id,
        job_type="check",
    )
    return job_id


def prepare_contact_sheet_batch(
    batch: dict[str, Any],
) -> dict[str, Any]:
    batch_id = str(batch["batch_id"])

    if str(batch.get("pipeline_version") or "") != "1.7.0":
        return batch

    if not bool((batch.get("automation") or {}).get("auto_review", True)):
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            status="completed_generation_only",
            stage="completed",
            next_stage="completed",
            message="AI 검수가 비활성화되어 생성 배치만 완료했습니다.",
        )

    template_path = DEFAULT_REVIEW_TEMPLATE
    if not template_path.is_file():
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            status="contact_sheet_preparation_failed",
            stage="contact_sheet_template_missing",
            next_stage="stopped",
            message=f"Contact Sheet API를 찾을 수 없습니다: {template_path}",
        )

    completed_generation_ids: list[str] = []
    failed_generation_ids: list[str] = []
    for job_id in batch.get("generation_job_ids") or []:
        status = read_json(JOBS_ROOT / job_id / "status.json", {}) or {}
        if status.get("status") == "completed":
            completed_generation_ids.append(job_id)
        else:
            failed_generation_ids.append(job_id)

    if not completed_generation_ids:
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            status="generation_failed",
            stage="generation_failed",
            next_stage="stopped",
            message="완료된 생성 영상이 없어 Contact Sheet를 만들 수 없습니다.",
        )

    check_ids: list[str] = []
    preparation_errors: list[dict[str, str]] = []
    for parent_job_id in completed_generation_ids:
        try:
            check_ids.append(
                _create_contact_sheet_job(
                    batch=batch,
                    parent_job_id=parent_job_id,
                    template_path=template_path,
                )
            )
        except Exception as exc:
            preparation_errors.append(
                {
                    "parent_job_id": parent_job_id,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    if preparation_errors:
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            status="contact_sheet_preparation_failed",
            stage="contact_sheet_preparation_failed",
            next_stage="stopped",
            contact_sheet_preparation_errors=preparation_errors,
            failed_generation_job_ids=failed_generation_ids,
            message=(
                f"Contact Sheet 작업 준비 실패 {len(preparation_errors)}건 · "
                "배치 기록의 오류 내용을 확인하세요."
            ),
        )

    batch = update_batch(
        ENGINE_ROOT,
        batch_id,
        status="contact_sheet_queued",
        stage="contact_sheet_generation",
        next_stage="contact_sheet",
        check_job_ids=check_ids,
        failed_generation_job_ids=failed_generation_ids,
        contact_sheet_jobs_created_at=now_iso(),
        message=(
            f"Contact Sheet 작업 {len(check_ids)}건을 자동 등록했습니다."
            + (
                f" 생성 실패 {len(failed_generation_ids)}건은 제외했습니다."
                if failed_generation_ids
                else ""
            )
        ),
    )
    log_event(
        "contact_sheet_jobs_created",
        batch_id=batch_id,
        check_job_ids=check_ids,
    )
    return batch


def monitor_contact_sheet_batch(
    batch: dict[str, Any],
) -> dict[str, Any]:
    batch_id = str(batch["batch_id"])
    check_ids = list(batch.get("check_job_ids") or [])
    if not check_ids:
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            status="contact_sheet_preparation_failed",
            stage="contact_sheet_jobs_missing",
            next_stage="stopped",
            message="Contact Sheet 작업 ID가 없습니다.",
        )

    statuses: dict[str, str] = {}
    for job_id in check_ids:
        payload = read_json(JOBS_ROOT / job_id / "status.json", {}) or {}
        statuses[job_id] = str(payload.get("status") or "unknown")

    completed_count = sum(value == "completed" for value in statuses.values())
    failed_ids = [
        job_id
        for job_id, value in statuses.items()
        if value in {"failed", "cancelled"}
    ]

    if failed_ids:
        batch = update_batch(
            ENGINE_ROOT,
            batch_id,
            status="contact_sheet_failed",
            stage="contact_sheet_failed",
            next_stage="stopped",
            failed_check_job_ids=failed_ids,
            message=f"Contact Sheet 생성 실패 {len(failed_ids)}건",
        )
        log_event(
            "contact_sheet_batch_failed",
            batch_id=batch_id,
            failed_check_job_ids=failed_ids,
        )
        return batch

    if batch_typed_jobs_are_terminal(
        JOBS_ROOT,
        batch,
        "check_job_ids",
    ):
        batch = update_batch(
            ENGINE_ROOT,
            batch_id,
            status="ready_for_ai_review",
            stage="contact_sheet_complete",
            next_stage="vllm_review",
            contact_sheet_completed_at=now_iso(),
            message=(
                f"Contact Sheet {completed_count}/{len(check_ids)}건 완료 · "
                "다음 단계는 vLLM 검수입니다."
            ),
        )
        log_event(
            "contact_sheet_batch_complete",
            batch_id=batch_id,
            check_job_ids=check_ids,
            next_stage="vllm_review",
        )
        return batch

    return update_batch(
        ENGINE_ROOT,
        batch_id,
        status="contact_sheet_queued",
        stage="contact_sheet_generation",
        next_stage="contact_sheet",
        message=f"Contact Sheet 생성 진행 {completed_count}/{len(check_ids)}",
    )



def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _localize_generation_video(
    parent_job_id: str,
) -> tuple[Path, dict[str, Any]]:
    """ComfyUI가 실행 중일 때 원본 생성 영상을 review 공유 경로로 복사합니다."""
    parent_dir = JOBS_ROOT / parent_job_id
    request = read_json(parent_dir / "request.json", {}) or {}
    manifest = read_json(parent_dir / "manifest.json", {}) or {}
    status = read_json(parent_dir / "status.json", {}) or {}

    existing = manifest.get("review_video_local_path")
    if existing:
        existing_path = Path(str(existing))
        if existing_path.is_file() and existing_path.stat().st_size > 0:
            return existing_path, {
                "filename": existing_path.name,
                "size_bytes": existing_path.stat().st_size,
                "sha256": manifest.get("review_video_sha256")
                or _sha256_file(existing_path),
                "reused": True,
            }

    video_info = find_primary_video_output(
        list(manifest.get("outputs") or status.get("outputs") or [])
    )
    if video_info is None:
        raise RuntimeError(
            f"생성 영상 출력 정보를 찾지 못했습니다: {parent_job_id}"
        )

    suffix = Path(str(video_info.get("filename") or "")).suffix.lower()
    if not suffix:
        suffix = ".mp4"

    artifacts = parent_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    target = artifacts / f"review_source_video{suffix}"

    comfy_url = str(
        request.get("comfy_url")
        or os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
    )
    client = ComfyClient(comfy_url)
    written = client.download_file_to_path(video_info, str(target))
    checksum = _sha256_file(target)

    manifest.update(
        {
            "review_video_local_path": str(target),
            "review_video_source": video_info,
            "review_video_size_bytes": written,
            "review_video_sha256": checksum,
            "review_video_localized_at": now_iso(),
            "updated_at": now_iso(),
        }
    )
    atomic_write_json(parent_dir / "manifest.json", manifest)

    log_event(
        "review_video_localized",
        job_id=parent_job_id,
        local_path=str(target),
        size_bytes=written,
        sha256=checksum,
    )
    return target, {
        "filename": target.name,
        "size_bytes": written,
        "sha256": checksum,
        "reused": False,
    }


def _active_review_job_ids(batch: dict[str, Any]) -> list[str]:
    review_ids = [str(value) for value in batch.get("review_job_ids") or []]
    if review_ids:
        return review_ids
    return [
        str(value) for value in batch.get("generation_job_ids") or []
    ]


def prepare_direct_video_review_batch(
    batch: dict[str, Any],
) -> dict[str, Any]:
    batch_id = str(batch["batch_id"])

    if str(batch.get("pipeline_version") or "") != DIRECT_VIDEO_PIPELINE_VERSION:
        return batch

    if (
        not bool((batch.get("automation") or {}).get("auto_review", True))
        and str(batch.get("batch_mode") or "") != "final_review"
    ):
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            status="completed_generation_only",
            stage="completed",
            next_stage="completed",
            message="AI 검수가 비활성화되어 생성 배치만 완료했습니다.",
        )

    completed_ids: list[str] = []
    failed_review_ids: list[str] = []
    review_job_ids = _active_review_job_ids(batch)
    for job_id in review_job_ids:
        status = read_json(JOBS_ROOT / job_id / "status.json", {}) or {}
        if status.get("status") == "completed":
            completed_ids.append(job_id)
        else:
            failed_review_ids.append(job_id)

    if not completed_ids:
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            status="review_input_failed",
            stage="review_input_failed",
            next_stage="stopped",
            message="완료된 검수 대상 영상이 없어 직접 영상 검수를 준비할 수 없습니다.",
        )

    batch = update_batch(
        ENGINE_ROOT,
        batch_id,
        status="preparing_video_review",
        stage="localizing_review_videos",
        next_stage="video_review",
        message=(
            f"검수 대상 영상 {len(completed_ids)}건을 "
            "Qwen3-Omni 공유 경로로 복사합니다."
        ),
    )

    localized: dict[str, str] = {}
    metadata: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []

    for parent_job_id in completed_ids:
        try:
            path, info = _localize_generation_video(parent_job_id)
            localized[parent_job_id] = str(path)
            metadata[parent_job_id] = info
        except Exception as exc:
            errors.append(
                {
                    "job_id": parent_job_id,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    if errors:
        batch = update_batch(
            ENGINE_ROOT,
            batch_id,
            status="video_review_preparation_failed",
            stage="video_localization_failed",
            next_stage="stopped",
            video_review_preparation_errors=errors,
            review_video_paths=localized,
            message=(
                f"원본 영상 로컬 복사 실패 {len(errors)}건 · "
                "ComfyUI는 종료하지 않았습니다."
            ),
        )
        log_event(
            "review_video_preparation_failed",
            batch_id=batch_id,
            errors=errors,
        )
        return batch

    batch = update_batch(
        ENGINE_ROOT,
        batch_id,
        status="ready_for_ai_review",
        stage="direct_video_ready",
        next_stage="vllm_review",
        review_mode="direct_video_two_pass",
        review_video_paths=localized,
        review_video_metadata=metadata,
        review_job_ids=completed_ids,
        failed_review_job_ids=failed_review_ids,
        video_review_prepared_at=now_iso(),
        message=(
            f"검수 대상 영상 {len(localized)}건 로컬 복사 완료 · "
            "다음 단계는 Qwen3-Omni 직접 영상 검수입니다."
        ),
    )
    log_event(
        "review_videos_ready",
        batch_id=batch_id,
        review_video_paths=localized,
        next_stage="vllm_review",
    )
    return batch


def _review_video_for_parent(
    batch: dict[str, Any],
    parent_job_id: str,
) -> Path:
    value = (batch.get("review_video_paths") or {}).get(parent_job_id)
    if value:
        path = Path(str(value))
        if path.is_file():
            return path

    manifest = read_json(
        JOBS_ROOT / parent_job_id / "manifest.json",
        {},
    ) or {}
    value = manifest.get("review_video_local_path")
    if value:
        path = Path(str(value))
        if path.is_file():
            return path

    raise FileNotFoundError(
        f"직접 검수할 로컬 원본 영상을 찾지 못했습니다: {parent_job_id}"
    )


def _retake_correction_text(
    report: dict[str, Any],
    *,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
) -> str:
    return correction_policy.correction_text(
        report,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )


def _select_retake_window(
    report: dict[str, Any],
) -> tuple[float, float, float, dict[str, Any]]:
    return correction_policy.select_retake_window(report)


def _next_lineage_modify_cycle(root_job_id: str, requested_cycle: int) -> int:
    highest = 0
    for job_dir in JOBS_ROOT.glob(f"{root_job_id}__*"):
        request = read_json(job_dir / "request.json", {}) or {}
        if str(request.get("root_job_id") or "") != root_job_id:
            continue
        highest = max(highest, int(request.get("modify_cycle") or 0))
    return max(int(requested_cycle), highest + 1)

def _create_retake_job(
    *,
    batch: dict[str, Any],
    parent_job_id: str,
    report: dict[str, Any],
    cycle: int,
) -> str:
    parent_dir = JOBS_ROOT / parent_job_id
    parent_request = read_json(parent_dir / "request.json", {}) or {}
    if not parent_request:
        raise FileNotFoundError(
            f"Retake 원본 요청을 찾지 못했습니다: {parent_job_id}"
        )

    root_job_id = str(parent_request.get("root_job_id") or parent_job_id)
    root_dir = JOBS_ROOT / root_job_id
    root_request = read_json(root_dir / "request.json", {}) or parent_request
    effective_cycle = _next_lineage_modify_cycle(root_job_id, cycle)
    correction_mode = correction_policy.recommend_correction_mode(report)

    retake_start: float | None = None
    retake_end: float | None = None
    retake_strength: float | None = None
    primary_issue: dict[str, Any] = {}
    source_video_path: Path | None = None

    if correction_mode == "partial_retake":
        retake_start, retake_end, retake_strength, primary_issue = (
            _select_retake_window(report)
        )
        correction_text = correction_policy.build_retake_prompt(
            report,
            root_request,
            start_seconds=retake_start,
            end_seconds=retake_end,
            correction_mode=correction_mode,
        )
        # Auto-retakes are preservation edits, not fresh generations. A full
        # strength rewrite and a new seed were causing visual regressions.
        retake_strength = min(retake_strength, 0.70)
        parent_manifest = read_json(parent_dir / "manifest.json", {}) or {}
        source_video_path = Path(
            str(parent_manifest.get("review_video_local_path") or "")
        )
        if not source_video_path.is_file():
            raise FileNotFoundError(
                f"부분 Retake 원본 영상을 찾지 못했습니다: {parent_job_id}"
            )
        template_path = (
            DEFAULT_WORKFLOW_DIR / "(MD)LTX_Retake_Partial_API.json"
        ).expanduser()
        pipeline_stage = "retake_generation"
        workflow_kind_label = "자동 Retake (부분 구간 수정)"
        job_token = "retake"
    else:
        correction_text = correction_policy.build_retake_prompt(
            report,
            root_request,
            start_seconds=0.0,
            end_seconds=float(report.get("duration_seconds") or 0.0),
            correction_mode=correction_mode,
        )
        template_path = Path(
            str(
                root_request.get("workflow_source_path")
                or root_request.get("template_path")
                or ""
            )
        ).expanduser()
        if not template_path.is_file():
            template_path = Path(str(root_request.get("template_path") or "")).expanduser()
        pipeline_stage = "full_regeneration"
        workflow_kind_label = "자동 Retake (전체 재생성)"
        job_token = "regenerate"

    if not correction_text:
        raise ValueError(f"Retake 수정 프롬프트가 없습니다: {parent_job_id}")
    if not template_path.is_file():
        raise FileNotFoundError(f"수정용 API 템플릿을 찾지 못했습니다: {template_path}")

    source_segments = list(root_request.get("segments") or [])
    if not source_segments:
        raise ValueError(f"Retake 원본 이미지 구간이 없습니다: {root_job_id}")

    job_id = f"{root_job_id}__{job_token}_c{effective_cycle}"
    job_dir = JOBS_ROOT / job_id
    if job_dir.exists():
        raise FileExistsError(f"수정 작업 ID가 이미 존재합니다: {job_id}")
    job_dir.mkdir(parents=True, exist_ok=False)
    workflow_snapshot = job_dir / "selected_workflow_api.json"
    workflow_snapshot.write_bytes(template_path.read_bytes())

    correction_block = (
        "MANDATORY RETAKE CORRECTIONS FROM QUALITY CONTROL:\n"
        + correction_text
    )
    segments: list[dict[str, Any]] = []
    for source in source_segments:
        segment = dict(source)
        base_prompt = str(segment.get("prompt") or "").strip()
        segment["prompt"] = (
            f"{base_prompt}\n\n{correction_block}"
            if base_prompt
            else correction_block
        )
        segments.append(segment)

    original_global_prompt = str(root_request.get("global_prompt") or "").strip()
    global_prompt = (
        f"{original_global_prompt}\n\n{correction_block}"
        if original_global_prompt
        else correction_block
    )
    if correction_mode == "partial_retake":
        # Keep the source lineage stochastic state stable for a localized edit.
        seed = int(parent_request.get("seed") or root_request.get("seed") or 0)
    else:
        seed = int.from_bytes(os.urandom(8), "big") & ((1 << 63) - 1)
    created_at = now_iso()
    batch_id = str(batch["batch_id"])
    filename_prefix = (
        f"video/retakes/{root_job_id}/cycle_{effective_cycle}"
        if correction_mode == "partial_retake"
        else f"video/regenerations/{root_job_id}/cycle_{effective_cycle}"
    )

    request = {
        "schema_version": 2,
        "job_type": "modify",
        "pipeline_stage": pipeline_stage,
        "correction_mode": correction_mode,
        "job_id": job_id,
        "batch_id": batch_id,
        "job_dir": str(job_dir),
        "created_at": created_at,
        "job_name": (
            f"{root_request.get('job_name') or root_job_id} "
            f"{job_token} {effective_cycle}"
        ),
        "template_path": str(workflow_snapshot),
        "workflow_source_path": str(template_path),
        "workflow_filename": template_path.name,
        "workflow_kind": "modify",
        "workflow_kind_label": workflow_kind_label,
        "comfy_url": root_request.get(
            "comfy_url",
            os.environ.get("COMFY_URL", "http://127.0.0.1:8188"),
        ),
        "comfy_public_url": root_request.get("comfy_public_url", ""),
        "comfy_start_script": root_request.get(
            "comfy_start_script",
            str(HOME / "bin/ai-start-comfy"),
        ),
        "comfy_start_timeout": root_request.get(
            "comfy_start_timeout",
            DEFAULT_COMFY_START_TIMEOUT,
        ),
        "auto_start_comfy": True,
        "fps": int(root_request["fps"]),
        "seed": seed,
        "resolution": dict(root_request["resolution"]),
        "global_prompt": global_prompt,
        "duration_mode": root_request.get("duration_mode"),
        "target_total_seconds": root_request.get("target_total_seconds"),
        "filename_prefix": filename_prefix,
        "segments": segments,
        "parent_job_id": parent_job_id,
        "root_job_id": root_job_id,
        "modify_cycle": effective_cycle,
        "attempt": effective_cycle,
        "automation": dict(batch.get("automation") or {}),
        "retake_corrections": correction_text,
        "generated_retake_prompt": correction_text,
        "retake_prompt_source": "ai_review_report",
        "retake_policy": "conservative_preservation",
        "source_review_report": str(parent_dir / "ai_review_report.json"),
    }
    if correction_mode == "partial_retake":
        request.update(
            {
                "retake_source_video_path": str(source_video_path),
                "retake_source_duration_seconds": float(
                    report.get("duration_seconds") or 0.0
                ),
                "retake_start_seconds": retake_start,
                "retake_end_seconds": retake_end,
                "retake_strength": retake_strength,
                "retake_primary_issue": primary_issue,
            }
        )

    manifest = {
        "schema_version": 2,
        "job_id": job_id,
        "batch_id": batch_id,
        "parent_job_id": parent_job_id,
        "root_job_id": root_job_id,
        "job_type": "modify",
        "pipeline_stage": pipeline_stage,
        "correction_mode": correction_mode,
        "modify_cycle": effective_cycle,
        "created_at": created_at,
        "status": "queued",
        "workflow_source_path": str(template_path),
        "workflow_filename": template_path.name,
        "workflow_kind": "modify",
        "workflow_kind_label": workflow_kind_label,
        "seed": seed,
        "resolution": request["resolution"],
        "fps": request["fps"],
        "segments": segments,
        "retake_corrections": correction_text,
        "generated_retake_prompt": correction_text,
        "retake_prompt_source": "ai_review_report",
        "retake_policy": "conservative_preservation",
        "source_review_report": request["source_review_report"],
        "outputs": [],
    }
    for key in (
        "retake_source_video_path",
        "retake_source_duration_seconds",
        "retake_start_seconds",
        "retake_end_seconds",
        "retake_strength",
        "retake_primary_issue",
    ):
        if key in request:
            manifest[key] = request[key]

    atomic_write_json(job_dir / "request.json", request)
    atomic_write_json(job_dir / "manifest.json", manifest)
    update_status(
        job_dir,
        "queued",
        stage="Retake worker 대기",
        message=(
            f"원본 검수 작업: {parent_job_id} · cycle {effective_cycle} · "
            f"{workflow_kind_label}"
        ),
        progress=0.0,
        created_at=created_at,
    )
    attach_job_to_batch(
        ENGINE_ROOT,
        batch_id=batch_id,
        job_id=job_id,
        job_type="modify",
    )
    log_event(
        "retake_job_created",
        batch_id=batch_id,
        job_id=job_id,
        parent_job_id=parent_job_id,
        root_job_id=root_job_id,
        cycle=effective_cycle,
        correction_mode=correction_mode,
    )
    return job_id

def _contact_sheet_for_parent(
    batch: dict[str, Any],
    parent_job_id: str,
) -> tuple[str, Path]:
    for check_id in batch.get("check_job_ids") or []:
        request = read_json(JOBS_ROOT / check_id / "request.json", {}) or {}
        if request.get("parent_job_id") != parent_job_id:
            continue
        manifest = read_json(JOBS_ROOT / check_id / "manifest.json", {}) or {}
        local_value = manifest.get("contact_sheet_local_path")
        if local_value:
            path = Path(str(local_value))
            if path.is_file():
                return check_id, path
        for item in manifest.get("outputs") or []:
            local_value = item.get("local_path")
            if local_value and Path(str(local_value)).is_file():
                return check_id, Path(str(local_value))
    raise FileNotFoundError(
        f"생성 작업의 로컬 Contact Sheet를 찾지 못했습니다: {parent_job_id}"
    )


def restore_comfy_after_review(
    batch: dict[str, Any],
    *,
    outcome: str,
) -> dict[str, Any]:
    """검수 종료 후 vLLM을 내리고 다음 생성을 위해 ComfyUI를 복귀시킵니다."""
    batch_id = str(batch["batch_id"])

    if not AUTO_RESTORE_COMFY_AFTER_REVIEW:
        batch = update_batch(
            ENGINE_ROOT,
            batch_id,
            post_review_engine_return="disabled",
            post_review_target_engine="none",
            engine_snapshot_after_review=engine_snapshot(),
        )
        log_event(
            "post_review_engine_return_skipped",
            batch_id=batch_id,
            outcome=outcome,
        )
        return batch

    base_message = str(batch.get("message") or "").strip()
    log_event(
        "post_review_engine_return_started",
        batch_id=batch_id,
        outcome=outcome,
        target_engine="comfy",
    )
    write_worker_status(
        "busy",
        current_job=None,
        current_batch=batch_id,
        stage="AI 검수 완료 · ComfyUI 복귀",
    )

    batch = update_batch(
        ENGINE_ROOT,
        batch_id,
        post_review_engine_return="switching",
        post_review_target_engine="comfy",
        engine_snapshot_before_return=engine_snapshot(),
        message=(
            f"{base_message} · vLLM을 종료하고 ComfyUI를 다시 시작합니다."
            if base_message
            else "vLLM을 종료하고 ComfyUI를 다시 시작합니다."
        ),
    )

    try:
        ensure_comfy_engine()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        batch = update_batch(
            ENGINE_ROOT,
            batch_id,
            post_review_engine_return="failed",
            post_review_target_engine="comfy",
            post_review_engine_error=error,
            engine_snapshot_after_review=engine_snapshot(),
            message=(
                f"{base_message} · AI 검수 결과는 저장했지만 "
                f"ComfyUI 자동 복귀에 실패했습니다: {error}"
            ),
        )
        log_event(
            "post_review_engine_return_failed",
            batch_id=batch_id,
            outcome=outcome,
            error=error,
            engine_snapshot=engine_snapshot(),
        )
        return batch

    restored_at = now_iso()
    batch = update_batch(
        ENGINE_ROOT,
        batch_id,
        post_review_engine_return="completed",
        post_review_target_engine="comfy",
        post_review_engine="comfy",
        comfy_restored_at=restored_at,
        engine_snapshot_after_review=engine_snapshot(),
        message=(
            f"{base_message} · ComfyUI 재실행 완료"
            if base_message
            else "ComfyUI 재실행 완료"
        ),
    )
    log_event(
        "post_review_engine_return_complete",
        batch_id=batch_id,
        outcome=outcome,
        restored_at=restored_at,
        engine_snapshot=engine_snapshot(),
    )
    return batch


def _sync_final_review_entities(batch: dict[str, Any], entity_status: str) -> None:
    if str(batch.get("batch_mode") or "") != "final_review":
        return
    stamp = now_iso()
    error_message = str(batch.get("message") or "")
    for candidate_set_id in batch.get("candidate_set_ids") or []:
        path = (
            ENGINE_ROOT
            / "runtime"
            / "candidate_sets"
            / str(candidate_set_id)
            / "candidate_set.json"
        )
        payload = read_json(path, {}) or {}
        if not payload:
            continue
        payload.update(status=entity_status, updated_at=stamp)
        if entity_status == "completed":
            payload["completed_at"] = stamp
        elif entity_status == "final_review_failed":
            payload["last_error"] = error_message or "최종 AI 검수 실패"
        atomic_write_json(path, payload)
    for composition_id in batch.get("composition_ids") or []:
        path = (
            ENGINE_ROOT
            / "runtime"
            / "compositions"
            / str(composition_id)
            / "composition.json"
        )
        payload = read_json(path, {}) or {}
        if not payload:
            continue
        payload.update(status=entity_status, updated_at=stamp)
        if entity_status == "completed":
            payload["completed_at"] = stamp
        elif entity_status == "final_review_failed":
            payload["last_error"] = error_message or "최종 AI 검수 실패"
        atomic_write_json(path, payload)


def _entity_status_for_review_batch(batch_status: str) -> str | None:
    if batch_status == "review_completed":
        return "completed"
    if batch_status in {
        "review_complete_needs_modification",
        "manual_review_required",
        "modification_limit_reached",
        "ai_review_failed",
        "engine_switch_failed",
    }:
        return "final_review_failed"
    return None


def run_ai_review_batch(batch: dict[str, Any]) -> dict[str, Any]:
    batch_id = str(batch["batch_id"])
    current_cycle = int(batch.get("current_cycle") or 0)
    pipeline_version = str(batch.get("pipeline_version") or "")
    if pipeline_version not in {
        DIRECT_VIDEO_PIPELINE_VERSION,
        LEGACY_CONTACT_SHEET_PIPELINE_VERSION,
    }:
        return batch
    direct_video_mode = pipeline_version == DIRECT_VIDEO_PIPELINE_VERSION

    batch = update_batch(
        ENGINE_ROOT,
        batch_id,
        status="switching_to_vllm",
        stage="engine_switch_to_vllm",
        next_stage="vllm_review",
        ai_review_errors=[],
        engine_switch_error=None,
        message="ComfyUI를 종료하고 vLLM을 시작합니다.",
    )
    log_event(
        "engine_switch_started",
        batch_id=batch_id,
        target_engine="vllm",
    )

    try:
        ensure_vllm_engine()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        batch = update_batch(
            ENGINE_ROOT,
            batch_id,
            status="engine_switch_failed",
            stage="engine_switch_failed",
            next_stage="stopped",
            engine_switch_error=error,
            engine_snapshot=engine_snapshot(),
            message=f"vLLM 엔진 전환 실패 · {error}",
        )
        log_event(
            "engine_switch_failed",
            batch_id=batch_id,
            error=error,
        )
        _sync_final_review_entities(batch, "final_review_failed")
        return restore_comfy_after_review(
            batch,
            outcome="engine_switch_failed",
        )

    batch = update_batch(
        ENGINE_ROOT,
        batch_id,
        status="ai_reviewing",
        stage="vllm_review",
        next_stage="vllm_review",
        engine_snapshot=engine_snapshot(),
        message=(
            "Qwen3-Omni가 원본 영상 전체와 생성 프롬프트를 검수하고 있습니다."
            if direct_video_mode
            else "vLLM이 Contact Sheet와 생성 프롬프트를 검수하고 있습니다."
        ),
    )
    log_event(
        "vllm_review_started",
        batch_id=batch_id,
        review_job_ids=_active_review_job_ids(batch),
        cycle=current_cycle,
    )

    reports: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for parent_job_id in _active_review_job_ids(batch):
        parent_dir = JOBS_ROOT / parent_job_id
        parent_status = read_json(parent_dir / "status.json", {}) or {}
        if parent_status.get("status") != "completed":
            continue

        try:
            request = read_json(parent_dir / "request.json", {}) or {}
            manifest = read_json(parent_dir / "manifest.json", {}) or {}
            generation_summary = manifest.get("workflow_summary") or {}

            if direct_video_mode:
                video_path = _review_video_for_parent(
                    batch,
                    parent_job_id,
                )
                report = review_video(
                    video_path=video_path,
                    original_request=request,
                    generation_summary=generation_summary,
                    batch_id=batch_id,
                    job_id=parent_job_id,
                )
                report["reviewed_at"] = now_iso()
            else:
                raise RuntimeError(
                    "이 v1.8 worker는 새 배치의 직접 영상 검수만 지원합니다. "
                    "남아 있는 v1.7 Contact Sheet 배치는 기존 백업 worker로 처리하세요."
                )

            atomic_write_json(parent_dir / "ai_review_report.json", report)

            manifest["ai_review"] = report
            manifest["ai_review_report_path"] = str(
                parent_dir / "ai_review_report.json"
            )
            manifest["updated_at"] = now_iso()
            atomic_write_json(parent_dir / "manifest.json", manifest)
            reports.append(report)

            log_event(
                "vllm_review_job_complete",
                batch_id=batch_id,
                job_id=parent_job_id,
                accepted=report.get("accepted"),
                recommended_action=report.get("recommended_action"),
                issue_count=len(report.get("issues") or []),
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            errors.append(
                {
                    "job_id": parent_job_id,
                    "error": error,
                }
            )
            log_event(
                "vllm_review_job_failed",
                batch_id=batch_id,
                job_id=parent_job_id,
                error=error,
            )

    report_filename = (
        "ai_review_reports.json"
        if current_cycle == 0
        else f"ai_review_reports_cycle_{current_cycle}.json"
    )
    batch_report_path = (
        ENGINE_ROOT / "runtime" / "batches" / batch_id / report_filename
    )
    aggregate = {
        "batch_id": batch_id,
        "cycle": current_cycle,
        "pipeline_version": pipeline_version,
        "review_mode": (
            "direct_video_two_pass"
            if direct_video_mode
            else "legacy_contact_sheet"
        ),
        "reviewed_at": now_iso(),
        "reports": reports,
        "errors": errors,
    }
    atomic_write_json(batch_report_path, aggregate)

    if errors:
        batch = update_batch(
            ENGINE_ROOT,
            batch_id,
            status="ai_review_failed",
            stage="vllm_review_failed",
            next_stage="stopped",
            ai_review_report_path=str(batch_report_path),
            ai_review_errors=errors,
            message=f"AI 검수 실패 {len(errors)}건 · 로그와 보고서를 확인하세요.",
        )
        log_event(
            "vllm_review_batch_failed",
            batch_id=batch_id,
            errors=errors,
        )
        _sync_final_review_entities(batch, "final_review_failed")
        return restore_comfy_after_review(
            batch,
            outcome="ai_review_failed",
        )

    rejected = [
        report
        for report in reports
        if not bool(report.get("accepted"))
    ]
    automation = batch.get("automation") or {}
    auto_modify = bool(automation.get("auto_modify", False))
    max_modify_cycles = int(automation.get("max_modify_cycles", 1))
    report_paths = list(batch.get("ai_review_report_paths") or [])
    if str(batch_report_path) not in report_paths:
        report_paths.append(str(batch_report_path))

    retake_job_ids: list[str] = []
    retake_errors: list[dict[str, str]] = []
    result_cycle = current_cycle

    if not rejected:
        status = "review_completed"
        stage = "ai_review_complete"
        next_stage = "completed"
        message = f"AI 검수 {len(reports)}건 완료 · 모두 통과했습니다."
    elif not auto_modify:
        status = "review_complete_needs_modification"
        stage = "ai_review_complete"
        next_stage = "review_report"
        message = (
            f"AI 검수 {len(reports)}건 완료 · 수정 필요 {len(rejected)}건 · "
            "자동 수정은 비활성화되어 보고서만 저장했습니다."
        )
    elif current_cycle >= max_modify_cycles:
        status = "modification_limit_reached"
        stage = "ai_review_complete"
        next_stage = "review_report"
        message = (
            f"AI 검수 {len(reports)}건 완료 · 수정 필요 {len(rejected)}건 · "
            f"최대 자동 수정 {max_modify_cycles}회에 도달했습니다."
        )
    else:
        retake_candidates = [
            report
            for report in rejected
            if str(report.get("recommended_action") or "") == "retake"
        ]
        if not retake_candidates:
            status = "manual_review_required"
            stage = "ai_review_complete"
            next_stage = "review_report"
            message = (
                f"AI 검수 {len(reports)}건 완료 · 자동 Retake 가능한 판정이 없어 "
                "수동 검수가 필요합니다."
            )
        else:
            result_cycle = current_cycle + 1
            for report in retake_candidates:
                parent_job_id = str(report.get("job_id") or "")
                try:
                    retake_job_ids.append(
                        _create_retake_job(
                            batch=batch,
                            parent_job_id=parent_job_id,
                            report=report,
                            cycle=result_cycle,
                        )
                    )
                except Exception as exc:
                    retake_errors.append(
                        {
                            "job_id": parent_job_id,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )

            if retake_errors:
                for job_id in retake_job_ids:
                    job_dir = JOBS_ROOT / job_id
                    update_status(
                        job_dir,
                        "cancelled",
                        stage="Retake 배치 준비 실패로 취소",
                        message="같은 cycle의 다른 Retake 작업 준비가 실패했습니다.",
                    )
                    manifest = read_json(job_dir / "manifest.json", {}) or {}
                    manifest.update(
                        {
                            "status": "cancelled",
                            "cancelled_at": now_iso(),
                            "updated_at": now_iso(),
                        }
                    )
                    atomic_write_json(job_dir / "manifest.json", manifest)

                status = "modification_preparation_failed"
                stage = "retake_preparation_failed"
                next_stage = "stopped"
                message = (
                    f"Retake 작업 준비 실패 {len(retake_errors)}건 · "
                    "같은 cycle의 준비된 작업도 취소했습니다."
                )
            else:
                status = "retake_queued"
                stage = "retake_generation"
                next_stage = "retake_generation"
                message = (
                    f"AI 검수 {len(reports)}건 완료 · Retake "
                    f"{len(retake_job_ids)}건을 cycle {result_cycle}로 등록했습니다."
                )

    batch = update_batch(
        ENGINE_ROOT,
        batch_id,
        status=status,
        stage=stage,
        next_stage=next_stage,
        current_cycle=result_cycle,
        review_job_ids=(
            retake_job_ids
            if retake_job_ids and not retake_errors
            else _active_review_job_ids(batch)
        ),
        retake_job_ids=retake_job_ids,
        retake_preparation_errors=retake_errors,
        ai_review_completed_at=now_iso(),
        ai_review_report_path=str(batch_report_path),
        ai_review_report_paths=report_paths,
        ai_review_total=len(reports),
        ai_review_rejected=len(rejected),
        message=message,
    )
    log_event(
        "vllm_review_batch_complete",
        batch_id=batch_id,
        status=status,
        next_stage=next_stage,
        cycle=result_cycle,
        review_total=len(reports),
        rejected=len(rejected),
        retake_job_ids=retake_job_ids,
    )
    entity_status = _entity_status_for_review_batch(status)
    if entity_status:
        _sync_final_review_entities(batch, entity_status)
    return restore_comfy_after_review(
        batch,
        outcome=status,
    )


def monitor_retake_batch(batch: dict[str, Any]) -> dict[str, Any]:
    batch_id = str(batch["batch_id"])
    review_job_ids = _active_review_job_ids(batch)
    if not review_job_ids:
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            status="retake_failed",
            stage="retake_jobs_missing",
            next_stage="stopped",
            message="Retake 작업 ID가 없습니다.",
        )

    statuses: dict[str, str] = {}
    for job_id in review_job_ids:
        payload = read_json(JOBS_ROOT / job_id / "status.json", {}) or {}
        statuses[job_id] = str(payload.get("status") or "unknown")

    failed_ids = [
        job_id
        for job_id, status in statuses.items()
        if status in {"failed", "cancelled"}
    ]
    if failed_ids:
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            status="retake_failed",
            stage="retake_generation_failed",
            next_stage="stopped",
            failed_modify_job_ids=failed_ids,
            message=f"Retake 생성 실패 {len(failed_ids)}건",
        )

    if not all(status == "completed" for status in statuses.values()):
        return batch

    auto_recheck = bool(
        (batch.get("automation") or {}).get("auto_recheck", True)
    )
    if auto_recheck:
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            status="ready_for_review_preparation",
            stage="retake_generation_complete",
            next_stage="video_review",
            message=(
                f"Retake cycle {batch.get('current_cycle') or 0} 생성 완료 · "
                "자동 재검수를 준비합니다."
            ),
        )

    return update_batch(
        ENGINE_ROOT,
        batch_id,
        status="modification_completed",
        stage="retake_generation_complete",
        next_stage="completed",
        message=(
            f"Retake cycle {batch.get('current_cycle') or 0} 생성 완료 · "
            "자동 재검수는 비활성화되어 있습니다."
        ),
    )


def advance_review_batches() -> dict[str, Any] | None:
    candidates = find_batches_by_status(
        ENGINE_ROOT,
        {
            "ready_for_review_preparation",
            "ready_for_ai_review",
            "retake_queued",
        },
        limit=1000,
    )
    candidates = [
        item
        for item in candidates
        if str(item.get("pipeline_version") or "")
        == DIRECT_VIDEO_PIPELINE_VERSION
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda item: str(item.get("created_at") or ""))
    batch = candidates[0]
    status = str(batch.get("status") or "")

    if status == "ready_for_review_preparation":
        return prepare_direct_video_review_batch(batch)
    if status == "ready_for_ai_review":
        return run_ai_review_batch(batch)
    if status == "retake_queued":
        return monitor_retake_batch(batch)
    return batch


def get_comfy_queue_state(
    comfy_url: str,
) -> tuple[bool, int, int, str | None]:
    try:
        payload = ComfyClient(comfy_url).get_queue()
    except Exception as exc:
        return False, 0, 0, f"{type(exc).__name__}: {exc}"

    running_count = len(payload.get("queue_running") or [])
    pending_count = len(payload.get("queue_pending") or [])
    return running_count == 0 and pending_count == 0, running_count, pending_count, None


def maybe_finalize_open_batch() -> dict[str, Any] | None:
    open_batches = find_batches_by_status(ENGINE_ROOT, {"open"}, limit=1000)
    open_batches.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("batch_id") or ""),
        )
    )
    if not open_batches:
        log_batch_state(None)
        return None

    batch = open_batches[0]
    batch_id = str(batch["batch_id"])
    log_batch_state(batch)

    if not batch_generation_is_terminal(JOBS_ROOT, batch):
        if (
            batch.get("idle_since_epoch") is not None
            or batch.get("stage") != "collecting_generation_jobs"
        ):
            batch = update_batch(
                ENGINE_ROOT,
                batch_id,
                idle_since_epoch=None,
                stage="collecting_generation_jobs",
                message="생성 작업 완료를 기다리고 있습니다.",
            )
            log_batch_state(batch)
        return batch

    comfy_url = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
    queue_empty, running_count, pending_count, queue_error = get_comfy_queue_state(
        comfy_url
    )

    if queue_error is not None:
        batch = update_batch(
            ENGINE_ROOT,
            batch_id,
            idle_since_epoch=None,
            stage="waiting_for_comfy_api",
            message=f"ComfyUI 큐 상태 확인 실패 · {queue_error}",
        )
        log_batch_state(batch)
        return batch

    if not queue_empty:
        batch = update_batch(
            ENGINE_ROOT,
            batch_id,
            idle_since_epoch=None,
            stage="waiting_for_comfy_queue",
            message=(
                f"ComfyUI 큐 종료 대기 · 실행 {running_count}건 · "
                f"대기 {pending_count}건"
            ),
        )
        log_batch_state(batch)
        return batch

    now_epoch = time.time()
    idle_since = batch.get("idle_since_epoch")
    grace = int(
        (batch.get("automation") or {}).get("batch_idle_grace_seconds", 10)
    )

    if idle_since is None:
        batch = update_batch(
            ENGINE_ROOT,
            batch_id,
            idle_since_epoch=now_epoch,
            stage="batch_idle_grace",
            message=(
                f"생성 큐가 모두 비었습니다. 새 작업 유입을 {grace}초 동안 기다립니다."
            ),
        )
        log_batch_state(batch)
        return batch

    remaining = grace - (now_epoch - float(idle_since))
    if remaining > 0:
        # 메시지는 갱신하되 로그는 stage 변경 때만 출력합니다.
        return update_batch(
            ENGINE_ROOT,
            batch_id,
            stage="batch_idle_grace",
            message=f"배치 종료 안정 대기 중 · 약 {remaining:.0f}초 남음",
        )

    batch = mark_batch_generation_complete(ENGINE_ROOT, batch)
    log_batch_state(batch)
    log_event(
        "batch_generation_complete",
        batch_id=batch_id,
        status=batch.get("status"),
        next_stage=batch.get("next_stage"),
    )
    return batch


def main() -> None:
    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)
    write_worker_status("idle", current_job=None, started_at=now_iso())
    log_event(
        "worker_started",
        pid=os.getpid(),
        engine_root=str(ENGINE_ROOT),
        jobs_root=str(JOBS_ROOT),
        poll_seconds=POLL_SECONDS,
    )

    while not STOP_REQUESTED:
        open_batch = maybe_finalize_open_batch()
        if (
            open_batch
            and open_batch.get("status") == "open"
            and batch_generation_is_terminal(JOBS_ROOT, open_batch)
        ):
            write_worker_status(
                "idle",
                current_job=None,
                current_batch=open_batch.get("batch_id"),
                batch_stage=open_batch.get("stage"),
                batch_status=open_batch.get("status"),
                batch_message=open_batch.get("message"),
                batch_next_stage=open_batch.get("next_stage"),
            )
            time.sleep(POLL_SECONDS)
            continue

        job_dir = claim_next_queued_job(JOBS_ROOT, os.getpid())
        if job_dir is None:
            pipeline_batch = advance_review_batches()
            open_batch = maybe_finalize_open_batch()
            batch = pipeline_batch or open_batch
            write_worker_status(
                "idle",
                current_job=None,
                stage=None,
                elapsed_seconds=None,
                current_batch=(batch or {}).get("batch_id"),
                batch_stage=(batch or {}).get("stage"),
                batch_status=(batch or {}).get("status"),
                batch_message=(batch or {}).get("message"),
                batch_next_stage=(batch or {}).get("next_stage"),
            )
            time.sleep(POLL_SECONDS)
            continue

        request = read_json(job_dir / "request.json", {}) or {}
        current_batch = request.get("batch_id")
        write_worker_status(
            "busy",
            current_job=job_dir.name,
            current_batch=current_batch,
        )
        log_event(
            "job_started",
            job_id=job_dir.name,
            batch_id=current_batch,
        )
        try:
            process_job(job_dir)
            log_event(
                "job_completed",
                job_id=job_dir.name,
                batch_id=current_batch,
            )
        except Exception as exc:
            failed_status = read_json(job_dir / "status.json", {}) or {}
            failure_stage = str(
                failed_status.get("stage") or "worker 작업 처리"
            )
            error_text = f"{type(exc).__name__}: {exc}"
            log_event(
                "job_failed",
                job_id=job_dir.name,
                batch_id=current_batch,
                error=error_text,
            )
            trace = traceback.format_exc()
            (job_dir / "error.log").write_text(trace, encoding="utf-8")
            manifest = read_json(job_dir / "manifest.json", {}) or {}
            manifest.update(
                {
                    "status": "failed",
                    "error": error_text,
                    "failure_stage": failure_stage,
                    "failed_at": now_iso(),
                    "updated_at": now_iso(),
                }
            )
            atomic_write_json(job_dir / "manifest.json", manifest)
            update_status(
                job_dir,
                "failed",
                stage="실패",
                message=error_text,
                error=error_text,
                failure_stage=failure_stage,
                progress=0.0,
                failed_at=now_iso(),
            )
            failed_request = read_json(job_dir / "request.json", {}) or {}
            failed_job_type = str(failed_request.get("job_type") or "")
            composition_id = str(failed_request.get("composition_id") or "").strip()
            if composition_id:
                composition_path = (
                    ENGINE_ROOT / "runtime" / "compositions" / composition_id / "composition.json"
                )
                payload = read_json(composition_path, {}) or {}
                if payload:
                    if failed_job_type == "assemble":
                        payload["status"] = "assemble_failed"
                    payload["updated_at"] = now_iso()
                    payload["last_error"] = error_text
                    atomic_write_json(composition_path, payload)
        finally:
            open_batch = load_open_batch(ENGINE_ROOT)
            write_worker_status(
                "idle",
                current_job=None,
                stage=None,
                elapsed_seconds=None,
                current_batch=(open_batch or {}).get("batch_id"),
                batch_stage=(open_batch or {}).get("stage"),
                batch_status=(open_batch or {}).get("status"),
                batch_message=(open_batch or {}).get("message"),
                batch_next_stage=(open_batch or {}).get("next_stage"),
            )

    log_event("worker_stopped")
    write_worker_status("stopped", current_job=None)


if __name__ == "__main__":
    main()
