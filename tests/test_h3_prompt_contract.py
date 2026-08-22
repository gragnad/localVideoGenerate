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


if __name__ == "__main__":
    unittest.main()
