from __future__ import annotations

"""Registration and result recording for model-neutral benchmark jobs."""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from batch_manager import attach_job_to_batch, create_new_open_batch, load_batch, update_batch
from job_queue import atomic_write_json, now_iso, update_status
import model_test_assets
import model_test_registry
import workflow_adapter


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _job_id(case_version_id: str, repetition: int) -> str:
    token = "".join(char if char.isalnum() else "_" for char in case_version_id).strip("_")[-36:]
    return f"benchmark_{datetime.now():%Y%m%d_%H%M%S}_{token}_r{repetition:02d}_{os.urandom(2).hex()}"


def _runtime_id(session: Any, profile: Any) -> str:
    return "runtime_" + _hash_json({
        "model_id": session["model_id"],
        "engine": "ComfyUI",
        "workflow_profile_id": session["workflow_profile_id"],
        "workflow_sha256": profile["workflow_sha256"],
    })[:24]


def _prompt_variant_id(session: Any, case: Any, adapter: Any, compiled: dict[str, Any]) -> str:
    return "prompt_" + _hash_json({
        "case_id": case["case_id"],
        "model_id": session["model_id"],
        "adapter_id": session["adapter_id"],
        "prompt_sha256": compiled["prompt_sha256"],
    })[:24]


def _prepare_specs(root: Path, connection, session: Any) -> list[dict[str, Any]]:
    case_rows = connection.execute(
        """SELECT sc.case_version_id,sc.ordering,sc.planned_runs,sc.settings_json,v.case_id,v.title,
                  v.intent_ko,v.contract_json,v.category
           FROM test_session_cases sc
           JOIN benchmark_case_versions v ON v.case_version_id=sc.case_version_id
           WHERE sc.session_id=? ORDER BY sc.ordering""",
        (session["session_id"],),
    ).fetchall()
    adapter = connection.execute(
        "SELECT * FROM workflow_adapters WHERE adapter_id=?", (session["adapter_id"],)
    ).fetchone()
    profile = connection.execute(
        "SELECT * FROM workflow_profiles WHERE workflow_profile_id=?",
        (session["workflow_profile_id"],),
    ).fetchone()
    if not adapter or not profile:
        raise ValueError("세션의 워크플로우 프로필 또는 어댑터를 찾을 수 없습니다.")
    adapter_config = json.loads(adapter["config_json"] or "{}")
    bindings = dict(adapter_config.get("bindings") or {})
    specs: list[dict[str, Any]] = []
    for case in case_rows:
        for repetition in range(1, int(case["planned_runs"]) + 1):
            compiled = workflow_adapter.compile_case(
                connection, session, case["case_version_id"], repetition
            )
            if compiled.get("status") != "ready":
                raise RuntimeError(
                    f"사전검사 차단: {case['case_version_id']} · "
                    + "; ".join(compiled.get("blockers") or [])
                )
            asset_records = []
            for item in compiled.get("assets") or []:
                source_path = model_test_assets.resolve_file(root, connection, item["asset_id"])
                role = str(item["role"])
                binding = item.get("binding") or bindings.get(role)
                if not binding:
                    raise RuntimeError(f"테스트 자산 바인딩이 없습니다: {role}")
                asset_records.append({
                    **item,
                    "source_path": str(source_path),
                    "filename": f"{item['sha256']}{source_path.suffix.lower()}",
                    "binding": binding,
                })
            specs.append({
                "case": dict(case),
                "repetition": repetition,
                "compiled": compiled,
                "assets": asset_records,
                "prompt_text": str(compiled["prompt_text"]),
                "adapter": dict(adapter),
                "profile": dict(profile),
            })
    if not specs:
        raise ValueError("세션에 실행할 테스트 케이스가 없습니다.")
    return specs


def queue_session(root: Path, session_id: str) -> dict[str, Any]:
    session_id = str(session_id or "").strip()
    if not session_id:
        raise ValueError("테스트 세션 ID가 필요합니다.")
    jobs_root = root / "jobs"
    with model_test_registry.open_registry(root) as connection:
        session = connection.execute(
            "SELECT * FROM test_sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        if not session:
            raise FileNotFoundError("테스트 세션을 찾을 수 없습니다.")
        existing = connection.execute(
            "SELECT batch_id FROM test_session_batches WHERE session_id=?", (session_id,)
        ).fetchone()
        if existing:
            raise RuntimeError(f"이미 전용 큐에 등록된 세션입니다: {existing['batch_id']}")
        preflight = workflow_adapter.preflight_session(connection, session_id)
        if preflight["status"] != "ready":
            raise RuntimeError(
                f"사전검사를 통과하지 못했습니다: 준비 {preflight['ready_count']}개 · "
                f"차단 {preflight['blocked_count']}개"
            )
        session = connection.execute(
            "SELECT * FROM test_sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        specs = _prepare_specs(root, connection, session)

        settings = {
            "auto_review": True,
            "auto_modify": False,
            "auto_recheck": False,
            "max_modify_cycles": 0,
            "batch_idle_grace_seconds": 1,
        }
        batch = create_new_open_batch(root, settings)
        batch_id = str(batch["batch_id"])
        update_batch(
            root,
            batch_id,
            batch_mode="model_benchmark",
            test_session_ids=[session_id],
            registration_closed=False,
            pipeline_version="1.8.0",
            message=f"모델 테스트 {len(specs)}건을 등록하고 있습니다.",
        )
        runtime_id = _runtime_id(session, specs[0]["profile"])
        connection.execute(
            """INSERT OR IGNORE INTO model_runtimes(
                   runtime_id,model_id,engine,device_profile,runtime_config_json
               ) VALUES (?,?,?,?,?)""",
            (
                runtime_id,
                session["model_id"],
                "ComfyUI",
                "DGX Spark",
                _json({
                    "workflow_profile_id": session["workflow_profile_id"],
                    "metadata_completeness": "workflow_bound_runtime",
                    "unknown_fields": ["engine_version", "dtype", "quantization"],
                }),
            ),
        )
        queued_jobs = []
        created_at = now_iso()
        for queue_order, spec in enumerate(specs, start=1):
            case = spec["case"]
            compiled = spec["compiled"]
            repetition = spec["repetition"]
            job_id = _job_id(case["case_version_id"], repetition)
            job_dir = jobs_root / job_id
            job_dir.mkdir(parents=True, exist_ok=False)
            workflow_path = job_dir / "selected_workflow_api.json"
            atomic_write_json(workflow_path, compiled["compiled_workflow"])
            run_id = f"run_{job_id}"
            prompt_variant_id = _prompt_variant_id(session, case, spec["adapter"], compiled)
            settings_payload = dict(compiled["settings"])
            request = {
                "schema_version": 1,
                "job_type": "model_benchmark",
                "pipeline_stage": "model_benchmark_generation",
                "job_id": job_id,
                "batch_id": batch_id,
                "job_dir": str(job_dir),
                "engine_root": str(root),
                "created_at": created_at,
                "test_session_id": session_id,
                "case_version_id": case["case_version_id"],
                "case_id": case["case_id"],
                "case_title": case["title"],
                "canonical_prompt": spec["prompt_text"],
                "review_intent_ko": case["intent_ko"],
                "benchmark_contract": compiled.get("benchmark_contract") or json.loads(case["contract_json"] or "{}"),
                "case_settings": compiled.get("case_settings") or {},
                "repetition": repetition,
                "run_id": run_id,
                "queue_order": queue_order,
                "model_id": session["model_id"],
                "runtime_id": runtime_id,
                "prompt_variant_id": prompt_variant_id,
                "workflow_profile_id": session["workflow_profile_id"],
                "adapter_id": session["adapter_id"],
                "workflow_kind": spec["profile"]["profile_kind"],
                "workflow_filename": spec["profile"]["workflow_filename"],
                "source_workflow_sha256": compiled["source_workflow_sha256"],
                "compiled_workflow_sha256": compiled["workflow_sha256"],
                "prompt_sha256": compiled["prompt_sha256"],
                "template_path": str(workflow_path),
                "settings": settings_payload,
                "resolution": {"width": settings_payload.get("width"), "height": settings_payload.get("height")},
                "assets": spec["assets"],
                "filename_prefix": (
                    f"video/model-tests/{session_id}/{case['case_version_id']}_{repetition:02d}"
                ),
                "comfy_url": os.environ.get("COMFY_URL", "http://127.0.0.1:8188"),
                "comfy_start_script": os.environ.get(
                    "COMFY_START_SCRIPT", str(Path.home() / "bin/ai-start-comfy")
                ),
                "comfy_start_timeout": float(os.environ.get("COMFY_START_TIMEOUT", "180")),
                "auto_start_comfy": True,
                "automation": settings,
            }
            manifest = {
                "schema_version": 1,
                "job_id": job_id,
                "batch_id": batch_id,
                "job_type": "model_benchmark",
                "pipeline_stage": "model_benchmark_generation",
                "test_session_id": session_id,
                "case_version_id": case["case_version_id"],
                "repetition": repetition,
                "run_id": run_id,
                "resolution": {"width": settings_payload.get("width"), "height": settings_payload.get("height")},
                "status": "queued",
                "created_at": created_at,
                "outputs": [],
            }
            atomic_write_json(job_dir / "request.json", request)
            atomic_write_json(job_dir / "manifest.json", manifest)
            update_status(
                job_dir,
                "queued",
                stage="모델 테스트 worker 대기",
                message=f"{case['title']} · 반복 {repetition}",
                progress=0.0,
                created_at=created_at,
            )
            attach_job_to_batch(root, batch_id, job_id, "benchmark")
            connection.execute(
                """INSERT OR IGNORE INTO prompt_variants(
                       prompt_variant_id,case_id,model_id,adapter_name,adapter_version,
                       global_prompt,prompt_json,content_sha256
                   ) VALUES (?,?,?,?,?,?,?,?)""",
                (
                    prompt_variant_id,
                    case["case_id"],
                    session["model_id"],
                    spec["adapter"]["adapter_name"],
                    spec["adapter"]["adapter_version"],
                    spec["prompt_text"],
                    _json({"canonical_prompt": spec["prompt_text"]}),
                    compiled["prompt_sha256"],
                ),
            )
            connection.execute(
                """INSERT INTO generation_runs(
                       run_id,job_id,case_id,model_id,runtime_id,prompt_variant_id,
                       workflow_kind,workflow_filename,workflow_sha256,seed_text,seed_mode,
                       width,height,fps,frame_count,duration_seconds,status,settings_json,created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    job_id,
                    case["case_id"],
                    session["model_id"],
                    runtime_id,
                    prompt_variant_id,
                    spec["profile"]["profile_kind"],
                    spec["profile"]["workflow_filename"],
                    compiled["source_workflow_sha256"],
                    str(settings_payload.get("seed")),
                    "fixed_repetition_offset",
                    settings_payload.get("width"),
                    settings_payload.get("height"),
                    settings_payload.get("fps"),
                    settings_payload.get("frame_count"),
                    (
                        float(settings_payload.get("frame_count") or 0)
                        / float(settings_payload.get("fps") or 1)
                    ),
                    "queued",
                    _json({
                        "test_session_id": session_id,
                        "case_version_id": case["case_version_id"],
                        "repetition": repetition,
                        "compiled_workflow_sha256": compiled["workflow_sha256"],
                        "resolution": {"width": settings_payload.get("width"), "height": settings_payload.get("height")},
                    }),
                    created_at,
                ),
            )
            connection.execute(
                "INSERT INTO test_session_runs(session_id,case_version_id,run_id,repetition) VALUES (?,?,?,?)",
                (session_id, case["case_version_id"], run_id, repetition),
            )
            for ordering, asset in enumerate(spec["assets"], start=1):
                connection.execute(
                    "INSERT OR IGNORE INTO run_assets(run_id,asset_id,role,slot,ordering) VALUES (?,?,?,?,?)",
                    (run_id, asset["asset_id"], asset["role"], ordering, ordering),
                )
            queued_jobs.append(job_id)
        connection.execute(
            "INSERT INTO test_session_batches(session_id,batch_id,queued_at) VALUES (?,?,?)",
            (session_id, batch_id, created_at),
        )
        connection.execute(
            "UPDATE test_sessions SET status='queued',updated_at=? WHERE session_id=?",
            (created_at, session_id),
        )
        connection.commit()
        update_batch(
            root,
            batch_id,
            registration_closed=True,
            registration_closed_at=now_iso(),
            stage="benchmark_jobs_queued",
            next_stage="generation",
            message=f"모델 테스트 {len(queued_jobs)}건이 전용 큐에 등록되었습니다.",
        )
        return {
            "session_id": session_id,
            "batch_id": batch_id,
            "queued_count": len(queued_jobs),
            "job_ids": queued_jobs,
        }


def set_session_review_status(
    root: Path,
    session_ids: list[str],
    status: str,
) -> None:
    session_ids = [str(value) for value in session_ids if str(value or "").strip()]
    if not session_ids:
        return
    with model_test_registry.open_registry(root) as connection:
        connection.executemany(
            "UPDATE test_sessions SET status=?,updated_at=? WHERE session_id=?",
            [(status, now_iso(), session_id) for session_id in session_ids],
        )
        connection.commit()


def queue_ai_review(root: Path, session_id: str) -> dict[str, Any]:
    session_id = str(session_id or "").strip()
    if not session_id:
        raise ValueError("테스트 세션 ID가 필요합니다.")
    with model_test_registry.open_registry(root) as connection:
        session = connection.execute(
            "SELECT * FROM test_sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        if not session:
            raise FileNotFoundError("테스트 세션을 찾을 수 없습니다.")
        linked = connection.execute(
            "SELECT batch_id FROM test_session_batches WHERE session_id=?", (session_id,)
        ).fetchone()
        if not linked:
            raise RuntimeError("Qwen 검수에 연결할 전용 테스트 배치가 없습니다.")
        rows = connection.execute(
            """SELECT r.job_id FROM test_session_runs sr
               JOIN generation_runs r ON r.run_id=sr.run_id
               WHERE sr.session_id=? AND r.status='completed'
               ORDER BY r.created_at,r.job_id""",
            (session_id,),
        ).fetchall()
    completed_ids = [
        str(row["job_id"]) for row in rows
        if (root / "jobs" / str(row["job_id"]) / "manifest.json").is_file()
    ]
    if not completed_ids:
        raise RuntimeError("Qwen이 검수할 완료 영상이 없습니다.")
    batch_id = str(linked["batch_id"])
    batch = load_batch(root, batch_id)
    if not batch:
        raise FileNotFoundError("연결된 모델 테스트 배치 이력을 찾을 수 없습니다.")
    active = {
        "ready_for_review_preparation", "preparing_video_review",
        "ready_for_ai_review", "switching_to_vllm", "ai_reviewing",
    }
    if (
        str(batch.get("status") or "") in active
        and str(batch.get("pipeline_version") or "") == "1.8.0"
    ):
        return {
            "session_id": session_id,
            "batch_id": batch_id,
            "queued_count": len(completed_ids),
            "already_queued": True,
        }
    automation = dict(batch.get("automation") or {})
    automation.update(auto_review=True, auto_modify=False, auto_recheck=False, max_modify_cycles=0)
    update_batch(
        root,
        batch_id,
        batch_mode="model_benchmark",
        pipeline_version="1.8.0",
        test_session_ids=[session_id],
        automation=automation,
        review_job_ids=completed_ids,
        failed_review_job_ids=[],
        review_video_paths={},
        review_video_metadata={},
        video_review_preparation_errors=[],
        ai_review_errors=[],
        status="ready_for_review_preparation",
        stage="benchmark_review_queued",
        next_stage="video_review",
        message=f"기존 완료 영상 {len(completed_ids)}건의 Qwen 자동 검수를 대기합니다.",
    )
    set_session_review_status(root, [session_id], "ai_review_queued")
    return {
        "session_id": session_id,
        "batch_id": batch_id,
        "queued_count": len(completed_ids),
        "already_queued": False,
    }


def record_result(
    root: Path,
    request: dict[str, Any],
    *,
    status: str,
    generation_seconds: float | None = None,
    peak_gpu_memory_bytes: int | None = None,
    peak_system_memory_bytes: int | None = None,
    output_path: str | None = None,
    output_sha256: str | None = None,
    outputs: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> None:
    run_id = str(request.get("run_id") or "")
    if not run_id:
        return
    with model_test_registry.open_registry(root) as connection:
        row = connection.execute(
            "SELECT settings_json FROM generation_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if not row:
            return
        settings = json.loads(row["settings_json"] or "{}")
        settings["outputs"] = list(outputs or [])
        if error:
            settings["error"] = str(error)[:4000]
        connection.execute(
            """UPDATE generation_runs SET status=?,generation_seconds=?,
                   peak_gpu_memory_bytes=?,peak_system_memory_bytes=?,output_path=?,
                   output_sha256=?,settings_json=? WHERE run_id=?""",
            (
                status,
                generation_seconds,
                peak_gpu_memory_bytes,
                peak_system_memory_bytes,
                output_path,
                output_sha256,
                _json(settings),
                run_id,
            ),
        )
        session_id = str(request.get("test_session_id") or "")
        if session_id:
            counts = connection.execute(
                """SELECT COUNT(*) total,
                          SUM(CASE WHEN r.status IN ('completed','failed','cancelled') THEN 1 ELSE 0 END) terminal,
                          SUM(CASE WHEN r.status='completed' THEN 1 ELSE 0 END) completed
                   FROM test_session_runs sr JOIN generation_runs r ON r.run_id=sr.run_id
                   WHERE sr.session_id=?""",
                (session_id,),
            ).fetchone()
            session_status = "running"
            if int(counts["terminal"] or 0) == int(counts["total"] or 0):
                session_status = (
                    "completed"
                    if int(counts["completed"] or 0) == int(counts["total"] or 0)
                    else "completed_with_failures"
                )
            connection.execute(
                "UPDATE test_sessions SET status=?,updated_at=? WHERE session_id=?",
                (session_status, now_iso(), session_id),
            )
        connection.commit()
