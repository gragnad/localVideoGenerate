from __future__ import annotations

"""Batch-free MiniMax H3 production queue.

It is the persistence boundary for the H3-only production path. Archived job
directories are resolved read-only so existing benchmark videos remain playable.
"""

import copy
import hashlib
import json
import os
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import model_test_registry
import model_test_r2v
import workflow_adapter
import h3_prompt_projects
import h3_prompt_contract
from comfy_client import ComfyClient
from job_queue import atomic_write_json, now_iso, queue_claim_lock, read_json, update_status


H3_RUNTIME = Path("runtime/h3")
TERMINAL = {"completed", "failed", "cancelled"}
ACTIVE = {"claimed", "preparing", "uploading", "submitting", "submitted", "comfy_queued", "running"}
R2V_OUTPUT_RESOLUTIONS = {
    (608, 352), (832, 480), (960, 544), (1280, 704), (1280, 736),
}
R2V_RERENDER_RESOLUTIONS = R2V_OUTPUT_RESOLUTIONS | {(1024, 576)}
I2V_OUTPUT_RESOLUTIONS = {(832, 480), (1280, 704), (1376, 768)}
H3_SOL_ATTN_DEFAULT_OVERRIDES = {
    "int8_qk": False,
    "int8_pv": False,
    "morton": False,
}
WINDOWS_UPSCALE_WORKFLOW_PATH = (
    Path(__file__).resolve().parent
    / "deploy/windows-render-agent/rtx_1080p60_h264_api.json"
)
WINDOWS_UPSCALE_WORKFLOW_VERSION = "rtx_rife_1080p60_h264_v1"


def prompt_revision_authoring_config() -> dict[str, Any]:
    """Return the non-secret prompt authoring mode exposed to the UI."""
    remote_url = str(os.environ.get("H3_PROMPT_REVISION_REMOTE_URL") or "").strip()
    return {
        "mode": "remote_codex_api" if remote_url else "codex_conversation",
        "remote_configured": bool(remote_url),
    }


def candidate_render_config() -> dict[str, Any]:
    """Return the non-secret ComfyUI target used by production candidates."""
    configured = str(os.environ.get("H3_CANDIDATE_COMFY_URL") or "").strip()
    comfy_url = (
        configured
        or str(os.environ.get("COMFY_URL") or "").strip()
        or "http://127.0.0.1:8188"
    ).rstrip("/")
    parsed = urlparse(comfy_url)
    hostname = str(parsed.hostname or "").lower()
    remote = hostname not in {"", "127.0.0.1", "localhost", "::1"}
    return {
        "mode": "remote_windows_comfy" if configured and remote else "local_comfy",
        "comfy_url": comfy_url,
        "remote_configured": bool(configured and remote),
    }


def _candidate_comfy_url(data: dict[str, Any]) -> str:
    value = str(
        os.environ.get("H3_CANDIDATE_COMFY_URL")
        or data.get("comfy_url")
        or os.environ.get("COMFY_URL")
        or "http://127.0.0.1:8188"
    ).strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("후보 영상 ComfyUI 주소는 올바른 HTTP(S) URL이어야 합니다.")
    return value


def _production_workflow_settings(
    workflow: dict[str, Any], raw: Any = None
) -> dict[str, Any]:
    """Validate and apply production-only workflow controls."""
    if raw is None:
        raw_values: dict[str, Any] = {}
    elif isinstance(raw, dict):
        raw_values = dict(raw)
    else:
        raise ValueError("H3 워크플로우 설정 형식이 올바르지 않습니다.")
    unknown = set(raw_values) - {"sol_attn"}
    if unknown:
        raise ValueError(
            "지원하지 않는 H3 워크플로우 설정입니다: "
            + ", ".join(sorted(unknown))
        )

    supports_sol_attn = workflow_adapter.has_sol_attn_patch(workflow)
    if not supports_sol_attn:
        if raw_values:
            raise ValueError(
                "Patch Sol-Attn 설정은 Sol-Attn R2V 워크플로우에서만 사용할 수 있습니다."
            )
        return {}

    raw_sol_attn = raw_values.get("sol_attn")
    if raw_sol_attn is None:
        raw_sol_attn = {}
    if not isinstance(raw_sol_attn, dict):
        raise ValueError("Patch Sol-Attn 설정 형식이 올바르지 않습니다.")
    effective = {**H3_SOL_ATTN_DEFAULT_OVERRIDES, **raw_sol_attn}
    return {
        "sol_attn": workflow_adapter.apply_sol_attn_settings(
            workflow, effective
        )
    }


def roots(root: Path) -> dict[str, Path]:
    base = root / H3_RUNTIME
    return {
        "base": base,
        "jobs": base / "jobs",
        "candidate_sets": base / "candidate_sets",
        "prompt_revision_requests": base / "prompt_revision_requests",
        "project_test_sets": base / "project_test_sets",
        "test_queues": base / "test_queues",
        "outputs": base / "outputs",
        "worker_status": base / "worker_status.json",
        "windows_candidate_worker_status": base / "windows_candidate_worker_status.json",
    }


def _safe_id(value: str, label: str) -> str:
    value = str(value or "").strip()
    if not value or Path(value).name != value or value in {".", ".."}:
        raise ValueError(f"올바른 {label}이(가) 아닙니다.")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def available_adapters(root: Path) -> dict[str, Any]:
    with model_test_registry.open_registry(root) as connection:
        rows = connection.execute(
            """SELECT a.adapter_id,a.adapter_name,a.adapter_version,
                      w.workflow_profile_id,w.workflow_filename,m.display_name,
                      m.provider,m.family,m.version,
                      a.config_json
                 FROM workflow_adapters a
                 JOIN workflow_profiles w ON w.workflow_profile_id=a.workflow_profile_id
                 JOIN models m ON m.model_id=w.model_id
                ORDER BY m.display_name,w.name,a.adapter_name"""
        ).fetchall()
        usable_rows = []
        sol_attn_defaults = {}
        for row in rows:
            try:
                workflow, _ = workflow_adapter.load_api_workflow(
                    connection, row["workflow_profile_id"]
                )
            except (OSError, ValueError):
                continue
            usable_rows.append(row)
            if (
                str(row["workflow_filename"] or "")
                == model_test_r2v.R2V_PINT8_WORKFLOW_FILENAME
            ):
                compiled = copy.deepcopy(workflow)
                sol_attn_defaults[row["workflow_profile_id"]] = (
                    _production_workflow_settings(compiled)["sol_attn"]
                )
        rows = usable_rows
    adapters = []
    for row in rows:
        identity = " ".join(
            str(row[key] or "")
            for key in ("provider", "family", "display_name", "version")
        ).lower()
        if "minimax" not in identity or "h3" not in identity:
            continue
        config = json.loads(row["config_json"] or "{}")
        multi = dict(config.get("multi_reference") or {})
        bindings = dict(config.get("bindings") or {})
        if multi:
            generation_mode = "r2v"
            max_references = int(multi.get("max_slots") or 9)
        elif bindings.get("reference_image"):
            generation_mode = "i2v"
            max_references = 2 if bindings.get("last_reference_image") else 1
        else:
            continue
        adapters.append({
            "adapter_id": row["adapter_id"],
            "adapter_name": row["adapter_name"],
            "adapter_version": row["adapter_version"],
            "workflow_profile_id": row["workflow_profile_id"],
            "workflow_filename": row["workflow_filename"],
            "model_name": row["display_name"],
            "generation_mode": generation_mode,
            "default_for_generation": (
                generation_mode == "r2v"
                and row["workflow_filename"]
                == model_test_r2v.R2V_DEFAULT_WORKFLOW_FILENAME
            ),
            "required_references": 1,
            "supports_last_frame": bool(bindings.get("last_reference_image")),
            "max_references": max_references,
            "sol_attn_configurable": row["workflow_profile_id"] in sol_attn_defaults,
            "sol_attn_defaults": sol_attn_defaults.get(row["workflow_profile_id"]),
        })
    deduplicated: dict[tuple[str, str, str], dict[str, Any]] = {}
    for adapter in adapters:
        key = (
            str(adapter["workflow_profile_id"]),
            str(adapter["adapter_name"]),
            str(adapter["generation_mode"]),
        )
        current = deduplicated.get(key)
        if (
            current is None
            or int(adapter["max_references"]) > int(current["max_references"])
        ):
            deduplicated[key] = adapter
    adapters = list(deduplicated.values())
    return {
        "adapters": adapters,
        "defaults": {"width": 1280, "height": 704, "fps": 24, "duration_seconds": 5, "candidate_count": 3},
    }


def _compile_workflow(
    root: Path,
    adapter_id: str,
    values: dict[str, Any],
    reference_count: int,
    expected_generation_mode: str | None = None,
    workflow_settings: Any = None,
) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    with model_test_registry.open_registry(root) as connection:
        adapter = connection.execute(
            "SELECT * FROM workflow_adapters WHERE adapter_id=?", (adapter_id,)
        ).fetchone()
        if not adapter:
            raise ValueError("등록된 H3 어댑터를 찾을 수 없습니다.")
        requested_config = json.loads(adapter["config_json"] or "{}")
        requested_multi = dict(requested_config.get("multi_reference") or {})
        requested_capacity = int(requested_multi.get("max_slots") or 0)
        if requested_multi and reference_count > requested_capacity:
            alternatives = connection.execute(
                """SELECT * FROM workflow_adapters
                    WHERE workflow_profile_id=?
                      AND adapter_name=?""",
                (
                    adapter["workflow_profile_id"],
                    adapter["adapter_name"],
                ),
            ).fetchall()
            compatible = []
            for candidate in alternatives:
                candidate_config = json.loads(candidate["config_json"] or "{}")
                candidate_multi = dict(
                    candidate_config.get("multi_reference") or {}
                )
                capacity = int(candidate_multi.get("max_slots") or 0)
                if capacity >= reference_count:
                    compatible.append((capacity, candidate))
            if compatible:
                adapter = max(compatible, key=lambda item: item[0])[1]
        workflow, profile = workflow_adapter.load_api_workflow(connection, adapter["workflow_profile_id"])
    config = json.loads(adapter["config_json"] or "{}")
    bindings = workflow_adapter.validate_bindings(workflow, dict(config.get("bindings") or {}))
    multi = workflow_adapter._validate_multi_reference(workflow, config.get("multi_reference"))
    generation_mode = "r2v" if multi else "i2v" if bindings.get("reference_image") else ""
    if not generation_mode:
        raise ValueError("선택한 어댑터는 H3 이미지 기반 생성을 지원하지 않습니다.")
    if expected_generation_mode and expected_generation_mode != generation_mode:
        raise ValueError(
            f"선택한 워크플로우는 H3 {generation_mode.upper()}용입니다."
        )
    if generation_mode == "r2v" and (
        reference_count < 1 or reference_count > int(multi["max_slots"])
    ):
        raise ValueError(f"참조 이미지는 1~{multi['max_slots']}장이어야 합니다.")
    last_reference_binding = bindings.get("last_reference_image")
    if generation_mode == "i2v":
        valid_counts = {1, 2} if last_reference_binding else {1}
        if reference_count not in valid_counts:
            if last_reference_binding:
                raise ValueError("H3 FFLF는 시작 이미지 한 장과 선택적인 종료 이미지 한 장만 지원합니다.")
            raise ValueError("H3 I2V는 클립마다 시작 이미지 한 장이 필요합니다.")
    compiled = copy.deepcopy(workflow)
    effective_workflow_settings = _production_workflow_settings(
        compiled, workflow_settings
    )
    prompt_template = str(config.get("prompt_template") or "{prompt}")
    applied = {**dict(config.get("defaults") or {}), **values}
    applied["prompt"] = prompt_template.replace("{prompt}", str(values["prompt"])).replace("{intent_ko}", "")
    for key, binding in bindings.items():
        if key in applied:
            compiled[binding["node_id"]]["inputs"][binding["input"]] = applied[key]
    patches = []
    if generation_mode == "r2v":
        conditioner = compiled[multi["conditioning_node_id"]]["inputs"]
        for name in list(conditioner):
            if name.startswith(multi["input_prefix"]):
                conditioner.pop(name)
        loader_ids = list(multi["loader_node_ids"])
        template = workflow[multi["loader_template_node_id"]]
        for index in range(1, reference_count + 1):
            loader_id = loader_ids[index - 1] if index <= len(loader_ids) else f"h3_ref_{index}"
            if loader_id not in compiled:
                compiled[loader_id] = copy.deepcopy(template)
                compiled[loader_id].setdefault("_meta", {})["title"] = f"H3 Picture {index}"
            compiled[loader_id]["inputs"][multi["loader_input"]] = f"__H3_REFERENCE_{index}__"
            source_node_id = workflow_adapter.materialize_multi_reference_source(
                compiled,
                workflow,
                multi,
                index,
                loader_id,
                "h3",
            )
            conditioner[f"{multi['input_prefix']}{index - 1}"] = [
                source_node_id,
                0,
            ]
            patches.append({"node_id": loader_id, "input": multi["loader_input"]})
    else:
        binding = bindings["reference_image"]
        compiled[binding["node_id"]]["inputs"][binding["input"]] = "__H3_START_IMAGE__"
        patches.append({"node_id": binding["node_id"], "input": binding["input"]})
        last_binding = last_reference_binding
        if last_binding and reference_count == 2:
            compiled[last_binding["node_id"]]["inputs"][last_binding["input"]] = "__H3_LAST_IMAGE__"
            patches.append({
                "node_id": last_binding["node_id"],
                "input": last_binding["input"],
            })
        elif last_binding:
            last_node_id = last_binding["node_id"]
            for node in compiled.values():
                inputs = node.get("inputs") or {}
                for input_name, value in list(inputs.items()):
                    if value == [last_node_id, 0]:
                        inputs.pop(input_name)
            compiled.pop(last_node_id, None)
    return compiled, patches, {
        "adapter_id": adapter["adapter_id"],
        "workflow_profile_id": profile["workflow_profile_id"],
        "workflow_filename": profile["workflow_filename"],
        "generation_mode": generation_mode,
        "workflow_settings": effective_workflow_settings,
    }


def _candidate_letter(index: int) -> str:
    """Return A..Z, AA.. labels for one-based candidate positions."""
    value = int(index)
    if value < 1:
        raise ValueError("후보 순번은 1 이상이어야 합니다.")
    label = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        label = chr(65 + remainder) + label
    return label


def _normalize_generation_variants(
    data: dict[str, Any], prompt: str, count: int
) -> tuple[list[dict[str, str]], bool]:
    raw = data.get("prompt_variants")
    if raw in (None, []):
        return ([
            {
                "variant_id": _candidate_letter(index),
                "label": f"후보 {_candidate_letter(index)}",
                "rationale": "",
                "video_prompt": prompt,
            }
            for index in range(1, count + 1)
        ], False)
    variants = h3_prompt_projects.normalize_prompt_variants(raw)
    if len(variants) != 3:
        raise ValueError("독립 프롬프트 후보는 정확히 3개여야 합니다.")
    return ([
        {
            "variant_id": str(row["variant_id"]),
            "label": str(row["label"]),
            "rationale": str(row.get("rationale") or ""),
            "video_prompt": str(row["video_prompt"]),
        }
        for row in variants
    ], True)


def _next_clip_version(
    root: Path,
    project_id: str | None,
    scene_id: str | None,
    clip_id: str | None,
) -> int | None:
    if not project_id or not scene_id or not clip_id:
        return None
    maximum = 0
    base = roots(root)["candidate_sets"]
    if base.exists():
        for directory in base.iterdir():
            if not directory.is_dir():
                continue
            payload = read_json(directory / "candidate_set.json", {}) or {}
            if _candidate_set_deleted(payload):
                continue
            if payload.get("render_purpose") == "resolution_rerender":
                continue
            if (
                str(payload.get("source_project_id") or "") == project_id
                and str(payload.get("source_scene_id") or "") == scene_id
                and str(payload.get("source_clip_id") or "") == clip_id
            ):
                maximum = max(maximum, int(payload.get("clip_version") or 0))
    return maximum + 1


def enqueue_candidate_set(
    root: Path,
    data: dict[str, Any],
    *,
    lineage: dict[str, Any] | None = None,
    reference_provenance: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    adapter_id = str(data.get("adapter_id") or "").strip()
    requested_queue_lane = str(data.get("queue_lane") or "").strip()
    if requested_queue_lane not in {"", "windows_candidate", "local_generation"}:
        raise ValueError("H3 생성 큐는 Windows 후보 또는 로컬 생성이어야 합니다.")
    source_project_id = str(data.get("source_project_id") or "").strip() or None
    if source_project_id:
        blocked_reason = h3_prompt_projects.project_generation_block_reason(
            root, source_project_id
        )
        if blocked_reason:
            raise ValueError(blocked_reason)
    prompt = str(data.get("prompt") or "").strip()
    references = list(data.get("references") or [])
    requested_generation_mode = str(data.get("generation_mode") or "").strip().lower()
    if requested_generation_mode not in {"", "r2v", "i2v"}:
        raise ValueError("H3 생성 방식은 R2V 또는 I2V여야 합니다.")
    if not adapter_id or (not prompt and not data.get("prompt_variants")):
        raise ValueError("H3 어댑터와 영상 프롬프트가 필요합니다.")
    if not references:
        raise ValueError("참조 이미지를 한 장 이상 등록하세요.")
    count = int(data.get("candidate_count") or 3)
    if count < 1 or count > 6:
        raise ValueError("후보 개수는 1~6개여야 합니다.")
    prompt_variants, independent_prompts = _normalize_generation_variants(
        data, prompt, count
    )
    if independent_prompts:
        count = len(prompt_variants)
        prompt = prompt_variants[0]["video_prompt"]
    width, height = int(data.get("width") or 1280), int(data.get("height") or 704)
    resolution_rerender = bool(
        lineage and lineage.get("render_purpose") == "resolution_rerender"
    )
    allowed_resolutions = (
        I2V_OUTPUT_RESOLUTIONS
        if requested_generation_mode == "i2v"
        else R2V_RERENDER_RESOLUTIONS
        if resolution_rerender
        else R2V_OUTPUT_RESOLUTIONS
    )
    if (width, height) not in allowed_resolutions:
        if requested_generation_mode == "i2v":
            raise ValueError(
                "H3 I2V 출력 해상도는 832 × 480, 1280 × 704 또는 "
                "1376 × 768만 지원합니다."
            )
        raise ValueError(
            "H3 R2V 출력 해상도는 608 × 352, 832 × 480, 960 × 544, "
            "1280 × 704 또는 1280 × 736만 지원합니다."
        )
    duration = float(data.get("duration_seconds") or 5)
    if duration < 1 or duration > 15:
        raise ValueError("영상 길이는 1~15초여야 합니다.")
    created = now_iso()
    token = secrets.token_hex(3)
    set_id = f"h3set_{datetime.now():%Y%m%d_%H%M%S}_{token}"
    paths = roots(root)
    set_dir = paths["candidate_sets"] / set_id
    source_dir = set_dir / "sources"
    source_dir.mkdir(parents=True, exist_ok=False)
    copied = []
    provenance = list(reference_provenance or [])
    if provenance and len(provenance) != len(references):
        raise ValueError("참조 이미지 원본 정보 개수가 일치하지 않습니다.")
    for index, row in enumerate(references, start=1):
        project_id = str(row.get("project_id") or "").strip()
        clip_id = str(row.get("clip_id") or "").strip()
        project_picture_index = int(row.get("project_picture_index") or index)
        source = (
            h3_prompt_projects.picture_path(root, project_id, clip_id, project_picture_index)
            if project_id or clip_id
            else Path(str(row.get("upload_path") or ""))
        )
        if not source.is_file():
            raise FileNotFoundError(f"Picture {index} 파일을 찾을 수 없습니다.")
        suffix = source.suffix.lower() or ".png"
        target = source_dir / f"picture_{index:02d}{suffix}"
        shutil.copy2(source, target)
        source_metadata = provenance[index - 1] if provenance else {}
        copied.append({
            "picture_index": index,
            "role": str(row.get("role") or f"picture_{index}"),
            "original_name": str(row.get("original_name") or source.name),
            "source_path": str(target),
            "sha256": _sha256(target),
            "source_project_id": (
                str(source_metadata.get("source_project_id") or "") or project_id or None
            ),
            "source_clip_id": (
                str(source_metadata.get("source_clip_id") or "") or clip_id or None
            ),
            "source_picture_index": (
                source_metadata.get("source_picture_index")
                if source_metadata
                else project_picture_index if project_id else None
            ),
        })
    base_seed = int(data.get("seed", -1))
    job_ids = []
    resolved_generation_mode = requested_generation_mode or "r2v"
    effective_workflow_settings: dict[str, Any] = {}
    effective_adapter_id = adapter_id
    allowed_lineage_keys = {
        "render_purpose",
        "source_candidate_set_id",
        "source_selected_job_id",
        "source_resolution",
        "target_resolution",
        "seed_mode",
        "source_seed",
        "rerender_seed",
    }
    lineage_payload = {
        key: value
        for key, value in dict(lineage or {}).items()
        if key in allowed_lineage_keys
    }
    source_project_id = str(data.get("source_project_id") or "") or None
    source_scene_id = str(data.get("source_scene_id") or "") or None
    source_clip_id = str(data.get("source_clip_id") or "") or None
    clip_version = data.get("clip_version")
    if clip_version is None:
        clip_version = _next_clip_version(
            root, source_project_id, source_scene_id, source_clip_id
        )
    candidate_round = max(1, int(data.get("candidate_round") or 1))
    queue_lane = (
        "local_generation"
        if lineage_payload.get("render_purpose") == "resolution_rerender"
        else requested_queue_lane or "windows_candidate"
    )
    comfy_url = (
        str(os.environ.get("COMFY_URL") or "http://127.0.0.1:8188").rstrip("/")
        if queue_lane == "local_generation"
        else _candidate_comfy_url(data)
    )
    configured_render = candidate_render_config()
    render_target = (
        "local_comfy"
        if queue_lane == "local_generation"
        else "windows_comfy"
        if configured_render["remote_configured"]
        and comfy_url == configured_render["comfy_url"]
        else "custom_comfy"
        if comfy_url != "http://127.0.0.1:8188"
        else "local_comfy"
    )
    for candidate_index, variant in enumerate(prompt_variants, start=1):
        seed = secrets.randbits(63) if base_seed < 0 else (base_seed + candidate_index - 1) % ((1 << 63) - 1)
        job_id = f"h3job_{datetime.now():%Y%m%d_%H%M%S}_{candidate_index:02d}_{secrets.token_hex(2)}"
        job_dir = paths["jobs"] / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        values = {
            "prompt": variant["video_prompt"], "seed": seed, "width": width, "height": height,
            "fps": 24, "duration_seconds": duration,
            "filename_prefix": f"video/h3/{set_id}/{job_id}",
        }
        workflow, patches, profile = _compile_workflow(
            root,
            adapter_id,
            values,
            len(copied),
            requested_generation_mode or None,
            data.get("workflow_settings"),
        )
        effective_workflow_settings = dict(profile.get("workflow_settings") or {})
        effective_adapter_id = str(profile.get("adapter_id") or adapter_id)
        resolved_generation_mode = str(
            profile.get("generation_mode") or requested_generation_mode or "r2v"
        )
        atomic_write_json(job_dir / "workflow_api.json", workflow)
        request = {
            "schema_version": 2, "job_type": "h3_r2v_generate", "queue_name": "h3_generation",
            "queue_lane": queue_lane,
            "job_id": job_id, "candidate_set_id": set_id, "candidate_index": candidate_index,
            "candidate_count": count, "created_at": created, "adapter_id": adapter_id,
            "prompt_variant_id": variant["variant_id"],
            "prompt_variant_label": variant["label"],
            "prompt_variant_rationale": variant["rationale"],
            "candidate_round": candidate_round,
            "clip_version": clip_version,
            **profile, **values, "generation_mode": resolved_generation_mode,
            "references": copied, "reference_patches": patches,
            "source_project_id": source_project_id,
            "source_scene_id": source_scene_id,
            "source_clip_id": source_clip_id,
            "project_test_set_id": str(data.get("project_test_set_id") or "") or None,
            "comfy_url": comfy_url,
            "render_target": render_target,
            **lineage_payload,
        }
        atomic_write_json(job_dir / "request.json", request)
        atomic_write_json(job_dir / "manifest.json", {"schema_version": 1, "job_id": job_id, "status": "queued", "outputs": [], "created_at": created})
        queue_stage = (
            "로컬 생성 Worker 대기"
            if queue_lane == "local_generation"
            else "Windows 후보 Worker 대기"
        )
        atomic_write_json(job_dir / "status.json", {"job_id": job_id, "status": "queued", "stage": queue_stage, "progress": 0, "created_at": created, "updated_at": created})
        job_ids.append(job_id)
    candidate_set = {
        "schema_version": 2, "candidate_set_id": set_id, "status": "generating",
        "created_at": created, "updated_at": created, "prompt": prompt,
        "prompt_variants": prompt_variants,
        "independent_prompts": independent_prompts,
        "candidate_round": candidate_round,
        "clip_version": clip_version,
        "revision_feedback": str(data.get("revision_feedback") or "").strip() or None,
        "parent_candidate_set_id": str(data.get("parent_candidate_set_id") or "").strip() or None,
        "adapter_id": effective_adapter_id, "candidate_count": count, "candidate_job_ids": job_ids,
        "width": width, "height": height,
        "selected_job_id": None, "selected_jobs": [],
        "generation_mode": resolved_generation_mode,
        "comfy_url": comfy_url,
        "render_target": render_target,
        "queue_lane": queue_lane,
        "workflow_settings": effective_workflow_settings,
        "references": copied,
        "source_project_id": source_project_id,
        "source_scene_id": source_scene_id,
        "source_clip_id": source_clip_id,
        "project_test_set_id": str(data.get("project_test_set_id") or "") or None,
        **lineage_payload,
    }
    atomic_write_json(set_dir / "candidate_set.json", candidate_set)
    return candidate_set


def enqueue_selected_candidate_rerender(
    root: Path,
    candidate_set_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Queue one R2V resolution render with either preserved or random seed."""
    paths = roots(root)
    set_id = _safe_id(candidate_set_id, "후보 세트 ID")
    source_set_path = paths["candidate_sets"] / set_id / "candidate_set.json"
    source_set = read_json(source_set_path, {}) or {}
    if not source_set or _candidate_set_deleted(source_set):
        raise FileNotFoundError(f"H3 후보 세트를 찾을 수 없습니다: {set_id}")

    requested_source_job_id = str(data.get("source_job_id") or "").strip()
    source_job_id = _safe_id(
        requested_source_job_id
        or str(source_set.get("selected_job_id") or ""),
        "선택 작업 ID",
    )
    selected_job_ids = {
        row["job_id"] for row in _candidate_selected_jobs(source_set)
    }
    if source_job_id not in selected_job_ids:
        raise ValueError("해상도 재생성 대상이 현재 선택된 후보가 아닙니다.")
    if source_job_id not in list(source_set.get("candidate_job_ids") or []):
        raise ValueError("현재 후보군의 선택 작업 기록이 올바르지 않습니다.")
    source_job_dir = paths["jobs"] / source_job_id
    source_status = read_json(source_job_dir / "status.json", {}) or {}
    if source_status.get("status") != "completed":
        raise ValueError("완료된 선택 후보만 해상도를 변경해 재생성할 수 있습니다.")
    source_request = read_json(source_job_dir / "request.json", {}) or {}
    if str(source_request.get("generation_mode") or "r2v").lower() != "r2v":
        raise ValueError("해상도 재생성은 현재 H3 R2V 결과만 지원합니다.")

    width = int(data.get("width") or 0)
    height = int(data.get("height") or 0)
    if (width, height) not in R2V_RERENDER_RESOLUTIONS:
        raise ValueError(
            "재생성 해상도는 608 × 352, 832 × 480, 960 × 544, "
            "1024 × 576, 1280 × 704 또는 1280 × 736 중에서 선택하세요."
        )
    source_width = int(source_request.get("width") or 0)
    source_height = int(source_request.get("height") or 0)
    if width * height <= source_width * source_height:
        raise ValueError("원본보다 높은 해상도만 재생성 대상으로 선택할 수 있습니다.")

    source_seed = int(source_request.get("seed"))
    randomize_seed = bool(data.get("randomize_seed"))
    rerender_seed = source_seed
    if randomize_seed:
        rerender_seed = secrets.randbits(63)
        while rerender_seed == source_seed:
            rerender_seed = secrets.randbits(63)

    source_references = list(source_request.get("references") or [])
    if not source_references:
        raise ValueError("선택 후보의 참조 이미지 기록이 없습니다.")
    for index, reference in enumerate(source_references, start=1):
        source_path = Path(str(reference.get("source_path") or ""))
        if not source_path.is_file():
            raise FileNotFoundError(f"선택 후보의 Picture {index} 파일을 찾을 수 없습니다.")
        if _sha256(source_path) != str(reference.get("sha256") or ""):
            raise ValueError(f"선택 후보의 Picture {index} 파일 해시가 변경되었습니다.")

    stored_workflow = read_json(source_job_dir / "workflow_api.json", {}) or {}
    source_values = {
        key: source_request.get(key)
        for key in (
            "prompt",
            "seed",
            "width",
            "height",
            "fps",
            "duration_seconds",
            "filename_prefix",
        )
    }
    compiled, reference_patches, profile = _compile_workflow(
        root,
        str(source_request.get("adapter_id") or ""),
        source_values,
        len(source_references),
        "r2v",
        source_request.get("workflow_settings"),
    )
    if (
        compiled != stored_workflow
        or reference_patches != list(source_request.get("reference_patches") or [])
        or profile.get("workflow_profile_id")
        != source_request.get("workflow_profile_id")
        or profile.get("workflow_filename") != source_request.get("workflow_filename")
    ):
        raise ValueError(
            "선택 후보 생성 이후 워크플로우가 변경되어 해상도만 동일 조건으로 "
            "재생성할 수 없습니다."
        )

    with queue_claim_lock(paths["candidate_sets"]):
        current_source_set = read_json(source_set_path, {}) or {}
        current_selected_job_ids = {
            row["job_id"] for row in _candidate_selected_jobs(current_source_set)
        }
        if source_job_id not in current_selected_job_ids:
            raise ValueError("재생성 등록 중 후보 선택이 변경되었습니다. 다시 확인하세요.")
        if not randomize_seed and paths["candidate_sets"].exists():
            for directory in paths["candidate_sets"].iterdir():
                if not directory.is_dir():
                    continue
                existing = read_json(directory / "candidate_set.json", {}) or {}
                if (
                    existing.get("render_purpose") != "resolution_rerender"
                    or existing.get("source_selected_job_id") != source_job_id
                    or existing.get("target_resolution")
                    != {"width": width, "height": height}
                    or str(existing.get("seed_mode") or "preserved")
                    != "preserved"
                    or _candidate_set_deleted(existing)
                ):
                    continue
                statuses = [
                    str(
                        (
                            read_json(paths["jobs"] / job_id / "status.json", {})
                            or {}
                        ).get("status")
                        or "missing"
                    )
                    for job_id in existing.get("candidate_job_ids") or []
                ]
                if statuses and any(status not in TERMINAL for status in statuses):
                    return {**existing, "already_exists": True}

        rerender = enqueue_candidate_set(
            root,
            {
                "adapter_id": source_request.get("adapter_id"),
                "generation_mode": "r2v",
                "prompt": source_request.get("prompt"),
                "references": [
                    {
                        "upload_path": reference.get("source_path"),
                        "role": reference.get("role"),
                        "original_name": reference.get("original_name"),
                    }
                    for reference in source_references
                ],
                "candidate_count": 1,
                "seed": rerender_seed,
                "width": width,
                "height": height,
                "duration_seconds": float(source_request.get("duration_seconds") or 5),
                "workflow_settings": source_request.get("workflow_settings"),
                "source_project_id": source_request.get("source_project_id"),
                "source_scene_id": source_request.get("source_scene_id"),
                "source_clip_id": source_request.get("source_clip_id"),
                "comfy_url": os.environ.get("COMFY_URL", "http://127.0.0.1:8188"),
            },
            lineage={
                "render_purpose": "resolution_rerender",
                "source_candidate_set_id": set_id,
                "source_selected_job_id": source_job_id,
                "source_resolution": {
                    "width": source_width,
                    "height": source_height,
                },
                "target_resolution": {"width": width, "height": height},
                "seed_mode": "random" if randomize_seed else "preserved",
                "source_seed": source_seed,
                "rerender_seed": rerender_seed,
            },
            reference_provenance=source_references,
        )
    return {**rerender, "already_exists": False}


def enqueue_selected_candidate_upscale(
    root: Path,
    candidate_set_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Queue a completed Spark rerender for Windows RTX 1080p60 processing."""
    paths = roots(root)
    set_id = _safe_id(candidate_set_id, "후보 세트 ID")
    source_set = read_json(
        paths["candidate_sets"] / set_id / "candidate_set.json", {}
    ) or {}
    if not source_set or _candidate_set_deleted(source_set):
        raise FileNotFoundError(f"H3 후보 세트를 찾을 수 없습니다: {set_id}")

    selected_job_id = _safe_id(
        str(data.get("source_selected_job_id") or ""), "선택 작업 ID"
    )
    if selected_job_id not in {
        row["job_id"] for row in _candidate_selected_jobs(source_set)
    }:
        raise ValueError("현재 선택된 후보의 Spark 결과만 업스케일할 수 있습니다.")

    rerender_job_id = _safe_id(
        str(data.get("source_rerender_job_id") or ""), "Spark 재생성 작업 ID"
    )
    rerender_set: dict[str, Any] | None = None
    rerender_set_id = ""
    if paths["candidate_sets"].exists():
        for directory in paths["candidate_sets"].iterdir():
            if not directory.is_dir():
                continue
            candidate = read_json(directory / "candidate_set.json", {}) or {}
            if (
                candidate.get("render_purpose") == "resolution_rerender"
                and candidate.get("source_candidate_set_id") == set_id
                and candidate.get("source_selected_job_id") == selected_job_id
                and rerender_job_id in list(candidate.get("candidate_job_ids") or [])
                and not _candidate_set_deleted(candidate)
            ):
                rerender_set = candidate
                rerender_set_id = directory.name
                break
    if rerender_set is None:
        raise ValueError("선택 후보와 연결된 Spark 해상도 재생성 결과가 아닙니다.")

    rerender_job_dir = paths["jobs"] / rerender_job_id
    rerender_status = read_json(rerender_job_dir / "status.json", {}) or {}
    rerender_manifest = read_json(rerender_job_dir / "manifest.json", {}) or {}
    rerender_request = read_json(rerender_job_dir / "request.json", {}) or {}
    if rerender_status.get("status") != "completed":
        raise ValueError("완료된 Spark 해상도 재생성 결과만 업스케일할 수 있습니다.")
    source_video = Path(str(rerender_manifest.get("local_video_path") or ""))
    if not source_video.is_file():
        raise FileNotFoundError("Spark 해상도 재생성 영상 파일을 찾을 수 없습니다.")
    source_sha256 = str(rerender_manifest.get("output_sha256") or "").strip()
    if not source_sha256 or _sha256(source_video) != source_sha256:
        raise ValueError("Spark 해상도 재생성 영상 해시가 일치하지 않습니다.")

    workflow_path = WINDOWS_UPSCALE_WORKFLOW_PATH
    workflow = read_json(workflow_path, {}) or {}
    if not workflow:
        raise FileNotFoundError(f"Windows 업스케일 워크플로우가 없습니다: {workflow_path}")
    if (
        str((workflow.get("8") or {}).get("inputs", {}).get("format") or "")
        != "video/h264-mp4"
    ):
        raise ValueError("Windows 업스케일 워크플로우 출력은 H264 MP4여야 합니다.")
    workflow_sha256 = _sha256(workflow_path)

    with queue_claim_lock(paths["jobs"]):
        if paths["jobs"].exists():
            for directory in paths["jobs"].iterdir():
                if not directory.is_dir():
                    continue
                existing = read_json(directory / "request.json", {}) or {}
                if (
                    existing.get("job_type") != "h3_video_upscale"
                    or existing.get("source_rerender_job_id") != rerender_job_id
                    or existing.get("workflow_version")
                    != WINDOWS_UPSCALE_WORKFLOW_VERSION
                ):
                    continue
                status = read_json(directory / "status.json", {}) or {}
                if str(status.get("status") or "") not in {"failed", "cancelled"}:
                    return {
                        "job_id": directory.name,
                        "status": status.get("status"),
                        "already_exists": True,
                        "source_rerender_job_id": rerender_job_id,
                        "target_resolution": {"width": 1920, "height": 1080},
                        "target_fps": 60,
                    }

        created = now_iso()
        job_id = f"h3upscale_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(3)}"
        job_dir = paths["jobs"] / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        workflow["8"]["inputs"]["filename_prefix"] = (
            f"video/h3/upscale/{set_id}/{job_id}"
        )
        comfy_url = _candidate_comfy_url(data)
        source_width = int(rerender_request.get("width") or 0)
        source_height = int(rerender_request.get("height") or 0)
        request = {
            "schema_version": 1,
            "job_id": job_id,
            "job_type": "h3_video_upscale",
            "queue_name": "h3_generation",
            "queue_lane": "windows_candidate",
            "render_purpose": "upscale_1080p60",
            "render_target": "windows_comfy",
            "comfy_url": comfy_url,
            "created_at": created,
            "case_title": f"{source_set.get('source_clip_id') or selected_job_id} · 1080p60",
            "source_candidate_set_id": set_id,
            "source_selected_job_id": selected_job_id,
            "source_rerender_set_id": rerender_set_id,
            "source_rerender_job_id": rerender_job_id,
            "source_video_path": str(source_video),
            "source_output_sha256": source_sha256,
            "source_resolution": {"width": source_width, "height": source_height},
            "target_resolution": {"width": 1920, "height": 1080},
            "target_fps": 60,
            "width": 1920,
            "height": 1080,
            "fps": 60,
            "output_codec": "h264",
            "workflow_version": WINDOWS_UPSCALE_WORKFLOW_VERSION,
            "workflow_filename": workflow_path.name,
            "workflow_sha256": workflow_sha256,
            "source_project_id": source_set.get("source_project_id"),
            "source_scene_id": source_set.get("source_scene_id"),
            "source_clip_id": source_set.get("source_clip_id"),
        }
        atomic_write_json(job_dir / "request.json", request)
        atomic_write_json(job_dir / "workflow_api.json", workflow)
        atomic_write_json(
            job_dir / "manifest.json",
            {
                "schema_version": 1,
                "job_id": job_id,
                "status": "queued",
                "outputs": [],
                "created_at": created,
            },
        )
        atomic_write_json(
            job_dir / "status.json",
            {
                "job_id": job_id,
                "status": "queued",
                "stage": "Windows 1080p·60fps 업스케일 대기",
                "progress": 0,
                "created_at": created,
                "updated_at": created,
            },
        )
    return {
        "job_id": job_id,
        "status": "queued",
        "already_exists": False,
        "source_rerender_job_id": rerender_job_id,
        "target_resolution": {"width": 1920, "height": 1080},
        "target_fps": 60,
    }


def requeue_candidate_set(root: Path, candidate_set_id: str) -> dict[str, Any]:
    """Clone a terminal production candidate set with fresh random seeds."""
    paths = roots(root)
    set_id = _safe_id(candidate_set_id, "후보 세트 ID")
    source_path = paths["candidate_sets"] / set_id / "candidate_set.json"
    source_set = read_json(source_path, {}) or {}
    if not source_set or _candidate_set_deleted(source_set):
        raise FileNotFoundError(f"H3 후보 세트를 찾을 수 없습니다: {set_id}")
    if source_set.get("render_purpose") == "resolution_rerender":
        raise ValueError("해상도 재생성 작업은 후보군으로 다시 등록할 수 없습니다.")

    source_job_ids = list(source_set.get("candidate_job_ids") or [])
    if not source_job_ids:
        raise ValueError("다시 등록할 후보 작업 기록이 없습니다.")
    statuses = [
        str(
            (
                read_json(paths["jobs"] / job_id / "status.json", {}) or {}
            ).get("status")
            or "missing"
        )
        for job_id in source_job_ids
    ]
    if any(status not in TERMINAL for status in statuses):
        raise ValueError("모든 기존 후보 작업이 끝난 뒤 다시 등록할 수 있습니다.")

    source_request = read_json(
        paths["jobs"] / source_job_ids[0] / "request.json", {}
    ) or {}
    source_requests = [
        read_json(paths["jobs"] / job_id / "request.json", {}) or {}
        for job_id in source_job_ids
    ]
    source_prompt_variants = (
        list(source_set.get("prompt_variants") or [])
        if source_set.get("independent_prompts") is True
        else []
    )
    if not source_prompt_variants and len(source_requests) == 3:
        source_prompt_variants = [
            {
                "variant_id": request.get("prompt_variant_id")
                or _candidate_letter(index),
                "label": request.get("prompt_variant_label")
                or f"후보 {_candidate_letter(index)}",
                "rationale": request.get("prompt_variant_rationale") or "",
                "video_prompt": request.get("prompt") or "",
            }
            for index, request in enumerate(source_requests, start=1)
        ]
    source_references = list(source_request.get("references") or [])
    if not source_references:
        raise ValueError("기존 후보군의 참조 이미지 기록이 없습니다.")
    references = []
    for index, reference in enumerate(source_references, start=1):
        reference_path = Path(str(reference.get("source_path") or ""))
        if not reference_path.is_file():
            raise FileNotFoundError(
                f"기존 후보군의 Picture {index} 파일을 찾을 수 없습니다."
            )
        if _sha256(reference_path) != str(reference.get("sha256") or ""):
            raise ValueError(
                f"기존 후보군의 Picture {index} 파일 해시가 변경되었습니다."
            )
        references.append({
            "upload_path": str(reference_path),
            "role": reference.get("role"),
            "original_name": reference.get("original_name"),
        })

    with queue_claim_lock(paths["candidate_sets"]):
        current = read_json(source_path, {}) or {}
        if not current or _candidate_set_deleted(current):
            raise FileNotFoundError(f"H3 후보 세트를 찾을 수 없습니다: {set_id}")
        current_statuses = [
            str(
                (
                    read_json(paths["jobs"] / job_id / "status.json", {}) or {}
                ).get("status")
                or "missing"
            )
            for job_id in current.get("candidate_job_ids") or []
        ]
        if not current_statuses or any(
            status not in TERMINAL for status in current_statuses
        ):
            raise ValueError("모든 기존 후보 작업이 끝난 뒤 다시 등록할 수 있습니다.")

        requeued = enqueue_candidate_set(
            root,
            {
                "adapter_id": source_request.get("adapter_id"),
                "generation_mode": source_request.get("generation_mode"),
                "prompt": source_request.get("prompt"),
                "prompt_variants": source_prompt_variants or None,
                "references": references,
                "candidate_count": int(
                    current.get("candidate_count")
                    or source_request.get("candidate_count")
                    or len(source_job_ids)
                ),
                "seed": -1,
                "width": int(source_request.get("width") or 1280),
                "height": int(source_request.get("height") or 704),
                "duration_seconds": float(
                    source_request.get("duration_seconds") or 5
                ),
                "workflow_settings": source_request.get("workflow_settings"),
                "source_project_id": source_request.get("source_project_id"),
                "source_scene_id": source_request.get("source_scene_id"),
                "source_clip_id": source_request.get("source_clip_id"),
                "project_test_set_id": source_request.get("project_test_set_id"),
                "comfy_url": source_request.get("comfy_url"),
                "candidate_round": int(current.get("candidate_round") or 1),
                "parent_candidate_set_id": set_id,
            },
            lineage={
                "render_purpose": "candidate_rerun",
                "source_candidate_set_id": set_id,
            },
            reference_provenance=source_references,
        )
    return {
        **requeued,
        "requeued_from_candidate_set_id": set_id,
        "fresh_random_seeds": True,
    }


def list_prompt_revision_requests(root: Path) -> list[dict[str, Any]]:
    base = roots(root)["prompt_revision_requests"]
    candidate_sets = roots(root)["candidate_sets"]
    if not base.exists():
        return []
    rows = []
    for directory in (path for path in base.iterdir() if path.is_dir()):
        payload = read_json(directory / "request.json", {}) or {}
        if payload:
            row = dict(payload)
            authored_payload = read_json(
                directory / "authored_variants.json", {}
            ) or {}
            authored_variants = (
                authored_payload.get("prompt_variants")
                if isinstance(authored_payload, dict)
                else None
            )
            if isinstance(authored_variants, list) and authored_variants:
                row["authored_prompt_variants"] = authored_variants
                row["authored_variant_ids"] = [
                    str(item.get("variant_id") or "")
                    for item in authored_variants
                    if isinstance(item, dict)
                ]
                row["authored_draft_available"] = True
            else:
                row["authored_prompt_variants"] = []
                row["authored_variant_ids"] = []
                row["authored_draft_available"] = False

            result_set_id = str(row.get("result_candidate_set_id") or "")
            result_set = (
                read_json(
                    candidate_sets / result_set_id / "candidate_set.json", {}
                ) or {}
                if result_set_id
                else {}
            )
            row["result_candidate_set_deleted"] = bool(
                result_set and _candidate_set_deleted(result_set)
            )
            row["result_candidate_set_status"] = (
                str(result_set.get("status") or "") or None
            )
            row["result_clip_version"] = (
                int(result_set.get("clip_version") or 0) or None
            )
            row["result_candidate_round"] = (
                int(result_set.get("candidate_round") or 0) or None
            )
            rows.append(row)
    return sorted(
        rows,
        key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""),
        reverse=True,
    )


def update_prompt_revision_request(
    root: Path,
    prompt_revision_request_id: str,
    updates: dict[str, Any],
    *,
    expected_statuses: set[str] | None = None,
) -> dict[str, Any]:
    """Atomically update dispatcher metadata without bypassing request ownership."""
    request_id = _safe_id(prompt_revision_request_id, "프롬프트 수정 요청 ID")
    base = roots(root)["prompt_revision_requests"]
    request_path = base / request_id / "request.json"
    with queue_claim_lock(base):
        payload = read_json(request_path, {}) or {}
        if not payload:
            raise FileNotFoundError(f"프롬프트 수정 요청을 찾을 수 없습니다: {request_id}")
        current = str(payload.get("status") or "")
        if expected_statuses is not None and current not in expected_statuses:
            raise ValueError(
                f"프롬프트 수정 요청 상태가 변경되었습니다: {current or 'missing'}"
            )
        safe_updates = {
            key: value
            for key, value in updates.items()
            if key not in {
                "prompt_revision_request_id",
                "source_candidate_set_id",
                "source_prompt_variants",
                "clip_context",
                "feedback",
                "expected_variant_ids",
                "created_at",
            }
        }
        payload.update(safe_updates, updated_at=now_iso())
        atomic_write_json(request_path, payload)
        return payload


def _source_revision_context(
    root: Path,
    source_set: dict[str, Any],
    source_requests: list[dict[str, Any]],
) -> dict[str, Any]:
    source_request = source_requests[0]
    context: dict[str, Any] = {
        "project_id": source_set.get("source_project_id"),
        "scene_id": source_set.get("source_scene_id"),
        "clip_id": source_set.get("source_clip_id"),
        "duration_seconds": source_request.get("duration_seconds"),
        "references": [
            {
                "picture_index": row.get("picture_index"),
                "role": row.get("role"),
                "sha256": row.get("sha256"),
            }
            for row in source_request.get("references") or []
        ],
    }
    try:
        if source_set.get("source_project_id") and source_set.get("source_clip_id"):
            clip = h3_prompt_projects.load_clip(
                root,
                str(source_set["source_project_id"]),
                str(source_set["source_clip_id"]),
            )
            for key in (
                "continuity_in", "continuity_out", "event_state_in",
                "event_state_out", "screen_direction", "summary",
                "before_state", "after_state", "world_action_axis",
                "scenario_ko", "required_dialogue", "action_requirements",
            ):
                if clip.get(key) is not None:
                    context[key] = clip[key]
            context["reference_contract"] = [
                {
                    "picture_index": row.get("picture_index"),
                    "role": row.get("role"),
                    "label": row.get("label"),
                    "description": row.get("description"),
                }
                for row in clip.get("references") or []
            ]
    except (FileNotFoundError, ValueError):
        pass
    return context


def save_prompt_revision_request(
    root: Path, candidate_set_id: str, data: dict[str, Any]
) -> dict[str, Any]:
    """Persist feedback for later Codex authoring without running any model."""
    paths = roots(root)
    set_id = _safe_id(candidate_set_id, "후보 세트 ID")
    source_path = paths["candidate_sets"] / set_id / "candidate_set.json"
    feedback = str(data.get("feedback") or "").strip()
    if len(feedback) < 3 or len(feedback) > 4000:
        raise ValueError("수정 의견은 3~4,000자로 입력하세요.")

    with queue_claim_lock(paths["prompt_revision_requests"]):
        source_set = read_json(source_path, {}) or {}
        if not source_set or _candidate_set_deleted(source_set):
            raise FileNotFoundError(f"H3 후보 세트를 찾을 수 없습니다: {set_id}")
        if source_set.get("render_purpose") == "resolution_rerender":
            raise ValueError("해상도 재생성 결과에는 수정 의견을 저장할 수 없습니다.")
        if str(source_set.get("generation_mode") or "r2v") != "r2v":
            raise ValueError("프롬프트 수정 의견 저장은 현재 H3 R2V만 지원합니다.")
        job_ids = list(source_set.get("candidate_job_ids") or [])
        if len(job_ids) != 3 or source_set.get("independent_prompts") is not True:
            raise ValueError("독립 프롬프트 후보 3개가 있는 버전에서만 수정 의견을 저장할 수 있습니다.")
        statuses = [
            str((read_json(paths["jobs"] / job_id / "status.json", {}) or {}).get("status") or "missing")
            for job_id in job_ids
        ]
        if any(status not in TERMINAL for status in statuses):
            raise ValueError("현재 후보 3개의 생성이 모두 끝난 뒤 수정 의견을 저장할 수 있습니다.")

        source_requests = [
            read_json(paths["jobs"] / job_id / "request.json", {}) or {}
            for job_id in job_ids
        ]
        source_variants = list(source_set.get("prompt_variants") or [])
        if len(source_variants) != 3:
            source_variants = [
                {
                    "variant_id": request.get("prompt_variant_id") or _candidate_letter(index),
                    "label": request.get("prompt_variant_label") or f"후보 {_candidate_letter(index)}",
                    "rationale": request.get("prompt_variant_rationale") or "",
                    "video_prompt": request.get("prompt") or "",
                }
                for index, request in enumerate(source_requests, start=1)
            ]
        next_round = int(source_set.get("candidate_round") or 1) + 1
        expected_variant_ids = [
            _candidate_letter((next_round - 1) * 3 + offset)
            for offset in range(1, 4)
        ]
        remote_authoring = prompt_revision_authoring_config()["remote_configured"]
        pending_statuses = (
            {
                "awaiting_codex_authoring",
                "awaiting_remote_authoring",
                "remote_authoring_failed",
            }
            if remote_authoring
            else {"awaiting_codex_authoring"}
        )
        existing = next(
            (
                row for row in list_prompt_revision_requests(root)
                if row.get("source_candidate_set_id") == set_id
                and row.get("status") in pending_statuses
            ),
            None,
        )
        remote_in_progress = next(
            (
                row for row in list_prompt_revision_requests(root)
                if row.get("source_candidate_set_id") == set_id
                and row.get("status") == "remote_authoring_in_progress"
            ),
            None,
        )
        if remote_in_progress:
            raise ValueError("원격 PC가 현재 이 수정 의견으로 후보 프롬프트를 작성 중입니다.")
        stamp = now_iso()
        request_id = (
            str(existing.get("prompt_revision_request_id"))
            if existing
            else f"h3rev_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(3)}"
        )
        request_payload = {
            "schema_version": 1,
            "prompt_revision_request_id": request_id,
            "status": (
                "awaiting_remote_authoring"
                if remote_authoring
                else "awaiting_codex_authoring"
            ),
            "authoring_mode": (
                "remote_codex_api" if remote_authoring else "codex_conversation"
            ),
            "local_model_execution": False,
            "source_candidate_set_id": set_id,
            "source_project_id": source_set.get("source_project_id"),
            "source_scene_id": source_set.get("source_scene_id"),
            "source_clip_id": source_set.get("source_clip_id"),
            "source_clip_version": source_set.get("clip_version"),
            "source_candidate_round": source_set.get("candidate_round") or 1,
            "next_candidate_round": next_round,
            "expected_variant_ids": expected_variant_ids,
            "feedback": feedback,
            "source_prompt_variants": source_variants,
            "clip_context": _source_revision_context(
                root, source_set, source_requests
            ),
            "created_at": existing.get("created_at") if existing else stamp,
            "updated_at": stamp,
            "result_candidate_set_id": None,
            "applied_at": None,
            "remote_attempts": int(existing.get("remote_attempts") or 0) if existing else 0,
            "remote_error": None,
            "next_retry_at": None,
        }
        request_dir = paths["prompt_revision_requests"] / request_id
        request_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(request_dir / "request.json", request_payload)

        revision_ids = list(source_set.get("prompt_revision_request_ids") or [])
        if request_id not in revision_ids:
            revision_ids.append(request_id)
        source_set.update(
            pending_prompt_revision_request_id=request_id,
            prompt_revision_request_ids=revision_ids,
            updated_at=stamp,
        )
        atomic_write_json(source_path, source_set)
    return {**request_payload, "feedback_updated": bool(existing), "jobs_created": 0}


def apply_authored_prompt_revision(
    root: Path, prompt_revision_request_id: str, data: dict[str, Any]
) -> dict[str, Any]:
    """Queue Codex-authored prompts after validating the saved feedback contract."""
    paths = roots(root)
    request_id = _safe_id(prompt_revision_request_id, "프롬프트 수정 요청 ID")
    request_path = paths["prompt_revision_requests"] / request_id / "request.json"
    request_payload = read_json(request_path, {}) or {}
    if not request_payload:
        raise FileNotFoundError(f"프롬프트 수정 요청을 찾을 수 없습니다: {request_id}")
    if request_payload.get("status") not in {
        "awaiting_codex_authoring",
        "awaiting_remote_authoring",
        "remote_authoring_in_progress",
    }:
        raise ValueError("작성 대기 또는 원격 작성 중인 프롬프트 수정 요청이 아닙니다.")

    source_id = _safe_id(
        str(request_payload.get("source_candidate_set_id") or ""),
        "원본 후보 세트 ID",
    )
    source_path = paths["candidate_sets"] / source_id / "candidate_set.json"
    source_set = read_json(source_path, {}) or {}
    if not source_set or _candidate_set_deleted(source_set):
        raise FileNotFoundError(f"원본 H3 후보 세트를 찾을 수 없습니다: {source_id}")
    authored = h3_prompt_projects.normalize_prompt_variants(
        data.get("prompt_variants")
    )
    if len(authored) != 3:
        raise ValueError("대화에서 작성한 전체 프롬프트는 정확히 3개여야 합니다.")
    expected_ids = list(request_payload.get("expected_variant_ids") or [])
    if [row["variant_id"] for row in authored] != expected_ids:
        raise ValueError(
            "작성 후보 ID가 저장된 다음 순번과 다릅니다: "
            + ", ".join(expected_ids)
        )
    if len({row["video_prompt"] for row in authored}) != 3:
        raise ValueError("작성한 후보 3개의 전체 프롬프트가 서로 달라야 합니다.")

    job_ids = list(source_set.get("candidate_job_ids") or [])
    if len(job_ids) != 3:
        raise ValueError("원본 후보 세트의 렌더 작업 3개를 찾을 수 없습니다.")
    source_request = read_json(paths["jobs"] / job_ids[0] / "request.json", {}) or {}
    duration_seconds = float(source_request.get("duration_seconds") or 0)
    detailed_descriptions = {
        h3_prompt_projects.extract_detailed_description(row["video_prompt"])
        for row in authored
    }
    if len(detailed_descriptions) != 3:
        raise ValueError("작성 후보 3개는 detailed_description 연출부터 서로 달라야 합니다.")
    for row in authored:
        report = h3_prompt_contract.validate_prompt(
            row["video_prompt"], duration_seconds=duration_seconds
        )
        if not report.valid:
            reasons = "; ".join(issue.message for issue in report.errors[:5])
            raise ValueError(
                f"후보 {row['variant_id']}가 새 H3 프롬프트 계약을 통과하지 못했습니다: "
                + reasons
            )
    source_references = list(source_request.get("references") or [])
    references = []
    for index, reference in enumerate(source_references, start=1):
        reference_path = Path(str(reference.get("source_path") or ""))
        if not reference_path.is_file():
            raise FileNotFoundError(f"원본 후보군의 Picture {index} 파일을 찾을 수 없습니다.")
        if _sha256(reference_path) != str(reference.get("sha256") or ""):
            raise ValueError(f"원본 후보군의 Picture {index} 파일 해시가 변경되었습니다.")
        references.append({
            "upload_path": str(reference_path),
            "role": reference.get("role"),
            "original_name": reference.get("original_name"),
        })

    revised = enqueue_candidate_set(
        root,
        {
            "adapter_id": source_request.get("adapter_id"),
            "generation_mode": "r2v",
            "prompt_variants": authored,
            "references": references,
            "candidate_count": 3,
            "seed": -1,
            "width": int(source_request.get("width") or 1280),
            "height": int(source_request.get("height") or 704),
            "duration_seconds": float(source_request.get("duration_seconds") or 5),
            "workflow_settings": source_request.get("workflow_settings"),
            "source_project_id": source_request.get("source_project_id"),
            "source_scene_id": source_request.get("source_scene_id"),
            "source_clip_id": source_request.get("source_clip_id"),
            "project_test_set_id": source_request.get("project_test_set_id"),
            "comfy_url": source_request.get("comfy_url"),
            "candidate_round": int(request_payload.get("next_candidate_round") or 1),
            "revision_feedback": request_payload.get("feedback"),
            "parent_candidate_set_id": source_id,
        },
        lineage={
            "render_purpose": "feedback_revision",
            "source_candidate_set_id": source_id,
        },
        reference_provenance=source_references,
    )
    stamp = now_iso()
    authored_by = str(data.get("authored_by") or request_payload.get("authoring_mode") or "codex_conversation")
    if authored_by not in {"codex_conversation", "remote_codex_api"}:
        authored_by = "codex_conversation"
    request_payload.update(
        status="applied_and_queued",
        result_candidate_set_id=revised["candidate_set_id"],
        applied_at=stamp,
        updated_at=stamp,
        authored_by=authored_by,
        remote_error=None,
        next_retry_at=None,
    )
    atomic_write_json(request_path, request_payload)
    source_set.update(
        pending_prompt_revision_request_id=None,
        applied_prompt_revision_request_id=request_id,
        updated_at=stamp,
    )
    atomic_write_json(source_path, source_set)
    return {
        **revised,
        "prompt_revision_request_id": request_id,
        "authored_by": authored_by,
    }


def restore_candidate_version(root: Path, candidate_set_id: str) -> dict[str, Any]:
    """Restore an immutable candidate version by cloning its snapshot as a new version."""
    paths = roots(root)
    source_id = _safe_id(candidate_set_id, "후보 세트 ID")
    source_path = paths["candidate_sets"] / source_id / "candidate_set.json"
    source = read_json(source_path, {}) or {}
    if not source or _candidate_set_deleted(source):
        raise FileNotFoundError(f"H3 후보 세트를 찾을 수 없습니다: {source_id}")
    if source.get("render_purpose") == "resolution_rerender":
        raise ValueError("해상도 재생성 기록은 클립 버전으로 복원할 수 없습니다.")
    job_ids = list(source.get("candidate_job_ids") or [])
    if not job_ids:
        raise ValueError("복원할 후보 작업 기록이 없습니다.")
    statuses = [
        str((read_json(paths["jobs"] / job_id / "status.json", {}) or {}).get("status") or "missing")
        for job_id in job_ids
    ]
    if any(status not in TERMINAL for status in statuses):
        raise ValueError("생성이 끝난 클립 버전만 복원할 수 있습니다.")

    created = now_iso()
    restored_id = f"h3set_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(3)}"
    version = _next_clip_version(
        root,
        str(source.get("source_project_id") or "") or None,
        str(source.get("source_scene_id") or "") or None,
        str(source.get("source_clip_id") or "") or None,
    )
    restored = copy.deepcopy(source)
    restored_selection = _candidate_selected_jobs(source)[-1:]
    restored.update({
        "schema_version": 2,
        "candidate_set_id": restored_id,
        "created_at": created,
        "updated_at": created,
        "clip_version": version,
        "render_purpose": "version_restore",
        "source_candidate_set_id": source_id,
        "restored_from_candidate_set_id": source_id,
        "parent_candidate_set_id": source_id,
        "version_restored": True,
        "deleted": False,
        "deleted_at": None,
        "selected_jobs": restored_selection,
        "selected_job_id": (
            restored_selection[0]["job_id"] if restored_selection else None
        ),
        "selected_at": (
            restored_selection[0].get("selected_at") if restored_selection else None
        ),
    })
    target_dir = paths["candidate_sets"] / restored_id
    target_dir.mkdir(parents=True, exist_ok=False)
    atomic_write_json(target_dir / "candidate_set.json", restored)
    reconciled = reconcile(root, restored_id)
    return reconciled[0] if reconciled else restored


def _project_snapshot(
    root: Path,
    project_id: str,
    scene_id: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    project_id = _safe_id(project_id, "H3 프로젝트 ID")
    scene_id = _safe_id(scene_id, "H3 씬 ID") if scene_id else None
    overview = h3_prompt_projects.project_clips(root, project_id)
    clips = list(overview.get("clips") or [])
    if scene_id:
        clips = [
            clip for clip in clips
            if str(clip.get("scene_id") or "") == scene_id
        ]
        if not clips:
            raise FileNotFoundError(f"H3 씬을 찾을 수 없습니다: {scene_id}")
    if not clips:
        raise ValueError("테스트 세트로 만들 H3 클립이 없습니다.")
    projects = h3_prompt_projects.list_projects(root).get("projects") or []
    project = next((row for row in projects if row.get("project_id") == project_id), None)
    if not project:
        raise FileNotFoundError("H3 프로젝트를 찾을 수 없습니다.")
    generation_mode = str(project.get("generation_mode") or "").strip()
    signature_payload = [{
        "generation_mode": generation_mode,
        "scene_id": clip.get("scene_id"),
        "clip_id": clip.get("clip_id"),
        "duration_seconds": clip.get("duration_seconds"),
        "video_prompt": clip.get("video_prompt"),
        "references": [{
            "picture_index": row.get("picture_index"),
            "role": row.get("role"),
            "source_path": row.get("source_path"),
            "linked": row.get("linked"),
        } for row in clip.get("references") or []],
    } for clip in clips]
    signature = hashlib.sha256(json.dumps(signature_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return project, clips, signature


def _test_set_clips(source_clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "generation_mode": str(clip.get("generation_mode") or "r2v"),
        "scene_id": str(clip.get("scene_id") or ""),
        "clip_id": str(clip.get("clip_id") or ""),
        "sequence": int(clip.get("sequence") or 0),
        "duration_seconds": float(clip.get("duration_seconds") or 0),
        "picture_count": len(clip.get("references") or []),
        "ready": bool(clip.get("ready")),
        "errors": list(clip.get("errors") or []),
    } for clip in source_clips]


def _project_test_set_deleted(payload: dict[str, Any]) -> bool:
    return bool(
        payload.get("deleted")
        or payload.get("deleted_at")
        or payload.get("status") == "deleted"
    )


def _project_test_set_identity(
    payload: dict[str, Any],
) -> tuple[str, str, str | None, str]:
    project_id = str(payload.get("project_id") or "").strip()
    try:
        schema_version = int(payload.get("schema_version") or 1)
    except (TypeError, ValueError):
        schema_version = 1
    scope = (
        str(payload.get("scope") or "project").strip()
        if schema_version >= 2
        else "project"
    )
    if scope != "scene":
        scope = "project"
    scene_id = (
        str(payload.get("scene_id") or "").strip() or None
        if scope == "scene"
        else None
    )
    generation_mode = (
        str(payload.get("generation_mode") or "r2v").strip().lower()
        if schema_version >= 3
        else "r2v"
    )
    if generation_mode not in {"r2v", "i2v"}:
        generation_mode = "r2v"
    return project_id, scope, scene_id, generation_mode


def _existing_test_set(
    root: Path,
    *,
    project_id: str,
    scope: str,
    scene_id: str | None,
    generation_mode: str,
    signature: str,
) -> dict[str, Any] | None:
    base = roots(root)["project_test_sets"]
    if not base.exists():
        return None
    for directory in sorted(
        (path for path in base.iterdir() if path.is_dir()), reverse=True
    ):
        payload = read_json(directory / "project_test_set.json", {}) or {}
        if _project_test_set_deleted(payload):
            continue
        payload_scope = str(payload.get("scope") or "project")
        payload_scene_id = str(payload.get("scene_id") or "") or None
        if (
            payload.get("project_id") == project_id
            and payload_scope == scope
            and payload_scene_id == scene_id
            and str(payload.get("generation_mode") or "r2v") == generation_mode
            and payload.get("source_signature") == signature
            and payload.get("status") in {"ready_to_queue", "blocked"}
        ):
            return {**payload, "already_exists": True}
    return None


def _create_test_set(
    root: Path,
    *,
    project: dict[str, Any],
    project_id: str,
    scene_id: str | None,
    source_clips: list[dict[str, Any]],
    signature: str,
) -> dict[str, Any]:
    scope = "scene" if scene_id else "project"
    generation_mode = str(project.get("generation_mode") or "").strip().lower()
    if generation_mode not in {"r2v", "i2v"}:
        raise ValueError("지원하지 않는 H3 프로젝트 생성 방식입니다.")
    clips = _test_set_clips(source_clips)
    created = now_iso()
    blocked = [clip for clip in clips if not clip["ready"]]
    title = str(project.get("title") or project_id)
    name = (
        f"{title} · {scene_id} 씬 {generation_mode.upper()} 테스트"
        if scene_id
        else f"{title} · 전체 클립 {generation_mode.upper()} 테스트"
    )
    base = roots(root)["project_test_sets"]
    with queue_claim_lock(base):
        existing = _existing_test_set(
            root,
            project_id=project_id,
            scope=scope,
            scene_id=scene_id,
            generation_mode=generation_mode,
            signature=signature,
        )
        if existing:
            return existing
        test_set_id = (
            f"h3test_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(3)}"
        )
        payload = {
            "schema_version": 3,
            "project_test_set_id": test_set_id,
            "name": name,
            "scope": scope,
            "project_id": project_id,
            "scene_id": scene_id,
            "generation_mode": generation_mode,
            "status": "blocked" if blocked else "ready_to_queue",
            "created_at": created,
            "updated_at": created,
            "source_signature": signature,
            "scene_count": len({clip["scene_id"] for clip in clips}),
            "clip_count": len(clips),
            "clip_ids": [clip["clip_id"] for clip in clips],
            "ready_count": len(clips) - len(blocked),
            "blocked_count": len(blocked),
            "clips": clips,
            "candidate_count": None,
            "candidate_set_ids": [],
            "job_count": 0,
        }
        directory = base / test_set_id
        directory.mkdir(parents=True, exist_ok=False)
        atomic_write_json(directory / "project_test_set.json", payload)
        return payload


def create_project_test_set(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    if str(data.get("scene_id") or "").strip():
        return create_scene_test_set(root, data)
    project_id = str(data.get("project_id") or "").strip()
    project, source_clips, signature = _project_snapshot(root, project_id)
    requested_mode = str(data.get("generation_mode") or "").strip().lower()
    if requested_mode and requested_mode != project.get("generation_mode"):
        raise ValueError("선택한 페이지의 생성 방식과 H3 프로젝트 종류가 다릅니다.")
    return _create_test_set(
        root,
        project=project,
        project_id=project_id,
        scene_id=None,
        source_clips=source_clips,
        signature=signature,
    )


def create_scene_test_set(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    project_id = _safe_id(
        str(data.get("project_id") or ""), "H3 프로젝트 ID"
    )
    scene_id = _safe_id(str(data.get("scene_id") or ""), "H3 씬 ID")
    project, source_clips, signature = _project_snapshot(
        root, project_id, scene_id
    )
    requested_mode = str(data.get("generation_mode") or "").strip().lower()
    if requested_mode and requested_mode != project.get("generation_mode"):
        raise ValueError("선택한 페이지의 생성 방식과 H3 프로젝트 종류가 다릅니다.")
    return _create_test_set(
        root,
        project=project,
        project_id=project_id,
        scene_id=scene_id,
        source_clips=source_clips,
        signature=signature,
    )


def list_project_test_sets(root: Path) -> list[dict[str, Any]]:
    base = roots(root)["project_test_sets"]
    if not base.exists():
        return []
    rows = []
    for directory in (path for path in base.iterdir() if path.is_dir()):
        payload = read_json(directory / "project_test_set.json", {}) or {}
        if payload and not _project_test_set_deleted(payload):
            rows.append(payload)
    return sorted(rows, key=lambda row: str(row.get("created_at") or ""), reverse=True)


def delete_project_test_set(
    root: Path, project_test_set_id: str
) -> dict[str, Any]:
    """Soft-delete one logical project/scene registration and its old markers."""
    test_set_id = _safe_id(
        project_test_set_id, "프로젝트 테스트 세트 ID"
    )
    base = roots(root)["project_test_sets"]
    requested_path = base / test_set_id / "project_test_set.json"
    stamp = now_iso()
    tombstoned_ids: list[str] = []
    changed_ids: list[str] = []
    requested_deleted_at: str | None = None

    with queue_claim_lock(base):
        requested = read_json(requested_path, {}) or {}
        if not requested:
            raise FileNotFoundError(
                f"H3 프로젝트 테스트 세트를 찾을 수 없습니다: {test_set_id}"
            )
        project_id, scope, scene_id, generation_mode = _project_test_set_identity(requested)
        if not project_id:
            raise ValueError("프로젝트 정보가 없는 테스트 세트는 삭제할 수 없습니다.")
        if (
            project_id == model_test_r2v.DRAGON_SEASON_1_PROJECT_ID
            and scope == "project"
        ):
            raise ValueError(
                "용 키우기 시즌 1 Official 전체 프로젝트 테스트 세트는 "
                "기본 제공 세트이므로 삭제할 수 없습니다."
            )
        requested_already_deleted = _project_test_set_deleted(requested)
        identity = (project_id, scope, scene_id, generation_mode)
        for directory in sorted(
            (path for path in base.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        ):
            path = directory / "project_test_set.json"
            payload = read_json(path, {}) or {}
            if not payload or _project_test_set_identity(payload) != identity:
                continue
            already_deleted = _project_test_set_deleted(payload)
            # A retry for an old tombstone must not delete a newer registration
            # created after the original request completed.  The current marker
            # remains addressable by its own ID and can be deleted explicitly.
            if requested_already_deleted and not already_deleted:
                continue
            status_before_delete = str(payload.get("status") or "")
            if already_deleted:
                status_before_delete = str(
                    payload.get("status_before_delete") or ""
                )
            deleted_at = str(payload.get("deleted_at") or stamp)
            needs_write = not (
                already_deleted
                and payload.get("deleted") is True
                and payload.get("deleted_at")
                and "status_before_delete" in payload
                and payload.get("status") == "deleted"
            )
            if needs_write:
                payload.update(
                    deleted=True,
                    deleted_at=deleted_at,
                    status_before_delete=status_before_delete,
                    status="deleted",
                    updated_at=stamp,
                )
                atomic_write_json(path, payload)
            tombstoned_ids.append(
                str(payload.get("project_test_set_id") or directory.name)
            )
            if directory.name == test_set_id:
                requested_deleted_at = deleted_at
            if not already_deleted:
                changed_ids.append(
                    str(payload.get("project_test_set_id") or directory.name)
                )

    return {
        "project_test_set_id": test_set_id,
        "project_id": project_id,
        "scope": scope,
        "scene_id": scene_id,
        "generation_mode": generation_mode,
        "deleted": True,
        "soft_deleted": True,
        "already_deleted": requested_already_deleted,
        "deleted_at": requested_deleted_at or stamp,
        "tombstoned_project_test_set_ids": tombstoned_ids,
        "newly_tombstoned_count": len(changed_ids),
        "sessions_preserved": True,
        "results_preserved": True,
        "assets_preserved": True,
        "queues_preserved": True,
        "files_preserved": True,
    }


def delete_prompt_project(
    root: Path,
    project_id: str,
    *,
    expected_generation_mode: str = "r2v",
) -> dict[str, Any]:
    """Permanently delete one authored H3 project after dependency checks."""
    project_id = _safe_id(project_id, "H3 프로젝트 ID")
    if project_id in h3_prompt_projects.PROTECTED_PROJECT_IDS:
        raise ValueError("기본 제공 H3 프로젝트 템플릿은 삭제할 수 없습니다.")
    directory = h3_prompt_projects.project_dir(root, project_id)
    if not directory.is_dir():
        raise FileNotFoundError(f"H3 프로젝트를 찾을 수 없습니다: {project_id}")
    try:
        manifest = json.loads(
            (directory / "manifest.json").read_text(encoding="utf-8")
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise ValueError("H3 프로젝트 manifest.json을 읽을 수 없습니다.") from exc
    generation_mode = h3_prompt_projects.PROJECT_KIND_MODES.get(
        str(manifest.get("project_kind") or "")
    )
    if not generation_mode:
        raise ValueError("지원하지 않는 H3 프로젝트 종류입니다.")
    if expected_generation_mode and generation_mode != expected_generation_mode:
        raise ValueError(
            f"선택한 프로젝트는 H3 {generation_mode.upper()} 프로젝트입니다."
        )

    dependency_files = []
    project_prefix = str(directory.resolve()) + "/"
    base = h3_prompt_projects.projects_root(root)
    for other in sorted(path for path in base.iterdir() if path.is_dir()):
        if other == directory:
            continue
        for path in sorted(other.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".md"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            logical_dependency = (
                '"asset_source_project"' in text and project_id in text
            )
            if project_prefix in text or logical_dependency:
                dependency_files.append(
                    path.relative_to(base).as_posix()
                )
    if dependency_files:
        raise ValueError(
            "다른 H3 프로젝트가 이 프로젝트의 이미지를 참조하고 있습니다. "
            "참조 프로젝트를 먼저 독립화하세요: "
            + ", ".join(dependency_files[:5])
        )

    registrations = [
        row
        for row in list_project_test_sets(root)
        if str(row.get("project_id") or "") == project_id
    ]
    if registrations:
        raise ValueError(
            "이 프로젝트에 연결된 테스트 세트가 있습니다. "
            "07·08 모델 테스트에서 테스트 세트를 먼저 삭제하세요."
        )
    active_candidate_sets = [
        row
        for row in reconcile(root)
        if str(row.get("source_project_id") or "") == project_id
        and str(row.get("status") or "") in {"generating", "cancelling"}
    ]
    if active_candidate_sets:
        raise ValueError(
            "이 프로젝트의 후보 큐가 실행 중입니다. "
            "완료하거나 강제종료한 뒤 프로젝트를 삭제하세요."
        )

    files = [path for path in directory.rglob("*") if path.is_file()]
    deleted_bytes = sum(path.stat().st_size for path in files)
    staging_root = roots(root)["base"] / ".project-delete-staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    staged = staging_root / f"{project_id}_{secrets.token_hex(4)}"
    with queue_claim_lock(staging_root):
        if not directory.is_dir():
            raise FileNotFoundError(f"H3 프로젝트를 찾을 수 없습니다: {project_id}")
        directory.rename(staged)
    try:
        shutil.rmtree(staged)
    except Exception:
        with queue_claim_lock(staging_root):
            if staged.exists() and not directory.exists():
                staged.rename(directory)
        raise
    return {
        "project_id": project_id,
        "title": str(manifest.get("title") or project_id),
        "generation_mode": generation_mode,
        "deleted": True,
        "deleted_file_count": len(files),
        "deleted_bytes": deleted_bytes,
        "candidate_results_preserved": True,
        "recoverable": False,
    }


def reconcile_test_queues(root: Path, test_queue_id: str | None = None) -> list[dict[str, Any]]:
    paths = roots(root)
    if test_queue_id:
        directories = [paths["test_queues"] / _safe_id(test_queue_id, "H3 테스트 큐 ID")]
    elif paths["test_queues"].exists():
        directories = [path for path in paths["test_queues"].iterdir() if path.is_dir()]
    else:
        directories = []
    rows = []
    for directory in directories:
        path = directory / "queue.json"
        payload = read_json(path, {}) or {}
        if not payload:
            continue
        statuses = [
            str((read_json(paths["jobs"] / job_id / "status.json", {}) or {}).get("status") or "missing")
            for job_id in payload.get("job_ids") or []
        ]
        counts = {
            "queued_count": sum(value == "queued" for value in statuses),
            "running_count": sum(value in ACTIVE for value in statuses),
            "completed_count": sum(value == "completed" for value in statuses),
            "failed_count": sum(value in {"failed", "cancelled"} for value in statuses),
        }
        if payload.get("cancel_requested") and statuses and all(value in TERMINAL for value in statuses):
            status = "cancelled"
        elif payload.get("cancel_requested"):
            status = "cancelling"
        elif not statuses:
            status = str(payload.get("status") or "empty")
        elif all(value in TERMINAL for value in statuses):
            status = "completed" if counts["completed_count"] == len(statuses) else "completed_with_failures"
        elif counts["running_count"]:
            status = "running"
        else:
            status = "queued"
        if payload.get("status") != status or any(payload.get(key) != value for key, value in counts.items()):
            payload.update(status=status, updated_at=now_iso(), **counts)
            atomic_write_json(path, payload)
        rows.append(payload)
    return sorted(rows, key=lambda row: str(row.get("created_at") or ""), reverse=True)


def resolve_job_dir(root: Path, job_id: str) -> Path:
    job_id = _safe_id(job_id, "작업 ID")
    h3 = roots(root)["jobs"] / job_id
    if (h3 / "request.json").is_file():
        return h3
    archived = root / "jobs" / job_id
    if (archived / "request.json").is_file():
        return archived
    raise FileNotFoundError(f"작업 폴더를 찾을 수 없습니다: {job_id}")


def queue_project_test_set(root: Path, project_test_set_id: str, data: dict[str, Any]) -> dict[str, Any]:
    test_set_id = _safe_id(project_test_set_id, "프로젝트 테스트 세트 ID")
    path = roots(root)["project_test_sets"] / test_set_id / "project_test_set.json"
    payload = read_json(path, {}) or {}
    if not payload:
        raise FileNotFoundError("H3 프로젝트 테스트 세트를 찾을 수 없습니다.")
    if payload.get("status") not in {"ready_to_queue", "queue_failed"}:
        raise ValueError("큐 등록 가능한 H3 프로젝트 테스트 세트가 아닙니다.")
    adapter_id = str(data.get("adapter_id") or "").strip()
    if not adapter_id:
        raise ValueError("H3 워크플로우를 선택하세요.")
    candidate_count = int(data.get("candidate_count") or 1)
    if candidate_count < 1 or candidate_count > 6:
        raise ValueError("클립당 후보 개수는 1~6개여야 합니다.")
    scene_id = (
        str(payload.get("scene_id") or "") or None
        if str(payload.get("scope") or "project") == "scene"
        else None
    )
    project, clips, signature = _project_snapshot(
        root, str(payload.get("project_id") or ""), scene_id
    )
    if signature != payload.get("source_signature"):
        raise ValueError("프로젝트 내용이 테스트 세트 생성 후 변경되었습니다. 테스트 세트를 다시 만드세요.")
    blocked = [clip for clip in clips if not clip["ready"]]
    if blocked:
        raise ValueError(f"준비되지 않은 H3 클립이 {len(blocked)}개 있습니다.")
    if str(project.get("generation_mode") or payload.get("generation_mode") or "") == "r2v" and all(
        len(clip.get("prompt_variants") or []) == 3 for clip in clips
    ):
        candidate_count = 3
    payload.update(status="queueing", adapter_id=adapter_id, candidate_count=candidate_count, updated_at=now_iso())
    atomic_write_json(path, payload)
    candidate_set_ids = []
    base_seed = int(data.get("seed", -1))
    try:
        for clip_index, clip in enumerate(clips):
            clip_seed = -1 if base_seed < 0 else (base_seed + clip_index * candidate_count) % ((1 << 63) - 1)
            candidate = enqueue_candidate_set(root, {
                "adapter_id": adapter_id,
                "prompt": clip["video_prompt"],
                "prompt_variants": clip.get("prompt_variants") or None,
                "duration_seconds": clip["duration_seconds"],
                "candidate_count": candidate_count,
                "seed": clip_seed,
                "width": 1280,
                "height": 704,
                "source_project_id": payload["project_id"],
                "source_scene_id": clip["scene_id"],
                "source_clip_id": clip["clip_id"],
                "project_test_set_id": test_set_id,
                "references": [{
                    "role": row.get("role"),
                    "project_id": payload["project_id"],
                    "clip_id": clip["clip_id"],
                    "project_picture_index": row.get("picture_index"),
                } for row in clip.get("references") or []],
            })
            candidate_set_ids.append(candidate["candidate_set_id"])
            payload.update(candidate_set_ids=candidate_set_ids, job_count=len(candidate_set_ids) * candidate_count, updated_at=now_iso())
            atomic_write_json(path, payload)
    except Exception as exc:
        payload.update(status="partial_queue_failed" if candidate_set_ids else "queue_failed", queue_error=str(exc), updated_at=now_iso())
        atomic_write_json(path, payload)
        raise
    payload.update(status="queued", queued_at=now_iso(), updated_at=now_iso(), queue_error=None)
    atomic_write_json(path, payload)
    return payload


def _latest_authored_scene_prompt(
    revision_requests: list[dict[str, Any]],
    project_id: str,
    scene_id: str,
    clip_id: str,
) -> dict[str, Any] | None:
    matches = [
        row
        for row in revision_requests
        if row.get("authored_draft_available")
        and str(row.get("source_project_id") or "") == project_id
        and str(row.get("source_scene_id") or "") == scene_id
        and str(row.get("source_clip_id") or "") == clip_id
        and len(row.get("authored_prompt_variants") or []) == 3
    ]
    if not matches:
        return None
    matches.sort(
        key=lambda row: (
            int(
                row.get("result_clip_version")
                or row.get("next_candidate_round")
                or 0
            ),
            str(row.get("updated_at") or row.get("applied_at") or ""),
            str(row.get("prompt_revision_request_id") or ""),
        ),
        reverse=True,
    )
    selected = matches[0]
    return {
        "prompt_variants": list(selected["authored_prompt_variants"]),
        "prompt_revision_request_id": str(
            selected.get("prompt_revision_request_id") or ""
        ),
        "clip_version": int(
            selected.get("result_clip_version")
            or selected.get("next_candidate_round")
            or 0
        ),
        "candidate_round": int(
            selected.get("result_candidate_round")
            or selected.get("next_candidate_round")
            or 0
        ),
        "variant_ids": [
            str(row.get("variant_id") or "")
            for row in selected["authored_prompt_variants"]
        ],
    }


def enqueue_scene_candidate_sets(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Queue one independent candidate set for every ready clip in a scene."""
    queue_lane = str(data.get("queue_lane") or "windows_candidate").strip()
    if queue_lane not in {"windows_candidate", "local_generation"}:
        raise ValueError("H3 생성 큐는 Windows 후보 또는 로컬 생성이어야 합니다.")
    project_id = _safe_id(str(data.get("project_id") or ""), "H3 프로젝트 ID")
    blocked_reason = h3_prompt_projects.project_generation_block_reason(root, project_id)
    if blocked_reason:
        raise ValueError(blocked_reason)
    scene_id = _safe_id(str(data.get("scene_id") or ""), "H3 씬 ID")
    adapter_id = str(data.get("adapter_id") or "").strip()
    if not adapter_id:
        raise ValueError("H3 워크플로우를 선택하세요.")
    candidate_count = int(data.get("candidate_count") or 3)
    if candidate_count < 1 or candidate_count > 6:
        raise ValueError("클립당 후보 개수는 1~6개여야 합니다.")
    width = int(data.get("width") or 1280)
    height = int(data.get("height") or 704)
    overview = h3_prompt_projects.project_clips(root, project_id)
    generation_mode = str(
        data.get("generation_mode") or overview.get("generation_mode") or "r2v"
    ).strip().lower()
    if generation_mode not in {"r2v", "i2v"}:
        raise ValueError("H3 생성 방식은 R2V 또는 I2V여야 합니다.")
    allowed_resolutions = (
        I2V_OUTPUT_RESOLUTIONS
        if generation_mode == "i2v"
        else R2V_OUTPUT_RESOLUTIONS
    )
    if (width, height) not in allowed_resolutions:
        if generation_mode == "i2v":
            raise ValueError(
                "H3 I2V 출력 해상도는 832 × 480, 1280 × 704 또는 "
                "1376 × 768만 지원합니다."
            )
        raise ValueError(
            "H3 R2V 출력 해상도는 608 × 352, 832 × 480, 960 × 544, "
            "1280 × 704 또는 1280 × 736만 지원합니다."
        )
    if overview.get("generation_mode") not in {None, generation_mode}:
        raise ValueError("선택한 프로젝트와 H3 생성 방식이 일치하지 않습니다.")
    scene = next(
        (row for row in overview.get("scenes") or [] if str(row.get("scene_id") or "") == scene_id),
        None,
    )
    if not scene:
        raise FileNotFoundError(f"H3 씬을 찾을 수 없습니다: {scene_id}")
    clips = list(scene.get("clips") or [])
    if not clips:
        raise ValueError("후보군으로 등록할 H3 클립이 없습니다.")
    blocked = [clip for clip in clips if not clip.get("ready")]
    if blocked:
        details = ", ".join(
            f"{clip.get('clip_id')}: {'; '.join(clip.get('errors') or ['준비되지 않음'])}"
            for clip in blocked[:5]
        )
        raise ValueError(f"준비되지 않은 클립 {len(blocked)}개가 있어 씬 등록을 중단했습니다. {details}")
    prompt_version_sources = []
    if generation_mode == "r2v":
        revision_requests = list_prompt_revision_requests(root)
        resolved_clips = []
        for clip in clips:
            resolved = dict(clip)
            authored = _latest_authored_scene_prompt(
                revision_requests,
                project_id,
                scene_id,
                str(clip.get("clip_id") or ""),
            )
            if authored:
                for variant in authored["prompt_variants"]:
                    report = h3_prompt_contract.validate_prompt(
                        str(variant.get("video_prompt") or ""),
                        duration_seconds=float(clip.get("duration_seconds") or 0),
                    )
                    if not report.valid:
                        reasons = "; ".join(
                            issue.message for issue in report.errors[:5]
                        )
                        raise ValueError(
                            f"{clip.get('clip_id')}의 최신 작성 후보 "
                            f"{variant.get('variant_id')}가 새 H3 계약을 통과하지 "
                            f"못했습니다: {reasons}"
                        )
                resolved["prompt_variants"] = authored["prompt_variants"]
                resolved["video_prompt"] = authored["prompt_variants"][0][
                    "video_prompt"
                ]
                prompt_version_sources.append({
                    "clip_id": clip["clip_id"],
                    "source": "latest_authored_revision",
                    **{
                        key: value
                        for key, value in authored.items()
                        if key != "prompt_variants"
                    },
                })
            else:
                variants = list(clip.get("prompt_variants") or [])
                prompt_version_sources.append({
                    "clip_id": clip["clip_id"],
                    "source": "project_prompt",
                    "prompt_revision_request_id": None,
                    "clip_version": 1,
                    "candidate_round": 1,
                    "variant_ids": [
                        str(row.get("variant_id") or "") for row in variants
                    ],
                })
            resolved_clips.append(resolved)
        clips = resolved_clips
    if generation_mode == "r2v" and all(
        len(clip.get("prompt_variants") or []) == 3 for clip in clips
    ):
        candidate_count = 3
    base_seed = int(data.get("seed", -1))
    preflight_errors = []
    for clip_index, clip in enumerate(clips):
        references = list(clip.get("references") or [])
        try:
            for reference_index, reference in enumerate(references, start=1):
                source = h3_prompt_projects.picture_path(
                    root,
                    project_id,
                    str(clip["clip_id"]),
                    int(reference.get("picture_index") or reference_index),
                )
                if not source.is_file():
                    raise FileNotFoundError(
                        f"Picture {reference_index} 파일을 찾을 수 없습니다."
                    )
            variants = list(clip.get("prompt_variants") or [])
            prompt = str(
                (variants[0].get("video_prompt") if variants else None)
                or clip["video_prompt"]
            )
            _compile_workflow(
                root,
                adapter_id,
                {
                    "prompt": prompt,
                    "seed": 0 if base_seed < 0 else base_seed + clip_index,
                    "width": width,
                    "height": height,
                    "fps": 24,
                    "duration_seconds": clip["duration_seconds"],
                    "filename_prefix": "video/h3/scene-preflight",
                },
                len(references),
                generation_mode,
                data.get("workflow_settings"),
            )
        except Exception as exc:
            preflight_errors.append(f"{clip.get('clip_id')}: {exc}")
    if preflight_errors:
        raise ValueError(
            "씬 전체 사전검사에 실패하여 아무 후보군도 등록하지 않았습니다. "
            + "; ".join(preflight_errors[:5])
        )
    candidate_sets = []
    try:
        for clip_index, clip in enumerate(clips):
            clip_seed = (
                -1
                if base_seed < 0
                else (base_seed + clip_index * candidate_count) % ((1 << 63) - 1)
            )
            candidate_sets.append(enqueue_candidate_set(root, {
                "adapter_id": adapter_id,
                "queue_lane": queue_lane,
                "generation_mode": generation_mode,
                "prompt": clip["video_prompt"],
                "prompt_variants": clip.get("prompt_variants") or None,
                "duration_seconds": clip["duration_seconds"],
                "candidate_count": candidate_count,
                "seed": clip_seed,
                "width": width,
                "height": height,
                "workflow_settings": data.get("workflow_settings"),
                "source_project_id": project_id,
                "source_scene_id": scene_id,
                "source_clip_id": clip["clip_id"],
                "references": [{
                    "role": row.get("role"),
                    "project_id": project_id,
                    "clip_id": clip["clip_id"],
                    "project_picture_index": row.get("picture_index"),
                } for row in clip.get("references") or []],
            }))
    except Exception as exc:
        if candidate_sets:
            raise RuntimeError(
                f"씬 후보군을 {len(candidate_sets)}/{len(clips)}클립까지 등록한 뒤 실패했습니다: {exc}"
            ) from exc
        raise
    candidate_set_ids = [row["candidate_set_id"] for row in candidate_sets]
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "clip_count": len(clips),
        "candidate_count": candidate_count,
        "job_count": len(clips) * candidate_count,
        "width": width,
        "height": height,
        "generation_mode": generation_mode,
        "queue_lane": queue_lane,
        "candidate_set_ids": candidate_set_ids,
        "job_ids": [job_id for row in candidate_sets for job_id in row["candidate_job_ids"]],
        "prompt_version_sources": prompt_version_sources,
    }


def _candidate_set_deleted(payload: dict[str, Any]) -> bool:
    return bool(
        payload.get("deleted")
        or payload.get("deleted_at")
        or payload.get("status") == "deleted"
    )


def _candidate_selected_jobs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized multi-selection rows with legacy scalar fallback."""
    raw = payload.get("selected_jobs")
    if isinstance(raw, list):
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw:
            if isinstance(item, dict):
                job_id = str(item.get("job_id") or "").strip()
                selected_at = str(item.get("selected_at") or "") or None
            else:
                job_id = str(item or "").strip()
                selected_at = None
            if not job_id or job_id in seen:
                continue
            seen.add(job_id)
            rows.append({"job_id": job_id, "selected_at": selected_at})
        return rows
    legacy_job_id = str(payload.get("selected_job_id") or "").strip()
    if not legacy_job_id:
        return []
    return [{
        "job_id": legacy_job_id,
        "selected_at": str(payload.get("selected_at") or "") or None,
    }]


def _reconcile_candidate_path(
    paths: dict[str, Path], path: Path
) -> dict[str, Any] | None:
    payload = read_json(path, {}) or {}
    if not payload or _candidate_set_deleted(payload):
        return None
    statuses = [
        str(
            (
                read_json(paths["jobs"] / job_id / "status.json", {}) or {}
            ).get("status")
            or "missing"
        )
        for job_id in payload.get("candidate_job_ids") or []
    ]
    selected_jobs = _candidate_selected_jobs(payload)
    if (
        payload.get("cancel_requested")
        and statuses
        and all(value in TERMINAL for value in statuses)
    ):
        status = "cancelled"
    elif payload.get("cancel_requested"):
        status = "cancelling"
    elif selected_jobs:
        status = "selected"
    elif statuses and all(value in TERMINAL for value in statuses):
        status = (
            "awaiting_candidate_selection"
            if "completed" in statuses
            else "generation_failed"
        )
    else:
        status = "generating"
    if payload.get("status") != status:
        payload.update(status=status, updated_at=now_iso())
        atomic_write_json(path, payload)
    return {**payload, "selected_jobs": selected_jobs}


def reconcile(root: Path, candidate_set_id: str | None = None) -> list[dict[str, Any]]:
    paths = roots(root)
    dirs = []
    if candidate_set_id:
        dirs = [paths["candidate_sets"] / _safe_id(candidate_set_id, "후보 세트 ID")]
    elif paths["candidate_sets"].exists():
        dirs = [path for path in paths["candidate_sets"].iterdir() if path.is_dir()]
    results = []
    with queue_claim_lock(paths["candidate_sets"]):
        for directory in dirs:
            payload = _reconcile_candidate_path(
                paths, directory / "candidate_set.json"
            )
            if payload:
                results.append(payload)
    return sorted(
        results,
        key=lambda row: str(row.get("created_at") or ""),
        reverse=True,
    )


def force_stop_group(
    root: Path,
    group_id: str,
    *,
    queued_only: bool = False,
) -> dict[str, Any]:
    """Stop only the unfinished jobs belonging to one H3 queue group."""
    group_id = _safe_id(group_id, "H3 큐 그룹 ID")
    paths = roots(root)
    candidates = [
        ("test_queue", paths["test_queues"] / group_id / "queue.json", "job_ids"),
        ("candidate_set", paths["candidate_sets"] / group_id / "candidate_set.json", "candidate_job_ids"),
    ]
    matches = [
        (kind, path, key)
        for kind, path, key in candidates
        if path.is_file()
    ]
    if not matches:
        raise FileNotFoundError(f"H3 큐 그룹을 찾을 수 없습니다: {group_id}")
    if len(matches) > 1:
        raise RuntimeError(f"동일한 ID의 H3 큐 그룹이 둘 이상입니다: {group_id}")
    kind, group_path, job_key = matches[0]
    group_lock_root = (
        paths["candidate_sets"] if kind == "candidate_set" else paths["test_queues"]
    )
    stamp = now_iso()
    cancelled: list[str] = []
    requested: list[str] = []
    prompt_targets: list[tuple[str, str, str]] = []
    benchmark_cancellations: list[dict[str, Any]] = []
    with queue_claim_lock(paths["jobs"]), queue_claim_lock(group_lock_root):
        group = read_json(group_path, {}) or {}
        if not group or (
            kind == "candidate_set" and _candidate_set_deleted(group)
        ):
            raise FileNotFoundError(f"H3 큐 그룹을 찾을 수 없습니다: {group_id}")
        job_ids = [
            _safe_id(str(value), "H3 작업 ID")
            for value in group.get(job_key) or []
        ]
        if queued_only:
            current_statuses = {
                job_id: str(
                    (
                        read_json(paths["jobs"] / job_id / "status.json", {})
                        or {}
                    ).get("status")
                    or "missing"
                )
                for job_id in job_ids
            }
            running_job_ids = [
                job_id
                for job_id, current in current_statuses.items()
                if current not in TERMINAL and current not in {"queued", "missing"}
            ]
            queued_job_ids = [
                job_id
                for job_id, current in current_statuses.items()
                if current in {"queued", "missing"}
            ]
            if running_job_ids or not queued_job_ids:
                return {
                    "group_id": group_id,
                    "group_type": kind,
                    "status": "skipped_running" if running_job_ids else "skipped_no_pending",
                    "cancelled_job_ids": [],
                    "cancel_requested_job_ids": [],
                    "running_job_ids": running_job_ids,
                    "queued_only": True,
                    "completed_jobs_preserved": True,
                    "warnings": [],
                }
        for job_id in job_ids:
            job_dir = paths["jobs"] / job_id
            status = read_json(job_dir / "status.json", {}) or {}
            current = str(status.get("status") or "missing")
            if current in TERMINAL:
                continue
            message = f"H3 큐 그룹 {group_id} 강제정지 요청"
            if current == "queued" or current == "missing":
                update_status(
                    job_dir,
                    "cancelled",
                    stage="사용자가 H3 큐 그룹 강제정지",
                    message=message,
                    cancel_requested=True,
                    cancelled_at=stamp,
                    progress=0.0,
                )
                cancelled.append(job_id)
                request = read_json(job_dir / "request.json", {}) or {}
                if request.get("job_type") in {"h3_r2v_benchmark", "h3_model_benchmark"}:
                    benchmark_cancellations.append(request)
            else:
                update_status(
                    job_dir,
                    current,
                    stage="H3 큐 그룹 강제정지 요청",
                    message=message,
                    cancel_requested=True,
                    cancel_requested_at=stamp,
                )
                requested.append(job_id)
                request = read_json(job_dir / "request.json", {}) or {}
                manifest = read_json(job_dir / "manifest.json", {}) or {}
                prompt_id = str(status.get("prompt_id") or manifest.get("prompt_id") or "").strip()
                if prompt_id:
                    prompt_targets.append((job_id, str(request.get("comfy_url") or "http://127.0.0.1:8188"), prompt_id))
            manifest = read_json(job_dir / "manifest.json", {}) or {}
            manifest.update(
                status="cancelled" if job_id in cancelled else str(manifest.get("status") or current),
                cancel_requested=True,
                cancel_requested_at=stamp,
                updated_at=stamp,
            )
            if job_id in cancelled:
                manifest["cancelled_at"] = stamp
            atomic_write_json(job_dir / "manifest.json", manifest)
        group.update(
            status="cancelling" if requested else "cancelled",
            cancel_requested=True,
            cancel_requested_at=stamp,
            force_stopped_at=stamp,
            updated_at=stamp,
        )
        atomic_write_json(group_path, group)
    warnings = []
    if benchmark_cancellations:
        import benchmark_jobs

        for request in benchmark_cancellations:
            try:
                benchmark_jobs.record_result(
                    root,
                    request,
                    status="cancelled",
                    error=f"H3 큐 그룹 {group_id} 강제정지로 취소했습니다.",
                )
            except Exception as exc:
                warnings.append(
                    f"{request.get('job_id')}: 모델 테스트 DB 취소 동기화 실패 "
                    f"({type(exc).__name__}: {exc})"
                )
    for job_id, comfy_url, prompt_id in prompt_targets:
        try:
            ComfyClient(comfy_url).cancel_prompt(prompt_id)
        except Exception as exc:
            warnings.append(f"{job_id}: ComfyUI 취소 확인 실패 ({type(exc).__name__}: {exc})")
    if kind == "test_queue":
        group = reconcile_test_queues(root, group_id)[0]
    else:
        group = reconcile(root, group_id)[0]
    return {
        "group_id": group_id,
        "group_type": kind,
        "status": group.get("status"),
        "cancelled_job_ids": cancelled,
        "cancel_requested_job_ids": requested,
        "benchmark_cancelled_count": len(benchmark_cancellations),
        "completed_jobs_preserved": True,
        "queued_only": queued_only,
        "warnings": warnings,
    }


def state(root: Path) -> dict[str, Any]:
    import candidate_review_queue

    paths = roots(root)
    candidate_sets = reconcile(root)
    deleted_candidate_set_ids: set[str] = set()
    if paths["candidate_sets"].exists():
        with queue_claim_lock(paths["candidate_sets"]):
            for directory in paths["candidate_sets"].iterdir():
                if not directory.is_dir():
                    continue
                payload = read_json(directory / "candidate_set.json", {}) or {}
                if _candidate_set_deleted(payload):
                    deleted_candidate_set_ids.add(directory.name)
    candidate_sets = [
        payload
        for payload in candidate_sets
        if payload.get("candidate_set_id") not in deleted_candidate_set_ids
    ]
    jobs = []
    if paths["jobs"].exists():
        for directory in sorted((p for p in paths["jobs"].iterdir() if p.is_dir()), reverse=True):
            request = read_json(directory / "request.json", {}) or {}
            if (
                request.get("job_type") == "h3_r2v_generate"
                and request.get("candidate_set_id") in deleted_candidate_set_ids
            ):
                continue
            if request.get("seed") is not None:
                request = {**request, "seed_text": str(request["seed"])}
            jobs.append({
                "job_id": directory.name,
                "request": request,
                "status": read_json(directory / "status.json", {}) or {},
                "manifest": read_json(directory / "manifest.json", {}) or {},
            })
    return {
        "jobs": jobs,
        "candidate_sets": candidate_sets,
        "prompt_revision_requests": list_prompt_revision_requests(root),
        "project_test_sets": list_project_test_sets(root),
        "test_queues": reconcile_test_queues(root),
        "worker": read_json(paths["worker_status"], {}) or {},
        "workers": {
            "local_generation": read_json(paths["worker_status"], {}) or {},
            "windows_candidate": read_json(
                paths["windows_candidate_worker_status"], {}
            ) or {},
        },
        "prompt_authoring": prompt_revision_authoring_config(),
        "candidate_render": candidate_render_config(),
        "candidate_ai_review": candidate_review_queue.state(root),
    }


def select_candidate(root: Path, candidate_set_id: str, job_id: str) -> dict[str, Any]:
    paths = roots(root)
    set_id = _safe_id(candidate_set_id, "후보 세트 ID")
    job_id = _safe_id(job_id, "작업 ID")
    path = paths["candidate_sets"] / set_id / "candidate_set.json"
    with queue_claim_lock(paths["candidate_sets"]):
        payload = read_json(path, {}) or {}
        if not payload or _candidate_set_deleted(payload):
            raise FileNotFoundError(f"H3 후보 세트를 찾을 수 없습니다: {set_id}")
        if job_id not in payload.get("candidate_job_ids", []):
            raise ValueError("해당 후보 세트의 작업이 아닙니다.")
        status = read_json(paths["jobs"] / job_id / "status.json", {}) or {}
        if status.get("status") != "completed":
            raise ValueError("완료된 후보만 선택할 수 있습니다.")
        selected_jobs = _candidate_selected_jobs(payload)
        if (
            len(selected_jobs) == 1
            and selected_jobs[0]["job_id"] == job_id
        ):
            return {**payload, "selected_jobs": selected_jobs}
        selected_at = now_iso()
        selected_jobs = [{"job_id": job_id, "selected_at": selected_at}]
        payload.update(
            selected_job_id=job_id,
            selected_jobs=selected_jobs,
            status="selected",
            selected_at=selected_at,
            updated_at=selected_at,
        )
        atomic_write_json(path, payload)
        return payload


def clear_candidate_selection(
    root: Path,
    candidate_set_id: str,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Clear the exclusive selected candidate and derive the set state."""
    paths = roots(root)
    set_id = _safe_id(candidate_set_id, "후보 세트 ID")
    requested_job_id = _safe_id(job_id, "선택 작업 ID") if job_id else None
    path = paths["candidate_sets"] / set_id / "candidate_set.json"
    with queue_claim_lock(paths["candidate_sets"]):
        payload = read_json(path, {}) or {}
        if not payload or _candidate_set_deleted(payload):
            raise FileNotFoundError(f"H3 후보 세트를 찾을 수 없습니다: {set_id}")

        selected_jobs = _candidate_selected_jobs(payload)
        previous_job_ids = [row["job_id"] for row in selected_jobs]
        previous_job_id = str(payload.get("selected_job_id") or "") or None
        remaining = (
            [row for row in selected_jobs if row["job_id"] != requested_job_id]
            if requested_job_id
            else []
        )
        removed_job_ids = [
            job_id for job_id in previous_job_ids
            if not any(row["job_id"] == job_id for row in remaining)
        ]
        had_selection_fields = bool(removed_job_ids)
        if had_selection_fields or "selected_jobs" not in payload:
            latest = remaining[-1] if remaining else None
            payload.update(
                selected_job_id=latest["job_id"] if latest else None,
                selected_jobs=remaining,
                selected_at=latest.get("selected_at") if latest else None,
                updated_at=now_iso(),
            )
            atomic_write_json(path, payload)

        reconciled = _reconcile_candidate_path(paths, path)
        if not reconciled:
            raise FileNotFoundError(f"H3 후보 세트를 찾을 수 없습니다: {set_id}")
        return {
            **reconciled,
            "selection_cleared": had_selection_fields,
            "previous_selected_job_id": previous_job_id,
            "previous_selected_job_ids": previous_job_ids,
            "cleared_job_ids": removed_job_ids,
        }


def delete_candidate_set(root: Path, candidate_set_id: str) -> dict[str, Any]:
    """Soft-delete a terminal candidate set and retire unfinished AI reviews."""
    paths = roots(root)
    set_id = _safe_id(candidate_set_id, "후보 세트 ID")
    path = paths["candidate_sets"] / set_id / "candidate_set.json"

    # Keep queued work from being claimed between the terminal-state check and
    # soft deletion. Candidate-set mutations use their own lock as well.
    with queue_claim_lock(paths["jobs"]), queue_claim_lock(paths["candidate_sets"]):
        payload = read_json(path, {}) or {}
        if not payload:
            raise FileNotFoundError(f"H3 후보 세트를 찾을 수 없습니다: {set_id}")

        already_deleted = _candidate_set_deleted(payload)
        job_ids = [
            _safe_id(str(value), "H3 작업 ID")
            for value in payload.get("candidate_job_ids") or []
        ]
        statuses: dict[str, str] = {}
        unfinished: list[str] = []
        for job_id in job_ids:
            job_status = read_json(
                paths["jobs"] / job_id / "status.json", {}
            ) or {}
            status = str(job_status.get("status") or "missing")
            statuses[job_id] = status
            if status not in TERMINAL:
                unfinished.append(job_id)

        if unfinished and not already_deleted:
            details = ", ".join(
                f"{job_id}({statuses[job_id]})" for job_id in unfinished[:5]
            )
            if len(unfinished) > 5:
                details += f" 외 {len(unfinished) - 5}개"
            raise RuntimeError(
                "대기·실행 중인 후보 작업이 있어 후보군을 삭제할 수 "
                f"없습니다. 먼저 후보군을 강제종료하세요: {details}"
            )

        if not already_deleted:
            stamp = now_iso()
            payload.update(
                deleted=True,
                deleted_at=stamp,
                status_before_delete=str(payload.get("status") or ""),
                status="deleted",
                updated_at=stamp,
            )
            atomic_write_json(path, payload)

    # The candidate-set deletion flag is committed before taking the review
    # queue lock. This prevents new automatic reviews from being registered,
    # while avoiding nested locks shared with the review worker.
    import candidate_review_queue

    review_cleanup = candidate_review_queue.retire_candidate_set_reviews(
        root, set_id,
    )

    return {
        "candidate_set_id": set_id,
        "deleted": True,
        "soft_deleted": True,
        "already_deleted": already_deleted,
        "deleted_at": payload.get("deleted_at"),
        "job_count": len(job_ids),
        "job_ids": job_ids,
        "job_statuses": statuses,
        "jobs_preserved": True,
        "outputs_preserved": True,
        "sources_preserved": True,
        "completed_reviews_preserved": True,
        "review_cleanup": review_cleanup,
    }


def video_path(root: Path, job_id: str) -> Path:
    job_id = _safe_id(job_id, "작업 ID")
    job_dir = roots(root)["jobs"] / job_id
    status = read_json(job_dir / "status.json", {}) or {}
    if status.get("status") != "completed":
        raise FileNotFoundError("완료된 H3 영상 출력이 없습니다.")
    manifest = read_json(job_dir / "manifest.json", {}) or {}
    path = Path(str(manifest.get("local_video_path") or ""))
    if not path.is_file():
        raise FileNotFoundError("H3 영상 출력이 없습니다.")
    return path
