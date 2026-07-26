from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from engine_switch import engine_snapshot
from batch_manager import find_batches_by_status, load_open_batch
from job_queue import read_json


HOME = Path.home()
ENGINE_ROOT = Path(os.environ.get("VIDEO_ENGINE_ROOT", HOME / "local-ai/video-engine"))
JOBS_ROOT = ENGINE_ROOT / "jobs"
WORKER_STATUS = ENGINE_ROOT / "worker_status.json"
COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")


def print_json(title: str, payload: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


worker = read_json(WORKER_STATUS, {}) or {}
print_json("worker_status", worker)
print_json("engine_snapshot", engine_snapshot())

batch = load_open_batch(ENGINE_ROOT)
print_json("open_batch", batch or {"open_batch": None})

pipeline_batches = find_batches_by_status(
    ENGINE_ROOT,
    {
        "ready_for_review_preparation",
        "contact_sheet_queued",
        "ready_for_ai_review",
        "contact_sheet_failed",
        "contact_sheet_preparation_failed",
        "switching_to_vllm",
        "ai_reviewing",
        "review_completed",
        "review_complete_needs_modification",
        "retake_queued",
        "retake_failed",
        "modification_completed",
        "modification_limit_reached",
        "modification_preparation_failed",
        "manual_review_required",
        "review_input_failed",
        "ai_review_failed",
        "engine_switch_failed",
    },
    limit=20,
)
print_json("pipeline_batches", pipeline_batches)

if batch:
    statuses = {}
    for job_id in batch.get("generation_job_ids") or []:
        statuses[job_id] = read_json(JOBS_ROOT / job_id / "status.json", {}) or {}
    print_json("generation_job_statuses", statuses)

try:
    response = requests.get(f"{COMFY_URL}/queue", timeout=10)
    response.raise_for_status()
    print_json("comfy_queue", response.json())
except Exception as exc:
    print_json(
        "comfy_queue_error",
        {"error": f"{type(exc).__name__}: {exc}", "url": f"{COMFY_URL}/queue"},
    )
