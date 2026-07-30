from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import msr_prompt_projects
import ui_backend
from comfy_workflow_export import graph_to_api
from msr_sequence_v2 import (
    MSRSequenceValidationError,
    PROMPT_STRATEGY,
    WORKFLOW,
    validate_submission,
)
from workflow_builder import build_msr_v2_workflow


OFFICIAL_GRAPH = Path.home() / "ai-workspace/apps/ComfyUI/user/default/workflows/LTX-2.3_MSR_sample_workflow_V2+multiGuide.json"


def submission(image: Path) -> dict:
    return {
        "workflow": WORKFLOW,
        "prompt_strategy": PROMPT_STRATEGY,
        "job_name": "continuity-test",
        "world_prompt": "Premium stylized 3D coastal fantasy animation.",
        "continuity_mode": "new_anchor",
        "references": [
            {
                "slot": 1,
                "role": "character_1",
                "description": "Lua, a human girl with messy brown hair and beige coastal clothes.",
                "upload_path": str(image),
                "original_name": "lua.png",
            },
            {
                "slot": 3,
                "role": "prop_3",
                "description": "Lua's fixed wooden fishing spear with a dark stone tip.",
                "upload_path": str(image),
                "original_name": "spear.png",
            },
        ],
        "anchor": {
            "description": "A wet breakwater with open movement space and shallow water below.",
            "upload_path": str(image),
            "original_name": "anchor.png",
        },
        "relay_segments": [
            {"prompt": "Lua enters and notices a fish below the breakwater.", "seconds": 8},
            {"prompt": "She misses, falls into the shallows and rises again.", "seconds": 12},
        ],
        "candidate_count": 2,
        "seed": 10,
        "width": 1280,
        "height": 704,
    }


class MSRSequenceV2Test(unittest.TestCase):
    def test_submission_compiles_small_msr_only_global_and_preserves_slots(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "image.png"
            image.write_bytes(b"image")
            result = validate_submission(submission(image))
        self.assertEqual(result["workflow"], WORKFLOW)
        self.assertEqual(result["prompt_strategy"], PROMPT_STRATEGY)
        self.assertFalse(result["director_prompt_inheritance"])
        self.assertEqual(result["requested_seconds"], 20)
        self.assertEqual([row["slot"] for row in result["references"]], [1, 3])
        self.assertIn("Picture 1 — Character", result["global_prompt"])
        self.assertIn("Picture 3 — Prop", result["global_prompt"])
        self.assertNotIn("CINEMATIC CAMERA BIBLE", result["global_prompt"])

    def test_more_than_twenty_seconds_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "image.png"
            image.write_bytes(b"image")
            data = submission(image)
            data["relay_segments"][1]["seconds"] = 12.1
            with self.assertRaisesRegex(MSRSequenceValidationError, "최대 20초"):
                validate_submission(data)

    def test_prop_slot_cannot_be_relabelled_as_character(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "image.png"
            image.write_bytes(b"image")
            data = submission(image)
            data["references"][1]["role"] = "character_3"
            with self.assertRaisesRegex(MSRSequenceValidationError, "prop_3"):
                validate_submission(data)

    def test_workflow_keeps_slot_three_when_slot_two_is_empty(self):
        graph = json.loads(OFFICIAL_GRAPH.read_text(encoding="utf-8"))
        for node in graph["nodes"]:
            if int(node.get("id") or 0) == 196:
                node["mode"] = 0
        template = graph_to_api(graph)
        workflow, summary = build_msr_v2_workflow(
            template=template,
            references=[
                {"slot": 1, "name": "lua.png", "subfolder": "msr"},
                {"slot": 3, "name": "spear.png", "subfolder": "msr"},
            ],
            background={"name": "anchor.png", "subfolder": "msr"},
            relay_segments=[
                {"prompt": "Lua enters.", "seconds": 8},
                {"prompt": "Lua falls and rises.", "seconds": 12},
            ],
            global_prompt="Short world and identity prompt.",
            seed=123,
            filename_prefix="tests/msr-sequence",
            width=1280,
            height=704,
            maximum_duration_seconds=20,
            prompt_strategy=PROMPT_STRATEGY,
        )
        self.assertEqual(summary["mode"], WORKFLOW)
        self.assertEqual(summary["reference_slots"], [1, 3])
        self.assertLessEqual(summary["total_seconds"], 20)
        self.assertIn("29", workflow)
        self.assertNotIn("33", workflow)
        self.assertIn("196", workflow)
        self.assertNotIn("201", workflow)
        self.assertEqual(workflow["194"]["inputs"]["image"], "msr/anchor.png")
        self.assertNotIn("211", workflow)
        self.assertEqual(workflow["207"]["inputs"]["vae"], ["3", 2])
        self.assertEqual(workflow["180"]["inputs"]["global_prompt"], "Short world and identity prompt.")

    def test_registered_anchor_is_immediately_ready_without_review(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project_id = "sequence-project"
            project = root / "prompt_projects" / project_id
            project.mkdir(parents=True)
            (project / "manifest.json").write_text(json.dumps({
                "workflow": WORKFLOW,
                "prompt_strategy": PROMPT_STRATEGY,
                "director_prompt_inheritance": False,
            }), encoding="utf-8")
            (project / "background_catalog.json").write_text(json.dumps({
                "backgrounds": {
                    "ANC_TEST": {
                        "suggested_filename": "ANC_TEST.png",
                        "prompt": "Integrated anchor",
                    }
                }
            }), encoding="utf-8")
            upload = root / "upload.png"
            upload.write_bytes(b"anchor")
            saved = msr_prompt_projects.save_background_link_action(root, {
                "project_id": project_id,
                "background_id": "ANC_TEST",
                "filename": "ANC_TEST.png",
                "upload_path": str(upload),
            })
            self.assertEqual(saved["link"]["review_status"], "approved")
            payload = {
                "workflow": WORKFLOW,
                "prompt_strategy": PROMPT_STRATEGY,
                "background": {
                    "background_id": "ANC_TEST",
                    "review_status": "pending",
                    "status": "missing",
                },
            }
            merged = msr_prompt_projects.merge_payload_background(root, project_id, payload)
            self.assertEqual(merged["background"]["review_status"], "approved")
            self.assertEqual(merged["background"]["status"], "linked")
            self.assertEqual(
                msr_prompt_projects.resolve_effective_status(merged, has_errors=False),
                "reviewed",
            )
            listed = msr_prompt_projects.list_project_backgrounds_action(
                root, {"project_id": project_id}
            )["backgrounds"]
            self.assertEqual(listed[0]["review_status"], "approved")

    def test_backend_writes_versioned_request_without_director_fallback(self):
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
                result = ui_backend.create_msr_sequence_candidates_action(submission(image))
                self.assertEqual(result["generation_mode"], WORKFLOW)
                for job_id in result["candidate_job_ids"]:
                    request = json.loads((jobs / job_id / "request.json").read_text())
                    self.assertEqual(request["workflow_kind"], WORKFLOW)
                    self.assertEqual(request["prompt_strategy"], PROMPT_STRATEGY)
                    self.assertFalse(request["director_prompt_inheritance"])
                    self.assertEqual(request["maximum_duration_seconds"], 20)
                    self.assertEqual(
                        [row["role"] for row in request["msr_references"]],
                        ["character_1", "prop_3"],
                    )
                    self.assertNotEqual(request["global_prompt"], ui_backend.DEFAULT_GLOBAL)
            finally:
                for key, value in originals.items():
                    setattr(ui_backend, key, value)


if __name__ == "__main__":
    unittest.main()
