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
import benchmark_jobs
import h3_queue
import model_test_review_queue
import workflow_adapter
from job_queue import atomic_write_json, read_json


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

    def test_active_review_cancel_stays_pending_until_worker_confirms_stop(self):
        session = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile["workflow_profile_id"],
            "adapter_id": self.adapter["adapter_id"],
            "suite_id": model_test_r2v.ACTION_SUITE_ID,
            "repetitions": 1,
            "resolution": {"width": 832, "height": 480},
        })
        queue_dir = (
            self.root / "runtime/model_test_review_queue/review_active_cancel"
        )
        atomic_write_json(queue_dir / "request.json", {
            "session_id": session["session_id"],
            "generation_job_ids": ["generation_job"],
        })
        atomic_write_json(queue_dir / "status.json", {
            "status": "reviewing",
        })

        result = model_test_review_queue.cancel(self.root, session["session_id"])

        self.assertTrue(result["cancel_requested"])
        self.assertEqual(
            "cancel_requested",
            read_json(queue_dir / "status.json", {})["status"],
        )
        with model_test_registry.open_registry(self.root) as connection:
            status = connection.execute(
                "SELECT status FROM test_sessions WHERE session_id=?",
                (session["session_id"],),
            ).fetchone()["status"]
        self.assertEqual("review_cancel_requested", status)
        with self.assertRaisesRegex(RuntimeError, "실행 중이거나 큐 대기 중"):
            model_test_registry.delete_session(self.root, session["session_id"])

        atomic_write_json(queue_dir / "status.json", {"status": "cancelled"})
        benchmark_jobs.set_session_review_status(
            self.root, [session["session_id"]], "review_cancelled"
        )
        deleted = model_test_registry.delete_session(self.root, session["session_id"])
        self.assertEqual(1, deleted["deleted_review_queue_count"])

    def _write_project(
        self,
        project_id: str,
        title: str,
        clips: list[tuple[str, str, int]],
    ) -> dict[str, str]:
        project = self.root / "prompt_projects" / project_id
        (project / "assets").mkdir(parents=True, exist_ok=True)
        (project / "assets" / "hero.png").write_bytes(self.image.read_bytes())
        (project / "manifest.json").write_text(json.dumps({
            "project_kind": "h3_r2v_production",
            "title": title,
        }), encoding="utf-8")
        prompts = {}
        for scene_id, clip_id, sequence in clips:
            (project / scene_id).mkdir(exist_ok=True)
            prompt = (
                "subject_definitions:\n<Subject 1> is from <Picture 1>.\n\n"
                f"detailed_description:\n[Shot 1] Scene action {sequence}."
            )
            prompts[clip_id] = prompt
            payload = {
                "schema_version": 1,
                "workflow": "h3_r2v_production",
                "project_id": project_id,
                "scene_id": scene_id,
                "clip_id": clip_id,
                "sequence": sequence,
                "duration_seconds": 5,
                "video_prompt": prompt,
                "review_intent_ko": f"{scene_id} 동작을 검수한다.",
                "references": [{
                    "picture_index": 1,
                    "role": "hero",
                    "label": "주인공",
                    "description": "same hero",
                    "required": True,
                    "source_path": "assets/hero.png",
                }],
            }
            (project / scene_id / f"{clip_id}.md").write_text(
                "## Machine Payload\n\n```json\n"
                + json.dumps(payload) + "\n```\n",
                encoding="utf-8",
            )
        return prompts

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

    def test_pint8_sol_attn_workflow_is_registered_and_compiles_for_h3_r2v(self):
        payload = json.loads(self.workflow.read_text(encoding="utf-8"))
        payload["127"] = {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
                "weight_dtype": "default",
            },
        }
        payload["136"]["inputs"]["ref_images.ref_image_2"] = ["143", 0]
        payload["143"] = {
            "class_type": "LoadImage",
            "inputs": {"image": "picture3.png"},
        }
        payload["154"] = {
            "class_type": "SolAttnPatch",
            "inputs": {
                "model": ["127", 0],
                "tau": 1.3,
                "int8_qk": True,
                "int8_pv": True,
            },
        }
        pint8_path = (
            self.workflows / model_test_r2v.R2V_PINT8_WORKFLOW_FILENAME
        )
        pint8_path.write_text(json.dumps(payload), encoding="utf-8")

        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        profile = next(
            row
            for row in dashboard["workflows"]
            if row["workflow_filename"] == pint8_path.name
        )
        self.assertEqual("optimized_variant", profile["profile_kind"])
        self.assertTrue(profile["sol_attn_configurable"])
        self.assertEqual(1.3, profile["sol_attn_defaults"]["tau"])
        self.assertEqual(0.2, profile["sol_attn_defaults"]["start_percent"])
        self.assertEqual(0.9, profile["sol_attn_defaults"]["end_percent"])
        adapter = next(
            row
            for row in dashboard["adapters"]
            if row["workflow_profile_id"] == profile["workflow_profile_id"]
        )
        self.assertEqual("h3_r2v_multi_reference", adapter["input_mode"])
        self.assertEqual(
            ["139", "137", "143"],
            adapter["config"]["multi_reference"]["loader_node_ids"],
        )
        self.assertEqual(
            "137",
            adapter["config"]["multi_reference"]["loader_template_node_id"],
        )
        available = h3_queue.available_adapters(self.root)["adapters"]
        self.assertTrue(any(
            row["adapter_id"] == adapter["adapter_id"]
            and row["workflow_filename"] == pint8_path.name
            and row["sol_attn_configurable"] is True
            and row["sol_attn_defaults"]["int8_qk"] is False
            and row["sol_attn_defaults"]["int8_pv"] is False
            and row["sol_attn_defaults"]["morton"] is False
            for row in available
        ))

        compiled, patches, metadata = h3_queue._compile_workflow(
            self.root,
            adapter["adapter_id"],
            {
                "prompt": "[Shot 1] The hero moves.",
                "seed": 7,
                "width": 832,
                "height": 480,
                "duration_seconds": 5,
                "filename_prefix": "video/pint8-test",
            },
            3,
        )
        self.assertEqual(pint8_path.name, metadata["workflow_filename"])
        self.assertIn("154", compiled)
        self.assertEqual(["127", 0], compiled["154"]["inputs"]["model"])
        self.assertFalse(compiled["154"]["inputs"]["int8_qk"])
        self.assertFalse(compiled["154"]["inputs"]["int8_pv"])
        self.assertFalse(compiled["154"]["inputs"]["morton"])
        self.assertEqual(
            metadata["workflow_settings"]["sol_attn"],
            {
                key: compiled["154"]["inputs"][key]
                for key in workflow_adapter.SOL_ATTN_SETTING_RULES
            },
        )
        self.assertEqual(
            [["139", 0], ["137", 0], ["143", 0]],
            [
                compiled["136"]["inputs"][f"ref_images.ref_image_{index}"]
                for index in range(3)
            ],
        )
        self.assertEqual(
            ["139", "137", "143"],
            [row["node_id"] for row in patches],
        )

        enabled, _, enabled_metadata = h3_queue._compile_workflow(
            self.root,
            adapter["adapter_id"],
            {
                "prompt": "[Shot 1] The hero moves.",
                "seed": 8,
                "width": 832,
                "height": 480,
                "duration_seconds": 5,
                "filename_prefix": "video/pint8-enabled-test",
            },
            3,
            "r2v",
            {"sol_attn": {"int8_qk": True, "int8_pv": True, "morton": True}},
        )
        self.assertTrue(enabled["154"]["inputs"]["int8_qk"])
        self.assertTrue(enabled["154"]["inputs"]["int8_pv"])
        self.assertTrue(enabled["154"]["inputs"]["morton"])
        self.assertTrue(enabled_metadata["workflow_settings"]["sol_attn"]["int8_qk"])

        sol_attn_settings = {
            "tau": 1.75,
            "start_percent": 0.1,
            "end_percent": 0.8,
            "min_tokens": 8192,
            "int8_qk": True,
            "sink_conditioning": "exact_kv",
            "morton": True,
            "morton_curve": "3d",
            "int8_pv": False,
            "verbose": False,
            "use_tma": True,
            "dense_blocks": "0-1, -1",
        }
        session = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": profile["workflow_profile_id"],
            "adapter_id": adapter["adapter_id"],
            "suite_id": model_test_r2v.ACTION_V2_SUITE_ID,
            "repetitions": 1,
            "resolution": {"width": 832, "height": 480},
            "workflow_settings": {"sol_attn": sol_attn_settings},
        })
        self.assertEqual(24, session["case_count"])
        self.assertEqual("0-1,-1", session["workflow_settings"]["sol_attn"]["dense_blocks"])

        case_version_id = model_test_r2v.action_v2_case_version_id("rs01")
        with model_test_registry.open_registry(self.root) as connection:
            for index in range(1, 3):
                model_test_assets.save_and_link(self.root, connection, {
                    "case_version_id": case_version_id,
                    "role": f"reference_image_{index}",
                    "upload_path": str(self.image),
                    "original_name": f"sol-attn-picture-{index}.png",
                })
            session_row = connection.execute(
                "SELECT * FROM test_sessions WHERE session_id=?",
                (session["session_id"],),
            ).fetchone()
            compiled_case = workflow_adapter.compile_case(
                connection, session_row, case_version_id
            )
        sol_node = next(
            node for node in compiled_case["compiled_workflow"].values()
            if node["class_type"] == "SolAttnPatch"
        )
        self.assertEqual(1.75, sol_node["inputs"]["tau"])
        self.assertEqual(0.1, sol_node["inputs"]["start_percent"])
        self.assertEqual(0.8, sol_node["inputs"]["end_percent"])
        self.assertEqual(8192, sol_node["inputs"]["min_tokens"])
        self.assertEqual("exact_kv", sol_node["inputs"]["sink_conditioning"])
        self.assertTrue(sol_node["inputs"]["morton"])
        self.assertFalse(sol_node["inputs"]["int8_pv"])
        self.assertEqual(
            session["workflow_settings"],
            compiled_case["settings"]["workflow_settings"],
        )
        self.assertEqual(
            1.3,
            json.loads(pint8_path.read_text(encoding="utf-8"))["154"]["inputs"]["tau"],
        )

        followup = model_test_registry.create_followup_session(self.root, {
            "source_session_id": session["session_id"],
            "case_version_ids": [case_version_id],
            "repetitions": 1,
            "reason": "sol_attn_reproducibility",
        })
        queued = benchmark_jobs.queue_session(self.root, followup["session_id"])
        job_dir = self.root / "runtime/h3/jobs" / queued["job_ids"][0]
        queued_workflow = read_json(job_dir / "workflow_api.json", {})
        queued_sol_node = next(
            node for node in queued_workflow.values()
            if node["class_type"] == "SolAttnPatch"
        )
        request = read_json(job_dir / "request.json", {})
        manifest = read_json(job_dir / "manifest.json", {})
        self.assertEqual(1.75, queued_sol_node["inputs"]["tau"])
        self.assertEqual(
            session["workflow_settings"], request["settings"]["workflow_settings"]
        )
        self.assertEqual(session["workflow_settings"], manifest["workflow_settings"])
        with model_test_registry.open_registry(self.root) as connection:
            run = connection.execute(
                "SELECT settings_json,runtime_id FROM generation_runs WHERE job_id=?",
                (queued["job_ids"][0],),
            ).fetchone()
            runtime = connection.execute(
                "SELECT runtime_config_json FROM model_runtimes WHERE runtime_id=?",
                (run["runtime_id"],),
            ).fetchone()
            followup_row = connection.execute(
                "SELECT workflow_settings_json FROM test_sessions WHERE session_id=?",
                (followup["session_id"],),
            ).fetchone()
        self.assertEqual(
            session["workflow_settings"],
            json.loads(run["settings_json"])["workflow_settings"],
        )
        self.assertEqual(
            session["workflow_settings"],
            json.loads(runtime["runtime_config_json"])["workflow_settings"],
        )
        self.assertEqual(
            session["workflow_settings"],
            json.loads(followup_row["workflow_settings_json"]),
        )
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        saved_session = next(
            row for row in dashboard["sessions"]
            if row["session_id"] == session["session_id"]
        )
        self.assertEqual(session["workflow_settings"], saved_session["workflow_settings"])

        legacy = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": profile["workflow_profile_id"],
            "adapter_id": adapter["adapter_id"],
            "suite_id": model_test_r2v.ACTION_V2_SUITE_ID,
            "repetitions": 1,
            "resolution": {"width": 832, "height": 480},
        })
        with model_test_registry.open_registry(self.root) as connection:
            connection.execute(
                "UPDATE test_sessions SET workflow_settings_json='{}' WHERE session_id=?",
                (legacy["session_id"],),
            )
            legacy_row = connection.execute(
                "SELECT * FROM test_sessions WHERE session_id=?",
                (legacy["session_id"],),
            ).fetchone()
            legacy_compiled = workflow_adapter.compile_case(
                connection, legacy_row, case_version_id
            )
        self.assertEqual(
            1.3,
            legacy_compiled["settings"]["workflow_settings"]["sol_attn"]["tau"],
        )
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        legacy_dashboard = next(
            row for row in dashboard["sessions"]
            if row["session_id"] == legacy["session_id"]
        )
        self.assertTrue(legacy_dashboard["workflow_settings_inherited"])
        self.assertEqual(
            legacy_compiled["settings"]["workflow_settings"],
            legacy_dashboard["workflow_settings"],
        )

        with self.assertRaisesRegex(ValueError, r"PINT8 \+ Sol-Attn"):
            model_test_registry.create_session(self.root, {
                "model_id": self.model_id,
                "workflow_profile_id": self.profile["workflow_profile_id"],
                "adapter_id": self.adapter["adapter_id"],
                "suite_id": model_test_r2v.ACTION_V2_SUITE_ID,
                "resolution": {"width": 832, "height": 480},
                "workflow_settings": {"sol_attn": sol_attn_settings},
            })

    def test_update_attention_workflow_is_registered_as_default_r2v_adapter(self):
        payload = json.loads(self.workflow.read_text(encoding="utf-8"))
        payload["127"] = {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
                "weight_dtype": "default",
            },
        }
        payload["153"] = {
            "class_type": "ModelAttentionBackend",
            "inputs": {
                "model": ["127", 0],
                "attention": "comfy kitchen attention",
            },
        }
        loaders = ["137", "139", "145", "149", "147"]
        for index, loader_id in enumerate(loaders, start=1):
            payload[loader_id] = {
                "class_type": "LoadImage",
                "inputs": {"image": f"picture{index}.png"},
            }
            payload["136"]["inputs"][f"ref_images.ref_image_{index - 1}"] = [
                loader_id,
                0,
            ]
        update_path = (
            self.workflows / model_test_r2v.R2V_UPDATE_ATTN_WORKFLOW_FILENAME
        )
        update_path.write_text(json.dumps(payload), encoding="utf-8")

        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        profile = next(
            row
            for row in dashboard["workflows"]
            if row["workflow_filename"] == update_path.name
        )
        adapter = next(
            row
            for row in dashboard["adapters"]
            if row["workflow_profile_id"] == profile["workflow_profile_id"]
        )
        multi = adapter["config"]["multi_reference"]
        self.assertEqual(loaders, multi["loader_node_ids"])
        self.assertEqual([], multi["conditioning_source_node_ids"])
        self.assertEqual("", multi["conditioning_source_template_node_id"])
        self.assertEqual(9, multi["max_slots"])

        available = h3_queue.available_adapters(self.root)["adapters"]
        production = next(
            row for row in available if row["adapter_id"] == adapter["adapter_id"]
        )
        self.assertTrue(production["default_for_generation"])
        compiled, patches, metadata = h3_queue._compile_workflow(
            self.root,
            adapter["adapter_id"],
            {
                "prompt": "The hero runs.",
                "seed": 7,
                "width": 832,
                "height": 480,
                "duration_seconds": 5,
                "filename_prefix": "video/update-attn",
            },
            9,
            "r2v",
        )
        self.assertEqual(update_path.name, metadata["workflow_filename"])
        self.assertEqual(
            [
                {"node_id": node_id, "input": "image"}
                for node_id in loaders
            ]
            + [
                {"node_id": f"h3_ref_{slot}", "input": "image"}
                for slot in range(6, 10)
            ],
            patches,
        )
        self.assertEqual(
            "comfy kitchen attention", compiled["153"]["inputs"]["attention"]
        )
        for index, loader_id in enumerate(loaders):
            self.assertEqual(
                [loader_id, 0],
                compiled["136"]["inputs"][f"ref_images.ref_image_{index}"],
            )
        for slot in range(6, 10):
            self.assertEqual(
                [f"h3_ref_{slot}", 0],
                compiled["136"]["inputs"][f"ref_images.ref_image_{slot - 1}"],
            )
        with self.assertRaisesRegex(ValueError, "1~9장"):
            h3_queue._compile_workflow(
                self.root,
                adapter["adapter_id"],
                {
                    "prompt": "The hero runs.",
                    "seed": 7,
                    "width": 832,
                    "height": 480,
                    "duration_seconds": 5,
                    "filename_prefix": "video/update-attn-invalid",
                },
                10,
                "r2v",
            )

    def test_sol_attn_settings_reject_invalid_or_unsafe_values(self):
        workflow = {
            "154": {
                "class_type": "SolAttnPatch",
                "inputs": {
                    "model": ["127", 0], "tau": 1.3,
                    "start_percent": 0.2, "end_percent": 0.9,
                    "min_tokens": 4096, "int8_qk": True,
                    "sink_conditioning": "exact_kv_and_rows",
                    "morton": False, "morton_curve": "2d_frame",
                    "int8_pv": True, "verbose": True,
                    "use_tma": False, "dense_blocks": "0-2,-1",
                },
            }
        }
        invalid = (
            ({"tau": 4.1}, "tau"),
            ({"start_percent": 0.9, "end_percent": 0.2}, "시작 비율"),
            ({"min_tokens": 1.5}, "정수"),
            ({"int8_qk": "false"}, "true 또는 false"),
            ({"sink_conditioning": "unsafe"}, "exact_kv"),
            ({"morton_curve": "hilbert"}, "2d_frame"),
            ({"dense_blocks": "first,last"}, "0-2,-1"),
            ({"model": ["1", 0]}, "지원하지 않는"),
            ({"int8_qk": False, "int8_pv": True}, "INT8 PV"),
        )
        for settings, message in invalid:
            with self.subTest(settings=settings):
                with self.assertRaisesRegex(ValueError, message):
                    workflow_adapter.normalize_sol_attn_settings(workflow, settings)
        normalized = workflow_adapter.normalize_sol_attn_settings(
            workflow, {"int8_qk": False}
        )
        self.assertFalse(normalized["int8_qk"])
        self.assertFalse(normalized["int8_pv"])

    def test_h3_prompt_project_is_exposed_as_r2v_suite_with_linked_assets(self):
        project = self.root / "prompt_projects" / model_test_r2v.DRAGON_SEASON_1_PROJECT_ID
        (project / "EP01-S01").mkdir(parents=True)
        (project / "assets").mkdir()
        (project / "assets" / "hero.png").write_bytes(self.image.read_bytes())
        (project / "manifest.json").write_text(json.dumps({
            "project_kind": "h3_r2v_production", "title": "용 키우기 시즌 1",
        }), encoding="utf-8")
        prompt = "subject_definitions:\n<Subject 1> is the blue dragon from <Picture 1>.\n\ndetailed_description:\n[Shot 1] The blue dragon turns."
        payload = {
            "schema_version": 1, "workflow": "h3_r2v_production",
            "project_id": model_test_r2v.DRAGON_SEASON_1_PROJECT_ID,
            "scene_id": "EP01-S01", "clip_id": "EP01-S01-C01", "sequence": 1,
            "duration_seconds": 9, "video_prompt": prompt,
            "review_intent_ko": "원본 사건과 정체성을 검수한다.",
            "references": [{
                "picture_index": 1, "role": "young_dragon", "label": "어린 용",
                "description": "small blue dragon", "required": True,
                "source_path": "assets/hero.png",
            }],
        }
        (project / "EP01-S01" / "EP01-S01-C01.md").write_text(
            "## Machine Payload\n\n```json\n" + json.dumps(payload) + "\n```\n",
            encoding="utf-8",
        )
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        suite = next(row for row in dashboard["suites"] if row["suite_id"] == model_test_r2v.DRAGON_SEASON_1_SUITE_ID)
        self.assertEqual("h3_r2v_multi_reference", suite["input_mode"])
        self.assertEqual("용 키우기 시즌 1 · 전체 씬·클립", suite["name"])
        self.assertEqual(1, len(suite["cases"]))
        self.assertEqual(prompt, suite["cases"][0]["prompts"][0]["prompt_text"])
        self.assertEqual(["reference_image_1"], [row["role"] for row in suite["cases"][0]["asset_requirements"]])
        links = [row for row in dashboard["case_assets"] if row["case_version_id"] == suite["cases"][0]["case_version_id"]]
        self.assertEqual(1, len(links))

        session = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile["workflow_profile_id"],
            "adapter_id": self.adapter["adapter_id"],
            "suite_id": model_test_r2v.DRAGON_SEASON_1_SUITE_ID,
            "repetitions": 1,
            "resolution": {"width": 832, "height": 480},
        })
        with model_test_registry.open_registry(self.root) as connection:
            preflight = workflow_adapter.preflight_session(connection, session["session_id"])
        self.assertEqual(1, preflight["ready_count"])
        self.assertEqual(0, preflight["blocked_count"])
        queued = benchmark_jobs.queue_session(self.root, session["session_id"])
        self.assertEqual("h3_generation", queued["queue_backend"])
        self.assertEqual(1, queued["queued_count"])
        self.assertFalse((self.root / "runtime/batches").exists())
        self.assertFalse((self.root / "jobs").exists())
        job_id = queued["job_ids"][0]
        request = read_json(self.root / "runtime/h3/jobs" / job_id / "request.json", {})
        self.assertEqual("h3_r2v_benchmark", request["job_type"])
        self.assertEqual(queued["queue_id"], request["test_queue_id"])
        self.assertEqual(["reference_image_1"], [row["role"] for row in request["references"]])
        h3_state = h3_queue.state(self.root)
        self.assertEqual(queued["queue_id"], h3_state["test_queues"][0]["test_queue_id"])
        self.assertEqual("queued", h3_state["test_queues"][0]["status"])
        review_queue = model_test_review_queue.enqueue(
            self.root, session["session_id"]
        )
        self.assertEqual([job_id], review_queue["generation_job_ids"])
        self.assertEqual(1, review_queue["queued_count"])
        self.assertEqual(
            "session_completed_at_execution",
            review_queue["target_scope"],
        )
        self.assertEqual(
            "H3·ComfyUI 생성 큐 완료 후 AI 검수 대기",
            read_json(
                self.root
                / "runtime/model_test_review_queue"
                / review_queue["queue_id"]
                / "status.json",
                {},
            )["stage"],
        )
        benchmark_jobs.record_result(
            self.root, request, status="completed", output_path=str(self.root / "runtime/h3/outputs/test.mp4")
        )
        first_queue_dir = (
            self.root / "runtime/model_test_review_queue" / review_queue["queue_id"]
        )
        atomic_write_json(first_queue_dir / "summary.json", {
            "errors": [{"job_id": job_id, "error": "finish_reason=length"}],
        })
        atomic_write_json(first_queue_dir / "status.json", {
            "status": "completed_with_failures",
        })
        retry = model_test_review_queue.enqueue(self.root, session["session_id"])
        self.assertEqual("latest_failed_reviews", retry["target_scope"])
        self.assertEqual([job_id], retry["generation_job_ids"])
        self.assertEqual(
            [job_id],
            model_test_review_queue.resolved_generation_job_ids(self.root, retry),
        )

    def test_created_project_test_set_is_exposed_as_its_own_r2v_suite(self):
        project_id = "RaisingaDragonSeason01_H3_CINEMATIC_LIGHTING"
        project = self.root / "prompt_projects" / project_id
        (project / "EP01-S01").mkdir(parents=True)
        (project / "assets").mkdir()
        (project / "assets" / "hero.png").write_bytes(self.image.read_bytes())
        (project / "manifest.json").write_text(json.dumps({
            "project_kind": "h3_r2v_production",
            "title": "용 키우기 시즌 1 · MiniMax H3 Cinematic Lighting",
        }), encoding="utf-8")
        prompt = "subject_definitions:\n<Subject 1> is from <Picture 1>.\n\ndetailed_description:\n[Shot 1] The hero advances."
        payload = {
            "schema_version": 1, "workflow": "h3_r2v_production",
            "project_id": project_id, "scene_id": "EP01-S01", "clip_id": "EP01-S01-C01",
            "sequence": 1, "duration_seconds": 9, "video_prompt": prompt,
            "review_intent_ko": "시네마틱 조명과 동작을 검수한다.",
            "references": [{
                "picture_index": 1, "role": "hero", "label": "주인공",
                "description": "cinematic hero", "required": True,
                "source_path": "assets/hero.png",
            }],
        }
        (project / "EP01-S01" / "EP01-S01-C01.md").write_text(
            "## Machine Payload\n\n```json\n" + json.dumps(payload) + "\n```\n",
            encoding="utf-8",
        )

        created = h3_queue.create_project_test_set(self.root, {"project_id": project_id})
        self.assertEqual(project_id, created["project_id"])
        self.assertEqual("blocked", created["status"])
        self.assertEqual(1, created["blocked_count"])

        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        suite_id = model_test_r2v.project_suite_id(project_id)
        suite = next(row for row in dashboard["suites"] if row["suite_id"] == suite_id)
        self.assertEqual("h3_r2v_multi_reference", suite["input_mode"])
        self.assertEqual(1, len(suite["cases"]))
        self.assertEqual(project_id, suite["cases"][0]["contract"]["source_project_id"])
        self.assertEqual(prompt, suite["cases"][0]["prompts"][0]["prompt_text"])
        self.assertTrue(model_test_r2v.is_r2v_suite_id(suite_id))

        session = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile["workflow_profile_id"],
            "adapter_id": self.adapter["adapter_id"],
            "suite_id": suite_id,
            "repetitions": 1,
            "resolution": {"width": 832, "height": 480},
        })
        self.assertEqual(1, session["case_count"])

    def test_deleted_project_suite_is_hidden_without_losing_session_cases_or_assets(self):
        project_id = "project_suite_soft_delete"
        self._write_project(
            project_id,
            "Project Suite Soft Delete",
            [("SCENE_001", "CLIP_001", 1)],
        )
        created = h3_queue.create_project_test_set(
            self.root, {"project_id": project_id}
        )
        suite_id = model_test_r2v.project_suite_id(project_id)

        before = model_test_registry.dashboard(self.root, self.workflows)
        suite = next(
            row for row in before["suites"] if row["suite_id"] == suite_id
        )
        self.assertTrue(suite["deletable"])
        self.assertEqual(
            created["project_test_set_id"], suite["project_test_set_id"]
        )
        self.assertEqual(project_id, suite["source_project_id"])
        self.assertIsNone(suite["source_scene_id"])
        case_version_ids = [
            row["case_version_id"] for row in suite["cases"]
        ]
        self.assertEqual(1, len(case_version_ids))
        linked_asset = next(
            row for row in before["case_assets"]
            if row["case_version_id"] == case_version_ids[0]
        )

        session = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile["workflow_profile_id"],
            "adapter_id": self.adapter["adapter_id"],
            "suite_id": suite_id,
            "repetitions": 1,
            "resolution": {"width": 832, "height": 480},
        })
        session_id = session["session_id"]
        before_with_session = model_test_registry.dashboard(
            self.root, self.workflows
        )
        dashboard_session = next(
            row for row in before_with_session["sessions"]
            if row["session_id"] == session_id
        )
        self.assertEqual(
            "h3_r2v_multi_reference", dashboard_session["input_mode"]
        )
        with model_test_registry.open_registry(self.root) as connection:
            asset_path = model_test_assets.resolve_file(
                self.root, connection, linked_asset["asset_id"]
            )
            asset_bytes = asset_path.read_bytes()
            preserved_counts = {
                "session_cases": connection.execute(
                    "SELECT COUNT(*) count FROM test_session_cases WHERE session_id=?",
                    (session_id,),
                ).fetchone()["count"],
                "suite_cases": connection.execute(
                    "SELECT COUNT(*) count FROM suite_cases WHERE suite_id=?",
                    (suite_id,),
                ).fetchone()["count"],
                "prompts": connection.execute(
                    "SELECT COUNT(*) count FROM benchmark_case_prompts WHERE case_version_id=?",
                    (case_version_ids[0],),
                ).fetchone()["count"],
                "assets": connection.execute(
                    "SELECT COUNT(*) count FROM benchmark_case_assets WHERE case_version_id=?",
                    (case_version_ids[0],),
                ).fetchone()["count"],
            }
        project_files = {
            path.relative_to(self.root): path.read_bytes()
            for path in (self.root / "prompt_projects" / project_id).rglob("*")
            if path.is_file()
        }

        deleted = h3_queue.delete_project_test_set(
            self.root, created["project_test_set_id"]
        )
        self.assertTrue(deleted["soft_deleted"])
        after = model_test_registry.dashboard(self.root, self.workflows)
        self.assertFalse(any(
            row["suite_id"] == suite_id for row in after["suites"]
        ))
        preserved_session = next(
            row for row in after["sessions"]
            if row["session_id"] == session_id
        )
        self.assertEqual(suite_id, preserved_session["suite_id"])
        self.assertEqual(
            "h3_r2v_multi_reference", preserved_session["input_mode"]
        )
        self.assertEqual(1, preserved_session["case_count"])
        self.assertEqual(project_files, {
            path.relative_to(self.root): path.read_bytes()
            for path in (self.root / "prompt_projects" / project_id).rglob("*")
            if path.is_file()
        })

        with model_test_registry.open_registry(self.root) as connection:
            self.assertEqual(0, connection.execute(
                "SELECT active FROM benchmark_suites WHERE suite_id=?",
                (suite_id,),
            ).fetchone()["active"])
            self.assertIsNotNone(connection.execute(
                "SELECT 1 FROM test_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone())
            self.assertEqual(preserved_counts, {
                "session_cases": connection.execute(
                    "SELECT COUNT(*) count FROM test_session_cases WHERE session_id=?",
                    (session_id,),
                ).fetchone()["count"],
                "suite_cases": connection.execute(
                    "SELECT COUNT(*) count FROM suite_cases WHERE suite_id=?",
                    (suite_id,),
                ).fetchone()["count"],
                "prompts": connection.execute(
                    "SELECT COUNT(*) count FROM benchmark_case_prompts WHERE case_version_id=?",
                    (case_version_ids[0],),
                ).fetchone()["count"],
                "assets": connection.execute(
                    "SELECT COUNT(*) count FROM benchmark_case_assets WHERE case_version_id=?",
                    (case_version_ids[0],),
                ).fetchone()["count"],
            })
            self.assertEqual(
                asset_bytes,
                model_test_assets.resolve_file(
                    self.root, connection, linked_asset["asset_id"]
                ).read_bytes(),
            )

        replacement = h3_queue.create_project_test_set(
            self.root, {"project_id": project_id}
        )
        self.assertNotEqual(
            created["project_test_set_id"],
            replacement["project_test_set_id"],
        )
        reactivated = model_test_registry.dashboard(self.root, self.workflows)
        reactivated_suite = next(
            row for row in reactivated["suites"]
            if row["suite_id"] == suite_id
        )
        self.assertEqual(suite_id, reactivated_suite["suite_id"])
        self.assertTrue(reactivated_suite["deletable"])
        self.assertEqual(
            replacement["project_test_set_id"],
            reactivated_suite["project_test_set_id"],
        )
        self.assertTrue(any(
            row["session_id"] == session_id
            for row in reactivated["sessions"]
        ))

    def test_project_and_scene_suite_deletion_are_independent_and_static_suites_are_safe(self):
        project_id = "independent_project_scene_delete"
        self._write_project(project_id, "Independent Delete", [
            ("SCENE_001", "CLIP_001", 1),
            ("SCENE_002", "CLIP_002", 2),
        ])
        project_marker = h3_queue.create_project_test_set(
            self.root, {"project_id": project_id}
        )
        scene_marker = h3_queue.create_project_test_set(self.root, {
            "project_id": project_id,
            "scene_id": "SCENE_001",
        })
        project_suite_id = model_test_r2v.project_suite_id(project_id)
        scene_suite_id = model_test_r2v.project_scene_suite_id(
            project_id, "SCENE_001"
        )

        initial = model_test_registry.dashboard(self.root, self.workflows)
        project_suite = next(
            row for row in initial["suites"]
            if row["suite_id"] == project_suite_id
        )
        scene_suite = next(
            row for row in initial["suites"]
            if row["suite_id"] == scene_suite_id
        )
        self.assertEqual(
            project_marker["project_test_set_id"],
            project_suite["project_test_set_id"],
        )
        self.assertEqual(
            scene_marker["project_test_set_id"],
            scene_suite["project_test_set_id"],
        )

        h3_queue.delete_project_test_set(
            self.root, project_marker["project_test_set_id"]
        )
        after = model_test_registry.dashboard(self.root, self.workflows)
        self.assertFalse(any(
            row["suite_id"] == project_suite_id for row in after["suites"]
        ))
        remaining_scene = next(
            row for row in after["suites"] if row["suite_id"] == scene_suite_id
        )
        self.assertTrue(remaining_scene["deletable"])
        self.assertEqual(
            scene_marker["project_test_set_id"],
            remaining_scene["project_test_set_id"],
        )

        static_suite = next(
            row for row in after["suites"]
            if row["suite_id"] == model_test_r2v.ACTION_SUITE_ID
        )
        self.assertFalse(static_suite["deletable"])
        self.assertIsNone(static_suite["project_test_set_id"])

    def test_scene_test_set_is_a_distinct_r2v_suite_with_only_scene_clips(self):
        project_id = "dragon_scene_validation"
        project = self.root / "prompt_projects" / project_id
        (project / "assets").mkdir(parents=True)
        (project / "assets" / "hero.png").write_bytes(self.image.read_bytes())
        prop_bytes = b"\x89PNG\r\n\x1a\nscene-prop-reference"
        (project / "assets" / "prop.png").write_bytes(prop_bytes)
        (project / "manifest.json").write_text(json.dumps({
            "project_kind": "h3_r2v_production",
            "title": "Dragon Scene Validation",
        }), encoding="utf-8")
        prompts = {}
        clips = (
            ("SCENE_001", "CLIP_001", 1),
            ("SCENE_001", "CLIP_002", 2),
            ("SCENE_002", "CLIP_003", 3),
        )
        for scene_id, clip_id, sequence in clips:
            (project / scene_id).mkdir(exist_ok=True)
            prompt = (
                "subject_definitions:\n<Subject 1> is from <Picture 1>.\n\n"
                f"detailed_description:\n[Shot 1] Scene action {sequence}."
            )
            prompts[clip_id] = prompt
            payload = {
                "schema_version": 1,
                "workflow": "h3_r2v_production",
                "project_id": project_id,
                "scene_id": scene_id,
                "clip_id": clip_id,
                "sequence": sequence,
                "duration_seconds": 5,
                "video_prompt": prompt,
                "review_intent_ko": f"{scene_id} 동작을 검수한다.",
                "references": [{
                    "picture_index": 1,
                    "role": "hero",
                    "label": "주인공",
                    "description": "same hero",
                    "required": True,
                    "source_path": "assets/hero.png",
                }, {
                    "picture_index": 2,
                    "role": "prop",
                    "label": "소품",
                    "description": "same prop",
                    "required": True,
                    "source_path": "assets/prop.png",
                }],
            }
            (project / scene_id / f"{clip_id}.md").write_text(
                "## Machine Payload\n\n```json\n"
                + json.dumps(payload) + "\n```\n",
                encoding="utf-8",
            )

        project_test_set = h3_queue.create_project_test_set(
            self.root, {"project_id": project_id}
        )
        scene_test_set = h3_queue.create_project_test_set(self.root, {
            "project_id": project_id,
            "scene_id": "SCENE_001",
        })
        self.assertEqual("project", project_test_set["scope"])
        self.assertEqual("scene", scene_test_set["scope"])
        self.assertEqual(2, scene_test_set["clip_count"])

        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        project_suite_id = model_test_r2v.project_suite_id(project_id)
        scene_suite_id = model_test_r2v.project_scene_suite_id(
            project_id, "SCENE_001"
        )
        self.assertNotEqual(project_suite_id, scene_suite_id)
        project_suite = next(
            row for row in dashboard["suites"]
            if row["suite_id"] == project_suite_id
        )
        scene_suite = next(
            row for row in dashboard["suites"]
            if row["suite_id"] == scene_suite_id
        )
        self.assertEqual(3, len(project_suite["cases"]))
        self.assertEqual(2, len(scene_suite["cases"]))
        self.assertIn("SCENE_001", scene_suite["name"])
        self.assertTrue(model_test_r2v.is_r2v_suite_id(scene_suite_id))
        self.assertEqual(
            {"CLIP_001", "CLIP_002"},
            {
                row["contract"]["source_clip_id"]
                for row in scene_suite["cases"]
            },
        )
        for case in scene_suite["cases"]:
            clip_id = case["contract"]["source_clip_id"]
            self.assertEqual("SCENE_001", case["contract"]["source_scene_id"])
            self.assertEqual(prompts[clip_id], case["prompts"][0]["prompt_text"])
            links = [
                row for row in dashboard["case_assets"]
                if row["case_version_id"] == case["case_version_id"]
            ]
            self.assertEqual(
                ["reference_image_1", "reference_image_2"],
                [row["role"] for row in links],
            )

        session = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile["workflow_profile_id"],
            "adapter_id": self.adapter["adapter_id"],
            "suite_id": scene_suite_id,
            "repetitions": 1,
            "resolution": {"width": 832, "height": 480},
        })
        self.assertEqual(2, session["case_count"])
        with model_test_registry.open_registry(self.root) as connection:
            preflight = workflow_adapter.preflight_session(
                connection, session["session_id"]
            )
        self.assertEqual(2, preflight["ready_count"])
        queued = benchmark_jobs.queue_session(self.root, session["session_id"])
        self.assertEqual(2, queued["queued_count"])
        expected_shas = [
            hashlib.sha256(self.image.read_bytes()).hexdigest(),
            hashlib.sha256(prop_bytes).hexdigest(),
        ]
        for job_id in queued["job_ids"]:
            request = read_json(
                self.root / "runtime/h3/jobs" / job_id / "request.json", {}
            )
            self.assertEqual(
                ["reference_image_1", "reference_image_2"],
                [row["role"] for row in request["references"]],
            )
            self.assertEqual(
                expected_shas,
                [row["sha256"] for row in request["references"]],
            )
            self.assertEqual(
                ["139", "137"],
                [row["node_id"] for row in request["reference_patches"]],
            )

    def test_scene_registration_membership_changes_only_after_reregister(self):
        project_id = "scene_snapshot_membership"
        self._write_project(
            project_id,
            "Scene Snapshot Membership",
            [("SCENE_001", "CLIP_001", 1)],
        )
        first = h3_queue.create_project_test_set(self.root, {
            "project_id": project_id,
            "scene_id": "SCENE_001",
        })
        suite_id = model_test_r2v.project_scene_suite_id(
            project_id, "SCENE_001"
        )
        initial = model_test_registry.dashboard(self.root, self.workflows)
        initial_suite = next(
            row for row in initial["suites"] if row["suite_id"] == suite_id
        )
        self.assertEqual(["CLIP_001"], [
            row["contract"]["source_clip_id"]
            for row in initial_suite["cases"]
        ])

        self._write_project(
            project_id,
            "Scene Snapshot Membership",
            [("SCENE_001", "CLIP_002", 2)],
        )
        before_reregister = model_test_registry.dashboard(
            self.root, self.workflows
        )
        fixed_suite = next(
            row for row in before_reregister["suites"]
            if row["suite_id"] == suite_id
        )
        self.assertEqual(["CLIP_001"], [
            row["contract"]["source_clip_id"]
            for row in fixed_suite["cases"]
        ])

        latest = h3_queue.create_project_test_set(self.root, {
            "project_id": project_id,
            "scene_id": "SCENE_001",
        })
        self.assertNotEqual(
            first["project_test_set_id"], latest["project_test_set_id"]
        )
        after_reregister = model_test_registry.dashboard(
            self.root, self.workflows
        )
        updated_suite = next(
            row for row in after_reregister["suites"]
            if row["suite_id"] == suite_id
        )
        self.assertEqual(["CLIP_001", "CLIP_002"], [
            row["contract"]["source_clip_id"]
            for row in updated_suite["cases"]
        ])

    def test_same_title_and_scene_in_distinct_projects_have_unique_suite_names(self):
        project_ids = ("same_title_project_a", "same_title_project_b")
        for project_id in project_ids:
            self._write_project(
                project_id,
                "Shared Display Title",
                [("SCENE_001", "CLIP_001", 1)],
            )
            h3_queue.create_project_test_set(self.root, {
                "project_id": project_id,
                "scene_id": "SCENE_001",
            })

        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        suites = [
            next(
                row for row in dashboard["suites"]
                if row["suite_id"] == model_test_r2v.project_scene_suite_id(
                    project_id, "SCENE_001"
                )
            )
            for project_id in project_ids
        ]
        self.assertNotEqual(suites[0]["suite_id"], suites[1]["suite_id"])
        self.assertNotEqual(suites[0]["name"], suites[1]["name"])
        for project_id, suite in zip(project_ids, suites):
            self.assertIn(project_id, suite["name"])

    def test_scope_less_schema1_registration_remains_project_wide(self):
        project_id = "schema1_project_registration"
        self._write_project(project_id, "Schema 1 Project", [
            ("SCENE_001", "CLIP_001", 1),
            ("SCENE_002", "CLIP_002", 2),
        ])
        marker = (
            self.root / "runtime/h3/project_test_sets/legacy_schema1"
        )
        marker.mkdir(parents=True)
        (marker / "project_test_set.json").write_text(json.dumps({
            "schema_version": 1,
            "project_test_set_id": "legacy_schema1",
            "project_id": project_id,
            "scene_id": "SCENE_001",
            "clip_ids": ["CLIP_001"],
            "status": "ready_to_queue",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }), encoding="utf-8")

        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        suite_id = model_test_r2v.project_suite_id(project_id)
        suite = next(
            row for row in dashboard["suites"] if row["suite_id"] == suite_id
        )
        self.assertEqual({"CLIP_001", "CLIP_002"}, {
            row["contract"]["source_clip_id"] for row in suite["cases"]
        })
        self.assertFalse(any(
            row["suite_id"] == model_test_r2v.project_scene_suite_id(
                project_id, "SCENE_001"
            )
            for row in dashboard["suites"]
        ))

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
        self.assertIn("The cut picks up her sprint", first["prompts"][0]["prompt_text"])
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

    def test_r2v_accepts_preview_resolution_and_rejects_unsupported_resolution(self):
        base = {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile["workflow_profile_id"],
            "adapter_id": self.adapter["adapter_id"],
            "suite_id": model_test_r2v.ACTION_SUITE_ID,
        }
        for suite_id in (model_test_r2v.ACTION_SUITE_ID, model_test_r2v.ACTION_V2_SUITE_ID):
            with self.subTest(suite_id=suite_id), self.assertRaisesRegex(ValueError, "608×352, 736×416, 832×480 또는 1280×736"):
                model_test_registry.create_session(self.root, {
                    **base, "suite_id": suite_id,
                    "resolution": {"width": 768, "height": 480},
                })
        for width, height in ((608, 352), (736, 416), (832, 480), (1280, 736)):
            with self.subTest(resolution=(width, height)):
                preview = model_test_registry.create_session(self.root, {
                    **base, "resolution": {"width": width, "height": height},
                })
                self.assertEqual({"width": width, "height": height}, preview["resolution"])
        with self.assertRaisesRegex(ValueError, "3~10"):
            model_test_registry.create_session(self.root, {
                **base, "resolution": {"width": 832, "height": 480},
                "case_settings": {model_test_r2v.case_version_id("rs05"): {"enemy_count": 11}},
            })


if __name__ == "__main__":
    unittest.main()
