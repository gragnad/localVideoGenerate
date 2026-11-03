from __future__ import annotations

import copy
import unittest

import h3_prompt_contract as contract


def valid_spec() -> dict:
    return {
        "duration_seconds": 4,
        "subjects": [{
            "subject_id": 1,
            "picture_id": 1,
            "name": "Lua",
            "description": "A young spear fighter in blue dragon-scale armor",
        }],
        "summary": "Lua releases a charged spear strike that clears the path.",
        "retention_analysis": [{
            "subject_id": 1,
            "shots": [1],
            "marker": "fully_preserved",
            "description": "Preserve her face, armor, spear, and proportions",
        }],
        "style_opening": [
            "Moonlit stone ruins with wet surfaces and sharp cyan reflections"
        ],
        "shots": [{
            "number": 1,
            "description": (
                "A low three-quarter view frames <Subject 1> Lua as she plants her "
                "lead foot, turns her torso with the spear, and drives its charged "
                "tip forward. The impact throws the blocking fragments outward and "
                "leaves the newly opened passage visible behind them."
            ),
        }],
        "overall_soundscape": "Stone cracks, spear hum, and a short impact burst.",
        "non_diegetic_music": "Fast low strings rise into one brass hit.",
    }


class H3PromptContractTest(unittest.TestCase):
    def test_renderer_produces_minimal_valid_six_section_prompt(self):
        prompt = contract.render_prompt(valid_spec())
        report = contract.validate_prompt(prompt, duration_seconds=4)

        self.assertTrue(report.valid, report.as_dict())
        self.assertLess(len(prompt.split()), 170)
        self.assertEqual(contract.SECTION_NAMES, report.section_names)
        self.assertNotIn("CAMERA:", prompt)
        self.assertNotIn("ACTION:", prompt)

    def test_short_prompt_has_no_legacy_minimum_word_failure(self):
        prompt = contract.render_prompt(valid_spec())
        self.assertTrue(contract.validate_prompt(prompt, duration_seconds=4).valid)

    def test_rejects_subject_name_before_shot_label(self):
        spec = valid_spec()
        spec["shots"][0]["description"] = (
            "Lua runs into frame before <Subject 1> braces with her spear."
        )
        with self.assertRaises(contract.PromptContractError) as raised:
            contract.render_prompt(spec)
        self.assertIn(
            "subject_label_after_name",
            {issue.code for issue in raised.exception.report.errors},
        )

    def test_rejects_legacy_camera_action_blocks(self):
        spec = valid_spec()
        spec["shots"][0]["description"] = (
            "<Subject 1> Lua braces. CAMERA: locked wide. ACTION: Lua attacks."
        )
        with self.assertRaises(contract.PromptContractError) as raised:
            contract.render_prompt(spec)
        self.assertIn(
            "legacy_camera_action_labels",
            {issue.code for issue in raised.exception.report.errors},
        )

    def test_dialogue_requires_explicit_speaker_before_each_line(self):
        spec = valid_spec()
        spec["shots"][0]["description"] = (
            "<Subject 1> Lua looks up. <d>[Korean]멈춰.</d>"
        )
        with self.assertRaises(contract.PromptContractError) as raised:
            contract.render_prompt(spec)
        self.assertIn(
            "dialogue_speaker_missing",
            {issue.code for issue in raised.exception.report.errors},
        )

        spec["shots"][0]["description"] = (
            "A tracking view follows <Subject 1> Lua as she keeps running, turns "
            "her spear toward the threat, and shouts <Subject 1> (S1) "
            "<d>[Korean]멈춰.</d> without breaking stride."
        )
        self.assertTrue(contract.validate_prompt(contract.render_prompt(spec)).valid)

    def test_rejects_too_many_shots_for_short_duration(self):
        spec = valid_spec()
        spec["shots"] = [
            {
                "number": 1,
                "description": "<Subject 1> Lua raises her spear.",
            },
            {
                "number": 2,
                "start_seconds": 1.2,
                "description": "<Subject 1> Lua turns toward the doorway.",
            },
            {
                "number": 3,
                "start_seconds": 2.7,
                "description": "<Subject 1> Lua drives the spear forward.",
            },
        ]
        spec["retention_analysis"][0]["shots"] = [1, 2, 3]
        with self.assertRaises(contract.PromptContractError) as raised:
            contract.render_prompt(spec)
        self.assertIn(
            "shot_budget",
            {issue.code for issue in raised.exception.report.errors},
        )

    def test_allows_four_fast_storyboard_shots_in_eight_seconds(self):
        spec = valid_spec()
        spec["duration_seconds"] = 8
        spec["shots"] = [
            {"number": 1, "description": "<Subject 1> Lua starts one continuous shield press."},
            {
                "number": 2,
                "start_seconds": 2,
                "description": "<Subject 1> Lua continues the same pressure without resetting.",
            },
            {
                "number": 3,
                "start_seconds": 4,
                "description": "<Subject 1> Lua slides while the same force continues.",
            },
            {
                "number": 4,
                "start_seconds": 6,
                "description": "<Subject 1> Lua completes the carried action.",
            },
        ]
        spec["retention_analysis"][0]["shots"] = [1, 2, 3, 4]
        prompt = contract.render_prompt(spec)
        self.assertTrue(contract.validate_prompt(prompt, duration_seconds=8).valid)

    def test_allows_four_fast_storyboard_shots_in_six_point_five_seconds(self):
        spec = valid_spec()
        spec["duration_seconds"] = 6.5
        spec["shots"] = [
            {"number": 1, "description": "<Subject 1> Lua starts one continuous dodge."},
            {
                "number": 2,
                "start_seconds": 1.625,
                "description": "<Subject 1> Lua carries the same dodge under the hand.",
            },
            {
                "number": 3,
                "start_seconds": 3.25,
                "description": "<Subject 1> Lua keeps moving without a reset.",
            },
            {
                "number": 4,
                "start_seconds": 4.875,
                "description": "<Subject 1> Lua completes the same dodge.",
            },
        ]
        spec["retention_analysis"][0]["shots"] = [1, 2, 3, 4]
        prompt = contract.render_prompt(spec)
        self.assertTrue(contract.validate_prompt(prompt, duration_seconds=6.5).valid)

    def test_allows_six_storyboard_shots_in_fifteen_seconds_when_explicit(self):
        spec = valid_spec()
        spec["duration_seconds"] = 15
        spec["allow_six_shots"] = True
        spec["shots"] = []
        for number in range(1, 7):
            row = {
                "number": number,
                "description": f"<Subject 1> Lua continues chronological action {number}.",
            }
            if number > 1:
                row["start_seconds"] = (number - 1) * 2.5
            spec["shots"].append(row)
        spec["retention_analysis"][0]["shots"] = list(range(1, 7))

        prompt = contract.render_prompt(spec)
        allowed = contract.validate_prompt(
            prompt,
            duration_seconds=15,
            allow_six_shots=True,
        )
        rejected = contract.validate_prompt(prompt, duration_seconds=15)

        self.assertTrue(allowed.valid, allowed.as_dict())
        self.assertIn("shot_budget", {issue.code for issue in rejected.errors})

    def test_storyboard_picture_is_independent_from_subject_numbering(self):
        spec = valid_spec()
        spec["duration_seconds"] = 8
        spec["subjects"][0].pop("picture_id")
        spec["subjects"][0]["picture_ids"] = [1, 2]
        spec["pictures"] = [{
            "picture_id": 4,
            "name": "the chronological four-panel storyboard",
            "description": (
                "Read its 2x2 grid top-left, top-right, bottom-left, then "
                "bottom-right as Shot 1 through Shot 4"
            ),
        }]
        spec["retention_analysis"] = [
            {
                "subject_id": 1,
                "shots": [1, 2, 3, 4],
                "marker": "fully_preserved",
                "description": "Preserve Lua across both identity references",
            },
            {
                "picture_id": 4,
                "shots": [1, 2, 3, 4],
                "marker": "fully_preserved",
                "description": "Preserve panel order, blocking, and action causality",
            },
        ]
        spec["shots"] = []
        for number, ordinal in enumerate(("first", "second", "third", "fourth"), start=1):
            row = {
                "number": number,
                "description": (
                    f"Use the {ordinal} planned composition from <Picture 4> only for "
                    f"this Shot's viewpoint and subject placement while <Subject 1> Lua "
                    "continues one action."
                ),
            }
            if number > 1:
                row["start_seconds"] = (number - 1) * 2
            spec["shots"].append(row)

        prompt = contract.render_prompt(spec)
        report = contract.validate_prompt(prompt, duration_seconds=8)

        self.assertTrue(report.valid, report.as_dict())
        self.assertIn("from <Picture 1> and <Picture 2>", prompt)
        self.assertIn("<Picture 4> is the chronological four-panel storyboard", prompt)
        self.assertNotIn("<Subject 4>", prompt)

    def test_split_dialogue_may_continue_without_a_second_speaker_tag(self):
        spec = valid_spec()
        spec["shots"][0]["description"] = (
            "Under the dusk sky <Subject 1> Lua grips her spear and <Subject 1> (S1) says, "
            "<d>[Korean]멈춰.</d> She pauses to take a ragged breath, then continues, "
            "<d>[Korean]돌아가.</d> Her breathing stays heavy."
        )
        self.assertTrue(contract.validate_prompt(contract.render_prompt(spec)).valid)

        spec["shots"][0]["description"] = (
            "Under the dusk sky <Subject 1> Lua grips her spear and <Subject 1> (S1) says, "
            "<d>[Korean]멈춰.</d> She looks away. <d>[Korean]돌아가.</d>"
        )
        with self.assertRaises(contract.PromptContractError) as raised:
            contract.render_prompt(spec)
        self.assertIn(
            "dialogue_speaker_missing",
            {issue.code for issue in raised.exception.report.errors},
        )

    def test_ir_style_findings_are_warnings_only(self):
        spec = valid_spec()
        spec["shots"][0]["description"] = (
            "A wide view from far out frames <Subject 1> Lua small in the frame; "
            "from the first frame she braces, and <Subject 1> (S1) says, "
            "<d>[Korean]…멈춰. 돌아가.</d> The frame holds on her until the shot ends."
        )
        report = contract.validate_prompt(contract.render_prompt(spec), duration_seconds=4)
        self.assertTrue(report.valid, report.as_dict())
        codes = {issue.code for issue in report.warnings}
        for code in ("style_frame_hold", "style_from_first_frame", "style_far_small", "style_semicolon",
                     "style_shot_light_missing", "style_dialogue_leading_ellipsis",
                     "style_dialogue_multi_sentence"):
            self.assertIn(code, codes)

        spec["shots"][0]["description"] = (
            "A medium shot of <Subject 1> Lua, braced at the right edge of frame. "
            "The camera is fixed at her eye level, viewing her from the side. "
            "The red dusk sky lights her face from the left. "
            "She draws a sharp breath and <Subject 1> (S1) says, <d>[Korean]멈춰.</d> "
            "She pauses to take a ragged breath, then continues, <d>[Korean]돌아가.</d> "
            "Her chest keeps heaving as the wind hisses over the stones."
        )
        report = contract.validate_prompt(contract.render_prompt(spec), duration_seconds=4)
        self.assertTrue(report.valid, report.as_dict())
        self.assertFalse([i.code for i in report.warnings if i.code.startswith("style_")])

    def test_shot_structure_and_quoted_sound_warnings(self):
        spec = valid_spec()
        spec["shots"][0]["description"] = (
            "A fixed medium close-up of <Subject 1> Lua, her black ponytail and navy wrap top, standing on the stone path, "
            "framed from the top of her head to her chest with a hand-span of space above her head, at her eye level. "
            "Torchlight lights her face. She knocks on the branch, and a clear 'tong— tong—' answers."
        )
        report = contract.validate_prompt(contract.render_prompt(spec), duration_seconds=4)
        self.assertTrue(report.valid, report.as_dict())
        codes = {issue.code for issue in report.warnings}
        for code in ("style_shot_opener_long", "style_camera_sentence_missing", "style_romanized_onomatopoeia"):
            self.assertIn(code, codes)

        spec["shots"][0]["description"] = (
            "A medium close-up of <Subject 1> Lua, standing on the stone path. "
            "The camera is fixed at her eye level, viewing her from the front. "
            "Torchlight lights Lua's face from the left. She knocks on the branch, and a clear, ringing hollow tone answers."
        )
        report = contract.validate_prompt(contract.render_prompt(spec), duration_seconds=4)
        self.assertFalse([i.code for i in report.warnings if i.code.startswith("style_")])


    def test_ep08_face_low_prop_wide_small_and_creature_sound_warnings(self):
        spec = valid_spec()
        spec["shots"][0]["description"] = (
            "A medium close-up of <Subject 1> Lua, sitting on a low stool. "
            "The camera is fixed at her seated eye level, viewing her from the front. "
            "Firelight lights her face. The old shaft lies across her knees as the coals crackle."
        )
        codes = {i.code for i in contract.validate_prompt(contract.render_prompt(spec), duration_seconds=4).warnings}
        self.assertIn("style_mcu_low_prop", codes)

        spec["shots"][0]["description"] = (
            "A wide view of the harbor at dusk. The camera is fixed on the pier, viewing the sea. "
            "Dusk light glows on the water. The boat sits small at the center of the frame as waves lap."
        )
        codes = {i.code for i in contract.validate_prompt(contract.render_prompt(spec), duration_seconds=4).warnings}
        self.assertIn("style_wide_subject_small", codes)

        spec["shots"][0]["description"] = (
            "A close-up of <Subject 1> Mir by the bench. The camera is fixed at its eye level, viewing its face. "
            "Window light falls on its face. Mir tilts its head, and <Subject 1> (S1) sniffs, <d>[Korean] 킁?</d>"
        )
        codes = {i.code for i in contract.validate_prompt(contract.render_prompt(spec), duration_seconds=4).warnings}
        self.assertIn("style_creature_onomatopoeia_dialogue", codes)

        spec["shots"][0]["description"] = (
            "A medium shot of <Subject 1> Lua, sitting on a low stool. "
            "The camera is fixed at her seated eye level, viewing her from the front. "
            "Firelight lights her face. She holds the shaft at chest height, and <Subject 1> (S1) says, <d>[Korean] 네.</d>"
        )
        codes = {i.code for i in contract.validate_prompt(contract.render_prompt(spec), duration_seconds=4).warnings}
        for code in ("style_mcu_low_prop", "style_wide_subject_small", "style_creature_onomatopoeia_dialogue"):
            self.assertNotIn(code, codes)

if __name__ == "__main__":
    unittest.main()
