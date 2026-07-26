from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import seed_library
import ui_backend
from job_queue import atomic_write_json


class SeedLibraryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.jobs = self.root / "jobs"
        self.jobs.mkdir()
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        self.image = self.root / "source.png"
        self.image.write_bytes(b"fake-image")
        self.cr = self.workflows / "director-api.json"
        atomic_write_json(
            self.cr,
            {
                "1": {"class_type": "LTXDirector", "inputs": {}},
                "134": {"class_type": "LoraLoaderBlockWeight //Inspire", "inputs": {"seed": 831913303995591}},
            },
        )
        self.originals = {
            "ROOT": ui_backend.ROOT,
            "JOBS": ui_backend.JOBS,
            "WF_DIR": ui_backend.WF_DIR,
            "CR": ui_backend.CR,
            "CANDIDATE_SETS": ui_backend.CANDIDATE_SETS,
        }
        ui_backend.ROOT = self.root
        ui_backend.JOBS = self.jobs
        ui_backend.WF_DIR = self.workflows
        ui_backend.CR = self.cr
        ui_backend.CANDIDATE_SETS = self.root / "runtime/candidate_sets"

    def tearDown(self):
        for key, value in self.originals.items():
            setattr(ui_backend, key, value)
        self.temp.cleanup()

    def create_payload(self, seed=-1):
        return {
            "job_name": "seed_test",
            "fps": 24,
            "seed": seed,
            "width": 1536,
            "height": 864,
            "global_prompt": "ocean fantasy mir dialogue",
            "segments": [
                {
                    "upload_path": str(self.image),
                    "original_name": "source.png",
                    "prompt": "Young Mir swims through ocean ruins",
                    "seconds": 5,
                    "order": 1,
                }
            ],
        }

    def test_resolve_video_seed_random_for_negative_input(self):
        seed, raw, mode = ui_backend.resolve_video_seed({"seed": -1})
        self.assertEqual(raw, -1)
        self.assertEqual(mode, "random")
        self.assertGreaterEqual(seed, 0)

    def test_create_action_uses_random_seed_when_input_negative(self):
        with patch.object(ui_backend, "resolve_seed", return_value=424242):
            out = ui_backend.create_action(self.create_payload(seed=-1))
        request = json.loads((self.jobs / out["job_id"] / "request.json").read_text())
        self.assertEqual(request["seed"], 424242)
        self.assertEqual(request["seed_input"], -1)
        self.assertEqual(request["seed_mode"], "random")

    def test_create_candidates_use_independent_random_seeds(self):
        with patch.object(ui_backend, "resolve_seed", side_effect=[111, 222, 333]):
            ui_backend.create_candidates_action({**self.create_payload(seed=-1), "candidate_count": 3})
        seeds = sorted(
            int(json.loads((path / "request.json").read_text())["seed"])
            for path in self.jobs.iterdir()
            if path.is_dir()
        )
        self.assertEqual(seeds, [111, 222, 333])

    def test_like_and_recommend_by_prompt_tokens(self):
        created = ui_backend.create_action({**self.create_payload(seed=1001), "seed_input": 1001})
        job_id = created["job_id"]
        job_dir = self.jobs / job_id
        atomic_write_json(
            job_dir / "selected_workflow_api.json",
            {"134": {"class_type": "LoraLoaderBlockWeight //Inspire", "inputs": {"seed": 831913303995591}}},
        )
        request = json.loads((job_dir / "request.json").read_text())
        seed_library.like_seed_entry(self.root, job_id, request, job_dir)

        result = seed_library.recommend_seeds(
            self.root,
            {
                "global_prompt": "ocean fantasy mir dialogue",
                "segments": [{"prompt": "Young Mir swims through ocean ruins", "order": 1}],
                "fps": 24,
                "width": 1536,
                "height": 864,
            },
        )

        self.assertEqual(len(result["recommendations"]), 1)
        self.assertEqual(result["recommendations"][0]["video_noise_seed"], 1001)
        self.assertGreater(result["recommendations"][0]["score"], 0)

    def test_tokenize_prompt_deduplicates_stopwords(self):
        tokens = seed_library.tokenize_prompt("Project style ocean ocean mir")
        self.assertIn("ocean", tokens)
        self.assertIn("mir", tokens)
        self.assertNotIn("project", tokens)


if __name__ == "__main__":
    unittest.main()
