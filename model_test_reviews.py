from __future__ import annotations

"""Structured, revision-preserving human reviews for benchmark generation runs."""

import hashlib
import json
from pathlib import Path
from typing import Any

import candidate_reviews
from job_queue import now_iso, read_json
import model_test_registry

I2V_SCORE_DIMENSIONS = {
    "prompt_adherence": "프롬프트 이해·반영",
    "identity_consistency": "캐릭터 정체성",
    "motion_physics": "동작·물리",
    "temporal_consistency": "시간적 일관성",
    "camera_control": "카메라 제어",
    "spatial_continuity": "공간·장면 연속성",
    "audio_dialogue": "대사·오디오",
    "visual_quality": "화질·디테일",
    "vfx_quality": "VFX 정확성·안정성",
    "narrative_causality": "시나리오 이해·인과관계",
}

R2V_SCORE_DIMENSIONS = {
    "prompt_understanding": "프롬프트·시나리오 이해",
    "reference_adherence": "참조 이미지 충실도",
    "reference_role_binding": "참조 역할 바인딩",
    "identity_consistency": "캐릭터 정체성",
    "prop_consistency": "소품 일관성",
    "event_execution": "사건 수행",
    "interaction_contact": "상호작용·접촉",
    "visual_consistency": "시각적 일관성",
    "temporal_quality": "시간적 품질",
    "camera_control": "카메라 제어",
    "shot_structure": "일반 숏 구조",
    "style_fidelity": "장르·스타일 충실도",
    "audio_dialogue": "대사·오디오",
    "overall_visual_quality": "종합 시각 품질",
}
SCORE_DIMENSIONS = {**I2V_SCORE_DIMENSIONS, **R2V_SCORE_DIMENSIONS}


def _score_dimensions(contract: dict[str, Any]) -> dict[str, str]:
    if str(contract.get("input_mode") or "") in {
        "h3_r2v_multi_reference", "r2v_multi_reference",
    }:
        return R2V_SCORE_DIMENSIONS
    return I2V_SCORE_DIMENSIONS


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _run_context(connection, run_id: str):
    run_id = str(run_id or "").strip()
    if not run_id:
        raise ValueError("평가 실행 ID가 필요합니다.")
    row = connection.execute(
        """SELECT r.*,sr.session_id,sr.case_version_id,sr.repetition,
                  v.title case_title,v.intent_ko,v.contract_json,
                  p.prompt_text canonical_prompt,s.model_id,s.workflow_profile_id,
                  m.display_name model_name,w.name workflow_name,w.profile_kind
           FROM generation_runs r
           JOIN test_session_runs sr ON sr.run_id=r.run_id
           JOIN test_sessions s ON s.session_id=sr.session_id
           JOIN benchmark_case_versions v ON v.case_version_id=sr.case_version_id
           JOIN models m ON m.model_id=s.model_id
           JOIN workflow_profiles w ON w.workflow_profile_id=s.workflow_profile_id
           LEFT JOIN benchmark_case_prompts p ON p.case_version_id=sr.case_version_id
                AND p.language='en' AND p.prompt_kind='canonical'
           WHERE r.run_id=?""",
        (run_id,),
    ).fetchone()
    if not row:
        raise FileNotFoundError("모델 테스트 실행 기록을 찾을 수 없습니다.")
    return row


def _latest_review(connection, run_id: str, reviewer_kind: str = "human_benchmark") -> dict[str, Any] | None:
    row = connection.execute(
        """SELECT * FROM reviews WHERE run_id=? AND reviewer_kind=?
           ORDER BY revision DESC LIMIT 1""",
        (run_id, reviewer_kind),
    ).fetchone()
    if not row:
        return None
    review = dict(row)
    review["issues"] = [
        {
            **dict(issue),
            "difference": issue["difference_text"],
        }
        for issue in connection.execute(
            """SELECT issue_id,category,subcategory,severity,start_seconds,end_seconds,
                      expected,observed,difference_text,cause_hypothesis,suggestion
               FROM review_issues WHERE review_version_id=? ORDER BY issue_id""",
            (row["review_version_id"],),
        )
    ]
    for issue in review["issues"]:
        issue.pop("difference_text", None)
    review["scores"] = {
        score["dimension"]: score["score"]
        for score in connection.execute(
            "SELECT dimension,score FROM capability_scores WHERE review_version_id=? ORDER BY dimension",
            (row["review_version_id"],),
        )
    }
    return review


def effective_latest_reviews(
    connection,
    run_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    params: list[Any] = []
    condition = ""
    if run_ids is not None:
        if not run_ids:
            return []
        placeholders = ",".join("?" for _ in run_ids)
        condition = f" AND rv.run_id IN ({placeholders})"
        params.extend(run_ids)
    rows = [
        dict(row)
        for row in connection.execute(
            f"""SELECT rv.* FROM reviews rv
                 WHERE rv.reviewer_kind IN ('human_benchmark','ai_benchmark','ai_benchmark_r2v')
                   {condition}
                   AND rv.revision=(
                       SELECT MAX(r2.revision) FROM reviews r2
                       WHERE r2.review_lineage_id=rv.review_lineage_id
                   )
                 ORDER BY rv.run_id,rv.reviewer_kind""",
            params,
        )
    ]
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        current = selected.get(str(row["run_id"]))
        if current is None or (
            row["reviewer_kind"] == "human_benchmark"
            and current["reviewer_kind"] != "human_benchmark"
        ):
            selected[str(row["run_id"])] = row
    return list(selected.values())


def _normalize_scores(raw: Any) -> dict[str, float]:
    if raw in (None, ""):
        return {}
    if not isinstance(raw, dict):
        raise ValueError("공통 평가 점수 형식이 올바르지 않습니다.")
    unknown = set(raw) - set(SCORE_DIMENSIONS)
    if unknown:
        raise ValueError(f"지원하지 않는 평가 축입니다: {', '.join(sorted(unknown))}")
    scores: dict[str, float] = {}
    for dimension, value in raw.items():
        if value in (None, ""):
            continue
        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{SCORE_DIMENSIONS[dimension]} 점수는 숫자여야 합니다.") from exc
        if score < 0 or score > 5:
            raise ValueError(f"{SCORE_DIMENSIONS[dimension]} 점수는 0~5 범위여야 합니다.")
        scores[dimension] = round(score, 2)
    return scores


def _save_review(
    root: Path,
    run_id: str,
    data: dict[str, Any],
    *,
    reviewer_kind: str,
    source_path: str,
) -> dict[str, Any]:
    normalized = candidate_reviews.normalize_review(data)
    scores = _normalize_scores(data.get("scores"))
    if reviewer_kind not in {"human_benchmark", "ai_benchmark", "ai_benchmark_r2v"}:
        raise ValueError("지원하지 않는 모델 테스트 리뷰 종류입니다.")
    with model_test_registry.open_registry(root) as connection:
        connection.execute("BEGIN IMMEDIATE")
        context = _run_context(connection, run_id)
        if str(context["status"] or "") != "completed":
            raise RuntimeError("완료된 모델 테스트 영상만 리뷰할 수 있습니다.")
        latest = _latest_review(connection, run_id, reviewer_kind)
        revision = int((latest or {}).get("revision") or 0) + 1
        lineage_id = f"{reviewer_kind}_review_{run_id}"
        review_version_id = f"{lineage_id}@{revision}"
        timestamp = now_iso()
        source_payload = {
            "run_id": run_id,
            "reviewer_kind": reviewer_kind,
            "revision": revision,
            "verdict": normalized["verdict"],
            "positive_note": normalized["positive_note"],
            "overall_note": normalized["overall_note"],
            "issues": normalized["issues"],
            "scores": scores,
        }
        source_sha256 = hashlib.sha256(_json(source_payload).encode("utf-8")).hexdigest()
        connection.execute(
            """INSERT INTO reviews(
                   review_version_id,review_lineage_id,revision,run_id,reviewer_kind,
                   verdict,positive_note,overall_note,created_at,updated_at,
                   source_sha256,source_path
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                review_version_id, lineage_id, revision, run_id, reviewer_kind,
                normalized["verdict"], normalized["positive_note"],
                normalized["overall_note"], timestamp, timestamp, source_sha256,
                source_path,
            ),
        )
        for issue in normalized["issues"]:
            connection.execute(
                """INSERT INTO review_issues(
                       review_version_id,issue_id,category,subcategory,severity,
                       start_seconds,end_seconds,expected,observed,difference_text,
                       cause_hypothesis,suggestion
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    review_version_id, issue["issue_id"], issue["category"],
                    issue["subcategory"], issue["severity"], issue["start_seconds"],
                    issue["end_seconds"], issue["expected"], issue["observed"],
                    issue["difference"], issue["cause_hypothesis"], issue["suggestion"],
                ),
            )
        for dimension, score in scores.items():
            score_id = f"score_{review_version_id}_{dimension}"
            connection.execute(
                """INSERT INTO capability_scores(score_id,review_version_id,dimension,score,evidence)
                   VALUES (?,?,?,?,?)""",
                (score_id, review_version_id, dimension, score, normalized["overall_note"]),
            )
        connection.commit()
        return {
            "run_id": run_id,
            "session_id": context["session_id"],
            "review": _latest_review(connection, run_id, reviewer_kind),
        }


def save_review(root: Path, run_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return _save_review(
        root, run_id, data,
        reviewer_kind="human_benchmark",
        source_path=f"model_test_review:{run_id}",
    )


def save_ai_review(
    root: Path,
    run_id: str,
    data: dict[str, Any],
    *,
    source_path: str,
) -> dict[str, Any]:
    return _save_review(
        root, run_id, data,
        reviewer_kind="ai_benchmark",
        source_path=source_path,
    )


def save_r2v_ai_review(
    root: Path,
    run_id: str,
    data: dict[str, Any],
    *,
    source_path: str,
) -> dict[str, Any]:
    return _save_review(
        root, run_id, data,
        reviewer_kind="ai_benchmark_r2v",
        source_path=source_path,
    )

def run_review(root: Path, run_id: str) -> dict[str, Any]:
    with model_test_registry.open_registry(root) as connection:
        context = dict(_run_context(connection, run_id))
        context["contract"] = json.loads(context.pop("contract_json") or "{}")
        context["settings"] = json.loads(context.pop("settings_json") or "{}")
        context["video_url"] = f"/api/jobs/{context['job_id']}/video" if context.get("job_id") else None
        return {
            "run": context,
            "review": _latest_review(connection, run_id),
            "score_dimensions": _score_dimensions(context["contract"]),
            "issue_categories": sorted(candidate_reviews.CATEGORIES),
        }


def session_results(root: Path, session_id: str) -> dict[str, Any]:
    with model_test_registry.open_registry(root) as connection:
        session = connection.execute(
            """SELECT s.*,m.display_name model_name,w.name workflow_name,w.profile_kind,
                      b.batch_id
               FROM test_sessions s
               JOIN models m ON m.model_id=s.model_id
               JOIN workflow_profiles w ON w.workflow_profile_id=s.workflow_profile_id
               LEFT JOIN test_session_batches b ON b.session_id=s.session_id
               WHERE s.session_id=?""",
            (session_id,),
        ).fetchone()
        if not session:
            raise FileNotFoundError("테스트 세션을 찾을 수 없습니다.")
        session_data = dict(session)
        batch = {}
        batch_id = str(session_data.get("batch_id") or "")
        if batch_id:
            batch = read_json(
                root / "runtime" / "batches" / batch_id / "batch.json", {}
            ) or {}
        review_job_ids = [str(value) for value in batch.get("review_job_ids") or []]
        review_order = {job_id: index for index, job_id in enumerate(review_job_ids)}
        batch_status = str(batch.get("status") or "")
        batch_errors = {
            str(item.get("job_id") or ""): str(item.get("error") or "")
            for item in (batch.get("ai_review_errors") or [])
            if isinstance(item, dict)
        }
        report_jobs = {
            job_id for job_id in review_job_ids
            if (root / "jobs" / job_id / "benchmark_ai_review_report.json").is_file()
        }
        current_review_job = None
        if batch_status == "ai_reviewing":
            current_review_job = next(
                (job_id for job_id in review_job_ids if job_id not in report_jobs),
                None,
            )

        rows = connection.execute(
            """SELECT r.run_id,r.job_id,r.status,r.seed_text,r.width,r.height,r.fps,
                      r.frame_count,r.duration_seconds,r.generation_seconds,
                      r.peak_gpu_memory_bytes,r.peak_system_memory_bytes,r.output_path,
                      sr.case_version_id,sr.repetition,sc.ordering,
                      v.title,v.intent_ko,v.category,v.tier,v.contract_json
               FROM test_session_runs sr
               JOIN generation_runs r ON r.run_id=sr.run_id
               JOIN test_session_cases sc ON sc.session_id=sr.session_id
                    AND sc.case_version_id=sr.case_version_id
               JOIN benchmark_case_versions v ON v.case_version_id=sr.case_version_id
               WHERE sr.session_id=? ORDER BY sc.ordering,sr.repetition""",
            (session_id,),
        ).fetchall()
        runs = []
        for row in rows:
            item = dict(row)
            item["contract"] = json.loads(item.pop("contract_json") or "{}")
            item["video_url"] = f"/api/jobs/{item['job_id']}/video" if item.get("job_id") else None
            human_review = _latest_review(connection, item["run_id"], "human_benchmark")
            ai_kind = (
                "ai_benchmark_r2v"
                if str(item["contract"].get("input_mode") or "") == "h3_r2v_multi_reference"
                else "ai_benchmark"
            )
            ai_review = _latest_review(connection, item["run_id"], ai_kind)
            if ai_review and item.get("job_id"):
                manifest = read_json(
                    root / "jobs" / str(item["job_id"]) / "manifest.json", {}
                ) or {}
                report = manifest.get("benchmark_ai_review") or {}
                ai_review["confidence"] = report.get("confidence")
                ai_review["event_checks"] = list(report.get("event_checks") or [])
                ai_review["forbidden_checks"] = list(report.get("forbidden_checks") or [])
                ai_review["reference_checks"] = list(report.get("reference_checks") or [])
                ai_review["dialogue_checks"] = list(report.get("dialogue_checks") or [])
                ai_review["subject_binding_checks"] = list(report.get("subject_binding_checks") or [])
                ai_review["shot_structure_check"] = dict(report.get("shot_structure_check") or {})
                ai_review["enforcement"] = dict(report.get("enforcement") or {})
                ai_review["rubric_version"] = report.get("rubric_version")
                ai_review["review_model"] = report.get("model")
            job_id = str(item.get("job_id") or "")
            status_payload = read_json(root / "jobs" / job_id / "status.json", {}) or {}
            explicit_status = str(status_payload.get("ai_review_status") or "")
            if (
                explicit_status
                and str(status_payload.get("ai_review_batch_id") or batch_id) == batch_id
            ):
                ai_status = explicit_status
            elif job_id in batch_errors:
                ai_status = "failed"
            elif ai_review or job_id in report_jobs:
                ai_status = "completed"
            elif job_id == current_review_job:
                ai_status = "reviewing"
            elif job_id in review_order and batch_status in {
                "ready_for_review_preparation", "preparing_video_review",
                "ready_for_ai_review", "switching_to_vllm", "ai_reviewing",
            }:
                ai_status = (
                    "preparing"
                    if batch_status in {"preparing_video_review", "switching_to_vllm"}
                    else "queued"
                )
            else:
                ai_status = "not_started"
            item["ai_review_status"] = ai_status
            item["ai_review_error"] = batch_errors.get(job_id) or str(
                status_payload.get("ai_review_error") or ""
            )
            item["ai_review_order"] = review_order.get(job_id)
            item["human_review"] = human_review
            item["ai_review"] = ai_review
            item["review"] = human_review or ai_review
            runs.append(item)
        ai_status_counts: dict[str, int] = {}
        for item in runs:
            key = str(item.get("ai_review_status") or "not_started")
            ai_status_counts[key] = ai_status_counts.get(key, 0) + 1
        return {
            "session": session_data,
            "batch": {
                "batch_id": batch_id or None,
                "status": batch_status or None,
                "stage": batch.get("stage"),
                "message": batch.get("message"),
            },
            "ai_review_summary": {
                "total": len(review_job_ids),
                "counts": ai_status_counts,
                "completed": ai_status_counts.get("completed", 0),
                "failed": ai_status_counts.get("failed", 0),
                "reviewing": ai_status_counts.get("reviewing", 0),
                "pending": (
                    ai_status_counts.get("queued", 0)
                    + ai_status_counts.get("preparing", 0)
                ),
            },
            "runs": runs,
            "score_dimensions": (
                R2V_SCORE_DIMENSIONS
                if any(
                    str(item["contract"].get("input_mode") or "") == "h3_r2v_multi_reference"
                    for item in runs
                )
                else I2V_SCORE_DIMENSIONS
            ),
        }

def comparison(root: Path) -> dict[str, Any]:
    with model_test_registry.open_registry(root) as connection:
        groups = connection.execute(
            """SELECT s.model_id,s.workflow_profile_id,m.display_name model_name,
                      w.name workflow_name,w.profile_kind,COUNT(DISTINCT s.session_id) session_count,
                      COUNT(r.run_id) run_count,
                      SUM(CASE WHEN r.status='completed' THEN 1 ELSE 0 END) completed_count,
                      AVG(r.generation_seconds) average_generation_seconds
               FROM test_sessions s
               JOIN models m ON m.model_id=s.model_id
               JOIN workflow_profiles w ON w.workflow_profile_id=s.workflow_profile_id
               LEFT JOIN test_session_runs sr ON sr.session_id=s.session_id
               LEFT JOIN generation_runs r ON r.run_id=sr.run_id
               GROUP BY s.model_id,s.workflow_profile_id
               ORDER BY m.display_name,w.profile_kind,w.name"""
        ).fetchall()
        results = []
        for row in groups:
            item = dict(row)
            scoped_run_ids = [
                value["run_id"]
                for value in connection.execute(
                    """SELECT r.run_id FROM generation_runs r
                       JOIN test_session_runs sr ON sr.run_id=r.run_id
                       JOIN test_sessions s ON s.session_id=sr.session_id
                       WHERE s.model_id=? AND s.workflow_profile_id=?""",
                    (row["model_id"], row["workflow_profile_id"]),
                )
            ]
            latest = effective_latest_reviews(connection, scoped_run_ids)
            review_ids = [review["review_version_id"] for review in latest]
            item["reviewed_count"] = len(review_ids)
            item["verdict_counts"] = {
                verdict: sum(review["verdict"] == verdict for review in latest)
                for verdict in candidate_reviews.VERDICTS
            }
            item["average_scores"] = {}
            if review_ids:
                placeholders = ",".join("?" for _ in review_ids)
                for score in connection.execute(
                    f"""SELECT dimension,AVG(score) average_score
                          FROM capability_scores WHERE review_version_id IN ({placeholders})
                          GROUP BY dimension""",
                    review_ids,
                ):
                    item["average_scores"][score["dimension"]] = round(float(score["average_score"]), 2)
            results.append(item)
        return {"groups": results, "score_dimensions": SCORE_DIMENSIONS}
