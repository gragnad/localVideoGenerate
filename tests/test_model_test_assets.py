from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import model_test_assets
import model_test_registry
import workflow_adapter


class ModelTestAssetsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.upload = self.root / "reference.png"
        self.upload.write_bytes(b"\x89PNG\r\n\x1a\n" + b"benchmark-reference")
        with model_test_registry.open_registry(self.root) as connection:
            self.case_id = connection.execute(
                """SELECT case_version_id FROM benchmark_case_asset_requirements
                   WHERE case_version_id='benchmark_reference_following_v1'
                     AND role='reference_image'"""
            ).fetchone()[0]

    def tearDown(self):
        self.temp.cleanup()

    def test_asset_is_content_addressed_linked_and_resolvable(self):
        with model_test_registry.open_registry(self.root) as connection:
            first = model_test_assets.save_and_link(self.root, connection, {
                "case_version_id": self.case_id,
                "role": "reference_image",
                "upload_path": str(self.upload),
                "original_name": "캐릭터 참조.png",
            })
            second = model_test_assets.save_and_link(self.root, connection, {
                "case_version_id": self.case_id,
                "role": "reference_image",
                "upload_path": str(self.upload),
                "original_name": "같은 이미지.png",
            })
            self.assertEqual(first["asset_id"], second["asset_id"])
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM benchmark_case_assets").fetchone()[0], 1)
            path = model_test_assets.resolve_file(self.root, connection, first["asset_id"])
            self.assertEqual(path.read_bytes(), self.upload.read_bytes())
            dashboard = model_test_assets.case_assets(connection)
            self.assertEqual(dashboard[0]["metadata"]["mime_type"], "image/png")
            self.assertNotIn("path", dashboard[0])

    def test_unlink_preserves_immutable_library_file(self):
        with model_test_registry.open_registry(self.root) as connection:
            saved = model_test_assets.save_and_link(self.root, connection, {
                "case_version_id": self.case_id, "role": "reference_image", "upload_path": str(self.upload)
            })
            path = model_test_assets.resolve_file(self.root, connection, saved["asset_id"])
            out = model_test_assets.unlink(connection, {"case_version_id": self.case_id, "role": "reference_image"})
            self.assertTrue(out["unlinked"])
            self.assertTrue(path.is_file())
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM benchmark_case_assets").fetchone()[0], 0)

    def test_invalid_image_and_undefined_role_are_rejected(self):
        bad = self.root / "bad.png"
        bad.write_bytes(b"not-an-image")
        with model_test_registry.open_registry(self.root) as connection:
            with self.assertRaisesRegex(ValueError, "PNG"):
                model_test_assets.save_and_link(self.root, connection, {
                    "case_version_id": self.case_id, "role": "reference_image", "upload_path": str(bad)
                })
            with self.assertRaisesRegex(ValueError, "정의되지 않은"):
                model_test_assets.save_and_link(self.root, connection, {
                    "case_version_id": self.case_id, "role": "background", "upload_path": str(self.upload)
                })

    def test_linked_reference_and_image_binding_make_all_cases_ready(self):
        workflows = self.root / "workflows"
        workflows.mkdir()
        workflow = workflows / "official.json"
        workflow.write_text(json.dumps({
            "1": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
            "2": {"class_type": "LoadImage", "inputs": {"image": "reference.png"}},
            "3": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"length": 121}},
        }), encoding="utf-8")
        model_id = model_test_registry.register_model(self.root, {
            "provider": "Provider", "family": "Family", "display_name": "Model"
        })["model_id"]
        profile_id = model_test_registry.register_workflow(self.root, workflows, {
            "model_id": model_id, "workflow_filename": workflow.name, "name": "Official"
        })["workflow_profile_id"]
        with model_test_registry.open_registry(self.root) as connection:
            adapter_id = workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": profile_id,
                "bindings": {
                    "prompt": {"node_id": "1", "input": "text"},
                    "reference_image": {"node_id": "2", "input": "image"},
                    "frame_count": {"node_id": "3", "input": "length"},
                },
            })["adapter_id"]
            model_test_assets.save_and_link(self.root, connection, {
                "case_version_id": self.case_id, "role": "reference_image", "upload_path": str(self.upload)
            })
        session_id = model_test_registry.create_session(self.root, {
            "model_id": model_id, "workflow_profile_id": profile_id, "adapter_id": adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID, "repetitions": 1,
        })["session_id"]
        with model_test_registry.open_registry(self.root) as connection:
            result = workflow_adapter.preflight_session(connection, session_id)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["ready_count"], 39)
        self.assertEqual(result["blocked_count"], 0)

    def test_i2v_suite_requires_one_fixed_anchor_for_every_case(self):
        workflows = self.root / "i2v_workflows"
        workflows.mkdir()
        workflow = workflows / "official_i2v.json"
        workflow.write_text(json.dumps({
            "1": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
            "2": {"class_type": "LoadImage", "inputs": {"image": "reference.png"}},
            "3": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"length": 121}},
        }), encoding="utf-8")
        model_id = model_test_registry.register_model(self.root, {
            "provider": "Provider", "family": "I2V", "display_name": "I2V Model"
        })["model_id"]
        profile_id = model_test_registry.register_workflow(self.root, workflows, {
            "model_id": model_id, "workflow_filename": workflow.name, "name": "Official I2V"
        })["workflow_profile_id"]
        with model_test_registry.open_registry(self.root) as connection:
            adapter_id = workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": profile_id,
                "bindings": {
                    "prompt": {"node_id": "1", "input": "text"},
                    "reference_image": {"node_id": "2", "input": "image"},
                    "frame_count": {"node_id": "3", "input": "length"},
                },
            })["adapter_id"]
        session_id = model_test_registry.create_session(self.root, {
            "model_id": model_id,
            "workflow_profile_id": profile_id,
            "adapter_id": adapter_id,
            "suite_id": model_test_registry.I2V_SUITE_ID,
        })["session_id"]
        with model_test_registry.open_registry(self.root) as connection:
            blocked = workflow_adapter.preflight_session(connection, session_id)
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["blocked_count"], 39)
            case_ids = [row[0] for row in connection.execute(
                "SELECT case_version_id FROM suite_cases WHERE suite_id=? ORDER BY ordering",
                (model_test_registry.I2V_SUITE_ID,),
            )]
            for case_id in case_ids:
                model_test_assets.save_and_link(self.root, connection, {
                    "case_version_id": case_id,
                    "role": "reference_image",
                    "upload_path": str(self.upload),
                })
            ready = workflow_adapter.preflight_session(connection, session_id)
        self.assertEqual(ready["status"], "ready")
        self.assertEqual(ready["ready_count"], 39)


if __name__ == "__main__":
    unittest.main()
