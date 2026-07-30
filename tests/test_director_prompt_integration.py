from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ui_backend


class DirectorPromptIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "director_prompt_projects" / "episode01"
        images = self.project / "scene_images"
        images.mkdir(parents=True)
        image = images / "SC01_SEG01.png"
        image.write_bytes(b"approved-scene-image")
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        payload = {
            "workflow": "director_prompt_v1",
            "project_id": "episode01",
            "scene_id": "SC01",
            "clip_id": "SC01_CLIP01",
            "sequence": 1,
            "status": "ready_for_director",
            "fps": 24,
            "resolution": {"width": 1280, "height": 704},
            "global_prompt": "High quality animated fantasy scene.",
            "prompt_review": {"status": "approved"},
            "segments": [
                {
                    "segment_id": "SC01_SEG01",
                    "order": 1,
                    "seconds": 5,
                    "director_prompt": (
                        'Lua walks toward Mir and says in Korean, "미르야."'
                    ),
                    "scene_image": {
                        "source_path": "scene_images/SC01_SEG01.png",
                        "sha256": digest,
                        "review_status": "approved",
                        "prompt": "Full cinematic establishing frame.",
                    },
                }
            ],
        }
        markdown = "# Scene\n\n```json\n" + json.dumps(payload) + "\n```\n"
        (self.project / "SC01_CLIP01.md").write_text(markdown, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_ui_backend_actions_return_registerable_clip(self) -> None:
        with patch.object(ui_backend, "ROOT", self.root):
            projects = ui_backend.list_director_prompt_projects_action({})
            clips = ui_backend.list_director_prompt_project_clips_action(
                {"project_id": "episode01"}
            )
            detail = ui_backend.get_director_prompt_project_clip_action(
                {"project_id": "episode01", "clip_id": "SC01_CLIP01"}
            )
            asset = ui_backend.director_prompt_asset_action(
                {
                    "project_id": "episode01",
                    "asset_path": "scene_images/SC01_SEG01.png",
                }
            )

        self.assertEqual(projects["projects"][0]["ready_count"], 1)
        self.assertTrue(clips["clips"][0]["can_register_director"])
        self.assertTrue(detail["can_register_director"])
        self.assertEqual(
            detail["machine_payload"]["segments"][0]["director_prompt"],
            'Lua walks toward Mir and says in Korean, "미르야."',
        )
        self.assertEqual(Path(asset["path"]).read_bytes(), b"approved-scene-image")

    def test_node_and_browser_contracts_are_wired(self) -> None:
        root = Path(__file__).resolve().parents[1]
        server = (root / "web" / "server.mjs").read_text(encoding="utf-8")
        browser = (root / "web" / "public" / "app.js").read_text(encoding="utf-8")

        for action in (
            "list_director_prompt_projects",
            "list_director_prompt_project_clips",
            "get_director_prompt_project_clip",
            "director_prompt_asset",
        ):
            self.assertIn(action, server)
        self.assertIn("/api/director-prompt-projects", browser)
        self.assertIn("can_register_director", browser)
        self.assertIn("applyDirectorPromptClip", browser)
        self.assertIn("apiBlob(image.asset_url)", browser)


if __name__ == "__main__":
    unittest.main()
