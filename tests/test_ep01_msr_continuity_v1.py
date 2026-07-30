from __future__ import annotations

import unittest
from pathlib import Path

import msr_prompt_projects
import msr_sequence_v2
import ui_backend


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "RaisingaDragonSeason01_EP01_MSR_CONTINUITY_V1"
PROJECT_DIR = ROOT / "prompt_projects" / PROJECT_ID


class EP01MSRContinuityV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clips = msr_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        cls.payloads = {}
        for clip in cls.clips:
            path = ROOT / "prompt_projects" / clip["markdown_path"]
            cls.payloads[clip["clip_id"]] = msr_prompt_projects.extract_machine_payload(
                path.read_text(encoding="utf-8")
            )

    def test_episode_scope_duration_and_status(self):
        self.assertEqual(len(self.clips), 23)
        self.assertEqual(sum(clip["requested_seconds"] for clip in self.clips), 380)
        self.assertTrue(all(clip["valid"] for clip in self.clips))
        self.assertTrue(all(
            clip["status"] == ("reviewed" if clip["background_linked"] else "awaiting_background")
            for clip in self.clips
        ))
        self.assertLessEqual(max(clip["requested_seconds"] for clip in self.clips), 20)

    def test_clean_slate_strategy_and_compiled_globals(self):
        for clip_id, payload in self.payloads.items():
            self.assertEqual(payload["workflow"], msr_sequence_v2.WORKFLOW, clip_id)
            self.assertEqual(payload["prompt_strategy"], msr_sequence_v2.PROMPT_STRATEGY, clip_id)
            self.assertIs(payload["director_prompt_inheritance"], False, clip_id)
            self.assertEqual(
                payload["global_prompt"],
                msr_sequence_v2.compile_global_prompt(
                    payload["world_prompt"], payload["references"]
                ),
                clip_id,
            )
            self.assertNotIn("CINEMATIC CAMERA BIBLE", payload["global_prompt"], clip_id)
            self.assertEqual(
                sum(float(item["seconds"]) for item in payload["relay_segments"]),
                float(payload["requested_seconds"]),
                clip_id,
            )

    def test_reference_slot_contract(self):
        for clip_id, payload in self.payloads.items():
            slots = [int(ref["slot"]) for ref in payload["references"]]
            self.assertEqual(slots, sorted(set(slots)), clip_id)
            self.assertIn(1, slots, clip_id)
            self.assertLessEqual(sum(slot in {1, 2} for slot in slots), 2, clip_id)
            for ref in payload["references"]:
                slot = int(ref["slot"])
                expected = f"character_{slot}" if slot <= 2 else f"prop_{slot}"
                self.assertEqual(ref["role"], expected, clip_id)

    def test_village_scene_uses_cast_changes_as_cut_boundaries(self):
        first = self.payloads["SC01-002_M01"]
        self.assertEqual(first["requested_seconds"], 20)
        self.assertEqual([ref["slot"] for ref in first["references"]], [1, 3])
        first_text = " ".join(item["prompt"] for item in first["relay_segments"])
        self.assertNotIn("Village Child", first_text)
        self.assertIn("End after she is standing again", first_text)

        child1 = self.payloads["SC01-002_M02"]
        child2 = self.payloads["SC01-002_M03"]
        fisherman = self.payloads["SC01-002_M04"]
        lua_only = self.payloads["SC01-002_M05"]
        self.assertIn("villageChild01.png", child1["references"][1]["source_path"])
        self.assertIn("village_child_2.png", child2["references"][1]["source_path"])
        self.assertIn("old_fisherman.png", fisherman["references"][1]["source_path"])
        self.assertEqual(fisherman["requested_seconds"], 15)
        fisher_text = " ".join(item["prompt"] for item in fisherman["relay_segments"])
        self.assertIn("오늘은 동굴 쪽 가지 마라", fisher_text)
        self.assertEqual([ref["slot"] for ref in lua_only["references"]], [1, 3])

    def test_anchor_reset_and_continuity_frame_counts(self):
        modes = [payload["continuity_mode"] for payload in self.payloads.values()]
        self.assertEqual(modes.count("new_anchor"), 18)
        self.assertEqual(modes.count("continuity_frame"), 5)
        for clip_id, payload in self.payloads.items():
            if payload["continuity_mode"] == "continuity_frame":
                self.assertTrue(payload.get("continuity_from_clip"), clip_id)
                note = " ".join(payload["background_generation"]["continuity_notes"])
                self.assertIn("stable end frame", note, clip_id)

    def test_new_ui_lists_only_the_new_episode_project(self):
        projects = ui_backend.list_msr_sequence_projects_action({})["projects"]
        ids = {item["project_id"] for item in projects}
        self.assertIn(PROJECT_ID, ids)
        detail = ui_backend.get_msr_sequence_project_clip_action(
            {"project_id": PROJECT_ID, "clip_id": "SC01-002_M04"}
        )
        self.assertEqual(detail["status"], "awaiting_background")
        self.assertFalse(detail["can_register_msr"])


if __name__ == "__main__":
    unittest.main()
