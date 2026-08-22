from __future__ import annotations

import json
import unittest
from pathlib import Path

import benchmark_jobs
from job_queue import read_json
import model_test_analysis
import model_test_exports
import model_test_r2v
import model_test_registry
import model_test_reviews
import tests.test_benchmark_jobs as benchmark_fixture


class ModelTestAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.fixture = benchmark_fixture.BenchmarkJobsTest(methodName="test_schema_v10_has_no_batch_link_table")
        self.fixture.setUp()
        self.root = self.fixture.root
        self.source_session_id = self.fixture.session_id
        queued = benchmark_jobs.queue_session(self.root, self.source_session_id)
        self.requests = [
            read_json(
                self.root / "runtime/h3/jobs" / job_id / "request.json", {}
            )
            for job_id in queued["job_ids"]
        ]
        self.request = self.requests[0]
        benchmark_jobs.record_result(
            self.root,
            self.request,
            status="completed",
            generation_seconds=15.25,
            peak_gpu_memory_bytes=4096,
            peak_system_memory_bytes=8192,
        )
        model_test_reviews.save_review(self.root, self.request["run_id"], {
            "verdict": "needs_improvement",
            "positive_note": "구도는 안정적",
            "overall_note": "카메라 속도 개선 필요",
            "issues": [{
                "issue_id": "issue_camera",
                "category": "camera_direction",
                "subcategory": "camera_speed",
                "severity": "major",
                "start_seconds": 1,
                "end_seconds": 3,
                "expected": "카메라가 천천히 이동한다.",
                "observed": "카메라가 급격하게 이동한다.",
                "difference": "속도가 지나치게 빠르다.",
                "cause_hypothesis": "속도 제약이 약함",
                "suggestion": "카메라 이동 속도와 종료 지점을 명시한다.",
            }],
            "scores": {"prompt_adherence": 3, "camera_control": 2, "visual_quality": 4},
        })
        self.model_id = self.request["model_id"]
        self.workflow_profile_id = self.request["workflow_profile_id"]

    def tearDown(self):
        self.fixture.tearDown()

    def test_analysis_marks_small_evidence_and_builds_policy_candidate(self):
        result = model_test_analysis.analyze(self.root, self.model_id, self.workflow_profile_id)
        self.assertEqual(result["summary"]["completed_count"], 1)
        self.assertEqual(result["summary"]["reviewed_count"], 1)
        camera = next(row for row in result["dimensions"] if row["dimension"] == "camera_control")
        self.assertEqual(camera["average_score"], 2.0)
        self.assertEqual(camera["confidence"], "insufficient")
        candidate = result["policy_candidates"][0]
        self.assertIn("카메라 이동 속도", candidate["rule_text"])
        self.assertEqual(candidate["evidence_run_ids"], [self.request["run_id"]])
        weak_case = next(row for row in result["cases"] if row["case_version_id"] == self.request["case_version_id"])
        self.assertTrue(weak_case["needs_more_evidence"])

    def test_r2v_workflow_uses_only_r2v_capability_dimensions(self):
        for filename in model_test_r2v.R2V_WORKFLOW_FILENAMES:
            with self.subTest(filename=filename):
                with model_test_registry.open_registry(self.root) as connection:
                    connection.execute(
                        "UPDATE workflow_profiles SET workflow_filename=? WHERE workflow_profile_id=?",
                        (filename, self.workflow_profile_id),
                    )
                result = model_test_analysis.analyze(
                    self.root, self.model_id, self.workflow_profile_id
                )
                self.assertEqual(result["input_mode"], "h3_r2v_multi_reference")
                self.assertEqual(
                    {row["dimension"] for row in result["dimensions"]},
                    set(model_test_reviews.R2V_SCORE_DIMENSIONS),
                )
                self.assertNotIn(
                    "prompt_adherence",
                    {row["dimension"] for row in result["dimensions"]},
                )
                self.assertEqual(
                    result["issues"][0]["dimension"], "camera_control"
                )

    def test_policy_requires_review_evidence_and_can_be_deactivated(self):
        with self.assertRaisesRegex(ValueError, "근거 실행"):
            model_test_analysis.save_policy(self.root, {
                "model_id": self.model_id,
                "rule_text": "근거 없는 규칙",
                "evidence_run_ids": [],
            })
        saved = model_test_analysis.save_policy(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.workflow_profile_id,
            "dimension": "camera_control",
            "rule_text": "카메라 이동 속도와 종료 지점을 명시한다.",
            "evidence_run_ids": [self.request["run_id"]],
        })
        self.assertTrue(saved["active"])
        with model_test_registry.open_registry(self.root) as connection:
            scope = connection.execute(
                "SELECT workflow_profile_id FROM prompt_policy_scopes WHERE policy_id=?",
                (saved["policy_id"],),
            ).fetchone()
            self.assertEqual(scope["workflow_profile_id"], self.workflow_profile_id)
        analyzed = model_test_analysis.analyze(
            self.root, self.model_id, self.workflow_profile_id
        )
        self.assertIn("카메라 이동 속도", analyzed["prompt_guidance"])
        self.assertEqual(
            analyzed["active_policies"][0]["workflow_profile_id"],
            self.workflow_profile_id,
        )
        disabled = model_test_analysis.set_policy_active(self.root, saved["policy_id"], False)
        self.assertFalse(disabled["active"])
        result = model_test_analysis.analyze(self.root, self.model_id, self.workflow_profile_id)
        self.assertEqual(result["active_policies"], [])

    def test_policy_evidence_must_match_workflow_scope(self):
        other = self.fixture.workflows / "other.json"
        other.write_text(
            (self.fixture.workflows / "official.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        profile = model_test_registry.register_workflow(
            self.root,
            self.fixture.workflows,
            {
                "model_id": self.model_id,
                "workflow_filename": "other.json",
                "profile_kind": "controlled_variant",
                "name": "Other workflow",
            },
        )
        with self.assertRaisesRegex(ValueError, "최신 사람 리뷰"):
            model_test_analysis.save_policy(self.root, {
                "model_id": self.model_id,
                "workflow_profile_id": profile["workflow_profile_id"],
                "dimension": "camera_control",
                "rule_text": "다른 워크플로우에 잘못 귀속하면 안 된다.",
                "evidence_run_ids": [self.request["run_id"]],
            })

    def test_targeted_followup_session_preserves_lineage_and_subset(self):
        selected = [self.requests[0]["case_version_id"], self.requests[4]["case_version_id"]]
        result = model_test_registry.create_followup_session(self.root, {
            "source_session_id": self.source_session_id,
            "case_version_ids": selected,
            "repetitions": 2,
            "reason": "weak_cases",
        })
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["planned_run_count"], 4)
        with model_test_registry.open_registry(self.root) as connection:
            lineage = connection.execute(
                "SELECT parent_session_id,reason FROM test_session_lineage WHERE child_session_id=?",
                (result["session_id"],),
            ).fetchone()
            self.assertEqual(lineage["parent_session_id"], self.source_session_id)
            self.assertEqual(lineage["reason"], "weak_cases")
            cases = connection.execute(
                "SELECT case_version_id,planned_runs FROM test_session_cases WHERE session_id=? ORDER BY ordering",
                (result["session_id"],),
            ).fetchall()
            self.assertEqual([row["case_version_id"] for row in cases], selected)
            self.assertTrue(all(row["planned_runs"] == 2 for row in cases))
        dashboard = model_test_registry.dashboard(self.root, self.fixture.workflows)
        child = next(row for row in dashboard["sessions"] if row["session_id"] == result["session_id"])
        self.assertEqual(child["parent_session_id"], self.source_session_id)

    def test_portable_exports_omit_local_paths_and_redact_secret_like_text(self):
        model_test_analysis.save_policy(self.root, {
            "model_id": self.model_id,
            "dimension": "camera_control",
            "rule_text": "camera note token=do-not-export",
            "evidence_run_ids": [self.request["run_id"]],
        })
        json_export = model_test_exports.create_export(self.root, "json")
        content = Path(json_export["path"]).read_text(encoding="utf-8")
        payload = json.loads(content)
        self.assertEqual(payload["export_schema"], "video_model_benchmark_portable_v1")
        self.assertNotIn(str(self.root), content)
        self.assertNotIn("do-not-export", content)
        self.assertIn("[REDACTED]", content)
        self.assertNotIn("workflow_path", content)
        self.assertNotIn("output_path", content)
        self.assertIn("prompt_policy_scopes", payload)
        csv_export = model_test_exports.create_export(self.root, "csv")
        csv_text = Path(csv_export["path"]).read_text(encoding="utf-8-sig")
        self.assertIn("run_id,session_id,model_id", csv_text)
        self.assertIn(self.request["run_id"], csv_text)
        with self.assertRaisesRegex(ValueError, "json 또는 csv"):
            model_test_exports.create_export(self.root, "xlsx")


if __name__ == "__main__":
    unittest.main()
