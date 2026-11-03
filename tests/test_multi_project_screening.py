import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import h3_queue
import selected_screening as screening
from job_queue import atomic_write_json


class MultiProjectScreeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_normalized_project_set_and_legacy_scope_compatibility(self):
        a, key = screening.scope({"project_ids": ["B", "A", "A"], "scene_id": ""})
        self.assertEqual(a, {"project_ids": ["A", "B"], "scene_id": ""})
        self.assertEqual(key, screening.scope({"project_ids": ["A", "B"]})[1])
        legacy, old_key = screening.scope({"project_id": "A", "scene_id": "S1"})
        self.assertEqual(old_key, hashlib.sha256(b"A\0S1").hexdigest())
        self.assertEqual((legacy, old_key), screening.scope({"project_ids": ["A"], "scene_id": "S1"}))
        for value in [[], "A,B", [""], [None], ["A", "\0"], [5]]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                screening.scope({"project_ids": value})

    def test_union_all_candidates_same_clip_source_labels_natural_order(self):
        paths = h3_queue.roots(self.root)
        candidates = []
        for project in ["A", "B", "C"]:
            for n in range(1, 63):
                job = f"{project}-{n}"
                candidates.append({"candidate_set_id": "set-" + job, "source_project_id": project,
                                   "source_scene_id": "S2" if project == "A" else "S1",
                                   "source_clip_id": f"C{n}", "candidate_job_ids": [job],
                                   "selected_jobs": [{"job_id": job}]})
                atomic_write_json(paths["jobs"] / job / "request.json", {"candidate_index": 1})
        duplicate = {**candidates[0], "candidate_set_id": "alternate",
                     "candidate_job_ids": ["A-1-alt"], "selected_jobs": [{"job_id": "A-1-alt"}]}
        atomic_write_json(paths["jobs"] / "A-1-alt" / "request.json", {"candidate_index": 2})
        def media(root, job):
            if job == "B-2":
                raise FileNotFoundError()
            return Path("video.mp4")
        with patch.object(h3_queue, "reconcile", return_value=candidates[::-1] + [duplicate]), patch.object(h3_queue, "video_path", side_effect=media):
            result = screening.playlist(self.root, {"project_ids": ["A", "B"]})
        items = result["items"]
        self.assertEqual(125, len(items))
        self.assertEqual(["C1", "C1", "C1", "C2", "C2", "C3"], [row["clip_id"] for row in items[:6]])
        self.assertEqual({"A", "B"}, {row["project_id"] for row in items})
        self.assertEqual({"A-1", "A-1-alt", "B-1"}, {row["job_id"] for row in items if row["clip_id"] == "C1"})
        self.assertFalse(next(row for row in items if row["job_id"] == "B-2")["available"])

    def test_multi_review_roundtrip_order_independent_conflicts_and_single_isolation(self):
        state = {"project_ids": ["B", "A"], "scene_id": "", "revision": 0,
                 "order": ["A-1", "B-1"], "excluded": ["B-1"], "issues": {"A-1\nB-1": "cross-project boundary"}}
        saved = screening.save(self.root, state)
        self.assertEqual(1, saved["revision"])
        loaded = screening.load_state(self.root, {"project_ids": ["A", "B", "A"]})
        self.assertEqual(state["order"], loaded["order"])
        self.assertEqual(state["excluded"], loaded["excluded"])
        self.assertEqual(state["issues"], loaded["issues"])
        self.assertTrue(screening.save(self.root, state)["conflict"])
        self.assertEqual(0, screening.load_state(self.root, {"project_id": "A"})["revision"])
        self.assertEqual(0, screening.load_state(self.root, {"project_ids": ["A", "C"]})["revision"])
