from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

import model_test_assets
import model_test_r2v
import model_test_registry
import workflow_adapter


class ModelTestR2VTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        self.workflow = self.workflows / model_test_r2v.R2V_WORKFLOW_FILENAME
        self.workflow.write_text(json.dumps({
            "92": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output"}},
            "119": {"class_type": "VAELoader", "inputs": {"vae_name": "video"}},
            "120": {"class_type": "VAELoader", "inputs": {"vae_name": "audio"}},
            "128": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen"}},
            "129": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}},
            "132": {"class_type": "PrimitiveFloat", "_meta": {"title": "Float (Duration)"}, "inputs": {"value": 5}},
            "136": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {
                "prompt": ["138", 0], "width": ["141", 0], "height": ["142", 0],
                "length": ["131", 1], "clip": ["128", 0], "vae": ["119", 0], "audio_vae": ["120", 0],
                "ref_images.ref_image_0": ["139", 0], "ref_images.ref_image_1": ["137", 0],
            }},
            "137": {"class_type": "LoadImage", "inputs": {"image": "picture2.png"}},
            "138": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": "prompt"}},
            "139": {"class_type": "LoadImage", "inputs": {"image": "picture1.png"}},
            "141": {"class_type": "PrimitiveInt", "_meta": {"title": "Width"}, "inputs": {"value": 832}},
            "142": {"class_type": "PrimitiveInt", "_meta": {"title": "Height"}, "inputs": {"value": 480}},
        }), encoding="utf-8")
        self.model_id = model_test_registry.register_model(self.root, {
            "provider": "MiniMax", "family": "H3", "display_name": "MiniMax H3", "version": "1"
        })["model_id"]
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        self.profile = next(row for row in dashboard["workflows"] if row["workflow_filename"] == self.workflow.name)
        self.adapter = next(row for row in dashboard["adapters"] if row["input_mode"] == "h3_r2v_multi_reference")
        self.image = self.root / "reference.png"
        self.image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"r2v-reference")

    def tearDown(self):
        self.temp.cleanup()

    def test_suites_are_separate_and_reference_order_is_explicit(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        action = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.ACTION_SUITE_ID)
        turns = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.TURN_SUITE_ID)
        self.assertEqual(action["input_mode"], "h3_r2v_multi_reference")
        self.assertEqual(len(action["cases"]), 24)
        self.assertEqual(len(turns["cases"]), 5)
        self.assertEqual(len(turns["cases"][-1]["asset_requirements"]), 8)
        self.assertEqual(
            [row["role"] for row in action["cases"][0]["contract"]["reference_slots"]],
            ["reference_image_1", "reference_image_2", "reference_image_3"],
        )
        self.assertEqual(sum(len(row["contract"]["reference_slots"]) for row in action["cases"]), 92)
        self.assertTrue(all(
            sum("스토리보드" in slot["label_ko"] for slot in row["contract"]["reference_slots"]) == 1
            for row in action["cases"]
        ))
        self.assertTrue(all(
            not row["contract"]["prompt_only_shot_guidance"]
            for row in action["cases"]
        ))
        first_prompt = action["cases"][0]["prompts"][0]["prompt_text"]
        self.assertIn(
            "<Picture 3> is the storyboard reference for [Shot 1], [Shot 2], and [Shot 3]",
            first_prompt,
        )
        self.assertIn("camera composition, sprint direction and dodge trajectory", first_prompt)
        self.assertIn("subject_definitions:", first_prompt)
        self.assertIn("retention_analysis:", first_prompt)
        self.assertIn("detailed_description:", first_prompt)
        detail = first_prompt.split("detailed_description:", 1)[1]
        self.assertIn("[Shot 1]", detail)
        self.assertIn("<Subject 1>", detail)
        self.assertIn("[Shot 2] At 00:02.000", detail)
        self.assertIn("[Shot 3] At 00:04.000", detail)
        self.assertIn("2nd storyboard frame in <Picture 3>", detail)
        self.assertIn("3rd storyboard frame in <Picture 3>", detail)
        self.assertIn("a short-dark-braided woman in a teal field jacket and ochre scarf", detail)
        self.assertEqual(detail.count("the same teal-jacketed woman with a short dark braid"), 2)
        self.assertNotIn("Storyboard panel", detail)

    def test_action_v2_is_a_separate_storyboard_free_suite(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        v1 = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.ACTION_SUITE_ID)
        v2 = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.ACTION_V2_SUITE_ID)
        self.assertEqual(v1["version"], 1)
        self.assertEqual(v2["version"], 2)
        self.assertEqual(v2["input_mode"], "h3_r2v_multi_reference")
        self.assertEqual(len(v1["cases"]), 24)
        self.assertEqual(len(v2["cases"]), 24)
        self.assertEqual(sum(len(row["contract"]["reference_slots"]) for row in v2["cases"]), 68)
        self.assertTrue(all(
            row["contract"]["shot_plan_source"] == "prompt_only_text"
            for row in v2["cases"]
        ))
        for case in v2["cases"]:
            contract = case["contract"]
            prompt = case["prompts"][0]["prompt_text"]
            self.assertTrue(contract["prompt_only_shot_guidance"], case["case_version_id"])
            self.assertTrue(all(
                slot["reference_kind"] == "visual_reference"
                for slot in contract["reference_slots"]
            ))
            self.assertNotIn("storyboard", prompt.lower(), case["case_version_id"])
            self.assertNotIn("storyboard", json.dumps(contract, ensure_ascii=False).lower(), case["case_version_id"])
            image_prompts = "\n".join(
                slot["image_generation_prompt"] for slot in contract["reference_slots"]
            )
            self.assertNotIn("storyboard", image_prompts.lower(), case["case_version_id"])
            detail = prompt.split("detailed_description:", 1)[1].split("overall_soundscape:", 1)[0]
            self.assertEqual(
                detail.count("[Shot "), len(contract["prompt_only_shot_guidance"]),
                case["case_version_id"],
            )

        first = v2["cases"][0]
        self.assertEqual(first["case_version_id"], model_test_r2v.action_v2_case_version_id("rs01"))
        self.assertEqual(
            [slot["role"] for slot in first["contract"]["reference_slots"]],
            ["reference_image_1", "reference_image_2"],
        )
        self.assertNotIn("<Picture 3>", first["prompts"][0]["prompt_text"])
        self.assertIn("[Shot 2] At 00:02.000", first["prompts"][0]["prompt_text"])
        self.assertIn("A direct cut changes to the specified composition", first["prompts"][0]["prompt_text"])
        self.assertNotIn("장면 컷 전환", first["contract"]["forbidden_failures"])

    def test_action_v1_contract_and_prompts_remain_immutable(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        v1 = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.ACTION_SUITE_ID)
        snapshot = [{
            "case_version_id": case["case_version_id"],
            "contract": case["contract"],
            "prompt": case["prompts"][0]["prompt_text"],
        } for case in v1["cases"]]
        encoded = json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(encoded).hexdigest(),
            "2998a8fc4433572c8b2138d798f96dd76a4577fb069840e4c02e55b4ae03034e",
        )

    def test_registered_range_stays_3d_and_unregistered_range_is_split_by_genre(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        action = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.ACTION_SUITE_ID)
        self.assertTrue(all(row["contract"]["visual_style"] == "stylized_3d" for row in action["cases"][:14]))
        styles = {row["case_version_id"]: row["contract"]["visual_style"] for row in action["cases"]}
        self.assertEqual(styles[model_test_r2v.case_version_id("rd03")], "live_action")
        self.assertEqual(styles[model_test_r2v.case_version_id("rd04")], "live_action")
        self.assertEqual(styles[model_test_r2v.case_version_id("rd05")], "hand_drawn_2d")
        self.assertEqual(styles[model_test_r2v.case_version_id("rd06")], "hand_drawn_2d")
        self.assertEqual([row["contract"]["visual_style"] for row in action["cases"][14:19]], ["live_action"] * 5)
        self.assertEqual([row["contract"]["visual_style"] for row in action["cases"][19:24]], ["hand_drawn_2d"] * 5)
        live_case = next(row for row in action["cases"] if row["case_version_id"] == model_test_r2v.case_version_id("rl01"))
        animation_case = next(row for row in action["cases"] if row["case_version_id"] == model_test_r2v.case_version_id("ra03"))
        self.assertIn("photorealistic live-action", live_case["prompts"][0]["prompt_text"])
        self.assertIn("authentic hand-drawn 2D", animation_case["prompts"][0]["prompt_text"])

    def test_every_reference_slot_has_grouped_image_generation_prompt(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        suites = [
            row for row in dashboard["suites"]
            if row["suite_id"] in {model_test_r2v.ACTION_SUITE_ID, model_test_r2v.TURN_SUITE_ID}
        ]
        for suite in suites:
            for case in suite["cases"]:
                slots = case["contract"]["reference_slots"]
                self.assertTrue(slots, msg=case["case_version_id"])
                for index, slot in enumerate(slots, start=1):
                    prompt = slot["image_generation_prompt"]
                    self.assertTrue(prompt, msg=f"{case['case_version_id']} Picture {index}")
                    self.assertIn(f"<Picture {index}>", prompt)
        first = suites[0]["cases"][0]["contract"]["reference_slots"]
        self.assertIn("full-body front view", first[0]["image_generation_prompt"])
        self.assertIn("environment reference plate", first[1]["image_generation_prompt"])
        self.assertIn("multi-panel cinematic storyboard sheet", first[2]["image_generation_prompt"])
        self.assertIn("exactly 3 sequential panels", first[2]["image_generation_prompt"])
        self.assertEqual(first[2]["reference_kind"], "storyboard")
        self.assertEqual(first[2]["storyboard_panel_count"], 3)
        self.assertEqual(first[2]["storyboard_reading_order"], "left_to_right_then_top_to_bottom")
        self.assertEqual([item["panel_index"] for item in first[2]["storyboard_beats"]], [1, 2, 3])
        self.assertEqual(first[2]["storyboard_beats"][1]["beat_kind"], "key_interaction")

    def test_character_sheets_are_appealing_and_genre_calibrated(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        cases = {
            row["case_version_id"]: row
            for suite in dashboard["suites"]
            if suite["input_mode"] == "h3_r2v_multi_reference"
            for row in suite["cases"]
        }
        stylized = cases[model_test_r2v.case_version_id("rs01")]
        live = cases[model_test_r2v.case_version_id("rl01")]
        drawn = cases[model_test_r2v.case_version_id("ra01")]
        stylized_prompt = stylized["contract"]["reference_slots"][0]["image_generation_prompt"]
        live_prompt = live["contract"]["reference_slots"][0]["image_generation_prompt"]
        drawn_prompt = drawn["contract"]["reference_slots"][0]["image_generation_prompt"]
        self.assertIn("visually appealing, charismatic and heroically stylish", stylized_prompt)
        self.assertIn("naturally attractive, charismatic and cinematic-looking", live_prompt)
        self.assertIn("no beauty-filter skin", live_prompt)
        self.assertIn("visually appealing, elegant and charismatic", drawn_prompt)
        self.assertIn("pleasant natural expression", stylized_prompt)

    def test_turn_prompts_use_official_speaker_and_dialogue_markup(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        suite = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.TURN_SUITE_ID)
        for case in suite["cases"]:
            prompt = case["prompts"][0]["prompt_text"]
            detail = prompt.split("detailed_description:", 1)[1].split("overall_soundscape:", 1)[0]
            dialogue = case["contract"]["dialogue"]
            for index, item in enumerate(dialogue, start=1):
                line = item["line_ko"]
                self.assertIn(f"<Subject {index}> (S{index})", detail)
                self.assertIn(f"<d>[Korean] {line}</d>", detail)
            storyboard = next(slot for slot in case["contract"]["reference_slots"] if slot["reference_kind"] == "storyboard")
            self.assertIn(f"<Picture {storyboard['picture_index']}>", detail)
            self.assertEqual(detail.count("[Shot "), storyboard["storyboard_panel_count"])
            self.assertNotIn("Storyboard panel", detail)

    def test_all_r2v_prompts_apply_subjects_and_storyboard_inside_shot_body(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        suites = [
            row for row in dashboard["suites"]
            if row["suite_id"] in {model_test_r2v.ACTION_SUITE_ID, model_test_r2v.TURN_SUITE_ID}
        ]
        for suite in suites:
            for case in suite["cases"]:
                prompt = case["prompts"][0]["prompt_text"]
                detail = prompt.split("detailed_description:", 1)[1].split("overall_soundscape:", 1)[0]
                subjects = [slot for slot in case["contract"]["reference_slots"] if slot["reference_kind"] != "storyboard"]
                storyboard = next(slot for slot in case["contract"]["reference_slots"] if slot["reference_kind"] == "storyboard")
                shot_bodies = [
                    match.group(0)
                    for match in re.finditer(r"\[Shot \d+\].*?(?=\n\[Shot \d+\]|\Z)", detail, re.DOTALL)
                ]
                self.assertEqual(
                    len(shot_bodies), storyboard["storyboard_panel_count"], msg=case["case_version_id"]
                )
                for subject_index in range(1, len(subjects) + 1):
                    self.assertIn(
                        f"<Subject {subject_index}>", shot_bodies[0],
                        msg=f"{case['case_version_id']} Shot 1 Subject {subject_index}",
                    )
                for shot_index, shot_body in enumerate(shot_bodies, start=1):
                    self.assertRegex(shot_body, r"<Subject \d+>")
                    self.assertIsNone(
                        re.search(r"<Subject \d+> \((?!S\d+\))", shot_body),
                        msg=f"non-official Subject parentheses: {case['case_version_id']} Shot {shot_index}",
                    )
                    self.assertNotIn("In this shot", shot_body)
                    self.assertNotIn("Current sound:", shot_body)
                    if shot_index > 1:
                        self.assertRegex(shot_body, rf"^\[Shot {shot_index}\] At \d{{2}}:\d{{2}}\.\d{{3}},")
                self.assertIn(f"<Picture {storyboard['picture_index']}>", detail)
                self.assertNotIn("Translate <Picture", detail)
                self.assertNotIn("Storyboard panel", detail)

    def test_execution_prompt_uses_natural_official_reference_language(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        action = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.ACTION_SUITE_ID)
        prompt = action["cases"][0]["prompts"][0]["prompt_text"]
        self.assertIn("is the protagonist, a young woman", prompt)
        self.assertIn("is the visible environment shown in <Picture 2>", prompt)
        self.assertNotIn("uses <Picture", prompt)
        self.assertNotIn("Generate one coherent target video", prompt)

    def test_generation_prompts_do_not_expose_benchmark_metadata(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        suites = [row for row in dashboard["suites"] if row["input_mode"] == "h3_r2v_multi_reference"]
        for suite in suites:
            for case in suite["cases"]:
                execution_prompt = case["prompts"][0]["prompt_text"]
                self.assertNotIn("benchmark", execution_prompt.lower(), msg=case["case_version_id"])
                for slot in case["contract"]["reference_slots"]:
                    self.assertNotIn(
                        "benchmark",
                        slot["image_generation_prompt"].lower(),
                        msg=f"{case['case_version_id']} Picture {slot['picture_index']}",
                    )

    def test_global_shared_asset_is_linked_once_and_styles_stay_separate(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        groups = {
            row["shared_asset_key"]: row
            for row in dashboard["r2v_shared_asset_groups"]
        }
        self.assertIn("stylized_3d_protagonist", groups)
        self.assertIn("live_action_character_a", groups)
        self.assertIn("hand_drawn_2d_character_a", groups)
        protagonist = groups["stylized_3d_protagonist"]
        self.assertEqual(protagonist["target_count"], 24)
        self.assertEqual(protagonist["linked_count"], 0)
        with model_test_registry.open_registry(self.root) as connection:
            saved = model_test_assets.save_and_link_r2v_shared(self.root, connection, {
                "shared_asset_key": "stylized_3d_protagonist",
                "upload_path": str(self.image),
                "original_name": "global-protagonist.png",
            })
            self.assertEqual(saved["linked_count"], 24)
            asset_ids = {
                row["asset_id"]
                for row in connection.execute(
                    """SELECT a.asset_id FROM benchmark_case_assets a
                       JOIN benchmark_case_versions v ON v.case_version_id=a.case_version_id
                       JOIN json_each(v.contract_json,'$.reference_slots') slot
                         ON json_extract(slot.value,'$.role')=a.role
                       WHERE json_extract(slot.value,'$.shared_asset_key')=?""",
                    ("stylized_3d_protagonist",),
                )
            }
            self.assertEqual(asset_ids, {saved["asset_id"]})
            removed = model_test_assets.unlink_r2v_shared(connection, {
                "shared_asset_key": "stylized_3d_protagonist",
            })
            self.assertEqual(removed["unlinked_count"], 24)

    def test_storyboard_free_v2_compiles_with_only_visual_references(self):
        case_version_id = model_test_r2v.action_v2_case_version_id("rs01")
        with model_test_registry.open_registry(self.root) as connection:
            for index in range(1, 3):
                model_test_assets.save_and_link(self.root, connection, {
                    "case_version_id": case_version_id,
                    "role": f"reference_image_{index}",
                    "upload_path": str(self.image),
                    "original_name": f"v2-picture-{index}.png",
                })
        session_id = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile["workflow_profile_id"],
            "adapter_id": self.adapter["adapter_id"],
            "suite_id": model_test_r2v.ACTION_V2_SUITE_ID,
            "resolution": {"width": 832, "height": 480},
        })["session_id"]
        with model_test_registry.open_registry(self.root) as connection:
            session = connection.execute(
                "SELECT * FROM test_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
            result = workflow_adapter.compile_case(connection, session, case_version_id)
        self.assertEqual(result["status"], "ready")
        self.assertEqual([row["picture_index"] for row in result["assets"]], [1, 2])
        self.assertNotIn("storyboard", result["prompt_text"].lower())
        self.assertIn("[Shot 3] At 00:04.000", result["prompt_text"])
        inputs = result["compiled_workflow"]["136"]["inputs"]
        self.assertIn("ref_images.ref_image_0", inputs)
        self.assertIn("ref_images.ref_image_1", inputs)
        self.assertNotIn("ref_images.ref_image_2", inputs)

    def test_three_references_and_case_setting_compile_to_h3_graph(self):
        case_version_id = model_test_r2v.case_version_id("rs05")
        with model_test_registry.open_registry(self.root) as connection:
            for index in range(1, 5):
                model_test_assets.save_and_link(self.root, connection, {
                    "case_version_id": case_version_id,
                    "role": f"reference_image_{index}",
                    "upload_path": str(self.image),
                    "original_name": f"picture-{index}.png",
                })
        session_id = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile["workflow_profile_id"],
            "adapter_id": self.adapter["adapter_id"],
            "suite_id": model_test_r2v.ACTION_SUITE_ID,
            "resolution": {"width": 832, "height": 480},
            "case_settings": {case_version_id: {"enemy_count": 7}},
        })["session_id"]
        with model_test_registry.open_registry(self.root) as connection:
            session = connection.execute("SELECT * FROM test_sessions WHERE session_id=?", (session_id,)).fetchone()
            result = workflow_adapter.compile_case(connection, session, case_version_id)
        self.assertEqual(result["status"], "ready")
        self.assertIn("exactly 7 distinct enemies", result["prompt_text"])
        self.assertIn("follow <Picture 4>", result["prompt_text"])
        self.assertNotIn("Translate <Picture", result["prompt_text"])
        self.assertEqual(result["compiled_workflow"]["138"]["inputs"]["value"], result["prompt_text"])
        self.assertEqual(result["case_settings"], {"enemy_count": 7})
        self.assertEqual(result["settings"]["frame_count"], 158)
        self.assertEqual(result["compiled_workflow"]["141"]["inputs"]["value"], 832)
        self.assertEqual(result["compiled_workflow"]["142"]["inputs"]["value"], 480)
        inputs = result["compiled_workflow"]["136"]["inputs"]
        self.assertEqual(inputs["ref_images.ref_image_0"], ["139", 0])
        self.assertEqual(inputs["ref_images.ref_image_1"], ["137", 0])
        self.assertEqual(inputs["ref_images.ref_image_2"], ["benchmark_ref_3", 0])
        self.assertEqual(inputs["ref_images.ref_image_3"], ["benchmark_ref_4", 0])
        self.assertNotIn("ref_images.ref_image_4", inputs)
        self.assertEqual([row["picture_index"] for row in result["assets"]], [1, 2, 3, 4])

    def test_storyboard_plan_is_compiled_as_official_picture_reference(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        action = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.ACTION_SUITE_ID)
        case = next(
            row for row in action["cases"]
            if row["case_version_id"] == model_test_r2v.case_version_id("rd03")
        )
        prompt = case["prompts"][0]["prompt_text"]
        self.assertIn(
            "positions, trajectories, contact timing and camera composition",
            prompt,
        )
        self.assertIn("<Picture 4> is the storyboard reference for [Shot 1]", prompt)
        self.assertIn("[Shot 4] At 00:05.250", prompt)
        self.assertIn("4th storyboard frame in <Picture 4>", prompt)
        self.assertNotIn("Storyboard panel", prompt)

    def test_dialogue_action_uses_official_markup_and_action_ending(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        action = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.ACTION_SUITE_ID)
        case = next(row for row in action["cases"] if row["case_version_id"] == model_test_r2v.case_version_id("rd06"))
        detail = case["prompts"][0]["prompt_text"].split("detailed_description:", 1)[1].split("overall_soundscape:", 1)[0]
        self.assertIn("<Subject 1> (S1)", detail)
        self.assertIn("<d>[Korean] 뒤로 물러서!</d>", detail)
        self.assertIn("With both mouths closed", detail)
        self.assertIn("<Subject 2> moves laterally", detail)
        self.assertIn("performs one readable counterattack", detail)
        self.assertNotIn("<Subject 1> completes one readable nod", detail)

    def test_storyboard_asset_is_preserved_with_later_prop_role(self):
        case_version_id = model_test_r2v.case_version_id("rd03")
        old_labels = [
            "캐릭터 A 시트", "캐릭터 B 시트", "행동 공간 배경",
            "2인 액션 스토리보드", "무기·소품 디자인",
        ]
        with model_test_registry.open_registry(self.root) as connection:
            connection.execute("DELETE FROM benchmark_case_asset_requirements WHERE case_version_id=?", (case_version_id,))
            connection.execute("DELETE FROM benchmark_case_assets WHERE case_version_id=?", (case_version_id,))
            for index, label in enumerate(old_labels, start=1):
                asset_id = f"asset_legacy_{index}"
                connection.execute(
                    "INSERT INTO assets(asset_id,kind,path,sha256) VALUES (?,'image',?,?)",
                    (asset_id, f"legacy-{index}.png", f"sha-{index}"),
                )
                connection.execute(
                    """INSERT INTO benchmark_case_asset_requirements
                       (case_version_id,role,kind,minimum_count,description)
                       VALUES (?,?,'image',1,?)""",
                    (case_version_id, f"reference_image_{index}", f"<Picture {index}> · {label}"),
                )
                connection.execute(
                    """INSERT INTO benchmark_case_assets(case_version_id,asset_id,role,ordering)
                       VALUES (?,?,?,1)""",
                    (case_version_id, asset_id, f"reference_image_{index}"),
                )
            model_test_r2v.ensure_suites(connection)
            model_test_r2v.ensure_suites(connection)
            links = connection.execute(
                "SELECT asset_id,role FROM benchmark_case_assets WHERE case_version_id=? ORDER BY role",
                (case_version_id,),
            ).fetchall()
            requirements = connection.execute(
                "SELECT role,description FROM benchmark_case_asset_requirements WHERE case_version_id=? ORDER BY role",
                (case_version_id,),
            ).fetchall()
        self.assertEqual([row["role"] for row in links], [
            "reference_image_1", "reference_image_2", "reference_image_3",
            "reference_image_4", "reference_image_5",
        ])
        self.assertIn("asset_legacy_4", [row["asset_id"] for row in links])
        self.assertEqual(next(row["role"] for row in links if row["asset_id"] == "asset_legacy_5"), "reference_image_5")
        self.assertTrue(any("스토리보드" in row["description"] for row in requirements))

    def test_r2v_rejects_wrong_resolution_and_out_of_range_setting(self):
        base = {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile["workflow_profile_id"],
            "adapter_id": self.adapter["adapter_id"],
            "suite_id": model_test_r2v.ACTION_SUITE_ID,
        }
        for suite_id in (model_test_r2v.ACTION_SUITE_ID, model_test_r2v.ACTION_V2_SUITE_ID):
            with self.subTest(suite_id=suite_id), self.assertRaisesRegex(ValueError, "고정 해상도"):
                model_test_registry.create_session(self.root, {
                    **base, "suite_id": suite_id,
                    "resolution": {"width": 768, "height": 480},
                })
        with self.assertRaisesRegex(ValueError, "3~10"):
            model_test_registry.create_session(self.root, {
                **base, "resolution": {"width": 832, "height": 480},
                "case_settings": {model_test_r2v.case_version_id("rs05"): {"enemy_count": 11}},
            })


if __name__ == "__main__":
    unittest.main()
