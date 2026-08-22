from __future__ import annotations

"""Wake and hibernate the Windows ComfyUI host used for candidate renders."""

import json
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class RemoteRenderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    comfy_url: str
    agent_url: str
    agent_token: str
    wol_mac: str
    wol_broadcast: str
    wol_port: int = 9
    wake_timeout_seconds: float = 240.0
    poll_seconds: float = 5.0
    hibernate_idle_seconds: float = 300.0
    hibernate_confirm_timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "Config | None":
        comfy_url = str(os.environ.get("H3_CANDIDATE_COMFY_URL") or "").strip().rstrip("/")
        if not comfy_url:
            return None
        return cls(
            comfy_url=comfy_url,
            agent_url=str(
                os.environ.get("H3_RENDER_AGENT_URL")
                or os.environ.get("H3_PROMPT_REVISION_REMOTE_URL")
                or ""
            ).strip().rstrip("/"),
            agent_token=str(
                os.environ.get("H3_RENDER_AGENT_TOKEN")
                or os.environ.get("H3_PROMPT_REVISION_REMOTE_TOKEN")
                or ""
            ).strip(),
            wol_mac=str(
                os.environ.get("H3_RENDER_WOL_MAC")
                or os.environ.get("H3_PROMPT_REVISION_WOL_MAC")
                or ""
            ).strip(),
            wol_broadcast=str(
                os.environ.get("H3_RENDER_WOL_BROADCAST")
                or os.environ.get("H3_PROMPT_REVISION_WOL_BROADCAST")
                or "255.255.255.255"
            ).strip(),
            wol_port=int(
                os.environ.get("H3_RENDER_WOL_PORT")
                or os.environ.get("H3_PROMPT_REVISION_WOL_PORT")
                or 9
            ),
            wake_timeout_seconds=float(
                os.environ.get("H3_RENDER_WAKE_TIMEOUT_SECONDS") or 240
            ),
            poll_seconds=float(os.environ.get("H3_RENDER_POLL_SECONDS") or 5),
            hibernate_idle_seconds=float(
                os.environ.get("H3_RENDER_HIBERNATE_IDLE_SECONDS") or 300
            ),
            hibernate_confirm_timeout_seconds=float(
                os.environ.get("H3_RENDER_HIBERNATE_CONFIRM_TIMEOUT_SECONDS") or 60
            ),
        )


def send_wake_on_lan(mac: str, broadcast: str, port: int = 9) -> None:
    normalized = "".join(character for character in mac if character.isalnum())
    if len(normalized) != 12:
        raise ValueError("Windows 렌더 PC의 WOL MAC 주소 형식이 올바르지 않습니다.")
    try:
        mac_bytes = bytes.fromhex(normalized)
    except ValueError as exc:
        raise ValueError("Windows 렌더 PC의 WOL MAC 주소 형식이 올바르지 않습니다.") from exc
    packet = b"\xff" * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as handle:
        handle.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        handle.sendto(packet, (broadcast, port))


class RemoteRenderPowerManager:
    def __init__(self, config: Config | None) -> None:
        self.config = config
        self.wake_owned = False
        self.hibernate_armed = False
        self.last_activity = time.monotonic()

    def manages(self, comfy_url: str) -> bool:
        return bool(
            self.config
            and str(comfy_url or "").rstrip("/") == self.config.comfy_url
        )

    def _agent_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        authenticated: bool,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        if not self.config or not self.config.agent_url:
            raise RemoteRenderUnavailable("Windows 전원 에이전트 주소가 설정되지 않았습니다.")
        headers = {"accept": "application/json"}
        body = None
        if authenticated:
            if not self.config.agent_token:
                raise RemoteRenderUnavailable("Windows 전원 에이전트 토큰이 설정되지 않았습니다.")
            headers["authorization"] = f"Bearer {self.config.agent_token}"
        if payload is not None:
            headers["content-type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.agent_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
        parsed = json.loads(raw.decode("utf-8")) if raw else {}
        return parsed if isinstance(parsed, dict) else {}

    def agent_awake(self) -> bool:
        try:
            response = self._agent_request(
                "GET", "/healthz", authenticated=False, timeout=3.0
            )
            return response.get("status") == "ok"
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
            return False

    def ensure_comfy(self, client: Any) -> bool:
        """Return True when this worker had to wake the managed Windows host."""
        initial_error: Exception | None = None
        try:
            client.health()
            self.touch()
            return False
        except Exception as exc:
            initial_error = exc
        if not self.config:
            raise RemoteRenderUnavailable("Windows 후보 렌더 설정이 없습니다.")

        was_awake = self.agent_awake()
        if not was_awake:
            if not self.config.wol_mac:
                raise RemoteRenderUnavailable(
                    "Windows 후보 렌더 PC가 꺼져 있고 WOL MAC 주소가 설정되지 않았습니다."
                ) from initial_error
            for _ in range(5):
                send_wake_on_lan(
                    self.config.wol_mac,
                    self.config.wol_broadcast,
                    self.config.wol_port,
                )
            self.wake_owned = True

        deadline = time.monotonic() + self.config.wake_timeout_seconds
        last_error = initial_error
        while time.monotonic() < deadline:
            try:
                client.health()
                self.touch()
                return not was_awake
            except Exception as exc:
                last_error = exc
                time.sleep(self.config.poll_seconds)

        state = "켜져 있지만" if was_awake or self.agent_awake() else "WOL 이후에도 켜지지 않았고"
        raise RemoteRenderUnavailable(
            f"Windows PC가 {state} ComfyUI API가 준비되지 않았습니다: "
            f"{self.config.comfy_url} ({type(last_error).__name__}: {last_error})"
        ) from last_error

    def touch(self) -> None:
        if self.config:
            self.hibernate_armed = True
            self.last_activity = time.monotonic()

    def _comfy_busy(self) -> bool:
        if not self.config:
            return False
        try:
            with urllib.request.urlopen(
                f"{self.config.comfy_url}/queue", timeout=3.0
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
            return False
        return bool(
            list(payload.get("queue_running") or [])
            or list(payload.get("queue_pending") or [])
        )

    def _wait_for_agent_offline(self) -> float:
        if not self.config:
            raise RemoteRenderUnavailable("Windows 후보 렌더 설정이 없습니다.")
        started = time.monotonic()
        deadline = started + self.config.hibernate_confirm_timeout_seconds
        misses = 0
        while time.monotonic() < deadline:
            if self.agent_awake():
                misses = 0
            else:
                misses += 1
                if misses >= 3:
                    return time.monotonic() - started
            time.sleep(min(2.0, max(0.1, self.config.poll_seconds)))
        raise RemoteRenderUnavailable(
            "Windows 최대절전 명령은 수락됐지만 전원 API가 오프라인으로 전환되지 않았습니다."
        )

    def maybe_hibernate(self) -> bool:
        if (
            not self.config
            or not self.hibernate_armed
            or self.config.hibernate_idle_seconds <= 0
            or time.monotonic() - self.last_activity < self.config.hibernate_idle_seconds
        ):
            return False
        if self._comfy_busy():
            self.last_activity = time.monotonic()
            return False
        try:
            response = self._agent_request(
                "POST",
                "/v1/power/hibernate",
                {"confirm": "hibernate"},
                authenticated=True,
                timeout=10.0,
            )
        except urllib.error.HTTPError as exc:
            raise RemoteRenderUnavailable(
                f"Windows 최대절전 API가 HTTP {exc.code}로 거절했습니다."
            ) from exc
        if response.get("status") != "hibernate_scheduled":
            raise RemoteRenderUnavailable(
                f"Windows 최대절전 요청 응답이 올바르지 않습니다: {response}"
            )
        self._wait_for_agent_offline()
        self.hibernate_armed = False
        self.wake_owned = False
        return True
