import tempfile
import unittest
from pathlib import Path

from candidate_set_status import reconcile_candidate_set
from job_queue import atomic_write_json


class CandidateSetStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_set(self, status="generating"):
        path = self.root / "runtime/candidate_sets/cset_test/candidate_set.json"
        atomic_write_json(
            path,
            {
                "candidate_set_id": "cset_test",
                "status": status,
                "candidate_job_ids": ["job_a", "job_b", "job_c"],
            },
        )
        return path

    def write_job(self, job_id, status):
        atomic_write_json(
            self.root / "jobs" / job_id / "status.json",
            {
                "status": status,
                "updated_at": f"2026-07-29T00:00:0{len(job_id)}+09:00",
            },
        )

    def test_completed_candidates_wait_for_selection(self):
        self.write_set()
        self.write_job("job_a", "completed")
        self.write_job("job_b", "completed")
        self.write_job("job_c", "failed")

        payload = reconcile_candidate_set(self.root, "cset_test")

        self.assertEqual(payload["status"], "awaiting_candidate_selection")
        self.assertTrue(payload["candidate_jobs_terminal"])
        self.assertEqual(payload["completed_candidate_count"], 2)
        self.assertEqual(payload["failed_candidate_count"], 1)
        self.assertIn("generation_completed_at", payload)

    def test_all_failed_candidates_mark_generation_failed(self):
        self.write_set()
        for job_id in ("job_a", "job_b", "job_c"):
            self.write_job(job_id, "failed")

        payload = reconcile_candidate_set(self.root, "cset_test")

        self.assertEqual(payload["status"], "generation_failed")
        self.assertEqual(payload["completed_candidate_count"], 0)

    def test_active_candidate_keeps_generating(self):
        self.write_set()
        self.write_job("job_a", "completed")
        self.write_job("job_b", "running")
        self.write_job("job_c", "queued")

        payload = reconcile_candidate_set(self.root, "cset_test")

        self.assertEqual(payload["status"], "generating")
        self.assertFalse(payload["candidate_jobs_terminal"])

    def test_selected_candidate_set_is_not_downgraded(self):
        path = self.write_set(status="selected")
        before = path.read_text(encoding="utf-8")
        for job_id in ("job_a", "job_b", "job_c"):
            self.write_job(job_id, "completed")

        payload = reconcile_candidate_set(self.root, "cset_test")

        self.assertEqual(payload["status"], "selected")
        self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
