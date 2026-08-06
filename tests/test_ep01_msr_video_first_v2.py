from __future__ import annotations

import unittest
from pathlib import Path

import msr_prompt_projects
import msr_sequence_v2
import ui_backend
from scripts import generate_ep01_msr_video_first_v2 as generator


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = generator.PROJECT_ID


@unittest.skip("LTX 2.3 EP01 MSR 프로젝트 보관 처리")
class EP01MSRVideoFirstV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generator.main()
        cls.clips = msr_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        cls.payloads = {}
        for clip in cls.clips:
            path = ROOT / "prompt_projects" / clip["markdown_path"]
            cls.payloads[clip["clip_id"]] = msr_prompt_projects.extract_machine_payload(
                path.read_text(encoding="utf-8")
            )
        cls.by_frame = {payload["frame_id"]: payload for payload in cls.payloads.values()}

    def test_is_a_separate_clean_slate_project(self):
        self.assertEqual(PROJECT_ID, "RaisingaDragonSeason01_EP01_MSR_VIDEO_FIRST_V2")
        self.assertEqual(len(self.clips), 36)
        self.assertEqual(sum(c["requested_seconds"] for c in self.clips), 363)
        self.assertTrue(all(c["valid"] for c in self.clips))
        statuses = {clip["clip_id"]: clip["status"] for clip in self.clips}
        backgrounds = ROOT / "prompt_projects" / PROJECT_ID / "backgrounds"
        for clip_id, payload in self.payloads.items():
            suggested = payload["background_generation"]["suggested_filename"]
            expected = "reviewed" if (backgrounds / suggested).exists() else "awaiting_background"
            self.assertEqual(statuses[clip_id], expected, clip_id)

    def test_character_free_first_shot_reuses_anchor_as_reference_one(self):
        first = self.payloads["SC01-001_V01"]
        self.assertEqual(first["reference_mode"], "anchor_as_reference")
        self.assertEqual(first["references"], [])
        self.assertNotIn("Picture 1", first["global_prompt"])
        self.assertIn(
            "No character, creature or recognizable body is visible",
            first["background_generation"]["prompt"],
        )

        second = self.payloads["SC01-001_V02"]
        self.assertEqual(second["reference_mode"], "subject_references")
        self.assertTrue(second["references"])
        self.assertIn("Picture 1 — Character", second["global_prompt"])

        app = (ROOT / "web" / "public" / "app.js").read_text(encoding="utf-8")
        self.assertIn("reference_mode:payload.reference_mode||'subject_references'", app)
        self.assertIn("reference_mode==='anchor_as_reference'", app)
        self.assertIn("setMsrInputFile(msrFileInputs[0],referenceFile)", app)
        self.assertIn("Scene Anchor", app)

    def test_video_is_authored_before_anchor_prompt(self):
        for clip_id, payload in self.payloads.items():
            self.assertTrue(payload["video_design"]["authored_first"], clip_id)
            self.assertTrue(payload["video_design"]["compiled_video_prompt"].strip(), clip_id)
            generation = payload["background_generation"]
            self.assertEqual(generation["derived_from"], "video_design.opening_state", clip_id)
            expected_revision = generator.REGEN_REVISIONS.get(payload["sequence"], 2)
            self.assertEqual(generation["image_prompt_version"], expected_revision, clip_id)
            self.assertTrue(payload["anchor"]["background_id"].endswith(f"_IMAGE_R{expected_revision}"), clip_id)
            self.assertTrue(generation["suggested_filename"].endswith(f"_R{expected_revision}.png"), clip_id)
            self.assertIn(payload["video_design"]["space_bible"], generation["prompt"], clip_id)
            self.assertIn("STATIC FRAMING:", generation["prompt"], clip_id)
            self.assertIn("EXACT FROZEN STATE:", generation["prompt"], clip_id)
            self.assertNotRegex(
                generation["prompt"].lower(),
                r"\b(camera|push|tracking|track|drift|pan|flight)\b",
                clip_id,
            )
            self.assertNotIn("INCOMING CONTINUITY", generation["prompt"], clip_id)
            self.assertNotIn("same as frame", generation["prompt"].lower(), clip_id)

    def test_detailed_video_prompts_cover_every_clip(self):
        self.assertEqual(len(self.payloads), 36)
        for clip_id, payload in self.payloads.items():
            design = payload["video_design"]
            compiled = design["compiled_video_prompt"]
            self.assertEqual(design["prompt_version"], 2, clip_id)
            self.assertIn("candidate reviews", design["detail_basis"], clip_id)
            self.assertGreaterEqual(len(compiled.split()), 90, clip_id)
            self.assertIn("End ", compiled, clip_id)
            self.assertEqual(
                compiled,
                " ".join(row["prompt"] for row in payload["relay_segments"]),
                clip_id,
            )

    def test_restored_scenario_dialogue_and_reviewed_action_rules(self):
        cave_entry = self.payloads["SC01-003_V01"]
        self.assertIn("상당히 귀찮은 사람이다", cave_entry["video_design"]["compiled_video_prompt"])
        self.assertIn("상당히 귀찮은 사람이다", cave_entry["video_design"]["dialogue_ko"])

        fall = self.payloads["SC01-002_V02"]["video_design"]["compiled_video_prompt"]
        self.assertIn("brief cinematic slow-motion emphasis", fall)
        self.assertIn("full impact speed", fall)
        self.assertIn("spear stays in her hands", fall)

        children = self.payloads["SC01-002_V04"]["video_design"]["compiled_video_prompt"]
        self.assertIn("Only Child 1 moves his mouth", children)
        self.assertIn("Only Child 2 moves her mouth", children)

        finger = self.payloads["SC01-003_V04"]["video_design"]["compiled_video_prompt"]
        self.assertIn("single index fingertip", finger)
        self.assertIn("same gentle contact intact", finger)

    def test_frame_order_matches_story_time(self):
        expected = {
            "EP01_15": "SC01-003_V01",
            "EP01_16": "SC01-003_V02",
            "EP01_17": "SC01-003_V03",
            "EP01_18": "SC01-003_V04",
            "EP01_19": "SC01-003_V05",
            "EP01_20": "SC01-003_V06",
            "EP01_21": "SC01-003_V07",
            "EP01_22": "SC01-003_V08",
            "EP01_23": "SC01-004_V01",
            "EP01_24": "SC01-004_V02",
            "EP01_25": "SC01-004_V03",
            "EP01_26": "SC01-004_V04",
            "EP01_27": "SC01-004_V05",
            "EP01_28": "SC01-004_V06",
            "EP01_29": "SC01-004_V07",
            "EP01_30": "SC01-004_V08",
        }
        self.assertEqual({frame: self.by_frame[frame]["clip_id"] for frame in expected}, expected)
        self.assertIn("open hand", self.by_frame["EP01_17"]["video_design"]["opening_state"])
        self.assertIn("mouth is already gently closed", self.by_frame["EP01_18"]["video_design"]["opening_state"])
        self.assertIn("droplet is already suspended", self.by_frame["EP01_29"]["video_design"]["opening_state"])
        self.assertIn("bead is already on Lua's forehead", self.by_frame["EP01_30"]["video_design"]["opening_state"])

    def test_cave_uses_one_texture_and_preserves_wrap(self):
        cave_frames = [self.by_frame[f"EP01_{n:02d}"] for n in (15, 16, 17, 18, 20, 21, 22)]
        self.assertTrue(all(p["video_design"]["space_id"] == "cave_clean" for p in cave_frames))
        bibles = {p["video_design"]["space_bible"] for p in cave_frames}
        self.assertEqual(len(bibles), 1)
        self.assertIn("smooth dark wave-polished basalt", next(iter(bibles)))
        for frame in (21, 22):
            prompt = self.by_frame[f"EP01_{frame:02d}"]["background_generation"]["prompt"]
            self.assertIn("cloth bundle", prompt)
            self.assertIn("fully enclosed", prompt)
            self.assertIn("dragon head", prompt)
        self.assertEqual(
            self.by_frame["EP01_22"]["continuity_from_clip"],
            self.by_frame["EP01_21"]["clip_id"],
        )

    def test_house_uses_one_layout_and_shell_is_preestablished(self):
        house_frames = [self.by_frame[f"EP01_{n:02d}"] for n in range(23, 31)]
        self.assertTrue(all(p["video_design"]["space_id"] == "lua_house_day" for p in house_frames))
        self.assertEqual(len({p["video_design"]["space_bible"] for p in house_frames}), 1)
        for frame in (23, 24, 25, 26):
            prompt = self.by_frame[f"EP01_{frame:02d}"]["background_generation"]["prompt"]
            self.assertIn("palm-sized spiral shell", prompt)
            self.assertIn("low table", prompt)
        self.assertIn("wrapped", self.by_frame["EP01_23"]["background_generation"]["prompt"])

    def test_mir_scale_and_dragon_identity_are_contextual(self):
        for clip_id, payload in self.payloads.items():
            has_mir = any(ref["source_path"].endswith("YoungMir.png") for ref in payload["references"])
            if not has_mir:
                continue
            prompt = payload["background_generation"]["prompt"]
            self.assertIn("quadrupedal dragon hatchling", prompt, clip_id)
            self.assertNotIn("never a human baby or child", prompt, clip_id)
            if payload["video_design"]["space_id"] in {"lua_house_day", "lua_house_night"}:
                self.assertIn("fits inside the shallow water bowl", prompt, clip_id)
            else:
                self.assertNotIn("shallow water bowl", prompt, clip_id)

    def test_failed_visual_states_are_explicitly_separated(self):
        p23 = self.by_frame["EP01_23"]["background_generation"]["prompt"]
        self.assertIn("cloth-wrapped Mir bundle", p23)
        self.assertIn("bowl is empty", p23)
        self.assertIn("shell is already on the low table", p23)

        p26 = self.by_frame["EP01_26"]["background_generation"]["prompt"]
        self.assertIn("exactly one palm-sized spiral shell", p26)
        self.assertIn("empty hands", p26)

        p29 = self.by_frame["EP01_29"]["background_generation"]["prompt"]
        self.assertIn("Exactly one clear water droplet", p29)
        self.assertIn("touches neither face", p29)

        p30 = self.by_frame["EP01_30"]["background_generation"]["prompt"]
        self.assertIn("No droplet remains in the air", p30)
        self.assertIn("glowing wrist mark", p30)
        self.assertIn("glowing chest mark", p30)

    def test_breakwater_reverse_screen_direction_is_explicit(self):
        children = self.by_frame["EP01_11"]["background_generation"]["prompt"]
        lua = self.by_frame["EP01_12"]["background_generation"]["prompt"]
        self.assertIn("screen-right", children)
        self.assertIn("empty frame-right", children)
        self.assertIn("screen-left", lua)
        self.assertIn("empty frame-left", lua)

    def test_reference_slots_and_relay_duration(self):
        for clip_id, payload in self.payloads.items():
            self.assertEqual(payload["workflow"], msr_sequence_v2.WORKFLOW, clip_id)
            slots = [int(ref["slot"]) for ref in payload["references"]]
            self.assertEqual(slots, sorted(set(slots)), clip_id)
            self.assertLessEqual(sum(slot in {1, 2} for slot in slots), 2, clip_id)
            self.assertEqual(
                sum(float(row["seconds"]) for row in payload["relay_segments"]),
                float(payload["requested_seconds"]),
                clip_id,
            )

    def test_only_visual_failures_are_revision_r3(self):
        expected = {"EP01_01", "EP01_06", "EP01_18", "EP01_28", "EP01_30", "EP01_32"}
        actual = {
            payload["frame_id"]
            for payload in self.payloads.values()
            if payload["background_generation"]["image_prompt_version"] == 3
        }
        self.assertEqual(actual, expected)
        for frame_id in expected:
            generation = self.by_frame[frame_id]["background_generation"]
            self.assertTrue(generation["suggested_filename"].endswith("_R3.png"))
        self.assertIn("no face, head, statue or additional dragon", self.by_frame["EP01_06"]["background_generation"]["prompt"])
        self.assertIn("clear physical contact", self.by_frame["EP01_18"]["background_generation"]["prompt"])
        self.assertIn("no magical effect", self.by_frame["EP01_28"]["background_generation"]["prompt"])
        self.assertIn("flat translucent crown-horned cast shadow", self.by_frame["EP01_32"]["background_generation"]["prompt"])

    def test_background_cards_show_stable_two_digit_sequence(self):
        app = (ROOT / "web" / "public" / "app.js").read_text(encoding="utf-8")
        self.assertIn("items.map((bg,index)=>", app)
        self.assertIn("String(index+1).padStart(2,'0')", app)

    def test_ui_lists_v2_independently(self):
        projects = ui_backend.list_msr_sequence_projects_action({})["projects"]
        ids = {item["project_id"] for item in projects}
        self.assertIn(PROJECT_ID, ids)
        self.assertIn("RaisingaDragonSeason01_EP01_MSR_CONTINUITY_V1", ids)
        ready = ui_backend.get_msr_sequence_project_clip_action(
            {"project_id": PROJECT_ID, "clip_id": "SC01-003_V01"}
        )
        self.assertEqual(ready["status"], "reviewed")
        self.assertTrue(ready["can_register_msr"])
        regenerate = ui_backend.get_msr_sequence_project_clip_action(
            {"project_id": PROJECT_ID, "clip_id": "SC01-003_V04"}
        )
        suggested = regenerate["machine_payload"]["background_generation"]["suggested_filename"]
        self.assertTrue(suggested.endswith("_R3.png"))
        expected_ready = (
            ROOT / "prompt_projects" / PROJECT_ID / "backgrounds" / suggested
        ).exists()
        self.assertEqual(regenerate["status"], "reviewed" if expected_ready else "awaiting_background")
        self.assertEqual(regenerate["can_register_msr"], expected_ready)


if __name__ == "__main__":
    unittest.main()
