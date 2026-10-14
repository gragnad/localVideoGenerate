from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

from job_queue import atomic_write_json, now_iso


HOME = Path.home()
ENGINE_ROOT = Path(os.environ.get("VIDEO_ENGINE_ROOT", HOME / "local-ai/video-engine"))
RUNTIME_ROOT = ENGINE_ROOT / "runtime"
ENGINE_STATE_PATH = RUNTIME_ROOT / "engine_state.json"

COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
VLLM_URL = os.environ.get("VLLM_URL", "http://127.0.0.1:8091").rstrip("/")

COMFY_START_SCRIPT = Path(
    os.environ.get("COMFY_START_SCRIPT", HOME / "bin/ai-start-comfy")
).expanduser()
COMFY_STOP_SCRIPT = Path(
    os.environ.get("COMFY_STOP_SCRIPT", HOME / "bin/ai-stop-comfy")
).expanduser()
VLLM_START_SCRIPT = Path(
    os.environ.get("VLLM_START_SCRIPT", HOME / "bin/ai-start-vllm")
).expanduser()
VLLM_STOP_SCRIPT = Path(
    os.environ.get("VLLM_STOP_SCRIPT", HOME / "bin/ai-stop-vllm")
).expanduser()

COMFY_START_TIMEOUT = float(os.environ.get("COMFY_START_TIMEOUT", "240"))
COMFY_STOP_TIMEOUT = float(os.environ.get("COMFY_STOP_TIMEOUT", "120"))
VLLM_START_TIMEOUT = float(os.environ.get("VLLM_START_TIMEOUT", "900"))
VLLM_STOP_TIMEOUT = float(os.environ.get("VLLM_STOP_TIMEOUT", "180"))


class EngineSwitchError(RuntimeError):
    pass


def _write_state(state: str, **fields: Any) -> None:
    payload = {
        "state": state,
        "updated_at": now_iso(),
        **fields,
    }
    atomic_write_json(ENGINE_STATE_PATH, payload)


def _run_script(path: Path, label: str, timeout: float = 120.0) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{label} 스크립트를 찾을 수 없습니다: {path}")
    if not os.access(path, os.X_OK):
        raise PermissionError(f"{label} 스크립트에 실행 권한이 없습니다: {path}")

    completed = subprocess.run(
        [str(path)],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = "\n".join(
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part and part.strip()
    )
    if completed.returncode != 0:
        raise EngineSwitchError(
            f"{label} 실패 (exit={completed.returncode})\n{output}"
        )
    return output or f"{label} 완료"


def _http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        response = requests.get(url, timeout=timeout)
        return response.ok
    except requests.RequestException:
        return False


def comfy_ready() -> bool:
    return _http_ok(f"{COMFY_URL}/system_stats")


def vllm_ready() -> bool:
    return _http_ok(f"{VLLM_URL}/v1/models")


def _wait_until(
    predicate,
    *,
    expected: bool,
    timeout: float,
    label: str,
    interval: float = 2.0,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if bool(predicate()) is expected:
            return
        time.sleep(interval)
    condition = "준비" if expected else "종료"
    raise TimeoutError(f"{label} {condition} 확인 시간 초과 ({timeout:.0f}초)")


def stop_comfy() -> None:
    if not comfy_ready():
        _write_state("comfy_stopped", active_engine="none")
        return

    _write_state(
        "comfy_stopping",
        active_engine="comfy",
        script=str(COMFY_STOP_SCRIPT),
    )
    _run_script(
        COMFY_STOP_SCRIPT,
        "ComfyUI 종료",
        timeout=max(120.0, COMFY_STOP_TIMEOUT + 30.0),
    )
    _wait_until(
        comfy_ready,
        expected=False,
        timeout=COMFY_STOP_TIMEOUT,
        label="ComfyUI",
    )
    _write_state("comfy_stopped", active_engine="none")


def start_comfy() -> None:
    if comfy_ready():
        _write_state("comfy_ready", active_engine="comfy")
        return

    _write_state(
        "comfy_starting",
        active_engine="none",
        script=str(COMFY_START_SCRIPT),
    )
    _run_script(
        COMFY_START_SCRIPT,
        "ComfyUI 시작",
        timeout=max(120.0, COMFY_START_TIMEOUT + 30.0),
    )
    _wait_until(
        comfy_ready,
        expected=True,
        timeout=COMFY_START_TIMEOUT,
        label="ComfyUI",
    )
    _write_state("comfy_ready", active_engine="comfy")


def stop_vllm() -> None:
    if not vllm_ready():
        _write_state("vllm_stopped", active_engine="none")
        return

    _write_state(
        "vllm_stopping",
        active_engine="vllm",
        script=str(VLLM_STOP_SCRIPT),
    )
    _run_script(
        VLLM_STOP_SCRIPT,
        "vLLM 종료",
        timeout=max(180.0, VLLM_STOP_TIMEOUT + 30.0),
    )
    _wait_until(
        vllm_ready,
        expected=False,
        timeout=VLLM_STOP_TIMEOUT,
        label="vLLM",
    )
    _write_state("vllm_stopped", active_engine="none")


def start_vllm() -> None:
    if vllm_ready():
        _write_state("vllm_ready", active_engine="vllm")
        return

    _write_state(
        "vllm_starting",
        active_engine="none",
        script=str(VLLM_START_SCRIPT),
    )
    _run_script(
        VLLM_START_SCRIPT,
        "vLLM 시작",
        timeout=max(300.0, VLLM_START_TIMEOUT + 60.0),
    )
    _wait_until(
        vllm_ready,
        expected=True,
        timeout=VLLM_START_TIMEOUT,
        label="vLLM",
    )
    _write_state("vllm_ready", active_engine="vllm")


def ensure_comfy_engine() -> None:
    """생성/검수 이미지 작업 전에 vLLM을 내리고 ComfyUI를 보장합니다."""
    if comfy_ready():
        _write_state("comfy_ready", active_engine="comfy")
        return

    if vllm_ready():
        stop_vllm()
    start_comfy()


def ensure_vllm_engine() -> None:
    """ComfyUI 큐가 완전히 끝난 뒤 ComfyUI를 내리고 vLLM을 보장합니다."""
    if vllm_ready() and not comfy_ready():
        _write_state("vllm_ready", active_engine="vllm")
        return

    if comfy_ready():
        stop_comfy()
    start_vllm()


def engine_snapshot() -> dict[str, Any]:
    return {
        "comfy_ready": comfy_ready(),
        "vllm_ready": vllm_ready(),
        "comfy_url": COMFY_URL,
        "vllm_url": VLLM_URL,
        "state_file": str(ENGINE_STATE_PATH),
    }
