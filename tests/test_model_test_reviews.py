from __future__ import annotations

import unittest

import benchmark_jobs
import model_test_registry
import model_test_reviews
from job_queue import read_json
from tests.test_benchmark_jobs import BenchmarkJobsTest


class ModelTestReviewsTest(unittest.TestCase):
    def setUp(self):
        self.fixture = BenchmarkJobsTest(methodName="test_schema_v5_contains_session_batch_link")
        self.fixture.setUp()
        self.root = self.fixture.root
        self.session_id = self.fixture.session_id
        queued = benchmark_jobs.queue_session(self.root, self.session_id)
        self.job_id = queued["job_ids"][0]
        self.request = read_json(self.root / "jobs" / self.job_id / "request.json", {})
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


    def test_ai_review_is_separate_and_human_review_has_display_priority(self):
        ai = model_test_reviews.save_ai_review(
            self.root,
            self.run_id,
            self.review_payload(2.5),
            source_path="/tmp/benchmark_ai_review_report.json",
        )
        self.assertEqual(ai["review"]["reviewer_kind"], "ai_benchmark")
        results = model_test_reviews.session_results(self.root, self.session_id)
        target = next(item for item in results["runs"] if item["run_id"] == self.run_id)
        self.assertEqual(target["review"]["reviewer_kind"], "ai_benchmark")
        self.assertEqual(target["ai_review_status"], "completed")
        self.assertEqual(results["ai_review_summary"]["completed"], 1)
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
