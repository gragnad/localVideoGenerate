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
DIRECTOR_PROMPT_RELAY_EPSILON = 0.5
DIRECTOR_AUDIO_PROMPT_RELAY_EPSILON = 0.01
DIRECTOR_IMAGE_GUIDE_STRENGTH = 0.75
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
    relay_options = timeline.setdefault("relayOptions", {})
    relay_options["audioEpsilon"] = DIRECTOR_AUDIO_PROMPT_RELAY_EPSILON

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
    inputs["guide_strength"] = ",".join(f"{DIRECTOR_IMAGE_GUIDE_STRENGTH:.2f}" for _ in runtime)
    inputs["epsilon"] = DIRECTOR_PROMPT_RELAY_EPSILON
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
        "prompt_relay_epsilon": DIRECTOR_PROMPT_RELAY_EPSILON,
        "audio_prompt_relay_epsilon": DIRECTOR_AUDIO_PROMPT_RELAY_EPSILON,
        "image_guide_strength": DIRECTOR_IMAGE_GUIDE_STRENGTH,
        "segments": [
            {
                **asdict(item),
                "effective_prompt": apply_korean_speech_policy(item.prompt),
            }
            for item in runtime
        ],
    }
    return workflow, summary


MSR_V2_LORA = "LTX-2.3-Licon-MSR-V2.safetensors"


def _msr_node(workflow: dict[str, Any], node_id: str, class_type: str) -> dict[str, Any]:
    node = workflow.get(node_id)
    if not isinstance(node, dict) or node.get("class_type") != class_type:
        raise ValueError(f"MSR V2 워크플로 노드 {node_id} ({class_type})를 찾을 수 없습니다.")
    return node


def build_msr_v2_workflow(
    *,
    template: dict[str, Any],
    references: list[dict[str, str]],
    background: dict[str, str],
    relay_segments: list[dict[str, Any]],
    global_prompt: str,
    seed: int,
    filename_prefix: str,
    width: int,
    height: int,
    epsilon: float = 0.0011,
    reference_frame_count: int = 65,
    maximum_duration_seconds: float | None = None,
    prompt_strategy: str = "legacy_msr_v2",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build MSR V2 while preserving the semantic meaning of reference slots 1-4."""
    if not 1 <= len(references) <= 4:
        raise ValueError("MSR V2 참조 이미지는 1~4장이어야 합니다.")
    slotted: dict[int, dict[str, str]] = {}
    for index, reference in enumerate(references, 1):
        slot = int(reference.get("slot") or index)
        if slot < 1 or slot > 4:
            raise ValueError(f"MSR V2 참조 슬롯은 1~4만 가능합니다: {slot}")
        if slot in slotted:
            raise ValueError(f"MSR V2 참조 슬롯이 중복되었습니다: {slot}")
        slotted[slot] = reference
    if 1 not in slotted:
        raise ValueError("MSR V2 캐릭터 참조 슬롯 1은 필수입니다.")
    if width <= 0 or height <= 0 or width % 32 or height % 32:
        raise ValueError("MSR V2 해상도는 가로·세로 모두 32의 배수여야 합니다.")
    if not relay_segments:
        raise ValueError("프롬프트 릴레이 구간을 한 개 이상 입력하세요.")
    durations = [float(item.get("seconds") or 0) for item in relay_segments]
    if any(value <= 0 for value in durations):
        raise ValueError("각 프롬프트 릴레이 시간은 0초보다 커야 합니다.")
    requested_seconds = sum(durations)
    if maximum_duration_seconds is not None and requested_seconds > float(maximum_duration_seconds) + 1e-6:
        raise ValueError(
            f"MSR 연속 생성은 최대 {float(maximum_duration_seconds):g}초입니다. "
            f"현재 합계: {requested_seconds:g}초"
        )
    prompts = [str(item.get("prompt") or "").strip() for item in relay_segments]
    if any(not prompt for prompt in prompts):
        raise ValueError("모든 프롬프트 릴레이 구간에 프롬프트가 필요합니다.")

    fps = 24
    segment_frames = allocate_frames(durations, fps)
    raw_total = sum(segment_frames)
    total_frames = ((max(1, raw_total) - 1 + 7) // 8) * 8 + 1
    if maximum_duration_seconds is not None and total_frames / fps > float(maximum_duration_seconds):
        frame_cap = max(1, int(math.floor(float(maximum_duration_seconds) * fps)))
        total_frames = ((frame_cap - 1) // 8) * 8 + 1
    adjustment = total_frames - raw_total
    if adjustment >= 0:
        segment_frames[-1] += adjustment
    else:
        remaining = -adjustment
        for index in range(len(segment_frames) - 1, -1, -1):
            removable = max(0, segment_frames[index] - 1)
            take = min(removable, remaining)
            segment_frames[index] -= take
            remaining -= take
            if remaining == 0:
                break
        if remaining:
            raise ValueError("MSR 프레임 길이를 유효한 범위로 조정할 수 없습니다.")

    workflow = copy.deepcopy(template)
    load_ids = {1: "29", 2: "33", 3: "196", 4: "201"}
    msr = _msr_node(workflow, "190", "LiconMSR")
    for slot, node_id in load_ids.items():
        reference = slotted.get(slot)
        if reference is None:
            workflow.pop(node_id, None)
            msr["inputs"].pop(str(slot), None)
            continue
        node = _msr_node(workflow, node_id, "LoadImage")
        node["inputs"]["image"] = str(
            PurePosixPath(reference.get("subfolder", "")) / reference["name"]
        )
    _msr_node(workflow, "194", "LoadImage")["inputs"]["image"] = str(
        PurePosixPath(background.get("subfolder", "")) / background["name"]
    )

    _msr_node(workflow, "43", "INTConstant")["inputs"]["value"] = int(width)
    _msr_node(workflow, "44", "INTConstant")["inputs"]["value"] = int(height)
    _msr_node(workflow, "50", "INTConstant")["inputs"]["value"] = total_frames
    _msr_node(workflow, "129", "FloatConstant")["inputs"]["value"] = fps
    _msr_node(workflow, "15", "RandomNoise")["inputs"]["noise_seed"] = int(seed)
    _msr_node(workflow, "172", "CreateVideo")["inputs"]["fps"] = fps
    _msr_node(workflow, "7", "LTXVConditioning")["inputs"]["frame_rate"] = fps
    audio = _msr_node(workflow, "22", "LTXVEmptyLatentAudio")["inputs"]
    audio.update(frames_number=total_frames, frame_rate=fps)
    msr["inputs"].update(width=int(width), height=int(height), frame_count=str(reference_frame_count))
    lora = _msr_node(workflow, "10", "LTXICLoRALoaderModelOnly")["inputs"]
    lora.update(lora_name=MSR_V2_LORA)
    relay = _msr_node(workflow, "180", "PromptRelayEncode")["inputs"]
    effective_global = str(global_prompt or "").strip()
    if prompt_strategy != "msr_continuity_v1":
        effective_global = apply_korean_speech_policy(effective_global)
    elif not effective_global:
        raise ValueError("MSR 연속 생성 글로벌 프롬프트가 비어 있습니다.")
    effective_prompts = [apply_korean_speech_policy(prompt) for prompt in prompts]
    relay.update(
        global_prompt=effective_global,
        local_prompts=" | ".join(effective_prompts),
        segment_lengths=",".join(str(value) for value in segment_frames),
        epsilon=float(epsilon),
    )
    _msr_node(workflow, "173", "SaveVideo")["inputs"]["filename_prefix"] = filename_prefix
    return workflow, {
        "mode": "msr_sequence_v2" if prompt_strategy == "msr_continuity_v1" else "msr_v2",
        "prompt_strategy": prompt_strategy,
        "fps": fps,
        "seed": int(seed),
        "width": int(width),
        "height": int(height),
        "total_frames": total_frames,
        "total_seconds": total_frames / fps,
        "requested_seconds": requested_seconds,
        "segment_frames": segment_frames,
        "reference_count": len(slotted),
        "reference_slots": sorted(slotted),
        "reference_frame_count": int(reference_frame_count),
        "filename_prefix": filename_prefix,
        "global_prompt": effective_global,
        "language_policy": "spoken_korean_required",
    }


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
