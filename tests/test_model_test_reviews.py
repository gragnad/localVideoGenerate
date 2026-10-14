from __future__ import annotations

import json
import unittest

import benchmark_jobs
import model_test_r2v
import model_test_registry
import model_test_reviews
from job_queue import read_json
from tests.test_benchmark_jobs import BenchmarkJobsTest


class ModelTestReviewsTest(unittest.TestCase):
    def setUp(self):
        self.fixture = BenchmarkJobsTest(methodName="test_schema_v10_has_no_batch_link_table")
        self.fixture.setUp()
        self.root = self.fixture.root
        self.session_id = self.fixture.session_id
        queued = benchmark_jobs.queue_session(self.root, self.session_id)
        self.job_id = queued["job_ids"][0]
        self.request = read_json(
            self.root / "runtime/h3/jobs" / self.job_id / "request.json", {}
        )
        benchmark_jobs.record_result(
            self.root,
            self.request,
            status="completed",
            generation_seconds=12.5,
            peak_gpu_memory_bytes=1024,
            peak_system_memory_bytes=2048,
            outputs=[{"filename": "sample.mp4", "subfolder": "model-tests", "type": "output"}],
        )
        self.run_id = self.request["run_id"]

    def tearDown(self):
        self.fixture.tearDown()

    def review_payload(self, score=4.0):
        return {
            "verdict": "needs_improvement",
            "positive_note": "정체성은 유지됨",
            "overall_note": "접촉 물리를 개선해야 함",
            "issues": [{
                "issue_id": "issue_contact",
                "category": "motion_physics",
                "subcategory": "ground_contact_missing",
                "severity": "major",
                "start_seconds": 1.2,
                "end_seconds": 2.8,
                "expected": "인물이 지면에 손을 짚는다.",
                "observed": "손이 지면 위에서 떠 있다.",
                "difference": "접촉과 하중 반응이 없다.",
                "cause_hypothesis": "접촉 조건이 약함",
                "suggestion": "손바닥 접촉과 체중 이동을 명시",
            }],
            "scores": {
                "prompt_adherence": score,
                "motion_physics": 2.0,
                "visual_quality": 3.5,
            },
        }

    def test_review_revisions_preserve_previous_rows(self):
        first = model_test_reviews.save_review(self.root, self.run_id, self.review_payload())
        second = model_test_reviews.save_review(self.root, self.run_id, self.review_payload(4.5))
        self.assertEqual(first["review"]["revision"], 1)
        self.assertEqual(second["review"]["revision"], 2)
        self.assertEqual(second["review"]["scores"]["prompt_adherence"], 4.5)
        self.assertEqual(second["review"]["issues"][0]["observed"], "손이 지면 위에서 떠 있다.")
        with model_test_registry.open_registry(self.root) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM reviews WHERE run_id=?", (self.run_id,)).fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM capability_scores").fetchone()[0], 6)

    def test_invalid_score_and_unknown_run_are_rejected(self):
        payload = self.review_payload()
        payload["scores"]["motion_physics"] = 5.1
        with self.assertRaisesRegex(ValueError, "0~5"):
            model_test_reviews.save_review(self.root, self.run_id, payload)
        with self.assertRaises(FileNotFoundError):
            model_test_reviews.run_review(self.root, "missing_run")

    def test_session_results_and_comparison_use_latest_review(self):
        model_test_reviews.save_review(self.root, self.run_id, self.review_payload(3.0))
        model_test_reviews.save_review(self.root, self.run_id, self.review_payload(5.0))
        results = model_test_reviews.session_results(self.root, self.session_id)
        target = next(item for item in results["runs"] if item["run_id"] == self.run_id)
        self.assertEqual(target["status"], "completed")
        self.assertEqual(target["review"]["revision"], 2)
        self.assertTrue(target["video_url"].endswith(f"/{self.job_id}/video"))
        comparison = model_test_reviews.comparison(self.root)
        group = comparison["groups"][0]
        self.assertEqual(group["reviewed_count"], 1)
        self.assertEqual(group["average_scores"]["prompt_adherence"], 5.0)
        self.assertEqual(group["verdict_counts"]["needs_improvement"], 1)

    def test_comparison_classifies_pint8_workflow_as_r2v(self):
        with model_test_registry.open_registry(self.root) as connection:
            connection.execute(
                "UPDATE workflow_profiles SET workflow_filename=? "
                "WHERE workflow_profile_id=?",
                (
                    model_test_r2v.R2V_PINT8_WORKFLOW_FILENAME,
                    self.request["workflow_profile_id"],
                ),
            )
        comparison = model_test_reviews.comparison(self.root)
        group = next(
            row
            for row in comparison["groups"]
            if row["workflow_profile_id"] == self.request["workflow_profile_id"]
        )
        self.assertEqual("h3_r2v_multi_reference", group["input_mode"])

    def test_comparison_keeps_sol_attn_parameter_variants_separate(self):
        first_settings = {"sol_attn": {"tau": 1.3}}
        second_settings = {"sol_attn": {"tau": 1.8}}
        with model_test_registry.open_registry(self.root) as connection:
            connection.execute(
                "UPDATE workflow_profiles SET workflow_filename=? "
                "WHERE workflow_profile_id=?",
                (
                    model_test_r2v.R2V_PINT8_WORKFLOW_FILENAME,
                    self.request["workflow_profile_id"],
                ),
            )
            connection.execute(
                "UPDATE test_sessions SET workflow_settings_json=? WHERE session_id=?",
                (json.dumps(first_settings), self.session_id),
            )
            connection.execute(
                """INSERT INTO test_sessions(
                       session_id,suite_id,model_id,workflow_profile_id,adapter_id,status,
                       repetitions,output_width,output_height,workflow_settings_json,
                       notes,created_at,updated_at
                   )
                   SELECT ?,suite_id,model_id,workflow_profile_id,adapter_id,'planned',
                          repetitions,output_width,output_height,?,notes,created_at,updated_at
                   FROM test_sessions WHERE session_id=?""",
                (
                    "test_sol_attn_variant",
                    json.dumps(second_settings),
                    self.session_id,
                ),
            )
        groups = [
            row for row in model_test_reviews.comparison(self.root)["groups"]
            if row["workflow_profile_id"] == self.request["workflow_profile_id"]
        ]
        self.assertEqual(2, len(groups))
        self.assertEqual(
            {1.3, 1.8},
            {row["workflow_settings"]["sol_attn"]["tau"] for row in groups},
        )
        self.assertEqual({"h3_r2v_multi_reference"}, {row["input_mode"] for row in groups})


    def test_archived_ai_review_is_read_only_and_human_review_has_display_priority(self):
        ai = model_test_reviews._save_review(
            self.root,
            self.run_id,
            self.review_payload(2.5),
            reviewer_kind="ai_benchmark",
            source_path="/tmp/benchmark_ai_review_report.json",
        )
        self.assertEqual(ai["review"]["reviewer_kind"], "ai_benchmark")
        results = model_test_reviews.session_results(self.root, self.session_id)
        target = next(item for item in results["runs"] if item["run_id"] == self.run_id)
        self.assertEqual(target["review"]["reviewer_kind"], "ai_benchmark")
        self.assertNotIn("ai_review_status", target)
        self.assertNotIn("ai_review_summary", results)
        self.assertNotIn("review_queue", results)
        comparison = model_test_reviews.comparison(self.root)
        self.assertEqual(
            comparison["groups"][0]["average_scores"]["prompt_adherence"], 2.5
        )

        human = model_test_reviews.save_review(
            self.root, self.run_id, self.review_payload(4.5)
        )
        self.assertEqual(human["review"]["reviewer_kind"], "human_benchmark")
        results = model_test_reviews.session_results(self.root, self.session_id)
        target = next(item for item in results["runs"] if item["run_id"] == self.run_id)
        self.assertEqual(target["ai_review"]["reviewer_kind"], "ai_benchmark")
        self.assertEqual(target["human_review"]["reviewer_kind"], "human_benchmark")
        self.assertEqual(target["review"]["reviewer_kind"], "human_benchmark")
        comparison = model_test_reviews.comparison(self.root)
        self.assertEqual(
            comparison["groups"][0]["average_scores"]["prompt_adherence"], 4.5
        )


if __name__ == "__main__":
    unittest.main()
