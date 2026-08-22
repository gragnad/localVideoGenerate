from __future__ import annotations

"""Shared validation contract for human and AI model-test reviews."""

from typing import Any


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


def _text(value: Any, label: str, *, required: bool = False) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"{label}을(를) 입력하세요.")
    if len(result) > MAX_TEXT:
        raise ValueError(f"{label}은(는) {MAX_TEXT}자 이하여야 합니다.")
    return result


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
        raise ValueError("리뷰 종합 판단이 올바르지 않습니다.")
    raw_issues = data.get("issues") or []
    if not isinstance(raw_issues, list):
        raise ValueError("문제 목록 형식이 올바르지 않습니다.")
    if len(raw_issues) > MAX_ISSUES:
        raise ValueError(f"리뷰 하나에는 문제를 최대 {MAX_ISSUES}개까지 저장할 수 있습니다.")
    return {
        "verdict": verdict,
        "positive_note": _text(data.get("positive_note"), "잘된 부분"),
        "overall_note": _text(data.get("overall_note"), "종합 메모"),
        "issues": [
            normalize_issue(dict(item or {}), index)
            for index, item in enumerate(raw_issues, 1)
        ],
    }
