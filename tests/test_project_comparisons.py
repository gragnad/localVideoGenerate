import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import h3_queue
import project_comparisons as comparisons
from job_queue import atomic_write_json


class ProjectComparisonsTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.paths = h3_queue.roots(self.root)
        self.video = self.root / "test.mp4"
        self.video.write_bytes(b"test video")
        for name in ("left", "right", "third"):
            folder = self.paths["jobs"] / name
            atomic_write_json(folder / "request.json", {"job_id": name, "candidate_set_id": "set-" + name,
                "source_project_id": "EP07_V1" if name == "left" else "EP07_V2", "source_project_name": "Project " + name,
                "source_scene_id": "S1", "source_clip_id": "C01", "candidate_index": 2, "seed": 123})
            atomic_write_json(folder / "status.json", {"status": "completed"})
            atomic_write_json(folder / "manifest.json", {"local_video_path": str(self.video)})
            atomic_write_json(self.paths["candidate_sets"] / ("set-" + name) / "candidate_set.json",
                {"candidate_set_id": "set-" + name, "candidate_job_ids": [name], "selected_job_id": name,
                 "selected_jobs": [{"job_id": name}]})

    def payload(self, index=1, **extra):
        return {"comparison_id": f"comparison_{index:032x}", "left_job_id": "left", "right_job_id": "right", "winner": "left", **extra}

    def test_snapshot_authority_and_selection_is_not_modified(self):
        files = list(self.paths["candidate_sets"].glob("*/candidate_set.json"))
        original = {p: p.read_bytes() for p in files}
        result = comparisons.save(self.root, self.payload(project_name="forged", left={"project_id": "forged"}))
        self.assertEqual(result["left"]["project_id"], "EP07_V1")
        self.assertEqual(result["left"]["project_name"], "Project left")
        self.assertEqual(result["right"]["candidate_index"], 2)
        self.assertEqual(result["winner_job_id"], "left")
        self.assertTrue(result["created_at"])
        self.assertEqual(original, {p: p.read_bytes() for p in files})

    def test_retry_is_idempotent_and_conflicting_id_cannot_overwrite(self):
        saved = comparisons.save(self.root, self.payload())
        self.assertEqual(comparisons.save(self.root, self.payload()), saved)
        self.assertTrue(comparisons.save(self.root, self.payload(winner="right"))["conflict"])
        self.assertEqual(comparisons.listing(self.root, {})["pagination"]["total"], 1)

    def test_concurrent_same_request_creates_one_record(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(lambda _: comparisons.save(self.root, self.payload()), range(4)))
        self.assertTrue(all(row == rows[0] for row in rows))
        self.assertEqual(comparisons.listing(self.root, {})["pagination"]["total"], 1)

    def test_concurrent_different_decisions_preserve_all_history(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda i: comparisons.save(self.root, self.payload(i)), range(1, 5)))
        self.assertEqual(comparisons.listing(self.root, {})["pagination"]["total"], 4)

    def test_flip_vote_is_append_only_and_pagination_and_reversed_pair_work(self):
        first = comparisons.save(self.root, self.payload())
        second = comparisons.save(self.root, self.payload(2, winner="right"))
        comparisons.save(self.root, self.payload(3, right_job_id="third"))
        page = comparisons.listing(self.root, {"page_size": 2})
        self.assertEqual(page["pagination"]["total_pages"], 2)
        self.assertEqual(len(comparisons.listing(self.root, {"page": 2, "page_size": 2})["records"]), 1)
        pair = comparisons.listing(self.root, {"left_job_id": "right", "right_job_id": "left"})
        self.assertEqual(pair["records"], [second, first])

    def test_history_survives_renames_deletion_and_missing_media(self):
        saved = comparisons.save(self.root, self.payload())
        request = self.paths["jobs"] / "left/request.json"
        atomic_write_json(request, {"source_project_id": "renamed"})
        (self.paths["candidate_sets"] / "set-left/candidate_set.json").unlink()
        loaded = comparisons.load(self.root, {"comparison_id": saved["comparison_id"]})
        self.assertEqual(loaded["left"], saved["left"])
        self.assertTrue(loaded["available"]["left"])
        self.video.unlink()
        self.assertFalse(any(comparisons.load(self.root, saved)["available"].values()))
        self.assertEqual(comparisons.listing(self.root, {})["records"], [saved])
        self.assertEqual(comparisons.save(self.root, self.payload()), saved)

    def test_rejects_invalid_identical_incomplete_or_nonmember_jobs(self):
        for extra in ({"comparison_id": "../escape"}, {"left_job_id": "../escape"}, {"winner": "both"}, {"right_job_id": "left"}, {"right_job_id": "missing"}):
            with self.assertRaises((ValueError, FileNotFoundError)):
                comparisons.save(self.root, self.payload(**extra))
        atomic_write_json(self.paths["jobs"] / "right/status.json", {"status": "queued"})
        with self.assertRaises(ValueError): comparisons.save(self.root, self.payload())
        atomic_write_json(self.paths["jobs"] / "right/status.json", {"status": "completed"})
        atomic_write_json(self.paths["candidate_sets"] / "set-right/candidate_set.json", {"candidate_job_ids": []})
        with self.assertRaises(ValueError): comparisons.save(self.root, self.payload())
        self.assertEqual(comparisons.listing(self.root, {})["records"], [])

    def test_failure_and_corrupt_file_are_preserved_not_replaced(self):
        with mock.patch.object(comparisons, "atomic_write_json", side_effect=OSError("disk full")):
            with self.assertRaises(OSError): comparisons.save(self.root, self.payload())
        self.assertEqual(comparisons.listing(self.root, {})["records"], [])
        path = comparisons.record_path(self.root, self.payload()["comparison_id"])
        path.write_text("broken")
        with self.assertRaises(json.JSONDecodeError): comparisons.save(self.root, self.payload())
        self.assertEqual(path.read_text(), "broken")

    def test_missing_history_and_partial_pair(self):
        self.assertTrue(comparisons.load(self.root, self.payload())["not_found"])
        with self.assertRaises(ValueError): comparisons.listing(self.root, {"left_job_id": "left"})
