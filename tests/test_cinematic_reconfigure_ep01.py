from __future__ import annotations

import copy
import unittest
from pathlib import Path

import director_prompt_projects
from scripts.reconfigure_cinematic_ep01_scenes_001_003 import (
    CLIP_PLANS,
    IMAGE_VERSION,
    PLAN_VERSION,
    REFERENCE_CLIP,
    reconfigure_payload,
)


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "RaisingaDragonSeason01"
PROJECT_DIR = ROOT / "director_prompt_projects" / PROJECT_ID
TARGET_SCENES = {"SC01-001", "SC01-002", "SC01-003"}


@unittest.skip("LTX 2.3 EP01 Director 프로젝트 보관 처리")
class CinematicReconfigureEp01Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = {}
        for path in PROJECT_DIR.rglob("*.md"):
            if "scene_images" in path.parts:
                continue
            payload = director_prompt_projects.extract_machine_payload(
                path.read_text(encoding="utf-8")
            )
            if payload.get("scene_id") in TARGET_SCENES:
                cls.payloads[payload["clip_id"]] = payload

    def test_exact_scope_and_reference_preservation(self):
        self.assertEqual(set(CLIP_PLANS), set(self.payloads) - {REFERENCE_CLIP})
        self.assertEqual(len(CLIP_PLANS), 15)
        self.assertEqual(
            sum(len(self.payloads[clip_id]["segments"]) for clip_id in CLIP_PLANS),
            53,
        )
        reference = self.payloads[REFERENCE_CLIP]
        self.assertTrue(all(
            segment["scene_image"]["review_status"] == "approved"
            for segment in reference["segments"]
        ))
        self.assertNotEqual(
            (reference.get("cinematic_plan") or {}).get("version"),
            PLAN_VERSION,
        )

    def test_reconfigured_camera_and_anchor_contract(self):
        for clip_id, plan in CLIP_PLANS.items():
            payload = self.payloads[clip_id]
            cinematic = payload["cinematic_plan"]
            segments = payload["segments"]
            self.assertEqual(cinematic["version"], PLAN_VERSION, clip_id)
            self.assertTrue(cinematic["continuous_generation"], clip_id)
            self.assertLessEqual(cinematic["camera_move_budget"], 2, clip_id)
            self.assertEqual(cinematic["camera_move_budget"], plan["movement_budget"])
            self.assertEqual(len(cinematic["beats"]), len(segments), clip_id)
            self.assertEqual(
                sum(segment["seconds"] for segment in segments),
                payload["requested_seconds"],
                clip_id,
            )
            for index, segment in enumerate(segments):
                image = segment["scene_image"]
                beat = cinematic["beats"][index]
                self.assertEqual(image["prompt_version"], IMAGE_VERSION)
                if image.get("source_path"):
                    self.assertEqual(image["status"], "approved")
                    self.assertEqual(image["review_status"], "approved")
                    self.assertTrue((PROJECT_DIR / image["source_path"]).is_file())
                else:
                    self.assertEqual(image["status"], "missing")
                    self.assertEqual(image["review_status"], "changes_required")
                self.assertEqual(image["camera_axis"], beat["camera_axis"])
                self.assertEqual(image["recommended_guide_strength"], 0.75)
                self.assertTrue(segment["director_prompt_base"])
                self.assertTrue(image["prompt_base"])
                self.assertTrue(image["generation_prompt_base"])
                self.assertTrue(image["prompt"].startswith("Cinematic keyframe"))
                self.assertTrue(image["generation_prompt"].startswith(
                    "Premium stylized 3D animated"
                ))

    def test_transform_is_idempotent(self):
        for clip_id, plan in CLIP_PLANS.items():
            once = reconfigure_payload(copy.deepcopy(self.payloads[clip_id]), plan)
            twice = reconfigure_payload(copy.deepcopy(once), plan)
            self.assertEqual(once, twice, clip_id)


if __name__ == "__main__":
    unittest.main()
