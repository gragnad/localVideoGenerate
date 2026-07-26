#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


HOME = Path.home()
ENV_PATH = HOME / ".config/ltx-video-ui/ui.env"


def load_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {'"', "'"}
        ):
            value = value[1:-1]
        result[key.strip()] = value
    return result


def command(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    text = "\n".join(
        part.strip()
        for part in (proc.stdout, proc.stderr)
        if part and part.strip()
    )
    return proc.returncode, text


def http_ok(url: str) -> bool:
    try:
        with urlopen(url, timeout=3) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


env = load_env(ENV_PATH)
engine_root = Path(
    env.get("VIDEO_ENGINE_ROOT", str(HOME / "local-ai/video-engine"))
).expanduser()
review_template = Path(
    env.get(
        "LTX_REVIEW_WORKFLOW_TEMPLATE",
        str(
            HOME
            / "ai-workspace/apps/ComfyUI/user/default/workflows"
            / "(CH)Video_ContactSheet_API_fixed.json"
        ),
    )
).expanduser()

checks: list[tuple[str, bool, str]] = []

checks.append(("ui.env", ENV_PATH.is_file(), str(ENV_PATH)))
checks.append(("video engine", engine_root.is_dir(), str(engine_root)))
checks.append(
    (
        "pipeline v1.7 worker",
        (engine_root / "worker.py").is_file()
        and '"1.7.0"' in (engine_root / "worker.py").read_text(
            encoding="utf-8", errors="ignore"
        ),
        str(engine_root / "worker.py"),
    )
)
checks.append(
    (
        "Qwen bridge engine_switch",
        (engine_root / "engine_switch.py").is_file()
        and "VLLM_START_TIMEOUT + 60.0"
        in (engine_root / "engine_switch.py").read_text(
            encoding="utf-8", errors="ignore"
        ),
        str(engine_root / "engine_switch.py"),
    )
)
checks.append(
    (
        "Qwen bridge reviewer",
        (engine_root / "vllm_reviewer.py").is_file()
        and 'message.get("reasoning")'
        in (engine_root / "vllm_reviewer.py").read_text(
            encoding="utf-8", errors="ignore"
        ),
        str(engine_root / "vllm_reviewer.py"),
    )
)
checks.append(
    (
        "Contact Sheet workflow",
        review_template.is_file(),
        str(review_template),
    )
)

for script_key in (
    "COMFY_START_SCRIPT",
    "COMFY_STOP_SCRIPT",
    "VLLM_START_SCRIPT",
    "VLLM_STOP_SCRIPT",
):
    default_name = {
        "COMFY_START_SCRIPT": "ai-start-comfy",
        "COMFY_STOP_SCRIPT": "ai-stop-comfy",
        "VLLM_START_SCRIPT": "ai-start-vllm",
        "VLLM_STOP_SCRIPT": "ai-stop-vllm",
    }[script_key]
    path = Path(env.get(script_key, str(HOME / "bin" / default_name))).expanduser()
    checks.append(
        (
            script_key,
            path.is_file() and os.access(path, os.X_OK),
            str(path),
        )
    )

code, worker_status = command(
    "systemctl",
    "--user",
    "is-active",
    "ltx-video-worker.service",
)
checks.append(
    (
        "ltx-video-worker.service",
        code == 0 and worker_status.strip() == "active",
        worker_status or "inactive",
    )
)

code, ui_status = command(
    "systemctl",
    "--user",
    "is-active",
    "ltx-video-ui.service",
)
checks.append(
    (
        "ltx-video-ui.service",
        code == 0 and ui_status.strip() == "active",
        ui_status or "inactive",
    )
)

comfy_url = env.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
vllm_url = env.get("VLLM_URL", "http://127.0.0.1:8091").rstrip("/")
comfy_ready = http_ok(f"{comfy_url}/system_stats")
vllm_ready = http_ok(f"{vllm_url}/v1/models")

print("=== LTX → Contact Sheet → Qwen3-Omni preflight ===")
failed = 0
for label, ok, detail in checks:
    mark = "OK" if ok else "FAIL"
    print(f"[{mark:4}] {label}: {detail}")
    if not ok:
        failed += 1

print()
print(f"ComfyUI ready : {comfy_ready}")
print(f"vLLM ready    : {vllm_ready}")
if comfy_ready and vllm_ready:
    print("경고: ComfyUI와 vLLM이 동시에 응답합니다.")
elif comfy_ready:
    print("현재 생성 단계 준비 상태입니다.")
elif vllm_ready:
    print("현재 검수 단계 상태입니다. 새 생성 전에는 vLLM을 종료하고 ComfyUI를 시작하세요.")
else:
    print("현재 활성 엔진이 없습니다.")

print()
print("핵심 설정:")
for key in (
    "LTX_REVIEW_WORKFLOW_TEMPLATE",
    "COMFY_STOP_SCRIPT",
    "VLLM_START_SCRIPT",
    "VLLM_MODEL",
    "VLLM_START_TIMEOUT",
    "VLLM_REVIEW_TIMEOUT",
):
    print(f"  {key}={env.get(key, '')}")

raise SystemExit(1 if failed else 0)
