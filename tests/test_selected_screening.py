import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import h3_queue
import selected_screening as screening
from job_queue import atomic_write_json


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.scope = {"project_id": "EP_V1", "scene_id": ""}

    def tearDown(self):
        self.temp.cleanup()

    def state(self, **kwargs):
        return {**self.scope, "revision": 0, "order": ["j1", "j2"], "excluded": [], "issues": {"j1\nj2": "시선 불일치"}, **kwargs}

    def test_roundtrip_and_conflict(self):
        self.assertEqual(screening.load_state(self.root, self.scope)["revision"], 0)
        result = screening.save(self.root, self.state())
        self.assertEqual(result["revision"], 1)
        self.assertEqual(screening.load_state(self.root, self.scope)["issues"], {"j1\nj2": "시선 불일치"})
        self.assertTrue(screening.save(self.root, self.state())["conflict"])
        other_scene = {**self.scope, "scene_id": "S1"}
        self.assertEqual(screening.load_state(self.root, other_scene)["revision"], 0)

    def test_invalid_and_traversal_input(self):
        for kwargs in ({"order": ["../secret"]}, {"order": ["j1", "j1"]}, {"excluded": ["/tmp/x"]},
                       {"issues": {"j1": "x"}}, {"issues": {"j1\nj1": "x"}}, {"issues": {"j1\nj2": "x" * 4001}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                screening.save(self.root, self.state(**kwargs))
        # Scope names are hashed, never used as filesystem path components.
        screening.save(self.root, self.state(project_id="../../EP"))
        self.assertEqual(len(list((self.root / "runtime/selected_screening").glob("*.json"))), 1)

    def test_corrupt_state_not_overwritten(self):
        _, key = screening.scope(self.scope)
        path = screening.state_path(self.root, key)
        path.parent.mkdir(parents=True)
        path.write_text("broken", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            screening.save(self.root, self.state())
        self.assertEqual(path.read_text(), "broken")

    def test_complete_playlist_natural_order_duplicates_and_missing_media(self):
        paths = h3_queue.roots(self.root)
        candidates = []
        for n in range(1, 62):
            job = f"j{n}"
            candidate = {"candidate_set_id": f"set{n}", "source_project_id": "EP_V1", "source_scene_id": "S1",
                         "source_clip_id": f"C{n}", "selected_jobs": [{"job_id": job}], "candidate_job_ids": [job]}
            candidates.append(candidate)
            atomic_write_json(paths["jobs"] / job / "request.json", {"candidate_index": 1})
        duplicate = {**candidates[0], "candidate_set_id": "another", "candidate_job_ids": ["another"], "selected_jobs": [{"job_id": "another"}]}
        excluded_project = {**candidates[0], "source_project_id": "OTHER"}
        rerender = {**candidates[0], "render_purpose": "resolution_rerender"}
        def media(root, job):
            if job == "j2":
                raise FileNotFoundError()
            return Path("video.mp4")
        with patch.object(h3_queue, "reconcile", return_value=candidates[::-1] + [duplicate, excluded_project, rerender]), patch.object(h3_queue, "video_path", side_effect=media):
            result = screening.playlist(self.root, self.scope)
        self.assertEqual(len(result["items"]), 62)
        self.assertEqual([row["clip_id"] for row in result["items"][:4]], ["C1", "C1", "C2", "C3"])
        self.assertFalse(next(row for row in result["items"] if row["job_id"] == "j2")["available"])
        self.assertEqual(result["items"][-1]["clip_id"], "C61")
        self.assertEqual(screening.load_state(self.root, self.scope)["revision"], 0)


if __name__ == "__main__":
    unittest.main()
