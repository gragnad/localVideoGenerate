from __future__ import annotations

import unittest
from unittest.mock import patch

import batch_manager
import benchmark_jobs
from job_queue import atomic_write_json, read_json, update_status
import model_test_registry
import model_test_reviews
import worker
from tests.test_benchmark_jobs import BenchmarkJobsTest


class BenchmarkQwenWorkerTest(unittest.TestCase):
    def setUp(self):
        self.fixture = BenchmarkJobsTest(methodName="test_schema_v5_contains_session_batch_link")
        self.fixture.setUp()
        self.root = self.fixture.root
        self.session_id = self.fixture.session_id
        queued = benchmark_jobs.queue_session(self.root, self.session_id)
        self.batch_id = queued["batch_id"]
        self.job_id = queued["job_ids"][0]
        self.job_dir = self.root / "jobs" / self.job_id
        self.request = read_json(self.job_dir / "request.json", {})
        benchmark_jobs.record_result(self.root, self.request, status="completed")
        update_status(self.job_dir, "completed")
        self.video_path = self.job_dir / "artifacts" / "review_source_video.mp4"
        self.video_path.parent.mkdir()
        self.video_path.write_bytes(b"unit-test-video")
        batch_manager.update_batch(
            self.root,
            self.batch_id,
            status="ready_for_ai_review",
            review_job_ids=[self.job_id],
            review_video_paths={self.job_id: str(self.video_path)},
            test_session_ids=[self.session_id],
        )

    def tearDown(self):
        self.fixture.tearDown()

    def test_worker_persists_qwen_review_and_completes_batch(self):
        report = {
            "review": {
                "verdict": "needs_improvement",
                "positive_note": "주 피사체는 유지된다.",
                "overall_note": "지면 접촉이 약하다.",
                "scores": {"prompt_adherence": 4, "motion_physics": 2},
                "issues": [{
                    "issue_id": "ai_issue_01",
                    "category": "motion_physics",
                    "subcategory": "ground_contact_missing",
                    "severity": "major",
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "expected": "발이 지면에 닿는다.",
                    "observed": "발이 떠 있다.",
                    "difference": "접촉이 없다.",
                    "cause_hypothesis": "접촉 조건 부족",
                    "suggestion": "Keep both feet planted.",
                }],
            },
            "confidence": 0.9,
            "event_checks": [],
            "model": "unit-qwen",
            "review_mode": "qwen_omni_direct_video_fixed_benchmark_rubric",
        }
        with (
            patch.object(worker, "ENGINE_ROOT", self.root),
            patch.object(worker, "JOBS_ROOT", self.root / "jobs"),
            patch.object(worker, "ensure_vllm_engine", return_value={}),
            patch.object(worker, "engine_snapshot", return_value={"active_engine": "vllm"}),
            patch.object(
                worker.model_test_ai_reviewer,
                "review_benchmark_video",
                return_value=report,
            ),
            patch.object(worker, "restore_comfy_after_review", side_effect=lambda batch, outcome: batch),
        ):
            result = worker.run_model_benchmark_ai_review_batch(
                batch_manager.load_batch(self.root, self.batch_id)
            )
        self.assertEqual(result["status"], "benchmark_review_completed")
        self.assertEqual(result["benchmark_ai_review_count"], 1)
        self.assertTrue((self.job_dir / "benchmark_ai_review_report.json").is_file())
        job_status = read_json(self.job_dir / "status.json", {})
        self.assertEqual(job_status["ai_review_status"], "completed")
        self.assertEqual(job_status["ai_review_batch_id"], self.batch_id)
        saved = model_test_reviews.session_results(self.root, self.session_id)
        target = next(item for item in saved["runs"] if item["run_id"] == self.request["run_id"])
        self.assertEqual(target["ai_review"]["reviewer_kind"], "ai_benchmark")
        self.assertEqual(target["review"]["scores"]["motion_physics"], 2.0)
        with model_test_registry.open_registry(self.root) as connection:
            session_status = connection.execute(
                "SELECT status FROM test_sessions WHERE session_id=?", (self.session_id,)
            ).fetchone()[0]
        self.assertEqual(session_status, "review_completed")

    def test_r2v_request_uses_separate_reviewer_and_review_lineage(self):
        self.request["benchmark_contract"]["input_mode"] = "h3_r2v_multi_reference"
        atomic_write_json(self.job_dir / "request.json", self.request)
        report = {
            "review": {
                "verdict": "acceptable",
                "positive_note": "참조 정체성과 사건이 유지된다.",
                "overall_note": "R2V 기준 통과",
                "scores": {"reference_adherence": 5, "event_execution": 5},
                "issues": [],
            },
            "confidence": 0.92,
            "reference_checks": [],
            "event_checks": [],
            "forbidden_checks": [],
            "enforcement": {"rubric_version": "r2v_reference_grounded_v1"},
            "model": "unit-qwen",
            "review_mode": "qwen_omni_r2v_reference_grounded_v1",
            "rubric_version": "r2v_reference_grounded_v1",
        }
        with (
            patch.object(worker, "ENGINE_ROOT", self.root),
            patch.object(worker, "JOBS_ROOT", self.root / "jobs"),
            patch.object(worker, "ensure_vllm_engine", return_value={}),
            patch.object(worker, "engine_snapshot", return_value={"active_engine": "vllm"}),
            patch.object(
                worker.model_test_r2v_ai_reviewer,
                "review_benchmark_video",
                return_value=report,
            ) as r2v_review,
            patch.object(
                worker.model_test_ai_reviewer,
                "review_benchmark_video",
            ) as i2v_review,
            patch.object(worker, "restore_comfy_after_review", side_effect=lambda batch, outcome: batch),
        ):
            worker.run_model_benchmark_ai_review_batch(
                batch_manager.load_batch(self.root, self.batch_id)
            )
        r2v_review.assert_called_once()
        i2v_review.assert_not_called()
        with model_test_registry.open_registry(self.root) as connection:
            kind = connection.execute(
                "SELECT reviewer_kind FROM reviews WHERE run_id=?",
                (self.request["run_id"],),
            ).fetchone()[0]
        self.assertEqual(kind, "ai_benchmark_r2v")


    def test_empty_stale_open_batch_does_not_block_benchmark_finalization(self):
        stale = batch_manager.create_new_open_batch(
            self.root,
            {"auto_review": False, "batch_idle_grace_seconds": 1},
        )
        batch_manager.update_batch(
            self.root,
            stale["batch_id"],
            created_at="2000-01-01T00:00:00+09:00",
        )
        current = batch_manager.update_batch(
            self.root,
            self.batch_id,
            status="open",
            registration_closed=True,
            idle_since_epoch=0,
            stage="batch_idle_grace",
        )
        for job_id in current["benchmark_job_ids"]:
            update_status(self.root / "jobs" / job_id, "completed")
        with (
            patch.object(worker, "ENGINE_ROOT", self.root),
            patch.object(worker, "JOBS_ROOT", self.root / "jobs"),
            patch.object(worker, "get_comfy_queue_state", return_value=(True, 0, 0, None)),
        ):
            result = worker.maybe_finalize_open_batch()
        self.assertEqual(result["batch_id"], self.batch_id)
        self.assertEqual(result["status"], "ready_for_review_preparation")
        stale_after = batch_manager.load_batch(self.root, stale["batch_id"])
        self.assertEqual(stale_after["status"], "open")


if __name__ == "__main__":
    unittest.main()
