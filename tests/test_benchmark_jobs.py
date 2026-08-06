from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import batch_manager
import benchmark_jobs
import benchmark_worker
import evaluation_db
import model_test_assets
import model_test_registry
import workflow_adapter
from job_queue import find_next_queued_job, read_json, update_status


class FakeComfyClient:
    def __init__(self, fail_queue: bool = False):
        self.fail_queue = fail_queue
        self.queued_workflow = None
        self.prompt_id = "fake-prompt"

    def upload_input(self, *, filename, content, subfolder, overwrite=True):
        return {"name": filename, "subfolder": subfolder, "type": "input"}

    def queue_prompt(self, workflow):
        if self.fail_queue:
            raise RuntimeError("synthetic queue failure")
        self.queued_workflow = workflow
        return {"prompt_id": self.prompt_id}

    def get_history(self, prompt_id):
        return {prompt_id: {"outputs": {}}}

    def _raise_on_execution_error(self, item):
        return None

    def extract_output_files(self, history, prompt_id):
        return [{"filename": "benchmark.mp4", "subfolder": "model-tests", "type": "output"}]

    def get_queue(self):
        return {"queue_running": [], "queue_pending": []}


class BenchmarkJobsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        workflow = self.workflows / "official.json"
        workflow.write_text(json.dumps({
            "1": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
            "2": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}},
            "3": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": 512, "height": 288, "length": 97}},
            "4": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output"}},
            "5": {"class_type": "LoadImage", "inputs": {"image": "reference.png"}},
        }), encoding="utf-8")
        model_id = model_test_registry.register_model(self.root, {
            "provider": "Provider", "family": "Family", "display_name": "Benchmark Model", "version": "1"
        })["model_id"]
        profile_id = model_test_registry.register_workflow(self.root, self.workflows, {
            "model_id": model_id,
            "workflow_filename": workflow.name,
            "profile_kind": "official_baseline",
            "name": "Official",
        })["workflow_profile_id"]
        with model_test_registry.open_registry(self.root) as connection:
            adapter_id = workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": profile_id,
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
            "model_id": model_id,
            "workflow_profile_id": profile_id,
            "adapter_id": adapter_id,
            "suite_id": model_test_registry.DEFAULT_SUITE_ID,
            "repetitions": 1,
            "resolution": {"width": 960, "height": 544},
        })["session_id"]

    def tearDown(self):
        self.temp.cleanup()

    def queue(self):
        return benchmark_jobs.queue_session(self.root, self.session_id)

    def test_ready_session_registers_independent_batch_and_runs(self):
        result = self.queue()
        self.assertEqual(result["queued_count"], 39)
        batch = read_json(self.root / "runtime/batches" / result["batch_id"] / "batch.json", {})
        self.assertEqual(batch["batch_mode"], "model_benchmark")
        self.assertTrue(batch["registration_closed"])
        self.assertEqual(len(batch["benchmark_job_ids"]), 39)
        self.assertEqual(batch["generation_job_ids"], batch["benchmark_job_ids"])
        self.assertTrue(batch["automation"]["auto_review"])
        orders = []
        for job_id in result["job_ids"]:
            request = read_json(self.root / "jobs" / job_id / "request.json", {})
            self.assertEqual(request["job_type"], "model_benchmark")
            self.assertTrue(request["canonical_prompt"])
            self.assertTrue(request["review_intent_ko"])
            self.assertEqual(request["resolution"], {"width": 960, "height": 544})
            workflow = read_json(self.root / "jobs" / job_id / "selected_workflow_api.json", {})
            self.assertEqual(workflow["3"]["inputs"]["width"], 960)
            self.assertEqual(workflow["3"]["inputs"]["height"], 544)
            self.assertIn("required_events", request["benchmark_contract"])
            self.assertTrue((self.root / "jobs" / job_id / "selected_workflow_api.json").is_file())
            orders.append(request["queue_order"])
        self.assertEqual(orders, list(range(1, 40)))
        self.assertEqual(find_next_queued_job(self.root / "jobs").name, result["job_ids"][0])
        with model_test_registry.open_registry(self.root) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM generation_runs").fetchone()[0], 39)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM test_session_runs").fetchone()[0], 39)
            self.assertEqual(connection.execute("SELECT status FROM test_sessions WHERE session_id=?", (self.session_id,)).fetchone()[0], "queued")
            self.assertEqual(connection.execute("SELECT batch_id FROM test_session_batches WHERE session_id=?", (self.session_id,)).fetchone()[0], result["batch_id"])
        with self.assertRaisesRegex(RuntimeError, "이미 전용 큐"):
            self.queue()

    def test_benchmark_batch_advances_to_qwen_review_pipeline(self):
        result = self.queue()
        for job_id in result["job_ids"]:
            update_status(self.root / "jobs" / job_id, "completed")
        batch = batch_manager.load_batch(self.root, result["batch_id"])
        completed = batch_manager.mark_batch_generation_complete(self.root, batch)
        self.assertEqual(completed["status"], "ready_for_review_preparation")
        self.assertEqual(completed["next_stage"], "video_review")
        self.assertEqual(completed["benchmark_completed_count"], 39)
        self.assertEqual(completed["benchmark_failed_count"], 0)
        self.assertEqual(completed["review_job_ids"], result["job_ids"])

    def test_case_specific_durations_compile_into_workflow_frames(self):
        expected = {
            "benchmark_two_subject_separation_v1": (6, 145),
            "benchmark_ground_contact_v1": (8, 193),
            "benchmark_action_level_5_v1": (10, 241),
            "benchmark_vfx_impact_v1": (7, 169),
            "benchmark_offscreen_return_v1": (9, 217),
            "benchmark_dialogue_action_v1": (10, 241),
            "benchmark_scenario_level_1_v1": (8, 193),
            "benchmark_scenario_level_3_v1": (12, 289),
            "benchmark_scenario_level_4_v1": (16, 385),
            "benchmark_scenario_level_5_v1": (20, 481),
        }
        with model_test_registry.open_registry(self.root) as connection:
            session = connection.execute(
                "SELECT * FROM test_sessions WHERE session_id=?", (self.session_id,)
            ).fetchone()
            for case_version_id, (seconds, frames) in expected.items():
                compiled = workflow_adapter.compile_case(connection, session, case_version_id)
                self.assertEqual(compiled["status"], "ready")
                self.assertEqual(compiled["settings"]["duration_seconds"], seconds)
                self.assertEqual(compiled["settings"]["frame_count"], frames)
                self.assertEqual(compiled["compiled_workflow"]["3"]["inputs"]["length"], frames)

    def test_long_continuity_case_compiles_to_twenty_seconds(self):
        with model_test_registry.open_registry(self.root) as connection:
            session = connection.execute("SELECT * FROM test_sessions WHERE session_id=?", (self.session_id,)).fetchone()
            compiled = workflow_adapter.compile_case(connection, session, "benchmark_long_temporal_v1")
        self.assertEqual(compiled["status"], "ready")
        self.assertEqual(compiled["settings"]["frame_count"], 481)
        self.assertEqual(compiled["compiled_workflow"]["3"]["inputs"]["length"], 481)

    def test_active_session_deletion_is_rejected_without_removing_files(self):
        result = self.queue()
        job_dirs = [self.root / "jobs" / job_id for job_id in result["job_ids"]]
        batch_dir = self.root / "runtime" / "batches" / result["batch_id"]
        with self.assertRaisesRegex(RuntimeError, "실행 중이거나 큐 대기 중"):
            model_test_registry.delete_session(self.root, self.session_id)
        self.assertTrue(all(path.is_dir() for path in job_dirs))
        self.assertTrue(batch_dir.is_dir())
        with model_test_registry.open_registry(self.root) as connection:
            self.assertIsNotNone(connection.execute(
                "SELECT 1 FROM test_sessions WHERE session_id=?", (self.session_id,)
            ).fetchone())

    def test_completed_session_deletion_removes_local_artifacts(self):
        result = self.queue()
        job_ids = result["job_ids"]
        batch_dir = self.root / "runtime" / "batches" / result["batch_id"]
        output_dir = self.root / "comfy-output" / "model-tests"
        output_dir.mkdir(parents=True)
        output_file = output_dir / "benchmark.mp4"
        output_file.write_bytes(b"video")
        with model_test_registry.open_registry(self.root) as connection:
            run_id = connection.execute(
                "SELECT run_id FROM test_session_runs WHERE session_id=? ORDER BY run_id LIMIT 1",
                (self.session_id,),
            ).fetchone()[0]
            connection.execute(
                "UPDATE generation_runs SET status='completed',output_path=? WHERE run_id=?",
                (str(output_file), run_id),
            )
            connection.execute("UPDATE generation_runs SET status='completed'")
            connection.execute("UPDATE test_sessions SET status='completed' WHERE session_id=?", (self.session_id,))
            connection.commit()
        previous_output_dir = os.environ.get("COMFY_OUTPUT_DIR")
        os.environ["COMFY_OUTPUT_DIR"] = str(self.root / "comfy-output")
        try:
            deleted = model_test_registry.delete_session(self.root, self.session_id)
        finally:
            if previous_output_dir is None:
                os.environ.pop("COMFY_OUTPUT_DIR", None)
            else:
                os.environ["COMFY_OUTPUT_DIR"] = previous_output_dir
        self.assertEqual(deleted["deleted_run_count"], len(job_ids))
        self.assertEqual(deleted["deleted_job_count"], len(job_ids))
        self.assertEqual(deleted["deleted_output_count"], 1)
        self.assertEqual(deleted["deleted_batch_count"], 1)
        self.assertFalse(deleted["files_preserved"])
        self.assertTrue(all(not (self.root / "jobs" / job_id).exists() for job_id in job_ids))
        self.assertFalse(batch_dir.exists())
        self.assertFalse(output_file.exists())
        with model_test_registry.open_registry(self.root) as connection:
            self.assertIsNone(connection.execute("SELECT 1 FROM test_sessions WHERE session_id=?", (self.session_id,)).fetchone())
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM generation_runs").fetchone()[0], 0)

    def test_worker_completion_records_metrics_without_real_comfy(self):
        result = self.queue()
        job_dir = self.root / "jobs" / result["job_ids"][0]
        client = FakeComfyClient()
        benchmark_worker.process_benchmark_job(
            job_dir,
            ensure_client=lambda request: client,
            queue_position=lambda queue, prompt_id: ("running", 0),
            memory_sampler=lambda: {"gpu": 1234, "system": 5678},
            poll_seconds=0,
            timeout_seconds=10,
        )
        status = read_json(job_dir / "status.json", {})
        self.assertEqual(status["status"], "completed")
        with model_test_registry.open_registry(self.root) as connection:
            row = connection.execute(
                "SELECT status,generation_seconds,peak_gpu_memory_bytes,peak_system_memory_bytes FROM generation_runs WHERE job_id=?",
                (job_dir.name,),
            ).fetchone()
        self.assertEqual(row["status"], "completed")
        self.assertIsNotNone(row["generation_seconds"])
        self.assertEqual(row["peak_gpu_memory_bytes"], 1234)
        self.assertEqual(row["peak_system_memory_bytes"], 5678)

    def test_worker_failure_is_recorded(self):
        result = self.queue()
        job_dir = self.root / "jobs" / result["job_ids"][0]
        with self.assertRaisesRegex(RuntimeError, "synthetic queue failure"):
            benchmark_worker.process_benchmark_job(
                job_dir,
                ensure_client=lambda request: FakeComfyClient(fail_queue=True),
                queue_position=lambda queue, prompt_id: ("running", 0),
                memory_sampler=lambda: {"gpu": None, "system": None},
                poll_seconds=0,
                timeout_seconds=10,
            )
        with model_test_registry.open_registry(self.root) as connection:
            row = connection.execute(
                "SELECT status,settings_json FROM generation_runs WHERE job_id=?", (job_dir.name,)
            ).fetchone()
        self.assertEqual(row["status"], "failed")
        self.assertIn("synthetic queue failure", json.loads(row["settings_json"])["error"])

    def test_schema_v5_contains_session_batch_link(self):
        with model_test_registry.open_registry(self.root) as connection:
            self.assertEqual(
                connection.execute("SELECT value FROM schema_metadata WHERE key='schema_version'").fetchone()[0],
                str(evaluation_db.SCHEMA_VERSION),
            )
            self.assertIsNotNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_session_batches'"
            ).fetchone())


    def test_completed_session_can_queue_qwen_review_again(self):
        result = self.queue()
        request = read_json(self.root / "jobs" / result["job_ids"][0] / "request.json", {})
        benchmark_jobs.record_result(self.root, request, status="completed")
        queued = benchmark_jobs.queue_ai_review(self.root, self.session_id)
        self.assertEqual(queued["queued_count"], 1)
        self.assertFalse(queued["already_queued"])
        batch = batch_manager.load_batch(self.root, result["batch_id"])
        self.assertEqual(batch["status"], "ready_for_review_preparation")
        self.assertEqual(batch["review_job_ids"], [result["job_ids"][0]])
        self.assertEqual(batch["pipeline_version"], "1.8.0")
        with model_test_registry.open_registry(self.root) as connection:
            status = connection.execute(
                "SELECT status FROM test_sessions WHERE session_id=?", (self.session_id,)
            ).fetchone()[0]
        self.assertEqual(status, "ai_review_queued")


if __name__ == "__main__":
    unittest.main()
