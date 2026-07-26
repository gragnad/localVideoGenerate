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


if not BATCH_ROOT.is_dir():
    raise SystemExit(f"배치 디렉터리가 없습니다: {BATCH_ROOT}")

items = []
for path in BATCH_ROOT.glob("*/batch.json"):
    payload = load(path)
    if not isinstance(payload, dict):
        continue
    items.append((str(payload.get("created_at") or ""), path, payload))

if not items:
    raise SystemExit("배치 기록이 없습니다.")

_, batch_path, batch = sorted(items)[-1]
batch_id = str(batch.get("batch_id") or batch_path.parent.name)

print("=== latest batch ===")
for key in (
    "batch_id",
    "pipeline_version",
    "status",
    "stage",
    "next_stage",
    "message",
    "ai_review_total",
    "ai_review_rejected",
    "ai_review_report_path",
):
    print(f"{key}: {batch.get(key)}")

report_path_value = batch.get("ai_review_report_path")
if report_path_value:
    report_path = Path(str(report_path_value))
else:
    report_path = batch_path.parent / "ai_review_reports.json"

print()
print(f"batch file : {batch_path}")
print(f"report file: {report_path}")

report = load(report_path)
if not isinstance(report, dict):
    print("아직 AI 검수 보고서가 없습니다.")
    raise SystemExit(0)

print()
print("=== reports ===")
for item in report.get("reports") or []:
    print(
        json.dumps(
            {
                "job_id": item.get("job_id"),
                "accepted": item.get("accepted"),
                "confidence": item.get("confidence"),
                "summary_ko": item.get("summary_ko"),
                "recommended_action": item.get("recommended_action"),
                "issue_count": len(item.get("issues") or []),
                "contact_sheet_path": item.get("contact_sheet_path"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

errors = report.get("errors") or []
if errors:
    print()
    print("=== errors ===")
    print(json.dumps(errors, ensure_ascii=False, indent=2))
