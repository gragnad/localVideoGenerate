from __future__ import annotations

"""Qwen3-Omni direct-video reviewer for model benchmark runs."""

import json
from pathlib import Path
from typing import Any

import candidate_reviews
import vllm_reviewer as omni


SCORE_KEYS = (
    "prompt_adherence", "identity_consistency", "motion_physics",
    "temporal_consistency", "camera_control", "spatial_continuity",
    "audio_dialogue", "visual_quality", "vfx_quality", "narrative_causality",
)

SYSTEM_PROMPT = r"""
You are the fixed-rubric evaluator for a cross-model AI video benchmark.
Review the attached complete source video directly, not extracted still images.
You receive the canonical generation prompt, Korean intent, required events,
forbidden failures, duration, and an independent prompt-blind observation.

Mandatory prompt-compliance audit:
1. Read the complete canonical prompt before judging quality. Treat every explicit action, actor,
   object, order, camera instruction, dialogue, causal reaction, and ending state as a claim to verify.
2. Inspect the complete video from beginning through ending. Never infer an event from the prompt,
   a plausible pose, a cut, or an attractive frame. Only visible or clearly audible evidence counts.
3. Return exactly one event_check for every required event, in the same order and using the exact
   Korean requirement text. A verified event requires concrete evidence and a narrow timestamp.
4. Return exactly one forbidden_check for every forbidden failure, in the same order and using the
   exact Korean failure text. Mark absent only after checking the whole relevant timeline.
5. The contract's required_events are the minimum gate, not the whole prompt. Also report omissions
   of explicit canonical-prompt details as issues.
6. Judge prompt compliance before visual appeal. Do not decide that a video is acceptable from its
   general impression.

Evidence and verdict rules:
- The prompt is intent, never evidence. Base every judgment on visible or audible video evidence.
- Evaluate the whole timeline: beginning, middle, and end.
- Give narrow timestamps for every local event and problem.
- Mark dialogue accuracy only when audio was supplied and intelligible.
- Do not reward attractiveness when required actions, order, identity, physics, causality, or ending fail.
- Apply the same 0-5 rubric to every model: 5 fully reliable, 4 minor defects, 3 usable with clear defects,
  2 major failure, 1 mostly failed, 0 absent or contradicted.
- Use null for a score dimension genuinely not exercised by this case.
- acceptable is allowed only when every required event is verified, every forbidden failure is absent,
  prompt_adherence is at least 4, and there is no major or critical issue.
- One uncertain or unverifiable required event means at least needs_improvement.
- A contradicted required event, two or more unresolved required events, an observed forbidden failure,
  or any critical issue means reject.
- Return exactly one JSON object, with no prose outside JSON.

Allowed issue categories and subcategories:
- prompt_detail_omission: fine_detail_missing, emotion_missing, environment_reaction_missing,
  object_interaction_missing, action_order_ignored, intensity_speed_mismatch
- motion_physics: ground_contact_missing, weight_missing, friction_missing,
  collision_reaction_missing, sliding_fall_trajectory, inertia_acceleration,
  center_of_mass, over_smoothed_motion, position_jump, limb_distortion
- character_identity: face_identity, body_anatomy, species_mixing,
  costume_accessory, duplicate_missing
- scene_continuity: abrupt_transition, spatial_discontinuity, temporal_order, object_position
- camera_direction: camera_speed, framing, focus_subject, unwanted_cut
- background_props: background_change, prop_identity, prop_interaction, missing_object
- dialogue_audio: dialogue_missing, dialogue_mixed, lip_sync, voice_language, sound_effect
- visual_temporal_quality: flicker, detail_collapse, texture_crawling, blur_noise, style_drift
- vfx_effects: effect_missing, origin_position, causal_timing, effect_instability,
  subject_fusion, lighting_response, particle_flicker, identity_collapse
- scenario_comprehension: event_missing, event_order, role_binding, causal_link,
  state_persistence, ending_missing, partial_collapse
- other: other

Schema:
{
  "verdict": "acceptable|needs_improvement|reject|unrated",
  "confidence": 0.0,
  "positive_note": "Korean factual strengths",
  "overall_note": "Korean evidence-based summary",
  "scores": {
    "prompt_adherence": 0,
    "identity_consistency": 0,
    "motion_physics": 0,
    "temporal_consistency": 0,
    "camera_control": null,
    "spatial_continuity": 0,
    "audio_dialogue": null,
    "visual_quality": 0,
    "vfx_quality": null,
    "narrative_causality": null
  },
  "event_checks": [
    {"requirement_ko":"", "status":"verified|contradicted|uncertain|not_verifiable", "evidence_ko":"", "start_seconds":0.0, "end_seconds":0.0}
  ],
  "forbidden_checks": [
    {"failure_ko":"", "status":"absent|observed|uncertain", "evidence_ko":"", "start_seconds":0.0, "end_seconds":0.0}
  ],
  "issues": [
    {
      "issue_id":"ai_issue_01", "category":"other", "subcategory":"other",
      "severity":"minor|major|critical", "start_seconds":0.0, "end_seconds":0.0,
      "expected":"Korean expected behavior", "observed":"Korean direct observation",
      "difference":"Korean difference", "cause_hypothesis":"Korean cautious hypothesis",
      "suggestion":"English prompt or setting improvement"
    }
  ]
}
""".strip()


def _seconds(value: Any, duration: float) -> float | None:
    if value in (None, ""):
        return None
    try:
        return round(max(0.0, min(duration, float(value))), 3)
    except (TypeError, ValueError):
        return None


def _normalize_check_time(raw: dict[str, Any], duration: float) -> tuple[float | None, float | None]:
    start = _seconds(raw.get("start_seconds"), duration)
    end = _seconds(raw.get("end_seconds"), duration)
    if start is not None and end is not None and end < start:
        start, end = end, start
    return start, end


def _ordered_required_checks(
    payload: dict[str, Any],
    required_events: list[str],
    duration: float,
) -> list[dict[str, Any]]:
    raw_checks = [
        item for item in (payload.get("event_checks") or []) if isinstance(item, dict)
    ]
    allowed = {"verified", "contradicted", "uncertain", "not_verifiable"}
    checks: list[dict[str, Any]] = []
    unused = list(raw_checks)
    for index, requirement in enumerate(required_events):
        exact = next(
            (
                item for item in unused
                if str(item.get("requirement_ko") or "").strip() == requirement
            ),
            None,
        )
        raw = exact or {}
        if exact is not None:
            unused.remove(exact)
        status = str(raw.get("status") or "not_verifiable")
        if status not in allowed:
            status = "not_verifiable"
        evidence = str(raw.get("evidence_ko") or "").strip()
        start, end = _normalize_check_time(raw, duration)
        if status == "verified" and (not evidence or (start is None and end is None)):
            status = "uncertain"
        checks.append({
            "requirement_ko": requirement,
            "status": status,
            "evidence_ko": evidence,
            "start_seconds": start,
            "end_seconds": end,
        })
    return checks


def _ordered_forbidden_checks(
    payload: dict[str, Any],
    forbidden_failures: list[str],
    duration: float,
) -> list[dict[str, Any]]:
    raw_checks = [
        item for item in (payload.get("forbidden_checks") or []) if isinstance(item, dict)
    ]
    allowed = {"absent", "observed", "uncertain"}
    checks: list[dict[str, Any]] = []
    unused = list(raw_checks)
    for failure in forbidden_failures:
        exact = next(
            (
                item for item in unused
                if str(item.get("failure_ko") or "").strip() == failure
            ),
            None,
        )
        raw = exact or {}
        if exact is not None:
            unused.remove(exact)
        status = str(raw.get("status") or "uncertain")
        if status not in allowed:
            status = "uncertain"
        evidence = str(raw.get("evidence_ko") or "").strip()
        start, end = _normalize_check_time(raw, duration)
        if status == "observed" and not evidence:
            status = "uncertain"
        checks.append({
            "failure_ko": failure,
            "status": status,
            "evidence_ko": evidence,
            "start_seconds": start,
            "end_seconds": end,
        })
    return checks


def _normalize(
    payload: dict[str, Any],
    *,
    duration: float,
    intent_ko: str,
    required_events: list[str] | None = None,
    forbidden_failures: list[str] | None = None,
) -> dict[str, Any]:
    required_events = [str(value).strip() for value in (required_events or []) if str(value).strip()]
    forbidden_failures = [
        str(value).strip() for value in (forbidden_failures or []) if str(value).strip()
    ]
    event_checks = _ordered_required_checks(payload, required_events, duration)
    forbidden_checks = _ordered_forbidden_checks(payload, forbidden_failures, duration)

    scores: dict[str, float] = {}
    raw_scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    for key in SCORE_KEYS:
        value = raw_scores.get(key)
        if value in (None, ""):
            continue
        try:
            scores[key] = round(max(0.0, min(5.0, float(value))), 2)
        except (TypeError, ValueError):
            continue

    issues = []
    for index, raw in enumerate((payload.get("issues") or [])[:candidate_reviews.MAX_ISSUES], 1):
        if not isinstance(raw, dict):
            continue
        category = str(raw.get("category") or "other")
        if category not in candidate_reviews.CATEGORIES:
            category = "other"
        severity = str(raw.get("severity") or "major")
        if severity not in candidate_reviews.SEVERITIES:
            severity = "major"
        start, end = _normalize_check_time(raw, duration)
        observed = str(
            raw.get("observed") or raw.get("evidence_ko")
            or "영상에서 의도와 다른 결과가 관찰됨"
        ).strip()
        issues.append({
            "issue_id": str(raw.get("issue_id") or f"ai_issue_{index:02d}"),
            "category": category,
            "subcategory": str(raw.get("subcategory") or "other"),
            "severity": severity,
            "start_seconds": start,
            "end_seconds": end,
            "expected": str(raw.get("expected") or intent_ko).strip(),
            "observed": observed,
            "difference": str(raw.get("difference") or "").strip(),
            "cause_hypothesis": str(raw.get("cause_hypothesis") or "").strip(),
            "suggestion": str(raw.get("suggestion") or "").strip(),
        })

    existing_expected = {str(item.get("expected") or "").strip() for item in issues}
    for check in event_checks:
        if check["status"] == "verified" or check["requirement_ko"] in existing_expected:
            continue
        issues.append({
            "issue_id": f"required_event_{len(issues) + 1:02d}",
            "category": "scenario_comprehension",
            "subcategory": "event_missing",
            "severity": "major",
            "start_seconds": check["start_seconds"],
            "end_seconds": check["end_seconds"],
            "expected": check["requirement_ko"],
            "observed": check["evidence_ko"] or "영상 근거가 확인되지 않음",
            "difference": f"필수 사건 판정: {check['status']}",
            "cause_hypothesis": "",
            "suggestion": "Make this required action visually explicit with a clear subject, action, timing, and end state.",
        })
        if len(issues) >= candidate_reviews.MAX_ISSUES:
            break

    unresolved = [item for item in event_checks if item["status"] != "verified"]
    contradicted = [item for item in event_checks if item["status"] == "contradicted"]
    observed_forbidden = [item for item in forbidden_checks if item["status"] == "observed"]
    uncertain_forbidden = [item for item in forbidden_checks if item["status"] == "uncertain"]

    if observed_forbidden:
        scores["prompt_adherence"] = min(scores.get("prompt_adherence", 5.0), 1.0)
    elif contradicted or len(unresolved) >= 2:
        scores["prompt_adherence"] = min(scores.get("prompt_adherence", 5.0), 2.0)
    elif unresolved or uncertain_forbidden:
        scores["prompt_adherence"] = min(scores.get("prompt_adherence", 5.0), 3.0)

    critical_issue = any(item["severity"] == "critical" for item in issues)
    major_issue = any(item["severity"] == "major" for item in issues)
    prompt_score = scores.get("prompt_adherence")
    hard_reject = bool(
        critical_issue or contradicted or len(unresolved) >= 2 or observed_forbidden
    )
    gate_passed = bool(
        not unresolved
        and not observed_forbidden
        and not uncertain_forbidden
        and prompt_score is not None
        and prompt_score >= 4.0
        and not major_issue
        and not critical_issue
    )
    if hard_reject:
        verdict = "reject"
    elif gate_passed:
        verdict = "acceptable"
    else:
        verdict = "needs_improvement"

    summary = (
        f"필수 사건 {len(event_checks) - len(unresolved)}/{len(event_checks)} 확인"
        f" · 금지 실패 관찰 {len(observed_forbidden)}건"
        f" · 금지 실패 불확실 {len(uncertain_forbidden)}건"
    )
    overall_note = str(payload.get("overall_note") or "").strip()
    overall_note = f"{overall_note} | 엄격 게이트: {summary}" if overall_note else f"엄격 게이트: {summary}"
    return {
        "verdict": verdict,
        "positive_note": str(payload.get("positive_note") or "").strip(),
        "overall_note": overall_note,
        "scores": scores,
        "issues": issues[:candidate_reviews.MAX_ISSUES],
        "event_checks": event_checks,
        "forbidden_checks": forbidden_checks,
        "enforcement": {
            "rubric_version": "strict_prompt_compliance_v2",
            "gate_passed": gate_passed,
            "required_verified": len(event_checks) - len(unresolved),
            "required_total": len(event_checks),
            "required_unresolved": len(unresolved),
            "required_contradicted": len(contradicted),
            "forbidden_observed": len(observed_forbidden),
            "forbidden_uncertain": len(uncertain_forbidden),
        },
    }


def review_benchmark_video(
    *, video_path: Path, request: dict[str, Any], batch_id: str, job_id: str,
) -> dict[str, Any]:
    if not video_path.is_file():
        raise FileNotFoundError(f"검수 영상 파일이 없습니다: {video_path}")
    probe = omni.probe_video(video_path)
    if not probe.get("has_video"):
        raise omni.VLLMReviewError(f"검수 파일에 영상 스트림이 없습니다: {video_path}")
    duration = float(probe.get("duration_seconds") or request.get("settings", {}).get("duration_seconds") or 0)
    use_audio = omni._should_use_audio(probe)
    probe["audio_reviewed"] = use_audio
    video_data_url, video_metadata = omni._direct_video_data_url(video_path)
    audio_data_url = None
    if use_audio:
        audio_data_url, audio_metadata = omni._direct_audio_data_url(video_path)
        video_metadata["audio_input"] = audio_metadata
    observation = None
    observation_raw = ""
    if omni.VLLM_VIDEO_REVIEW_TWO_PASS:
        observed, _message, observation_raw = omni._response_json(
            model=omni._model_id(), system_prompt=omni.OBSERVATION_SYSTEM_PROMPT,
            required_keys={"observed_summary_ko", "timeline", "audio_observation"},
            user_text="Observe this complete benchmark video without seeing its intended prompt.",
            video_data_url=video_data_url, audio_data_url=audio_data_url,
            video_metadata=video_metadata,
        )
        observation = omni._normalize_observation(
            observed, duration_seconds=duration, audio_reviewed=use_audio,
        )
    context = {
        "case_title": request.get("case_title"),
        "canonical_prompt_en": request.get("canonical_prompt"),
        "intent_ko": request.get("review_intent_ko"),
        "contract": request.get("benchmark_contract") or {},
        "duration_seconds": duration,
        "fps": request.get("settings", {}).get("fps"),
        "audio_reviewed": use_audio,
        "independent_observation": observation,
    }
    payload, _message, raw = omni._response_json(
        model=omni._model_id(), system_prompt=SYSTEM_PROMPT,
        required_keys={
            "verdict", "positive_note", "overall_note", "scores", "issues",
            "event_checks", "forbidden_checks",
        },
        user_text="Evaluate this benchmark video with the fixed rubric.\n" + json.dumps(context, ensure_ascii=False, separators=(",", ":")),
        video_data_url=video_data_url, audio_data_url=audio_data_url,
        video_metadata=video_metadata,
    )
    contract = request.get("benchmark_contract") or {}
    review = _normalize(
        payload,
        duration=duration,
        intent_ko=str(request.get("review_intent_ko") or ""),
        required_events=list(contract.get("required_events") or []),
        forbidden_failures=list(contract.get("forbidden_failures") or []),
    )
    return {
        "review": review,
        "confidence": max(0.0, min(1.0, float(payload.get("confidence") or 0))),
        "event_checks": review["event_checks"],
        "forbidden_checks": review["forbidden_checks"],
        "enforcement": review["enforcement"],
        "model": omni._model_id(),
        "review_mode": "qwen_omni_direct_video_strict_prompt_compliance_v2",
        "rubric_version": "strict_prompt_compliance_v2",
        "duration_seconds": round(duration, 3),
        "media_probe": probe,
        "observation": observation,
        "raw_observation_response": observation_raw,
        "raw_response": raw,
        "batch_id": batch_id,
        "job_id": job_id,
    }
