from __future__ import annotations

"""Minimal Windows power and GPU telemetry agent for H3 remote rendering."""

import argparse
import faulthandler
import hmac
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


AGENT_VERSION = "4"
MAX_BODY_BYTES = 16 * 1024
HEARTBEAT_INTERVAL_SECONDS = 30
HEARTBEAT_GAP_WARNING_SECONDS = 90


LOGGER = logging.getLogger("nalstudio.windows_render_agent")
LOGGER.addHandler(logging.NullHandler())


def _configure_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.handlers.clear()
    LOGGER.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s pid=%(process)d thread=%(threadName)s %(message)s"
    )
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    rotating = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    rotating.setFormatter(formatter)
    LOGGER.addHandler(stream)
    LOGGER.addHandler(rotating)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporary, path)


class LifecycleDiagnostics:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.started_at = time.time()
        self.last_heartbeat_at = self.started_at
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.payload: dict[str, Any] = {}

    def start(self) -> None:
        previous: dict[str, Any] = {}
        try:
            loaded = json.loads(self.state_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                previous = loaded
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        if previous and not previous.get("clean_shutdown", False):
            LOGGER.warning(
                "previous_run_unclean previous_pid=%s previous_started_at_epoch=%s "
                "previous_heartbeat_at_epoch=%s previous_exit_reason=%s",
                previous.get("pid"),
                previous.get("started_at_epoch"),
                previous.get("heartbeat_at_epoch"),
                previous.get("exit_reason"),
            )
        self.payload = {
            "agent_version": AGENT_VERSION,
            "pid": os.getpid(),
            "started_at_epoch": self.started_at,
            "heartbeat_at_epoch": self.started_at,
            "clean_shutdown": False,
            "exit_reason": None,
        }
        self._write()
        self.thread = threading.Thread(
            target=self._heartbeat_loop,
            name="diagnostic-heartbeat",
            daemon=True,
        )
        self.thread.start()

    def _write(self) -> None:
        try:
            _atomic_write_json(self.state_file, self.payload)
        except OSError:
            LOGGER.exception("diagnostic_state_write_failed path=%s", self.state_file)

    def _heartbeat_loop(self) -> None:
        while not self.stop_event.wait(HEARTBEAT_INTERVAL_SECONDS):
            now = time.time()
            gap = now - self.last_heartbeat_at
            if gap >= HEARTBEAT_GAP_WARNING_SECONDS:
                LOGGER.warning("heartbeat_gap seconds=%.1f possible_sleep_or_stall=true", gap)
            self.last_heartbeat_at = now
            self.payload["heartbeat_at_epoch"] = now
            self._write()

    def stop(self, reason: str, *, clean: bool) -> None:
        self.stop_event.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=2)
        now = time.time()
        self.payload.update(
            {
                "heartbeat_at_epoch": now,
                "stopped_at_epoch": now,
                "clean_shutdown": clean,
                "exit_reason": reason,
            }
        )
        self._write()
        LOGGER.info("agent_stopping reason=%s clean=%s", reason, clean)


def _install_exception_logging(crash_file: Path) -> Any:
    crash_file.parent.mkdir(parents=True, exist_ok=True)
    crash_handle = crash_file.open("a", encoding="utf-8")
    faulthandler.enable(file=crash_handle, all_threads=True)

    def process_exception(exc_type: Any, exc_value: Any, traceback: Any) -> None:
        LOGGER.critical(
            "unhandled_process_exception",
            exc_info=(exc_type, exc_value, traceback),
        )

    def thread_exception(args: threading.ExceptHookArgs) -> None:
        LOGGER.critical(
            "unhandled_thread_exception thread=%s",
            getattr(args.thread, "name", None),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = process_exception
    threading.excepthook = thread_exception
    return crash_handle


def _read_token(path: Path) -> str:
    token = path.read_text(encoding="utf-8").strip()
    if len(token) < 32:
        raise ValueError("Bearer token must contain at least 32 characters")
    return token


def _nvidia_smi_command() -> str | None:
    resolved = shutil.which("nvidia-smi.exe") or shutil.which("nvidia-smi")
    if resolved:
        return resolved
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidate = Path(program_files) / "NVIDIA Corporation" / "NVSMI" / "nvidia-smi.exe"
    return str(candidate) if candidate.is_file() else None


def gpu_power_w() -> float | None:
    """Return total instantaneous NVIDIA GPU power, or None when unavailable."""
    command = _nvidia_smi_command()
    if not command:
        return None
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [
                command,
                "--query-gpu=power.draw",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=4,
            check=False,
            creationflags=creation_flags,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    values: list[float] = []
    for line in completed.stdout.splitlines():
        try:
            values.append(float(line.strip()))
        except ValueError:
            continue
    return round(sum(values), 1) if values else None


class AgentState:
    def __init__(
        self,
        token: str,
        *,
        log_file: Path | None = None,
        state_file: Path | None = None,
        crash_file: Path | None = None,
    ) -> None:
        self.token = token
        self.started_at = time.time()
        self.log_file = log_file
        self.state_file = state_file
        self.crash_file = crash_file
        self.hibernate_scheduled = False
        self.last_hibernate_requested_at: float | None = None
        self.last_hibernate_finished_at: float | None = None
        self.last_hibernate_exit_code: int | None = None
        self.last_hibernate_error: str | None = None
        self.lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "H3WindowsRenderAgent/4"

    @property
    def state(self) -> AgentState:
        return self.server.agent_state  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        if self.path == "/healthz" and len(args) > 1 and str(args[1]) == "200":
            return
        LOGGER.info("http client=%s %s", self.address_string(), format % args)

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        supplied = self.headers.get("authorization", "")
        return hmac.compare_digest(supplied, f"Bearer {self.state.token}")

    def do_GET(self) -> None:
        if self.path != "/healthz":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        power_w = gpu_power_w()
        with self.state.lock:
            power_status = {
                "hibernate_scheduled": self.state.hibernate_scheduled,
                "last_hibernate_requested_at_epoch": self.state.last_hibernate_requested_at,
                "last_hibernate_finished_at_epoch": self.state.last_hibernate_finished_at,
                "last_hibernate_exit_code": self.state.last_hibernate_exit_code,
                "last_hibernate_error": self.state.last_hibernate_error,
            }
        self._send(
            HTTPStatus.OK,
            {
                "status": "ok",
                "agent_version": AGENT_VERSION,
                "role": "windows_render_power",
                "power_state": "awake",
                "power_policy": "linux_managed_hibernate",
                "gpu_power_w": power_w,
                "gpu_power_available": power_w is not None,
                "started_at_epoch": self.state.started_at,
                "pid": os.getpid(),
                "diagnostics": {
                    "log_file": str(self.state.log_file or ""),
                    "state_file": str(self.state.state_file or ""),
                    "crash_file": str(self.state.crash_file or ""),
                    "heartbeat_interval_seconds": HEARTBEAT_INTERVAL_SECONDS,
                },
                **power_status,
            },
        )

    def do_POST(self) -> None:
        if self.path != "/v1/power/hibernate":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_body_size"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return
        if not isinstance(payload, dict) or payload.get("confirm") != "hibernate":
            self._send(
                HTTPStatus.BAD_REQUEST,
                {"error": "confirm must equal hibernate"},
            )
            return
        with self.state.lock:
            if self.state.hibernate_scheduled:
                self._send(HTTPStatus.CONFLICT, {"error": "hibernate_already_scheduled"})
                return
            self.state.hibernate_scheduled = True
            self.state.last_hibernate_requested_at = time.time()
            self.state.last_hibernate_finished_at = None
            self.state.last_hibernate_exit_code = None
            self.state.last_hibernate_error = None
        LOGGER.warning("hibernate_requested client=%s", self.address_string())
        self._send(
            HTTPStatus.ACCEPTED,
            {
                "status": "hibernate_scheduled",
                "agent_version": AGENT_VERSION,
                "scheduled_in_seconds": 2,
            },
        )
        self.wfile.flush()
        threading.Thread(
            target=_hibernate_after_response,
            args=(self.state,),
            daemon=True,
        ).start()


class DiagnosticHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request: Any, client_address: Any) -> None:
        LOGGER.exception("http_handler_error client=%s", client_address)


def _hibernate_after_response(state: AgentState) -> None:
    time.sleep(2)
    exit_code: int | None = None
    error: str | None = None
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    LOGGER.warning("hibernate_command_start command=shutdown.exe_/h")
    try:
        completed = subprocess.run(
            ["shutdown.exe", "/h"],
            check=False,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=20,
            creationflags=creation_flags,
        )
        exit_code = completed.returncode
        if exit_code != 0:
            error = (completed.stderr or "").strip() or f"shutdown.exe exited {exit_code}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        # The Python process resumes with the same memory after Wake-on-LAN.
        # Always release the one-shot lock so a later idle cycle can hibernate again.
        with state.lock:
            state.hibernate_scheduled = False
            state.last_hibernate_finished_at = time.time()
            state.last_hibernate_exit_code = exit_code
            state.last_hibernate_error = error
        if error:
            LOGGER.error("hibernate_command_finished exit_code=%s error=%s", exit_code, error)
        else:
            LOGGER.warning("hibernate_command_finished exit_code=%s", exit_code)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="100.78.202.37")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--log-file", type=Path)
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--crash-file", type=Path)
    args = parser.parse_args()
    token_file = args.token_file.resolve()
    log_file = (args.log_file or token_file.parent / "render-agent.log").resolve()
    state_file = (args.state_file or token_file.parent / "runtime-state.json").resolve()
    crash_file = (args.crash_file or token_file.parent / "crash.log").resolve()
    _configure_logging(log_file)
    crash_handle = _install_exception_logging(crash_file)
    LOGGER.info(
        "agent_starting version=%s bind=%s port=%s log_file=%s state_file=%s crash_file=%s",
        AGENT_VERSION,
        args.bind,
        args.port,
        log_file,
        state_file,
        crash_file,
    )
    try:
        token = _read_token(token_file)
    except (OSError, ValueError) as exc:
        LOGGER.exception("token_load_failed path=%s error=%s", token_file, exc)
        faulthandler.disable()
        crash_handle.close()
        return 2

    diagnostics = LifecycleDiagnostics(state_file)
    diagnostics.start()
    state = AgentState(
        token,
        log_file=log_file,
        state_file=state_file,
        crash_file=crash_file,
    )
    try:
        server = DiagnosticHTTPServer((args.bind, args.port), Handler)
    except OSError as exc:
        LOGGER.exception(
            "server_bind_failed bind=%s port=%s error=%s", args.bind, args.port, exc
        )
        diagnostics.stop("server_bind_failed", clean=False)
        faulthandler.disable()
        crash_handle.close()
        return 3
    server.agent_state = state  # type: ignore[attr-defined]
    LOGGER.info("agent_listening url=http://%s:%s", args.bind, args.port)

    def handle_signal(signum: int, frame: Any) -> None:
        LOGGER.warning("termination_signal signal=%s", signum)
        raise KeyboardInterrupt

    for signal_name in ("SIGINT", "SIGTERM"):
        candidate = getattr(signal, signal_name, None)
        if candidate is not None:
            signal.signal(candidate, handle_signal)

    exit_reason = "normal_return"
    clean = True
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        exit_reason = "keyboard_interrupt_or_signal"
        LOGGER.warning("server_interrupted")
    except BaseException:
        exit_reason = "unhandled_server_exception"
        clean = False
        LOGGER.exception("server_unhandled_exception")
        raise
    finally:
        server.server_close()
        diagnostics.stop(exit_reason, clean=clean)
        faulthandler.disable()
        crash_handle.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
