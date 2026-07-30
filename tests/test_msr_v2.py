from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import batch_manager
import ui_backend
from comfy_workflow_export import graph_to_api
from job_queue import update_status
from workflow_builder import build_msr_v2_workflow


OFFICIAL_GRAPH = Path.home() / "ai-workspace/apps/ComfyUI/user/default/workflows/LTX-2.3_MSR_sample_workflow_V2+multiGuide.json"


class MSRV2Test(unittest.TestCase):
    def test_official_graph_builds_four_references_at_fixed_24fps_without_duration_cap(self):
        graph = json.loads(OFFICIAL_GRAPH.read_text(encoding="utf-8"))
        for node in graph["nodes"]:
            if int(node.get("id") or 0) in {196, 201}:
                node["mode"] = 0
        template = graph_to_api(graph)
        workflow, summary = build_msr_v2_workflow(
            template=template,
            references=[{"name": f"ref-{i}.png", "subfolder": "msr"} for i in range(1, 5)],
            background={"name": "background.png", "subfolder": "msr"},
            relay_segments=[
                {"prompt": "첫 장면에서 천천히 접근한다.", "seconds": 120},
                {"prompt": "두 번째 장면에서 한국어로 말한다.", "seconds": 80},
            ],
            global_prompt="네 인물의 외형과 의상을 유지한다.",
            seed=123,
            filename_prefix="tests/msr",
            width=1280,
            height=704,
        )
        self.assertEqual(summary["fps"], 24)
        self.assertGreater(summary["total_seconds"], 199)
        self.assertEqual(summary["reference_count"], 4)
        self.assertEqual(workflow["129"]["inputs"]["value"], 24)
        self.assertEqual(workflow["172"]["inputs"]["fps"], 24)
        self.assertEqual(workflow["7"]["inputs"]["frame_rate"], 24)
        self.assertEqual(workflow["22"]["inputs"]["frame_rate"], 24)
        self.assertEqual(workflow["190"]["inputs"]["frame_count"], "65")
        self.assertEqual(workflow["180"]["inputs"]["local_prompts"].count(" | "), 1)
        self.assertIn("196", workflow)
        self.assertIn("201", workflow)
        self.assertEqual(workflow["194"]["inputs"]["image"], "msr/background.png")
        self.assertNotIn("211", workflow)
        self.assertEqual(workflow["207"]["inputs"]["vae"], ["3", 2])

    def test_candidate_registration_enforces_24fps_and_independent_batch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            jobs = root / "jobs"
            jobs.mkdir()
            image = root / "image.png"
            image.write_bytes(b"fake-image")
            originals = {
                "ROOT": ui_backend.ROOT,
                "JOBS": ui_backend.JOBS,
                "CANDIDATE_SETS": ui_backend.CANDIDATE_SETS,
                "COMPOSITIONS": ui_backend.COMPOSITIONS,
                "MSR_GRAPH": ui_backend.MSR_GRAPH,
            }
            try:
                ui_backend.ROOT = root
                ui_backend.JOBS = jobs
                ui_backend.CANDIDATE_SETS = root / "runtime/candidate_sets"
                ui_backend.COMPOSITIONS = root / "runtime/compositions"
                ui_backend.MSR_GRAPH = OFFICIAL_GRAPH
                payload = ui_backend.create_msr_candidates_action({
                    "candidate_count": 2,
                    "job_name": "msr-test",
                    "fps": 50,
                    "seed": 10,
                    "width": 1280,
                    "height": 704,
                    "global_prompt": "외형 유지",
                    "references": [{"upload_path": str(image), "original_name": "one.png", "description": "그림 1"}],
                    "background": {"upload_path": str(image), "original_name": "bg.png", "description": "배경"},
                    "relay_segments": [{"prompt": "긴 장면", "seconds": 180}],
                })
                self.assertEqual(payload["generation_mode"], "msr_v2")
                self.assertEqual(len(payload["candidate_job_ids"]), 2)
                batch = batch_manager.load_batch(root, payload["batch_id"])
                self.assertTrue(batch["registration_closed"])
                for job_id in payload["candidate_job_ids"]:
                    request = json.loads((jobs / job_id / "request.json").read_text())
                    self.assertEqual(request["fps"], 24)
                    self.assertEqual(request["workflow_kind"], "msr_v2")
                    self.assertEqual(request["relay_segments"][0]["seconds"], 180)
                    self.assertEqual(request["msr_reference_frame_count"], 65)
                    update_status(jobs / job_id, "failed", stage="실패", message="validation failed")
                failed_batch = batch_manager.mark_batch_generation_complete(root, batch)
                self.assertEqual(failed_batch["status"], "failed")
                self.assertEqual(failed_batch["stage"], "candidate_generation_failed")
            finally:
                for key, value in originals.items():
                    setattr(ui_backend, key, value)


if __name__ == "__main__":
    unittest.main()
