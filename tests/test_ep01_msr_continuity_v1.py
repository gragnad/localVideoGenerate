from __future__ import annotations

import unittest
from pathlib import Path

import msr_prompt_projects
import msr_sequence_v2
import ui_backend
from scripts.generate_ep01_msr_continuity_v1 import RECONFIGURATION_PLAN, SC01_002_REVIEW_EVIDENCE


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "RaisingaDragonSeason01_EP01_MSR_CONTINUITY_V1"
PROJECT_DIR = ROOT / "prompt_projects" / PROJECT_ID


@unittest.skip("LTX 2.3 EP01 MSR 프로젝트 보관 처리")
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
        self.assertEqual(len(self.clips), 36)
        self.assertEqual(sum(clip["requested_seconds"] for clip in self.clips), 361)
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
            self.assertTrue(payload["review_intent_ko"].strip(), clip_id)
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
        first_parts = [self.payloads[clip_id] for clip_id in (
            "SC01-002_M01", "SC01-002_M01B", "SC01-002_M01C"
        )]
        self.assertEqual([part["requested_seconds"] for part in first_parts], [4, 5, 5])
        self.assertTrue(all(
            [ref["slot"] for ref in part["references"]] == [1, 3]
            for part in first_parts
        ))
        self.assertEqual(first_parts[2]["continuity_mode"], "continuity_frame")
        self.assertEqual(first_parts[2]["continuity_from_clip"], "SC01-002_M01B")
        self.assertEqual(first_parts[0]["anchor"]["background_id"], "ANC_SC01-002_M01_EXP_V2")
        first_text = " ".join(
            item["prompt"] for part in first_parts for item in part["relay_segments"]
        )
        self.assertNotIn("Village Child", first_text)

        children = self.payloads["SC01-002_M02"]
        lua_reply = self.payloads["SC01-002_M03"]
        fisherman = self.payloads["SC01-002_M04"]
        lua_only = self.payloads["SC01-002_M05"]
        self.assertEqual([ref["slot"] for ref in children["references"]], [1, 2])
        self.assertIn("villageChild01.png", children["references"][0]["source_path"])
        self.assertIn("village_child_2.png", children["references"][1]["source_path"])
        self.assertNotIn("Lua.png", [ref["source_path"] for ref in children["references"]])
        self.assertNotIn("Lua", children["global_prompt"])
        self.assertNotIn("off-screen", children["anchor"]["description"])
        self.assertEqual([ref["slot"] for ref in lua_reply["references"]], [1, 3])
        self.assertIn("Lua.png", lua_reply["references"][0]["source_path"])
        self.assertNotIn(
            "village",
            " ".join(ref["source_path"].lower() for ref in lua_reply["references"]),
        )
        self.assertIn("old_fisherman.png", fisherman["references"][1]["source_path"])
        self.assertEqual(fisherman["requested_seconds"], 15)
        fisher_text = " ".join(item["prompt"] for item in fisherman["relay_segments"])
        self.assertIn("오늘은 동굴 쪽 가지 마라", fisher_text)
        self.assertEqual([ref["slot"] for ref in lua_only["references"]], [1, 3])

    def test_village_scene_has_cinematic_and_performance_controls(self):
        texts = {
            clip_id: " ".join(
                item["prompt"] for item in self.payloads[clip_id]["relay_segments"]
            )
            for clip_id in (
                "SC01-002_M01",
                "SC01-002_M01B",
                "SC01-002_M01C",
                "SC01-002_M02",
                "SC01-002_M03",
                "SC01-002_M04",
                "SC01-002_M05",
            )
        }
        self.assertTrue(all("camera" in text.lower() for text in texts.values()))
        self.assertIn("small controlled adjustment of the low spear point", texts["SC01-002_M01"])
        self.assertIn("subtle forward push along the existing spear line", texts["SC01-002_M01"])
        self.assertIn("broad clean gap between spear tip and fish", self.payloads["SC01-002_M01"]["anchor"]["description"])
        self.assertIn("held breath immediately before the thrust", texts["SC01-002_M01"])
        self.assertIn("front sandal releases from the slick stone lip", texts["SC01-002_M01B"])
        self.assertIn("one energetic continuous move", texts["SC01-002_M01B"])
        self.assertIn("brief cinematic slow-motion emphasis", texts["SC01-002_M01B"])
        self.assertIn("full impact speed", texts["SC01-002_M01B"])
        self.assertNotIn("no slow motion", texts["SC01-002_M01B"].lower())
        self.assertNotIn("no new spear action", texts["SC01-002_M01B"].lower())
        self.assertNotIn("no other voice", texts["SC01-002_M01B"].lower())
        self.assertIn("already settled in the shallow water", texts["SC01-002_M01C"])
        self.assertIn("pushes herself back to stable footing", texts["SC01-002_M01C"])
        self.assertNotIn("앗!", texts["SC01-002_M01C"])
        self.assertIn("Only Village Child 1 speaks", texts["SC01-002_M02"])
        self.assertIn("Only Village Child 2 speaks", texts["SC01-002_M02"])
        self.assertNotIn("toward Lua", texts["SC01-002_M02"])
        self.assertIn("empty frame-right edge", texts["SC01-002_M02"])
        self.assertIn("closed lips", texts["SC01-002_M02"])
        self.assertIn("spear keeps it physically supported and motionless", texts["SC01-002_M03"])
        self.assertIn("Lua alone", texts["SC01-002_M03"])
        self.assertNotIn("village children", texts["SC01-002_M03"])
        self.assertIn("empty frame-left edge", texts["SC01-002_M03"])
        self.assertNotIn("off-screen", texts["SC01-002_M03"])
        self.assertNotIn("laughter", texts["SC01-002_M03"])
        self.assertNotIn("move wet hair", texts["SC01-002_M03"])
        self.assertIn("Both of Lua's hands remain below chest level", texts["SC01-002_M03"])
        self.assertIn("waist-up framing toward chest-up framing", texts["SC01-002_M03"])
        self.assertIn("no cut or isolated talking head", texts["SC01-002_M04"])
        self.assertIn("internal Korean voice-over", texts["SC01-002_M05"])
        self.assertIn("reflected light travel across wet stones", texts["SC01-002_M05"])
        self.assertIn("clear visual decision cue", texts["SC01-002_M05"])
        self.assertIn("smooth low rear three-quarter tracking shot", texts["SC01-002_M05"])
        self.assertIn("Every running step lands visibly on solid stone", texts["SC01-002_M05"])
        self.assertIn("실제 찌르기 직전", self.payloads["SC01-002_M01"]["review_intent_ko"])

    def test_anchor_reset_and_continuity_frame_counts(self):
        modes = [payload["continuity_mode"] for payload in self.payloads.values()]
        self.assertEqual(modes.count("new_anchor"), 35)
        self.assertEqual(modes.count("continuity_frame"), 1)
        for clip_id, payload in self.payloads.items():
            if payload["continuity_mode"] == "continuity_frame":
                self.assertTrue(payload.get("continuity_from_clip"), clip_id)
                note = " ".join(payload["background_generation"]["continuity_notes"])
                self.assertIn("stable end frame", note, clip_id)

    def test_reconfiguration_plan_covers_every_clip(self):
        self.assertEqual(set(RECONFIGURATION_PLAN), set(self.payloads))
        allowed = {"유지", "프롬프트 수정", "컷 분할", "새 앵커 필요"}
        counts = {label: 0 for label in allowed}
        for clip_id, plan in RECONFIGURATION_PLAN.items():
            self.assertIn(plan["priority"], {"P0", "P1", "P2"}, clip_id)
            self.assertTrue(plan["reason"].strip(), clip_id)
            self.assertTrue(plan["next"].strip(), clip_id)
            self.assertTrue(plan["actions"], clip_id)
            self.assertTrue(set(plan["actions"]) <= allowed, clip_id)
            for action in plan["actions"]:
                counts[action] += 1
        self.assertEqual(counts["유지"], 8)
        self.assertEqual(counts["프롬프트 수정"], 8)
        self.assertEqual(counts["컷 분할"], 20)
        self.assertEqual(counts["새 앵커 필요"], 20)

    def test_full_scene_002_review_evidence_drives_v2_prompt_contract(self):
        self.assertEqual(SC01_002_REVIEW_EVIDENCE["review_count"], 75)
        self.assertEqual(SC01_002_REVIEW_EVIDENCE["by_clip"]["SC01-002_M05"]["acceptable"], 7)
        self.assertNotIn("SC01-002_M04B", self.payloads)
        for clip_id, payload in self.payloads.items():
            generation = payload["background_generation"]
            experiment = payload["prompt_experiment"]
            self.assertEqual(experiment["version"], 2, clip_id)
            self.assertTrue(experiment["review_focus_ko"].strip(), clip_id)
            if experiment["implementation"] == "experiment_v2_ready":
                self.assertTrue(payload["anchor"]["background_id"].endswith("_EXP_V2"), clip_id)
            self.assertIn("exact physical starting state", generation["prompt"], clip_id)
            self.assertTrue(generation["prompt_contract"]["opening_state_only"], clip_id)
            self.assertEqual(
                generation["prompt_contract"]["review_basis"],
                "SC01-002 full candidate review set",
                clip_id,
            )

    def test_new_ui_lists_only_the_new_episode_project(self):
        projects = ui_backend.list_msr_sequence_projects_action({})["projects"]
        ids = {item["project_id"] for item in projects}
        self.assertIn(PROJECT_ID, ids)
        detail = ui_backend.get_msr_sequence_project_clip_action(
            {"project_id": PROJECT_ID, "clip_id": "SC01-002_M04"}
        )
        expected_status = "reviewed" if detail["background_linked"] else "awaiting_background"
        self.assertEqual(detail["status"], expected_status)
        self.assertEqual(detail["can_register_msr"], detail["background_linked"])


if __name__ == "__main__":
    unittest.main()
