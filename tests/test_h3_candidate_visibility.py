from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import h3_queue
from job_queue import atomic_write_json


class H3CandidateVisibilityTest(unittest.TestCase):
    def test_candidate_page_omits_explicitly_hidden_sets_and_filters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = h3_queue.roots(root)
            for set_id, project_id, hidden in (
                ("episode-set", "RaisingaDragonSeason01_EP03", False),
                ("asset-set", "__direct__", True),
            ):
                job_id = f"job-{set_id}"
                atomic_write_json(paths["jobs"] / job_id / "status.json", {
                    "status": "completed",
                })
                atomic_write_json(
                    paths["candidate_sets"] / set_id / "candidate_set.json",
                    {
                        "candidate_set_id": set_id,
                        "candidate_job_ids": [job_id],
                        "source_project_id": project_id,
                        "source_scene_id": "scene-1",
                        "source_clip_id": "clip-1",
                        "hidden_from_candidate_page": hidden,
                        "created_at": "2026-09-16T00:00:00+09:00",
                    },
                )

            page = h3_queue.candidate_page(root, {"page": 1, "page_size": 10})

            self.assertEqual(1, page["pagination"]["total"])
            self.assertEqual("episode-set", page["candidate_sets"][0]["candidate_set_id"])
            self.assertEqual(
                ["RaisingaDragonSeason01_EP03"],
                page["filters"]["projects"],
            )


if __name__ == "__main__":
    unittest.main()
