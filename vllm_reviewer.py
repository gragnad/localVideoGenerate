from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any
import requests


VLLM_URL = os.environ.get("VLLM_URL", "http://127.0.0.1:8091").rstrip("/")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "").strip()
VLLM_REVIEW_TIMEOUT = float(os.environ.get("VLLM_REVIEW_TIMEOUT", "1200"))
VLLM_REVIEW_MAX_TOKENS = int(os.environ.get("VLLM_REVIEW_MAX_TOKENS", "5000"))
VLLM_REVIEW_TEMPERATURE = float(
    os.environ.get("VLLM_REVIEW_TEMPERATURE", "0.1")
)
VLLM_VIDEO_REVIEW_TWO_PASS = (
    os.environ.get("VLLM_VIDEO_REVIEW_TWO_PASS", "true")
    .strip()
    .lower()
    not in {"0", "false", "no", "off"}
)
VLLM_REVIEW_USE_AUDIO_IN_VIDEO = (
    os.environ.get("VLLM_REVIEW_USE_AUDIO_IN_VIDEO", "auto")
    .strip()
    .lower()
)
VLLM_REVIEW_STORE_RAW_MESSAGE = (
    os.environ.get("VLLM_REVIEW_STORE_RAW_MESSAGE", "false")
    .strip()
    .lower()
    in {"1", "true", "yes", "on"}
)
VLLM_REVIEW_VIDEO_MAX_BYTES = int(
    os.environ.get("VLLM_REVIEW_VIDEO_MAX_BYTES", str(128 * 1024 * 1024))
)
VLLM_REVIEW_VIDEO_TRANSPORT = os.environ.get(
    "VLLM_REVIEW_VIDEO_TRANSPORT",
    "direct_mp4_base64",
).strip() or "direct_mp4_base64"
VLLM_REVIEW_PROXY_FPS = max(
    1,
    int(os.environ.get("VLLM_REVIEW_PROXY_FPS", "8")),
)
VLLM_REVIEW_PROXY_MAX_WIDTH = max(
    320,
    int(os.environ.get("VLLM_REVIEW_PROXY_MAX_WIDTH", "768")),
)


OBSERVATION_SYSTEM_PROMPT = r"""
You are the first-pass evidence observer for a short AI-generated cinematic video.

You receive the complete generated source video file, including its original
motion and audio track when present. You do NOT receive the generation prompt.
Record only events directly supported by the video and audio. Review temporal
motion continuously rather than treating isolated still frames as the source.

Rules:
- Never infer intended actions, character names, dialogue text, or story meaning.
- Do not invent motion or dialogue that is not supported by the source video.
- Distinguish visible evidence, audible evidence, and uncertainty.
- Use timestamps only within the supplied duration.
- A brief event must have a narrow time range, not the full clip.
- Inspect motion throughout the timeline for implausible acceleration, sudden pose
  changes, sliding or teleporting, reversed or interrupted actions, unstable body
  geometry, impossible collisions, and reactions without a visible cause.
- Report repeated flashes, disappearing entities, deformation, identity drift,
  unwanted text, abrupt camera jumps, collisions, misses, and contact when visible.
- Do not dismiss an abnormal action merely because the character and background
  remain recognizable. Local motion quality is an independent acceptance criterion.
- If audio was not supplied, do not claim dialogue or sound accuracy.
- If audio was supplied but words are unclear, report them as unclear.
- Cover the beginning, middle, and end, and isolate every suspicious motion interval.
- Keep reasoning concise and use at most 12 timeline entries.
- Return exactly one JSON object and no prose outside JSON.

Schema:
{
  "observed_summary_ko": "Korean factual summary",
  "visible_entities": [
    {
      "description_ko": "observable entity description",
      "first_seen_seconds": 0.0,
      "last_seen_seconds": 0.0,
      "continuity_ko": "observable continuity"
    }
  ],
  "timeline": [
    {
      "start_seconds": 0.0,
      "end_seconds": 0.0,
      "visual_event_ko": "directly observed event",
      "camera_event_ko": "directly observed camera behavior",
      "audio_event_ko": "directly heard event or not reviewed"
    }
  ],
  "visual_artifacts": [
    {
      "start_seconds": 0.0,
      "end_seconds": 0.0,
      "type": "deformation|identity_drift|object_break|flicker|text_artifact|camera_jump|unnatural_motion|teleport|collision|other",
      "evidence_ko": "direct evidence"
    }
  ],
  "audio_observation": {
    "reviewed": false,
    "speech_detected": false,
    "clear_transcript_ko": [],
    "uncertainty_ko": ""
  },
  "uncertainties_ko": []
}
""".strip()


COMPLIANCE_SYSTEM_PROMPT = r"""
You are the second-pass quality-control reviewer for an AI-generated cinematic
video production pipeline.

You receive:
1. the original generation instructions,
2. the complete generated source video with its original motion and available audio,
3. an independent first-pass observation that was produced without seeing the
   generation instructions,
4. timing and media metadata.

Compare the required production behavior against actual video evidence.

Evidence discipline:
- Do not treat the original prompt as proof that an event occurred.
- Prefer direct source-video evidence over the observation when they conflict.
- Do not turn "maybe", "appears", or an ambiguous dark shape into a verified fact.
- Distinguish verified, contradicted, uncertain, and not_verifiable requirements.
- Do not claim exact dialogue accuracy unless audio was reviewed and intelligible.
- Visible lip motion alone does not prove exact spoken words.
- Use narrow time ranges for localized events.
- Do not mark an entity missing for the entire clip when it is required only during
  an early, middle, or late interval.
- Evaluate each requirement once and avoid duplicate issues.

Review priorities:
- required visible characters, creatures, threats, objects, and prohibited extras,
- character identity and continuity,
- chronological action order, sustained motion, one-time events, contact or miss,
- start state and end state,
- camera movement and shot transition,
- deformation, duplicated limbs, merged bodies, broken props, flicker,
- unintended readable text, logos, watermarks, subtitles, or UI,
- dialogue/audio only when audio evidence is available.

Mandatory motion-quality audit:
- Check pose-to-pose continuity, limb and body articulation, direction and speed,
  contact physics, object permanence, cause-and-effect reactions, and whether each
  prompted action actually begins, develops, and ends coherently.
- Treat sudden unmotivated movement, teleporting, sliding, rubber-like deformation,
  direction reversal, frozen motion followed by a jump, or an impossible collision
  as a concrete issue with a narrow timestamp.
- Include at least one requirement_check in action or continuity and at least one
  requirement_check in artifact, even when both pass.

Severity:
- blocking: makes the shot unusable or directly contradicts a required core beat.
- major: clearly harms continuity or readability.
- minor: cosmetic issue that should not trigger an automatic retake by itself.
- advisory: uncertain or preference-based observation.

Return exactly one JSON object and no prose outside JSON.

Schema:
{
  "accepted": true,
  "confidence": 0.0,
  "summary_ko": "Korean summary",
  "requirement_checks": [
    {
      "requirement_ko": "requirement being checked",
      "category": "character|entity|action|timing|camera|dialogue|audio|continuity|artifact|other",
      "status": "verified|contradicted|uncertain|not_verifiable",
      "start_seconds": 0.0,
      "end_seconds": 0.0,
      "evidence_ko": "direct evidence"
    }
  ],
  "issues": [
    {
      "severity": "blocking|major|minor|advisory",
      "type": "character_continuity|action_mismatch|temporal_mismatch|camera_mismatch|deformation|extra_character|missing_entity|dialogue_mismatch|audio_mismatch|text_artifact|lighting_continuity|other",
      "sample_indices": [],
      "start_seconds": 0.0,
      "end_seconds": 0.0,
      "evidence_ko": "Korean direct evidence",
      "recommended_workflow": "retake|manual_review|none",
      "retake_prompt_en": "English correction prompt with temporal behavior",
      "retake_strength": 1.0
    }
  ],
  "recommended_action": "accept|retake|manual_review"
}

Decision rules:
- accepted must be false if any blocking or major issue exists.
- recommended_action is retake only when a localized correction is plausible.
- use manual_review when a required core behavior remains uncertain.
- start_seconds and end_seconds must fit the supplied duration.
- sample_indices remains an empty list in direct-video mode.
- a passing decision must be based on observed evidence, not prompt repetition.
- Keep reasoning concise. Return at most 12 requirement_checks and 8 issues.
- The final JSON must be complete; never stop in the middle of an array or object.
- finish with the JSON object in assistant content; do not leave the final answer
  only in reasoning or reasoning_content.
""".strip()


ONE_PASS_SYSTEM_PROMPT = r"""
You are the automated quality-control reviewer for a short AI-generated cinematic
video supplied as the complete source MP4. Review its motion, timing, visual
continuity, and available audio against the supplied generation instructions.

Judge actual chronological video evidence, not prompt wording. Do not infer exact
dialogue from lip motion. Use narrow timestamps. Separate ambiguity from failure.
Do not duplicate issues.

Return exactly one JSON object with this schema:
{
  "accepted": true,
  "confidence": 0.0,
  "summary_ko": "Korean summary",
  "requirement_checks": [],
  "issues": [
    {
      "severity": "blocking|major|minor|advisory",
      "type": "character_continuity|action_mismatch|temporal_mismatch|camera_mismatch|deformation|extra_character|missing_entity|dialogue_mismatch|audio_mismatch|text_artifact|lighting_continuity|other",
      "sample_indices": [],
      "start_seconds": 0.0,
      "end_seconds": 0.0,
      "evidence_ko": "Korean evidence",
      "recommended_workflow": "retake|manual_review|none",
      "retake_prompt_en": "English correction with temporal behavior",
      "retake_strength": 1.0
    }
  ],
  "recommended_action": "accept|retake|manual_review"
}
""".strip()


class VLLMReviewError(RuntimeError):
    pass


def _model_id() -> str:
    try:
        response = requests.get(f"{VLLM_URL}/v1/models", timeout=30)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise VLLMReviewError(f"vLLM 모델 목록 조회 실패: {exc}") from exc

    model_ids = [
        str(item.get("id") or "").strip()
        for item in (payload.get("data") or [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    if not model_ids:
        raise VLLMReviewError("vLLM /v1/models 응답에서 모델 ID를 찾지 못했습니다.")

    if VLLM_MODEL and VLLM_MODEL in model_ids:
        return VLLM_MODEL
    if len(model_ids) == 1:
        return model_ids[0]
    if VLLM_MODEL:
        raise VLLMReviewError(
            f"설정된 모델 ID {VLLM_MODEL!r}가 서버 모델 목록에 없습니다: "
            + ", ".join(model_ids)
        )
    return model_ids[0]


def _extract_json(
    text: str,
    *,
    required_keys: set[str] | None = None,
) -> dict[str, Any]:
    stripped = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^\x60{3}(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*\x60{3}$", "", stripped)

    required = required_keys or set()

    def is_valid(value: Any) -> bool:
        return isinstance(value, dict) and required.issubset(value.keys())

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        candidates: list[tuple[int, int, dict[str, Any]]] = []
        for match in re.finditer(r"{", stripped):
            try:
                value, consumed = decoder.raw_decode(stripped[match.start() :])
            except json.JSONDecodeError:
                continue
            if is_valid(value):
                candidates.append((consumed, match.start(), value))

        if not candidates:
            missing_text = ", ".join(sorted(required)) or "top-level object"
            raise VLLMReviewError(
                "vLLM 응답에서 완결된 필수 JSON 객체를 찾지 못했습니다. "
                f"필수 키: {missing_text}\n"
                + stripped[-5000:]
            )
        _, _, payload = max(
            candidates,
            key=lambda item: (item[0], -item[1]),
        )

    if not is_valid(payload):
        missing = (
            sorted(required.difference(payload.keys()))
            if isinstance(payload, dict)
            else sorted(required)
        )
        raise VLLMReviewError(
            "vLLM 검수 결과의 최상위 스키마가 불완전합니다. "
            f"누락 키: {', '.join(missing) or 'JSON object'}"
        )
    return payload


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def probe_video(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "ffprobe_available": False,
        "duration_seconds": None,
        "has_video": True,
        "has_audio": False,
        "video_streams": [],
        "audio_streams": [],
    }
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,format_name:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return result

    if proc.returncode != 0:
        result["ffprobe_error"] = (proc.stderr or proc.stdout)[-3000:]
        return result

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result["ffprobe_error"] = "ffprobe JSON 해석 실패"
        return result

    result["ffprobe_available"] = True
    duration = _safe_float((payload.get("format") or {}).get("duration"), -1.0)
    if duration >= 0:
        result["duration_seconds"] = duration

    for stream in payload.get("streams") or []:
        if stream.get("codec_type") == "audio":
            result["audio_streams"].append(stream)
        elif stream.get("codec_type") == "video":
            result["video_streams"].append(stream)

    result["has_video"] = bool(result["video_streams"])
    result["has_audio"] = bool(result["audio_streams"])
    return result


def _should_use_audio(media_probe: dict[str, Any]) -> bool:
    if VLLM_REVIEW_USE_AUDIO_IN_VIDEO in {"1", "true", "yes", "on"}:
        return bool(media_probe.get("has_audio"))
    if VLLM_REVIEW_USE_AUDIO_IN_VIDEO in {"0", "false", "no", "off"}:
        return False
    return bool(media_probe.get("has_audio"))


def _prepare_review_video(video_path: Path) -> Path:
    review_path = video_path.with_name(
        f"review_source_video_mjpeg_{VLLM_REVIEW_PROXY_FPS}fps_"
        f"{VLLM_REVIEW_PROXY_MAX_WIDTH}w.avi"
    )
    if (
        review_path.is_file()
        and review_path.stat().st_size > 0
        and review_path.stat().st_mtime >= video_path.stat().st_mtime
    ):
        return review_path

    temporary_path = review_path.with_name(f".{review_path.name}.tmp.avi")
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(video_path),
                "-map",
                "0:v:0",
                "-an",
                "-vf",
                (
                    f"fps={VLLM_REVIEW_PROXY_FPS},"
                    f"scale='min(iw,{VLLM_REVIEW_PROXY_MAX_WIDTH})':-2"
                ),
                "-c:v",
                "mjpeg",
                "-q:v",
                "3",
                "-pix_fmt",
                "yuvj420p",
                str(temporary_path),
            ],
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        if proc.returncode != 0:
            raise VLLMReviewError(
                "전체 영상 MJPEG 검수 프록시 생성 실패: "
                + (proc.stderr or proc.stdout)[-4000:]
            )
        temporary_path.replace(review_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return review_path


def _direct_video_data_url(video_path: Path) -> tuple[str, dict[str, Any]]:
    review_path = _prepare_review_video(video_path)
    size_bytes = review_path.stat().st_size
    if size_bytes <= 0:
        raise VLLMReviewError(f"검수 영상 파일이 비어 있습니다: {review_path}")
    if size_bytes > VLLM_REVIEW_VIDEO_MAX_BYTES:
        raise VLLMReviewError(
            "검수 영상이 직접 전송 크기 제한을 초과했습니다: "
            f"{size_bytes} > {VLLM_REVIEW_VIDEO_MAX_BYTES} bytes"
        )

    encoded = base64.b64encode(review_path.read_bytes()).decode("ascii")
    return (
        f"data:video/x-msvideo;base64,{encoded}",
        {
            "transport": VLLM_REVIEW_VIDEO_TRANSPORT,
            "mime_type": "video/x-msvideo",
            "source_path": str(video_path),
            "source_size_bytes": video_path.stat().st_size,
            "review_video_path": str(review_path),
            "review_video_size_bytes": size_bytes,
            "encoded_size_bytes": len(encoded),
            "review_codec": "mjpeg",
            "review_fps": VLLM_REVIEW_PROXY_FPS,
            "review_max_width": VLLM_REVIEW_PROXY_MAX_WIDTH,
            "complete_source_video": True,
            "complete_timeline": True,
        },
    )


def _direct_audio_data_url(video_path: Path) -> tuple[str, dict[str, Any]]:
    audio_path = video_path.with_name("review_source_audio_16k_mono.wav")
    if (
        not audio_path.is_file()
        or audio_path.stat().st_size <= 0
        or audio_path.stat().st_mtime < video_path.stat().st_mtime
    ):
        temporary_path = audio_path.with_name(f".{audio_path.name}.tmp.wav")
        try:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(temporary_path),
                ],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if proc.returncode != 0:
                raise VLLMReviewError(
                    "검수 영상의 오디오 WAV 추출 실패: "
                    + (proc.stderr or proc.stdout)[-4000:]
                )
            temporary_path.replace(audio_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    size_bytes = audio_path.stat().st_size
    if size_bytes > VLLM_REVIEW_VIDEO_MAX_BYTES:
        raise VLLMReviewError(
            "검수 오디오가 직접 전송 크기 제한을 초과했습니다: "
            f"{size_bytes} > {VLLM_REVIEW_VIDEO_MAX_BYTES} bytes"
        )
    encoded = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    return (
        f"data:audio/wav;base64,{encoded}",
        {
            "transport": "direct_wav_base64",
            "codec": "pcm_s16le",
            "sample_rate": 16000,
            "channels": 1,
            "source_size_bytes": size_bytes,
            "encoded_size_bytes": len(encoded),
            "local_path": str(audio_path),
        },
    )


def _response_json(
    *,
    model: str,
    system_prompt: str,
    user_text: str,
    required_keys: set[str],
    video_data_url: str,
    audio_data_url: str | None,
    video_metadata: dict[str, Any],
    reference_video_data_url: str | None = None,
    reference_video_metadata: dict[str, Any] | None = None,
    image_data_urls: list[dict[str, str]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    user_content: list[dict[str, Any]] = []
    for item in image_data_urls or []:
        user_content.extend([
            {"type": "text", "text": str(item.get("label") or "REFERENCE IMAGE")},
            {"type": "image_url", "image_url": {"url": str(item.get("url") or "")}},
        ])
    if reference_video_data_url:
        user_content.extend([
            {"type":"text","text":"REFERENCE SELECTED CANDIDATE VIDEO (preserve identity, motion, timing and composition):"},
            {"type":"video_url","video_url":{"url":reference_video_data_url}},
            {"type":"text","text":"UPSCALED RESULT VIDEO TO REVIEW:"},
        ])
    user_content.append({"type":"video_url","video_url":{"url":video_data_url}})
    if reference_video_metadata:
        user_content.append({"type":"text","text":"REFERENCE VIDEO METADATA: "+json.dumps(
            reference_video_metadata,ensure_ascii=False,separators=(",",":"))})
    if audio_data_url:
        user_content.append(
            {
                "type": "audio_url",
                "audio_url": {
                    "url": audio_data_url,
                },
            }
        )
    user_content.append(
        {
            "type": "text",
            "text": user_text,
        }
    )

    payload: dict[str, Any] = {
        "model": model,
        "temperature": VLLM_REVIEW_TEMPERATURE,
        "max_tokens": VLLM_REVIEW_MAX_TOKENS,
        "mm_processor_kwargs": {
            "use_audio_in_video": False,
        },
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
    }

    response = requests.post(
        f"{VLLM_URL}/v1/chat/completions",
        json=payload,
        timeout=VLLM_REVIEW_TIMEOUT,
    )
    if response.status_code == 400:
        fallback_payload = dict(payload)
        fallback_payload.pop("response_format", None)
        response = requests.post(
            f"{VLLM_URL}/v1/chat/completions",
            json=fallback_payload,
            timeout=VLLM_REVIEW_TIMEOUT,
        )
    if not response.ok:
        raise VLLMReviewError(
            f"vLLM 직접 MP4 영상 검수 요청 실패 "
            f"({response.status_code}): {response.text[:12000]}\n"
            "--- direct video metadata ---\n"
            + json.dumps(
                video_metadata,
                ensure_ascii=False,
                separators=(",", ":"),
            )[:12000]
        )

    body = response.json()
    choices = body.get("choices") or []
    if not choices:
        raise VLLMReviewError(
            "vLLM 영상 검수 응답에 choices가 없습니다:\n"
            + json.dumps(
                body,
                ensure_ascii=False,
                separators=(",", ":"),
            )[:12000]
        )

    message = choices[0].get("message", {}) or {}
    finish_reason = str(choices[0].get("finish_reason") or "")
    candidates = [
        value.strip()
        for value in (
            message.get("content"),
            message.get("reasoning"),
            message.get("reasoning_content"),
        )
        if isinstance(value, str) and value.strip()
    ]
    if not candidates:
        raise VLLMReviewError(
            "vLLM 영상 검수 응답 본문이 비어 있습니다:\n"
            + json.dumps(
                body,
                ensure_ascii=False,
                separators=(",", ":"),
            )[:12000]
        )

    errors: list[str] = []
    for candidate in candidates:
        try:
            parsed = _extract_json(
                candidate,
                required_keys=required_keys,
            )
            parsed["_video_transport"] = VLLM_REVIEW_VIDEO_TRANSPORT
            return parsed, message, candidate
        except VLLMReviewError as exc:
            errors.append(str(exc))

    raise VLLMReviewError(
        "vLLM 영상 검수 응답에서 유효한 JSON을 찾지 못했습니다.\n"
        + (f"finish_reason={finish_reason}\n" if finish_reason else "")
        + "\n".join(errors)[:12000]
        + "\n--- full response ---\n"
        + json.dumps(
            body,
            ensure_ascii=False,
            indent=2,
        )[:12000]
    )


def _clamp_time(value: Any, duration: float, default: float = 0.0) -> float:
    return round(max(0.0, min(duration, _safe_float(value, default))), 3)


def _normalize_observation(
    payload: dict[str, Any],
    *,
    duration_seconds: float,
    audio_reviewed: bool,
) -> dict[str, Any]:
    visible_entities = []
    for raw in payload.get("visible_entities") or []:
        if not isinstance(raw, dict):
            continue
        first = _clamp_time(raw.get("first_seen_seconds"), duration_seconds)
        last = _clamp_time(
            raw.get("last_seen_seconds"),
            duration_seconds,
            first,
        )
        last = max(first, last)
        visible_entities.append(
            {
                "description_ko": str(raw.get("description_ko") or "").strip(),
                "first_seen_seconds": first,
                "last_seen_seconds": last,
                "continuity_ko": str(raw.get("continuity_ko") or "").strip(),
            }
        )

    timeline = []
    for raw in payload.get("timeline") or []:
        if not isinstance(raw, dict):
            continue
        start = _clamp_time(raw.get("start_seconds"), duration_seconds)
        end = _clamp_time(raw.get("end_seconds"), duration_seconds, start)
        timeline.append(
            {
                "start_seconds": start,
                "end_seconds": max(start, end),
                "visual_event_ko": str(raw.get("visual_event_ko") or "").strip(),
                "camera_event_ko": str(raw.get("camera_event_ko") or "").strip(),
                "audio_event_ko": str(raw.get("audio_event_ko") or "").strip(),
            }
        )

    artifacts = []
    for raw in payload.get("visual_artifacts") or []:
        if not isinstance(raw, dict):
            continue
        start = _clamp_time(raw.get("start_seconds"), duration_seconds)
        end = _clamp_time(raw.get("end_seconds"), duration_seconds, start)
        artifacts.append(
            {
                "start_seconds": start,
                "end_seconds": max(start, end),
                "type": str(raw.get("type") or "other"),
                "evidence_ko": str(raw.get("evidence_ko") or "").strip(),
            }
        )

    audio = payload.get("audio_observation") or {}
    if not isinstance(audio, dict):
        audio = {}

    return {
        "observed_summary_ko": str(
            payload.get("observed_summary_ko") or ""
        ).strip(),
        "visible_entities": visible_entities,
        "timeline": timeline,
        "visual_artifacts": artifacts,
        "audio_observation": {
            "reviewed": bool(audio_reviewed),
            "speech_detected": (
                bool(audio.get("speech_detected")) if audio_reviewed else False
            ),
            "clear_transcript_ko": [
                str(item).strip()
                for item in (audio.get("clear_transcript_ko") or [])
                if str(item).strip()
            ] if audio_reviewed else [],
            "uncertainty_ko": str(audio.get("uncertainty_ko") or "").strip(),
        },
        "uncertainties_ko": [
            str(item).strip()
            for item in (payload.get("uncertainties_ko") or [])
            if str(item).strip()
        ],
    }


def _normalize_report(
    payload: dict[str, Any],
    *,
    duration_seconds: float,
) -> dict[str, Any]:
    checks = []
    allowed_check_status = {
        "verified",
        "contradicted",
        "uncertain",
        "not_verifiable",
    }
    for raw in payload.get("requirement_checks") or []:
        if not isinstance(raw, dict):
            continue
        start = _clamp_time(raw.get("start_seconds"), duration_seconds)
        end = _clamp_time(raw.get("end_seconds"), duration_seconds, start)
        status = str(raw.get("status") or "uncertain")
        if status not in allowed_check_status:
            status = "uncertain"
        checks.append(
            {
                "requirement_ko": str(raw.get("requirement_ko") or "").strip(),
                "category": str(raw.get("category") or "other"),
                "status": status,
                "start_seconds": start,
                "end_seconds": max(start, end),
                "evidence_ko": str(raw.get("evidence_ko") or "").strip(),
            }
        )

    issues_out: list[dict[str, Any]] = []
    for raw in payload.get("issues") or []:
        if not isinstance(raw, dict):
            continue

        start = _clamp_time(raw.get("start_seconds"), duration_seconds)
        end = _clamp_time(raw.get("end_seconds"), duration_seconds, start)

        severity = str(raw.get("severity") or "advisory")
        if severity not in {"blocking", "major", "minor", "advisory"}:
            severity = "advisory"

        workflow = str(raw.get("recommended_workflow") or "none")
        if workflow not in {"retake", "manual_review", "none"}:
            workflow = "manual_review"

        strength = max(
            0.0,
            min(1.0, _safe_float(raw.get("retake_strength"), 1.0)),
        )

        issues_out.append(
            {
                "severity": severity,
                "type": str(raw.get("type") or "other"),
                "sample_indices": [],
                "start_seconds": start,
                "end_seconds": max(start, end),
                "evidence_ko": str(raw.get("evidence_ko") or "").strip(),
                "recommended_workflow": workflow,
                "retake_prompt_en": str(
                    raw.get("retake_prompt_en") or ""
                ).strip(),
                "retake_strength": strength,
            }
        )

    hard_issue = any(
        item["severity"] in {"blocking", "major"} for item in issues_out
    )
    accepted = bool(payload.get("accepted", not hard_issue))
    if hard_issue:
        accepted = False

    action = str(payload.get("recommended_action") or "")
    if action not in {"accept", "retake", "manual_review"}:
        if accepted:
            action = "accept"
        elif any(
            item["recommended_workflow"] == "retake"
            for item in issues_out
            if item["severity"] in {"blocking", "major"}
        ):
            action = "retake"
        else:
            action = "manual_review"

    uncertain_core = any(
        item["status"] in {"uncertain", "not_verifiable"}
        and item["category"] in {
            "character",
            "entity",
            "action",
            "timing",
            "camera",
            "dialogue",
            "audio",
            "continuity",
        }
        for item in checks
    )
    if accepted and uncertain_core:
        accepted = False
        action = "manual_review"

    categories = {item["category"] for item in checks}
    issue_types = {item["type"] for item in issues_out}
    motion_issue_types = {
        "action_mismatch",
        "temporal_mismatch",
        "camera_mismatch",
        "character_continuity",
        "deformation",
    }
    artifact_issue_types = {
        "deformation",
        "character_continuity",
        "extra_character",
        "text_artifact",
        "lighting_continuity",
    }
    missing_quality_audits = []
    if (
        not categories.intersection({"action", "continuity"})
        and not issue_types.intersection(motion_issue_types)
    ):
        missing_quality_audits.append("동작/연속성")
    if "artifact" not in categories and not issue_types.intersection(
        artifact_issue_types
    ):
        missing_quality_audits.append("영상 아티팩트")
    if missing_quality_audits:
        accepted = False
        action = "manual_review"
        issues_out.append(
            {
                "severity": "advisory",
                "type": "other",
                "sample_indices": [],
                "start_seconds": 0.0,
                "end_seconds": duration_seconds,
                "evidence_ko": (
                    "필수 품질 점검 항목이 응답에서 누락되었습니다: "
                    + ", ".join(missing_quality_audits)
                ),
                "recommended_workflow": "manual_review",
                "retake_prompt_en": "",
                "retake_strength": 0.0,
            }
        )

    if accepted:
        action = "accept"

    confidence = max(
        0.0,
        min(1.0, _safe_float(payload.get("confidence"), 0.0)),
    )

    return {
        "accepted": accepted,
        "confidence": confidence,
        "summary_ko": str(payload.get("summary_ko") or "").strip(),
        "requirement_checks": checks,
        "issues": issues_out,
        "recommended_action": action,
    }


def _request_context(
    *,
    original_request: dict[str, Any],
    generation_summary: dict[str, Any],
    batch_id: str,
    job_id: str,
    duration_seconds: float,
    media_probe: dict[str, Any],
) -> dict[str, Any]:
    segments = []
    for item in original_request.get("segments") or []:
        segments.append(
            {
                "order": item.get("order"),
                "seconds": item.get("seconds"),
                "prompt": item.get("prompt"),
                "image": item.get("original_name"),
            }
        )
    return {
        "batch_id": batch_id,
        "job_id": job_id,
        "duration_seconds": duration_seconds,
        "fps": original_request.get("fps"),
        "resolution": original_request.get("resolution"),
        "seed": original_request.get("seed"),
        "global_prompt": original_request.get("global_prompt"),
        "segments": segments,
        "media_probe": {
            "has_audio": media_probe.get("has_audio"),
            "audio_reviewed": media_probe.get("audio_reviewed"),
            "video_streams": media_probe.get("video_streams"),
            "audio_streams": media_probe.get("audio_streams"),
        },
    }


def review_video(
    *,
    video_path: Path,
    original_request: dict[str, Any],
    generation_summary: dict[str, Any],
    batch_id: str,
    job_id: str,
) -> dict[str, Any]:
    if not video_path.is_file():
        raise FileNotFoundError(f"검수 영상 파일이 없습니다: {video_path}")

    media_probe = probe_video(video_path)
    if not media_probe.get("has_video"):
        raise VLLMReviewError(f"검수 파일에 영상 스트림이 없습니다: {video_path}")

    summary_duration = _safe_float(
        generation_summary.get("total_seconds"),
        0.0,
    )
    probed_duration = _safe_float(
        media_probe.get("duration_seconds"),
        0.0,
    )
    duration_seconds = probed_duration or summary_duration
    if duration_seconds <= 0:
        duration_seconds = sum(
            _safe_float(item.get("seconds"), 0.0)
            for item in (original_request.get("segments") or [])
        )
    duration_seconds = max(0.0, duration_seconds)

    use_audio = _should_use_audio(media_probe)
    media_probe["audio_reviewed"] = use_audio
    media_probe["source_has_audio"] = bool(media_probe.get("has_audio"))
    media_probe["audio_review_note"] = (
        "The original video audio track was supplied to Qwen3-Omni."
        if use_audio
        else (
            "The source video has no audio track."
            if not media_probe.get("has_audio")
            else "Audio review is disabled by VLLM_REVIEW_USE_AUDIO_IN_VIDEO."
        )
    )

    model = _model_id()
    video_data_url, video_metadata = _direct_video_data_url(video_path)
    reference_video_data_url: str | None = None
    reference_video_metadata: dict[str, Any] | None = None
    reference_value=str(original_request.get("comparison_source_video_path") or "").strip()
    reference_path=Path(reference_value) if reference_value else None
    if reference_path is not None:
        if not reference_path.is_file():
            raise FileNotFoundError(f"업스케일 비교 원본 영상이 없습니다: {reference_path}")
        reference_video_data_url,reference_video_metadata=_direct_video_data_url(reference_path)
        reference_video_metadata["media_probe"]=probe_video(reference_path)
    audio_data_url: str | None = None
    audio_metadata: dict[str, Any] | None = None
    if use_audio:
        audio_data_url, audio_metadata = _direct_audio_data_url(video_path)

    video_metadata.update(
        {
            "audio_input": audio_metadata,
            "duration_seconds": round(duration_seconds, 3),
            "audio_supplied": use_audio,
            "source_has_audio": bool(media_probe.get("has_audio")),
            "video_streams": media_probe.get("video_streams") or [],
            "audio_streams": media_probe.get("audio_streams") or [],
        }
    )

    video_instruction = {
        "transport": VLLM_REVIEW_VIDEO_TRANSPORT,
        "complete_source_video": True,
        "duration_seconds": round(duration_seconds, 3),
        "audio_supplied": use_audio,
        "instruction": (
            "Review the attached complete source video directly. Evaluate actual "
            "motion and timing across the clip. When audio is supplied, listen to "
            "speech, narration, and sound and compare them with the request."
        ),
    }

    observation: dict[str, Any] | None = None
    observation_message: dict[str, Any] | None = None
    observation_raw = ""

    if VLLM_VIDEO_REVIEW_TWO_PASS:
        (
            observation_payload,
            observation_message,
            observation_raw,
        ) = _response_json(
            model=model,
            system_prompt=OBSERVATION_SYSTEM_PROMPT,
            required_keys={
                "observed_summary_ko",
                "timeline",
                "audio_observation",
            },
            user_text=(
                "Observe this complete source video without comparing it to any "
                "intended prompt.\n"
                + json.dumps(
                    video_instruction,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            ),
            video_data_url=video_data_url,
            audio_data_url=audio_data_url,
            video_metadata=video_metadata,
        )
        observation = _normalize_observation(
            observation_payload,
            duration_seconds=duration_seconds,
            audio_reviewed=use_audio,
        )

    context = _request_context(
        original_request=original_request,
        generation_summary=generation_summary,
        batch_id=batch_id,
        job_id=job_id,
        duration_seconds=duration_seconds,
        media_probe=media_probe,
    )
    context["video_input"] = video_instruction
    comparison_instruction=""
    if reference_video_data_url:
        context["upscale_comparison"]={
            "enabled":True,
            "reference_role":"selected_candidate",
            "result_role":"upscaled_result",
            "must_preserve":["character_identity","facial_proportions","costume","body_proportions",
                             "motion","timing","camera_composition","lip_timing"],
        }
        comparison_instruction=(
            "The first attached video is the selected candidate reference and the second is the "
            "upscaled result. Reject the result if upscaling changes character identity, face, "
            "costume, body proportions, motion trajectory, action timing, camera composition or "
            "lip timing. Confirm that useful detail improved without temporal flicker or invented "
            "anatomy. "
        )

    if observation is not None:
        system_prompt = COMPLIANCE_SYSTEM_PROMPT
        review_text = (
            comparison_instruction
            + "Compare the attached complete source video against the production "
            "request.\n\nPRODUCTION REQUEST AND METADATA:\n"
            + json.dumps(context,ensure_ascii=False,separators=(",", ":"))
            + "\n\nINDEPENDENT FIRST-PASS OBSERVATION:\n"
            + json.dumps(observation,ensure_ascii=False,separators=(",", ":"))
        )
    else:
        system_prompt = ONE_PASS_SYSTEM_PROMPT
        review_text = (
            comparison_instruction
            + "Review the attached complete source video against this production request:\n"
            + json.dumps(context,ensure_ascii=False,separators=(",", ":"))
        )

    (
        review_payload,
        review_message,
        review_raw,
    ) = _response_json(
        model=model,
        system_prompt=system_prompt,
        required_keys={
            "accepted",
            "confidence",
            "summary_ko",
            "requirement_checks",
            "issues",
            "recommended_action",
        },
        user_text=review_text,
        video_data_url=video_data_url,
        audio_data_url=audio_data_url,
        video_metadata=video_metadata,
        reference_video_data_url=reference_video_data_url,
        reference_video_metadata=reference_video_metadata,
    )

    report = _normalize_report(
        review_payload,
        duration_seconds=duration_seconds,
    )
    report.update(
        {
            "review_mode": (
                "direct_source_video_two_pass"
                if VLLM_VIDEO_REVIEW_TWO_PASS
                else "direct_source_video_one_pass"
            ),
            "video_transport": (
                review_payload.get("_video_transport")
                or VLLM_REVIEW_VIDEO_TRANSPORT
            ),
            "model": model,
            "batch_id": batch_id,
            "job_id": job_id,
            "video_local_path": str(video_path),
            "duration_seconds": round(duration_seconds, 3),
            "media_probe": media_probe,
            "video_input": video_metadata,
            "observation": observation,
            "raw_observation_response": observation_raw,
            "raw_response": review_raw,
        }
    )

    if VLLM_REVIEW_STORE_RAW_MESSAGE:
        report["raw_observation_message"] = observation_message
        report["raw_message"] = review_message

    return report
