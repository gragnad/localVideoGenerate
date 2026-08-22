from __future__ import annotations

"""Command bridge for H3 generation, candidate selection, and model tests."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

import benchmark_jobs
import candidate_review_queue
import h3_prompt_projects
import h3_queue
import model_test_analysis
import model_test_assets
import model_test_exports
import model_test_registry
import model_test_review_queue
import model_test_reviews
import workflow_adapter


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
    return h3_queue.state(ROOT)


def set_h3_candidate_ai_review(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data.get("enabled"), bool):
        raise ValueError("후보 AI 검수 enabled 값은 true 또는 false여야 합니다.")
    return candidate_review_queue.set_enabled(ROOT, bool(data["enabled"]))


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


def queue_model_test_ai_review(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_review_queue.enqueue(
        ROOT, str(data.get("session_id") or "")
    )


def cancel_model_test_ai_review(data: dict[str, Any]) -> dict[str, Any]:
    return model_test_review_queue.cancel(
        ROOT, str(data.get("session_id") or "")
    )


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
    "set_h3_candidate_ai_review": set_h3_candidate_ai_review,
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
    "h3_projects": h3_projects,
    "delete_h3_project": delete_h3_project,
    "h3_project_clips": h3_project_clips,
    "h3_project_clip": h3_project_clip,
    "h3_project_picture": h3_project_picture,
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
    "queue_model_test_ai_review": queue_model_test_ai_review,
    "cancel_model_test_ai_review": cancel_model_test_ai_review,
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
