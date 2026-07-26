#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import urlopen


HOME = Path.home()
ENGINE_ROOT = Path(
    os.environ.get("VIDEO_ENGINE_ROOT", HOME / "local-ai/video-engine")
)
BATCH_ROOT = ENGINE_ROOT / "runtime/batches"
ENGINE_STATE = ENGINE_ROOT / "runtime/engine_state.json"


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def http_ok(url: str) -> bool:
    try:
        with urlopen(url, timeout=3) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


items = []
if BATCH_ROOT.is_dir():
    for path in BATCH_ROOT.glob("*/batch.json"):
        payload = load(path)
        if isinstance(payload, dict):
            items.append((str(payload.get("created_at") or ""), path, payload))

print("=== engine ===")
print(f"ComfyUI ready: {http_ok('http://127.0.0.1:8188/system_stats')}")
print(f"vLLM ready   : {http_ok('http://127.0.0.1:8091/v1/models')}")
print(f"state file   : {json.dumps(load(ENGINE_STATE), ensure_ascii=False, indent=2)}")

if not items:
    raise SystemExit(0)

_, path, batch = sorted(items)[-1]
print()
print("=== latest batch ===")
for key in (
    "batch_id",
    "status",
    "stage",
    "next_stage",
    "message",
    "post_review_engine_return",
    "post_review_target_engine",
    "post_review_engine",
    "comfy_restored_at",
    "post_review_engine_error",
):
    print(f"{key}: {batch.get(key)}")
print(f"batch file: {path}")
