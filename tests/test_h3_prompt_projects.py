from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import h3_prompt_projects


def valid_r2v_prompt() -> str:
    return """subject_definitions:
<Subject 1> is Hero from <Picture 1>. Preserve the exact identity and clothing.

summary:
[reference generation] The hero turns toward a distant movement.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - Preserve the exact identity and clothing.

detailed_description:
[Shot 1] A medium-wide view frames <Subject 1> Hero turning the whole body toward a distant movement and tightening both hands around the weapon.

overall_soundscape:
Wind, cloth movement, and one boot scraping stone.

non_diegetic_music:
A restrained low string pulse."""


class H3PromptProjectTests(unittest.TestCase):
    def test_action_scene_route_fails_closed_without_dedicated_generator(self):
        payload = {
            "scene_type": "action",
            "prompt_profile": "generic_storyboard",
            "prompt_generator": "generic_generator",
            "action_scene_contract": {
                "version": h3_prompt_projects.ACTION_SCENE_CONTRACT_VERSION,
                "phase": "impact",
                "speed_profiles": ["a", "b", "c", "d"],
                "motion_links": ["a-b", "b-c", "c-d"],
                "environmental_proof": "water and debris preserve force direction",
            },
            "video_prompt": "single project prompt",
        }

        errors = h3_prompt_projects.action_scene_routing_errors(payload)

        self.assertTrue(any("prompt_profile" in error for error in errors))
        self.assertTrue(any("prompt_generator" in error for error in errors))
        self.assertFalse(any("A/D/E" in error for error in errors))

    def test_superseded_project_reports_generation_block_and_replacements(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "prompt_projects" / "old_combined"
            project.mkdir(parents=True)
            (project / "manifest.json").write_text(json.dumps({
                "generation_blocked": True,
                "generation_block_reason": "Split by directing profile.",
                "replacement_project_ids": ["ep00_action", "ep01_story"],
            }), encoding="utf-8")

            reason = h3_prompt_projects.project_generation_block_reason(
                root, "old_combined"
            )

            self.assertIn("Split by directing profile.", reason)
            self.assertIn("ep00_action", reason)
            self.assertIn("ep01_story", reason)

    def test_extracts_only_detailed_description_for_scene_translation(self):
        prompt = (
            "subject_definitions:\n<Subject 1>: Hero.\n\n"
            "summary:\nA short summary.\n\n"
            "detailed_description:\n"
            "[Shot 1] The hero turns.\n\n"
            "[Shot 2] At 00:02.000, the hero runs.\n\n"
            "overall_soundscape:\nWind and footsteps.\n\n"
            "non_diegetic_music:\nN/A"
        )
        self.assertEqual(
            "[Shot 1] The hero turns.\n\n"
            "[Shot 2] At 00:02.000, the hero runs.",
            h3_prompt_projects.extract_detailed_description(prompt),
        )
        self.assertEqual("", h3_prompt_projects.extract_detailed_description("Shot 1 only"))

    def test_r2v_ui_uses_scene_description_translation(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "web/public/index.html").read_text(encoding="utf-8")
        script = (root / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn('id="translateH3Scene"', html)
        self.assertIn('id="h3SceneTranslationClips"', html)
        self.assertNotIn('id="translateH3Prompt"', html)
        self.assertIn("item.detailed_description", script)
        self.assertNotIn("translateH3Prompt", script)

    def test_project_scene_clip_and_linked_picture(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "prompt_projects" / "demo"
            (project / "SCENE_001").mkdir(parents=True)
            (project / "source").mkdir()
            (project / "assets").mkdir()
            (project / "assets" / "hero.png").write_bytes(b"png")
            (project / "manifest.json").write_text(json.dumps({
                "project_kind": "h3_r2v_production", "title": "Demo",
            }), encoding="utf-8")
            payload = {
                "schema_version": 1, "workflow": "h3_r2v_production",
                "prompt_contract_version": "h3_ref_minimal_v1",
                "project_id": "demo", "scene_id": "SCENE_001", "clip_id": "CLIP_001",
                "sequence": 1, "duration_seconds": 5,
                "video_prompt": valid_r2v_prompt(),
                "references": [{"picture_index": 1, "role": "character", "required": True, "source_path": "assets/hero.png"}],
            }
            (project / "SCENE_001" / "CLIP_001.md").write_text(
                "## Machine Payload\n\n```json\n" + json.dumps(payload) + "\n```\n",
                encoding="utf-8",
            )
            (project / "source" / "supplied.source.md").write_text(
                "# Supplied prompt source\n",
                encoding="utf-8",
            )
            projects = h3_prompt_projects.list_projects(root)["projects"]
            self.assertEqual("demo", projects[0]["project_id"])
            self.assertEqual("r2v", projects[0]["generation_mode"])
            self.assertEqual(1, projects[0]["clip_count"])
            overview = h3_prompt_projects.project_clips(root, "demo")
            self.assertEqual("r2v", overview["generation_mode"])
            self.assertEqual(1, len(overview["clips"]))
            self.assertEqual("SCENE_001", overview["scenes"][0]["scene_id"])
            clip = h3_prompt_projects.load_clip(root, "demo", "CLIP_001")
            self.assertTrue(clip["ready"])
            self.assertTrue(clip["references"][0]["linked"])
            self.assertRegex(
                clip["references"][0]["asset_url"],
                r"^/api/h3/projects/demo/clips/CLIP_001/pictures/1\?v=[0-9a-f]+-[0-9a-f]+$",
            )
            first_asset_url = clip["references"][0]["asset_url"]
            (project / "assets" / "hero.png").write_bytes(b"new-png")
            refreshed = h3_prompt_projects.load_clip(root, "demo", "CLIP_001")
            self.assertNotEqual(first_asset_url, refreshed["references"][0]["asset_url"])
            self.assertEqual(project / "assets" / "hero.png", h3_prompt_projects.picture_path(root, "demo", "CLIP_001", 1))

    def test_project_clips_use_global_sequence_before_scene_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "prompt_projects" / "ordered_demo"
            (project / "SCENE_01-COASTAL").mkdir(parents=True)
            (project / "SCENE_01-1-HIDDEN").mkdir(parents=True)
            (project / "assets").mkdir()
            (project / "assets" / "hero.png").write_bytes(b"png")
            (project / "manifest.json").write_text(json.dumps({
                "project_kind": "h3_r2v_production", "title": "Ordered Demo",
            }), encoding="utf-8")
            rows = [
                ("SCENE_01-COASTAL", "CLIP_001", 1),
                ("SCENE_01-1-HIDDEN", "CLIP_002", 2),
            ]
            for scene_id, clip_id, sequence in rows:
                payload = {
                    "schema_version": 1,
                    "workflow": "h3_r2v_production",
                    "prompt_contract_version": "h3_ref_minimal_v1",
                    "project_id": "ordered_demo",
                    "scene_id": scene_id,
                    "clip_id": clip_id,
                    "sequence": sequence,
                    "duration_seconds": 5,
                    "video_prompt": valid_r2v_prompt(),
                    "references": [{
                        "picture_index": 1,
                        "role": "character",
                        "required": True,
                        "source_path": "assets/hero.png",
                    }],
                }
                (project / scene_id / f"{clip_id}.md").write_text(
                    "## Machine Payload\n\n```json\n" + json.dumps(payload) + "\n```\n",
                    encoding="utf-8",
                )

            overview = h3_prompt_projects.project_clips(root, "ordered_demo")
            self.assertEqual(["CLIP_001", "CLIP_002"], [row["clip_id"] for row in overview["clips"]])
            self.assertEqual(
                ["SCENE_01-COASTAL", "SCENE_01-1-HIDDEN"],
                [row["scene_id"] for row in overview["scenes"]],
            )

    def test_i2v_project_normalizes_one_linked_start_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "prompt_projects" / "i2v_demo"
            (project / "SCENE_001").mkdir(parents=True)
            (project / "assets").mkdir()
            start = project / "assets" / "opening.webp"
            start.write_bytes(b"webp")
            (project / "manifest.json").write_text(json.dumps({
                "project_kind": "h3_i2v_production", "title": "I2V Demo",
            }), encoding="utf-8")
            payload = {
                "schema_version": 1, "workflow": "h3_i2v_production",
                "project_id": "i2v_demo", "scene_id": "SCENE_001", "clip_id": "CLIP_001",
                "sequence": 1, "duration_seconds": 6,
                "video_prompt": "The subject walks forward from the opening frame.",
                "start_image": {"source_path": "assets/opening.webp", "label": "Opening"},
            }
            (project / "SCENE_001" / "CLIP_001.md").write_text(
                "## Machine Payload\n\n```json\n" + json.dumps(payload) + "\n```\n",
                encoding="utf-8",
            )
            projects = h3_prompt_projects.list_projects(root)["projects"]
            self.assertEqual("i2v", projects[0]["generation_mode"])
            clip = h3_prompt_projects.load_clip(root, "i2v_demo", "CLIP_001")
            self.assertTrue(clip["ready"])
            self.assertEqual("i2v", clip["generation_mode"])
            self.assertEqual("start_frame", clip["start_image"]["role"])
            self.assertEqual([1], [row["picture_index"] for row in clip["references"]])
            self.assertEqual(start, h3_prompt_projects.picture_path(root, "i2v_demo", "CLIP_001", 1))

    def test_template_project_is_discoverable_but_requests_uploads(self):
        root = Path(__file__).resolve().parents[1]
        projects = h3_prompt_projects.list_projects(root)["projects"]
        template = next(row for row in projects if row["project_id"] == "H3_PROJECT_TEMPLATE")
        self.assertFalse(template["deletable"])
        self.assertIn("템플릿", template["delete_block_reason"])
        self.assertEqual(1, template["scene_count"])
        clip = h3_prompt_projects.load_clip(root, "H3_PROJECT_TEMPLATE", "CLIP_001")
        self.assertFalse(clip["ready"])
        self.assertEqual([1, 2], [row["picture_index"] for row in clip["references"]])
        i2v_template = next(row for row in projects if row["project_id"] == "H3_I2V_PROJECT_TEMPLATE")
        self.assertFalse(i2v_template["deletable"])
        self.assertEqual("i2v", i2v_template["generation_mode"])
        i2v_clip = h3_prompt_projects.load_clip(root, "H3_I2V_PROJECT_TEMPLATE", "CLIP_001")
        self.assertFalse(i2v_clip["ready"])
        self.assertEqual("start_frame", i2v_clip["start_image"]["role"])
        self.assertIn("클립 시작 이미지가 연결되지 않았습니다.", i2v_clip["errors"])

    def test_retired_generated_projects_are_not_discoverable(self):
        root = Path(__file__).resolve().parents[1]
        retired = (
            "RaisingaDragonSeason01_EP00_H3_R2V_V2",
            "RaisingaDragonSeason01_EP01_H3_R2V_V2",
        )
        visible = {
            row["project_id"]
            for row in h3_prompt_projects.list_projects(root)["projects"]
        }
        for project_id in retired:
            self.assertNotIn(project_id, visible)
            self.assertFalse((root / "prompt_projects" / project_id).exists())
            self.assertTrue(
                (
                    root
                    / "archive/retired_h3_prompt_pipeline_20260815/projects"
                    / project_id
                ).is_dir()
            )


if __name__ == "__main__":
    unittest.main()
