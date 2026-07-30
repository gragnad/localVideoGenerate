from __future__ import annotations

import json
import unittest
from pathlib import Path

import director_prompt_projects
import msr_prompt_projects


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "RaisingaDragonSeason01"
V4_ID = "RaisingaDragonSeason01_EP01_v4"
PROJECT_DIR = ROOT / "director_prompt_projects" / PROJECT_ID
CAMERA_TEST_CLIP_ID = "SC01-003_09"


class DirectorRaisingDragonEp01Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PROJECT_DIR.is_dir():
            raise unittest.SkipTest(
                "Director project missing — run scripts/generate_director_raising_dragon_ep01.py"
            )

    def test_project_structure(self):
        for name in (
            "manifest.json",
            "character_identity_registry.json",
            "location_registry.json",
        ):
            self.assertTrue((PROJECT_DIR / name).is_file(), name)

    def test_clip_count_and_duration(self):
        clips = director_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        self.assertEqual(len(clips), 24)
        total = sum(c["requested_seconds"] for c in clips)
        self.assertEqual(total, 412)
        segments = sum(c["segment_count"] for c in clips)
        self.assertEqual(segments, 89)

    def test_clip_image_states(self):
        clips = director_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        for clip in clips:
            self.assertTrue(clip["valid"], clip)
            if clip["clip_id"] == CAMERA_TEST_CLIP_ID:
                self.assertIn(
                    clip["status"],
                    {"image_review_required", "image_changes_required", "ready_for_director"},
                )
            else:
                self.assertEqual(
                    clip["status"], "awaiting_scene_images", clip["clip_id"]
                )

    def test_no_needs_confirmation(self):
        clips = director_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        statuses = {c["clip_id"]: c["status"] for c in clips}
        self.assertNotIn("needs_confirmation", statuses.values())

    def test_workflow_and_resolution(self):
        clips = director_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        for clip in clips:
            path = ROOT / "director_prompt_projects" / clip["markdown_path"]
            payload = director_prompt_projects.extract_machine_payload(
                path.read_text(encoding="utf-8")
            )
            self.assertEqual(payload["workflow"], "director_prompt_v1")
            self.assertEqual(payload["project_id"], PROJECT_ID)
            self.assertEqual(payload["resolution"], {"width": 1280, "height": 704})
            self.assertEqual(payload["fps"], 24)
            self.assertEqual(payload["prompt_review"]["status"], "approved")
            for seg in payload["segments"]:
                self.assertTrue(seg["director_prompt"])
                self.assertTrue(seg["scene_image"]["prompt"])
                self.assertTrue(seg["scene_image"]["negative_prompt"])
                if clip["clip_id"] == CAMERA_TEST_CLIP_ID:
                    self.assertTrue(seg["scene_image"]["source_path"])
                    review_status = seg["scene_image"]["review_status"]
                    self.assertIn(
                        review_status, {"pending", "approved", "changes_required"}
                    )
                    expected = "approved" if review_status == "approved" else "uploaded"
                    self.assertEqual(seg["scene_image"]["status"], expected)
                else:
                    self.assertIsNone(seg["scene_image"]["source_path"])
                    self.assertEqual(seg["scene_image"]["status"], "missing")

    def test_character_registry_project_id(self):
        reg = json.loads(
            (PROJECT_DIR / "character_identity_registry.json").read_text(encoding="utf-8")
        )
        self.assertEqual(reg["project_id"], PROJECT_ID)
        self.assertIn("CHAR_LUA", reg["characters"])
        self.assertIn("CHAR_YOUNG_MIR", reg["characters"])

    def test_location_registry_covers_backgrounds(self):
        loc = json.loads(
            (PROJECT_DIR / "location_registry.json").read_text(encoding="utf-8")
        )
        self.assertGreaterEqual(len(loc["locations"]), 10)

    def test_dialogue_preserved_vs_v4(self):
        v4_clips = msr_prompt_projects.scan_project_clips(ROOT, V4_ID)
        director_clips = director_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        v4_by_id = {c["clip_id"]: c for c in v4_clips}
        for dclip in director_clips:
            path = ROOT / "director_prompt_projects" / dclip["markdown_path"]
            payload = director_prompt_projects.extract_machine_payload(
                path.read_text(encoding="utf-8")
            )
            v4_path = (
                ROOT
                / "prompt_projects"
                / V4_ID
                / payload["scene_id"]
                / f"{payload['clip_id']}.md"
            )
            v4_payload = msr_prompt_projects.extract_machine_payload(
                v4_path.read_text(encoding="utf-8")
            )
            d_lines = [
                (d["speaker"], d["text"])
                for seg in payload["segments"]
                for d in seg.get("dialogue") or []
            ]
            v4_lines = [
                (d["speaker"], d["text"]) for d in v4_payload.get("dialogue") or []
            ]
            self.assertEqual(d_lines, v4_lines, payload["clip_id"])

    def test_scene_image_prompt_quality(self):
        import re

        cam = re.compile(
            r"camera\s+(moves|tilts|continues|pans|tracks|pulls|pushes|dolly|breaks|drifts|shudders|follows)",
            re.I,
        )
        temporal = re.compile(
            r"\b(slowly|gradually|then again|continues to|begins to|about to|gains ground|"
            r"moves closer|Specify screen positions|Segment opening frozen moment)\b",
            re.I,
        )
        forbidden = re.compile(
            r"Picture\s+\d+|(?:CHAR|ENTITY|PROP)_[A-Z0-9_]+|Specify screen positions",
            re.I,
        )
        for clip in director_prompt_projects.scan_project_clips(ROOT, PROJECT_ID):
            path = ROOT / "director_prompt_projects" / clip["markdown_path"]
            payload = director_prompt_projects.extract_machine_payload(
                path.read_text(encoding="utf-8")
            )
            for seg in payload["segments"]:
                image = seg["scene_image"]
                legacy = image.get("prompt") or ""
                gen = image.get("generation_prompt") or ""
                self.assertTrue(
                    legacy.startswith(("High-quality stylized", "Cinematic keyframe")),
                    seg["segment_id"],
                )
                self.assertTrue(
                    gen.startswith("Premium stylized 3D animated"),
                    seg["segment_id"],
                )
                self.assertTrue(image.get("background_id"), seg["segment_id"])
                self.assertIn("reference_paths", image)
                self.assertNotIn("Specify screen positions", legacy, seg["segment_id"])
                self.assertIsNone(re.search(r"Picture \d+", legacy), seg["segment_id"])
                self.assertIsNone(cam.search(legacy), seg["segment_id"])
                self.assertIsNone(temporal.search(legacy), seg["segment_id"])
                self.assertIsNone(forbidden.search(gen), seg["segment_id"])
                self.assertIsNone(cam.search(gen), seg["segment_id"])

    def test_scene_image_directories_exist(self):
        clips = director_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        for clip in clips:
            img_dir = PROJECT_DIR / "scene_images" / clip["clip_id"]
            self.assertTrue(img_dir.is_dir(), clip["clip_id"])


if __name__ == "__main__":
    unittest.main()
