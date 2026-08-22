from __future__ import annotations

"""Evidence-bounded capability analysis and prompt policy curation."""

import hashlib
import json
from pathlib import Path
from typing import Any

from job_queue import now_iso
import model_test_registry
import model_test_r2v
from model_test_reviews import (
    I2V_SCORE_DIMENSIONS,
    R2V_SCORE_DIMENSIONS,
    SCORE_DIMENSIONS,
    effective_latest_reviews,
)

CATEGORY_DIMENSIONS = {
    "prompt_detail_omission": "prompt_adherence",
    "motion_physics": "motion_physics",
    "character_identity": "identity_consistency",
    "scene_continuity": "spatial_continuity",
    "camera_direction": "camera_control",
    "background_props": "spatial_continuity",
    "dialogue_audio": "audio_dialogue",
    "visual_temporal_quality": "visual_quality",
    "vfx_effects": "vfx_quality",
    "scenario_comprehension": "narrative_causality",
    "other": None,
}

R2V_CATEGORY_DIMENSIONS = {
    "prompt_detail_omission": "prompt_understanding",
    "motion_physics": "interaction_contact",
    "character_identity": "identity_consistency",
    "scene_continuity": "visual_consistency",
    "camera_direction": "camera_control",
    "background_props": "prop_consistency",
    "dialogue_audio": "audio_dialogue",
    "visual_temporal_quality": "temporal_quality",
    "vfx_effects": "visual_consistency",
    "scenario_comprehension": "event_execution",
    "other": None,
}

def _is_r2v_workflow(workflow: dict[str, Any] | None) -> bool:
    return bool(
        workflow
        and model_test_r2v.is_r2v_workflow_filename(
            str(workflow.get("workflow_filename") or "")
        )
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _confidence(evidence_count: int) -> str:
    if evidence_count < 3:
        return "insufficient"
    if evidence_count < 10:
        return "exploratory"
    return "supported"


def _selector(connection, model_id: str, workflow_profile_id: str | None):
    model = connection.execute("SELECT * FROM models WHERE model_id=?", (model_id,)).fetchone()
    if not model:
        raise FileNotFoundError("분석할 모델을 찾을 수 없습니다.")
    params: list[Any] = [model_id]
    condition = "s.model_id=?"
    workflow = None
    if workflow_profile_id:
        workflow = connection.execute(
            "SELECT * FROM workflow_profiles WHERE workflow_profile_id=? AND model_id=?",
            (workflow_profile_id, model_id),
        ).fetchone()
        if not workflow:
            raise ValueError("선택한 워크플로우가 모델에 속하지 않습니다.")
        condition += " AND s.workflow_profile_id=?"
        params.append(workflow_profile_id)
    return dict(model), dict(workflow) if workflow else None, condition, params


def analyze(root: Path, model_id: str, workflow_profile_id: str | None = None) -> dict[str, Any]:
    with model_test_registry.open_registry(root) as connection:
        model, workflow, condition, params = _selector(connection, model_id, workflow_profile_id)
        is_r2v = _is_r2v_workflow(workflow)
        dimension_catalog = (
            R2V_SCORE_DIMENSIONS if is_r2v
            else I2V_SCORE_DIMENSIONS if workflow
            else SCORE_DIMENSIONS
        )
        category_dimensions = R2V_CATEGORY_DIMENSIONS if is_r2v else CATEGORY_DIMENSIONS
        runs = [
            dict(row)
            for row in connection.execute(
                f"""SELECT r.run_id,r.status,r.generation_seconds,sr.session_id,
                           sr.case_version_id,v.title,v.category,v.intent_ko,
                           s.workflow_profile_id,w.name workflow_name,w.profile_kind
                    FROM test_session_runs sr
                    JOIN generation_runs r ON r.run_id=sr.run_id
                    JOIN test_sessions s ON s.session_id=sr.session_id
                    JOIN workflow_profiles w ON w.workflow_profile_id=s.workflow_profile_id
                    JOIN benchmark_case_versions v ON v.case_version_id=sr.case_version_id
                    WHERE {condition}""",
                params,
            )
        ]
        run_ids = [row["run_id"] for row in runs]
        latest_reviews = effective_latest_reviews(connection, run_ids)
        review_by_run = {row["run_id"]: row for row in latest_reviews}
        review_ids = [row["review_version_id"] for row in latest_reviews]
        issues: list[dict[str, Any]] = []
        scores: list[dict[str, Any]] = []
        if review_ids:
            placeholders = ",".join("?" for _ in review_ids)
            issues = [
                dict(row)
                for row in connection.execute(
                    f"""SELECT i.*,rv.run_id FROM review_issues i
                          JOIN reviews rv ON rv.review_version_id=i.review_version_id
                          WHERE i.review_version_id IN ({placeholders})""",
                    review_ids,
                )
            ]
            scores = [
                dict(row)
                for row in connection.execute(
                    f"""SELECT c.*,rv.run_id FROM capability_scores c
                          JOIN reviews rv ON rv.review_version_id=c.review_version_id
                          WHERE c.review_version_id IN ({placeholders})""",
                    review_ids,
                )
            ]
        dimension_rows = []
        for dimension, label in dimension_catalog.items():
            values = [float(row["score"]) for row in scores if row["dimension"] == dimension]
            dimension_rows.append({
                "dimension": dimension,
                "label": label,
                "average_score": round(sum(values) / len(values), 2) if values else None,
                "evidence_count": len(values),
                "confidence": _confidence(len(values)),
            })
        issue_groups: dict[tuple[str, str], dict[str, Any]] = {}
        for issue in issues:
            key = (str(issue["category"]), str(issue["subcategory"]))
            group = issue_groups.setdefault(key, {
                "category": key[0],
                "subcategory": key[1],
                "dimension": category_dimensions.get(key[0]),
                "count": 0,
                "critical_count": 0,
                "major_count": 0,
                "run_ids": [],
                "suggestions": {},
            })
            group["count"] += 1
            if issue["severity"] == "critical":
                group["critical_count"] += 1
            if issue["severity"] == "major":
                group["major_count"] += 1
            if issue["run_id"] not in group["run_ids"]:
                group["run_ids"].append(issue["run_id"])
            suggestion = str(issue.get("suggestion") or "").strip()
            if suggestion:
                suggestion_evidence = group["suggestions"].setdefault(
                    suggestion, {"count": 0, "run_ids": []}
                )
                suggestion_evidence["count"] += 1
                if issue["run_id"] not in suggestion_evidence["run_ids"]:
                    suggestion_evidence["run_ids"].append(issue["run_id"])
        issue_rows = []
        for group in issue_groups.values():
            group["confidence"] = _confidence(len(group["run_ids"]))
            group["suggestions"] = [
                {
                    "rule_text": text,
                    "evidence_count": len(evidence["run_ids"]),
                    "run_ids": evidence["run_ids"],
                }
                for text, evidence in sorted(
                    group["suggestions"].items(),
                    key=lambda item: (-item[1]["count"], item[0]),
                )
            ]
            issue_rows.append(group)
        issue_rows.sort(key=lambda row: (-row["critical_count"], -row["major_count"], -row["count"], row["category"], row["subcategory"]))
        cases: dict[str, dict[str, Any]] = {}
        score_by_run: dict[str, list[float]] = {}
        for score in scores:
            score_by_run.setdefault(score["run_id"], []).append(float(score["score"]))
        issues_by_run: dict[str, int] = {}
        for issue in issues:
            issues_by_run[issue["run_id"]] = issues_by_run.get(issue["run_id"], 0) + 1
        for run in runs:
            case = cases.setdefault(run["case_version_id"], {
                "case_version_id": run["case_version_id"],
                "title": run["title"],
                "category": run["category"],
                "intent_ko": run["intent_ko"],
                "run_count": 0,
                "completed_count": 0,
                "reviewed_count": 0,
                "acceptable_count": 0,
                "issue_count": 0,
                "score_values": [],
            })
            case["run_count"] += 1
            if run["status"] == "completed":
                case["completed_count"] += 1
            review = review_by_run.get(run["run_id"])
            if review:
                case["reviewed_count"] += 1
                if review["verdict"] == "acceptable":
                    case["acceptable_count"] += 1
                case["issue_count"] += issues_by_run.get(run["run_id"], 0)
                case["score_values"].extend(score_by_run.get(run["run_id"], []))
        case_rows = []
        for case in cases.values():
            values = case.pop("score_values")
            case["average_score"] = round(sum(values) / len(values), 2) if values else None
            case["acceptance_rate"] = (
                round(case["acceptable_count"] / case["reviewed_count"], 3)
                if case["reviewed_count"] else None
            )
            case["confidence"] = _confidence(case["reviewed_count"])
            case["needs_more_evidence"] = case["reviewed_count"] < 3
            case_rows.append(case)
        case_rows.sort(key=lambda row: (row["average_score"] is None, row["average_score"] or 0, -row["issue_count"], row["title"]))
        policy_candidates = []
        for group in issue_rows:
            for suggestion in group["suggestions"]:
                candidate = {
                    "candidate_id": "policy_candidate_" + hashlib.sha256(
                        _json({"model_id": model_id, "workflow_profile_id": workflow_profile_id, "group": group["category"], "subcategory": group["subcategory"], "rule": suggestion["rule_text"]}).encode("utf-8")
                    ).hexdigest()[:20],
                    "dimension": group["dimension"],
                    "category": group["category"],
                    "subcategory": group["subcategory"],
                    "rule_text": suggestion["rule_text"],
                    "evidence_count": suggestion["evidence_count"],
                    "confidence": _confidence(suggestion["evidence_count"]),
                    "evidence_run_ids": list(suggestion["run_ids"]),
                }
                policy_candidates.append(candidate)
        policy_condition = "p.model_id=? AND p.active=1"
        policy_params: list[Any] = [model_id]
        if workflow_profile_id:
            policy_condition += " AND (s.workflow_profile_id IS NULL OR s.workflow_profile_id=?)"
            policy_params.append(workflow_profile_id)
        active_policies = [
            {
                **dict(row),
                "evidence": json.loads(row["evidence_json"] or "{}"),
            }
            for row in connection.execute(
                f"""SELECT p.*,s.workflow_profile_id,w.name workflow_name
                    FROM prompt_policies p
                    LEFT JOIN prompt_policy_scopes s ON s.policy_id=p.policy_id
                    LEFT JOIN workflow_profiles w ON w.workflow_profile_id=s.workflow_profile_id
                    WHERE {policy_condition}
                    ORDER BY p.dimension,p.created_at""",
                policy_params,
            )
        ]
        prompt_guidance = "\n".join(
            [
                "# Evidence-based prompt guidance",
                f"- Model: {model['display_name']}",
                f"- Workflow: {workflow['name'] if workflow else 'all workflows'}",
                "- Apply only the following human-approved rules; do not invent unsupported model traits.",
                *[
                    f"- [{row['workflow_name'] or 'all workflows'}] {row['rule_text']}"
                    for row in active_policies
                ],
            ]
        )
        completed = sum(row["status"] == "completed" for row in runs)
        failed = sum(row["status"] == "failed" for row in runs)
        cancelled = sum(row["status"] == "cancelled" for row in runs)
        generation_times = [float(row["generation_seconds"]) for row in runs if row["generation_seconds"] is not None]
        return {
            "model": model,
            "workflow": workflow,
            "input_mode": "h3_r2v_multi_reference" if is_r2v else "general",
            "scope": {"model_id": model_id, "workflow_profile_id": workflow_profile_id},
            "summary": {
                "run_count": len(runs),
                "completed_count": completed,
                "failed_count": failed,
                "cancelled_count": cancelled,
                "reviewed_count": len(latest_reviews),
                "scored_review_count": len({row["run_id"] for row in scores}),
                "review_coverage": round(len(latest_reviews) / completed, 3) if completed else 0.0,
                "average_generation_seconds": round(sum(generation_times) / len(generation_times), 2) if generation_times else None,
            },
            "dimensions": dimension_rows,
            "issues": issue_rows,
            "cases": case_rows,
            "policy_candidates": policy_candidates,
            "active_policies": active_policies,
            "prompt_guidance": prompt_guidance,
            "evidence_notice": "리뷰 3건 미만은 insufficient, 3~9건은 exploratory, 10건 이상은 supported로 표시합니다.",
        }


def save_policy(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    model_id = str(data.get("model_id") or "").strip()
    workflow_profile_id = str(data.get("workflow_profile_id") or "").strip() or None
    rule_text = str(data.get("rule_text") or "").strip()
    dimension = str(data.get("dimension") or "").strip() or None
    run_ids = list(dict.fromkeys(str(value or "").strip() for value in (data.get("evidence_run_ids") or []) if str(value or "").strip()))
    if not model_id or not rule_text:
        raise ValueError("모델과 프롬프트 정책 문장이 필요합니다.")
    if len(rule_text) > 4000:
        raise ValueError("프롬프트 정책은 4000자 이하여야 합니다.")
    if dimension and dimension not in SCORE_DIMENSIONS:
        raise ValueError("지원하지 않는 정책 평가 축입니다.")
    if not run_ids:
        raise ValueError("정책을 승인하려면 근거 실행이 한 건 이상 필요합니다.")
    with model_test_registry.open_registry(root) as connection:
        _selector(connection, model_id, workflow_profile_id)
        placeholders = ",".join("?" for _ in run_ids)
        evidence_condition = "s.model_id=?"
        evidence_params: list[Any] = [model_id]
        if workflow_profile_id:
            evidence_condition += " AND s.workflow_profile_id=?"
            evidence_params.append(workflow_profile_id)
        found = connection.execute(
            f"""SELECT DISTINCT r.run_id FROM generation_runs r
                  JOIN test_session_runs sr ON sr.run_id=r.run_id
                  JOIN test_sessions s ON s.session_id=sr.session_id
                  JOIN reviews rv ON rv.run_id=r.run_id AND rv.reviewer_kind='human_benchmark'
                    AND rv.revision=(SELECT MAX(r2.revision) FROM reviews r2
                                     WHERE r2.review_lineage_id=rv.review_lineage_id)
                  WHERE {evidence_condition} AND r.run_id IN ({placeholders})""",
            [*evidence_params, *run_ids],
        ).fetchall()
        found_ids = {row["run_id"] for row in found}
        if found_ids != set(run_ids):
            raise ValueError("모델의 최신 사람 리뷰로 확인되지 않은 근거 실행이 포함됐습니다.")
        evidence = {
            "run_ids": run_ids,
            "workflow_profile_id": workflow_profile_id,
            "approved_at": now_iso(),
            "source": "human_confirmed_benchmark_analysis",
        }
        policy_id = "policy_" + hashlib.sha256(
            _json({
                "model": model_id,
                "workflow_profile_id": workflow_profile_id,
                "dimension": dimension,
                "rule": rule_text,
                "evidence": run_ids,
            }).encode("utf-8")
        ).hexdigest()[:24]
        confidence = _confidence(len(run_ids))
        connection.execute(
            """INSERT INTO prompt_policies(
                   policy_id,model_id,dimension,rule_text,evidence_count,confidence,
                   evidence_json,active,created_at,updated_at
               ) VALUES (?,?,?,?,?,?,?,1,?,?)
               ON CONFLICT(policy_id) DO UPDATE SET active=1,updated_at=excluded.updated_at""",
            (policy_id, model_id, dimension, rule_text, len(run_ids), confidence, _json(evidence), now_iso(), now_iso()),
        )
        connection.execute(
            """INSERT INTO prompt_policy_scopes(policy_id,workflow_profile_id) VALUES (?,?)
               ON CONFLICT(policy_id) DO UPDATE SET workflow_profile_id=excluded.workflow_profile_id""",
            (policy_id, workflow_profile_id),
        )
        connection.commit()
        return {"policy_id": policy_id, "active": True, "confidence": confidence, "evidence_count": len(run_ids)}


def set_policy_active(root: Path, policy_id: str, active: bool) -> dict[str, Any]:
    with model_test_registry.open_registry(root) as connection:
        cursor = connection.execute(
            "UPDATE prompt_policies SET active=?,updated_at=? WHERE policy_id=?",
            (1 if active else 0, now_iso(), str(policy_id or "")),
        )
        if not cursor.rowcount:
            raise FileNotFoundError("프롬프트 정책을 찾을 수 없습니다.")
        connection.commit()
        return {"policy_id": policy_id, "active": bool(active)}
