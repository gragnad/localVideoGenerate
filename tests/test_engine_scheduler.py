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

    def test_external_review_lease_blocks_only_local_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("engine_scheduler.comfy_work_active", return_value=False):
                lease_id, blocked = engine_scheduler.claim_external_review(
                    root,
                    os.getpid(),
                    "scene-director",
                )
            self.assertIsNotNone(lease_id)
            self.assertIsNone(blocked)
            self.assertTrue(engine_scheduler.external_review_active(root))

            windows = self._queue(
                root,
                "runtime/h3/jobs",
                "candidate_1",
                queue_lane="windows_candidate",
                candidate_set_id="set_1",
            )
            claimed_windows, windows_blocked = engine_scheduler.claim_generation(
                root,
                os.getpid(),
                lane="windows_candidate",
            )
            self.assertEqual(windows, claimed_windows)
            self.assertIsNone(windows_blocked)

            local = self._queue(
                root,
                "runtime/h3/jobs",
                "local_1",
                queue_lane="local_generation",
            )
            claimed_local, generation_blocked = engine_scheduler.claim_generation(
                root,
                os.getpid(),
                lane="local_generation",
            )
            self.assertIsNone(claimed_local)
            self.assertEqual("review", generation_blocked)
            self.assertEqual("queued", read_json(local / "status.json")["status"])

            engine_scheduler.release_external_review(root, str(lease_id))
            self.assertFalse(engine_scheduler.external_review_active(root))


    def test_external_review_lease_waits_for_pending_local_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._queue(
                root,
                "runtime/h3/jobs",
                "local_1",
                queue_lane="local_generation",
            )
            with patch("engine_scheduler.comfy_work_active", return_value=False):
                lease_id, blocked = engine_scheduler.claim_external_review(
                    root,
                    os.getpid(),
                    "scene-director",
                )
            self.assertIsNone(lease_id)
            self.assertEqual("generation", blocked)
            self.assertFalse(engine_scheduler.external_review_active(root))

    def test_stale_review_queue_directories_do_not_block_local_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in (
                "runtime/model_test_review_queue",
                "runtime/h3/candidate_review_queue",
            ):
                stale = self._queue(root, relative, "review_1")
                update_status(stale, "reviewing", stage="reviewing")
            local = self._queue(
                root,
                "runtime/h3/jobs",
                "local_1",
                queue_lane="local_generation",
            )
            claimed_local, blocked = engine_scheduler.claim_generation(
                root,
                os.getpid(),
                lane="local_generation",
            )
            self.assertEqual(local, claimed_local)
            self.assertIsNone(blocked)


if __name__ == "__main__":
    unittest.main()
