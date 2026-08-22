from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import model_test_review_worker as worker
from job_queue import atomic_write_json, read_json, update_status


class CandidateReviewWorkerTest(unittest.TestCase):
    def test_completed_candidate_keeps_qwen_loaded_for_next_review(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_dir = root / "runtime/h3/jobs/job-1"
            queue_dir = root / "runtime/h3/candidate_review_queue/review-1"
            video = root / "candidate.mp4"
            video.write_bytes(b"video")
            atomic_write_json(
                job_dir / "request.json",
                {"candidate_set_id": "set-1", "prompt": "test", "references": []},
            )
            atomic_write_json(
                job_dir / "manifest.json", {"local_video_path": str(video)},
            )
            update_status(job_dir, "completed", stage="done")
            atomic_write_json(
                queue_dir / "request.json",
                {
                    "queue_name": "candidate_ai_review",
                    "generation_job_id": "job-1",
                },
            )
            update_status(queue_dir, "preparing", stage="claimed")
            report = {
                "overall_score": 4.0,
                "verdict": "usable",
                "revision_feedback_ko": "보완 의견",
            }

            with (
                mock.patch.object(worker, "ROOT", root),
                mock.patch.object(worker.h3_queue, "resolve_job_dir", return_value=job_dir),
                mock.patch.object(worker, "ensure_vllm_engine") as start_qwen,
                mock.patch.object(worker, "ensure_comfy_engine") as restore_comfy,
                mock.patch.object(
                    worker.candidate_ai_reviewer,
                    "review_candidate_video",
                    return_value=report,
                ),
            ):
                worker.process_candidate(queue_dir)

            start_qwen.assert_called_once_with()
            restore_comfy.assert_not_called()
            self.assertEqual(
                "completed", read_json(queue_dir / "status.json", {})["status"]
            )
            self.assertEqual(
                4.0,
                read_json(job_dir / "status.json", {})["candidate_ai_review_score"],
            )


if __name__ == "__main__":
    unittest.main()
