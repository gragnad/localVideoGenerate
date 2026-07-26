from __future__ import annotations

from typing import Any


def retake_issues(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        issue
        for issue in report.get("issues") or []
        if isinstance(issue, dict)
        and str(issue.get("recommended_workflow") or "") == "retake"
    ]


def covered_seconds(report: dict[str, Any]) -> float:
    duration = max(0.0, float(report.get("duration_seconds") or 0.0))
    ranges = []
    for issue in retake_issues(report):
        start = max(0.0, float(issue.get("start_seconds") or 0.0))
        end = min(duration, float(issue.get("end_seconds") or 0.0))
        if end > start:
            ranges.append((start, end))
    ranges.sort()
    merged: list[list[float]] = []
    for start, end in ranges:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start for start, end in merged)


def recommend_correction_mode(report: dict[str, Any]) -> str:
    """Use a partial Retake only for one localized correction."""
    issues = retake_issues(report)
    duration = max(0.0, float(report.get("duration_seconds") or 0.0))
    coverage_ratio = covered_seconds(report) / duration if duration else 0.0

    # Multiple independently reported defects need competing corrections.  In
    # that case a fresh generation from the original images is more reliable
    # than rewriting a source video in place.
    if len(issues) != 1 or coverage_ratio >= 0.45:
        return "full_regeneration"
    return "partial_retake"


def correction_text(
    report: dict[str, Any],
    *,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
) -> str:
    corrections: list[str] = []
    for issue in retake_issues(report):
        if start_seconds is not None and end_seconds is not None:
            issue_start = float(issue.get("start_seconds") or 0.0)
            issue_end = float(issue.get("end_seconds") or 0.0)
            if issue_end <= start_seconds or issue_start >= end_seconds:
                continue
        prompt = str(issue.get("retake_prompt_en") or "").strip()
        if prompt and prompt not in corrections:
            corrections.append(prompt)
    if not corrections:
        summary = str(report.get("summary_ko") or "").strip()
        if summary:
            corrections.append(
                "Correct the quality-control failure described as: " + summary
            )
    return "\n".join(f"- {item}" for item in corrections)


def _overlapping_segments(
    original_request: dict[str, Any],
    start_seconds: float,
    end_seconds: float,
) -> list[tuple[int, float, float, dict[str, Any]]]:
    cursor = 0.0
    selected: list[tuple[int, float, float, dict[str, Any]]] = []
    for index, segment in enumerate(original_request.get("segments") or [], start=1):
        duration = max(0.0, float(segment.get("seconds") or 0.0))
        segment_start, segment_end = cursor, cursor + duration
        cursor = segment_end
        if segment_end > start_seconds and segment_start < end_seconds:
            selected.append((index, segment_start, segment_end, segment))
    return selected


def build_retake_prompt(
    report: dict[str, Any],
    original_request: dict[str, Any],
    *,
    start_seconds: float,
    end_seconds: float,
    correction_mode: str = "partial_retake",
    user_instruction: str = "",
) -> str:
    """Build the exact, auditable prompt used by automatic and manual retakes."""
    duration = max(
        float(report.get("duration_seconds") or 0.0),
        sum(float(item.get("seconds") or 0.0) for item in original_request.get("segments") or []),
    )
    if correction_mode == "full_regeneration":
        start_seconds, end_seconds = 0.0, duration
    start_seconds = max(0.0, float(start_seconds))
    end_seconds = max(start_seconds, float(end_seconds))

    overlapping = _overlapping_segments(original_request, start_seconds, end_seconds)
    relevant_issues = []
    for issue in retake_issues(report):
        issue_start = float(issue.get("start_seconds") or 0.0)
        issue_end = float(issue.get("end_seconds") or 0.0)
        if correction_mode == "full_regeneration" or (
            issue_end > start_seconds and issue_start < end_seconds
        ):
            relevant_issues.append(issue)

    lines = [
        "QUALITY-CONTROL RETAKE SPECIFICATION (follow exactly)",
        f"MODE: {'FULL REGENERATION' if correction_mode == 'full_regeneration' else 'PARTIAL RETAKE'}",
        f"TARGET SOURCE-TIMELINE WINDOW: {start_seconds:.3f}s to {end_seconds:.3f}s",
        "",
        "ORIGINAL REQUIREMENTS FOR THE TARGET WINDOW:",
    ]
    global_prompt = str(original_request.get("global_prompt") or "").strip()
    if global_prompt:
        lines.append(f"- Global requirement: {global_prompt}")
    for index, segment_start, segment_end, segment in overlapping:
        prompt = str(segment.get("prompt") or "").strip()
        lines.append(
            f"- Scene {index} ({segment_start:.3f}s–{segment_end:.3f}s): "
            + (prompt or "Preserve the original scene content and continuity.")
        )

    lines.extend(["", "OBSERVED FAILURES AND EVIDENCE:"])
    if relevant_issues:
        for issue in relevant_issues:
            lines.append(
                "- [{severity}/{kind}] {start:.3f}s–{end:.3f}s: {evidence}".format(
                    severity=issue.get("severity") or "unspecified",
                    kind=issue.get("type") or "quality_failure",
                    start=float(issue.get("start_seconds") or 0.0),
                    end=float(issue.get("end_seconds") or 0.0),
                    evidence=str(issue.get("evidence_ko") or issue.get("description_ko") or "검수 실패 근거 미기록").strip(),
                )
            )
    else:
        lines.append("- No timestamped automated issue overlaps this manually selected window.")

    lines.extend(["", "MANDATORY CORRECTIONS:"])
    corrections = correction_text(
        report,
        start_seconds=None if correction_mode == "full_regeneration" else start_seconds,
        end_seconds=None if correction_mode == "full_regeneration" else end_seconds,
    )
    lines.append(corrections or "- Correct the visible motion, continuity, anatomy, and prompt-compliance defects in the target window.")
    if user_instruction.strip():
        lines.append(f"- USER-DIRECTED CORRECTION: {user_instruction.strip()}")

    lines.extend(
        [
            "",
            "PRESERVATION AND ACCEPTANCE CONSTRAINTS:",
            "- Preserve character identity, costume, environment, lighting, camera direction, and temporal continuity unless a listed correction explicitly requires a change.",
            "- Keep motion physically continuous at both boundaries; no pose jump, morphing, teleportation, sudden speed change, or new unwanted object/text.",
            "- Any spoken dialogue must be natural Korean only. Do not add English speech, subtitles, captions, or on-screen text unless explicitly required by the original prompt.",
        ]
    )
    if correction_mode == "partial_retake":
        lines.append("- Modify only the target window and preserve all source-video frames outside it.")
    lines.append("- The result must satisfy both the original requirements and every mandatory correction above.")
    return "\n".join(lines).strip()


def select_retake_window(
    report: dict[str, Any],
) -> tuple[float, float, float, dict[str, Any]]:
    """Choose one conservative retake window, merging nearby QC failures."""
    duration = float(report.get("duration_seconds") or 0.0)
    severity_rank = {"blocking": 0, "major": 1, "minor": 2, "advisory": 3}
    candidates: list[dict[str, Any]] = []
    for issue in retake_issues(report):
        start = max(0.0, float(issue.get("start_seconds") or 0.0))
        end = min(duration, float(issue.get("end_seconds") or 0.0))
        if end <= start:
            continue
        candidates.append({"start": start, "end": end, "issue": issue})
    if not candidates:
        raise ValueError("시간 구간이 지정된 Retake 이슈가 없습니다.")

    # Adjacent failures are one continuity problem in practice. Splitting them
    # causes the first repair to introduce a seam immediately before the next one.
    candidates.sort(key=lambda item: (item["start"], item["end"]))
    clusters: list[list[dict[str, Any]]] = []
    for item in candidates:
        if not clusters or item["start"] > max(x["end"] for x in clusters[-1]) + 0.75:
            clusters.append([item])
        else:
            clusters[-1].append(item)

    def cluster_key(cluster: list[dict[str, Any]]) -> tuple[float, float, float, float]:
        issues = [item["issue"] for item in cluster]
        return (
            min(severity_rank.get(str(issue.get("severity") or "advisory"), 3) for issue in issues),
            -max(float(issue.get("retake_strength") or 1.0) for issue in issues),
            -sum(item["end"] - item["start"] for item in cluster),
            min(item["start"] for item in cluster),
        )

    selected = min(clusters, key=cluster_key)
    start = max(0.0, min(item["start"] for item in selected) - 0.25)
    end = min(duration, max(item["end"] for item in selected) + 0.25)
    if duration > 0 and end - start >= duration * 0.8:
        raise ValueError(
            "검수 이슈 범위가 영상 대부분을 차지해 부분 Retake로 처리할 수 없습니다."
        )
    issues = [item["issue"] for item in selected]
    primary = dict(min(
        issues,
        key=lambda issue: (
            severity_rank.get(str(issue.get("severity") or "advisory"), 3),
            -float(issue.get("retake_strength") or 1.0),
        ),
    ))
    primary["clustered_issues"] = issues
    primary["cluster_start_seconds"] = start
    primary["cluster_end_seconds"] = end
    return (
        start,
        end,
        max(0.0, min(1.0, max(float(issue.get("retake_strength") or 1.0) for issue in issues))),
        primary,
    )
