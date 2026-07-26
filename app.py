from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import streamlit as st

import correction_policy
from batch_manager import (
    attach_job_to_batch,
    get_or_create_open_batch,
    list_batches,
    load_automation_settings,
    save_automation_settings,
)
from comfy_client import ComfyClient
from job_queue import (
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    atomic_write_json,
    list_jobs,
    now_iso,
    read_json,
    update_status,
)
from workflow_builder import (
    KOREAN_SPEECH_POLICY,
    SegmentSpec,
    preview_segments,
    resolve_seed,
    sanitize_token,
)


HOME = Path.home()
ENGINE_ROOT = Path(os.environ.get("VIDEO_ENGINE_ROOT", HOME / "local-ai/video-engine"))
JOBS_ROOT = ENGINE_ROOT / "jobs"
WORKER_STATUS_PATH = ENGINE_ROOT / "worker_status.json"
AUTOMATION_SETTINGS_PATH = ENGINE_ROOT / "runtime" / "automation_settings.json"
ENGINE_STATE_PATH = ENGINE_ROOT / "runtime" / "engine_state.json"
DEFAULT_TEMPLATE = Path(
    os.environ.get(
        "LTX_WORKFLOW_TEMPLATE",
        HOME
        / "ai-workspace/apps/ComfyUI/user/default/workflows/"
        "LTX_Director_2_Workflow_Hotfix_api.json",
    )
).expanduser()
DEFAULT_WORKFLOW_DIR = Path(
    os.environ.get("COMFY_WORKFLOW_DIR", str(DEFAULT_TEMPLATE.parent))
).expanduser()
WORKFLOW_KIND_LABELS = {
    "create": "생성 (CR)",
    "modify": "수정 (MD)",
    "check": "검수 (CH)",
    "other": "미분류 API",
}
WORKFLOW_KIND_ORDER = {
    "create": 0,
    "modify": 1,
    "check": 2,
    "other": 9,
}
DEFAULT_COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
DEFAULT_COMFY_PUBLIC_URL = os.environ.get("COMFY_PUBLIC_URL", "").strip()
DEFAULT_COMFY_START_SCRIPT = Path(
    os.environ.get("COMFY_START_SCRIPT", HOME / "bin/ai-start-comfy")
).expanduser()
DEFAULT_COMFY_TMUX_SESSION = os.environ.get("COMFY_TMUX_SESSION", "comfy").strip() or "comfy"
DEFAULT_COMFY_START_TIMEOUT = float(os.environ.get("COMFY_START_TIMEOUT", "180"))
DEFAULT_GLOBAL_PROMPT = (
    "Project style: Original ocean fantasy growth-adventure world, "
    "cinematic fantasy realism, wide 16:9. "
    + KOREAN_SPEECH_POLICY
)
MIN_SEED = -1
MAX_SEED = (1 << 63) - 2
DEFAULT_SEED = 831913303995591
DEFAULT_RESOLUTION_LABEL = "1280 × 704 · 기본 · 32배수"
RESOLUTION_PRESETS: dict[str, tuple[int, int]] = {
    "512 × 288 · 저해상도 테스트": (512, 288),
    "1024 × 576 · 빠른 생성": (1024, 576),
    DEFAULT_RESOLUTION_LABEL: (1280, 704),
    "1536 × 864 · 고해상도": (1536, 864),
    "2048 × 1152 · 매우 높음 / 메모리 주의": (2048, 1152),
}
STATUS_LABELS = {
    "queued": "우리 큐 대기",
    "preparing": "작업 준비",
    "uploading": "이미지 업로드",
    "building": "워크플로 구성",
    "submitting": "ComfyUI 제출",
    "comfy_queued": "ComfyUI 큐 대기",
    "submitted": "제출 확인 중",
    "running": "영상 생성 중",
    "completed": "완료",
    "failed": "실패",
    "cancelled": "취소",
}


def parse_seed_input(value: str) -> int:
    normalized = value.strip()
    if not normalized:
        raise ValueError("시드를 입력하세요. 자동 생성은 -1입니다.")
    try:
        seed = int(normalized, 10)
    except ValueError as exc:
        raise ValueError("시드는 -1 또는 정수여야 합니다.") from exc
    if seed < MIN_SEED or seed > MAX_SEED:
        raise ValueError(f"시드는 {MIN_SEED} 이상 {MAX_SEED} 이하여야 합니다.")
    return seed


def load_template(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise ValueError("API 워크플로 템플릿이 비어 있거나 객체 형식이 아닙니다.")
    if any(not isinstance(node, dict) or "class_type" not in node for node in payload.values()):
        raise ValueError("ComfyUI API 워크플로 형식이 아닙니다.")
    return payload


def classify_workflow(path: Path) -> str:
    name = path.name.strip().upper()
    if name.startswith("(CR)"):
        return "create"
    if name.startswith("(MD)"):
        return "modify"
    if name.startswith("(CH)"):
        return "check"
    return "other"


def discover_api_workflows(workflow_dir: Path) -> list[Path]:
    if not workflow_dir.is_dir():
        return []

    workflows = [
        path
        for path in workflow_dir.rglob("*.json")
        if path.is_file() and "api" in path.name.casefold()
    ]
    workflows.sort(
        key=lambda path: (
            WORKFLOW_KIND_ORDER[classify_workflow(path)],
            str(path.relative_to(workflow_dir)).casefold(),
        )
    )
    return workflows


def workflow_display_name(path: Path, workflow_dir: Path) -> str:
    kind = classify_workflow(path)
    try:
        relative_name = str(path.relative_to(workflow_dir))
    except ValueError:
        relative_name = path.name
    return f"[{WORKFLOW_KIND_LABELS[kind]}] {relative_name}"


def default_workflow_index(workflows: list[Path]) -> int:
    if not workflows:
        return 0

    for index, path in enumerate(workflows):
        if classify_workflow(path) == "create":
            return index

    try:
        default_resolved = DEFAULT_TEMPLATE.resolve()
        for index, path in enumerate(workflows):
            if path.resolve() == default_resolved:
                return index
    except OSError:
        pass
    return 0


def safe_uploaded_name(original_name: str, content: bytes, index: int) -> str:
    suffix = Path(original_name).suffix.lower() or ".png"
    stem = sanitize_token(Path(original_name).stem, fallback=f"image_{index:02d}")
    digest = hashlib.sha256(content).hexdigest()[:10]
    return f"{index:02d}_{stem}_{digest}{suffix}"


def tmux_session_exists(session_name: str) -> bool:
    completed = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return completed.returncode == 0


def run_comfy_start_script(script_path: Path) -> str:
    if not script_path.is_file():
        raise FileNotFoundError(f"ComfyUI 시작 스크립트를 찾을 수 없습니다: {script_path}")
    if not os.access(script_path, os.X_OK):
        raise PermissionError(f"ComfyUI 시작 스크립트에 실행 권한이 없습니다: {script_path}")
    completed = subprocess.run(
        [str(script_path)],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    output = "\n".join(
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part and part.strip()
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"ComfyUI 시작 스크립트 실패 (exit={completed.returncode})\n{output}"
        )
    return output or "ComfyUI 시작 스크립트 실행 완료"


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def worker_is_online(payload: dict[str, Any]) -> bool:
    updated = parse_timestamp(payload.get("updated_at"))
    if updated is None:
        return False
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - updated.astimezone(timezone.utc)).total_seconds()
    return age < 15


def format_elapsed(seconds: Any) -> str:
    try:
        value = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return "-"
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}시간 {minutes}분 {secs}초"
    if minutes:
        return f"{minutes}분 {secs}초"
    return f"{secs}초"


def public_file_url(base_url: str, file_info: dict[str, Any]) -> str:
    params = urlencode(
        {
            "filename": file_info.get("filename", ""),
            "subfolder": file_info.get("subfolder", ""),
            "type": file_info.get("type", "output"),
        }
    )
    return f"{base_url.rstrip('/')}/view?{params}"


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status or "알 수 없음")


VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".gif"}
BATCH_FAILURE_FIELDS = {
    "engine_switch_error": "엔진 전환",
    "ai_review_errors": "AI 영상 검수",
    "video_review_preparation_errors": "검수 영상 준비",
    "retake_preparation_errors": "Retake 준비",
    "contact_sheet_preparation_errors": "Contact Sheet 준비",
    "post_review_engine_error": "검수 후 ComfyUI 복귀",
    "failed_generation_job_ids": "생성 실패 작업",
    "failed_review_job_ids": "검수 실패 작업",
    "failed_modify_job_ids": "Retake 실패 작업",
    "failed_check_job_ids": "보조 검수 실패 작업",
}


def redact_sensitive_text(value: Any, limit: int = 12000) -> str:
    text = str(value or "")
    patterns = (
        (r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+", r"\1[REDACTED]"),
        (
            r"(?i)((?:api[_-]?key|access[_-]?token|token|password|secret)"
            r"\b[\x22\x27]?\s*[:=]\s*[\x22\x27]?)[^\s,;}\]\x22\x27]+",
            r"\1[REDACTED]",
        ),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    if len(text) > limit:
        return text[:limit] + "\n… 화면 표시 길이 제한으로 이후 내용 생략"
    return text


def job_type_of(job: dict[str, Any]) -> str:
    request = job.get("request") or {}
    manifest = job.get("manifest") or {}
    return str(request.get("job_type") or manifest.get("job_type") or "generate")


def lineage_root_id(job: dict[str, Any]) -> str:
    request = job.get("request") or {}
    manifest = job.get("manifest") or {}
    return str(
        request.get("root_job_id")
        or manifest.get("root_job_id")
        or job.get("job_id")
        or ""
    )


def primary_video_output(job: dict[str, Any]) -> dict[str, Any] | None:
    manifest = job.get("manifest") or {}
    status = job.get("status") or {}
    for item in manifest.get("outputs") or status.get("outputs") or []:
        if Path(str(item.get("filename") or "")).suffix.lower() in VIDEO_SUFFIXES:
            return item
    return None


def video_source_for_job(
    job: dict[str, Any],
    settings: dict[str, Any],
) -> tuple[str | None, str]:
    manifest = job.get("manifest") or {}
    local_value = manifest.get("review_video_local_path")
    if local_value:
        local_path = Path(str(local_value))
        if local_path.is_file():
            return str(local_path), local_path.name

    file_info = primary_video_output(job)
    if file_info is None:
        return None, ""
    request = job.get("request") or {}
    public_base = (
        request.get("comfy_public_url")
        or settings.get("comfy_public_url")
        or settings.get("comfy_url")
    )
    if not public_base:
        return None, str(file_info.get("filename") or "")
    return public_file_url(str(public_base), file_info), str(
        file_info.get("filename") or ""
    )


def load_source_review(job: dict[str, Any]) -> dict[str, Any]:
    manifest = job.get("manifest") or {}
    request = job.get("request") or {}
    report = manifest.get("ai_review")
    if isinstance(report, dict):
        return report
    path_value = request.get("source_review_report") or manifest.get(
        "source_review_report"
    )
    if path_value:
        payload = read_json(Path(str(path_value)), {}) or {}
        if isinstance(payload, dict):
            return payload
    return {}



def _next_manual_modify_cycle(root_job_id: str) -> int:
    highest = 0
    for job_dir in JOBS_ROOT.iterdir():
        if not job_dir.is_dir():
            continue
        request = read_json(job_dir / "request.json", {}) or {}
        if str(request.get("root_job_id") or "") != root_job_id:
            continue
        highest = max(highest, int(request.get("modify_cycle") or 0))
    return highest + 1


def queue_manual_correction(
    *,
    original: dict[str, Any],
    parent: dict[str, Any],
    settings: dict[str, Any],
    correction_mode: str,
    correction_prompt: str,
    start_seconds: float,
    end_seconds: float,
    source_duration_seconds: float,
    uploaded_video_name: str | None,
    uploaded_video_content: bytes | None,
) -> tuple[str, str]:
    if correction_mode not in {"partial_retake", "full_regeneration"}:
        raise ValueError(f"지원하지 않는 수정 방식입니다: {correction_mode}")
    correction_prompt = correction_prompt.strip()
    if not correction_prompt:
        raise ValueError("수정 프롬프트를 입력하세요.")

    root_job_id = lineage_root_id(original)
    root_request = original.get("request") or {}
    source_segments = list(root_request.get("segments") or [])
    if not source_segments:
        raise ValueError("원본 이미지·구간 정보를 찾을 수 없습니다.")

    if correction_mode == "partial_retake":
        if not uploaded_video_content or not uploaded_video_name:
            raise ValueError("부분 수정을 위해 기준 영상을 업로드하세요.")
        if source_duration_seconds <= 0:
            raise ValueError("기준 영상 길이를 확인할 수 없습니다.")
        if start_seconds < 0 or end_seconds <= start_seconds:
            raise ValueError("부분 수정 시작·종료 시간을 확인하세요.")
        end_seconds = min(end_seconds, source_duration_seconds)
        template_path = (
            DEFAULT_WORKFLOW_DIR / "(MD)LTX_Retake_Partial_API.json"
        ).expanduser()
        pipeline_stage = "retake_generation"
        workflow_kind_label = "사용자 재수정 (부분 구간)"
        token = "manual_retake"
    else:
        template_path = Path(
            str(
                root_request.get("workflow_source_path")
                or root_request.get("template_path")
                or ""
            )
        ).expanduser()
        if not template_path.is_file():
            template_path = Path(
                str(root_request.get("template_path") or "")
            ).expanduser()
        pipeline_stage = "full_regeneration"
        workflow_kind_label = "사용자 재수정 (전체 재생성)"
        token = "manual_regenerate"

    if not template_path.is_file():
        raise FileNotFoundError(f"수정용 API 템플릿이 없습니다: {template_path}")

    automation_settings = load_automation_settings(ENGINE_ROOT)
    batch = get_or_create_open_batch(ENGINE_ROOT, automation_settings)
    batch_id = str(batch["batch_id"])
    cycle = _next_manual_modify_cycle(root_job_id)
    job_id = f"{root_job_id}__{token}_c{cycle}_{secrets.token_hex(2)}"
    job_dir = JOBS_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    workflow_snapshot = job_dir / "selected_workflow_api.json"
    shutil.copy2(template_path, workflow_snapshot)

    correction_block = (
        "MANDATORY USER CORRECTIONS:\n- " + correction_prompt
    )
    segments: list[dict[str, Any]] = []
    for source in source_segments:
        segment = dict(source)
        base_prompt = str(segment.get("prompt") or "").strip()
        segment["prompt"] = (
            f"{base_prompt}\n\n{correction_block}"
            if base_prompt
            else correction_block
        )
        segments.append(segment)

    original_global_prompt = str(root_request.get("global_prompt") or "").strip()
    global_prompt = (
        f"{original_global_prompt}\n\n{correction_block}"
        if original_global_prompt
        else correction_block
    )
    created_at = now_iso()
    seed = secrets.randbelow((1 << 63) - 1)
    parent_job_id = str(parent.get("job_id") or "")
    parent_dir = JOBS_ROOT / parent_job_id
    source_report_path = parent_dir / "ai_review_report.json"

    request: dict[str, Any] = {
        "schema_version": 2,
        "job_type": "modify",
        "pipeline_stage": pipeline_stage,
        "correction_mode": correction_mode,
        "manual_correction": True,
        "job_id": job_id,
        "batch_id": batch_id,
        "job_dir": str(job_dir),
        "created_at": created_at,
        "job_name": f"{root_request.get('job_name') or root_job_id} manual {cycle}",
        "template_path": str(workflow_snapshot),
        "workflow_source_path": str(template_path),
        "workflow_filename": template_path.name,
        "workflow_kind": "modify",
        "workflow_kind_label": workflow_kind_label,
        "comfy_url": settings["comfy_url"],
        "comfy_public_url": settings["comfy_public_url"],
        "comfy_start_script": str(settings["comfy_start_script"]),
        "comfy_start_timeout": DEFAULT_COMFY_START_TIMEOUT,
        "auto_start_comfy": bool(settings["auto_start_comfy"]),
        "fps": int(root_request["fps"]),
        "seed": seed,
        "resolution": dict(root_request["resolution"]),
        "global_prompt": global_prompt,
        "duration_mode": root_request.get("duration_mode"),
        "target_total_seconds": root_request.get("target_total_seconds"),
        "filename_prefix": (
            f"video/manual_retakes/{root_job_id}/cycle_{cycle}"
            if correction_mode == "partial_retake"
            else f"video/manual_regenerations/{root_job_id}/cycle_{cycle}"
        ),
        "segments": segments,
        "parent_job_id": parent_job_id,
        "root_job_id": root_job_id,
        "modify_cycle": cycle,
        "attempt": cycle,
        "automation": dict(batch.get("automation") or automation_settings),
        "retake_corrections": "- " + correction_prompt,
        "source_review_report": (
            str(source_report_path) if source_report_path.is_file() else ""
        ),
    }

    if correction_mode == "partial_retake":
        suffix = Path(str(uploaded_video_name)).suffix.lower()
        if suffix not in VIDEO_SUFFIXES:
            raise ValueError("MP4, WEBM, MOV, MKV 또는 AVI 영상을 업로드하세요.")
        video_dir = job_dir / "artifacts"
        video_dir.mkdir(parents=True, exist_ok=True)
        stored_video = (
            video_dir
            / f"manual_source_{hashlib.sha256(uploaded_video_content).hexdigest()[:10]}{suffix}"
        )
        stored_video.write_bytes(uploaded_video_content)
        request.update(
            {
                "retake_source_video_path": str(stored_video),
                "retake_source_duration_seconds": source_duration_seconds,
                "retake_start_seconds": start_seconds,
                "retake_end_seconds": end_seconds,
                "retake_strength": 1.0,
                "retake_primary_issue": {
                    "severity": "user",
                    "type": "manual_correction",
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "evidence_ko": "사용자가 UI에서 직접 지정한 재수정 구간",
                },
            }
        )

    manifest = {
        "schema_version": 2,
        "job_id": job_id,
        "batch_id": batch_id,
        "parent_job_id": parent_job_id,
        "root_job_id": root_job_id,
        "job_type": "modify",
        "pipeline_stage": pipeline_stage,
        "correction_mode": correction_mode,
        "manual_correction": True,
        "modify_cycle": cycle,
        "created_at": created_at,
        "status": "queued",
        "workflow_source_path": str(template_path),
        "workflow_filename": template_path.name,
        "workflow_kind": "modify",
        "workflow_kind_label": workflow_kind_label,
        "seed": seed,
        "resolution": request["resolution"],
        "fps": request["fps"],
        "segments": segments,
        "retake_corrections": request["retake_corrections"],
        "source_review_report": request["source_review_report"],
        "outputs": [],
    }
    for key in (
        "retake_source_video_path",
        "retake_source_duration_seconds",
        "retake_start_seconds",
        "retake_end_seconds",
        "retake_strength",
        "retake_primary_issue",
    ):
        if key in request:
            manifest[key] = request[key]

    atomic_write_json(job_dir / "request.json", request)
    atomic_write_json(job_dir / "manifest.json", manifest)
    update_status(
        job_dir,
        "queued",
        stage="사용자 재수정 worker 대기",
        message=workflow_kind_label,
        progress=0.0,
        created_at=created_at,
    )
    # 새 배치의 생성 단계로 수집해야 완료 후 자동 검수가 정상 연결됩니다.
    attach_job_to_batch(
        ENGINE_ROOT,
        batch_id=batch_id,
        job_id=job_id,
        job_type="generate",
    )
    return job_id, batch_id


def render_review_issues(review: dict[str, Any]) -> None:
    issues = [
        issue
        for issue in review.get("issues") or []
        if isinstance(issue, dict)
    ]
    if not issues:
        st.success("기록된 수정 필요 항목이 없습니다.")
        return
    st.markdown("**수정이 필요한 내용**")
    st.dataframe(
        [
            {
                "심각도": issue.get("severity", "-"),
                "유형": issue.get("type", "-"),
                "구간": (
                    f"{issue.get('start_seconds', '-')}–"
                    f"{issue.get('end_seconds', '-')}초"
                ),
                "실패 근거": issue.get("evidence_ko", "-"),
                "권장 처리": issue.get("recommended_workflow", "-"),
                "수정 프롬프트": issue.get("retake_prompt_en", "-"),
            }
            for issue in issues
        ],
        width="stretch",
        hide_index=True,
    )

def render_job_video(
    job: dict[str, Any],
    settings: dict[str, Any],
    *,
    title: str,
) -> None:
    status = job.get("status") or {}
    status_name = str(status.get("status") or "unknown")
    st.markdown(f"**{title}**")
    st.caption(
        f"{job.get('job_id', '-')} · {status_label(status_name)} · "
        f"seed {((job.get('request') or {}).get('seed', '-'))}"
    )
    source, filename = video_source_for_job(job, settings)
    if source:
        st.video(source)
        if source.startswith(("http://", "https://")):
            st.link_button("영상 열기 · 다운로드", source, width="stretch")
        else:
            local_path = Path(source)
            if local_path.is_file():
                st.download_button(
                    "영상 다운로드",
                    data=local_path.read_bytes(),
                    file_name=filename or local_path.name,
                    mime="video/mp4",
                    key=f"download_{job.get('job_id', local_path.name)}",
                    use_container_width=True,
                )
        st.caption(filename)
    else:
        st.warning("표시 가능한 영상 출력 경로가 없습니다.")
    render_job_failure_panel(job)


def render_retake_changes(
    original: dict[str, Any],
    retake: dict[str, Any],
) -> None:
    request = retake.get("request") or {}
    manifest = retake.get("manifest") or {}
    source_report_path = request.get("source_review_report") or manifest.get(
        "source_review_report"
    )
    report = (
        read_json(Path(str(source_report_path)), {}) or {}
        if source_report_path
        else {}
    )
    cycle = request.get("modify_cycle", manifest.get("modify_cycle", "-"))
    original_seed = (original.get("request") or {}).get(
        "seed", (original.get("manifest") or {}).get("seed", "-")
    )
    retake_seed = request.get("seed", manifest.get("seed", "-"))

    st.markdown(f"**Retake cycle {cycle} 수정 내역**")
    cols = st.columns(3)
    cols[0].metric("원본 Seed", str(original_seed))
    cols[1].metric("Retake Seed", str(retake_seed))
    cols[2].metric("검수 이슈", str(len(report.get("issues") or [])))
    st.caption(
        f"원본: {lineage_root_id(retake)} · 직전 작업: "
        f"{request.get('parent_job_id') or manifest.get('parent_job_id') or '-'}"
    )
    retake_start = request.get(
        "retake_start_seconds", manifest.get("retake_start_seconds")
    )
    retake_end = request.get(
        "retake_end_seconds", manifest.get("retake_end_seconds")
    )
    correction_mode = str(
        request.get("correction_mode")
        or manifest.get("correction_mode")
        or "partial_retake"
    )
    if correction_mode == "full_regeneration":
        st.success("수정 방식: 전체 재생성 · 최초 이미지와 교정 프롬프트로 전 구간 재생성")
    elif retake_start is not None and retake_end is not None:
        st.success(
            f"부분 Retake 적용 구간: {float(retake_start):.3f}–"
            f"{float(retake_end):.3f}초 · 나머지 구간은 원본 유지"
        )
    primary_issue = request.get(
        "retake_primary_issue", manifest.get("retake_primary_issue")
    ) or {}
    if primary_issue:
        st.warning(
            "대표 수정 원인: "
            + str(primary_issue.get("evidence_ko") or primary_issue.get("type") or "-")
        )

    summary = str(report.get("summary_ko") or "").strip()
    if summary:
        st.info(f"검수 요약: {summary}")

    rows: list[dict[str, Any]] = []
    for issue in report.get("issues") or []:
        rows.append(
            {
                "심각도": issue.get("severity", "-"),
                "유형": issue.get("type", "-"),
                "구간": (
                    f"{issue.get('start_seconds', '-')}–"
                    f"{issue.get('end_seconds', '-')}초"
                ),
                "실패 근거": issue.get("evidence_ko", "-"),
                "수정 강도": issue.get("retake_strength", "-"),
                "처리": issue.get("recommended_workflow", "-"),
            }
        )
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)

    corrections = str(
        request.get("retake_corrections")
        or manifest.get("retake_corrections")
        or ""
    ).strip()
    with st.expander("실제 적용된 Retake 수정 프롬프트", expanded=True):
        st.code(corrections or "기록된 수정 프롬프트가 없습니다.", language=None)



def render_manual_correction_panel(
    *,
    original: dict[str, Any],
    lineage: list[dict[str, Any]],
    settings: dict[str, Any],
    panel_key: str,
) -> None:
    st.subheader("사용자 재수정")
    st.caption(
        "자동 수정 한도와 관계없이 최종 수정본을 선택해 다시 부분 수정하거나, "
        "문제가 넓으면 전체 재생성을 새 배치로 등록할 수 있습니다."
    )
    versions = sorted(
        [
            job
            for job in lineage
            if job_type_of(job) in {"generate", "modify"}
            and (job.get("status") or {}).get("status") == "completed"
        ],
        key=lambda job: (
            int(
                (job.get("request") or {}).get(
                    "modify_cycle",
                    (job.get("manifest") or {}).get("modify_cycle", 0),
                )
                or 0
            ),
            str((job.get("request") or {}).get("created_at") or ""),
        ),
    )
    if not versions:
        st.info("재수정할 완료 영상이 없습니다.")
        return

    source_id = st.selectbox(
        "재수정 기준 영상",
        [str(job.get("job_id") or "") for job in versions],
        index=len(versions) - 1,
        format_func=lambda job_id: next(
            (
                (
                    f"cycle {(job.get('request') or {}).get('modify_cycle', 0)} · "
                    f"{(job.get('request') or {}).get('workflow_kind_label', '최초 생성')} · "
                    f"{job_id}"
                )
                for job in versions
                if job.get("job_id") == job_id
            ),
            job_id,
        ),
        key=f"manual_source_{panel_key}",
    )
    source_job = next(job for job in versions if job.get("job_id") == source_id)
    source_review = load_source_review(source_job)
    recommended_mode = (
        correction_policy.recommend_correction_mode(source_review)
        if source_review
        else "partial_retake"
    )
    recommendation_label = (
        "전체 재생성"
        if recommended_mode == "full_regeneration"
        else "부분 수정"
    )
    if source_review:
        coverage = correction_policy.covered_seconds(source_review)
        duration = float(source_review.get("duration_seconds") or 0.0)
        ratio = coverage / duration if duration else 0.0
        st.info(
            f"자동 판단: {recommendation_label} · 주요 이슈 "
            f"{sum(str(item.get('severity')) in {'blocking', 'major'} for item in correction_policy.retake_issues(source_review))}개 · "
            f"영향 구간 {coverage:.2f}초 ({ratio:.0%})"
        )

    duration = float(source_review.get("duration_seconds") or 0.0)
    if duration <= 0:
        root_request = original.get("request") or {}
        duration = float(root_request.get("target_total_seconds") or 0.0)
    if duration <= 0:
        duration = sum(
            float(item.get("seconds") or 0.0)
            for item in (original.get("request") or {}).get("segments") or []
        )
    duration = max(0.1, duration)

    try:
        suggested_start, suggested_end, _, _ = (
            correction_policy.select_retake_window(source_review)
        )
    except ValueError:
        suggested_start, suggested_end = 0.0, min(duration, 3.0)

    suggested_prompt = correction_policy.correction_text(
        source_review,
        start_seconds=suggested_start,
        end_seconds=suggested_end,
    )
    if not suggested_prompt:
        suggested_prompt = "Describe the exact visual or motion correction to apply."

    with st.form(f"manual_correction_form_{panel_key}_{source_id}"):
        mode_choice = st.selectbox(
            "수정 방식",
            ["auto", "partial_retake", "full_regeneration"],
            format_func=lambda value: {
                "auto": f"자동 판단 ({recommendation_label})",
                "partial_retake": "부분 수정",
                "full_regeneration": "전체 재생성",
            }[value],
        )
        resolved_mode = (
            recommended_mode if mode_choice == "auto" else mode_choice
        )
        if resolved_mode == "partial_retake":
            time_cols = st.columns(2)
            start_seconds = time_cols[0].number_input(
                "수정 시작(초)",
                min_value=0.0,
                max_value=float(duration),
                value=float(min(suggested_start, duration)),
                step=0.25,
            )
            end_seconds = time_cols[1].number_input(
                "수정 종료(초)",
                min_value=0.0,
                max_value=float(duration),
                value=float(min(max(suggested_end, 0.25), duration)),
                step=0.25,
            )
            uploaded_video = st.file_uploader(
                "선택한 기준 영상을 다시 업로드",
                type=["mp4", "webm", "mov", "mkv", "avi"],
                help="UI에 표시된 최종 수정본을 내려받은 뒤 그대로 올릴 수 있습니다.",
            )
        else:
            start_seconds = 0.0
            end_seconds = duration
            uploaded_video = None
            st.warning(
                "전체 재생성은 업로드 영상의 일부를 고치는 대신, 최초 이미지와 "
                "프롬프트에 교정사항을 반영해 영상을 처음부터 다시 생성합니다."
            )

        correction_prompt = st.text_area(
            "재수정 프롬프트",
            value=suggested_prompt,
            height=180,
            help="구체적인 등장 시점, 움직임, 금지 요소를 영어로 작성하면 안정적입니다.",
        )
        submitted = st.form_submit_button(
            "새 재수정 작업 등록",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        try:
            uploaded_content = (
                uploaded_video.getvalue() if uploaded_video is not None else None
            )
            uploaded_name = (
                uploaded_video.name if uploaded_video is not None else None
            )
            job_id, batch_id = queue_manual_correction(
                original=original,
                parent=source_job,
                settings=settings,
                correction_mode=resolved_mode,
                correction_prompt=correction_prompt,
                start_seconds=float(start_seconds),
                end_seconds=float(end_seconds),
                source_duration_seconds=duration,
                uploaded_video_name=uploaded_name,
                uploaded_video_content=uploaded_content,
            )
            st.success(
                f"사용자 재수정 등록 완료 · {job_id} · 새 배치 {batch_id}"
            )
            st.info("큐 · 진행사항 화면에서 생성 및 자동 검수 상태를 확인하세요.")
        except Exception as exc:
            st.exception(exc)

def render_job_failure_panel(job: dict[str, Any]) -> None:
    status = job.get("status") or {}
    manifest = job.get("manifest") or {}
    status_name = str(status.get("status") or manifest.get("status") or "")
    error = status.get("error") or manifest.get("error")
    if status_name != "failed" and not error:
        return

    stage = (
        status.get("failure_stage")
        or manifest.get("failure_stage")
        or status.get("stage")
        or "단계 미기록"
    )
    message = redact_sensitive_text(error or status.get("message") or "원인 미기록", 3000)
    st.error(f"실패 단계: {stage} · {message}")

    details = [
        f"작업 ID: {job.get('job_id', '-')}",
        f"실패 단계: {stage}",
        f"상태: {status_name or '-'}",
        f"오류: {message}",
    ]
    error_log = Path(str(job.get("job_dir") or "")) / "error.log"
    if error_log.is_file():
        try:
            log_text = error_log.read_text(encoding="utf-8")[-12000:]
            details.extend(["", "traceback:", redact_sensitive_text(log_text)])
        except OSError as exc:
            details.append(f"오류 로그 읽기 실패: {exc}")
    with st.expander("실패 상세 · 단계/원인/traceback"):
        st.code("\n".join(details), language=None)


def batch_failure_payload(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        label: batch.get(field)
        for field, label in BATCH_FAILURE_FIELDS.items()
        if batch.get(field)
    }


REVIEW_OUTCOME_STATUSES = {
    "manual_review_required",
    "modification_limit_reached",
    "review_complete_needs_modification",
}


def batch_is_review_outcome(batch: dict[str, Any]) -> bool:
    return str(batch.get("status") or "") in REVIEW_OUTCOME_STATUSES


def batch_has_pipeline_failure(batch: dict[str, Any]) -> bool:
    if batch_failure_payload(batch):
        return True
    status_name = str(batch.get("status") or "").casefold()
    return any(
        token in status_name
        for token in ("failed", "error", "stopped")
    )


def batch_needs_attention(batch: dict[str, Any]) -> bool:
    return batch_is_review_outcome(batch) or batch_has_pipeline_failure(batch)


def render_batch_failure_panel(batch: dict[str, Any]) -> None:
    failures = batch_failure_payload(batch)
    if not batch_needs_attention(batch):
        return

    stage = batch.get("stage") or "단계 미기록"
    message = redact_sensitive_text(batch.get("message") or "원인 미기록", 3000)
    if batch_is_review_outcome(batch):
        st.warning(f"검수 결과 확인 필요: {stage} · {message}")
    else:
        st.error(f"파이프라인 실패 단계: {stage} · {message}")
    with st.expander("배치 실패 상세", expanded=True):
        st.code(
            redact_sensitive_text(
                json.dumps(
                    failures or {"상태": batch.get("status")},
                    ensure_ascii=False,
                    indent=2,
                )
            ),
            language="json",
        )


def require_access_key() -> None:
    access_key = os.environ.get("VIDEO_UI_ACCESS_KEY", "").strip()
    if not access_key:
        return
    if st.session_state.get("ltx_video_ui_authenticated") is True:
        return

    st.title("LTX Director 영상 생성기")
    st.caption("외부 접속 보호가 활성화되어 있습니다.")
    with st.form("access_key_form", clear_on_submit=False):
        entered = st.text_input("접속 키", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("접속", type="primary", use_container_width=True)
    if submitted:
        if hmac.compare_digest(entered.strip(), access_key):
            st.session_state["ltx_video_ui_authenticated"] = True
            st.rerun()
        else:
            st.error("접속 키가 올바르지 않습니다.")
    st.stop()


def render_sidebar() -> dict[str, Any]:
    access_key = os.environ.get("VIDEO_UI_ACCESS_KEY", "").strip()
    with st.sidebar:
        if access_key:
            st.success("외부 접속 보호 활성화")
            if st.button("로그아웃", use_container_width=True):
                st.session_state.pop("ltx_video_ui_authenticated", None)
                st.rerun()
            st.divider()

        page = st.radio(
            "페이지",
            ["새 영상 생성", "큐 · 진행사항", "배치 · 자동화", "결과물"],
            index=0,
        )
        st.divider()
        st.subheader("ComfyUI 연결")
        comfy_url = st.text_input(
            "내부 API URL",
            value=DEFAULT_COMFY_URL,
            help="같은 DGX Spark 내부 API 호출 주소입니다.",
        )
        comfy_public_url = st.text_input(
            "외부 편집 URL",
            value=DEFAULT_COMFY_PUBLIC_URL,
            help="외부 브라우저에서 ComfyUI 편집 화면을 여는 주소입니다.",
        )
        if comfy_public_url.strip():
            st.link_button(
                "ComfyUI 편집 화면 열기",
                comfy_public_url.strip(),
                use_container_width=True,
            )

        comfy_start_script_text = st.text_input(
            "ComfyUI 시작 스크립트",
            value=str(DEFAULT_COMFY_START_SCRIPT),
        )
        comfy_start_script = Path(comfy_start_script_text).expanduser()
        comfy_tmux_session = st.text_input("tmux 세션", value=DEFAULT_COMFY_TMUX_SESSION)
        auto_start_comfy = st.checkbox(
            "작업 시작 시 ComfyUI가 꺼져 있으면 시작",
            value=True,
            help="worker가 기존 ai-start-comfy 스크립트를 호출합니다.",
        )

        status_col, start_col = st.columns(2)
        with status_col:
            if st.button("API·tmux 확인", use_container_width=True):
                try:
                    stats = ComfyClient(comfy_url).health()
                    st.success("ComfyUI API 정상")
                    st.caption(
                        f"tmux `{comfy_tmux_session}`: "
                        + ("실행 중" if tmux_session_exists(comfy_tmux_session) else "없음")
                    )
                    st.json(stats, expanded=False)
                except Exception as exc:
                    st.error(f"API 연결 실패: {exc}")
        with start_col:
            if st.button("tmux 시작", use_container_width=True):
                try:
                    st.code(run_comfy_start_script(comfy_start_script), language=None)
                except Exception as exc:
                    st.error(str(exc))

        st.subheader("자동 파이프라인")
        automation_settings = load_automation_settings(ENGINE_ROOT)
        st.caption(
            "AI 검수 "
            + ("ON" if automation_settings["auto_review"] else "OFF")
            + " · 자동 수정 "
            + ("ON" if automation_settings["auto_modify"] else "OFF")
            + " · 최대 수정 "
            + f"{automation_settings['max_modify_cycles']}회"
        )

        st.subheader("API 워크플로 선택")
        workflow_dir = DEFAULT_WORKFLOW_DIR
        api_workflows = discover_api_workflows(workflow_dir)

        if not api_workflows:
            st.error(
                "워크플로 폴더에서 파일명에 API가 포함된 JSON을 찾지 못했습니다."
            )
            st.caption(f"검색 폴더: `{workflow_dir}`")
            template_path = None
            workflow_kind = "other"
        else:
            template_path = st.selectbox(
                "워크플로",
                options=api_workflows,
                index=default_workflow_index(api_workflows),
                format_func=lambda path: workflow_display_name(path, workflow_dir),
                help=(
                    "워크플로 폴더와 하위 폴더에서 파일명에 API가 포함된 "
                    "JSON을 대소문자 구분 없이 자동 검색합니다."
                ),
            )
            workflow_kind = classify_workflow(template_path)
            st.caption(
                f"검색 폴더: `{workflow_dir}` · 발견 {len(api_workflows)}개 · "
                f"선택 유형: **{WORKFLOW_KIND_LABELS[workflow_kind]}**"
            )
            if workflow_kind in {"modify", "check"}:
                st.warning(
                    "현재 페이지는 첫 영상 생성용입니다. "
                    "(MD)와 (CH) 워크플로는 목록에는 표시되지만 "
                    "수정·검수 페이지가 추가되기 전에는 큐 등록할 수 없습니다."
                )
            elif workflow_kind == "other":
                st.info(
                    "접두사가 없는 기존 API 워크플로입니다. "
                    "생성 구조가 호환되면 현재 페이지에서 사용할 수 있습니다."
                )

    return {
        "page": page,
        "comfy_url": comfy_url,
        "comfy_public_url": comfy_public_url,
        "comfy_start_script": comfy_start_script,
        "comfy_tmux_session": comfy_tmux_session,
        "auto_start_comfy": auto_start_comfy,
        "template_path": template_path,
        "workflow_dir": workflow_dir,
        "workflow_kind": workflow_kind,
        "automation_settings": automation_settings,
    }


def render_generation_page(settings: dict[str, Any]) -> None:
    st.title("LTX Director 영상 생성기 · 생성")
    st.caption("이미지와 프롬프트를 등록하면 작업 큐에 저장되고, worker가 순서대로 실행합니다.")

    selected_template = settings.get("template_path")
    selected_kind = str(settings.get("workflow_kind") or "other")
    if selected_template is not None:
        st.info(
            f"선택 워크플로: **{selected_template.name}** · "
            f"{WORKFLOW_KIND_LABELS.get(selected_kind, selected_kind)}"
        )

    uploaded_files = st.file_uploader(
        "시작 이미지들을 업로드하세요",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        help="업로드 순서는 아래 정렬 번호로 다시 지정할 수 있습니다.",
    )

    st.subheader("전체 설정")
    col_a, col_b, col_c, col_d = st.columns([1.2, 0.8, 1.2, 1.5])
    with col_a:
        job_name = st.text_input("작업 이름", value="LTX_scene")
    with col_b:
        fps = int(st.number_input("FPS", min_value=1, max_value=60, value=24, step=1))
    with col_c:
        seed_input = st.text_input(
            "시드 (-1은 자동 생성)",
            value=str(DEFAULT_SEED),
            help=(
                f"기본 고정 시드: {DEFAULT_SEED} · "
                f"허용 범위: {MIN_SEED} ~ {MAX_SEED}"
            ),
        )
    with col_d:
        resolution_options = list(RESOLUTION_PRESETS)
        resolution_label = st.selectbox(
            "첫 생성 출력 해상도 · 16:9 계열 · 32배수",
            options=resolution_options,
            index=resolution_options.index(DEFAULT_RESOLUTION_LABEL),
        )
    width, height = RESOLUTION_PRESETS[resolution_label]

    global_prompt = st.text_area(
        "Global prompt",
        value=DEFAULT_GLOBAL_PROMPT,
        height=90,
    )

    duration_mode = st.radio(
        "총 길이 계산 방식",
        options=["각 구간 시간의 합계", "목표 총 길이에 맞춰 비율 조정"],
        horizontal=True,
    )
    target_total_seconds: float | None = None
    if duration_mode == "목표 총 길이에 맞춰 비율 조정":
        target_total_seconds = float(
            st.number_input(
                "목표 총 길이(초)", min_value=0.1, value=20.0, step=0.1, format="%.3f"
            )
        )

    segment_rows: list[dict[str, Any]] = []
    if uploaded_files:
        st.subheader("이미지 구간 설정")
        for index, uploaded in enumerate(uploaded_files, start=1):
            content = uploaded.getvalue()
            identity = hashlib.sha256(content).hexdigest()[:16]
            with st.container(border=True):
                image_col, input_col = st.columns([1, 3])
                with image_col:
                    st.image(content, caption=uploaded.name, use_container_width=True)
                with input_col:
                    top_1, top_2, top_3 = st.columns([1, 1, 1])
                    with top_1:
                        enabled = st.checkbox("사용", value=True, key=f"enabled_{identity}")
                    with top_2:
                        order = int(
                            st.number_input(
                                "순서",
                                min_value=1,
                                max_value=max(1, len(uploaded_files)),
                                value=index,
                                step=1,
                                key=f"order_{identity}",
                            )
                        )
                    with top_3:
                        seconds = float(
                            st.number_input(
                                "구간 시간(초)",
                                min_value=0.1,
                                value=5.0,
                                step=0.1,
                                format="%.3f",
                                key=f"seconds_{identity}",
                            )
                        )
                    prompt = st.text_area(
                        "이 이미지 구간의 MSR 프롬프트",
                        height=180,
                        key=f"prompt_{identity}",
                        placeholder="Visible characters in this clip:\n- ...\n\nAction flow:\n...",
                    )
                    segment_rows.append(
                        {
                            "enabled": enabled,
                            "order": order,
                            "seconds": seconds,
                            "prompt": prompt,
                            "uploaded": uploaded,
                            "content": content,
                            "identity": identity,
                        }
                    )

    selected_rows = [row for row in segment_rows if row["enabled"]]
    preview = []
    if selected_rows:
        placeholder_specs = [
            SegmentSpec(
                image_name=row["uploaded"].name,
                image_subfolder="preview",
                prompt=row["prompt"],
                requested_seconds=row["seconds"],
                order=row["order"],
            )
            for row in selected_rows
        ]
        try:
            preview = preview_segments(
                placeholder_specs,
                fps=fps,
                target_total_seconds=target_total_seconds,
            )
            st.subheader("생성 예정 타임라인")
            st.dataframe(
                [
                    {
                        "순서": item.order,
                        "이미지": item.image_name,
                        "요청 시간(초)": round(item.requested_seconds, 3),
                        "실제 프레임": item.frame_count,
                        "실제 시간(초)": round(item.actual_seconds, 3),
                        "시작 프레임": item.start_frame,
                    }
                    for item in preview
                ],
                use_container_width=True,
                hide_index=True,
            )
            total_frames = sum(item.frame_count for item in preview)
            metric_1, metric_2, metric_3 = st.columns(3)
            metric_1.metric("최종 영상 길이", f"{total_frames / fps:.3f}초")
            metric_2.metric("총 프레임", f"{total_frames}")
            metric_3.metric("출력 해상도", f"{width} × {height}")
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    selected_workflow_kind = str(settings.get("workflow_kind") or "other")
    workflow_ready = (
        settings.get("template_path") is not None
        and selected_workflow_kind not in {"modify", "check"}
    )
    submit = st.button(
        "작업 큐에 등록",
        type="primary",
        use_container_width=True,
        disabled=not bool(selected_rows) or not workflow_ready,
    )

    if not submit:
        return

    try:
        template_path = settings["template_path"]
        workflow_kind = str(settings.get("workflow_kind") or "other")
        if template_path is None:
            raise FileNotFoundError("선택 가능한 API 워크플로가 없습니다.")
        if workflow_kind in {"modify", "check"}:
            raise ValueError(
                "현재 새 영상 생성 페이지에서는 (CR) 생성 워크플로 또는 "
                "접두사가 없는 호환 API 워크플로를 선택해야 합니다."
            )
        if not template_path.is_file():
            raise FileNotFoundError(f"워크플로 템플릿을 찾을 수 없습니다: {template_path}")
        load_template(template_path)
        if not selected_rows:
            raise ValueError("사용할 이미지를 한 장 이상 선택하세요.")
        blank_prompts = [row["uploaded"].name for row in selected_rows if not row["prompt"].strip()]
        if blank_prompts:
            raise ValueError("프롬프트가 비어 있는 이미지: " + ", ".join(blank_prompts))

        seed = resolve_seed(parse_seed_input(seed_input))
        automation_settings = load_automation_settings(ENGINE_ROOT)
        batch = get_or_create_open_batch(ENGINE_ROOT, automation_settings)
        batch_id = str(batch["batch_id"])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_token = sanitize_token(job_name, fallback="LTX_scene")
        job_id = f"{timestamp}_{job_token}_{secrets.token_hex(2)}"
        job_dir = JOBS_ROOT / job_id
        source_dir = job_dir / "source_images"
        source_dir.mkdir(parents=True, exist_ok=False)

        workflow_snapshot = job_dir / "selected_workflow_api.json"
        shutil.copy2(template_path, workflow_snapshot)

        stored_segments: list[dict[str, Any]] = []
        for index, row in enumerate(
            sorted(selected_rows, key=lambda item: (item["order"], item["uploaded"].name)),
            start=1,
        ):
            uploaded = row["uploaded"]
            content = row["content"]
            stored_name = safe_uploaded_name(uploaded.name, content, index)
            source_path = source_dir / stored_name
            source_path.write_bytes(content)
            stored_segments.append(
                {
                    "original_name": uploaded.name,
                    "stored_name": stored_name,
                    "source_path": str(source_path),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "prompt": row["prompt"].strip(),
                    "seconds": float(row["seconds"]),
                    "order": int(row["order"]),
                }
            )

        filename_prefix = f"video/jobs/{job_id}/{job_token}"
        request = {
            "schema_version": 2,
            "job_type": "generate",
            "pipeline_stage": "initial_generation",
            "job_id": job_id,
            "batch_id": batch_id,
            "job_dir": str(job_dir),
            "created_at": now_iso(),
            "job_name": job_name,
            "template_path": str(workflow_snapshot),
            "workflow_source_path": str(template_path),
            "workflow_filename": template_path.name,
            "workflow_kind": workflow_kind,
            "workflow_kind_label": WORKFLOW_KIND_LABELS[workflow_kind],
            "comfy_url": settings["comfy_url"],
            "comfy_public_url": settings["comfy_public_url"],
            "comfy_start_script": str(settings["comfy_start_script"]),
            "comfy_start_timeout": DEFAULT_COMFY_START_TIMEOUT,
            "auto_start_comfy": bool(settings["auto_start_comfy"]),
            "fps": fps,
            "seed": seed,
            "resolution": {"width": width, "height": height, "label": resolution_label},
            "global_prompt": global_prompt.strip(),
            "duration_mode": duration_mode,
            "target_total_seconds": target_total_seconds,
            "filename_prefix": filename_prefix,
            "segments": stored_segments,
            "parent_job_id": None,
            "attempt": 0,
            "automation": dict(batch.get("automation") or automation_settings),
        }
        manifest = {
            "schema_version": 2,
            "job_id": job_id,
            "batch_id": batch_id,
            "job_type": "generate",
            "pipeline_stage": "initial_generation",
            "created_at": request["created_at"],
            "status": "queued",
            "workflow_source_path": str(template_path),
            "workflow_filename": template_path.name,
            "workflow_kind": workflow_kind,
            "workflow_kind_label": WORKFLOW_KIND_LABELS[workflow_kind],
            "seed": seed,
            "resolution": request["resolution"],
            "fps": fps,
            "segments": stored_segments,
            "outputs": [],
        }
        atomic_write_json(job_dir / "request.json", request)
        atomic_write_json(job_dir / "manifest.json", manifest)
        attach_job_to_batch(
            ENGINE_ROOT,
            batch_id=batch_id,
            job_id=job_id,
            job_type="generate",
        )
        update_status(
            job_dir,
            "queued",
            stage="worker 대기",
            message="작업 큐에 등록되었습니다.",
            progress=0.0,
            created_at=request["created_at"],
        )

        st.success(f"작업 큐 등록 완료 · {job_id}")
        st.write(
            f"배치: `{batch_id}` · 워크플로: `{template_path.name}` · "
            f"시드: `{seed}` · 해상도: `{width}x{height}`"
        )
        st.info("왼쪽의 ‘큐 · 진행사항’ 페이지에서 처리 상태를 확인할 수 있습니다.")
    except Exception as exc:
        st.exception(exc)


def render_job_card(job: dict[str, Any], allow_cancel: bool = True) -> None:
    status = job["status"] or {}
    request = job["request"] or {}
    manifest = job["manifest"] or {}
    status_name = str(status.get("status") or manifest.get("status") or "unknown")
    stage = status.get("stage") or "-"
    message = status.get("message") or ""
    resolution = request.get("resolution") or manifest.get("resolution") or {}
    seed = request.get("seed", manifest.get("seed", "-"))

    with st.container(border=True):
        head_1, head_2, head_3 = st.columns([2.2, 1, 1])
        head_1.markdown(f"**{job['job_id']}**")
        head_2.markdown(f"**{status_label(status_name)}**")
        head_3.caption(status.get("updated_at") or manifest.get("updated_at") or "")

        st.write(stage + (f" · {message}" if message else ""))
        workflow_filename = (
            request.get("workflow_filename")
            or manifest.get("workflow_filename")
            or Path(str(request.get("template_path") or "")).name
        )
        batch_id = request.get("batch_id") or manifest.get("batch_id")
        if batch_id:
            st.caption(f"배치: `{batch_id}`")

        if workflow_filename:
            workflow_kind_label = (
                request.get("workflow_kind_label")
                or manifest.get("workflow_kind_label")
                or "API"
            )
            st.caption(f"워크플로: `{workflow_filename}` · {workflow_kind_label}")
        info_1, info_2, info_3, info_4 = st.columns(4)
        info_1.metric("Seed", str(seed))
        info_2.metric(
            "해상도",
            f"{resolution.get('width', '-')}×{resolution.get('height', '-')}",
        )
        info_3.metric("경과", format_elapsed(status.get("elapsed_seconds")))
        queue_pos = status.get("queue_position")
        info_4.metric("큐 위치", "실행 중" if queue_pos == 0 else (queue_pos or "-"))

        progress = status.get("progress")
        if isinstance(progress, (int, float)) and status_name not in {
            "comfy_queued", "submitted", "running"
        }:
            st.progress(max(0.0, min(1.0, float(progress))), text=status_label(status_name))
        elif status_name in {"comfy_queued", "submitted", "running"}:
            st.caption("ComfyUI 실행 구간은 현재 단계·큐 위치·경과 시간으로 표시됩니다.")

        render_job_failure_panel(job)
        if allow_cancel and status_name == "queued":
            if st.button("대기 작업 취소", key=f"cancel_{job['job_id']}"):
                update_status(
                    Path(job["job_dir"]),
                    "cancelled",
                    stage="취소",
                    message="사용자가 큐 대기 중 취소했습니다.",
                    cancelled_at=now_iso(),
                )
                current_manifest = read_json(Path(job["job_dir"]) / "manifest.json", {}) or {}
                current_manifest.update({"status": "cancelled", "cancelled_at": now_iso()})
                atomic_write_json(Path(job["job_dir"]) / "manifest.json", current_manifest)
                st.rerun()


def render_queue_contents() -> None:
    jobs = list_jobs(JOBS_ROOT, limit=100)
    worker = read_json(WORKER_STATUS_PATH, {}) or {}
    online = worker_is_online(worker)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Worker", "정상" if online else "오프라인")
    m2.metric("우리 큐 대기", sum(1 for job in jobs if job["status"].get("status") == "queued"))
    m3.metric(
        "처리 중",
        sum(1 for job in jobs if job["status"].get("status") in ACTIVE_STATUSES),
    )
    m4.metric("완료", sum(1 for job in jobs if job["status"].get("status") == "completed"))
    current_batch = worker.get("current_batch")
    if current_batch:
        st.caption(f"현재 생성 배치: `{current_batch}`")
    if worker.get("current_job"):
        st.caption(f"Worker 현재 작업: `{worker['current_job']}`")
    if not online:
        st.warning("worker heartbeat가 확인되지 않습니다. `ltx-video-worker-status`를 확인하세요.")

    active_jobs = [
        job
        for job in jobs
        if job["status"].get("status") not in TERMINAL_STATUSES
    ]
    if not active_jobs:
        st.info("현재 대기하거나 실행 중인 작업이 없습니다.")
    else:
        for job in reversed(active_jobs):
            render_job_card(job)

    with st.expander("최근 종료 작업"):
        terminal_jobs = [
            job for job in jobs if job["status"].get("status") in TERMINAL_STATUSES
        ][:20]
        for job in terminal_jobs:
            render_job_card(job, allow_cancel=False)


def render_queue_page() -> None:
    st.title("작업 큐 · 진행사항")
    st.caption("UI는 작업 등록만 수행하고, 별도 worker가 한 건씩 순차 처리합니다.")
    if hasattr(st, "fragment"):
        @st.fragment(run_every="3s")
        def live_panel() -> None:
            render_queue_contents()
        live_panel()
    else:
        if st.button("새로고침"):
            st.rerun()
        render_queue_contents()


def render_batch_automation_page() -> None:
    st.title("배치 · 자동화")
    st.caption(
        "여러 생성 작업을 하나의 배치로 묶고, 생성 큐가 완전히 끝난 뒤 "
        "검수·수정 단계로 전환하기 위한 설정입니다."
    )

    current = load_automation_settings(ENGINE_ROOT)
    with st.container(border=True):
        st.subheader("자동 파이프라인 설정")
        auto_review = st.toggle(
            "AI 검수 활성화",
            value=bool(current["auto_review"]),
            help=(
                "ON이면 생성 배치가 끝난 뒤 원본 영상을 로컬 검수 경로로 복사하고 "
                "Qwen3-Omni 직접 영상 검수 단계로 이어집니다."
            ),
        )
        auto_modify = st.toggle(
            "AI 자동 수정 활성화",
            value=bool(current["auto_modify"]),
            disabled=not auto_review,
            help="AI가 수정 필요 판정을 내리면 Retake 작업을 자동 생성합니다.",
        )
        auto_recheck = st.toggle(
            "수정 후 AI 재검수",
            value=bool(current["auto_recheck"]),
            disabled=not auto_review or not auto_modify,
        )
        max_cycles = int(
            st.selectbox(
                "최대 자동 수정 횟수",
                options=[0, 1, 2],
                index=[0, 1, 2].index(int(current["max_modify_cycles"])),
                disabled=not auto_review or not auto_modify,
            )
        )
        idle_grace = int(
            st.number_input(
                "생성 큐 종료 안정 대기(초)",
                min_value=3,
                max_value=300,
                value=int(current["batch_idle_grace_seconds"]),
                step=1,
                help=(
                    "자체 큐와 ComfyUI 큐가 모두 빈 뒤 이 시간 동안 새 작업이 없으면 "
                    "현재 생성 배치를 닫습니다."
                ),
            )
        )

        if st.button("자동화 설정 저장", type="primary", use_container_width=True):
            saved = save_automation_settings(
                ENGINE_ROOT,
                {
                    "auto_review": auto_review,
                    "auto_modify": auto_modify,
                    "auto_recheck": auto_recheck,
                    "max_modify_cycles": max_cycles,
                    "batch_idle_grace_seconds": idle_grace,
                },
            )
            st.success("자동화 설정을 저장했습니다.")
            st.json(saved, expanded=False)

    st.subheader("최근 배치")

    def render_live_batch_list() -> None:
        worker = read_json(WORKER_STATUS_PATH, {}) or {}
        engine_state = read_json(ENGINE_STATE_PATH, {}) or {}
        status_cols = st.columns(5)
        status_cols[0].metric("Worker", "정상" if worker_is_online(worker) else "오프라인")
        status_cols[1].metric("실행 엔진", engine_state.get("active_engine") or "-")
        status_cols[2].metric("현재 배치", worker.get("current_batch") or "-")
        status_cols[3].metric("배치 단계", worker.get("batch_stage") or "-")
        status_cols[4].metric("배치 상태", worker.get("batch_status") or "-")

        if worker.get("batch_message"):
            st.caption(worker["batch_message"])

        batches = list_batches(ENGINE_ROOT, limit=50)
        if not batches:
            st.info("아직 생성된 배치가 없습니다.")
            return

        for batch in batches:
            with st.container(border=True):
                head_1, head_2, head_3 = st.columns([2, 1, 1])
                head_1.markdown(f"**{batch.get('batch_id', '-')}**")
                head_2.markdown(f"**{batch.get('status', '-')}**")
                head_3.caption(batch.get("updated_at", ""))

                automation = batch.get("automation") or {}
                job_ids = batch.get("job_ids") or []
                generation_ids = batch.get("generation_job_ids") or []
                check_ids = batch.get("check_job_ids") or []
                modify_ids = batch.get("modify_job_ids") or []
                st.write(batch.get("message") or batch.get("stage") or "")
                st.caption(
                    f"생성 {len(generation_ids)}개 · Retake {len(modify_ids)}개 · "
                    f"보조 검수 작업 {len(check_ids)}개 · 전체 {len(job_ids)}개 · "
                    f"AI 검수 {'ON' if automation.get('auto_review') else 'OFF'} · "
                    f"자동 수정 {'ON' if automation.get('auto_modify') else 'OFF'}"
                )
                if batch.get("next_stage"):
                    st.code(f"next_stage={batch['next_stage']}", language=None)
                render_batch_failure_panel(batch)
                with st.expander("배치 작업 ID"):
                    st.code(
                        "\n".join(job_ids) if job_ids else "등록 작업 없음",
                        language=None,
                    )

    if hasattr(st, "fragment"):
        @st.fragment(run_every="3s")
        def live_batch_panel() -> None:
            render_live_batch_list()
        live_batch_panel()
    else:
        if st.button("배치 상태 새로고침"):
            st.rerun()
        render_live_batch_list()


def render_results_page(settings: dict[str, Any]) -> None:
    st.title("결과물 · 원본/Retake 비교")
    st.caption(
        "최초 생성본과 최신 Retake를 같은 계보로 비교하고, "
        "검수 실패 원인과 실제 적용된 수정 내용을 확인합니다."
    )
    st.info(
        "생성 프롬프트에는 한국어 발화 정책이 자동 적용됩니다. "
        "현재 Qwen 검수는 원본의 전체 프레임·시간축을 유지한 MJPEG AVI 동영상과 "
        "WAV 오디오 트랙을 함께 전달하여 영상 흐름과 발화 내용을 판정합니다."
    )

    jobs = list_jobs(JOBS_ROOT, limit=300)
    completed = [
        job
        for job in jobs
        if (job.get("status") or {}).get("status") == "completed"
    ]
    failed = [
        job
        for job in jobs
        if (job.get("status") or {}).get("status") == "failed"
    ]
    batches = list_batches(ENGINE_ROOT, limit=100)
    completed_video_job_ids = {
        str(job.get("job_id") or "")
        for job in completed
        if primary_video_output(job) is not None
    }
    failed_batches = [
        batch
        for batch in batches
        if batch_has_pipeline_failure(batch)
        and not any(
            str(job_id) in completed_video_job_ids
            for job_id in batch.get("job_ids") or []
        )
    ]
    batches_by_id = {
        str(batch.get("batch_id") or ""): batch
        for batch in batches
        if batch.get("batch_id")
    }

    lineages: dict[str, list[dict[str, Any]]] = {}
    for job in completed:
        if job_type_of(job) not in {"generate", "modify"}:
            continue
        lineages.setdefault(lineage_root_id(job), []).append(job)

    compare_tab, job_failure_tab, batch_failure_tab = st.tabs(
        [
            f"원본 ↔ Retake {len(lineages)}",
            f"작업 실패 {len(failed)}",
            f"파이프라인 실패 {len(failed_batches)}",
        ]
    )

    with compare_tab:
        if not lineages:
            st.info("비교 가능한 완료 영상이 없습니다.")
        else:
            root_ids = sorted(lineages, reverse=True)
            selected_root = st.selectbox("원본 계보 선택", root_ids)
            lineage = lineages[selected_root]
            original = next(
                (
                    job
                    for job in lineage
                    if job.get("job_id") == selected_root
                    and job_type_of(job) == "generate"
                ),
                min(
                    lineage,
                    key=lambda job: str(
                        (job.get("request") or {}).get("created_at")
                        or job.get("job_id")
                        or ""
                    ),
                ),
            )
            retakes = sorted(
                [
                    job
                    for job in lineage
                    if job_type_of(job) == "modify"
                ],
                key=lambda job: int(
                    (job.get("request") or {}).get(
                        "modify_cycle",
                        (job.get("manifest") or {}).get("modify_cycle", 0),
                    )
                    or 0
                ),
            )

            related_batches = [
                batches_by_id[batch_id]
                for batch_id in {
                    str((job.get("request") or {}).get("batch_id") or "")
                    for job in lineage
                }
                if batch_id in batches_by_id
            ]
            if related_batches:
                latest_batch = max(
                    related_batches,
                    key=lambda batch: str(batch.get("updated_at") or ""),
                )
                batch_id = str(latest_batch.get("batch_id") or "-")
                batch_status = str(latest_batch.get("status") or "-")
                batch_message = str(latest_batch.get("message") or "")
                if batch_is_review_outcome(latest_batch):
                    st.warning(
                        f"배치 {batch_id} · {batch_status} · {batch_message}"
                    )
                    st.caption(
                        "생성 영상은 정상 완료되었습니다. 아래에서 영상 확인·다운로드와 "
                        "수정 필요 내용을 확인하고 사용자 재수정을 등록할 수 있습니다."
                    )
                elif batch_has_pipeline_failure(latest_batch):
                    st.error(
                        f"배치 {batch_id} · {batch_status} · {batch_message}"
                    )
                    st.caption(
                        "파이프라인 후속 단계는 실패했지만 완료된 생성 영상은 "
                        "아래 결과 계보에서 계속 확인할 수 있습니다."
                    )

            st.subheader("영상 비교")
            original_col, retake_col = st.columns(2)
            with original_col:
                render_job_video(
                    original,
                    settings,
                    title="최초 생성본",
                )
            with retake_col:
                if retakes:
                    latest = retakes[-1]
                    latest_cycle = (latest.get("request") or {}).get(
                        "modify_cycle",
                        (latest.get("manifest") or {}).get("modify_cycle", "-"),
                    )
                    render_job_video(
                        latest,
                        settings,
                        title=f"검수 후 생성본 · cycle {latest_cycle}",
                    )
                else:
                    st.markdown("**검수 후 생성본**")
                    st.info("아직 완료된 Retake가 없습니다.")

            reviewed_job = retakes[-1] if retakes else original
            review = load_source_review(reviewed_job)
            st.subheader("최신 검수 판정")
            if review:
                summary = str(review.get("summary_ko") or "").strip()
                if bool(review.get("accepted")):
                    st.success(f"검수 통과 · {summary or '중대한 문제 없음'}")
                else:
                    st.warning(f"검수 실패/수정 필요 · {summary or '요약 없음'}")
                review_cols = st.columns(3)
                review_cols[0].metric(
                    "판정",
                    "통과" if bool(review.get("accepted")) else "수정 필요",
                )
                review_cols[1].metric(
                    "신뢰도",
                    str(review.get("confidence", "-")),
                )
                review_cols[2].metric(
                    "발견 이슈",
                    str(len(review.get("issues") or [])),
                )
                render_review_issues(review)
                with st.expander("최신 검수 보고서 원문"):
                    st.code(
                        redact_sensitive_text(
                            json.dumps(review, ensure_ascii=False, indent=2)
                        ),
                        language="json",
                    )
            else:
                st.info("이 영상에 연결된 AI 검수 보고서가 아직 없습니다.")

            render_manual_correction_panel(
                original=original,
                lineage=lineage,
                settings=settings,
                panel_key=selected_root,
            )

            if retakes:
                st.subheader("검수로 인해 변경된 내용")
                cycle_options = list(reversed(retakes))
                selected_retake_id = st.selectbox(
                    "Retake cycle 선택",
                    [job.get("job_id") for job in cycle_options],
                    format_func=lambda job_id: (
                        f"cycle "
                        f"{next((job.get('request') or {}).get('modify_cycle') for job in cycle_options if job.get('job_id') == job_id)}"
                        f" · {job_id}"
                    ),
                )
                selected_retake = next(
                    job
                    for job in cycle_options
                    if job.get("job_id") == selected_retake_id
                )
                render_retake_changes(original, selected_retake)

            with st.expander("최초 입력 프롬프트와 구간 정보"):
                original_request = original.get("request") or {}
                st.write(original_request.get("global_prompt", ""))
                rows = [
                    {
                        "순서": segment.get("order"),
                        "이미지": segment.get("original_name"),
                        "시간(초)": segment.get("seconds"),
                        "프롬프트": segment.get("prompt"),
                    }
                    for segment in original_request.get("segments") or []
                ]
                if rows:
                    st.dataframe(rows, width="stretch", hide_index=True)

    with job_failure_tab:
        if not failed:
            st.info("실패한 개별 작업이 없습니다.")
        else:
            for job in failed[:50]:
                render_job_card(job, allow_cancel=False)

    with batch_failure_tab:
        if not failed_batches:
            st.info("기록된 파이프라인 실패가 없습니다.")
        else:
            for batch in failed_batches:
                with st.container(border=True):
                    head_1, head_2, head_3 = st.columns([2, 1, 1])
                    head_1.markdown(f"**{batch.get('batch_id', '-')}**")
                    head_2.markdown(f"**{batch.get('status', '-')}**")
                    head_3.caption(batch.get("updated_at", ""))
                    render_batch_failure_panel(batch)
                    st.caption(
                        f"현재 cycle {batch.get('current_cycle', 0)} · "
                        f"next_stage {batch.get('next_stage', '-')}"
                    )


st.set_page_config(page_title="LTX Video Generator", page_icon="🎬", layout="wide")
require_access_key()
JOBS_ROOT.mkdir(parents=True, exist_ok=True)
settings = render_sidebar()

if settings["page"] == "새 영상 생성":
    render_generation_page(settings)
elif settings["page"] == "큐 · 진행사항":
    render_queue_page()
elif settings["page"] == "배치 · 자동화":
    render_batch_automation_page()
else:
    render_results_page(settings)
