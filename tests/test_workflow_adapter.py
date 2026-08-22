from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import model_test_registry
import model_test_assets
import workflow_adapter


class WorkflowAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        self.workflow_path = self.workflows / "official_api.json"
        self.workflow_path.write_text(json.dumps({
            "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "default"}},
            "2": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}},
            "3": {"class_type": "EmptyVideoLatent", "inputs": {"width": 512, "height": 288, "length": 97, "batch_size": 1}},
            "4": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output", "format": "auto"}},
            "5": {"class_type": "LoadImage", "inputs": {"image": "reference.png"}},
            "6": {"class_type": "LoadImage", "inputs": {"image": "last.png"}},
            "7": {
                "class_type": "MiniMaxH3ImageToVideo",
                "inputs": {"first_frame": ["5", 0], "last_frame": ["6", 0]},
            },
        }), encoding="utf-8")
        self.model_id = model_test_registry.register_model(self.root, {
            "provider": "Provider", "family": "Family", "display_name": "Video Model", "version": "1"
        })["model_id"]
        self.profile_id = model_test_registry.register_workflow(self.root, self.workflows, {
            "model_id": self.model_id, "workflow_filename": self.workflow_path.name,
            "profile_kind": "official_baseline", "name": "Official API",
        })["workflow_profile_id"]

    def tearDown(self):
        self.temp.cleanup()

    def bindings(self):
        return {
            "prompt": {"node_id": "1", "input": "text"},
            "seed": {"node_id": "2", "input": "noise_seed"},
            "width": {"node_id": "3", "input": "width"},
            "height": {"node_id": "3", "input": "height"},
            "frame_count": {"node_id": "3", "input": "length"},
            "filename_prefix": {"node_id": "4", "input": "filename_prefix"},
            "reference_image": {"node_id": "5", "input": "image"},
        }

    def register_adapter(self):
        with model_test_registry.open_registry(self.root) as connection:
            return workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": self.profile_id,
                "adapter_name": "Official binding",
                "adapter_version": "1",
                "prompt_template": "Official prompt rules:\n{prompt}",
                "bindings": self.bindings(),
            })["adapter_id"]

    def create_session(self):
        adapter_id = self.register_adapter()
        result = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile_id,
            "adapter_id": adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID,
            "repetitions": 2,
        })
        return result["session_id"]

    def test_inspection_lists_bindable_scalar_inputs(self):
        with model_test_registry.open_registry(self.root) as connection:
            result = workflow_adapter.inspect_workflow(connection, self.profile_id)
        choices = {(row["node_id"], row["input"]) for row in result["binding_options"]}
        self.assertIn(("1", "text"), choices)
        self.assertIn(("3", "length"), choices)
        self.assertEqual(
            result["suggested_bindings"]["reference_image"],
            {"node_id": "5", "input": "image"},
        )

    def test_h3_prompt_and_duration_bindings_are_suggested(self):
        h3_path = self.workflows / "h3_api.json"
        h3_path.write_text(json.dumps({
            "1": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"prompt": "", "width": 832, "height": 480, "length": ["2", 0]}},
            "2": {"class_type": "PrimitiveFloat", "_meta": {"title": "Float (duration)"}, "inputs": {"value": 5}},
        }), encoding="utf-8")
        profile_id = model_test_registry.register_workflow(self.root, self.workflows, {
            "model_id": self.model_id, "workflow_filename": h3_path.name,
            "profile_kind": "controlled_variant", "name": "H3 API",
        })["workflow_profile_id"]
        with model_test_registry.open_registry(self.root) as connection:
            result = workflow_adapter.inspect_workflow(connection, profile_id)
        self.assertEqual(result["suggested_bindings"]["prompt"], {"node_id": "1", "input": "prompt"})
        self.assertEqual(result["suggested_bindings"]["duration_seconds"], {"node_id": "2", "input": "value"})

    def test_fractional_target_seconds_are_preserved_for_h3_float_duration(self):
        h3_path = self.workflows / "h3_fractional_duration_api.json"
        h3_path.write_text(json.dumps({
            "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "default"}},
            "2": {
                "class_type": "PrimitiveFloat",
                "_meta": {"title": "Float (Duration)"},
                "inputs": {"value": 5.0},
            },
        }), encoding="utf-8")
        profile_id = model_test_registry.register_workflow(self.root, self.workflows, {
            "model_id": self.model_id,
            "workflow_filename": h3_path.name,
            "profile_kind": "controlled_variant",
            "name": "H3 fractional duration",
        })["workflow_profile_id"]
        with model_test_registry.open_registry(self.root) as connection:
            adapter_id = workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": profile_id,
                "adapter_name": "H3 fractional duration binding",
                "adapter_version": "1",
                "bindings": {
                    "prompt": {"node_id": "1", "input": "text"},
                    "duration_seconds": {"node_id": "2", "input": "value"},
                },
            })["adapter_id"]
        case_version_id = "benchmark_empty_environment_v1"
        session_id = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": profile_id,
            "adapter_id": adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID,
            "repetitions": 1,
        })["session_id"]
        with model_test_registry.open_registry(self.root) as connection:
            row = connection.execute(
                "SELECT contract_json FROM benchmark_case_versions WHERE case_version_id=?",
                (case_version_id,),
            ).fetchone()
            contract = json.loads(row["contract_json"])
            contract["generation"]["target_seconds"] = 10.5
            connection.execute(
                "UPDATE benchmark_case_versions SET contract_json=? WHERE case_version_id=?",
                (json.dumps(contract), case_version_id),
            )
            connection.commit()
            session = connection.execute(
                "SELECT * FROM test_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
            result = workflow_adapter.compile_case(
                connection, session, case_version_id
            )
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["settings"]["duration_seconds"], 10.5)
        self.assertEqual(result["compiled_workflow"]["2"]["inputs"]["value"], 10.5)

    def test_ui_graph_uses_embedded_widget_metadata(self):
        ui_path = self.workflows / "official_ui.json"
        ui_path.write_text(json.dumps({
            "nodes": [
                {"id": 1, "type": "PrimitiveStringMultiline", "mode": 0,
                 "inputs": [{"name": "value", "type": "STRING", "link": None, "widget": {"name": "value"}}],
                 "outputs": [{"name": "STRING", "type": "STRING", "links": []}],
                 "widgets_values": ["prompt text"]},
                {"id": 2, "type": "ResizeImagesByLongerEdge", "mode": 0,
                 "inputs": [
                     {"name": "images", "type": "IMAGE", "link": None},
                     {"name": "longer_edge", "type": "INT", "link": None, "widget": {"name": "longer_edge"}},
                 ],
                 "outputs": [{"name": "images", "type": "IMAGE", "links": []}],
                 "widgets_values": [1536]},
                {"id": 3, "type": "PreviewAny", "mode": 0,
                 "inputs": [], "outputs": [], "widgets_values": [None, None]},
                {"id": 4, "type": "MarkdownNote", "mode": 0,
                 "inputs": [], "outputs": [], "widgets_values": ["note"]},
            ],
            "links": [],
        }), encoding="utf-8")
        profile_id = model_test_registry.register_workflow(self.root, self.workflows, {
            "model_id": self.model_id,
            "workflow_filename": ui_path.name,
            "profile_kind": "controlled_variant",
            "name": "UI graph",
        })["workflow_profile_id"]
        with model_test_registry.open_registry(self.root) as connection:
            result = workflow_adapter.inspect_workflow(connection, profile_id)
        by_node = {row["node_id"]: row for row in result["nodes"]}
        self.assertEqual(by_node["1"]["scalar_inputs"][0]["input"], "value")
        self.assertEqual(by_node["2"]["scalar_inputs"][0]["current_value"], 1536)
        self.assertNotIn("4", by_node)

    def test_invalid_or_duplicate_bindings_are_rejected(self):
        with model_test_registry.open_registry(self.root) as connection:
            with self.assertRaisesRegex(ValueError, "필수 바인딩"):
                workflow_adapter.register_adapter(connection, {
                    "workflow_profile_id": self.profile_id, "bindings": {"seed": {"node_id": "2", "input": "noise_seed"}}
                })
            with self.assertRaisesRegex(ValueError, "중복"):
                workflow_adapter.register_adapter(connection, {
                    "workflow_profile_id": self.profile_id,
                    "bindings": {"prompt": {"node_id": "1", "input": "text"}, "negative_prompt": {"node_id": "1", "input": "text"}},
                })

    def test_preflight_compiles_text_cases_and_blocks_missing_reference_asset(self):
        session_id = self.create_session()
        with model_test_registry.open_registry(self.root) as connection:
            result = workflow_adapter.preflight_session(connection, session_id)
        self.assertEqual(result["status"], "partially_ready")
        self.assertEqual(result["ready_count"], 38)
        self.assertEqual(result["blocked_count"], 1)
        blocked = next(row for row in result["cases"] if row["status"] == "blocked")
        self.assertIn("테스트 자산 필요", blocked["blockers"][0])

    def test_compilation_changes_copy_not_registered_source(self):
        session_id = self.create_session()
        with model_test_registry.open_registry(self.root) as connection:
            session = connection.execute("SELECT * FROM test_sessions WHERE session_id=?", (session_id,)).fetchone()
            case_id = connection.execute("SELECT case_version_id FROM test_session_cases WHERE session_id=? ORDER BY ordering LIMIT 1", (session_id,)).fetchone()[0]
            result = workflow_adapter.compile_case(connection, session, case_id, 2)
        self.assertEqual(result["status"], "ready")
        self.assertIn("Official prompt rules", result["compiled_workflow"]["1"]["inputs"]["text"])
        seed = result["compiled_workflow"]["2"]["inputs"]["noise_seed"]
        self.assertGreaterEqual(seed, 0)
        self.assertLess(seed, 2**63)
        self.assertEqual(result["settings"]["seed"], seed)
        source = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        self.assertEqual(source["1"]["inputs"]["text"], "default")

    def test_fflf_optional_last_frame_is_removed_when_case_only_has_start_image(self):
        with model_test_registry.open_registry(self.root) as connection:
            adapter_id = workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": self.profile_id,
                "adapter_name": "FFLF binding",
                "adapter_version": "1",
                "bindings": {
                    **self.bindings(),
                    "last_reference_image": {"node_id": "6", "input": "image"},
                },
            })["adapter_id"]
            case_id = "benchmark_reference_following_v1"
            upload = self.root / "start.png"
            upload.write_bytes(b"\x89PNG\r\n\x1a\n" + b"start")
            model_test_assets.save_and_link(self.root, connection, {
                "case_version_id": case_id,
                "role": "reference_image",
                "upload_path": str(upload),
            })
        session_id = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile_id,
            "adapter_id": adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID,
            "repetitions": 1,
        })["session_id"]
        with model_test_registry.open_registry(self.root) as connection:
            session = connection.execute(
                "SELECT * FROM test_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
            result = workflow_adapter.compile_case(connection, session, case_id)
        self.assertEqual("ready", result["status"])
        self.assertNotIn("6", result["compiled_workflow"])
        self.assertNotIn("last_frame", result["compiled_workflow"]["7"]["inputs"])
        self.assertEqual(
            {"node_id": "5", "input": "image"},
            result["assets"][0]["binding"],
        )
        source = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        self.assertIn("6", source)
        self.assertIn("last_frame", source["7"]["inputs"])

    def test_fflf_start_and_last_assets_compile_in_frame_order(self):
        with model_test_registry.open_registry(self.root) as connection:
            adapter_id = workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": self.profile_id,
                "adapter_name": "FFLF binding",
                "adapter_version": "1",
                "bindings": {
                    **self.bindings(),
                    "last_reference_image": {"node_id": "6", "input": "image"},
                },
            })["adapter_id"]
            case_id = "benchmark_reference_following_v1"
            connection.execute(
                """INSERT INTO benchmark_case_asset_requirements
                       (case_version_id,role,kind,minimum_count,description)
                   VALUES (?,'last_reference_image','image',1,'종료 이미지')""",
                (case_id,),
            )
            for role in ("reference_image", "last_reference_image"):
                upload = self.root / f"{role}.png"
                upload.write_bytes(b"\x89PNG\r\n\x1a\n" + role.encode("utf-8"))
                model_test_assets.save_and_link(self.root, connection, {
                    "case_version_id": case_id,
                    "role": role,
                    "upload_path": str(upload),
                })
        session_id = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.profile_id,
            "adapter_id": adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID,
            "repetitions": 1,
        })["session_id"]
        with model_test_registry.open_registry(self.root) as connection:
            session = connection.execute(
                "SELECT * FROM test_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
            result = workflow_adapter.compile_case(connection, session, case_id)
        self.assertEqual("ready", result["status"])
        self.assertEqual(
            ["reference_image", "last_reference_image"],
            [asset["role"] for asset in result["assets"]],
        )
        self.assertEqual(
            ["5", "6"],
            [asset["binding"]["node_id"] for asset in result["assets"]],
        )
        self.assertIn("6", result["compiled_workflow"])
        self.assertEqual(["6", 0], result["compiled_workflow"]["7"]["inputs"]["last_frame"])

    def test_changed_workflow_is_blocked_by_registered_hash(self):
        self.register_adapter()
        self.workflow_path.write_text(json.dumps({"changed": True}), encoding="utf-8")
        with model_test_registry.open_registry(self.root) as connection:
            with self.assertRaisesRegex(ValueError, "변경되었습니다"):
                workflow_adapter.inspect_workflow(connection, self.profile_id)


if __name__ == "__main__":
    unittest.main()
