from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

import h3_prompt_project_builder
import h3_prompt_contract
import h3_prompt_projects


def prompt_spec() -> dict:
    return {
        "subjects": [{
            "subject_id": 1,
            "picture_id": 1,
            "name": "Lua",
            "description": "A young spear fighter in blue dragon-scale armor",
        }],
        "summary": "Lua clears the blocked passage with one charged spear strike.",
        "retention_analysis": [{
            "subject_id": 1,
            "shots": [1],
            "marker": "fully_preserved",
            "description": "Preserve her face, armor, spear, and proportions",
        }],
        "style_opening": [],
        "overall_soundscape": "Spear hum, boots on stone, and one impact.",
        "non_diegetic_music": "Fast low strings end on one brass hit.",
    }


def event_contract() -> dict:
    return {
        "shared_event": "Lua charges one spear strike and clears the blocked passage.",
        "bridge_in_id": "blocked_passage",
        "bridge_out_id": "open_passage",
        "boundary_policy": "referenced_cut",
        "source_shot_ids": ["SH01"],
        "incoming_reference_subjects": [1],
        "outgoing_reference_subjects": [1],
        "incoming_bridge": "<Subject 1> Lua begins with both feet braced before the blocked passage.",
        "outgoing_bridge": "End on <Subject 1> Lua looking through the newly opened passage.",
        "beats": [
            {"beat_id": "charge", "description": "<Subject 1> Lua gathers cyan energy at the spear tip."},
            {"beat_id": "strike", "description": "<Subject 1> Lua drives the charged spear into the floor and redirects the same debris to both sides."},
            {"beat_id": "result", "description": "<Subject 1> Lua settles with the cleared route visible beyond her."},
        ],
        "candidate_plans": {
            "A": {
                "emphasis": "cause-to-result spatial evidence",
                "shots": [
                    {"camera": "A wide view establishes the obstruction and contact line.", "beat_ids": ["charge"]},
                    {"start_seconds": 2.4, "camera": "A side medium view isolates the physical strike.", "beat_ids": ["strike"]},
                    {"start_seconds": 5.4, "camera": "A frontal result view reveals the open passage.", "beat_ids": ["result"]},
                ],
            },
            "B": {
                "emphasis": "whole-body mechanics followed by the result",
                "shots": [
                    {"camera": "A three-quarter track follows the complete load and release.", "beat_ids": ["charge", "strike"]},
                    {"start_seconds": 5.0, "camera": "An over-shoulder view holds the cleared destination.", "beat_ids": ["result"]},
                ],
            },
            "C": {
                "emphasis": "impact and reaction with a separate closing clue",
                "shots": [
                    {"camera": "A low reverse view establishes the blocked route.", "beat_ids": ["charge"]},
                    {"start_seconds": 2.0, "camera": "A contact-height insert follows debris leaving the path.", "beat_ids": ["strike"]},
                    {"start_seconds": 4.8, "camera": "A quiet profile close settles on the decision to advance.", "beat_ids": ["result"]},
                ],
            },
        },
    }


class H3PromptProjectBuilderTest(unittest.TestCase):
    def test_builds_only_a_new_valid_project_with_three_independent_prompts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_dir = root / "input"
            input_dir.mkdir()
            (input_dir / "lua.png").write_bytes(b"png")
            variants = []
            for variant_id, rationale in (
                ("A", "wide spatial impact evidence"),
                ("D", "three-quarter body mechanics"),
                ("E", "result-first debris evidence"),
            ):
                variants.append({
                    "variant_id": variant_id,
                    "rationale": rationale,
                    "prompt_spec": prompt_spec(),
                })
            contract = event_contract()
            contract["candidate_plans"] = {
                "A": contract["candidate_plans"]["A"],
                "D": contract["candidate_plans"]["B"],
                "E": contract["candidate_plans"]["C"],
            }
            spec = {
                "project_id": "dragon_ep00_clean",
                "title": "Dragon EP00 Clean",
                "clips": [{
                    "scene_id": "EP00-S01",
                    "clip_id": "EP00-S01-NC01",
                    "sequence": 1,
                    "duration_seconds": 8,
                    "references": [{
                        "picture_index": 1,
                        "role": "lua",
                        "copy_from": "lua.png",
                    }],
                    "event_contract": contract,
                    "prompt_variants": variants,
                }],
            }
            spec_path = input_dir / "project.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")

            result = h3_prompt_project_builder.build_project(root, spec_path)
            clip = h3_prompt_projects.load_clip(
                root, "dragon_ep00_clean", "EP00-S01-NC01"
            )

            self.assertEqual(1, result["clip_count"])
            self.assertTrue(clip["ready"], clip["errors"])
            self.assertEqual(["A", "D", "E"], [
                row["variant_id"] for row in clip["prompt_variants"]
            ])
            self.assertEqual(3, len({
                row["detailed_description"] for row in clip["prompt_variants"]
            }))
            incoming = event_contract()["incoming_bridge"]
            outgoing = event_contract()["outgoing_bridge"]
            self.assertTrue(all(
                incoming in row["detailed_description"]
                for row in clip["prompt_variants"]
            ))
            self.assertTrue(all(
                outgoing in row["detailed_description"]
                for row in clip["prompt_variants"]
            ))
            self.assertEqual([3, 2, 3], [
                len(re.findall(r"^\[Shot ", row["detailed_description"], re.MULTILINE))
                for row in clip["prompt_variants"]
            ])
            self.assertEqual(
                h3_prompt_projects.EVENT_CONTRACT_VERSION,
                clip["event_contract_version"],
            )
            self.assertEqual(["SH01"], clip["event_contract"]["source_shot_ids"])
            self.assertEqual(incoming, clip["event_contract"]["incoming_bridge"])
            self.assertEqual(outgoing, clip["event_contract"]["outgoing_bridge"])
            self.assertTrue((
                root
                / "prompt_projects/dragon_ep00_clean/assets/EP00-S01-NC01/picture_1.png"
            ).is_file())
            manifest = json.loads((
                root / "prompt_projects/dragon_ep00_clean/manifest.json"
            ).read_text(encoding="utf-8"))
            self.assertEqual("ready", manifest["review_status"])
            self.assertEqual({
                "clip_count": 1,
                "prompt_count": 3,
                "total_duration_seconds": 8.0,
            }, manifest["build_facts"])
            self.assertIs(False, manifest["queue_authorized"])
            self.assertIs(False, manifest["video_generation_authorized"])
            self.assertIs(False, manifest["queue_registration_performed"])
            self.assertIs(False, manifest["video_generation_performed"])

            with self.assertRaises(FileExistsError):
                h3_prompt_project_builder.build_project(root, spec_path)

    def test_asset_catalog_and_prompt_base_expand_into_each_variant(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_dir = root / "input"
            input_dir.mkdir()
            (input_dir / "lua.png").write_bytes(b"png")
            spec = {
                "project_id": "dragon_ep00_catalog",
                "asset_catalog": {
                    "lua": {
                        "role": "lua",
                        "copy_from": "lua.png",
                        "subject_name": "Lua",
                        "subject_description": "A young spear fighter in blue armor",
                        "retention_marker": "fully_preserved",
                        "retention_description": "Preserve her face and armor",
                    },
                },
                "clips": [{
                    "scene_id": "EP00-S01",
                    "clip_id": "EP00-S01-NC01",
                    "sequence": 1,
                    "duration_seconds": 8,
                    "references": ["lua"],
                    "prompt_base": {
                        "summary": "Lua completes one continuous defensive action.",
                        "style_opening": [],
                        "overall_soundscape": "Water pressure and one impact.",
                        "non_diegetic_music": "One rising low string note.",
                    },
                    "event_contract": event_contract(),
                    "prompt_variants": [{
                        "variant_id": variant_id,
                        "rationale": rationale,
                        "prompt_spec": {},
                    } for variant_id, rationale in (
                        ("A", "wide spatial proof"),
                        ("B", "profile body mechanics"),
                        ("C", "impact result evidence"),
                    )],
                }],
            }
            spec_path = input_dir / "project.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")

            result = h3_prompt_project_builder.build_project(root, spec_path)
            clip = h3_prompt_projects.load_clip(
                root, "dragon_ep00_catalog", "EP00-S01-NC01"
            )

            self.assertEqual(1, result["ready_count"])
            self.assertEqual("lua", clip["references"][0]["role"])
            self.assertIn("<Subject 1> is Lua from <Picture 1>", clip["video_prompt"])
            self.assertIn("fully_preserved", clip["video_prompt"])

    def test_rejects_one_shot_candidate_for_an_eight_second_clip(self):
        contract = event_contract()
        for variant_id in ("A", "B", "C"):
            contract["candidate_plans"][variant_id]["shots"] = [{
                "camera": "One unbroken view attempts to contain the whole event.",
                "beat_ids": ["charge", "strike", "result"],
            }]

        with self.assertRaisesRegex(ValueError, "Shot 2~4개"):
            h3_prompt_project_builder._candidate_shots(
                "EP00-S01-NC01", 8, contract, "A"
            )

    def test_rejects_required_dialogue_missing_from_all_candidate_prompts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_dir = root / "input"
            input_dir.mkdir()
            (input_dir / "lua.png").write_bytes(b"png")
            spec = {
                "project_id": "dialogue_guard",
                "clips": [{
                    "scene_id": "EP00-S01",
                    "clip_id": "EP00-S01-NC01",
                    "sequence": 1,
                    "duration_seconds": 8,
                    "references": [{
                        "picture_index": 1,
                        "role": "lua",
                        "copy_from": "lua.png",
                    }],
                    "event_contract": event_contract(),
                    "required_dialogue": ["멈춰."],
                    "prompt_variants": [{
                        "variant_id": variant_id,
                        "rationale": f"candidate {variant_id}",
                        "prompt_spec": prompt_spec(),
                    } for variant_id in ("A", "B", "C")],
                }],
            }
            spec_path = input_dir / "project.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "required_dialogue"):
                h3_prompt_project_builder.build_project(root, spec_path)

    def test_rejects_unreferenced_object_merge_without_two_source_shots(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_dir = root / "input"
            input_dir.mkdir()
            (input_dir / "lua.png").write_bytes(b"png")
            contract = event_contract()
            contract["boundary_policy"] = "merged_unreferenced_object"
            contracts_path = input_dir / "contracts.json"
            contracts_path.write_text(json.dumps({
                "version": "independent_shot_plans_v2",
                "clips": {"EP00-S01-NC01": contract},
            }), encoding="utf-8")
            spec = {
                "project_id": "invalid_merge",
                "event_contracts_file": "contracts.json",
                "clips": [{
                    "scene_id": "EP00-S01",
                    "clip_id": "EP00-S01-NC01",
                    "sequence": 1,
                    "duration_seconds": 8,
                    "references": [{
                        "picture_index": 1,
                        "role": "lua",
                        "copy_from": "lua.png",
                    }],
                    "prompt_variants": [{
                        "variant_id": variant_id,
                        "rationale": rationale,
                        "prompt_spec": prompt_spec(),
                    } for variant_id, rationale in (
                        ("A", "wide spatial proof"),
                        ("B", "body mechanics"),
                        ("C", "result evidence"),
                    )],
                }],
            }
            spec_path = input_dir / "project.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "source_shot_ids가 2개 이상"):
                h3_prompt_project_builder.build_project(root, spec_path)

    def test_storyboard_contract_keeps_grid_metadata_out_of_shot_text(self):
        contract = event_contract()
        contract.update({
            "storyboard_required": True,
            "storyboard_picture_id": 2,
            "storyboard_panel_count": 4,
            "beats": [
                {"beat_id": f"b{number}", "description": f"<Subject 1> Lua performs beat {number}."}
                for number in range(1, 5)
            ],
        })
        positions = ("top-left", "top-right", "bottom-left", "bottom-right")
        contract["candidate_plans"] = {}
        for variant_id in ("A", "D", "E"):
            shots = []
            for number, position in enumerate(positions, start=1):
                shot = {
                    "panel_index": number,
                    "panel_position": position,
                    "camera": f"A distinct {variant_id} camera composition preserves the action axis.",
                    "beat_ids": [f"b{number}"],
                }
                if number > 1:
                    shot["start_seconds"] = (number - 1) * 2
                shots.append(shot)
            contract["candidate_plans"][variant_id] = {
                "emphasis": f"{variant_id} storyboard interpretation",
                "shots": shots,
            }

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_dir = root / "input"
            input_dir.mkdir()
            (input_dir / "lua.png").write_bytes(b"png")
            (input_dir / "storyboard.png").write_bytes(b"png")
            spec = {
                "project_id": "storyboard_contract",
                "asset_catalog": {
                    "lua": {
                        "copy_from": "lua.png",
                        "subject_id": 1,
                        "subject_name": "Lua",
                        "subject_description": "A spear fighter in blue armor",
                    },
                    "storyboard": {
                        "copy_from": "storyboard.png",
                        "reference_kind": "storyboard",
                        "storyboard_panel_count": 4,
                        "storyboard_reading_order": "top-left to bottom-right",
                        "storyboard_beats": ["b1", "b2", "b3", "b4"],
                        "standalone_picture_name": "the chronological storyboard",
                        "standalone_picture_description": "Preserve its four-panel order and blocking",
                    },
                },
                "clips": [{
                    "scene_id": "EP00-S01",
                    "clip_id": "EP00-S01-NC01",
                    "sequence": 1,
                    "duration_seconds": 8,
                    "references": ["lua", "storyboard"],
                    "prompt_base": {
                        "summary": "Lua completes one continuous four-beat action.",
                        "style_opening": [],
                        "overall_soundscape": "Four connected impacts.",
                        "non_diegetic_music": "One accelerating string phrase.",
                    },
                    "event_contract": contract,
                    "prompt_variants": [{
                        "variant_id": variant_id,
                        "rationale": f"distinct {variant_id} camera path",
                        "prompt_spec": {},
                    } for variant_id in ("A", "D", "E")],
                }],
            }
            spec_path = input_dir / "project.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")

            h3_prompt_project_builder.build_project(root, spec_path)
            clip = h3_prompt_projects.load_clip(
                root, "storyboard_contract", "EP00-S01-NC01"
            )

            self.assertTrue(clip["ready"], clip["errors"])
            for variant in clip["prompt_variants"]:
                detail = variant["detailed_description"]
                self.assertEqual(4, detail.count("planned composition from <Picture 2>"))
                for ordinal in ("first", "second", "third", "fourth"):
                    self.assertIn(f"the {ordinal} planned composition", detail)
                self.assertIsNone(re.search(
                    r"\b(?:2x2|grid|quadrant|top-left|top-right|bottom-left|bottom-right|panel)\b",
                    detail,
                    re.IGNORECASE,
                ))
            self.assertIn("<Picture 2> is the chronological storyboard", clip["video_prompt"])

    def test_storyboard_plan_allows_shot_local_camera_without_next_panel_transition(self):
        contract = event_contract()
        contract.update({
            "storyboard_required": True,
            "storyboard_picture_id": 2,
            "storyboard_panel_count": 4,
            "beats": [
                {"beat_id": f"b{number}", "description": f"beat {number}"}
                for number in range(1, 5)
            ],
        })
        positions = ("top-left", "top-right", "bottom-left", "bottom-right")
        contract["candidate_plans"] = {
            "D": {
                "emphasis": "derived path",
                "shots": [{
                    "panel_index": number,
                    "panel_position": position,
                    "camera": "A camera view.",
                    "beat_ids": [f"b{number}"],
                    **({"start_seconds": (number - 1) * 2} if number > 1 else {}),
                } for number, position in enumerate(positions, start=1)],
            },
            "A": {"emphasis": "unused", "shots": []},
            "E": {"emphasis": "unused", "shots": []},
        }

        shots, emphasis = h3_prompt_project_builder._candidate_shots(
            "EP00-S01-NC01", 8, contract, "D"
        )
        self.assertEqual(4, len(shots))
        self.assertEqual("derived path", emphasis)
        self.assertTrue(all("planned composition from <Picture 2>" in row["description"] for row in shots))
        self.assertTrue(all("next panel" not in row["description"].lower() for row in shots))

        contract["candidate_plans"]["D"]["shots"][0]["transition_to_next"] = (
            "Track toward the following planned composition."
        )
        with self.assertRaisesRegex(ValueError, "transition_to_next"):
            h3_prompt_project_builder._candidate_shots(
                "EP00-S01-NC01", 8, contract, "D"
            )

    def test_action_storyboard_is_isolated_between_delegated_entry_and_exit_shots(self):
        mode = h3_prompt_projects.ISOLATED_ACTION_STORYBOARD_MODE
        contract = event_contract()
        contract.update({
            "storyboard_required": True,
            "storyboard_picture_id": 2,
            "storyboard_panel_count": 4,
            "storyboard_reading_order": "top-left, top-right, bottom-left, bottom-right",
            "storyboard_mode": mode,
            "beats": [
                {
                    "beat_id": "entry",
                    "description": "<Subject 1> Lua approaches to the instant before contact.",
                },
                *[
                {
                    "beat_id": f"b{number}",
                    "description": f"<Subject 1> Lua reaches action checkpoint {number}.",
                }
                for number in range(1, 5)
                ],
                {
                    "beat_id": "exit",
                    "description": "<Subject 1> Lua settles into the next visible event state.",
                },
            ],
            "candidate_plans": {
                variant_id: {
                    "emphasis": f"{variant_id} delegated entry and exit treatment",
                    "shots": [
                        {
                            "camera": f"Delegated entry camera treatment {variant_id}.",
                            "beat_ids": ["entry"],
                        },
                        {
                            "camera": "This is <Subject 1> Lua's fast defensive action.",
                            "storyboard_controlled": True,
                            "beat_ids": ["b1", "b2", "b3", "b4"],
                        },
                        {
                            "camera": f"Delegated exit camera treatment {variant_id}.",
                            "beat_ids": ["exit"],
                        },
                    ],
                }
                for variant_id in ("A", "D", "E")
            },
        })

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_dir = root / "input"
            input_dir.mkdir()
            (input_dir / "lua.png").write_bytes(b"png")
            (input_dir / "storyboard.png").write_bytes(b"png")
            spec = {
                "project_id": "single_shot_action_storyboard",
                "prompt_profile": h3_prompt_projects.ACTION_PROMPT_PROFILE,
                "prompt_generator": h3_prompt_projects.ACTION_PROMPT_GENERATOR,
                "asset_catalog": {
                    "lua": {
                        "copy_from": "lua.png",
                        "subject_id": 1,
                        "subject_name": "Lua",
                        "subject_description": "A spear fighter in blue armor",
                    },
                    "action-board": {
                        "copy_from": "storyboard.png",
                        "reference_kind": "storyboard",
                        "storyboard_mode": mode,
                        "storyboard_panel_count": 4,
                        "storyboard_reading_order": "top-left to bottom-right",
                        "storyboard_beats": ["b1", "b2", "b3", "b4"],
                        "standalone_picture_name": "the action checkpoint guide",
                        "standalone_picture_description": (
                            "This planning-only 2x2 sheet holds four ordered instantaneous action "
                            "key views for one full-screen action sequence and is never rendered."
                        ),
                        "retention_marker": "partially_preserved",
                        "retention_shots": [2],
                        "retention_description": (
                            "Use its four action states in order without reproducing the sheet"
                        ),
                    },
                },
                "clips": [{
                    "scene_id": "EP00-TEST",
                    "clip_id": "EP00-TEST-M01",
                    "sequence": 1,
                    "duration_seconds": 6,
                    "references": ["lua", "action-board"],
                    "prompt_base": {
                        "summary": "Lua completes one instant contact action.",
                        "style_opening": [
                            "Three separated full-screen Shots; never render a reference-sheet background."
                        ],
                        "overall_soundscape": "One fast impact and recoil.",
                        "non_diegetic_music": "One short percussion stop.",
                    },
                    "event_contract": contract,
                    "prompt_variants": [{
                        "variant_id": variant_id,
                        "rationale": f"distinct {variant_id} delegated camera behavior",
                        "prompt_spec": {},
                    } for variant_id in ("A", "D", "E")],
                    "scene_type": h3_prompt_projects.ACTION_SCENE_TYPE,
                    "prompt_profile": h3_prompt_projects.ACTION_PROMPT_PROFILE,
                    "prompt_generator": h3_prompt_projects.ACTION_PROMPT_GENERATOR,
                    "action_scene_contract": {
                        "version": h3_prompt_projects.ACTION_SCENE_CONTRACT_VERSION,
                        "storyboard_mode": mode,
                        "phase": "instant_contact_test",
                        "speed_profiles": ["s1", "s2", "s3", "s4"],
                        "motion_links": ["m1", "m2", "m3"],
                        "environmental_proof": "One visible impact mark remains.",
                    },
                }],
            }
            spec_path = input_dir / "project.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")

            h3_prompt_project_builder.build_project(root, spec_path)
            clip = h3_prompt_projects.load_clip(
                root, "single_shot_action_storyboard", "EP00-TEST-M01"
            )

            self.assertTrue(clip["ready"], clip["errors"])
            self.assertEqual(mode, clip["references"][1]["storyboard_mode"])
            for variant in clip["prompt_variants"]:
                detail = variant["detailed_description"]
                shots = list(h3_prompt_contract.SHOT_RE.finditer(detail))
                self.assertEqual(3, len(shots))
                self.assertIn(
                    "in this order: top-left, top-right, bottom-left, bottom-right",
                    detail,
                )
                self.assertNotIn("Lua reaches action checkpoint", detail)
                self.assertNotIn("Action timing:", shots[1].group(4))
                self.assertNotIn("Action timing:", detail)
                self.assertNotIn("<Picture 2>", shots[0].group(4))
                self.assertIn("<Picture 2>", shots[1].group(4))
                self.assertNotIn("<Picture 2>", shots[2].group(4))
                self.assertTrue(all(row.group(2) is None for row in shots))

    def test_four_panel_action_storyboard_becomes_four_concise_timed_shots(self):
        mode = h3_prompt_projects.FOUR_SHOT_ACTION_STORYBOARD_MODE
        contract = event_contract()
        contract.update({
            "incoming_bridge": "",
            "outgoing_bridge": "",
            "storyboard_required": True,
            "storyboard_picture_id": 2,
            "storyboard_panel_count": 4,
            "storyboard_reading_order": "top-left, top-right, bottom-left, bottom-right",
            "storyboard_mode": mode,
            "beats": [
                {"beat_id": f"b{number}", "description": f"private detail {number}"}
                for number in range(1, 5)
            ],
            "candidate_plans": {
                variant_id: {
                    "emphasis": f"{variant_id} timing",
                    "shots": [
                        {
                            "camera": f"Short action {number}.",
                            "panel_index": number,
                            "panel_position": position,
                            "beat_ids": [f"b{number}"],
                            **({} if number == 1 else {"start_seconds": number - 0.5}),
                        }
                        for number, position in enumerate(
                            ("top-left", "top-right", "bottom-left", "bottom-right"),
                            start=1,
                        )
                    ],
                }
                for variant_id in ("A", "D", "E")
            },
        })

        shots, _ = h3_prompt_project_builder._candidate_shots(
            "EP00-TEST-M02", 6, contract, "A"
        )

        self.assertEqual(4, len(shots))
        self.assertNotIn("private detail", " ".join(row["description"] for row in shots))
        self.assertEqual([1.5, 2.5, 3.5], [row["start_seconds"] for row in shots[1:]])
        for number, (shot, position) in enumerate(zip(
            shots,
            ("top-left", "top-right", "bottom-left", "bottom-right"),
            strict=True,
        ), start=1):
            expected = (
                "Use the top-left action image from <Picture 2> as the full-screen "
                "starting state for Shot 1."
                if number == 1
                else f"Use only the {position} action image from <Picture 2> as full-screen Shot {number}."
            )
            self.assertIn(expected, shot["description"])


if __name__ == "__main__":
    unittest.main()
