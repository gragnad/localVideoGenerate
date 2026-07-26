from __future__ import annotations

import copy
import json
import math
import re
import secrets
import uuid
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable
from urllib.parse import quote


KOREAN_SPEECH_POLICY = (
    "LANGUAGE REQUIREMENT: All spoken dialogue, narration, voice-over, lyrics, "
    "and intelligible character vocalizations must be performed in natural Korean. "
    "Do not use English or any other language for speech. Non-verbal ambience and "
    "sound effects may remain language-neutral."
)
KOREAN_SPEECH_POLICY_MARKER = "LANGUAGE REQUIREMENT: All spoken dialogue"


@dataclass(frozen=True)
class SegmentSpec:
    image_name: str
    image_subfolder: str
    prompt: str
    requested_seconds: float
    order: int

    @property
    def image_file(self) -> str:
        return str(PurePosixPath(self.image_subfolder) / self.image_name)


@dataclass(frozen=True)
class SegmentRuntime:
    image_name: str
    image_subfolder: str
    image_file: str
    prompt: str
    requested_seconds: float
    actual_seconds: float
    start_frame: int
    frame_count: int
    order: int


def sanitize_token(value: str, fallback: str = "job") -> str:
    value = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", value.strip())
    value = value.strip("._-")
    return value[:80] or fallback


def resolve_seed(seed: int) -> int:
    if seed >= 0:
        return seed
    return secrets.randbelow((1 << 63) - 1)


def apply_korean_speech_policy(prompt: str) -> str:
    normalized = str(prompt or "").strip()
    if KOREAN_SPEECH_POLICY_MARKER in normalized:
        return normalized
    if normalized:
        return f"{normalized}\n\n{KOREAN_SPEECH_POLICY}"
    return KOREAN_SPEECH_POLICY


def _find_single_node(workflow: dict[str, Any], class_type: str) -> tuple[str, dict[str, Any]]:
    matches = [
        (node_id, node)
        for node_id, node in workflow.items()
        if isinstance(node, dict) and node.get("class_type") == class_type
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{class_type} 노드는 정확히 1개여야 합니다. 현재 개수: {len(matches)}"
        )
    return matches[0]


def allocate_frames(
    durations_seconds: Iterable[float],
    fps: int,
    target_total_seconds: float | None = None,
) -> list[int]:
    durations = [float(value) for value in durations_seconds]
    if not durations:
        raise ValueError("최소 한 개의 이미지 구간이 필요합니다.")
    if fps <= 0:
        raise ValueError("FPS는 1 이상이어야 합니다.")
    if any(value <= 0 for value in durations):
        raise ValueError("각 이미지 구간 시간은 0초보다 커야 합니다.")

    if target_total_seconds is None:
        return [max(1, int(round(value * fps))) for value in durations]

    target_frames = int(round(float(target_total_seconds) * fps))
    if target_frames < len(durations):
        minimum_seconds = len(durations) / fps
        raise ValueError(
            f"목표 총 길이가 너무 짧습니다. 현재 구간 수에서는 최소 {minimum_seconds:.3f}초가 필요합니다."
        )

    total_weight = sum(durations)
    remaining = target_frames - len(durations)
    raw_extra = [remaining * value / total_weight for value in durations]
    extra_floor = [math.floor(value) for value in raw_extra]
    frames = [1 + value for value in extra_floor]

    leftover = target_frames - sum(frames)
    ranking = sorted(
        range(len(durations)),
        key=lambda index: raw_extra[index] - extra_floor[index],
        reverse=True,
    )
    for index in ranking[:leftover]:
        frames[index] += 1
    return frames


def preview_segments(
    segments: list[SegmentSpec],
    fps: int,
    target_total_seconds: float | None,
) -> list[SegmentRuntime]:
    ordered = sorted(segments, key=lambda item: (item.order, item.image_name))
    frames = allocate_frames(
        (item.requested_seconds for item in ordered),
        fps=fps,
        target_total_seconds=target_total_seconds,
    )

    runtime: list[SegmentRuntime] = []
    start = 0
    for item, frame_count in zip(ordered, frames, strict=True):
        runtime.append(
            SegmentRuntime(
                image_name=item.image_name,
                image_subfolder=item.image_subfolder,
                image_file=item.image_file,
                prompt=item.prompt.strip(),
                requested_seconds=item.requested_seconds,
                actual_seconds=frame_count / fps,
                start_frame=start,
                frame_count=frame_count,
                order=item.order,
            )
        )
        start += frame_count
    return runtime


UPSCALE_IC_LORA_X2 = "ltx-2.3-22b-ic-lora-pixel-spatial-upscaler-x2-0.9.safetensors"
UPSCALE_DISTILLED_LORA = "ltx-2.3-22b-distilled-lora-384-1.1.safetensors"
UPSCALE_TEXT_ENCODER = "gemma_3_12B_it.safetensors"
TEXT_ENCODER_ALIASES = {
    "comfy_gemma_3_12B_it.safetensors": UPSCALE_TEXT_ENCODER,
}


def normalize_comfy_lora_name(value: str) -> str:
    name = str(value or "").strip().replace("\\", "/")
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    return name


def normalize_upscale_ic_lora_name(value: str) -> str:
    name = normalize_comfy_lora_name(value)
    if "pixel-spatial-upscaler-x4" in name:
        return UPSCALE_IC_LORA_X2
    return name.replace("x4-0.9", "x2-0.9")


def normalize_resize_image_mask_inputs(inputs: dict[str, Any]) -> None:
    resize_type = str(inputs.get("resize_type") or "")
    if resize_type == "scale dimensions":
        crop = inputs.pop("crop", None)
        if crop is not None and "resize_type.crop" not in inputs:
            inputs["resize_type.crop"] = crop


def normalize_upscale_workflow_template(workflow: dict[str, Any]) -> None:
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        class_type = str(node.get("class_type") or "")
        inputs = node.setdefault("inputs", {})
        if class_type == "LTXAVTextEncoderLoader" and "text_encoder" in inputs:
            current = str(inputs["text_encoder"] or "")
            inputs["text_encoder"] = TEXT_ENCODER_ALIASES.get(current, current)
        elif class_type in {"LoraLoaderModelOnly", "LTXICLoRALoaderModelOnly"}:
            for key in ("lora_name", "ic_lora_name"):
                if key not in inputs:
                    continue
                if class_type == "LTXICLoRALoaderModelOnly":
                    inputs[key] = normalize_upscale_ic_lora_name(str(inputs[key]))
                else:
                    current = normalize_comfy_lora_name(str(inputs[key]))
                    if "distilled-lora" in current:
                        inputs[key] = UPSCALE_DISTILLED_LORA
                    else:
                        inputs[key] = current
        elif class_type == "ResizeImageMaskNode":
            normalize_resize_image_mask_inputs(inputs)


def build_upscale_workflow(
    *,
    template: dict[str, Any],
    source_video_name: str,
    source_video_subfolder: str,
    filename_prefix: str,
    prompt: str,
    seed: int,
    width: int,
    height: int,
    ic_lora_strength: float,
    sigmas: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    workflow=copy.deepcopy(template)
    normalize_upscale_workflow_template(workflow)

    def single(class_type: str)->dict[str,Any]:
        matches=[node for node in workflow.values() if node.get("class_type")==class_type]
        if len(matches)!=1:raise ValueError(f"업스케일 API 워크플로에 {class_type} 노드가 정확히 하나 필요합니다.")
        return matches[0]

    load_video=single("LoadVideo")
    video_value=str(PurePosixPath(source_video_subfolder)/source_video_name)
    video_key=next((key for key in ("file","video","video_path","filename") if key in load_video.get("inputs",{})),None)
    if video_key is None:raise ValueError("LoadVideo 입력 파일 필드를 찾을 수 없습니다.")
    load_video["inputs"][video_key]=video_value

    target_nodes=[node for node in workflow.values() if node.get("class_type")=="ResizeImageMaskNode"
                  and str((node.get("_meta") or {}).get("title") or "")=="UPSCALE_TARGET_SIZE"]
    if len(target_nodes)!=1:raise ValueError("UPSCALE_TARGET_SIZE 제목의 ResizeImageMaskNode가 정확히 하나 필요합니다.")
    target_inputs=target_nodes[0]["inputs"]
    for key in tuple(target_inputs):
        if key.startswith("resize_type.") or key == "crop":
            target_inputs.pop(key)
    target_inputs.update({"resize_type":"scale dimensions","resize_type.width":int(width),
                          "resize_type.height":int(height),"resize_type.crop":"center","scale_method":"lanczos"})

    lora=single("LTXICLoRALoaderModelOnly")
    for key in ("ic_lora_name","lora_name"):
        if key in lora.get("inputs",{}):
            lora["inputs"][key]=UPSCALE_IC_LORA_X2
    strength_key=next((key for key in ("strength","ic_lora_strength","strength_model") if key in lora.get("inputs",{})),None)
    if strength_key is None:raise ValueError("Pixel Spatial Upscaler IC-LoRA 강도 필드를 찾을 수 없습니다.")
    lora["inputs"][strength_key]=float(ic_lora_strength)

    single("ManualSigmas")["inputs"]["sigmas"]=str(sigmas)
    single("RandomNoise")["inputs"]["noise_seed"]=int(seed)
    single("SaveVideo")["inputs"]["filename_prefix"]=filename_prefix

    prompt_nodes=[node for node in workflow.values() if node.get("class_type")=="CLIPTextEncode"
                  and str((node.get("_meta") or {}).get("title") or "")=="UPSCALE_POSITIVE_PROMPT"]
    if len(prompt_nodes)!=1:raise ValueError("UPSCALE_POSITIVE_PROMPT 제목의 CLIPTextEncode가 정확히 하나 필요합니다.")
    prompt_nodes[0]["inputs"]["text"]=prompt

    return workflow,{"source_video":video_value,"filename_prefix":filename_prefix,"seed":int(seed),
                     "width":int(width),"height":int(height),"resolution":f"{width}x{height}",
                     "ic_lora_strength":float(ic_lora_strength),"sigmas":str(sigmas),
                     "audio_policy":"preserve_source_audio"}

def build_workflow(
    template: dict[str, Any],
    segments: list[SegmentSpec],
    global_prompt: str,
    fps: int,
    seed: int,
    filename_prefix: str,
    target_total_seconds: float | None = None,
    width: int = 1024,
    height: int = 576,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if width <= 0 or height <= 0:
        raise ValueError("출력 해상도는 1 이상이어야 합니다.")
    if width % 32 != 0 or height % 32 != 0:
        raise ValueError(
            f"출력 해상도는 가로·세로 모두 32의 배수여야 합니다: {width}x{height}"
        )

    target_ratio = 16 / 9
    actual_ratio = width / height
    ratio_error = abs(actual_ratio - target_ratio) / target_ratio
    if ratio_error > 0.03:
        raise ValueError(
            "출력 해상도는 16:9 계열 비율이어야 합니다 "
            f"(허용 오차 3%): {width}x{height}"
        )

    workflow = copy.deepcopy(template)
    _, director = _find_single_node(workflow, "LTXDirector")
    _, noise = _find_single_node(workflow, "RandomNoise")
    _, save_video = _find_single_node(workflow, "SaveVideo")

    runtime = preview_segments(segments, fps=fps, target_total_seconds=target_total_seconds)
    total_frames = sum(item.frame_count for item in runtime)
    total_seconds = total_frames / fps

    try:
        timeline = json.loads(director["inputs"]["timeline_data"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("LTXDirector.timeline_data를 해석할 수 없습니다.") from exc

    effective_global_prompt = apply_korean_speech_policy(global_prompt)
    timeline_segments: list[dict[str, Any]] = []
    for item in runtime:
        filename_q = quote(item.image_name, safe="")
        subfolder_q = quote(item.image_subfolder, safe="/")
        timeline_segments.append(
            {
                "id": uuid.uuid4().hex[:20],
                "start": item.start_frame,
                "length": item.frame_count,
                "prompt": apply_korean_speech_policy(item.prompt),
                "type": "image",
                "imageFile": item.image_file,
                "imageB64": (
                    f"/api/view?filename={filename_q}&type=input&subfolder={subfolder_q}"
                ),
                "isEndFrame": False,
            }
        )

    timeline["global_prompt"] = effective_global_prompt
    timeline["normalStartFrame"] = 0
    timeline["normalDurationFrames"] = total_frames
    timeline["segments"] = timeline_segments
    timeline["motionSegments"] = []
    timeline["audioSegments"] = []

    inputs = director["inputs"]
    inputs["start_second"] = 0
    inputs["end_second"] = total_seconds
    inputs["duration_seconds"] = total_seconds
    inputs["start_frame"] = 0
    inputs["end_frame"] = total_frames
    inputs["duration_frames"] = total_frames
    inputs["timeline_data"] = json.dumps(timeline, ensure_ascii=False, separators=(",", ":"))
    inputs["local_prompts"] = " | ".join(
        apply_korean_speech_policy(item.prompt) for item in runtime
    )
    inputs["segment_lengths"] = ",".join(str(item.frame_count) for item in runtime)
    inputs["guide_strength"] = ",".join("1.00" for _ in runtime)
    inputs["frame_rate"] = fps
    inputs["custom_width"] = int(width)
    inputs["custom_height"] = int(height)
    inputs["resize_method"] = "maintain aspect ratio"

    noise["inputs"]["noise_seed"] = int(seed)
    save_video["inputs"]["filename_prefix"] = filename_prefix

    summary = {
        "seed": int(seed),
        "fps": fps,
        "total_frames": total_frames,
        "total_seconds": total_seconds,
        "filename_prefix": filename_prefix,
        "global_prompt": effective_global_prompt,
        "language_policy": "spoken_korean_required",
        "width": int(width),
        "height": int(height),
        "resolution": f"{width}x{height}",
        "segments": [
            {
                **asdict(item),
                "effective_prompt": apply_korean_speech_policy(item.prompt),
            }
            for item in runtime
        ],
    }
    return workflow, summary


def build_retake_workflow(
    *,
    template: dict[str, Any],
    segments: list[SegmentSpec],
    global_prompt: str,
    fps: int,
    seed: int,
    filename_prefix: str,
    retake_video_name: str,
    retake_video_subfolder: str,
    retake_video_size_bytes: int,
    retake_video_duration_seconds: float | None,
    retake_start_seconds: float,
    retake_end_seconds: float,
    retake_prompt: str,
    retake_strength: float,
    target_total_seconds: float | None = None,
    width: int = 1024,
    height: int = 576,
) -> tuple[dict[str, Any], dict[str, Any]]:
    workflow, summary = build_workflow(
        template=template,
        segments=segments,
        global_prompt=global_prompt,
        fps=fps,
        seed=seed,
        filename_prefix=filename_prefix,
        target_total_seconds=target_total_seconds,
        width=width,
        height=height,
    )
    _, director = _find_single_node(workflow, "LTXDirector")
    planned_frames = int(summary["total_frames"])
    source_frames = int(round(float(retake_video_duration_seconds or 0.0) * fps))
    total_frames = max(planned_frames, source_frames)
    total_seconds = total_frames / fps
    director["inputs"]["end_second"] = total_seconds
    director["inputs"]["duration_seconds"] = total_seconds
    director["inputs"]["end_frame"] = total_frames
    director["inputs"]["duration_frames"] = total_frames
    start_frame = max(0, min(total_frames - 1, math.floor(retake_start_seconds * fps)))
    end_frame = max(start_frame + 1, min(total_frames, math.ceil(retake_end_seconds * fps)))
    retake_length = end_frame - start_frame
    strength = max(0.0, min(1.0, float(retake_strength)))
    correction = apply_korean_speech_policy(retake_prompt)
    video_file = str(
        PurePosixPath(retake_video_subfolder) / retake_video_name
        if retake_video_subfolder
        else PurePosixPath(retake_video_name)
    )

    timeline = json.loads(director["inputs"]["timeline_data"])
    timeline.update(
        {
            "retake_global_prompt": apply_korean_speech_policy(global_prompt),
            "retakeMode": True,
            "retakeStart": start_frame,
            "retakeLength": retake_length,
            "retakePrompt": correction,
            "retakeStrength": strength,
            "retakeVideo": {
                "fileName": retake_video_name,
                "imageFile": video_file,
                "videoDurationFrames": total_frames,
                "fileSize": int(retake_video_size_bytes),
            },
        }
    )
    director["inputs"]["timeline_data"] = json.dumps(
        timeline,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    prompt_parts: list[str] = []
    length_parts: list[str] = []
    strength_parts: list[str] = []
    if start_frame > 0:
        prompt_parts.append("video")
        length_parts.append(str(start_frame))
        strength_parts.append("0.00")
    prompt_parts.append(correction)
    length_parts.append(str(retake_length))
    strength_parts.append(f"{strength:.2f}")
    tail_frames = total_frames - end_frame
    if tail_frames > 0:
        prompt_parts.append("video")
        length_parts.append(str(tail_frames))
        strength_parts.append("0.00")

    director["inputs"]["local_prompts"] = " | ".join(prompt_parts)
    director["inputs"]["segment_lengths"] = ",".join(length_parts)
    director["inputs"]["guide_strength"] = ",".join(strength_parts)
    for node in workflow.values():
        if isinstance(node, dict) and node.get("class_type") == "LTXDirectorGuide":
            node.setdefault("inputs", {})["retake_mode"] = True

    summary.update(
        {
            "mode": "partial_retake",
            "total_frames": total_frames,
            "total_seconds": total_seconds,
            "source_video_frames": total_frames,
            "retake_start_frame": start_frame,
            "retake_end_frame": end_frame,
            "retake_length_frames": retake_length,
            "retake_start_seconds": start_frame / fps,
            "retake_end_seconds": end_frame / fps,
            "retake_strength": strength,
            "retake_video": video_file,
            "retake_prompt": correction,
        }
    )
    return workflow, summary
