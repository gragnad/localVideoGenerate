from __future__ import annotations

"""Registration and result recording for model-neutral benchmark jobs."""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


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


def _session_workflow_settings(session: Any) -> dict[str, Any]:
    if "workflow_settings_json" not in session.keys():
        return {}
    try:
        value = json.loads(session["workflow_settings_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _runtime_id(
    session: Any,
    profile: Any,
    workflow_settings: dict[str, Any] | None = None,
) -> str:
    return "runtime_" + _hash_json({
        "model_id": session["model_id"],
        "engine": "ComfyUI",
        "workflow_profile_id": session["workflow_profile_id"],
        "workflow_sha256": profile["workflow_sha256"],
        "workflow_settings": (
            workflow_settings
            if workflow_settings is not None
            else _session_workflow_settings(session)
        ),
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
    return queue_h3_session(root, session_id)


def queue_h3_session(root: Path, session_id: str) -> dict[str, Any]:
    """Compile a model benchmark session directly into the batch-free H3 queue."""
    import h3_queue

    paths = h3_queue.roots(root)
    created_at = now_iso()
    queue_id = f"h3testq_{datetime.now():%Y%m%d_%H%M%S}_{os.urandom(3).hex()}"
    queue_dir = paths["test_queues"] / queue_id
    queue_dir.mkdir(parents=True, exist_ok=False)
    try:
        with model_test_registry.open_registry(root) as connection:
            session = connection.execute(
                "SELECT * FROM test_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
            if not session:
                raise FileNotFoundError("테스트 세션을 찾을 수 없습니다.")
            model = connection.execute(
                "SELECT provider,family,display_name,version FROM models WHERE model_id=?",
                (session["model_id"],),
            ).fetchone()
            if model_test_registry.is_legacy_ltx_model(model):
                raise ValueError("LTX 테스트 세션은 과거 검수 데이터 열람 전용입니다.")
            is_r2v = model_test_registry.model_test_r2v.is_r2v_suite_id(session["suite_id"])
            is_i2v = (
                session["suite_id"] == model_test_registry.I2V_SUITE_ID
                or model_test_registry.model_test_i2v.is_i2v_suite_id(session["suite_id"])
            )
            job_type = "h3_r2v_benchmark" if is_r2v else "h3_model_benchmark"
            generation_mode = "r2v" if is_r2v else "i2v" if is_i2v else "model"
            test_label = "H3 R2V 테스트" if is_r2v else "H3 I2V 테스트" if is_i2v else "H3 일반 모델 테스트"
            existing = connection.execute(
                "SELECT COUNT(*) count FROM test_session_runs WHERE session_id=?", (session_id,)
            ).fetchone()
            if int(existing["count"] or 0):
                raise RuntimeError("이미 H3 테스트 큐에 등록된 세션입니다.")
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
            effective_workflow_settings = dict(
                specs[0]["compiled"]["settings"].get("workflow_settings") or {}
            )
            runtime_id = _runtime_id(
                session, specs[0]["profile"], effective_workflow_settings
            )
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
                        "queue_backend": "h3_generation",
                        "workflow_settings": effective_workflow_settings,
                        "metadata_completeness": "workflow_bound_runtime",
                        "unknown_fields": ["engine_version", "dtype", "quantization"],
                    }),
                ),
            )
            queued_jobs = []
            for queue_order, spec in enumerate(specs, start=1):
                case = spec["case"]
                compiled = spec["compiled"]
                repetition = spec["repetition"]
                base_id = _job_id(case["case_version_id"], repetition).replace("benchmark_", "h3bench_", 1)
                job_id = base_id
                job_dir = paths["jobs"] / job_id
                job_dir.mkdir(parents=True, exist_ok=False)
                atomic_write_json(job_dir / "workflow_api.json", compiled["compiled_workflow"])
                run_id = f"run_{job_id}"
                prompt_variant_id = _prompt_variant_id(session, case, spec["adapter"], compiled)
                settings_payload = dict(compiled["settings"])
                references = [{
                    "picture_index": index,
                    "role": asset["role"],
                    "asset_id": asset["asset_id"],
                    "source_path": asset["source_path"],
                    "original_name": Path(asset["source_path"]).name,
                    "sha256": asset["sha256"],
                } for index, asset in enumerate(spec["assets"], start=1)]
                reference_patches = [dict(asset["binding"]) for asset in spec["assets"]]
                request = {
                    "schema_version": 1,
                    "job_type": job_type,
                    "generation_mode": generation_mode,
                    "queue_name": "h3_generation",
                    "queue_lane": "local_generation",
                    "pipeline_stage": "model_benchmark_generation",
                    "job_id": job_id,
                    "test_queue_id": queue_id,
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
                    "settings": settings_payload,
                    "resolution": {"width": settings_payload.get("width"), "height": settings_payload.get("height")},
                    "assets": spec["assets"],
                    "references": references,
                    "reference_patches": reference_patches,
                    "filename_prefix": f"video/model-tests/{session_id}/{case['case_version_id']}_{repetition:02d}",
                    "comfy_url": os.environ.get("COMFY_URL", "http://127.0.0.1:8188"),
                }
                manifest = {
                    "schema_version": 1,
                    "job_id": job_id,
                    "job_type": job_type,
                    "test_queue_id": queue_id,
                    "test_session_id": session_id,
                    "case_version_id": case["case_version_id"],
                    "repetition": repetition,
                    "run_id": run_id,
                    "resolution": request["resolution"],
                    "workflow_settings": settings_payload.get("workflow_settings") or {},
                    "status": "queued",
                    "created_at": created_at,
                    "outputs": [],
                }
                atomic_write_json(job_dir / "request.json", request)
                atomic_write_json(job_dir / "manifest.json", manifest)
                update_status(
                    job_dir,
                    "queued",
                    stage=f"{test_label} 로컬 Worker 대기",
                    message=f"{case['title']} · 반복 {repetition}",
                    progress=0.0,
                    created_at=created_at,
                )
                connection.execute(
                    """INSERT OR IGNORE INTO prompt_variants(
                           prompt_variant_id,case_id,model_id,adapter_name,adapter_version,
                           global_prompt,prompt_json,content_sha256
                       ) VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        prompt_variant_id, case["case_id"], session["model_id"],
                        spec["adapter"]["adapter_name"], spec["adapter"]["adapter_version"],
                        spec["prompt_text"], _json({"canonical_prompt": spec["prompt_text"]}),
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
                        run_id, job_id, case["case_id"], session["model_id"], runtime_id,
                        prompt_variant_id, spec["profile"]["profile_kind"],
                        spec["profile"]["workflow_filename"], compiled["source_workflow_sha256"],
                        str(settings_payload.get("seed")), "random_resolved",
                        settings_payload.get("width"), settings_payload.get("height"),
                        settings_payload.get("fps"), settings_payload.get("frame_count"),
                        float(settings_payload.get("frame_count") or 0) / float(settings_payload.get("fps") or 1),
                        "queued",
                        _json({
                            "test_session_id": session_id,
                            "test_queue_id": queue_id,
                            "queue_backend": "h3_generation",
                            "case_version_id": case["case_version_id"],
                            "repetition": repetition,
                            "compiled_workflow_sha256": compiled["workflow_sha256"],
                            "resolution": request["resolution"],
                            "workflow_settings": settings_payload.get("workflow_settings") or {},
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
            queue_payload = {
                "schema_version": 1,
                "test_queue_id": queue_id,
                "queue_name": "h3_generation",
                "queue_kind": f"{generation_mode}_model_test",
                "generation_mode": generation_mode,
                "status": "queued",
                "test_session_id": session_id,
                "suite_id": session["suite_id"],
                "created_at": created_at,
                "updated_at": created_at,
                "job_ids": queued_jobs,
                "job_count": len(queued_jobs),
                "queued_count": len(queued_jobs),
                "running_count": 0,
                "completed_count": 0,
                "failed_count": 0,
            }
            atomic_write_json(queue_dir / "queue.json", queue_payload)
            connection.execute(
                "UPDATE test_sessions SET status='queued',updated_at=? WHERE session_id=?",
                (created_at, session_id),
            )
            connection.commit()
        return {
            "session_id": session_id,
            "queue_id": queue_id,
            "queue_backend": "h3_generation",
            "queued_count": len(queued_jobs),
            "job_ids": queued_jobs,
        }
    except Exception:
        atomic_write_json(queue_dir / "queue.json", {
            "schema_version": 1,
            "test_queue_id": queue_id,
            "queue_name": "h3_generation",
            "queue_kind": "r2v_model_test",
            "status": "registration_failed",
            "test_session_id": session_id,
            "created_at": created_at,
            "updated_at": now_iso(),
        })
        raise



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
