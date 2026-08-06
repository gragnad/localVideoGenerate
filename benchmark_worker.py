from __future__ import annotations

"""Generic ComfyUI execution path for model benchmark jobs."""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import benchmark_jobs
from job_queue import atomic_write_json, now_iso, read_json, update_status
from review_workflow import find_primary_video_output


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_memory_metrics() -> dict[str, int | None]:
    gpu_bytes = None
    system_bytes = None
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        values = [int(line.strip()) for line in completed.stdout.splitlines() if line.strip().isdigit()]
        if values:
            gpu_bytes = max(values) * 1024 * 1024
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    try:
        values: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0]) * 1024
        system_bytes = max(0, values.get("MemTotal", 0) - values.get("MemAvailable", 0))
    except (OSError, ValueError, IndexError):
        pass
    return {"gpu": gpu_bytes, "system": system_bytes}


def _max_metric(current: int | None, value: int | None) -> int | None:
    if value is None:
        return current
    return value if current is None else max(current, value)


def _local_output_path(output: dict[str, Any]) -> Path | None:
    if output.get("local_path"):
        path = Path(str(output["local_path"]))
        return path if path.is_file() else None
    if str(output.get("type") or "output") != "output":
        return None
    base = Path(
        os.environ.get(
            "COMFY_OUTPUT_DIR",
            str(Path.home() / "ai-workspace/apps/ComfyUI/output"),
        )
    ).expanduser().resolve()
    path = (base / str(output.get("subfolder") or "") / str(output.get("filename") or "")).resolve()
    if (path == base or base in path.parents) and path.is_file():
        return path
    return None


def process_benchmark_job(
    job_dir: Path,
    *,
    ensure_client: Callable[[dict[str, Any]], Any],
    queue_position: Callable[[dict[str, Any], str], tuple[str, int | None]],
    stop_requested: Callable[[], bool] = lambda: False,
    memory_sampler: Callable[[], dict[str, int | None]] = sample_memory_metrics,
    poll_seconds: float = 2.0,
    timeout_seconds: float = 8 * 60 * 60,
) -> None:
    request = read_json(job_dir / "request.json", {}) or {}
    if request.get("job_type") != "model_benchmark":
        raise ValueError("모델 벤치마크 작업 요청이 아닙니다.")
    request["job_dir"] = str(job_dir)
    update_status(
        job_dir,
        "preparing",
        stage="모델 테스트 준비",
        started_at=now_iso(),
        progress=0.02,
    )
    started = time.monotonic()
    peak_gpu = None
    peak_system = None
    outputs: list[dict[str, Any]] = []
    try:
        workflow_path = Path(str(request.get("template_path") or ""))
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        if _hash_json(workflow) != str(request.get("compiled_workflow_sha256") or ""):
            raise ValueError("큐 등록 후 컴파일된 워크플로우가 변경되었습니다.")
        client = ensure_client(request)
        upload_records = []
        assets = list(request.get("assets") or [])
        for index, asset in enumerate(assets, start=1):
            source = Path(str(asset.get("source_path") or ""))
            if not source.is_file():
                raise FileNotFoundError(f"테스트 자산을 찾을 수 없습니다: {asset.get('asset_id')}")
            content = source.read_bytes()
            if hashlib.sha256(content).hexdigest() != asset.get("sha256"):
                raise ValueError(f"테스트 자산 해시가 변경되었습니다: {asset.get('asset_id')}")
            update_status(
                job_dir,
                "uploading",
                stage=f"테스트 자산 업로드 {index}/{len(assets)}",
                progress=0.04 + 0.10 * index / max(1, len(assets)),
            )
            uploaded = client.upload_input(
                filename=str(asset["filename"]),
                content=content,
                subfolder="model_tests",
                overwrite=True,
            )
            binding = dict(asset.get("binding") or {})
            node = workflow.get(str(binding.get("node_id") or ""))
            input_name = str(binding.get("input") or "")
            if not node or input_name not in dict(node.get("inputs") or {}):
                raise ValueError(f"실행 시점 자산 바인딩이 유효하지 않습니다: {asset.get('role')}")
            value = "/".join(
                part.strip("/")
                for part in (uploaded.get("subfolder"), uploaded.get("name"))
                if str(part or "").strip("/")
            )
            node["inputs"][input_name] = value
            upload_records.append({
                "asset_id": asset.get("asset_id"),
                "role": asset.get("role"),
                "sha256": asset.get("sha256"),
                "comfy_response": uploaded,
            })
        atomic_write_json(job_dir / "workflow_api_runtime.json", workflow)
        manifest = read_json(job_dir / "manifest.json", {}) or {}
        manifest.update(status="built", uploads=upload_records, updated_at=now_iso())
        atomic_write_json(job_dir / "manifest.json", manifest)
        update_status(job_dir, "submitting", stage="모델 테스트 ComfyUI 큐 제출", progress=0.18)
        queue_response = client.queue_prompt(workflow)
        prompt_id = str(queue_response["prompt_id"])
        atomic_write_json(job_dir / "queue_response.json", queue_response)
        manifest.update(status="queued", prompt_id=prompt_id, updated_at=now_iso())
        atomic_write_json(job_dir / "manifest.json", manifest)
        update_status(
            job_dir,
            "comfy_queued",
            stage="모델 테스트 ComfyUI 큐 대기",
            prompt_id=prompt_id,
            progress=0.20,
        )
        last_status_write = 0.0
        while True:
            if stop_requested():
                raise RuntimeError("worker 종료 요청으로 모델 테스트를 중단했습니다.")
            elapsed = time.monotonic() - started
            if elapsed > timeout_seconds:
                raise TimeoutError("모델 테스트 생성이 제한 시간 안에 완료되지 않았습니다.")
            sample = memory_sampler()
            peak_gpu = _max_metric(peak_gpu, sample.get("gpu"))
            peak_system = _max_metric(peak_system, sample.get("system"))
            history = client.get_history(prompt_id)
            if prompt_id in history:
                client._raise_on_execution_error(history[prompt_id])
                atomic_write_json(job_dir / "history.json", history)
                outputs = client.extract_output_files(history, prompt_id)
                if not find_primary_video_output(outputs):
                    raise RuntimeError("워크플로우는 완료됐지만 영상 출력이 없습니다.")
                primary = find_primary_video_output(outputs)
                output_path = _local_output_path(primary or {})
                output_sha256 = _sha256_file(output_path) if output_path else None
                elapsed = time.monotonic() - started
                manifest.update(
                    status="completed",
                    completed_at=now_iso(),
                    outputs=outputs,
                    generation_seconds=round(elapsed, 3),
                    peak_gpu_memory_bytes=peak_gpu,
                    peak_system_memory_bytes=peak_system,
                    updated_at=now_iso(),
                )
                atomic_write_json(job_dir / "manifest.json", manifest)
                update_status(
                    job_dir,
                    "completed",
                    stage="모델 테스트 완료",
                    message=f"영상 출력 {len(outputs)}개",
                    progress=1.0,
                    elapsed_seconds=round(elapsed, 1),
                    outputs=outputs,
                    completed_at=now_iso(),
                )
                benchmark_jobs.record_result(
                    Path(str(request["engine_root"])),
                    request,
                    status="completed",
                    generation_seconds=elapsed,
                    peak_gpu_memory_bytes=peak_gpu,
                    peak_system_memory_bytes=peak_system,
                    output_path=str(output_path) if output_path else None,
                    output_sha256=output_sha256,
                    outputs=outputs,
                )
                return
            now = time.monotonic()
            if now - last_status_write >= 2.0:
                try:
                    state, position = queue_position(client.get_queue(), prompt_id)
                except Exception:
                    state, position = "running", None
                update_status(
                    job_dir,
                    state,
                    stage="모델 테스트 실행 중" if state == "running" else "모델 테스트 큐 대기",
                    prompt_id=prompt_id,
                    queue_position=position,
                    progress=0.30 if state == "running" else 0.20,
                    elapsed_seconds=round(elapsed, 1),
                )
                last_status_write = now
            time.sleep(poll_seconds)
    except Exception as exc:
        elapsed = time.monotonic() - started
        benchmark_jobs.record_result(
            Path(str(request.get("engine_root") or job_dir.parent.parent)),
            request,
            status="failed",
            generation_seconds=elapsed,
            peak_gpu_memory_bytes=peak_gpu,
            peak_system_memory_bytes=peak_system,
            outputs=outputs,
            error=f"{type(exc).__name__}: {exc}",
        )
        raise
