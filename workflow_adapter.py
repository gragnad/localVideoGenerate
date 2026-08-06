from __future__ import annotations

"""Validated ComfyUI bindings and dry compilation for model benchmarks."""

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from comfy_workflow_export import graph_to_api
import evaluation_db

BINDING_KEYS = ("prompt", "negative_prompt", "seed", "width", "height", "fps", "duration_seconds", "frame_count", "audio_frame_count", "filename_prefix", "reference_image")
REQUIRED_BINDINGS = {"prompt"}
DEFAULTS = {"seed": 831913303995591, "width": 768, "height": 432, "fps": 24, "duration_seconds": 5, "frame_count": 121, "audio_frame_count": 121}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash_json(value: Any) -> str:
    return _hash_bytes(_json(value).encode("utf-8"))


def _profile(connection, workflow_profile_id: str):
    row = connection.execute("SELECT * FROM workflow_profiles WHERE workflow_profile_id=?", (workflow_profile_id,)).fetchone()
    if not row:
        raise ValueError("등록된 워크플로우 프로필을 찾을 수 없습니다.")
    return row


def load_api_workflow(connection, workflow_profile_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    row = _profile(connection, workflow_profile_id)
    path = Path(row["workflow_path"])
    if not path.is_file():
        raise FileNotFoundError(f"워크플로우 파일을 찾을 수 없습니다: {row['workflow_filename']}")
    raw = path.read_bytes()
    actual_hash = _hash_bytes(raw)
    if actual_hash != row["workflow_sha256"]:
        raise ValueError("등록 후 워크플로우 파일이 변경되었습니다. 새 프로필로 다시 등록하세요.")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("워크플로우 JSON을 읽을 수 없습니다.") from exc
    if row["workflow_format"] == "comfyui_ui":
        try:
            payload = graph_to_api(payload)
        except ValueError as exc:
            raise ValueError(f"UI 워크플로우를 API 형식으로 변환할 수 없습니다: {exc}") from exc
    if not isinstance(payload, dict) or not payload or any(not isinstance(node, dict) or "class_type" not in node for node in payload.values()):
        raise ValueError("ComfyUI API 워크플로우 형식이 아닙니다.")
    return payload, dict(row)


def inspect_workflow(connection, workflow_profile_id: str) -> dict[str, Any]:
    workflow, profile = load_api_workflow(connection, workflow_profile_id)
    nodes = []
    options = []
    for node_id, node in workflow.items():
        inputs = dict(node.get("inputs") or {})
        title = str((node.get("_meta") or {}).get("title") or node.get("class_type") or node_id)
        scalar_inputs = []
        for input_name, value in inputs.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                option = {"node_id": str(node_id), "input": str(input_name), "class_type": str(node.get("class_type")), "title": title, "current_value": value}
                scalar_inputs.append(option)
                options.append(option)
        nodes.append({"node_id": str(node_id), "class_type": str(node.get("class_type")), "title": title, "scalar_inputs": scalar_inputs})
    def first_option(classes: tuple[str, ...], names: tuple[str, ...]):
        for class_type in classes:
            match = next(
                (
                    row for row in options
                    if row["class_type"] == class_type and row["input"] in names
                ),
                None,
            )
            if match:
                return {"node_id": match["node_id"], "input": match["input"]}
        return None

    def titled_option(title: str, input_name: str):
        match = next(
            (
                row for row in options
                if row["title"].strip().lower() == title.lower() and row["input"] == input_name
            ),
            None,
        )
        return {"node_id": match["node_id"], "input": match["input"]} if match else None

    def title_contains_option(fragment: str, input_name: str):
        match = next(
            (
                row for row in options
                if fragment.lower() in row["title"].strip().lower() and row["input"] == input_name
            ),
            None,
        )
        return {"node_id": match["node_id"], "input": match["input"]} if match else None

    suggestions = {
        "prompt": first_option(
            ("PrimitiveStringMultiline", "CLIPTextEncode", "TextGenerateLTX2Prompt", "MiniMaxH3ImageToVideo", "MiniMaxH3ReferenceToVideo"),
            ("value", "text", "prompt"),
        ),
        "negative_prompt": first_option(("CLIPTextEncode",), ("text",)),
        "reference_image": first_option(("LoadImage",), ("image",)),
        "seed": first_option(("RandomNoise",), ("noise_seed",)),
        "width": titled_option("Width", "value"),
        "height": titled_option("Height", "value"),
        "fps": titled_option("Frame Rate", "value"),
        "duration_seconds": titled_option("Duration", "value") or title_contains_option("duration", "value"),
        "frame_count": first_option(("EmptyLTXVLatentVideo", "LiconMSR"), ("length", "frame_count")),
        "audio_frame_count": first_option(("LTXVEmptyLatentAudio",), ("frames_number",)),
        "filename_prefix": first_option(("SaveVideo", "SaveImage"), ("filename_prefix",)),
    }
    return {
        "workflow_profile_id": workflow_profile_id,
        "workflow_filename": profile["workflow_filename"],
        "workflow_sha256": profile["workflow_sha256"],
        "workflow_format": profile["workflow_format"],
        "nodes": nodes,
        "binding_options": options,
        "suggested_bindings": {key: value for key, value in suggestions.items() if value},
    }


def _normalize_binding(raw: Any, key: str) -> dict[str, str] | None:
    if raw in (None, ""):
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{key} 바인딩 형식이 올바르지 않습니다.")
    node_id = str(raw.get("node_id") or "").strip()
    input_name = str(raw.get("input") or "").strip()
    if not node_id or not input_name:
        raise ValueError(f"{key} 바인딩의 노드와 입력 이름이 필요합니다.")
    return {"node_id": node_id, "input": input_name}


def validate_bindings(workflow: dict[str, Any], bindings: dict[str, Any]) -> dict[str, dict[str, str]]:
    normalized = {}
    unknown = set(bindings) - set(BINDING_KEYS)
    if unknown:
        raise ValueError(f"지원하지 않는 바인딩입니다: {', '.join(sorted(unknown))}")
    for key in BINDING_KEYS:
        binding = _normalize_binding(bindings.get(key), key)
        if not binding:
            continue
        node = workflow.get(binding["node_id"])
        if not node:
            raise ValueError(f"{key} 바인딩 노드가 없습니다: {binding['node_id']}")
        if binding["input"] not in dict(node.get("inputs") or {}):
            raise ValueError(f"{key} 입력이 노드에 없습니다: {binding['node_id']}.{binding['input']}")
        normalized[key] = binding
    missing = REQUIRED_BINDINGS - set(normalized)
    if missing:
        raise ValueError(f"필수 바인딩이 없습니다: {', '.join(sorted(missing))}")
    targets = [(row["node_id"], row["input"]) for row in normalized.values()]
    if len(targets) != len(set(targets)):
        raise ValueError("서로 다른 값이 같은 워크플로우 입력에 중복 바인딩되었습니다.")
    return normalized


def _validate_multi_reference(workflow: dict[str, Any], raw: Any) -> dict[str, Any] | None:
    if raw in (None, ""):
        return None
    if not isinstance(raw, dict):
        raise ValueError("다중 레퍼런스 설정 형식이 올바르지 않습니다.")
    conditioning_node_id = str(raw.get("conditioning_node_id") or "").strip()
    input_prefix = str(raw.get("input_prefix") or "ref_images.ref_image_").strip()
    loader_node_ids = [str(value).strip() for value in (raw.get("loader_node_ids") or []) if str(value).strip()]
    template_node_id = str(raw.get("loader_template_node_id") or (loader_node_ids[-1] if loader_node_ids else "")).strip()
    loader_input = str(raw.get("loader_input") or "image").strip()
    try:
        max_slots = int(raw.get("max_slots") or 9)
    except (TypeError, ValueError) as exc:
        raise ValueError("다중 레퍼런스 최대 개수는 숫자여야 합니다.") from exc
    conditioner = workflow.get(conditioning_node_id)
    if not conditioner or str(conditioner.get("class_type")) != "MiniMaxH3ReferenceToVideo":
        raise ValueError("MiniMax H3 R2V 컨디셔닝 노드를 찾을 수 없습니다.")
    if not input_prefix or max_slots < 1 or max_slots > 9:
        raise ValueError("다중 레퍼런스는 1~9장으로 설정해야 합니다.")
    if not loader_node_ids or not template_node_id:
        raise ValueError("다중 레퍼런스 LoadImage 노드가 필요합니다.")
    for node_id in set(loader_node_ids + [template_node_id]):
        node = workflow.get(node_id)
        if not node or str(node.get("class_type")) != "LoadImage" or loader_input not in dict(node.get("inputs") or {}):
            raise ValueError(f"다중 레퍼런스 이미지 로더가 올바르지 않습니다: {node_id}.{loader_input}")
    return {
        "conditioning_node_id": conditioning_node_id,
        "input_prefix": input_prefix,
        "loader_node_ids": loader_node_ids,
        "loader_template_node_id": template_node_id,
        "loader_input": loader_input,
        "max_slots": max_slots,
    }


def register_adapter(connection, data: dict[str, Any]) -> dict[str, Any]:
    workflow_profile_id = str(data.get("workflow_profile_id") or "").strip()
    if not workflow_profile_id:
        raise ValueError("워크플로우 프로필을 선택하세요.")
    workflow, _ = load_api_workflow(connection, workflow_profile_id)
    bindings = validate_bindings(workflow, dict(data.get("bindings") or {}))
    multi_reference = _validate_multi_reference(workflow, data.get("multi_reference"))
    adapter_name = str(data.get("adapter_name") or "ComfyUI binding adapter").strip()
    adapter_version = str(data.get("adapter_version") or "1").strip()
    if not adapter_name or not adapter_version:
        raise ValueError("어댑터 이름과 버전을 입력하세요.")
    prompt_template = str(data.get("prompt_template") or "{prompt}").strip()
    if "{prompt}" not in prompt_template:
        raise ValueError("프롬프트 템플릿에는 {prompt}가 필요합니다.")
    config = {"bindings": bindings, "prompt_template": prompt_template, "defaults": {**DEFAULTS, **dict(data.get("defaults") or {})}}
    if multi_reference:
        config["multi_reference"] = multi_reference
    adapter_id = f"adapter_{_hash_json({'profile': workflow_profile_id, 'name': adapter_name, 'version': adapter_version, 'config': config})[:24]}"
    connection.execute(
        """INSERT OR IGNORE INTO workflow_adapters
           (adapter_id,workflow_profile_id,adapter_name,adapter_version,config_json)
           VALUES (?,?,?,?,?)""",
        (adapter_id, workflow_profile_id, adapter_name, adapter_version, _json(config)),
    )
    connection.commit()
    return {"adapter_id": adapter_id, "workflow_profile_id": workflow_profile_id, "bindings": bindings}


def _render_prompt(template: str, canonical_prompt: str, intent_ko: str) -> str:
    return template.replace("{prompt}", canonical_prompt).replace("{intent_ko}", intent_ko)


def _format_case_value(value: Any, settings: dict[str, Any]) -> Any:
    if isinstance(value, str):
        try:
            return value.format_map(settings)
        except (KeyError, ValueError):
            return value
    if isinstance(value, list):
        return [_format_case_value(item, settings) for item in value]
    if isinstance(value, dict):
        return {key: _format_case_value(item, settings) for key, item in value.items()}
    return value


def _reference_role_index(role: str) -> int | None:
    prefix = "reference_image_"
    if not role.startswith(prefix):
        return None
    try:
        index = int(role[len(prefix):])
    except ValueError:
        return None
    return index if index >= 1 else None


def compile_case(connection, session: Any, case_version_id: str, repetition: int = 1) -> dict[str, Any]:
    adapter = connection.execute("SELECT * FROM workflow_adapters WHERE adapter_id=?", (session["adapter_id"],)).fetchone()
    if not adapter:
        raise ValueError("테스트 세션에 검증된 어댑터가 연결되지 않았습니다.")
    workflow, profile = load_api_workflow(connection, session["workflow_profile_id"])
    config = json.loads(adapter["config_json"])
    bindings = validate_bindings(workflow, dict(config.get("bindings") or {}))
    multi_reference = _validate_multi_reference(workflow, config.get("multi_reference"))
    case = connection.execute("SELECT * FROM benchmark_case_versions WHERE case_version_id=?", (case_version_id,)).fetchone()
    if not case:
        raise ValueError("테스트 케이스 버전을 찾을 수 없습니다.")
    session_case = connection.execute(
        "SELECT settings_json FROM test_session_cases WHERE session_id=? AND case_version_id=?",
        (session["session_id"], case_version_id),
    ).fetchone()
    case_settings = json.loads(session_case["settings_json"] or "{}") if session_case else {}
    prompt_row = connection.execute("SELECT prompt_text FROM benchmark_case_prompts WHERE case_version_id=? AND language='en' AND prompt_kind='canonical'", (case_version_id,)).fetchone()
    if not prompt_row:
        return {"case_version_id": case_version_id, "status": "blocked", "blockers": ["영문 정규 프롬프트가 없습니다."]}
    requirements = [dict(row) for row in connection.execute("SELECT role,kind,minimum_count,description FROM benchmark_case_asset_requirements WHERE case_version_id=?", (case_version_id,))]
    linked = [dict(row) for row in connection.execute("SELECT l.role,l.ordering,a.asset_id,a.sha256,a.path FROM benchmark_case_assets l JOIN assets a ON a.asset_id=l.asset_id WHERE l.case_version_id=? ORDER BY l.role,l.ordering", (case_version_id,))]
    blockers = []
    for requirement in requirements:
        role = str(requirement["role"])
        count = sum(1 for item in linked if item["role"] == role)
        if count < int(requirement["minimum_count"]):
            blockers.append(f"테스트 자산 필요: {role} ({requirement['minimum_count']}개)")
        is_multi_role = multi_reference is not None and _reference_role_index(role) is not None
        if not is_multi_role and role not in bindings:
            blockers.append(f"어댑터 이미지 바인딩 필요: {role}")
    selected_width = session["output_width"] if "output_width" in session.keys() else None
    selected_height = session["output_height"] if "output_height" in session.keys() else None
    if selected_width and selected_height:
        missing_resolution = [key for key in ("width", "height") if key not in bindings]
        if missing_resolution:
            blockers.append("선택 해상도 적용 바인딩 필요: " + ", ".join(missing_resolution))
    multi_assets = sorted(
        ((index, item) for item in linked if (index := _reference_role_index(str(item["role"]))) is not None),
        key=lambda pair: pair[0],
    )
    if multi_assets:
        indexes = [index for index, _ in multi_assets]
        if not multi_reference:
            blockers.append("R2V 다중 레퍼런스 어댑터 설정이 필요합니다.")
        elif indexes != list(range(1, len(indexes) + 1)):
            blockers.append("R2V 레퍼런스는 Picture 1부터 빈 슬롯 없이 연결해야 합니다.")
        elif len(indexes) > int(multi_reference["max_slots"]):
            blockers.append(f"R2V 레퍼런스는 최대 {multi_reference['max_slots']}장까지 지원합니다.")
    if blockers:
        return {"case_version_id": case_version_id, "status": "blocked", "blockers": blockers, "asset_requirements": requirements}
    defaults = dict(config.get("defaults") or {})
    values = {**DEFAULTS, **defaults}
    contract = _format_case_value(json.loads(case["contract_json"] or "{}"), case_settings)
    generation = dict(contract.get("generation") or {})
    if str(case["case_id"]) == "benchmark_long_temporal":
        generation = {"target_seconds": 20, "frame_count": 481, **generation}
    if "frame_count" in generation:
        values["frame_count"] = int(generation["frame_count"])
    if "target_seconds" in generation:
        values["duration_seconds"] = int(generation["target_seconds"])
    if contract.get("input_mode") == "h3_r2v_multi_reference":
        raw_frames = max(5, round(float(values["duration_seconds"]) * 24))
        values["frame_count"] = raw_frames + (5 - raw_frames % 17) % 17
        values["fps"] = 24
    if selected_width and selected_height:
        values["width"] = int(selected_width)
        values["height"] = int(selected_height)
    values["audio_frame_count"] = values["frame_count"]
    values["seed"] = int(values["seed"]) + max(0, repetition - 1)
    canonical_prompt = _format_case_value(str(prompt_row["prompt_text"]), case_settings)
    intent_ko = _format_case_value(str(case["intent_ko"]), case_settings)
    values["prompt"] = _render_prompt(str(config.get("prompt_template") or "{prompt}"), canonical_prompt, intent_ko)
    values["negative_prompt"] = str(defaults.get("negative_prompt") or "")
    reference = next((item for item in linked if item["role"] == "reference_image"), None)
    values["reference_image"] = f"model_tests/{reference['sha256']}{Path(reference['path']).suffix.lower()}" if reference else ""
    values["filename_prefix"] = f"video/model-tests/{session['session_id']}/{case_version_id}_{repetition:02d}"
    if int(values["frame_count"]) > int(DEFAULTS["frame_count"]):
        missing_duration = []
        if "duration_seconds" not in bindings and "frame_count" not in bindings:
            missing_duration.append("duration_seconds 또는 frame_count")
        direct_audio_frames = any(
            str(node.get("class_type")) == "LTXVEmptyLatentAudio"
            and not isinstance(dict(node.get("inputs") or {}).get("frames_number"), list)
            for node in workflow.values()
        )
        if "frame_count" in bindings and "duration_seconds" not in bindings and direct_audio_frames and "audio_frame_count" not in bindings:
            missing_duration.append("audio_frame_count")
        if missing_duration:
            return {"case_version_id": case_version_id, "status": "blocked", "blockers": ["장기 테스트 프레임 수 바인딩 필요: " + ", ".join(missing_duration)]}
    compiled = copy.deepcopy(workflow)
    for key, binding in bindings.items():
        compiled[binding["node_id"]]["inputs"][binding["input"]] = values[key]
    compiled_assets = []
    if multi_assets and multi_reference:
        conditioner_inputs = compiled[multi_reference["conditioning_node_id"]]["inputs"]
        for input_name in list(conditioner_inputs):
            if input_name.startswith(multi_reference["input_prefix"]):
                conditioner_inputs.pop(input_name)
        base_loaders = list(multi_reference["loader_node_ids"])
        template = workflow[multi_reference["loader_template_node_id"]]
        for slot, item in multi_assets:
            loader_id = base_loaders[slot - 1] if slot <= len(base_loaders) else f"benchmark_ref_{slot}"
            if loader_id not in compiled:
                compiled[loader_id] = copy.deepcopy(template)
                compiled[loader_id].setdefault("_meta", {})["title"] = f"Benchmark Picture {slot}"
            filename = f"model_tests/{item['sha256']}{Path(item['path']).suffix.lower()}"
            compiled[loader_id]["inputs"][multi_reference["loader_input"]] = filename
            conditioner_inputs[f"{multi_reference['input_prefix']}{slot - 1}"] = [loader_id, 0]
            compiled_assets.append({
                "asset_id": item["asset_id"], "role": item["role"], "sha256": item["sha256"],
                "picture_index": slot,
                "binding": {"node_id": loader_id, "input": multi_reference["loader_input"]},
            })
    else:
        compiled_assets = [{"asset_id": item["asset_id"], "role": item["role"], "sha256": item["sha256"]} for item in linked]
    return {
        "case_version_id": case_version_id,
        "status": "ready",
        "workflow_sha256": _hash_json(compiled),
        "source_workflow_sha256": profile["workflow_sha256"],
        "prompt_sha256": _hash_bytes(values["prompt"].encode("utf-8")),
        "prompt_text": values["prompt"],
        "benchmark_contract": contract,
        "case_settings": case_settings,
        "settings": {key: values[key] for key in ("seed", "width", "height", "fps", "duration_seconds", "frame_count")},
        "assets": compiled_assets,
        "compiled_workflow": compiled,
    }


def preflight_session(connection, session_id: str) -> dict[str, Any]:
    session = connection.execute("SELECT * FROM test_sessions WHERE session_id=?", (session_id,)).fetchone()
    if not session:
        raise ValueError("테스트 세션을 찾을 수 없습니다.")
    if not session["adapter_id"]:
        raise ValueError("테스트 세션에 어댑터가 연결되지 않았습니다.")
    rows = connection.execute("SELECT case_version_id,planned_runs FROM test_session_cases WHERE session_id=? ORDER BY ordering", (session_id,)).fetchall()
    cases = []
    for row in rows:
        first = compile_case(connection, session, row["case_version_id"], 1)
        first.pop("compiled_workflow", None)
        first["planned_runs"] = row["planned_runs"]
        cases.append(first)
    ready_count = sum(1 for row in cases if row["status"] == "ready")
    blocked_count = len(cases) - ready_count
    status = "ready" if blocked_count == 0 else ("partially_ready" if ready_count else "blocked")
    now = datetime.now().astimezone().isoformat()
    report = {"session_id": session_id, "status": status, "ready_count": ready_count, "blocked_count": blocked_count, "cases": cases}
    preflight_id = f"preflight_{_hash_json({'session': session_id, 'adapter': session['adapter_id'], 'at': now})[:24]}"
    connection.execute("INSERT INTO adapter_preflights(preflight_id,session_id,adapter_id,status,ready_count,blocked_count,report_json,created_at) VALUES (?,?,?,?,?,?,?,?)", (preflight_id, session_id, session["adapter_id"], status, ready_count, blocked_count, _json(report), now))
    connection.execute("UPDATE test_sessions SET status=?,updated_at=? WHERE session_id=?", (f"preflight_{status}", now, session_id))
    connection.commit()
    return {"preflight_id": preflight_id, **report}
