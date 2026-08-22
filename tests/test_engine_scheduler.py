from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import engine_scheduler
from job_queue import atomic_write_json, read_json, update_status


class EngineSchedulerTest(unittest.TestCase):
    def _queue(
        self,
        root: Path,
        relative: str,
        name: str,
        **request_fields: object,
    ) -> Path:
        directory = root / relative / name
        directory.mkdir(parents=True)
        atomic_write_json(
            directory / "request.json",
            {
                "created_at": "2026-08-08T00:00:00+09:00",
                **request_fields,
            },
        )
        update_status(directory, "queued", stage="waiting")
        return directory

    def test_review_waits_until_entire_h3_queue_is_terminal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generation = self._queue(root, "runtime/h3/jobs", "h3job_1")
            review = self._queue(
                root,
                "runtime/model_test_review_queue",
                "review_1",
            )

            with patch("engine_scheduler.comfy_work_active", return_value=False):
                claimed_review, blocked = engine_scheduler.claim_review(root, os.getpid())
            self.assertIsNone(claimed_review)
            self.assertEqual("generation", blocked)

            claimed_generation, blocked = engine_scheduler.claim_generation(
                root,
                os.getpid(),
            )
            self.assertEqual(generation, claimed_generation)
            self.assertIsNone(blocked)
            self.assertEqual(
                "preparing",
                read_json(generation / "status.json")["status"],
            )

            update_status(generation, "completed", stage="done")
            with patch("engine_scheduler.comfy_work_active", return_value=False):
                claimed_review, blocked = engine_scheduler.claim_review(root, os.getpid())
            self.assertEqual(review, claimed_review)
            self.assertIsNone(blocked)

    def test_new_h3_work_waits_while_review_is_active(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = self._queue(
                root,
                "runtime/model_test_review_queue",
                "review_1",
            )
            with patch("engine_scheduler.comfy_work_active", return_value=False):
                claimed_review, _ = engine_scheduler.claim_review(root, os.getpid())
            self.assertEqual(review, claimed_review)

            generation = self._queue(root, "runtime/h3/jobs", "h3job_1")
            claimed_generation, blocked = engine_scheduler.claim_generation(
                root,
                os.getpid(),
            )
            self.assertIsNone(claimed_generation)
            self.assertEqual("review", blocked)
            self.assertEqual(
                "queued",
                read_json(generation / "status.json")["status"],
            )

    def test_review_stays_queued_while_comfy_has_running_or_pending_work(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = self._queue(
                root,
                "runtime/model_test_review_queue",
                "review_1",
            )
            with patch("engine_scheduler.comfy_work_active", return_value=True):
                claimed_review, blocked = engine_scheduler.claim_review(
                    root,
                    os.getpid(),
                )
            self.assertIsNone(claimed_review)
            self.assertEqual("generation", blocked)
            self.assertEqual(
                "queued",
                read_json(review / "status.json")["status"],
            )

    def test_windows_candidate_and_local_generation_claim_independently(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = self._queue(
                root,
                "runtime/h3/jobs",
                "candidate_1",
                queue_lane="windows_candidate",
                candidate_set_id="set_1",
            )
            local = self._queue(
                root,
                "runtime/h3/jobs",
                "local_1",
                queue_lane="local_generation",
                test_queue_id="test_1",
            )

            claimed_candidate, candidate_blocked = engine_scheduler.claim_generation(
                root,
                os.getpid(),
                lane="windows_candidate",
            )
            claimed_local, local_blocked = engine_scheduler.claim_generation(
                root,
                os.getpid(),
                lane="local_generation",
            )

            self.assertEqual(candidate, claimed_candidate)
            self.assertEqual(local, claimed_local)
            self.assertIsNone(candidate_blocked)
            self.assertIsNone(local_blocked)
            self.assertEqual("preparing", read_json(candidate / "status.json")["status"])
            self.assertEqual("preparing", read_json(local / "status.json")["status"])

    def test_active_review_blocks_local_but_not_windows_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = self._queue(
                root,
                "runtime/model_test_review_queue",
                "review_1",
            )
            with patch("engine_scheduler.comfy_work_active", return_value=False):
                claimed_review, _ = engine_scheduler.claim_review(root, os.getpid())
            self.assertEqual(review, claimed_review)

            candidate = self._queue(
                root,
                "runtime/h3/jobs",
                "candidate_1",
                queue_lane="windows_candidate",
                candidate_set_id="set_1",
            )
            local = self._queue(
                root,
                "runtime/h3/jobs",
                "local_1",
                queue_lane="local_generation",
            )
            claimed_candidate, candidate_blocked = engine_scheduler.claim_generation(
                root,
                os.getpid(),
                lane="windows_candidate",
            )
            claimed_local, local_blocked = engine_scheduler.claim_generation(
                root,
                os.getpid(),
                lane="local_generation",
            )

            self.assertEqual(candidate, claimed_candidate)
            self.assertIsNone(candidate_blocked)
            self.assertIsNone(claimed_local)
            self.assertEqual("review", local_blocked)
            self.assertEqual("queued", read_json(local / "status.json")["status"])

    def test_review_ignores_pending_windows_candidate_queue(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._queue(
                root,
                "runtime/h3/jobs",
                "candidate_1",
                queue_lane="windows_candidate",
                candidate_set_id="set_1",
            )
            review = self._queue(
                root,
                "runtime/model_test_review_queue",
                "review_1",
            )
            with patch("engine_scheduler.comfy_work_active", return_value=False):
                claimed_review, blocked = engine_scheduler.claim_review(root, os.getpid())
            self.assertEqual(review, claimed_review)
            self.assertIsNone(blocked)

    def test_candidate_review_ignores_active_windows_candidate_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = self._queue(
                root,
                "runtime/h3/jobs",
                "candidate_1",
                queue_lane="windows_candidate",
                candidate_set_id="set_1",
            )
            claimed_candidate, _ = engine_scheduler.claim_generation(
                root, os.getpid(), lane="windows_candidate",
            )
            self.assertEqual(candidate, claimed_candidate)
            review = self._queue(
                root,
                "runtime/h3/candidate_review_queue",
                "candidate_review_1",
                queue_name="candidate_ai_review",
            )

            with patch("engine_scheduler.comfy_work_active", return_value=False):
                claimed_review, blocked = engine_scheduler.claim_review(root, os.getpid())
            self.assertEqual(review, claimed_review)
            self.assertIsNone(blocked)

    def test_active_candidate_review_blocks_only_local_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = self._queue(
                root,
                "runtime/h3/candidate_review_queue",
                "candidate_review_1",
                queue_name="candidate_ai_review",
            )
            with patch("engine_scheduler.comfy_work_active", return_value=False):
                claimed_review, _ = engine_scheduler.claim_review(root, os.getpid())
            self.assertEqual(review, claimed_review)

            windows = self._queue(
                root,
                "runtime/h3/jobs",
                "candidate_1",
                queue_lane="windows_candidate",
                candidate_set_id="set_1",
            )
            local = self._queue(
                root,
                "runtime/h3/jobs",
                "local_1",
                queue_lane="local_generation",
            )
            claimed_windows, windows_blocked = engine_scheduler.claim_generation(
                root, os.getpid(), lane="windows_candidate",
            )
            claimed_local, local_blocked = engine_scheduler.claim_generation(
                root, os.getpid(), lane="local_generation",
            )
            self.assertEqual(windows, claimed_windows)
            self.assertIsNone(windows_blocked)
            self.assertIsNone(claimed_local)
            self.assertEqual("review", local_blocked)
            self.assertEqual("queued", read_json(local / "status.json")["status"])

    def test_legacy_resolution_rerender_routes_to_local_lane(self):
        self.assertEqual(
            "local_generation",
            engine_scheduler.generation_lane(
                {
                    "job_type": "h3_r2v_generate",
                    "candidate_set_id": "rerender_set",
                    "render_purpose": "resolution_rerender",
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
