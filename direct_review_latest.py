#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


HOME = Path.home()
ENGINE_ROOT = Path(
    os.environ.get("VIDEO_ENGINE_ROOT", HOME / "local-ai/video-engine")
)
BATCH_ROOT = ENGINE_ROOT / "runtime/batches"


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


items = []
for path in BATCH_ROOT.glob("*/batch.json"):
    payload = load(path)
    if isinstance(payload, dict):
        items.append((str(payload.get("created_at") or ""), path, payload))

if not items:
    raise SystemExit("배치 기록이 없습니다.")

_, batch_path, batch = sorted(items)[-1]
print("=== latest direct-video batch ===")
for key in (
    "batch_id",
    "pipeline_version",
    "status",
    "stage",
    "next_stage",
    "review_mode",
    "message",
    "ai_review_total",
    "ai_review_rejected",
    "post_review_engine_return",
    "post_review_engine",
):
    print(f"{key}: {batch.get(key)}")

report_path = Path(
    str(
        batch.get("ai_review_report_path")
        or batch_path.parent / "ai_review_reports.json"
    )
)
print(f"report: {report_path}")

aggregate = load(report_path)
if not isinstance(aggregate, dict):
    raise SystemExit(0)

for report in aggregate.get("reports") or []:
    print()
    print(
        json.dumps(
            {
                "job_id": report.get("job_id"),
                "review_mode": report.get("review_mode"),
                "accepted": report.get("accepted"),
                "confidence": report.get("confidence"),
                "summary_ko": report.get("summary_ko"),
                "recommended_action": report.get("recommended_action"),
                "issue_count": len(report.get("issues") or []),
                "video_local_path": report.get("video_local_path"),
                "audio_reviewed": (
                    report.get("media_probe") or {}
                ).get("audio_reviewed"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
