from __future__ import annotations

"""Structured human reviews for generated video candidates."""

import hashlib
import json
from pathlib import Path
from typing import Any

from job_queue import atomic_write_json, now_iso, read_json


CATEGORIES = {
    "prompt_detail_omission",
    "motion_physics",
    "character_identity",
    "scene_continuity",
    "camera_direction",
    "background_props",
    "dialogue_audio",
    "visual_temporal_quality",
    "vfx_effects",
    "scenario_comprehension",
    "other",
}
SEVERITIES = {"minor", "major", "critical"}
VERDICTS = {"unrated", "acceptable", "needs_improvement", "reject"}
MAX_ISSUES = 30
MAX_TEXT = 4000


def _safe_id(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result or Path(result).name != result or result in {".", ".."}:
        raise ValueError(f"허용되지 않는 {label}입니다.")
    return result


def review_path(root: Path, candidate_set_id: str, job_id: str) -> Path:
    set_id = _safe_id(candidate_set_id, "후보군 ID")
    candidate_job_id = _safe_id(job_id, "작업 ID")
    return root / "runtime/candidate_reviews/entries" / f"{set_id}__{candidate_job_id}.json"


def _text(value: Any, label: str, *, required: bool = False) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"{label}을(를) 입력하세요.")
    if len(result) > MAX_TEXT:
        raise ValueError(f"{label}은(는) {MAX_TEXT}자 이하여야 합니다.")
    return result


def expected_default_ko(request: dict[str, Any]) -> str:
    translated = _text(request.get("review_intent_ko"), "한국어 프롬프트 의도")
    if translated:
        return translated
    source = _text(request.get("source_scene_refs"), "한국어 장면 의도")
    if "—" in source:
        source = source.split("—", 1)[1].strip()
    return source


def _seconds(value: Any, label: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}은(는) 숫자여야 합니다.") from exc
    if result < 0 or result > 3600:
        raise ValueError(f"{label}은(는) 0~3600초 범위여야 합니다.")
    return round(result, 3)


def normalize_issue(raw: dict[str, Any], index: int) -> dict[str, Any]:
    category = str(raw.get("category") or "").strip()
    if category not in CATEGORIES:
        raise ValueError(f"문제 {index}의 문제 유형이 올바르지 않습니다.")
    severity = str(raw.get("severity") or "major").strip()
    if severity not in SEVERITIES:
        raise ValueError(f"문제 {index}의 심각도가 올바르지 않습니다.")
    start = _seconds(raw.get("start_seconds"), f"문제 {index} 시작 시간")
    end = _seconds(raw.get("end_seconds"), f"문제 {index} 종료 시간")
    if start is not None and end is not None and end < start:
        raise ValueError(f"문제 {index}의 종료 시간은 시작 시간보다 빠를 수 없습니다.")
    return {
        "issue_id": _text(raw.get("issue_id"), f"문제 {index} ID") or f"issue_{index:02d}",
        "category": category,
        "subcategory": _text(raw.get("subcategory"), f"문제 {index} 세부 유형", required=True),
        "severity": severity,
        "start_seconds": start,
        "end_seconds": end,
        "expected": _text(raw.get("expected"), f"문제 {index} 의도한 표현", required=True),
        "observed": _text(raw.get("observed"), f"문제 {index} 실제 출력", required=True),
        "difference": _text(raw.get("difference"), f"문제 {index} 차이 설명"),
        "cause_hypothesis": _text(raw.get("cause_hypothesis"), f"문제 {index} 원인 추정"),
        "suggestion": _text(raw.get("suggestion"), f"문제 {index} 개선 제안"),
    }


def normalize_review(data: dict[str, Any]) -> dict[str, Any]:
    verdict = str(data.get("verdict") or "unrated").strip()
    if verdict not in VERDICTS:
        raise ValueError("후보 종합 판단이 올바르지 않습니다.")
    raw_issues = data.get("issues") or []
    if not isinstance(raw_issues, list):
        raise ValueError("문제 목록 형식이 올바르지 않습니다.")
    if len(raw_issues) > MAX_ISSUES:
        raise ValueError(f"후보 하나에는 문제를 최대 {MAX_ISSUES}개까지 저장할 수 있습니다.")
    issues = [normalize_issue(dict(item or {}), index) for index, item in enumerate(raw_issues, 1)]
    return {
        "verdict": verdict,
        "positive_note": _text(data.get("positive_note"), "잘된 부분"),
        "overall_note": _text(data.get("overall_note"), "종합 메모"),
        "issues": issues,
    }


def _workflow_sha256(job_dir: Path) -> str:
    for name in ("workflow_api_runtime.json", "selected_workflow_api.json"):
        path = job_dir / name
        if path.is_file():
            return hashlib.sha256(path.read_bytes()).hexdigest()
    return ""


def generation_snapshot(request: dict[str, Any], job_dir: Path) -> dict[str, Any]:
    segments = list(request.get("segments") or [])
    relay = list(request.get("relay_segments") or [])
    return {
        "workflow_kind": str(request.get("workflow_kind") or ""),
        "workflow_filename": str(request.get("workflow_filename") or ""),
        "workflow_sha256": _workflow_sha256(job_dir),
        "prompt_strategy": str(request.get("prompt_strategy") or ""),
        "seed": request.get("seed"),
        "seed_mode": str(request.get("seed_mode") or ""),
        "resolution": dict(request.get("resolution") or {}),
        "fps": request.get("fps"),
        "review_intent_ko": expected_default_ko(request),
        "global_prompt": str(request.get("global_prompt") or ""),
        "segments": [
            {
                "order": item.get("order"),
                "prompt": str(item.get("prompt") or ""),
                "seconds": item.get("seconds"),
                "sha256": str(item.get("sha256") or ""),
                "role": str(item.get("role") or ""),
                "slot": item.get("slot"),
            }
            for item in segments
        ],
        "relay_segments": [
            {
                "order": item.get("order"),
                "prompt": str(item.get("prompt") or ""),
                "seconds": item.get("seconds"),
            }
            for item in relay
        ],
    }


def load_review(root: Path, candidate_set_id: str, job_id: str) -> dict[str, Any] | None:
    payload = read_json(review_path(root, candidate_set_id, job_id), {}) or {}
    return payload or None


def save_review(
    root: Path,
    *,
    candidate_set_id: str,
    job_id: str,
    candidate_index: int | None,
    request: dict[str, Any],
    job_dir: Path,
    data: dict[str, Any],
) -> dict[str, Any]:
    normalized = normalize_review(data)
    existing = load_review(root, candidate_set_id, job_id)
    timestamp = now_iso()
    payload = {
        "schema_version": 1,
        "review_id": f"{_safe_id(candidate_set_id, '후보군 ID')}__{_safe_id(job_id, '작업 ID')}",
        "candidate_set_id": candidate_set_id,
        "job_id": job_id,
        "candidate_index": candidate_index,
        "created_at": str((existing or {}).get("created_at") or timestamp),
        "updated_at": timestamp,
        "revision": int((existing or {}).get("revision") or 0) + 1,
        **normalized,
        "generation_snapshot": generation_snapshot(request, job_dir),
    }
    path = review_path(root, candidate_set_id, job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, payload)
    return payload


def review_summary(review: dict[str, Any]) -> dict[str, Any]:
    issues = list(review.get("issues") or [])
    counts: dict[str, int] = {}
    for issue in issues:
        category = str(issue.get("category") or "other")
        counts[category] = counts.get(category, 0) + 1
    return {
        "review_id": str(review.get("review_id") or ""),
        "verdict": str(review.get("verdict") or "unrated"),
        "issue_count": len(issues),
        "severity_counts": {
            level: sum(1 for issue in issues if issue.get("severity") == level)
            for level in ("minor", "major", "critical")
        },
        "category_counts": counts,
        "has_positive_note": bool(str(review.get("positive_note") or "").strip()),
        "revision": int(review.get("revision") or 1),
        "updated_at": str(review.get("updated_at") or ""),
    }
