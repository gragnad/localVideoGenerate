from __future__ import annotations

"""Qwen3.8 visual direct-video reviewer for production candidate selection."""

import json
import re
from pathlib import Path
from typing import Any

import h3_prompt_projects
import model_test_r2v_ai_reviewer as r2v_review
import vllm_reviewer as omni


REVIEW_MODE = "qwen38_story_continuity_visual_v3"
RUBRIC_VERSION = "candidate_story_continuity_v3"
SCORE_KEYS = (
    "scenario_realization",
    "incoming_continuity",
    "outgoing_continuity",
    "causal_readability",
    "continuity_stability",
)

SYSTEM_PROMPT = """
You are a story-direction and clip-continuity reviewer for an episodic animated production.
Inspect the complete current video together with a compact scenario packet containing the
previous clip ending, current clip story beats, and next clip opening. Ordered Picture references
support identity and persistent-object recognition; they are not the main grading target.

Do NOT grade literal wording compliance with the production prompt. Grade whether a viewer can
understand the intended current scenario from visible action and staging, whether the opening
plausibly receives the previous scenario's final state or cause clue, and whether the ending leaves
the state or cause clue required to begin the next scenario. A continuity handoff may be conveyed
by a persistent pose, object, damage, direction, location, effect, or newly created threat.

Use only visible evidence from the current video. The neighboring clips are scenario text context,
not videos, so never claim that their rendered footage matches. Audio is deliberately not supplied:
never judge dialogue delivery, sound, or lip-sync. Cite narrow timestamps for visible problems.
Mention visual polish only when it blocks story readability or continuity. Do not prescribe engine
controls such as reference weights, interpolation, intermediate frames, post-processing, or exact
frame locking. Suggestions must be achievable by rewriting story action, staging, camera evidence,
or the visible ending handoff. Do not auto-select the candidate or rewrite a complete prompt.

Return Korean JSON with exactly these top-level keys:
{
  "verdict":"recommended|usable|needs_revision|reject",
  "summary_ko":"",
  "positive_note_ko":"",
  "scenario_assessment_ko":"",
  "incoming_continuity_ko":"",
  "outgoing_continuity_ko":"",
  "scores":{
    "scenario_realization":0,"incoming_continuity":0,"outgoing_continuity":0,
    "causal_readability":0,"continuity_stability":0
  },
  "issues":[{
    "severity":"minor|major|critical","start_seconds":0,"end_seconds":0,
    "observed_ko":"","expected_ko":"","suggestion_ko":""
  }],
  "revision_feedback_ko":"one concise actionable paragraph for the next candidate prompts",
  "confidence":0.0
}
Scores are 0 to 5. If previous or next scenario context is genuinely unavailable, give the
corresponding continuity score 2.5 and state that it was not verifiable. A recommendation must
still mention any visible story or continuity uncertainty.
""".strip()


SHOT_RE = re.compile(
    r"^\[Shot (\d+)\](?: At \d{2}:\d{2}\.\d{3},)?[ \t]*(.*?)"
    r"(?=^\[Shot \d+\]|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _section(prompt: str, name: str, next_name: str) -> str:
    match = re.search(
        rf"^{re.escape(name)}:\n(.*?)\n\n{re.escape(next_name)}:\n",
        prompt,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _scenario_from_prompt(prompt: str) -> dict[str, Any]:
    summary = _section(prompt, "summary", "retention_analysis")
    summary = re.sub(r"^\[reference generation]\s*", "", summary).strip()
    detailed = _section(prompt, "detailed_description", "overall_soundscape")
    actions = [
        {
            "shot": int(match.group(1)),
            "action": _legacy_action_or_natural_shot(match.group(2)),
        }
        for match in SHOT_RE.finditer(detailed)
    ]
    if not actions:
        if detailed:
            actions = [{"shot": 1, "action": detailed[-3000:]}]
    return {
        "summary": summary,
        "shot_actions": actions,
        "opening_event": actions[0]["action"] if actions else "",
        "ending_event": actions[-1]["action"] if actions else "",
    }


def _legacy_action_or_natural_shot(body: str) -> str:
    """Read old CAMERA/ACTION prompts while preferring the new natural Shot prose."""
    text = body.strip()
    legacy = re.search(r"\bACTION:\s*(.*)", text, re.DOTALL)
    return (legacy.group(1) if legacy else text).strip()


def _latest_authored_prompt(
    root: Path, project_id: str, scene_id: str, clip_id: str,
) -> str:
    base = root / "runtime/h3/prompt_revision_requests"
    matches: list[tuple[int, str, str]] = []
    if base.is_dir():
        for directory in base.iterdir():
            if not directory.is_dir():
                continue
            try:
                request = json.loads(
                    (directory / "request.json").read_text(encoding="utf-8")
                )
                authored = json.loads(
                    (directory / "authored_variants.json").read_text(
                        encoding="utf-8"
                    )
                )
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                continue
            if (
                str(request.get("source_project_id") or "") != project_id
                or str(request.get("source_scene_id") or "") != scene_id
                or str(request.get("source_clip_id") or "") != clip_id
            ):
                continue
            variants = authored.get("prompt_variants") or []
            if len(variants) != 3:
                continue
            prompt = str(variants[0].get("video_prompt") or "").strip()
            if prompt:
                matches.append((
                    int(request.get("next_candidate_round") or 0),
                    str(request.get("updated_at") or request.get("applied_at") or ""),
                    prompt,
                ))
    return max(matches, default=(0, "", ""))[2]


def _scenario_context(root: Path | None, request: dict[str, Any]) -> dict[str, Any]:
    current = {
        "project_id": request.get("source_project_id"),
        "scene_id": request.get("source_scene_id"),
        "clip_id": request.get("source_clip_id"),
        **_scenario_from_prompt(str(request.get("prompt") or "")),
    }
    if root is None:
        return {"previous": None, "current": current, "next": None}
    project_id = str(request.get("source_project_id") or "")
    clip_id = str(request.get("source_clip_id") or "")
    if not project_id or not clip_id:
        return {"previous": None, "current": current, "next": None}
    try:
        overview = h3_prompt_projects.project_clips(root, project_id)
    except (FileNotFoundError, ValueError, OSError):
        return {"previous": None, "current": current, "next": None}
    clips = sorted(
        [clip for scene in overview.get("scenes") or [] for clip in scene.get("clips") or []],
        key=lambda row: (
            str(row.get("scene_id") or ""),
            int(row.get("sequence") or 0),
            str(row.get("clip_id") or ""),
        ),
    )
    current_index = next(
        (index for index, clip in enumerate(clips) if str(clip.get("clip_id") or "") == clip_id),
        None,
    )
    if current_index is None:
        return {"previous": None, "current": current, "next": None}

    def neighbor(index: int) -> dict[str, Any] | None:
        if index < 0 or index >= len(clips):
            return None
        clip = clips[index]
        scene_id = str(clip.get("scene_id") or "")
        prompt = _latest_authored_prompt(
            root, project_id, scene_id, str(clip.get("clip_id") or "")
        ) or str(clip.get("video_prompt") or "")
        scenario = _scenario_from_prompt(prompt)
        return {
            "scene_id": scene_id,
            "clip_id": clip.get("clip_id"),
            "summary": scenario["summary"],
            "opening_event": scenario["opening_event"],
            "ending_event": scenario["ending_event"],
        }

    return {
        "previous": neighbor(current_index - 1),
        "current": current,
        "next": neighbor(current_index + 1),
    }


def _reference_media(request: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    media: list[dict[str, str]] = []
    descriptions: list[dict[str, Any]] = []
    for fallback_index, reference in enumerate(request.get("references") or [], start=1):
        if not isinstance(reference, dict):
            continue
        index = int(reference.get("picture_index") or fallback_index)
        path = Path(str(reference.get("source_path") or ""))
        if not path.is_file():
            raise FileNotFoundError(f"후보 검수 Picture {index} 파일이 없습니다: {path}")
        label = str(reference.get("original_name") or reference.get("role") or f"Picture {index}")
        media.append(
            {
                "label": f"<Picture {index}> {label} · ordered production reference",
                "url": r2v_review._review_reference_data_url(path),
            }
        )
        descriptions.append(
            {
                "picture_index": index,
                "role": reference.get("role"),
                "label": label,
                "sha256": reference.get("sha256"),
            }
        )
    return media, descriptions


def _number(value: Any, minimum: float, maximum: float, default: float = 0.0) -> float:
    try:
        return round(max(minimum, min(maximum, float(value))), 2)
    except (TypeError, ValueError):
        return default


def review_candidate_video(
    *,
    video_path: Path,
    request: dict[str, Any],
    review_id: str,
    job_id: str,
    root: Path | None = None,
) -> dict[str, Any]:
    if not video_path.is_file():
        raise FileNotFoundError(f"후보 검수 영상이 없습니다: {video_path}")
    probe = omni.probe_video(video_path)
    if not probe.get("has_video"):
        raise omni.VLLMReviewError(f"후보 검수 파일에 영상 스트림이 없습니다: {video_path}")
    duration = float(probe.get("duration_seconds") or request.get("duration_seconds") or 0)
    use_audio = False
    probe["audio_reviewed"] = False
    video_data_url, video_metadata = omni._direct_video_data_url(video_path)
    audio_data_url = None
    image_media, references = _reference_media(request)
    model = omni._model_id()
    scenario_packet = _scenario_context(root, request)
    context = {
        "candidate_job_id": job_id,
        "candidate_index": request.get("candidate_index"),
        "prompt_variant_id": request.get("prompt_variant_id"),
        "review_priority": (
            "visible scenario realization and previous/current/next clip handoff; "
            "not literal production-prompt compliance"
        ),
        "scenario_packet": scenario_packet,
        "references": references,
        "duration_seconds": duration,
        "audio_reviewed": use_audio,
    }
    payload, _message, raw = omni._response_json(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        required_keys={
            "verdict", "summary_ko", "positive_note_ko", "scores", "issues",
            "scenario_assessment_ko", "incoming_continuity_ko",
            "outgoing_continuity_ko", "revision_feedback_ko", "confidence",
        },
        user_text="Evaluate this candidate as one clip in a continuous episode.\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":")),
        video_data_url=video_data_url,
        audio_data_url=audio_data_url,
        video_metadata=video_metadata,
        image_data_urls=image_media,
    )
    verdict = str(payload.get("verdict") or "needs_revision")
    if verdict not in {"recommended", "usable", "needs_revision", "reject"}:
        verdict = "needs_revision"
    raw_scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    scores = {key: _number(raw_scores.get(key), 0, 5) for key in SCORE_KEYS}
    applicable_score_keys = list(SCORE_KEYS)
    if scenario_packet.get("previous") is None:
        applicable_score_keys.remove("incoming_continuity")
    if scenario_packet.get("next") is None:
        applicable_score_keys.remove("outgoing_continuity")
    issues = []
    for item in (payload.get("issues") or [])[:8]:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "major")
        if severity not in {"minor", "major", "critical"}:
            severity = "major"
        start = _number(item.get("start_seconds"), 0, duration)
        end = _number(item.get("end_seconds"), start, duration, start)
        issues.append(
            {
                "severity": severity,
                "start_seconds": start,
                "end_seconds": end,
                "observed_ko": str(item.get("observed_ko") or "").strip(),
                "expected_ko": str(item.get("expected_ko") or "").strip(),
                "suggestion_ko": str(item.get("suggestion_ko") or "").strip(),
            }
        )
    return {
        "review_id": review_id,
        "job_id": job_id,
        "review_mode": REVIEW_MODE,
        "rubric_version": RUBRIC_VERSION,
        "model": model,
        "verdict": verdict,
        "summary_ko": str(payload.get("summary_ko") or "").strip(),
        "positive_note_ko": str(payload.get("positive_note_ko") or "").strip(),
        "scenario_assessment_ko": str(
            payload.get("scenario_assessment_ko") or ""
        ).strip(),
        "incoming_continuity_ko": str(
            payload.get("incoming_continuity_ko") or ""
        ).strip(),
        "outgoing_continuity_ko": str(
            payload.get("outgoing_continuity_ko") or ""
        ).strip(),
        "scores": scores,
        "score_applicability": applicable_score_keys,
        "overall_score": round(
            sum(scores[key] for key in applicable_score_keys)
            / max(1, len(applicable_score_keys)),
            2,
        ),
        "issues": issues,
        "revision_feedback_ko": str(payload.get("revision_feedback_ko") or "").strip(),
        "confidence": _number(payload.get("confidence"), 0, 1),
        "duration_seconds": round(duration, 3),
        "reference_count": len(references),
        "review_capabilities": ["video", "image", "scenario_context"],
        "scenario_context": context["scenario_packet"],
        "media_probe": probe,
        "observation": None,
        "raw_observation_response": "",
        "raw_response": raw if omni.VLLM_REVIEW_STORE_RAW_MESSAGE else "",
    }
