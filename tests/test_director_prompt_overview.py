from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import director_prompt_overview


class DirectorPromptOverviewTests(unittest.TestCase):
    def test_groups_clips_and_counts_standalone_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "director_prompt_projects" / "episode01"
            scene = project / "SC01"
            scene.mkdir(parents=True)
            registry = {
                "locations": {
                    "LOC_CAVE": {
                        "background_id": "BG_CAVE",
                        "display_name": "Cave",
                        "terrain": "Wet rock",
                        "image_generation": {
                            "generation_prompt": "Empty wet cave background."
                        },
                    }
                }
            }
            (project / "location_registry.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )
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
                "location": {"location_id": "LOC_CAVE"},
                "segments": [
                    {
                        "segment_id": "SEG01",
                        "order": 1,
                        "seconds": 5,
                        "director_prompt": "Lua looks around.",
                        "scene_image": {
                            "generation_prompt": "Lua in a wet cave.",
                            "source_path": None,
                            "review_status": "pending",
                        },
                    }
                ],
            }
            (scene / "SC01_01.md").write_text(
                "# Clip\n\n```json\n"
                + json.dumps(payload)
                + "\n```\n",
                encoding="utf-8",
            )

            result = director_prompt_overview.project_overview_action(
                root, {"project_id": "episode01"}
            )

        self.assertEqual(result["summary"]["background_group_count"], 1)
        self.assertEqual(result["summary"]["background_prompt_ready_count"], 1)
        self.assertEqual(result["summary"]["standalone_segment_prompt_count"], 1)
        self.assertEqual(result["clips"][0]["background_id"], "BG_CAVE")
        self.assertEqual(
            result["background_groups"][0]["clips"][0]["clip_id"],
            "SC01_01",
        )


if __name__ == "__main__":
    unittest.main()
