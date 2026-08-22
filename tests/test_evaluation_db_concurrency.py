from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import evaluation_db
import model_test_r2v
import model_test_registry


def _r2v_workflow() -> dict[str, dict]:
    return {
        "92": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output"}},
        "119": {"class_type": "VAELoader", "inputs": {"vae_name": "video"}},
        "120": {"class_type": "VAELoader", "inputs": {"vae_name": "audio"}},
        "128": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen"}},
        "129": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}},
        "132": {"class_type": "PrimitiveFloat", "inputs": {"value": 5}},
        "136": {
            "class_type": "MiniMaxH3ReferenceToVideo",
            "inputs": {
                "prompt": ["138", 0],
                "width": ["141", 0],
                "height": ["142", 0],
                "length": ["131", 1],
                "clip": ["128", 0],
                "vae": ["119", 0],
                "audio_vae": ["120", 0],
                "ref_images.ref_image_0": ["139", 0],
                "ref_images.ref_image_1": ["137", 0],
            },
        },
        "137": {"class_type": "LoadImage", "inputs": {"image": "picture2.png"}},
        "138": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": "prompt"}},
        "139": {"class_type": "LoadImage", "inputs": {"image": "picture1.png"}},
        "141": {"class_type": "PrimitiveInt", "inputs": {"value": 832}},
        "142": {"class_type": "PrimitiveInt", "inputs": {"value": 480}},
    }


class EvaluationDatabaseConcurrencyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        (self.workflows / model_test_r2v.R2V_WORKFLOW_FILENAME).write_text(
            json.dumps(_r2v_workflow()), encoding="utf-8"
        )
        model_test_registry.register_model(
            self.root,
            {
                "provider": "MiniMax",
                "family": "H3",
                "display_name": "MiniMax H3",
                "version": "1",
            },
        )
        model_test_registry.dashboard(self.root, self.workflows)

    def tearDown(self):
        self.temp.cleanup()

    def test_registry_connection_uses_extended_busy_timeout(self):
        db_path = self.root / evaluation_db.DEFAULT_DB_PATH
        with evaluation_db.connect(db_path) as connection:
            busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
        self.assertEqual(evaluation_db.BUSY_TIMEOUT_MS, busy_timeout)
        self.assertGreaterEqual(busy_timeout, 30_000)

    def test_dashboard_and_adapter_wait_for_a_concurrent_registry_writer(self):
        db_path = self.root / evaluation_db.DEFAULT_DB_PATH
        writer_locked = threading.Event()
        release_writer = threading.Event()

        def hold_write_lock() -> None:
            with evaluation_db.connect(db_path) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "UPDATE schema_metadata SET value=value WHERE key='schema_version'"
                )
                writer_locked.set()
                if not release_writer.wait(timeout=5):
                    raise TimeoutError("test writer release was not signalled")
                connection.commit()

        with ThreadPoolExecutor(max_workers=3) as executor:
            writer = executor.submit(hold_write_lock)
            self.assertTrue(writer_locked.wait(timeout=5))
            dashboard = executor.submit(
                model_test_registry.dashboard, self.root, self.workflows
            )
            adapter = executor.submit(
                model_test_registry.ensure_h3_r2v_adapter,
                self.root,
                self.workflows,
            )
            time.sleep(0.2)
            self.assertFalse(dashboard.done())
            self.assertFalse(adapter.done())
            release_writer.set()
            self.assertIn("suites", dashboard.result(timeout=10))
            self.assertIsNotNone(adapter.result(timeout=10))
            writer.result(timeout=10)

    def test_dashboard_registers_h3_adapters_on_one_registry_connection(self):
        original_open_registry = model_test_registry.open_registry
        open_count = 0

        def counted_open_registry(root: Path):
            nonlocal open_count
            open_count += 1
            return original_open_registry(root)

        with patch.object(
            model_test_registry,
            "open_registry",
            side_effect=counted_open_registry,
        ):
            dashboard = model_test_registry.dashboard(self.root, self.workflows)

        self.assertIn("adapters", dashboard)
        self.assertEqual(1, open_count)


if __name__ == "__main__":
    unittest.main()
