from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import benchmark_jobs
import evaluation_db
import h3_queue
from job_queue import read_json, update_status
import model_test_assets
import model_test_registry
import workflow_adapter


class BenchmarkJobsTest(unittest.TestCase):
    """Reusable H3 benchmark fixture plus queue-boundary tests."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        workflow = self.workflows / "official.json"
        workflow.write_text(json.dumps({
            "1": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
            "2": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}},
            "3": {
                "class_type": "EmptyVideoLatent",
                "inputs": {"width": 832, "height": 480, "length": 97},
            },
            "4": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output"}},
            "5": {"class_type": "LoadImage", "inputs": {"image": "reference.png"}},
        }), encoding="utf-8")
        self.model_id = model_test_registry.register_model(self.root, {
            "provider": "MiniMax",
            "family": "H3",
            "display_name": "Benchmark H3",
            "version": "1",
        })["model_id"]
        self.workflow_profile_id = model_test_registry.register_workflow(
            self.root,
            self.workflows,
            {
                "model_id": self.model_id,
                "workflow_filename": workflow.name,
                "profile_kind": "official_baseline",
                "name": "Official",
            },
        )["workflow_profile_id"]
        with model_test_registry.open_registry(self.root) as connection:
            self.adapter_id = workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": self.workflow_profile_id,
                "adapter_name": "Official bindings",
                "adapter_version": "1",
                "bindings": {
                    "prompt": {"node_id": "1", "input": "text"},
                    "seed": {"node_id": "2", "input": "noise_seed"},
                    "width": {"node_id": "3", "input": "width"},
                    "height": {"node_id": "3", "input": "height"},
                    "frame_count": {"node_id": "3", "input": "length"},
                    "filename_prefix": {"node_id": "4", "input": "filename_prefix"},
                    "reference_image": {"node_id": "5", "input": "image"},
                },
            })["adapter_id"]
            reference_case = connection.execute(
                """SELECT case_version_id FROM benchmark_case_asset_requirements
                   WHERE case_version_id='benchmark_reference_following_v1'
                     AND role='reference_image'"""
            ).fetchone()[0]
            upload = self.root / "reference.png"
            upload.write_bytes(b"\x89PNG\r\n\x1a\n" + b"benchmark-reference")
            model_test_assets.save_and_link(self.root, connection, {
                "case_version_id": reference_case,
                "role": "reference_image",
                "upload_path": str(upload),
            })
        self.session_id = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.workflow_profile_id,
            "adapter_id": self.adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID,
            "repetitions": 1,
            "resolution": {"width": 832, "height": 480},
        })["session_id"]

    def tearDown(self):
        self.temp.cleanup()

    def queue(self):
        return benchmark_jobs.queue_session(self.root, self.session_id)

    def test_session_registers_only_h3_queue_jobs_with_random_seeds(self):
        result = self.queue()
        self.assertEqual("h3_generation", result["queue_backend"])
        self.assertEqual(39, result["queued_count"])
        self.assertFalse((self.root / "jobs").exists())
        self.assertFalse((self.root / "runtime/batches").exists())
        queue = read_json(
            self.root / "runtime/h3/test_queues" / result["queue_id"] / "queue.json",
            {},
        )
        self.assertEqual(result["job_ids"], queue["job_ids"])
        seeds = []
        for order, job_id in enumerate(result["job_ids"], start=1):
            job_dir = self.root / "runtime/h3/jobs" / job_id
            request = read_json(job_dir / "request.json", {})
            self.assertEqual("h3_model_benchmark", request["job_type"])
            self.assertEqual(result["queue_id"], request["test_queue_id"])
            self.assertEqual(order, request["queue_order"])
            self.assertTrue((job_dir / "workflow_api.json").is_file())
            seeds.append(request["settings"]["seed"])
        self.assertEqual(len(seeds), len(set(seeds)))
        self.assertTrue(all(0 <= seed < 2**63 for seed in seeds))
        with self.assertRaisesRegex(RuntimeError, "이미 H3 테스트 큐"):
            self.queue()

    def test_i2v_session_is_marked_and_grouped_as_i2v_in_h3_queue(self):
        upload = self.root / "i2v-anchor.png"
        upload.write_bytes(b"\x89PNG\r\n\x1a\n" + b"i2v-anchor")
        with model_test_registry.open_registry(self.root) as connection:
            case_ids = [row[0] for row in connection.execute(
                """SELECT s.case_version_id FROM suite_cases s
                     WHERE s.suite_id=? AND s.enabled=1 ORDER BY s.ordering""",
                (model_test_registry.I2V_SUITE_ID,),
            )]
            for case_version_id in case_ids:
                model_test_assets.save_and_link(self.root, connection, {
                    "case_version_id": case_version_id,
                    "role": "reference_image",
                    "upload_path": str(upload),
                })
        session_id = model_test_registry.create_session(self.root, {
            "model_id": self.model_id,
            "workflow_profile_id": self.workflow_profile_id,
            "adapter_id": self.adapter_id,
            "suite_id": model_test_registry.I2V_SUITE_ID,
            "repetitions": 1,
            "resolution": {"width": 832, "height": 480},
        })["session_id"]
        result = benchmark_jobs.queue_session(self.root, session_id)
        queue = read_json(
            self.root / "runtime/h3/test_queues" / result["queue_id"] / "queue.json",
            {},
        )
        self.assertEqual("i2v", queue["generation_mode"])
        self.assertEqual("i2v_model_test", queue["queue_kind"])
        for job_id in result["job_ids"]:
            request = read_json(self.root / "runtime/h3/jobs" / job_id / "request.json", {})
            self.assertEqual("h3_model_benchmark", request["job_type"])
            self.assertEqual("i2v", request["generation_mode"])

    def test_result_recording_completes_session_without_automatic_review(self):
        result = self.queue()
        for job_id in result["job_ids"]:
            job_dir = h3_queue.resolve_job_dir(self.root, job_id)
            request = read_json(job_dir / "request.json", {})
            update_status(job_dir, "completed")
            benchmark_jobs.record_result(
                self.root,
                request,
                status="completed",
                generation_seconds=1.25,
                peak_gpu_memory_bytes=1024,
                peak_system_memory_bytes=2048,
            )
        with model_test_registry.open_registry(self.root) as connection:
            session = connection.execute(
                "SELECT status FROM test_sessions WHERE session_id=?",
                (self.session_id,),
            ).fetchone()
            self.assertEqual("completed", session["status"])
            self.assertEqual(
                39,
                connection.execute(
                    "SELECT COUNT(*) FROM generation_runs WHERE status='completed'"
                ).fetchone()[0],
            )
        self.assertFalse((self.root / "runtime/model_test_review_queue").exists())

    def test_active_session_deletion_is_rejected(self):
        result = self.queue()
        with self.assertRaisesRegex(RuntimeError, "실행 중이거나 큐 대기 중"):
            model_test_registry.delete_session(self.root, self.session_id)
        self.assertTrue(all(
            (self.root / "runtime/h3/jobs" / job_id).is_dir()
            for job_id in result["job_ids"]
        ))

    def test_completed_session_deletion_removes_h3_artifacts(self):
        result = self.queue()
        output = self.root / "runtime/h3/outputs/test.mp4"
        output.parent.mkdir(parents=True)
        output.write_bytes(b"video")
        for index, job_id in enumerate(result["job_ids"]):
            job_dir = h3_queue.resolve_job_dir(self.root, job_id)
            request = read_json(job_dir / "request.json", {})
            update_status(job_dir, "completed")
            benchmark_jobs.record_result(
                self.root,
                request,
                status="completed",
                output_path=str(output) if index == 0 else None,
            )
        deleted = model_test_registry.delete_session(self.root, self.session_id)
        self.assertEqual(39, deleted["deleted_job_count"])
        self.assertEqual(1, deleted["deleted_h3_queue_count"])
        self.assertEqual(1, deleted["deleted_output_count"])
        self.assertFalse(output.exists())
        with model_test_registry.open_registry(self.root) as connection:
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM test_sessions WHERE session_id=?", (self.session_id,)
            ).fetchone())

    def test_schema_v10_has_no_batch_link_table(self):
        with model_test_registry.open_registry(self.root) as connection:
            self.assertEqual(
                str(evaluation_db.SCHEMA_VERSION),
                connection.execute(
                    "SELECT value FROM schema_metadata WHERE key='schema_version'"
                ).fetchone()[0],
            )
            self.assertIsNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_session_batches'"
            ).fetchone())


if __name__ == "__main__":
    unittest.main()
