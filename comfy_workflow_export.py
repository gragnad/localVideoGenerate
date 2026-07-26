from __future__ import annotations

"""Static ComfyUI workflow (graph) to API prompt conversion helpers.

This module intentionally does not import or start ComfyUI.  The widget schema is
limited to the nodes used by the bundled LTX 2.3 Pixel Spatial Upscaler workflow.
"""

import copy
from typing import Any

from workflow_builder import normalize_upscale_workflow_template


WIDGET_SCHEMAS: dict[str, tuple[str, ...]] = {
    "CFGGuider": ("cfg",),
    "CheckpointLoaderSimple": ("ckpt_name",),
    "CLIPTextEncode": ("text",),
    "ComfyMathExpression": ("expression",),
    "CreateVideo": ("fps",),
    "KSamplerSelect": ("sampler_name",),
    "LoraLoaderModelOnly": ("lora_name", "strength_model"),
    "LTXAVTextEncoderLoader": ("text_encoder", "ckpt_name", "device"),
    "LTXAddVideoICLoRAGuide": (
        "frame_idx", "strength", "latent_downscale_factor", "crop",
        "use_tiled_encode", "tile_size", "tile_overlap",
    ),
    "LTXICLoRALoaderModelOnly": ("lora_name", "strength_model"),
    "LTXVAudioVAELoader": ("ckpt_name",),
    "LTXVConditioning": ("frame_rate",),
    "LTXVTiledVAEDecode": (
        "horizontal_tiles", "vertical_tiles", "overlap", "last_frame_fix",
        "working_device", "working_dtype",
    ),
    "LoadVideo": ("file",),
    "ManualSigmas": ("sigmas",),
    "RandomNoise": ("noise_seed",),
    "SaveVideo": ("filename_prefix", "format", "codec"),
}


def _resize_widgets(values: list[Any]) -> dict[str, Any]:
    if not values:
        raise ValueError("ResizeImageMaskNode widget 값이 없습니다.")
    resize_type = str(values[0])
    output: dict[str, Any] = {"resize_type": resize_type}
    if resize_type == "scale dimensions":
        names = ("resize_type.width", "resize_type.height", "resize_type.crop", "scale_method")
    elif resize_type == "scale by multiplier":
        names = ("resize_type.multiplier", "scale_method")
    elif resize_type == "scale longer dimension":
        names = ("resize_type.longer_size", "scale_method")
    elif resize_type == "scale shorter dimension":
        names = ("resize_type.shorter_size", "scale_method")
    elif resize_type == "scale width":
        names = ("resize_type.width", "scale_method")
    elif resize_type == "scale height":
        names = ("resize_type.height", "scale_method")
    elif resize_type == "scale total pixels":
        names = ("resize_type.megapixels", "scale_method")
    elif resize_type == "scale to multiple":
        names = ("resize_type.multiple", "scale_method")
    else:
        raise ValueError(f"지원하지 않는 ResizeImageMaskNode 방식입니다: {resize_type}")
    if len(values) < len(names) + 1:
        raise ValueError(f"{resize_type} widget 값이 부족합니다: {values!r}")
    output.update(zip(names, values[1:], strict=False))
    return output


def graph_to_api(workflow: dict[str, Any]) -> dict[str, Any]:
    """Convert the installed official LTX upscaler graph without running ComfyUI."""
    nodes = workflow.get("nodes")
    links = workflow.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise ValueError("ComfyUI graph 형식(nodes/links)이 아닙니다.")

    link_sources = {int(link[0]): [str(link[1]), int(link[2])] for link in links}
    output: dict[str, Any] = {}
    for source in nodes:
        if int(source.get("mode", 0)) != 0 or source.get("type") == "Note":
            continue
        node_id = str(source["id"])
        class_type = str(source["type"])
        widget_values = list(source.get("widgets_values") or [])
        if class_type == "ResizeImageMaskNode":
            inputs = _resize_widgets(widget_values)
        else:
            schema = WIDGET_SCHEMAS.get(class_type, ())
            if widget_values and not schema:
                raise ValueError(f"widget 스키마가 정의되지 않은 노드입니다: {class_type} ({node_id})")
            inputs = dict(zip(schema, widget_values, strict=False))

        for input_spec in source.get("inputs") or []:
            link_id = input_spec.get("link")
            if link_id is not None:
                inputs[str(input_spec["name"])] = link_sources[int(link_id)]

        title = source.get("title") or class_type
        output[node_id] = {
            "inputs": inputs,
            "class_type": class_type,
            "_meta": {"title": str(title)},
        }
    return output


def mark_upscale_controls(prompt: dict[str, Any]) -> dict[str, Any]:
    """Mark the stable controls patched by video-engine at job execution time."""
    result = copy.deepcopy(prompt)
    expected = {
        "5007": ("ResizeImageMaskNode", "UPSCALE_TARGET_SIZE"),
        "2483": ("CLIPTextEncode", "UPSCALE_POSITIVE_PROMPT"),
    }
    for node_id, (class_type, title) in expected.items():
        node = result.get(node_id)
        if not node or node.get("class_type") != class_type:
            raise ValueError(f"공식 업스케일 워크플로 노드 {node_id} ({class_type})를 찾을 수 없습니다.")
        node.setdefault("_meta", {})["title"] = title
    normalize_upscale_workflow_template(result)
    return result
