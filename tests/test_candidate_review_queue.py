from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import candidate_review_queue
from job_queue import atomic_write_json, read_json, update_status


class CandidateReviewQueueTest(unittest.TestCase):
    def _candidate_set(self, root: Path, set_id: str, job_ids: list[str]) -> None:
        directory = root / "runtime/h3/candidate_sets" / set_id
        atomic_write_json(
            directory / "candidate_set.json",
            {
                "candidate_set_id": set_id,
                "candidate_job_ids": job_ids,
                "status": "generating",
                "render_purpose": "candidate_generation",
            },
        )

    def _completed_job(
        self, root: Path, set_id: str, job_id: str, index: int,
    ) -> Path:
        directory = root / "runtime/h3/jobs" / job_id
        video = root / "videos" / f"{job_id}.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"candidate-video")
        atomic_write_json(
            directory / "request.json",
            {
                "candidate_set_id": set_id,
                "candidate_index": index,
                "prompt_variant_id": f"variant-{index}",
                "render_purpose": "candidate_generation",
                "prompt": f"candidate prompt {index}",
            },
        )
        atomic_write_json(
            directory / "manifest.json",
            {
                "local_video_path": str(video),
                "output_sha256": f"{index:064x}",
            },
        )
        update_status(directory, "completed", stage="done")
        return directory

    def test_toggle_queues_existing_and_new_completed_candidates_once(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._candidate_set(root, "set-1", ["job-1", "job-2"])
            self._completed_job(root, "set-1", "job-1", 1)

            enabled = candidate_review_queue.set_enabled(root, True)
            self.assertTrue(enabled["enabled"])
            self.assertEqual(1, enabled["queued_count"])
            self.assertEqual(1, len(candidate_review_queue.list_reviews(root)))

            repeated = candidate_review_queue.sync_enabled_reviews(root)
            self.assertEqual(0, repeated["queued_count"])

            self._completed_job(root, "set-1", "job-2", 2)
            new_video = candidate_review_queue.sync_enabled_reviews(root)
            self.assertEqual(1, new_video["queued_count"])
            self.assertEqual(2, len(candidate_review_queue.list_reviews(root)))

    def test_disable_cancels_waiting_candidate_reviews(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._candidate_set(root, "set-1", ["job-1"])
            self._completed_job(root, "set-1", "job-1", 1)
            candidate_review_queue.set_enabled(root, True)

            disabled = candidate_review_queue.set_enabled(root, False)
            review = candidate_review_queue.list_reviews(root)[0]
            self.assertFalse(disabled["enabled"])
            self.assertEqual(1, disabled["cancelled_count"])
            self.assertEqual("cancelled", review["status"]["status"])

            reenabled = candidate_review_queue.set_enabled(root, True)
            review = candidate_review_queue.list_reviews(root)[0]
            self.assertEqual(1, reenabled["queued_count"])
            self.assertEqual("queued", review["status"]["status"])
            self.assertFalse(review["status"]["cancel_requested"])

    def test_completed_legacy_review_is_hidden_and_reprocessed_with_current_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._candidate_set(root, "set-1", ["job-1"])
            self._completed_job(root, "set-1", "job-1", 1)
            legacy = candidate_review_queue.queue_root(root) / "legacy-review"
            atomic_write_json(
                legacy / "request.json",
                {
                    "review_id": "legacy-review",
                    "review_schema_version": "candidate_qwen_omni_v1",
                    "candidate_set_id": "set-1",
                    "generation_job_id": "job-1",
                    "output_sha256": f"{1:064x}",
                    "created_at": "2026-08-01T00:00:00+09:00",
                },
            )
            atomic_write_json(legacy / "report.json", {"model": "legacy"})
            update_status(legacy, "completed", stage="legacy complete")

            enabled = candidate_review_queue.set_enabled(root, True)

            self.assertEqual(1, enabled["queued_count"])
            self.assertEqual(1, len(candidate_review_queue.list_reviews(root)))
            current = candidate_review_queue.list_reviews(root)[0]
            self.assertEqual(
                candidate_review_queue.REVIEW_SCHEMA_VERSION,
                current["review_schema_version"],
            )
            all_reviews = candidate_review_queue.list_reviews(
                root, include_legacy=True,
            )
            self.assertEqual(2, len(all_reviews))
            self.assertTrue((legacy / "report.json").is_file())

    def test_summary_ranks_reports_and_finishes_when_generation_failures_are_terminal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._candidate_set(root, "set-1", ["job-1", "job-2", "job-3"])
            self._completed_job(root, "set-1", "job-1", 1)
            self._completed_job(root, "set-1", "job-2", 2)
            failed = root / "runtime/h3/jobs/job-3"
            atomic_write_json(
                failed / "request.json", {"candidate_set_id": "set-1"},
            )
            update_status(failed, "failed", stage="generation failed")
            candidate_review_queue.set_enabled(root, True)

            for row in candidate_review_queue.list_reviews(root):
                review_dir = candidate_review_queue.queue_root(root) / row["review_id"]
                score = 4.5 if row["generation_job_id"] == "job-2" else 3.0
                atomic_write_json(
                    review_dir / "report.json",
                    {
                        "overall_score": score,
                        "verdict": "usable",
                        "rubric_version": "candidate_story_continuity_v3",
                        "scores": {
                            "scenario_realization": score,
                            "incoming_continuity": 4.0,
                            "outgoing_continuity": 3.5,
                        },
                        "revision_feedback_ko": f"{row['generation_job_id']} 보완",
                    },
                )
                update_status(review_dir, "completed", stage="reviewed")

            summary = candidate_review_queue.candidate_set_summaries(root)[0]
            self.assertEqual("completed", summary["status"])
            self.assertEqual(3, summary["candidate_count"])
            self.assertEqual(2, summary["review_target_count"])
            self.assertEqual(2, summary["reviewed_count"])
            self.assertEqual("job-2", summary["ranking"][0]["job_id"])
            self.assertIn("연출 4.5", summary["ai_revision_feedback"])
            self.assertIn("이전 연결 4.0", summary["ai_revision_feedback"])
            self.assertIn("job-2 보완", summary["ai_revision_feedback"])

    def test_deleted_and_resolution_rerender_sets_are_not_queued(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for set_id, extra in (
                ("deleted", {"deleted": True}),
                ("rerender", {"render_purpose": "resolution_rerender"}),
            ):
                directory = root / "runtime/h3/candidate_sets" / set_id
                atomic_write_json(
                    directory / "candidate_set.json",
                    {
                        "candidate_set_id": set_id,
                        "candidate_job_ids": [f"{set_id}-job"],
                        **extra,
                    },
                )
                self._completed_job(root, set_id, f"{set_id}-job", 1)

            result = candidate_review_queue.set_enabled(root, True)
            self.assertEqual(0, result["queued_count"])
            self.assertEqual([], candidate_review_queue.list_reviews(root))

    def test_sync_retires_review_left_by_previously_deleted_set(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._candidate_set(root, "set-1", ["job-1"])
            self._completed_job(root, "set-1", "job-1", 1)
            candidate_review_queue.set_enabled(root, True)
            review = candidate_review_queue.list_reviews(root)[0]
            review_dir = (
                candidate_review_queue.queue_root(root) / review["review_id"]
            )
            candidate_set_path = (
                root / "runtime/h3/candidate_sets/set-1/candidate_set.json"
            )
            candidate_set = read_json(candidate_set_path)
            candidate_set.update(deleted=True, status="deleted")
            atomic_write_json(candidate_set_path, candidate_set)

            self.assertEqual([], candidate_review_queue.list_reviews(root))
            synced = candidate_review_queue.sync_enabled_reviews(root)

            self.assertEqual(0, synced["queued_count"])
            status = read_json(review_dir / "status.json")
            self.assertEqual("cancelled", status["status"])
            self.assertTrue(status["hidden_from_state"])

    def test_deleting_candidate_set_retires_only_unfinished_reviews(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._candidate_set(root, "set-1", ["job-1", "job-2", "job-3"])
            for index in range(1, 4):
                self._completed_job(root, "set-1", f"job-{index}", index)
            candidate_review_queue.set_enabled(root, True)
            reviews = {
                row["generation_job_id"]: row
                for row in candidate_review_queue.list_reviews(root)
            }
            completed_dir = (
                candidate_review_queue.queue_root(root) / reviews["job-1"]["review_id"]
            )
            active_dir = (
                candidate_review_queue.queue_root(root) / reviews["job-2"]["review_id"]
            )
            queued_dir = (
                candidate_review_queue.queue_root(root) / reviews["job-3"]["review_id"]
            )
            atomic_write_json(completed_dir / "report.json", {"overall_score": 4.0})
            update_status(completed_dir, "completed", stage="reviewed")
            update_status(active_dir, "reviewing", stage="reviewing", worker_pid=123)

            result = candidate_review_queue.retire_candidate_set_reviews(
                root, "set-1",
            )

            self.assertEqual(1, result["cancelled_count"])
            self.assertEqual(1, result["cancel_requested_count"])
            self.assertEqual(1, result["preserved_completed_count"])
            visible = candidate_review_queue.list_reviews(root)
            self.assertEqual(["job-1"], [row["generation_job_id"] for row in visible])
            self.assertEqual("completed", read_json(completed_dir / "status.json")["status"])
            active = read_json(active_dir / "status.json")
            self.assertEqual("cancel_requested", active["status"])
            self.assertTrue(active["cancel_requested"])
            self.assertTrue(active["hidden_from_state"])
            queued = read_json(queued_dir / "status.json")
            self.assertEqual("cancelled", queued["status"])
            self.assertTrue(queued["hidden_from_state"])
            self.assertEqual(
                3,
                len(candidate_review_queue.list_reviews(root, include_hidden=True)),
            )

            repeated = candidate_review_queue.retire_candidate_set_reviews(
                root, "set-1",
            )
            self.assertEqual(0, repeated["cancelled_count"])
            self.assertEqual(0, repeated["cancel_requested_count"])
            self.assertEqual(1, repeated["preserved_completed_count"])

    def test_orphaned_active_review_is_requeued_after_worker_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._candidate_set(root, "set-1", ["job-1"])
            self._completed_job(root, "set-1", "job-1", 1)
            candidate_review_queue.set_enabled(root, True)
            review = candidate_review_queue.list_reviews(root)[0]
            directory = candidate_review_queue.queue_root(root) / review["review_id"]
            update_status(
                directory,
                "reviewing",
                stage="interrupted",
                worker_pid=99_999_999,
                progress=0.15,
            )

            recovered = candidate_review_queue.recover_orphaned_reviews(
                root, os.getpid(),
            )
            status = read_json(directory / "status.json", {})
            self.assertEqual(1, recovered["recovered_count"])
            self.assertEqual("queued", status["status"])
            self.assertIsNone(status["worker_pid"])
            self.assertEqual(0, status["progress"])

    def test_worker_restart_retires_active_review_from_older_rubric(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._candidate_set(root, "set-1", ["job-1"])
            self._completed_job(root, "set-1", "job-1", 1)
            legacy = candidate_review_queue.queue_root(root) / "legacy-review"
            atomic_write_json(
                legacy / "request.json",
                {
                    "review_id": "legacy-review",
                    "review_schema_version": "candidate_qwen38_visual_v2",
                    "candidate_set_id": "set-1",
                    "generation_job_id": "job-1",
                },
            )
            update_status(
                legacy,
                "reviewing",
                stage="old rubric",
                worker_pid=99_999_999,
            )

            recovered = candidate_review_queue.recover_orphaned_reviews(
                root, os.getpid(),
            )
            status = read_json(legacy / "status.json", {})

            self.assertEqual(0, recovered["recovered_count"])
            self.assertEqual(1, recovered["cancelled_count"])
            self.assertEqual("cancelled", status["status"])
            self.assertIn("최신 기준", status["stage"])
            self.assertIsNone(status["worker_pid"])


if __name__ == "__main__":
    unittest.main()
