from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import director_prompt_projects
import director_prompt_uploads


class DirectorPromptUploadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "director_prompt_projects" / "episode01"
        (self.project / "SC01").mkdir(parents=True)
        payload = {
            "schema_version": 1,
            "workflow": "director_prompt_v1",
            "project_id": "episode01",
            "scene_id": "SC01",
            "clip_id": "SC01_01",
            "status": "awaiting_scene_images",
            "fps": 24,
            "resolution": {"width": 1280, "height": 704},
            "global_prompt": "Animated fantasy scene.",
            "prompt_review": {"status": "approved"},
            "segments": [
                {
                    "segment_id": "SEG01",
                    "order": 1,
                    "seconds": 5,
                    "director_prompt": "Lua turns toward Mir.",
                    "scene_image": {
                        "status": "missing",
                        "source_path": None,
                        "review_status": "pending",
                        "review_notes": [],
                        "sha256": None,
                    },
                }
            ],
        }
        markdown = "# Clip\n\n```json\n" + json.dumps(payload) + "\n```\n"
        (self.project / "SC01" / "SC01_01.md").write_text(
            markdown, encoding="utf-8"
        )
        self.upload = self.root / "upload.png"
        self.upload.write_bytes(b"matched-image")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_upload_then_approve_reaches_ready_state(self) -> None:
        detail = director_prompt_uploads.save_segment_image_action(
            self.root,
            {
                "project_id": "episode01",
                "clip_id": "SC01_01",
                "segment_id": "SEG01",
                "upload_path": str(self.upload),
            },
        )
        image = detail["machine_payload"]["segments"][0]["scene_image"]
        self.assertEqual(detail["status"], "image_review_required")
        self.assertEqual(image["review_status"], "pending")
        self.assertEqual(
            image["sha256"], hashlib.sha256(b"matched-image").hexdigest()
        )
        stored = director_prompt_projects.extract_machine_payload(
            (self.project / "SC01" / "SC01_01.md").read_text(encoding="utf-8")
        )
        self.assertEqual(stored["status"], "image_review_required")

        detail = director_prompt_uploads.review_segment_image_action(
            self.root,
            {
                "project_id": "episode01",
                "clip_id": "SC01_01",
                "segment_id": "SEG01",
                "review_status": "approved",
            },
        )
        self.assertTrue(detail["can_register_director"])
        self.assertEqual(detail["status"], "ready_for_director")
        self.assertEqual(
            detail["machine_payload"]["image_review_summary"]["approved_count"],
            1,
        )
        stored = director_prompt_projects.extract_machine_payload(
            (self.project / "SC01" / "SC01_01.md").read_text(encoding="utf-8")
        )
        self.assertEqual(stored["status"], "ready_for_director")

    def test_changes_required_blocks_registration(self) -> None:
        director_prompt_uploads.save_segment_image_action(
            self.root,
            {
                "project_id": "episode01",
                "clip_id": "SC01_01",
                "segment_id": "SEG01",
                "upload_path": str(self.upload),
            },
        )
        detail = director_prompt_uploads.review_segment_image_action(
            self.root,
            {
                "project_id": "episode01",
                "clip_id": "SC01_01",
                "segment_id": "SEG01",
                "review_status": "changes_required",
                "review_notes": "Lua identity mismatch",
            },
        )
        self.assertEqual(detail["status"], "image_changes_required")
        self.assertFalse(detail["can_register_director"])

    def test_rejects_unknown_segment(self) -> None:
        with self.assertRaises(
            director_prompt_projects.DirectorPromptProjectError
        ):
            director_prompt_uploads.save_segment_image_action(
                self.root,
                {
                    "project_id": "episode01",
                    "clip_id": "SC01_01",
                    "segment_id": "SEG99",
                    "upload_path": str(self.upload),
                },
            )


if __name__ == "__main__":
    unittest.main()
