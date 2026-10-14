from __future__ import annotations

"""Command bridge for H3 generation, candidate selection, and model tests."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

import benchmark_jobs
import h3_prompt_projects
import h3_frame_export as h3_frame_export_module
import h3_frame_annotations
import h3_queue
import model_test_analysis
import model_test_assets
import model_test_exports
import model_test_registry
import model_test_reviews
import windows_power_policy
import workflow_adapter
import action_assets
from job_queue import read_json
from remote_render_power import Config as RemoteRenderPowerConfig
from remote_render_power import RemoteRenderPowerManager


HOME = Path.home()
ROOT = Path(
    os.environ.get("VIDEO_ENGINE_ROOT", HOME / "local-ai/video-engine")
).expanduser()
WORKFLOW_DIR = Path(
    os.environ.get(
        "COMFY_WORKFLOW_DIR",
        HOME / "ai-workspace/apps/ComfyUI/user/default/workflows",
    )
).expanduser()


def h3_config(_data: dict[str, Any]) -> dict[str, Any]:
    model_test_registry.ensure_h3_r2v_adapter(ROOT, WORKFLOW_DIR)
    model_test_registry.ensure_h3_i2v_adapter(ROOT, WORKFLOW_DIR)
    return h3_queue.available_adapters(ROOT)


def h3_state(_data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.state(ROOT, compact=True)


def get_windows_power_policy(_data: dict[str, Any]) -> dict[str, Any]:
    return windows_power_policy.get_policy(ROOT)


def set_windows_power_policy(data: dict[str, Any]) -> dict[str, Any]:
    return windows_power_policy.set_policy(ROOT, data.get("auto_hibernate_enabled"))


def control_windows_render_power(data: dict[str, Any]) -> dict[str, Any]:
    action = str(data.get("action") or "").strip().lower()
    if action not in {"wake", "hibernate"} or data.get("confirm") != action:
        raise ValueError("Windows PC 전원 명령 확인 값이 올바르지 않습니다.")
    manager = RemoteRenderPowerManager(RemoteRenderPowerConfig.from_env())
    if action == "wake":
        return manager.manual_wake()

    active_jobs = []
    jobs_root = h3_queue.roots(ROOT)["jobs"]
    if jobs_root.is_dir():
        for directory in jobs_root.iterdir():
            if not directory.is_dir():
                continue
            request = read_json(directory / "request.json", {}) or {}
            status = read_json(directory / "status.json", {}) or {}
            state = str(status.get("status") or "missing")
            remote_lane = (
                request.get("queue_lane") == "windows_candidate"
                or request.get("render_target") == "windows_comfy"
            )
            if remote_lane and state not in h3_queue.TERMINAL:
                active_jobs.append(directory.name)
    if active_jobs:
        raise ValueError(
            f"Windows 후보 큐에 미완료 작업 {len(active_jobs)}개가 있어 최대 절전할 수 없습니다."
        )
    return manager.manual_hibernate()


def h3_candidate_page(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.candidate_page(ROOT, data)


def h3_results_page(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.results_page(ROOT, data)


def h3_clip_versions(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.clip_versions(ROOT, data)


def create_h3_candidate_set(data: dict[str, Any]) -> dict[str, Any]:
    model_test_registry.ensure_h3_r2v_adapter(ROOT, WORKFLOW_DIR)
    model_test_registry.ensure_h3_i2v_adapter(ROOT, WORKFLOW_DIR)
    return h3_queue.enqueue_candidate_set(ROOT, data)


def create_h3_project_test_set(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.create_project_test_set(ROOT, data)


def queue_h3_project_test_set(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.queue_project_test_set(
        ROOT,
        str(data.get("project_test_set_id") or ""),
        data,
    )


def delete_h3_project_test_set(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.delete_project_test_set(
        ROOT,
        str(data.get("project_test_set_id") or ""),
    )


def queue_h3_scene_candidates(data: dict[str, Any]) -> dict[str, Any]:
    model_test_registry.ensure_h3_r2v_adapter(ROOT, WORKFLOW_DIR)
    model_test_registry.ensure_h3_i2v_adapter(ROOT, WORKFLOW_DIR)
    return h3_queue.enqueue_scene_candidate_sets(ROOT, data)


def force_stop_h3_group(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.force_stop_group(
        ROOT,
        str(data.get("group_id") or ""),
        queued_only=bool(data.get("queued_only")),
    )


def select_h3_candidate(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.select_candidate(
        ROOT,
        str(data.get("candidate_set_id") or ""),
        str(data.get("job_id") or ""),
    )


def requeue_h3_candidate_set(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.requeue_candidate_set(
        ROOT,
        str(data.get("candidate_set_id") or ""),
    )


def save_h3_prompt_revision_request(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.save_prompt_revision_request(
        ROOT,
        str(data.get("candidate_set_id") or ""),
        data,
    )


def revise_h3_candidate_set(data: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible alias; this only saves feedback and runs no model."""
    return save_h3_prompt_revision_request(data)


def apply_h3_prompt_revision(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.apply_authored_prompt_revision(
        ROOT,
        str(data.get("prompt_revision_request_id") or ""),
        data,
    )


def restore_h3_candidate_version(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.restore_candidate_version(
        ROOT,
        str(data.get("candidate_set_id") or ""),
    )


def create_h3_resolution_rerender(data: dict[str, Any]) -> dict[str, Any]:
    model_test_registry.ensure_h3_r2v_adapter(ROOT, WORKFLOW_DIR)
    return h3_queue.enqueue_selected_candidate_rerender(
        ROOT,
        str(data.get("candidate_set_id") or ""),
        data,
    )


def create_h3_video_upscale(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.enqueue_selected_candidate_upscale(
        ROOT,
        str(data.get("candidate_set_id") or ""),
        data,
    )


def clear_h3_candidate_selection(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.clear_candidate_selection(
        ROOT,
        str(data.get("candidate_set_id") or ""),
        str(data.get("job_id") or "") or None,
    )


def delete_h3_candidate_set(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.delete_candidate_set(
        ROOT,
        str(data.get("candidate_set_id") or ""),
    )


def h3_video(data: dict[str, Any]) -> dict[str, str]:
    return {
        "path": str(h3_queue.video_path(ROOT, str(data.get("job_id") or "")))
    }


def h3_frame_export(data: dict[str, Any]) -> dict[str, Any]:
    return h3_frame_export_module.export_frames(
        ROOT, str(data.get("job_id") or ""), data.get("interval")
    )


def h3_frame_selection_zip(data: dict[str, Any]) -> dict[str, Any]:
    return h3_frame_export_module.selection_zip(
        ROOT,
        str(data.get("job_id") or ""),
        str(data.get("tag") or ""),
        data.get("filenames"),
        labeled=bool(data.get("labeled")),
    )


def h3_frame_export_file(data: dict[str, Any]) -> dict[str, str]:
    return {
        "path": str(h3_frame_export_module.export_file(
            ROOT,
            str(data.get("job_id") or ""),
            str(data.get("tag") or ""),
            str(data.get("filename") or ""),
        ))
    }


def h3_action_assets(_data: dict[str, Any]) -> dict[str, Any]:
    return action_assets.list_assets(ROOT, include_archived=True)


def register_h3_action_asset(data: dict[str, Any]) -> dict[str, Any]:
    return action_assets.register_external(ROOT, data)


def register_h3_rerender_action_asset(data: dict[str, Any]) -> dict[str, Any]:
    return action_assets.register_rerender(ROOT, data)


def update_h3_action_asset(data: dict[str, Any]) -> dict[str, Any]:
    return action_assets.update_asset(
        ROOT,
        str(data.get("action_asset_id") or ""),
        data,
    )


def delete_h3_action_asset(data: dict[str, Any]) -> dict[str, Any]:
    return action_assets.delete_asset(ROOT, str(data.get("action_asset_id") or ""))


def h3_action_asset_media(data: dict[str, Any]) -> dict[str, str]:
    return {
        "path": str(action_assets.media_path(
            ROOT,
            str(data.get("action_asset_id") or ""),
            str(data.get("kind") or "h3"),
        ))
    }


def h3_projects(_data: dict[str, Any]) -> dict[str, Any]:
    return h3_prompt_projects.list_projects(ROOT)


def delete_h3_project(data: dict[str, Any]) -> dict[str, Any]:
    return h3_queue.delete_prompt_project(
        ROOT,
        str(data.get("project_id") or ""),
        expected_generation_mode="r2v",
    )


def h3_project_clips(data: dict[str, Any]) -> dict[str, Any]:
    return h3_prompt_projects.project_clips(
        ROOT, str(data.get("project_id") or "")
    )


def h3_project_clip(data: dict[str, Any]) -> dict[str, Any]:
    return h3_prompt_projects.load_clip(
        ROOT,
        str(data.get("project_id") or ""),
        str(data.get("clip_id") or ""),
    )


def h3_project_picture(data: dict[str, Any]) -> dict[str, str]:
    return {
        "path": str(
            h3_prompt_projects.picture_path(
                ROOT,
                str(data.get("project_id") or ""),
                str(data.get("clip_id") or ""),
                int(data.get("picture_index") or 0),
            )
        )
    }


def h3_candidate_reference(data: dict[str, Any]) -> dict[str, str]:
    return {
        "path": str(
            h3_queue.candidate_reference_path(
                ROOT,
                str(data.get("candidate_set_id") or ""),
                int(data.get("picture_index") or 0),
            )
        )
    }


def model_test_dashboard(_data: dict[str, Any]) -> dict[str, Any]:
    return model_test_registry.dashboard(ROOT, WORKFLOW_DIR)


def register_test_model(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_registry.register_model(ROOT, data)


def register_test_workflow(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_registry.register_workflow(ROOT, WORKFLOW_DIR, data)


def inspect_test_workflow(data: dict[str, Any]) -> dict[str, Any]:
    with model_test_registry.open_registry(ROOT) as connection:
        return workflow_adapter.inspect_workflow(
            connection, str(data.get("workflow_profile_id") or "")
        )


def register_test_adapter(data: dict[str, Any]) -> dict[str, Any]:
    with model_test_registry.open_registry(ROOT) as connection:
        return workflow_adapter.register_adapter(connection, data)


def create_model_test_session(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_registry.create_session(ROOT, data)


def delete_model_test_session(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_registry.delete_session(
        ROOT, str(data.get("session_id") or "")
    )


def save_model_test_asset(data: dict[str, Any]) -> dict[str, Any]:
    with model_test_registry.open_registry(ROOT) as connection:
        return model_test_assets.save_and_link(ROOT, connection, data)


def unlink_model_test_asset(data: dict[str, Any]) -> dict[str, Any]:
    with model_test_registry.open_registry(ROOT) as connection:
        return model_test_assets.unlink(connection, data)


def save_r2v_shared_asset(data: dict[str, Any]) -> dict[str, Any]:
    with model_test_registry.open_registry(ROOT) as connection:
        return model_test_assets.save_and_link_r2v_shared(ROOT, connection, data)


def unlink_r2v_shared_asset(data: dict[str, Any]) -> dict[str, Any]:
    with model_test_registry.open_registry(ROOT) as connection:
        return model_test_assets.unlink_r2v_shared(connection, data)


def model_test_asset_file(data: dict[str, Any]) -> dict[str, str]:
    with model_test_registry.open_registry(ROOT) as connection:
        return {
            "path": str(
                model_test_assets.resolve_file(
                    ROOT, connection, str(data.get("asset_id") or "")
                )
            )
        }


def preflight_model_test_session(data: dict[str, Any]) -> dict[str, Any]:
    with model_test_registry.open_registry(ROOT) as connection:
        return workflow_adapter.preflight_session(
            connection, str(data.get("session_id") or "")
        )


def queue_model_test_session(data: dict[str, Any]) -> dict[str, Any]:
    return benchmark_jobs.queue_session(ROOT, str(data.get("session_id") or ""))


def model_test_session_results(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_reviews.session_results(
        ROOT, str(data.get("session_id") or "")
    )


def model_test_run_review(data: dict[str, Any]) -> dict[str, Any]:
    run_id = str(data.get("run_id") or "")
    if data.get("review") is None:
        return model_test_reviews.run_review(ROOT, run_id)
    return model_test_reviews.save_review(
        ROOT, run_id, dict(data.get("review") or {})
    )


def model_test_comparison(_data: dict[str, Any]) -> dict[str, Any]:
    return model_test_reviews.comparison(ROOT)


def model_test_analysis_action(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_analysis.analyze(
        ROOT,
        str(data.get("model_id") or ""),
        str(data.get("workflow_profile_id") or "") or None,
    )


def save_model_test_policy(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_analysis.save_policy(ROOT, data)


def set_model_test_policy_active(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_analysis.set_policy_active(
        ROOT,
        str(data.get("policy_id") or ""),
        bool(data.get("active")),
    )


def create_model_test_followup(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_registry.create_followup_session(ROOT, data)


def export_model_tests(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_exports.create_export(
        ROOT, str(data.get("format") or "json")
    )


Action = Callable[[dict[str, Any]], dict[str, Any]]

ACTIONS: dict[str, Action] = {
    "h3_config": h3_config,
    "h3_state": h3_state,
    "control_windows_render_power": control_windows_render_power,
    "get_windows_power_policy": get_windows_power_policy,
    "set_windows_power_policy": set_windows_power_policy,
    "h3_candidate_page": h3_candidate_page,
    "h3_results_page": h3_results_page,
    "h3_clip_versions": h3_clip_versions,
    "create_h3_candidate_set": create_h3_candidate_set,
    "create_h3_project_test_set": create_h3_project_test_set,
    "queue_h3_project_test_set": queue_h3_project_test_set,
    "delete_h3_project_test_set": delete_h3_project_test_set,
    "queue_h3_scene_candidates": queue_h3_scene_candidates,
    "force_stop_h3_group": force_stop_h3_group,
    "select_h3_candidate": select_h3_candidate,
    "requeue_h3_candidate_set": requeue_h3_candidate_set,
    "save_h3_prompt_revision_request": save_h3_prompt_revision_request,
    "revise_h3_candidate_set": revise_h3_candidate_set,
    "apply_h3_prompt_revision": apply_h3_prompt_revision,
    "restore_h3_candidate_version": restore_h3_candidate_version,
    "create_h3_resolution_rerender": create_h3_resolution_rerender,
    "create_h3_video_upscale": create_h3_video_upscale,
    "clear_h3_candidate_selection": clear_h3_candidate_selection,
    "delete_h3_candidate_set": delete_h3_candidate_set,
    "h3_video": h3_video,
    "h3_frame_annotation_list": lambda data: h3_frame_annotations.listing(ROOT, data),
    "h3_frame_annotation_load": lambda data: h3_frame_annotations.load(ROOT, data),
    "h3_frame_annotation_save": lambda data: h3_frame_annotations.save(ROOT, data),
    "h3_frame_annotation_image": lambda data: h3_frame_annotations.image_file(ROOT, data),
    "h3_frame_export": h3_frame_export,
    "h3_frame_export_file": h3_frame_export_file,
    "h3_frame_selection_zip": h3_frame_selection_zip,
    "h3_action_assets": h3_action_assets,
    "register_h3_action_asset": register_h3_action_asset,
    "register_h3_rerender_action_asset": register_h3_rerender_action_asset,
    "update_h3_action_asset": update_h3_action_asset,
    "delete_h3_action_asset": delete_h3_action_asset,
    "h3_action_asset_media": h3_action_asset_media,
    "h3_projects": h3_projects,
    "delete_h3_project": delete_h3_project,
    "h3_project_clips": h3_project_clips,
    "h3_project_clip": h3_project_clip,
    "h3_project_picture": h3_project_picture,
    "h3_candidate_reference": h3_candidate_reference,
    "model_test_dashboard": model_test_dashboard,
    "register_test_model": register_test_model,
    "register_test_workflow": register_test_workflow,
    "inspect_test_workflow": inspect_test_workflow,
    "register_test_adapter": register_test_adapter,
    "create_model_test_session": create_model_test_session,
    "delete_model_test_session": delete_model_test_session,
    "save_model_test_asset": save_model_test_asset,
    "unlink_model_test_asset": unlink_model_test_asset,
    "save_r2v_shared_asset": save_r2v_shared_asset,
    "unlink_r2v_shared_asset": unlink_r2v_shared_asset,
    "model_test_asset_file": model_test_asset_file,
    "preflight_model_test_session": preflight_model_test_session,
    "queue_model_test_session": queue_model_test_session,
    "model_test_session_results": model_test_session_results,
    "model_test_run_review": model_test_run_review,
    "model_test_comparison": model_test_comparison,
    "model_test_analysis": model_test_analysis_action,
    "save_model_test_policy": save_model_test_policy,
    "set_model_test_policy_active": set_model_test_policy_active,
    "create_model_test_followup": create_model_test_followup,
    "export_model_tests": export_model_tests,
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ACTIONS:
        raise ValueError("지원하지 않는 UI 백엔드 작업입니다.")
    data = json.load(sys.stdin)
    result = ACTIONS[sys.argv[1]](data)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
