from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import evaluation_db
import model_test_registry
import workflow_adapter


class ModelTestRegistryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        (self.workflows / "official.json").write_text(json.dumps({"1": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}}, "2": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}}, "3": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output"}}}), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def register_model(self, name="Test Video"):
        return model_test_registry.register_model(self.root, {
            "provider": "Test Provider",
            "family": "Test Family",
            "display_name": name,
            "version": "1.0",
        })["model_id"]

    def register_workflow(self, model_id):
        return model_test_registry.register_workflow(self.root, self.workflows, {
            "model_id": model_id,
            "workflow_filename": "official.json",
            "profile_kind": "official_baseline",
            "name": "Official sample",
        })

    def register_adapter(self, profile_id):
        with model_test_registry.open_registry(self.root) as connection:
            return workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": profile_id,
                "adapter_name": "Official bindings",
                "adapter_version": "1",
                "bindings": {
                    "prompt": {"node_id": "1", "input": "text"},
                    "seed": {"node_id": "2", "input": "noise_seed"},
                    "filename_prefix": {"node_id": "3", "input": "filename_prefix"},
                },
            })["adapter_id"]

    def test_default_suite_is_versioned_and_model_neutral(self):
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        self.assertEqual(dashboard["schema_version"], 10)
        self.assertEqual(len(dashboard["suites"]), 5)
        generic = next(item for item in dashboard["suites"] if item["suite_id"] == model_test_registry.DEFAULT_SUITE_ID)
        cases = generic["cases"]
        self.assertEqual(len(cases), 39)
        self.assertEqual([item["ordering"] for item in cases], list(range(1, 40)))
        ground = next(item for item in cases if item["category"] == "motion_physics")
        self.assertIn("공중 부양", ground["contract"]["forbidden_failures"])
        self.assertNotIn("LTX", ground["intent_ko"])
        action_cases = [item for item in cases if item["case_version_id"].startswith("benchmark_action_level_")]
        self.assertEqual([item["ordering"] for item in action_cases], [17, 18, 19, 20, 21])
        self.assertEqual(action_cases[-1]["contract"]["generation"]["target_seconds"], 10)
        vfx_cases = [item for item in cases if item["category"] == "vfx_effects"]
        self.assertEqual([item["ordering"] for item in vfx_cases], [22, 23, 24, 25, 26])
        advanced_ids = [
            "benchmark_attribute_binding_v1", "benchmark_environment_reaction_v1",
            "benchmark_emotional_acting_v1", "benchmark_state_persistence_v1",
            "benchmark_scale_perspective_v1", "benchmark_offscreen_return_v1",
            "benchmark_dialogue_action_v1", "benchmark_style_persistence_v1",
        ]
        self.assertEqual(
            [item["case_version_id"] for item in cases if 27 <= item["ordering"] <= 34],
            advanced_ids,
        )
        scenario_cases = [item for item in cases if item["category"] == "scenario_comprehension"]
        self.assertEqual([item["ordering"] for item in scenario_cases], [35, 36, 37, 38, 39])
        self.assertEqual(
            [item["contract"]["generation"]["target_seconds"] for item in scenario_cases],
            [8, 10, 12, 16, 20],
        )
        i2v = next(item for item in dashboard["suites"] if item["suite_id"] == model_test_registry.I2V_SUITE_ID)
        self.assertTrue(i2v["recommended"])
        self.assertEqual(i2v["input_mode"], "i2v_fixed_anchor")
        self.assertEqual(len(i2v["cases"]), 39)
        self.assertEqual([item["ordering"] for item in i2v["cases"]], list(range(1, 40)))
        self.assertTrue(all(len(item["prompts"]) == 1 for item in i2v["cases"]))
        self.assertTrue(all(len(item["asset_requirements"]) == 1 for item in i2v["cases"]))
        expected_seconds = model_test_registry.CASE_TARGET_SECONDS
        for suite in (generic, i2v):
            for item in suite["cases"]:
                short_id = item["case_version_id"].removeprefix("benchmark_")
                short_id = short_id.removesuffix("_i2v_v1").removesuffix("_v1")
                generation = item["contract"]["generation"]
                self.assertEqual(generation["target_seconds"], expected_seconds[short_id])
                self.assertEqual(generation["frame_count"], expected_seconds[short_id] * 24 + 1)

    def test_official_workflow_is_registered_with_hash_and_format(self):
        model_id = self.register_model()
        result = self.register_workflow(model_id)
        self.assertEqual(result["workflow_format"], "comfyui_api")
        self.assertEqual(len(result["workflow_sha256"]), 64)
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        profile = dashboard["workflows"][0]
        self.assertEqual(profile["profile_kind"], "official_baseline")
        self.assertEqual(profile["model_id"], model_id)

    def test_minimax_h3_session_requires_32_multiple_and_accepts_fast_resolution(self):
        model_id = self.register_model("MiniMax H3")
        profile_id = self.register_workflow(model_id)["workflow_profile_id"]
        adapter_id = self.register_adapter(profile_id)
        base = {
            "model_id": model_id,
            "workflow_profile_id": profile_id,
            "adapter_id": adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID,
        }
        with self.assertRaisesRegex(ValueError, "32의 배수"):
            model_test_registry.create_session(self.root, {
                **base, "resolution": {"width": 768, "height": 432},
            })
        result = model_test_registry.create_session(self.root, {
            **base, "resolution": {"width": 608, "height": 352},
        })
        self.assertEqual(result["resolution"], {"width": 608, "height": 352})

    def test_session_plans_every_case_without_starting_generation(self):
        model_id = self.register_model()
        profile_id = self.register_workflow(model_id)["workflow_profile_id"]
        adapter_id = self.register_adapter(profile_id)
        result = model_test_registry.create_session(self.root, {
            "model_id": model_id,
            "workflow_profile_id": profile_id,
            "adapter_id": adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID,
            "repetitions": 3,
            "resolution": {"width": 1344, "height": 768},
        })
        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["resolution"], {"width": 1344, "height": 768})
        self.assertEqual(result["case_count"], 39)
        self.assertEqual(result["planned_run_count"], 117)
        with evaluation_db.connect(self.root / evaluation_db.DEFAULT_DB_PATH) as connection:
            statuses = connection.execute("SELECT DISTINCT status FROM test_session_cases").fetchall()
            self.assertEqual([row[0] for row in statuses], ["planned"])
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM generation_runs").fetchone()[0], 0)
            session = connection.execute("SELECT output_width,output_height FROM test_sessions").fetchone()
            self.assertEqual((session["output_width"], session["output_height"]), (1344, 768))

    def test_planned_session_history_can_be_deleted(self):
        model_id = self.register_model()
        profile_id = self.register_workflow(model_id)["workflow_profile_id"]
        adapter_id = self.register_adapter(profile_id)
        session_id = model_test_registry.create_session(self.root, {
            "model_id": model_id,
            "workflow_profile_id": profile_id,
            "adapter_id": adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID,
        })["session_id"]
        deleted = model_test_registry.delete_session(self.root, session_id)
        self.assertEqual(deleted["session_id"], session_id)
        self.assertEqual(deleted["deleted_run_count"], 0)
        with model_test_registry.open_registry(self.root) as connection:
            self.assertIsNone(connection.execute("SELECT 1 FROM test_sessions WHERE session_id=?", (session_id,)).fetchone())
        repeated = model_test_registry.delete_session(self.root, session_id)
        self.assertTrue(repeated["already_deleted"])
        self.assertEqual(repeated["deleted_run_count"], 0)

    def test_orphaned_ai_review_status_does_not_block_session_delete(self):
        model_id = self.register_model()
        profile_id = self.register_workflow(model_id)["workflow_profile_id"]
        adapter_id = self.register_adapter(profile_id)
        session_id = model_test_registry.create_session(self.root, {
            "model_id": model_id,
            "workflow_profile_id": profile_id,
            "adapter_id": adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID,
        })["session_id"]
        with model_test_registry.open_registry(self.root) as connection:
            connection.execute(
                "UPDATE test_sessions SET status='ai_review_queued' WHERE session_id=?",
                (session_id,),
            )
            connection.commit()

        deleted = model_test_registry.delete_session(self.root, session_id)
        self.assertEqual(session_id, deleted["session_id"])
        self.assertEqual(0, deleted["deleted_review_queue_count"])
        with model_test_registry.open_registry(self.root) as connection:
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM test_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone())

    def test_workflow_cannot_be_attached_to_another_model(self):
        first = self.register_model("First")
        second = model_test_registry.register_model(self.root, {
            "model_id": "second",
            "provider": "Test Provider",
            "family": "Test Family",
            "display_name": "Second",
        })["model_id"]
        profile_id = self.register_workflow(first)["workflow_profile_id"]
        adapter_id = self.register_adapter(profile_id)
        with self.assertRaisesRegex(ValueError, "속하지 않습니다"):
            model_test_registry.create_session(self.root, {
                "model_id": second,
                "workflow_profile_id": profile_id,
                "adapter_id": adapter_id,
                "suite_id": model_test_registry.DEFAULT_SUITE_ID,
            })

    def test_workflow_path_must_be_direct_child_json(self):
        model_id = self.register_model()
        with self.assertRaisesRegex(ValueError, "허용되지 않는"):
            model_test_registry.register_workflow(self.root, self.workflows, {
                "model_id": model_id,
                "workflow_filename": "../official.json",
                "name": "Bad",
            })

    def test_ltx_is_review_history_only_and_hidden_from_new_workflows(self):
        (self.workflows / "(basic)video_ltx2_3_i2v_api.json").write_text(
            json.dumps({"1": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}}}),
            encoding="utf-8",
        )
        available = model_test_registry.available_workflows(self.workflows)
        self.assertEqual(["official.json"], [row["filename"] for row in available])
        with self.assertRaisesRegex(ValueError, "열람 전용"):
            model_test_registry.register_model(self.root, {
                "provider": "Lightricks", "family": "LTX 2.3",
                "display_name": "LTX 2.3 Basic", "version": "2.3",
            })
        with model_test_registry.open_registry(self.root) as connection:
            connection.execute(
                """INSERT INTO models(
                       model_id,provider,family,display_name,version,modality,capabilities_json
                   ) VALUES ('legacy_ltx','Lightricks','LTX 2.3','LTX reviewed','2.3','video','{}')"""
            )
        dashboard = model_test_registry.dashboard(self.root, self.workflows)
        legacy = next(row for row in dashboard["models"] if row["model_id"] == "legacy_ltx")
        self.assertTrue(legacy["legacy_read_only"])


class ModelTestUITest(unittest.TestCase):
    def test_model_test_page_and_api_are_connected(self):
        root = Path(__file__).resolve().parents[1]
        index = (root / "web/public/index.html").read_text(encoding="utf-8")
        app = (root / "web/public/app.js").read_text(encoding="utf-8")
        server = (root / "web/server.mjs").read_text(encoding="utf-8")
        self.assertIn('data-page="model-tests"', index)
        self.assertIn('id="testSessionForm"', index)
        self.assertIn("refreshModelTests", app)
        self.assertIn("/api/model-tests/sessions", app)
        self.assertIn("id=\"testAdapterForm\"", index)
        self.assertIn("/api/model-tests/adapters", app)
        self.assertIn("preflight_model_test_session", server)
        self.assertIn("data-test-asset-file", app)
        self.assertIn("save_model_test_asset", server)
        self.assertIn('id="modelTestResults"', index)
        self.assertIn('id="modelTestReviewDialog"', index)
        self.assertIn('data-model-test-review', app)
        self.assertIn('/api/model-tests/comparison', app)
        self.assertIn('model_test_run_review', server)
        self.assertIn('model_test_session_results', server)
        self.assertIn('id="modelTestAnalysis"', index)
        self.assertIn('id="runModelTestAnalysis"', index)
        self.assertIn('modelTestRetestControls', app)
        self.assertIn('copyModelTestPromptGuidance', app)
        self.assertIn('data-copy-test-prompt', app)
        self.assertIn('고정 I2V 시작 이미지', app)
        self.assertIn('suggested_bindings', app)
        self.assertIn('copyTextToClipboard(prompt.prompt_text)', app)
        self.assertNotIn('data-test-ai-review', app)
        self.assertIn('보관된 AI 검수 · 읽기 전용', app)
        self.assertIn('modelTestReviewSummaries', app)
        self.assertNotIn('queue_model_test_ai_review', server)
        self.assertNotIn('/ai-review', server)
        self.assertNotIn('modelTestAiReviewStatus', app)
        self.assertIn('model-test-ai-progress', app)
        self.assertNotIn("['job','batch'].includes(detail.resource)", app)
        self.assertNotIn("kind: 'model_review_queue'", server)
        self.assertNotIn('navigator.clipboard.writeText(prompt.prompt_text)', app)
        self.assertIn('modelTestSubcategoryOptions', app)
        self.assertIn('data-model-test-field="subcategory"', app)
        self.assertIn('model_test_analysis', server)
        self.assertIn('save_model_test_policy', server)
        self.assertIn('create_model_test_followup', server)
        self.assertIn('export_model_tests', server)
        self.assertIn("python('create_model_test_session'", server)
        self.assertIn("delete_model_test_session", server)
        self.assertIn("data-delete-model-test-session", app)
        self.assertIn('id="r2vSharedAssets"', index)
        self.assertIn("data-r2v-shared-upload", app)
        self.assertIn("/api/model-tests/r2v/shared-assets/", app)
        self.assertIn("save_r2v_shared_asset", server)
        self.assertIn("unlink_r2v_shared_asset", server)
        self.assertIn("activeModelTestModels", app)
        self.assertIn("item.legacy_read_only!==true", app)
        adapter_source = (root / "workflow_adapter.py").read_text(encoding="utf-8")
        self.assertNotIn("TextGenerateLTX2Prompt", adapter_source)
        self.assertNotIn("LiconMSR", adapter_source)
        self.assertNotIn("LTXVEmptyLatentAudio", adapter_source)


if __name__ == "__main__":
    unittest.main()
