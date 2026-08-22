from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import h3_queue
import model_test_i2v
import model_test_registry


class H3ProjectI2VTestSetTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        self.project_id = "i2v_scene_project"
        project = self.root / "prompt_projects" / self.project_id
        (project / "assets").mkdir(parents=True)
        (project / "assets" / "opening.png").write_bytes(
            b"\x89PNG\r\n\x1a\nfirst-frame"
        )
        (project / "assets" / "closing.png").write_bytes(
            b"\x89PNG\r\n\x1a\nlast-frame"
        )
        (project / "manifest.json").write_text(json.dumps({
            "project_kind": "h3_i2v_production",
            "title": "I2V Scene Project",
        }), encoding="utf-8")
        for index, scene_id in enumerate(("SCENE_001", "SCENE_001", "SCENE_002"), start=1):
            (project / scene_id).mkdir(exist_ok=True)
            clip_id = f"CLIP_{index:03d}"
            payload = {
                "schema_version": 1,
                "workflow": "h3_i2v_production",
                "project_id": self.project_id,
                "scene_id": scene_id,
                "clip_id": clip_id,
                "sequence": index,
                "duration_seconds": 5,
                "video_prompt": f"Shot 1: The subject performs action {index}.",
                "review_intent_ko": f"동작 {index}을 검수한다.",
                "start_image": {
                    "role": "start_frame",
                    "label": f"시작 프레임 {index}",
                    "source_path": "assets/opening.png",
                },
            }
            if index == 1:
                payload["last_image"] = {
                    "role": "last_frame",
                    "label": "종료 프레임 1",
                    "source_path": "assets/closing.png",
                }
            (project / scene_id / f"{clip_id}.md").write_text(
                "## Machine Payload\n\n```json\n" + json.dumps(payload) + "\n```\n",
                encoding="utf-8",
            )

    def tearDown(self):
        self.temp.cleanup()

    def test_scene_registration_is_i2v_scoped_job_free_and_visible_in_general_tests(self):
        marker = h3_queue.create_project_test_set(self.root, {
            "project_id": self.project_id,
            "scene_id": "SCENE_001",
            "generation_mode": "i2v",
        })
        self.assertEqual(3, marker["schema_version"])
        self.assertEqual("i2v", marker["generation_mode"])
        self.assertEqual("scene", marker["scope"])
        self.assertEqual(["CLIP_001", "CLIP_002"], marker["clip_ids"])
        self.assertFalse((self.root / "runtime/h3/jobs").exists())

        duplicate = h3_queue.create_project_test_set(self.root, {
            "project_id": self.project_id,
            "scene_id": "SCENE_001",
            "generation_mode": "i2v",
        })
        self.assertTrue(duplicate["already_exists"])
        self.assertEqual(marker["project_test_set_id"], duplicate["project_test_set_id"])

        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        suite_id = model_test_i2v.project_scene_suite_id(
            self.project_id, "SCENE_001"
        )
        suite = next(row for row in dashboard["suites"] if row["suite_id"] == suite_id)
        self.assertEqual("i2v_fixed_anchor", suite["input_mode"])
        self.assertEqual(marker["project_test_set_id"], suite["project_test_set_id"])
        self.assertTrue(suite["deletable"])
        self.assertEqual(2, len(suite["cases"]))
        self.assertEqual(
            {"CLIP_001", "CLIP_002"},
            {row["contract"]["source_clip_id"] for row in suite["cases"]},
        )
        for case in suite["cases"]:
            self.assertEqual("i2v_fixed_anchor", case["contract"]["input_mode"])
            expected_roles = (
                ["last_reference_image", "reference_image"]
                if case["contract"]["source_clip_id"] == "CLIP_001"
                else ["reference_image"]
            )
            self.assertEqual(expected_roles, [
                requirement["role"] for requirement in case["asset_requirements"]
            ])
            self.assertEqual(len(expected_roles), len([
                asset for asset in dashboard["case_assets"]
                if asset["case_version_id"] == case["case_version_id"]
            ]))

        deleted = h3_queue.delete_project_test_set(
            self.root, marker["project_test_set_id"]
        )
        self.assertEqual("i2v", deleted["generation_mode"])
        after_delete = model_test_registry.dashboard(self.root, self.workflows)
        self.assertFalse(any(row["suite_id"] == suite_id for row in after_delete["suites"]))

    def test_page_generation_mode_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "생성 방식"):
            h3_queue.create_project_test_set(self.root, {
                "project_id": self.project_id,
                "scene_id": "SCENE_001",
                "generation_mode": "r2v",
            })


if __name__ == "__main__":
    unittest.main()
