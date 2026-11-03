import tempfile
import unittest
from pathlib import Path
import h3_queue
from job_queue import atomic_write_json, read_json
from tests import test_h3_server_paging as paging


class ResultRerenderFilterTests(unittest.TestCase):
    _candidate = paging.H3ServerPagingTest._candidate

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = h3_queue.roots(self.root)
        for index in range(16):
            sid, jid = self._candidate(index, selected=True)
            for number in range(index % 8):
                self.rerender(sid, jid, str(number), ["queued", "running", "completed"][number % 3])
            self.rerender(sid, jid, "failed", "failed")
            self.rerender(sid, jid, "cancelled", "cancelled")

    def tearDown(self):
        self.temp.cleanup()

    def rerender(self, source_set, source_job, suffix, status):
        sid = source_set + "-rerender-" + suffix
        jid = sid + "-job"
        atomic_write_json(self.paths["candidate_sets"] / sid / "candidate_set.json", {
            "candidate_set_id": sid, "candidate_job_ids": [jid], "render_purpose": "resolution_rerender",
            "source_candidate_set_id": source_set, "source_selected_job_id": source_job,
        })
        atomic_write_json(self.paths["jobs"] / jid / "request.json", {
            "job_id": jid, "candidate_set_id": sid, "job_type": "h3_r2v_generate",
            "render_purpose": "resolution_rerender", "source_selected_job_id": source_job,
        })
        atomic_write_json(self.paths["jobs"] / jid / "status.json", {"status": status})

    def ids(self, result):
        return {s["selected_job_id"] for s in result["candidate_sets"] if s.get("render_purpose") != "resolution_rerender"}

    def test_buckets_include_pending_and_completed_but_not_failed_or_cancelled(self):
        for count in [str(i) for i in range(6)] + ["n", ""]:
            with self.subTest(count=count):
                expected = {f"job-{i:02d}" for i in range(16) if not count or (i % 8 >= 6 if count == "n" else i % 8 == int(count))}
                result = h3_queue.results_page(self.root, {"rerender_count": count, "page_size": 50})
                self.assertEqual(expected, self.ids(result))
                self.assertEqual(len(expected), result["pagination"]["total"])
                self.assertEqual(len(expected), result["pagination"]["total_sets"])

    def test_filter_combines_with_project_scene_and_is_applied_before_paging(self):
        result = h3_queue.results_page(self.root, {"rerender_count": "0", "project_id": "project-a", "scene_id": "scene-2", "page_size": 1, "page": 2})
        self.assertEqual({"job-00"}, self.ids(result))
        self.assertEqual(2, result["pagination"]["total"])
        self.assertEqual(2, result["pagination"]["total_pages"])
        self.assertEqual(2, result["pagination"]["page"])
        empty = h3_queue.results_page(self.root, {"rerender_count": "5", "project_id": "project-a", "scene_id": "scene-2"})
        self.assertEqual(set(), self.ids(empty))
        self.assertEqual(0, empty["pagination"]["total"])

    def test_counts_belong_to_selected_candidate_not_sibling_or_upscale(self):
        sid, source = "set-00", "job-00"
        sibling = "selected-sibling"
        atomic_write_json(self.paths["jobs"] / sibling / "request.json", {"job_id": sibling, "candidate_set_id": sid})
        atomic_write_json(self.paths["jobs"] / sibling / "status.json", {"status": "completed"})
        file = self.paths["candidate_sets"] / sid / "candidate_set.json"
        payload = read_json(file, {})
        payload["candidate_job_ids"].append(sibling)
        payload["selected_jobs"].append({"job_id": sibling})
        atomic_write_json(file, payload)
        self.rerender(sid, sibling, "sibling", "completed")
        atomic_write_json(self.paths["jobs"] / "upscale" / "request.json", {"job_id": "upscale", "job_type": "h3_video_upscale", "source_selected_job_id": source})
        atomic_write_json(self.paths["jobs"] / "upscale" / "status.json", {"status": "completed"})
        zero = h3_queue.results_page(self.root, {"rerender_count": "0", "page_size": 50})
        one = h3_queue.results_page(self.root, {"rerender_count": "1", "page_size": 50})
        self.assertIn(source, self.ids(zero))
        self.assertNotIn(sibling, self.ids(zero))
        self.assertIn(sibling, self.ids(one))
