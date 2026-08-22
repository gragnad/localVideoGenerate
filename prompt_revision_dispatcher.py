from __future__ import annotations

"""Dispatch saved H3 prompt revisions to a wake-on-demand remote authoring PC."""

import argparse
import json
import os
import signal
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import h3_queue
import h3_prompt_contract
from job_queue import atomic_write_json, now_iso


@dataclass(frozen=True)
class Config:
    root: Path
    remote_url: str
    token: str
    wol_mac: str
    wol_broadcast: str
    wol_port: int = 9
    poll_seconds: float = 5.0
    wake_timeout_seconds: float = 180.0
    health_timeout_seconds: float = 3.0
    request_timeout_seconds: float = 1800.0
    retry_base_seconds: int = 30
    max_attempts: int = 5
    hibernate_after_idle_seconds: int = 300

    @classmethod
    def from_env(cls) -> "Config":
        remote_url = str(
            os.environ.get("H3_PROMPT_REVISION_REMOTE_URL")
            or os.environ.get("H3_RENDER_AGENT_URL")
            or ""
        ).strip().rstrip("/")
        token = str(
            os.environ.get("H3_PROMPT_REVISION_REMOTE_TOKEN")
            or os.environ.get("H3_RENDER_AGENT_TOKEN")
            or ""
        ).strip()
        mac = str(
            os.environ.get("H3_PROMPT_REVISION_WOL_MAC")
            or os.environ.get("H3_RENDER_WOL_MAC")
            or ""
        ).strip()
        if not remote_url or not token or not mac:
            raise ValueError(
                "원격 Windows 에이전트 URL, 토큰, WOL MAC 환경 변수가 필요합니다."
            )
        return cls(
            root=Path(os.environ.get("VIDEO_ENGINE_ROOT") or Path(__file__).resolve().parent).resolve(),
            remote_url=remote_url,
            token=token,
            wol_mac=mac,
            wol_broadcast=str(
                os.environ.get("H3_PROMPT_REVISION_WOL_BROADCAST")
                or os.environ.get("H3_RENDER_WOL_BROADCAST")
                or "255.255.255.255"
            ).strip(),
            wol_port=int(
                os.environ.get("H3_PROMPT_REVISION_WOL_PORT")
                or os.environ.get("H3_RENDER_WOL_PORT")
                or 9
            ),
            poll_seconds=float(os.environ.get("H3_PROMPT_REVISION_POLL_SECONDS") or 5),
            wake_timeout_seconds=float(
                os.environ.get("H3_PROMPT_REVISION_WAKE_TIMEOUT_SECONDS")
                or os.environ.get("H3_RENDER_WAKE_TIMEOUT_SECONDS")
                or 180
            ),
            request_timeout_seconds=float(
                os.environ.get("H3_PROMPT_REVISION_REQUEST_TIMEOUT_SECONDS") or 1800
            ),
            retry_base_seconds=int(
                os.environ.get("H3_PROMPT_REVISION_RETRY_BASE_SECONDS") or 30
            ),
            max_attempts=int(os.environ.get("H3_PROMPT_REVISION_MAX_ATTEMPTS") or 5),
            hibernate_after_idle_seconds=int(
                os.environ.get("H3_PROMPT_REVISION_HIBERNATE_IDLE_SECONDS")
                or os.environ.get("H3_RENDER_HIBERNATE_IDLE_SECONDS")
                or 300
            ),
        )


def _log(message: str) -> None:
    print(f"[{now_iso()}] {message}", flush=True)


def _json_request(
    config: Config,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float,
    authenticated: bool = True,
) -> dict[str, Any]:
    body = None
    headers = {"accept": "application/json"}
    if authenticated:
        headers["authorization"] = f"Bearer {config.token}"
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json"
    request = urllib.request.Request(
        f"{config.remote_url}{path}", data=body, headers=headers, method=method
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    parsed = json.loads(raw.decode("utf-8")) if raw else {}
    if not isinstance(parsed, dict):
        raise ValueError("원격 작성 API가 JSON 객체를 반환하지 않았습니다.")
    return parsed


def remote_health(config: Config) -> dict[str, Any] | None:
    try:
        health = _json_request(
            config,
            "GET",
            "/healthz",
            timeout=config.health_timeout_seconds,
            authenticated=False,
        )
        return health if health.get("status") == "ok" else None
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
        return None


def send_wake_on_lan(mac: str, broadcast: str, port: int = 9) -> None:
    normalized = "".join(character for character in mac if character.isalnum())
    if len(normalized) != 12:
        raise ValueError("WOL MAC 주소 형식이 올바르지 않습니다.")
    try:
        mac_bytes = bytes.fromhex(normalized)
    except ValueError as exc:
        raise ValueError("WOL MAC 주소 형식이 올바르지 않습니다.") from exc
    packet = b"\xff" * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as handle:
        handle.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        handle.sendto(packet, (broadcast, port))


def ensure_remote_awake(config: Config) -> tuple[dict[str, Any], bool]:
    health = remote_health(config)
    if health:
        return health, False
    send_wake_on_lan(config.wol_mac, config.wol_broadcast, config.wol_port)
    _log(
        f"WOL 전송: {config.wol_mac} -> {config.wol_broadcast}:{config.wol_port}"
    )
    deadline = time.monotonic() + config.wake_timeout_seconds
    while time.monotonic() < deadline:
        time.sleep(min(config.poll_seconds, 10.0))
        health = remote_health(config)
        if health:
            return health, True
    raise TimeoutError("WOL 이후 원격 프롬프트 작성 API가 준비되지 않았습니다.")


def _retry_due(payload: dict[str, Any]) -> bool:
    raw = str(payload.get("next_retry_at") or "").strip()
    if not raw:
        return True


def _in_progress_stale(payload: dict[str, Any], timeout_seconds: float) -> bool:
    raw = str(payload.get("remote_started_at") or "").strip()
    if not raw:
        return True
    try:
        started = datetime.fromisoformat(raw)
    except ValueError:
        return True
    return datetime.now().astimezone() - started > timedelta(
        seconds=timeout_seconds + 60
    )
    try:
        return datetime.fromisoformat(raw) <= datetime.now().astimezone()
    except ValueError:
        return True


def _remote_payload(request_payload: dict[str, Any], wake_owned: bool, config: Config) -> dict[str, Any]:
    payload = {
        "schema_version": 2,
        "prompt_contract_version": h3_prompt_contract.CONTRACT_VERSION,
        "authoring_mode": "fresh_from_scenario",
        "prompt_revision_request_id": request_payload["prompt_revision_request_id"],
        "feedback": request_payload.get("feedback"),
        "expected_variant_ids": request_payload.get("expected_variant_ids"),
        "clip_context": request_payload.get("clip_context"),
        "previous_error": request_payload.get("remote_error"),
    }
    if wake_owned and config.hibernate_after_idle_seconds > 0:
        payload["power_lease"] = {
            "hibernate_after_idle_seconds": config.hibernate_after_idle_seconds
        }
    return payload


def process_request(config: Config, request_payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(request_payload["prompt_revision_request_id"])
    attempts = int(request_payload.get("remote_attempts") or 0) + 1
    claimed = h3_queue.update_prompt_revision_request(
        config.root,
        request_id,
        {
            "status": "remote_authoring_in_progress",
            "authoring_mode": "remote_codex_api",
            "remote_attempts": attempts,
            "remote_started_at": now_iso(),
            "remote_error": None,
            "next_retry_at": None,
            "remote_dispatcher": socket.gethostname(),
        },
        expected_statuses={
            "awaiting_codex_authoring",
            "awaiting_remote_authoring",
            "remote_authoring_failed",
        },
    )
    try:
        health, wake_owned = ensure_remote_awake(config)
        _log(
            f"원격 작성 시작: {request_id} · wake_owned={wake_owned} · "
            f"agent={health.get('agent_version', 'unknown')}"
        )
        response = _json_request(
            config,
            "POST",
            "/v1/h3/prompt-revisions",
            _remote_payload(claimed, wake_owned, config),
            timeout=config.request_timeout_seconds,
        )
        if response.get("prompt_revision_request_id") != request_id:
            raise ValueError("원격 응답의 프롬프트 수정 요청 ID가 일치하지 않습니다.")
        response_path = (
            h3_queue.roots(config.root)["prompt_revision_requests"]
            / request_id
            / "remote_response.json"
        )
        atomic_write_json(response_path, response)
        revised = h3_queue.apply_authored_prompt_revision(
            config.root,
            request_id,
            {
                "prompt_variants": response.get("prompt_variants"),
                "authored_by": "remote_codex_api",
            },
        )
        _log(
            f"원격 작성 적용 완료: {request_id} -> {revised['candidate_set_id']}"
        )
        return revised
    except Exception as exc:
        delay = config.retry_base_seconds * (2 ** max(0, attempts - 1))
        next_retry = datetime.now().astimezone() + timedelta(seconds=delay)
        error = f"{type(exc).__name__}: {exc}"
        h3_queue.update_prompt_revision_request(
            config.root,
            request_id,
            {
                "status": "remote_authoring_failed",
                "remote_error": error[:2000],
                "remote_failed_at": now_iso(),
                "next_retry_at": next_retry.isoformat(),
            },
            expected_statuses={"remote_authoring_in_progress"},
        )
        _log(f"원격 작성 실패: {request_id} · {error}")
        raise


def process_once(config: Config) -> bool:
    for payload in h3_queue.list_prompt_revision_requests(config.root):
        status = str(payload.get("status") or "")
        if status == "remote_authoring_in_progress" and _in_progress_stale(
            payload, config.request_timeout_seconds
        ):
            h3_queue.update_prompt_revision_request(
                config.root,
                str(payload["prompt_revision_request_id"]),
                {
                    "status": "remote_authoring_failed",
                    "remote_error": "Dispatcher restarted after a stale remote authoring lease.",
                    "next_retry_at": now_iso(),
                },
                expected_statuses={"remote_authoring_in_progress"},
            )
            return False
        if status not in {
            "awaiting_codex_authoring",
            "awaiting_remote_authoring",
            "remote_authoring_failed",
        }:
            continue
        if int(payload.get("remote_attempts") or 0) >= config.max_attempts:
            continue
        if not _retry_due(payload):
            continue
        process_request(config, payload)
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="처리 가능한 요청 하나만 확인합니다.")
    args = parser.parse_args()
    try:
        config = Config.from_env()
    except (TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    stopped = False

    def stop(_signum: int, _frame: Any) -> None:
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    _log(f"원격 프롬프트 디스패처 시작: {config.remote_url}")
    while not stopped:
        try:
            processed = process_once(config)
        except Exception:
            processed = False
        if args.once:
            return 0 if processed else 1
        if not processed:
            time.sleep(config.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
