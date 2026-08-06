from __future__ import annotations

import unittest
from pathlib import Path

import director_prompt_projects


ROOT = Path(__file__).resolve().parents[1]
CLIP_PATH = (
    ROOT
    / "director_prompt_projects"
    / "RaisingaDragonSeason01"
    / "SC01-003"
    / "SC01-003_09.md"
)


@unittest.skip("LTX 2.3 EP01 카메라 실험 프로젝트 보관 처리")
class SC0100309CameraExperimentTest(unittest.TestCase):
    def test_continuous_anchor_transition_contract(self):
        payload = director_prompt_projects.extract_machine_payload(
            CLIP_PATH.read_text(encoding="utf-8")
        )
        segments = payload["segments"]

        self.assertEqual(payload["requested_seconds"], 20)
        self.assertEqual([segment["seconds"] for segment in segments], [6, 3, 6, 5])
        self.assertEqual(
            sum(segment["seconds"] for segment in segments),
            payload["requested_seconds"],
        )
        self.assertIn("one continuous unbroken take", payload["global_prompt"].lower())
        self.assertIn("physically continuous", segments[0]["director_prompt"].lower())
        self.assertIn("settles into the mouth-side interior-facing composition only", segments[0]["director_prompt"].lower())
        self.assertIn("without a cut", segments[1]["director_prompt"].lower())
        self.assertIn("cloth opening across the lower foreground", segments[1]["director_prompt"].lower())
        self.assertIn("without a cut", segments[2]["director_prompt"].lower())
        self.assertIn("cloth crosses the near foreground", segments[2]["director_prompt"].lower())
        self.assertIn("rear tracking move", segments[3]["director_prompt"].lower())
        self.assertNotIn("new shot begins directly", " ".join(
            segment["director_prompt"].lower() for segment in segments
        ))
        self.assertTrue(all(
            segment["scene_image"]["review_status"] == "approved"
            for segment in segments
        ))
        self.assertTrue(all(
            segment["scene_image"]["prompt_version"] == "cinematic_anchor_v2_video_first_35mm"
            for segment in segments
        ))
        self.assertIn("eye-level medium three-quarter rear-side", segments[2]["scene_image"]["prompt"].lower())
        validation = director_prompt_projects.validate_machine_payload(
            ROOT, payload, project_id="RaisingaDragonSeason01"
        )
        self.assertEqual(validation["status"], "ready_for_director")
        self.assertTrue(validation["can_register_director"])
        for segment in segments:
            self.assertIn(
                segment["scene_image"]["review_status"],
                {"pending", "approved", "changes_required"},
            )
            self.assertTrue(segment["scene_image"]["source_path"])



if __name__ == "__main__":
    unittest.main()
