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
VLLM_REVIEW_TOP_P = float(os.environ.get("VLLM_REVIEW_TOP_P", "0.95"))
VLLM_REVIEW_TOP_K = int(os.environ.get("VLLM_REVIEW_TOP_K", "20"))
VLLM_REVIEW_REASONING_EFFORT = os.environ.get(
    "VLLM_REVIEW_REASONING_EFFORT", ""
).strip()
VLLM_REVIEW_ENABLE_THINKING = (
    os.environ.get("VLLM_REVIEW_ENABLE_THINKING", "true")
    .strip()
    .lower()
    not in {"0", "false", "no", "off"}
)
VLLM_REVIEW_USE_AUDIO_IN_VIDEO = (
    os.environ.get("VLLM_REVIEW_USE_AUDIO_IN_VIDEO", "auto")
    .strip()
    .lower()
)
VLLM_REVIEW_AUDIO_CAPABLE = (
    os.environ.get("VLLM_REVIEW_AUDIO_CAPABLE", "true")
    .strip()
    .lower()
    not in {"0", "false", "no", "off"}
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
VLLM_REVIEW_VIDEO_PROXY_MODE = os.environ.get(
    "VLLM_REVIEW_VIDEO_PROXY_MODE", "mjpeg_avi"
).strip().lower()


def _json_object_env(name: str) -> dict[str, Any]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} JSON 설정을 해석할 수 없습니다: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{name} 설정은 JSON 객체여야 합니다.")
    return payload


VLLM_REVIEW_MM_PROCESSOR_KWARGS = _json_object_env(
    "VLLM_REVIEW_MM_PROCESSOR_KWARGS"
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
    if not VLLM_REVIEW_AUDIO_CAPABLE:
        return False
    if VLLM_REVIEW_USE_AUDIO_IN_VIDEO in {"1", "true", "yes", "on"}:
        return bool(media_probe.get("has_audio"))
    if VLLM_REVIEW_USE_AUDIO_IN_VIDEO in {"0", "false", "no", "off"}:
        return False
    return bool(media_probe.get("has_audio"))


def _prepare_review_video(video_path: Path) -> Path:
    if VLLM_REVIEW_VIDEO_PROXY_MODE in {"source", "original", "none"}:
        return video_path
    if VLLM_REVIEW_VIDEO_PROXY_MODE != "mjpeg_avi":
        raise VLLMReviewError(
            "지원하지 않는 영상 프록시 모드입니다: "
            f"{VLLM_REVIEW_VIDEO_PROXY_MODE}"
        )
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
    using_source = review_path.resolve() == video_path.resolve()
    suffix = review_path.suffix.lower()
    mime_type = {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".avi": "video/x-msvideo",
    }.get(suffix, "application/octet-stream")
    return (
        f"data:{mime_type};base64,{encoded}",
        {
            "transport": VLLM_REVIEW_VIDEO_TRANSPORT,
            "mime_type": mime_type,
            "source_path": str(video_path),
            "source_size_bytes": video_path.stat().st_size,
            "review_video_path": str(review_path),
            "review_video_size_bytes": size_bytes,
            "encoded_size_bytes": len(encoded),
            "review_codec": "source" if using_source else "mjpeg",
            "review_fps": None if using_source else VLLM_REVIEW_PROXY_FPS,
            "review_max_width": None if using_source else VLLM_REVIEW_PROXY_MAX_WIDTH,
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
        "top_p": VLLM_REVIEW_TOP_P,
        "top_k": VLLM_REVIEW_TOP_K,
        "max_tokens": VLLM_REVIEW_MAX_TOKENS,
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
    if VLLM_REVIEW_MM_PROCESSOR_KWARGS:
        payload["mm_processor_kwargs"] = VLLM_REVIEW_MM_PROCESSOR_KWARGS
    payload["chat_template_kwargs"] = {
        "enable_thinking": VLLM_REVIEW_ENABLE_THINKING,
        "preserve_thinking": False,
    }
    if VLLM_REVIEW_REASONING_EFFORT:
        payload["reasoning_effort"] = VLLM_REVIEW_REASONING_EFFORT
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
    if response.status_code == 400:
        # OpenAI-compatible servers expose different optional generation and
        # multimodal fields. Keep the full Qwen profile first, then make one
        # conservative compatibility retry without changing the messages or
        # the video input itself.
        compatibility_payload = dict(payload)
        for optional_key in (
            "response_format",
            "top_k",
            "mm_processor_kwargs",
            "chat_template_kwargs",
            "reasoning_effort",
        ):
            compatibility_payload.pop(optional_key, None)
        response = requests.post(
            f"{VLLM_URL}/v1/chat/completions",
            json=compatibility_payload,
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
