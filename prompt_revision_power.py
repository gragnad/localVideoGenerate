from __future__ import annotations

"""Authenticated hibernate and Wake-on-LAN control for the Windows render PC."""

import argparse
import sys
import time

from prompt_revision_dispatcher import (
    Config,
    _json_request,
    remote_health,
    send_wake_on_lan,
)


def wait_for_offline(config: Config, timeout_seconds: float = 90) -> float:
    started = time.monotonic()
    deadline = started + timeout_seconds
    misses = 0
    while time.monotonic() < deadline:
        if remote_health(config):
            misses = 0
        else:
            misses += 1
            if misses >= 3:
                return time.monotonic() - started
        time.sleep(2)
    raise TimeoutError("Windows 최대절전 진입을 확인하지 못했습니다.")


def send_wake(config: Config, packets: int = 5) -> None:
    for _index in range(packets):
        send_wake_on_lan(config.wol_mac, config.wol_broadcast, config.wol_port)
        time.sleep(1)


def wait_for_online(config: Config) -> float:
    started = time.monotonic()
    deadline = started + config.wake_timeout_seconds
    while time.monotonic() < deadline:
        if remote_health(config):
            return time.monotonic() - started
        time.sleep(3)
    raise TimeoutError("WOL 이후 Windows 전원 API가 복귀하지 않았습니다.")


def hibernate(config: Config) -> float:
    if not remote_health(config):
        raise ConnectionError("Windows 전원 API가 현재 온라인이 아닙니다.")
    response = _json_request(
        config,
        "POST",
        "/v1/power/hibernate",
        {"confirm": "hibernate"},
        timeout=10,
    )
    if response.get("status") != "hibernate_scheduled":
        raise RuntimeError("Windows 에이전트가 최대절전 요청을 수락하지 않았습니다.")
    print("최대절전 명령 수락 · 오프라인 전환 확인 중", flush=True)
    elapsed = wait_for_offline(config)
    print(f"최대절전 진입 확인 · {elapsed:.1f}초", flush=True)
    return elapsed


def cycle(config: Config, settle_seconds: float) -> None:
    hibernate(config)
    print(f"S4 안정화 대기 · {settle_seconds:.0f}초", flush=True)
    time.sleep(settle_seconds)
    send_wake(config)
    print("WOL 매직 패킷 5회 전송 · API 복귀 확인 중", flush=True)
    elapsed = wait_for_online(config)
    print(f"WOL 복귀 성공 · {elapsed:.1f}초", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("cycle", "hibernate", "wake", "status"), nargs="?", default="cycle"
    )
    parser.add_argument("--settle-seconds", type=float, default=15)
    args = parser.parse_args()
    try:
        config = Config.from_env()
        if args.action == "status":
            health = remote_health(config)
            print("online" if health else "offline")
            return 0 if health else 1
        if args.action == "hibernate":
            hibernate(config)
        elif args.action == "wake":
            send_wake(config)
            elapsed = wait_for_online(config)
            print(f"WOL 복귀 성공 · {elapsed:.1f}초")
        else:
            cycle(config, max(5, args.settle_seconds))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
