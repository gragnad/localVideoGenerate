import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import h3_queue
from job_queue import atomic_write_json, read_json
from tests.test_h3_queue import H3QueueTests


class ProjectGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        helper = H3QueueTests()
        helper._write_project(self.root)
        helper._write_clip(self.root, scene_id="SCENE_001", clip_id="CLIP_003", sequence=3)
        self.compiled = ({"1": {"class_type": "LoadImage", "inputs": {"image": "placeholder"}}},
                         [{"node_id": "1", "input": "image"}],
                         {"workflow_profile_id": "workflow_h3", "workflow_filename": "h3.json"})
        self.data = {"project_id": "dragon", "adapter_id": "adapter_h3", "candidate_count": 2,
                     "width": 832, "height": 480, "seed": 42}

    def tearDown(self):
        self.temp.cleanup()

    def test_project_queues_every_scene_in_project_sequence_with_settings_and_lineage(self):
        with patch.object(h3_queue, "_compile_workflow", return_value=self.compiled):
            result = h3_queue.enqueue_project_candidate_sets(self.root, {**self.data, "queue_lane": "windows_candidate"})
        self.assertEqual((2, 3, 6), (result["scene_count"], result["clip_count"], result["job_count"]))
        requests = [read_json(self.root / "runtime/h3/jobs" / jid / "request.json") for jid in result["job_ids"]]
        self.assertEqual(["CLIP_001", "CLIP_001", "CLIP_002", "CLIP_002", "CLIP_003", "CLIP_003"], [r["source_clip_id"] for r in requests])
        self.assertEqual(["SCENE_001", "SCENE_001", "SCENE_002", "SCENE_002", "SCENE_001", "SCENE_001"], [r["source_scene_id"] for r in requests])
        for request in requests:
            self.assertEqual("dragon", request["source_project_id"])
            self.assertEqual("windows_candidate", request["queue_lane"])
            self.assertEqual((832, 480), (request["width"], request["height"]))
            self.assertIn("Dragon action", request["prompt"])
            self.assertEqual(1, len(request["references"]))
        self.assertEqual(3, len(result["candidate_set_ids"]))
        self.assertFalse((self.root / "runtime/h3/project_test_sets").exists())

    def test_local_project_queue_uses_local_lane_for_all_clips(self):
        with patch.object(h3_queue, "_compile_workflow", return_value=self.compiled):
            result = h3_queue.enqueue_project_candidate_sets(self.root, {**self.data, "queue_lane": "local_generation", "seed": -1})
        for jid in result["job_ids"]:
            request = read_json(self.root / "runtime/h3/jobs" / jid / "request.json")
            self.assertEqual("local_generation", request["queue_lane"])
            self.assertGreaterEqual(request["seed"], 0)

    def test_all_project_clips_are_preflighted_before_first_registration(self):
        with patch.object(h3_queue, "_compile_workflow", side_effect=[self.compiled, self.compiled, ValueError("bad last clip")]) as compile:
            with self.assertRaisesRegex(ValueError, "아무 후보군도 등록하지 않았습니다"):
                h3_queue.enqueue_project_candidate_sets(self.root, self.data)
        self.assertEqual(3, compile.call_count)
        self.assertFalse((self.root / "runtime/h3/candidate_sets").exists())

    def test_unready_blocked_empty_and_i2v_projects_do_not_queue(self):
        overview = h3_queue.h3_prompt_projects.project_clips(self.root, "dragon")
        with patch.object(h3_queue, "enqueue_candidate_set") as enqueue:
            for contents in [
                {**overview, "clips": [], "scenes": []},
                {**overview, "clips": [{**overview["clips"][0], "ready": False}]},
                {**overview, "generation_mode": "i2v"},
            ]:
                with self.subTest(contents=contents), patch.object(h3_queue.h3_prompt_projects, "project_clips", return_value=contents):
                    with self.assertRaises(ValueError):
                        h3_queue.enqueue_project_candidate_sets(self.root, self.data)
            manifest = self.root / "prompt_projects/dragon/manifest.json"
            atomic_write_json(manifest, {**read_json(manifest), "generation_blocked": True, "generation_block_reason": "blocked project"})
            with self.assertRaisesRegex(ValueError, "blocked project"):
                h3_queue.enqueue_project_candidate_sets(self.root, self.data)
            enqueue.assert_not_called()

    def test_scene_generation_still_queues_only_selected_scene(self):
        with patch.object(h3_queue, "_compile_workflow", return_value=self.compiled):
            result = h3_queue.enqueue_scene_candidate_sets(self.root, {**self.data, "scene_id": "SCENE_002"})
        self.assertEqual((1, 2), (result["clip_count"], result["job_count"]))
        for jid in result["job_ids"]:
            self.assertEqual("SCENE_002", read_json(self.root / "runtime/h3/jobs" / jid / "request.json")["source_scene_id"])

    def test_project_endpoint_and_backend_action_are_connected(self):
        base = Path(__file__).resolve().parents[1]
        self.assertIn("url.pathname === '/api/h3/projects/candidate-sets'", (base / "web/server.mjs").read_text())
        backend = (base / "ui_backend.py").read_text()
        self.assertIn('"queue_h3_project_candidates": queue_h3_project_candidates', backend)
        self.assertIn("return h3_queue.enqueue_project_candidate_sets(ROOT, data)", backend)
