import tempfile
import unittest
from pathlib import Path

import h3_queue
from job_queue import atomic_write_json


def build_fixture(root):
    paths = h3_queue.roots(root)
    rows = []
    for index in range(24):
        project = "Dragon_EP07B1_V1" if index % 2 == 0 else "Dragon_EP07B2_V4"
        rows.append((project, f"clip-{24-index}", True))
    rows += [("Dragon_EP08_V1", "clip-1", True), ("custom", "clip-1", True),
             ("__direct__", "clip-1", True), ("Dragon_EP07B1_V1", "unselected", False)]
    atomic_write_json(root / "prompt_projects/custom/manifest.json", {"title": "용 EP09-A 검토"})
    for index, (project, clip, selected) in enumerate(rows):
        sid, jid = f"s{index:02}", f"j{index:02}"
        stamp = f"2026-11-02T00:{index:02}:00Z"
        request = {"job_id": jid, "job_type": "h3_r2v_generate", "candidate_set_id": sid,
                   "source_project_id": project, "source_scene_id": "S1", "source_clip_id": clip,
                   "candidate_index": 1, "width": 608, "height": 352}
        atomic_write_json(paths["jobs"] / jid / "request.json", request)
        atomic_write_json(paths["jobs"] / jid / "status.json", {"status": "completed", "updated_at": stamp})
        payload = {"candidate_set_id": sid, "candidate_job_ids": [jid], "source_project_id": project,
                   "source_scene_id": "S1", "source_clip_id": clip, "created_at": stamp, "updated_at": stamp}
        if selected:
            payload["selected_jobs"] = [{"job_id": jid, "selected_at": stamp}]
        atomic_write_json(paths["candidate_sets"] / sid / "candidate_set.json", payload)
    # Same clip, another project and multiple selected candidates must all survive aggregation.
    sid, jid = "s-extra", "j-extra"
    atomic_write_json(paths["jobs"] / jid / "request.json", {"job_id": jid, "candidate_set_id": sid,
        "source_project_id": "Dragon_EP07B2_V4", "source_scene_id": "S1", "source_clip_id": "clip-1", "candidate_index": 2})
    atomic_write_json(paths["jobs"] / jid / "status.json", {"status": "completed"})
    atomic_write_json(paths["candidate_sets"] / sid / "candidate_set.json", {"candidate_set_id": sid,
        "candidate_job_ids": [jid], "source_project_id": "Dragon_EP07B2_V4", "source_scene_id": "S1",
        "source_clip_id": "clip-1", "selected_jobs": [{"job_id": jid, "selected_at": "2026-11-01"}]})


class EpisodeFilterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        build_fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_filter_is_before_pagination_and_retains_deleted_project_sources(self):
        out = h3_queue.candidate_page(self.root, {"episode": "EP07", "page_size": 50})
        self.assertEqual(26, out["pagination"]["total"])
        self.assertTrue(all("_EP07" in row["source_project_id"] for row in out["candidate_sets"]))
        self.assertEqual(["EP07", "EP08", "EP09", "__other__"], out["filters"]["episodes"])
        self.assertEqual("EP09", out["filters"]["episodes_by_project"]["custom"])
        self.assertEqual(1, h3_queue.candidate_page(self.root, {"episode": "__other__"})["pagination"]["total"])

    def test_results_aggregate_all_versions_and_sort_naturally_before_paging(self):
        collected = []
        for page in (1, 2, 3):
            out = h3_queue.results_page(self.root, {"episode": "EP07", "sort_by": "name", "page": page, "page_size": 10})
            self.assertEqual(25, out["pagination"]["total"])
            self.assertEqual(2, out["pagination"]["total_projects"])
            collected += out["selection_order"]
            self.assertEqual("name", out["sort_by"])
        self.assertEqual(25, len(set(collected)))
        self.assertIn("j-extra", collected)
        # clip-1 duplicates, then clip-2..clip-24, not lexicographic clip-10 before clip-2.
        self.assertEqual(["j23", "j-extra", "j22", "j21"], collected[:4])
        self.assertEqual("j00", collected[-1])
        recent = h3_queue.results_page(self.root, {"episode": "EP07", "sort_by": "recent", "page_size": 50})
        self.assertEqual("j23", recent["selection_order"][0])
        self.assertEqual("j-extra", recent["selection_order"][-1])

    def test_project_scene_count_and_focus_combine_with_episode_and_sort(self):
        out = h3_queue.results_page(self.root, {"episode": "EP07", "project_id": "Dragon_EP07B1_V1", "scene_id": "S1", "rerender_count": "0", "sort_by": "name", "page_size": 1, "focus_job_id": "j00"})
        self.assertEqual(12, out["pagination"]["total"])
        self.assertEqual(12, out["pagination"]["page"])
        self.assertEqual(["j00"], out["selection_order"])
        self.assertEqual(0, h3_queue.results_page(self.root, {"episode": "EP08", "project_id": "Dragon_EP07B1_V1"})["pagination"]["total"])


if __name__ == "__main__":
    unittest.main()
