from __future__ import annotations

"""Static ComfyUI graph-to-API prompt conversion helpers."""

from typing import Any


WIDGET_SCHEMAS: dict[str, tuple[str, ...]] = {
    "CFGGuider": ("cfg",),
    "CheckpointLoaderSimple": ("ckpt_name",),
    "CLIPTextEncode": ("text",),
    "ComfyMathExpression": ("expression",),
    "CreateVideo": ("fps", "bit_depth"),
    "KSamplerSelect": ("sampler_name",),
    "LoraLoaderModelOnly": ("lora_name", "strength_model"),
    "LoadVideo": ("file",),
    "ManualSigmas": ("sigmas",),
    "RandomNoise": ("noise_seed",),
    "SaveImage": ("filename_prefix",),
    "SaveVideo": ("filename_prefix", "format", "codec"),
    "LoadImage": ("image",),
    "GetFrameByIndex": ("index",),
    "INTConstant": ("value",),
    "FloatConstant": ("value",),
    "SimpleMath+": ("expression",),
}

FRONTEND_WIDGET_STATE_NODES = {"PreviewAny"}


def _graph_widget_schema(source: dict[str, Any]) -> tuple[str, ...]:
    """Read widget order embedded by current ComfyUI graph JSON."""
    return tuple(
        str(item["name"])
        for item in source.get("inputs") or []
        if isinstance(item.get("widget"), dict) and item.get("name")
    )


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
    """Convert a supported ComfyUI graph without starting ComfyUI."""
    nodes = workflow.get("nodes")
    links = workflow.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise ValueError("ComfyUI graph 형식(nodes/links)이 아닙니다.")

    active_nodes = {
        int(node["id"]): node
        for node in nodes
        if int(node.get("mode", 0)) == 0 and node.get("type") != "Note"
    }
    api_ids = {
        node_id
        for node_id, node in active_nodes.items()
        if node.get("type") != "Reroute"
    }
    raw_links = {int(link[0]): link for link in links}

    def resolve_source(node_id: int, output_slot: int, seen: set[int] | None = None) -> list[Any]:
        node = active_nodes.get(node_id)
        if node is None:
            raise ValueError(f"비활성 또는 누락된 연결 소스 노드입니다: {node_id}")
        if node.get("type") != "Reroute":
            return [str(node_id), int(output_slot)]
        visited = set(seen or ())
        if node_id in visited:
            raise ValueError(f"Reroute 순환 연결을 발견했습니다: {node_id}")
        visited.add(node_id)
        input_link = next(
            (item.get("link") for item in node.get("inputs") or [] if item.get("link") is not None),
            None,
        )
        if input_link is None or int(input_link) not in raw_links:
            raise ValueError(f"입력 연결이 없는 Reroute 노드입니다: {node_id}")
        link = raw_links[int(input_link)]
        return resolve_source(int(link[1]), int(link[2]), visited)

    link_sources: dict[int, list[Any]] = {}
    for link in links:
        source_id, target_id = int(link[1]), int(link[3])
        if source_id in active_nodes and target_id in api_ids:
            link_sources[int(link[0])] = resolve_source(source_id, int(link[2]))

    output: dict[str, Any] = {}
    for source in nodes:
        if (
            int(source.get("mode", 0)) != 0
            or source.get("type") in {"Note", "MarkdownNote", "Reroute"}
        ):
            continue
        node_id = str(source["id"])
        class_type = str(source["type"])
        widget_values = list(source.get("widgets_values") or [])
        if class_type == "ResizeImageMaskNode":
            inputs = _resize_widgets(widget_values)
        else:
            schema = WIDGET_SCHEMAS.get(class_type) or _graph_widget_schema(source)
            if widget_values and not schema and class_type not in FRONTEND_WIDGET_STATE_NODES:
                raise ValueError(f"widget 스키마가 정의되지 않은 노드입니다: {class_type} ({node_id})")
            inputs = dict(zip(schema or (), widget_values, strict=False))

        for input_spec in source.get("inputs") or []:
            link_id = input_spec.get("link")
            if link_id is not None and int(link_id) in link_sources:
                inputs[str(input_spec["name"])] = link_sources[int(link_id)]

        title = source.get("title") or class_type
        output[node_id] = {
            "inputs": inputs,
            "class_type": class_type,
            "_meta": {"title": str(title)},
        }
    return output
