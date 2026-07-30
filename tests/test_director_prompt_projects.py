from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import director_prompt_projects


def markdown(payload: dict) -> str:
    return (
        f"# Director Prompt: {payload['clip_id']}\n\n"
        "## Machine Payload\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n"
    )


def base_payload(project_id: str = "director_test") -> dict:
    return {
        "schema_version": 1,
        "workflow": "director_prompt_v1",
        "project_id": project_id,
        "episode_id": "EP01",
        "scene_id": "SC01-001",
        "clip_id": "SC01-001_01",
        "sequence": 1,
        "status": "awaiting_scene_images",
        "fps": 24,
        "resolution": {"width": 1280, "height": 704},
        "requested_seconds": 10,
        "global_prompt": "Animated ocean fantasy. Spoken dialogue is Korean only.",
        "prompt_review": {"status": "approved"},
        "segments": [
            {
                "segment_id": "SEG01",
                "order": 1,
                "seconds": 5,
                "director_prompt": "Lua slowly approaches Young Mir.",
                "scene_image": {
                    "source_path": None,
                    "review_status": "pending",
                },
            },
            {
                "segment_id": "SEG02",
                "order": 2,
                "seconds": 5,
                "director_prompt": "Lua carefully kneels beside Young Mir.",
                "scene_image": {
                    "source_path": None,
                    "review_status": "pending",
                },
            },
        ],
    }


class DirectorPromptProjectsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project_id = "director_test"
        self.project = (
            self.root
            / director_prompt_projects.DIRECTOR_PROMPT_PROJECTS_DIR
            / self.project_id
        )
        self.scene = self.project / "SC01-001"
        self.images = self.project / "scene_images" / "SC01-001_01"
        self.scene.mkdir(parents=True)
        self.images.mkdir(parents=True)
        (self.project / "manifest.json").write_text(
            json.dumps(
                {
                    "project_id": self.project_id,
                    "title": "Director Test",
                    "description": "fixture",
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_clip(self, payload: dict):
        (self.scene / "SC01-001_01.md").write_text(
            markdown(payload), encoding="utf-8"
        )

    def add_image(self, name: str, data: bytes) -> tuple[str, str]:
        path = self.images / name
        path.write_bytes(data)
        relative = f"scene_images/SC01-001_01/{name}"
        return relative, hashlib.sha256(data).hexdigest()

    def test_awaiting_scene_images(self):
        payload = base_payload(self.project_id)
        validation = director_prompt_projects.validate_machine_payload(
            self.root, payload, project_id=self.project_id
        )
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["status"], "awaiting_scene_images")
        self.assertFalse(validation["can_register_director"])

    def test_ready_for_director_with_approved_images(self):
        payload = base_payload(self.project_id)
        for index, segment in enumerate(payload["segments"], 1):
            relative, digest = self.add_image(f"SEG{index:02d}.png", f"image-{index}".encode())
            segment["scene_image"] = {
                "source_path": relative,
                "review_status": "approved",
                "sha256": digest,
            }
        payload["status"] = "ready_for_director"
        self.write_clip(payload)

        detail = director_prompt_projects.get_clip_action(
            self.root,
            {"project_id": self.project_id, "clip_id": payload["clip_id"]},
        )
        self.assertTrue(detail["can_register_director"])
        self.assertEqual(detail["status"], "ready_for_director")
        self.assertEqual(len(detail["machine_payload"]["segments"]), 2)
        self.assertTrue(
            detail["machine_payload"]["segments"][0]["scene_image"][
                "asset_url"
            ].startswith("/api/director-prompt-assets/")
        )

    def test_changed_image_invalidates_approval(self):
        payload = base_payload(self.project_id)
        for index, segment in enumerate(payload["segments"], 1):
            relative, digest = self.add_image(f"SEG{index:02d}.png", f"image-{index}".encode())
            segment["scene_image"] = {
                "source_path": relative,
                "review_status": "approved",
                "sha256": digest,
            }
        (self.images / "SEG02.png").write_bytes(b"replaced")
        validation = director_prompt_projects.validate_machine_payload(
            self.root, payload, project_id=self.project_id
        )
        self.assertEqual(validation["status"], "image_review_required")
        self.assertTrue(
            any("승인이 무효화" in warning for warning in validation["warnings"])
        )

    def test_changes_required_blocks_registration(self):
        payload = base_payload(self.project_id)
        for index, segment in enumerate(payload["segments"], 1):
            relative, digest = self.add_image(f"SEG{index:02d}.png", f"image-{index}".encode())
            segment["scene_image"] = {
                "source_path": relative,
                "review_status": "approved",
                "sha256": digest,
            }
        payload["segments"][1]["scene_image"]["review_status"] = "changes_required"
        validation = director_prompt_projects.validate_machine_payload(
            self.root, payload, project_id=self.project_id
        )
        self.assertEqual(validation["status"], "image_changes_required")
        self.assertFalse(validation["can_register_director"])

    def test_prompt_review_required(self):
        payload = base_payload(self.project_id)
        payload["prompt_review"]["status"] = "pending"
        validation = director_prompt_projects.validate_machine_payload(
            self.root, payload, project_id=self.project_id
        )
        self.assertEqual(validation["status"], "prompt_review_required")

    def test_path_traversal_is_blocked(self):
        payload = base_payload(self.project_id)
        payload["segments"][0]["scene_image"] = {
            "source_path": "scene_images/../../outside.png",
            "review_status": "approved",
        }
        validation = director_prompt_projects.validate_machine_payload(
            self.root, payload, project_id=self.project_id
        )
        self.assertEqual(validation["status"], "awaiting_scene_images")
        self.assertTrue(validation["warnings"])

    def test_project_and_clip_listing(self):
        payload = base_payload(self.project_id)
        self.write_clip(payload)
        projects = director_prompt_projects.list_projects_action(self.root)
        self.assertEqual(projects["projects"][0]["project_id"], self.project_id)
        clips = director_prompt_projects.list_clips_action(
            self.root, {"project_id": self.project_id}
        )
        self.assertEqual(clips["clips"][0]["clip_id"], "SC01-001_01")
        self.assertEqual(clips["clips"][0]["status"], "awaiting_scene_images")


if __name__ == "__main__":
    unittest.main()
