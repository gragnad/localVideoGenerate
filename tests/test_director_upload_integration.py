from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ui_backend


class DirectorUploadIntegrationTests(unittest.TestCase):
    def test_backend_dispatch_contract_and_web_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "director_prompt_projects" / "episode01"
            (project / "SC01").mkdir(parents=True)
            payload = {
                "workflow": "director_prompt_v1",
                "project_id": "episode01",
                "scene_id": "SC01",
                "clip_id": "SC01_01",
                "status": "awaiting_scene_images",
                "fps": 24,
                "resolution": {"width": 1280, "height": 704},
                "global_prompt": "Animated fantasy.",
                "prompt_review": {"status": "approved"},
                "segments": [
                    {
                        "segment_id": "SEG01",
                        "order": 1,
                        "seconds": 5,
                        "director_prompt": "Lua looks toward Mir.",
                        "scene_image": {
                            "source_path": None,
                            "review_status": "pending",
                        },
                    }
                ],
            }
            (project / "SC01" / "SC01_01.md").write_text(
                "# Clip\n\n```json\n"
                + json.dumps(payload)
                + "\n```\n",
                encoding="utf-8",
            )
            upload = root / "scene.png"
            upload.write_bytes(b"integration-image")

            with patch.object(ui_backend, "ROOT", root):
                detail = ui_backend.save_director_prompt_segment_image_action(
                    {
                        "project_id": "episode01",
                        "clip_id": "SC01_01",
                        "segment_id": "SEG01",
                        "upload_path": str(upload),
                    }
                )
                self.assertEqual(detail["status"], "image_review_required")
                detail = ui_backend.review_director_prompt_segment_image_action(
                    {
                        "project_id": "episode01",
                        "clip_id": "SC01_01",
                        "segment_id": "SEG01",
                        "review_status": "approved",
                    }
                )
                self.assertTrue(detail["can_register_director"])

        source_root = Path(__file__).resolve().parents[1]
        server = (source_root / "web" / "server.mjs").read_text(encoding="utf-8")
        browser = (source_root / "web" / "public" / "app.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("save_director_prompt_segment_image", server)
        self.assertIn("review_director_prompt_segment_image", server)
        self.assertIn("data-director-drop", browser)
        self.assertIn("bindDirectorPromptSegmentControls", browser)
        self.assertIn("data-director-review", browser)
        self.assertIn("fetch(url,{headers,cache:'no-store'})", browser)


if __name__ == "__main__":
    unittest.main()
