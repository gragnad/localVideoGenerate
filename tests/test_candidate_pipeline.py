from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import batch_manager
import ui_backend
from job_queue import atomic_write_json, update_status
import worker


class CandidatePipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.jobs = self.root / "jobs"
        self.jobs.mkdir()
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        self.output = self.root / "comfy-output"
        self.output.mkdir()
        self.input = self.root / "comfy-input"
        self.input.mkdir()
        self.image = self.root / "source.png"
        self.image.write_bytes(b"fake-image")
        self.cr = self.workflows / "director-api.json"
        atomic_write_json(self.cr, {"1": {"class_type": "LTXDirector", "inputs": {}}})
        self.md = self.workflows / "retake-api.json"
        atomic_write_json(
            self.md,
            {
                "1": {"class_type": "LTXDirector", "inputs": {}},
                "2": {"class_type": "RandomNoise", "inputs": {}},
                "3": {"class_type": "SaveVideo", "inputs": {}},
            },
        )

        self.originals = {
            "ROOT": ui_backend.ROOT,
            "JOBS": ui_backend.JOBS,
            "WF_DIR": ui_backend.WF_DIR,
            "CR": ui_backend.CR,
            "MD": ui_backend.MD,
            "CANDIDATE_SETS": ui_backend.CANDIDATE_SETS,
            "COMPOSITIONS": ui_backend.COMPOSITIONS,
            "COMFY_OUTPUT": ui_backend.COMFY_OUTPUT,
            "COMFY_INPUT": ui_backend.COMFY_INPUT,
        }
        ui_backend.ROOT = self.root
        ui_backend.JOBS = self.jobs
        ui_backend.WF_DIR = self.workflows
        ui_backend.CR = self.cr
        ui_backend.MD = self.md
        ui_backend.CANDIDATE_SETS = self.root / "runtime/candidate_sets"
        ui_backend.COMPOSITIONS = self.root / "runtime/compositions"
        ui_backend.COMFY_OUTPUT = self.output
        ui_backend.COMFY_INPUT = self.input

    def tearDown(self):
        for key, value in self.originals.items():
            setattr(ui_backend, key, value)
        self.temp.cleanup()

    def candidate_payload(self):
        return {
            "candidate_count": 3,
            "job_name": "candidate",
            "fps": 24,
            "seed": 100,
            "width": 1536,
            "height": 864,
            "global_prompt": "same character",
            "segments": [
                {
                    "upload_path": str(self.image),
                    "original_name": "source.png",
                    "prompt": "character walks",
                    "seconds": 5,
                    "order": 1,
                }
            ],
        }

    def complete_candidate_set(self, candidate_set):
        video_dir = self.output / "video"
        video_dir.mkdir(exist_ok=True)
        for job_id in candidate_set["candidate_job_ids"]:
            update_status(self.jobs / job_id, "completed", stage="완료", progress=1.0)
            manifest = json.loads((self.jobs / job_id / "manifest.json").read_text())
            video_path = video_dir / f"{job_id}.mp4"
            video_path.write_bytes(b"fake-video")
            manifest.update(
                status="completed",
                outputs=[{"filename": video_path.name, "subfolder": "video", "type": "output"}],
            )
            atomic_write_json(self.jobs / job_id / "manifest.json", manifest)

    def test_create_action_defaults_to_1536x864(self):
        with patch("ui_backend.probe_video", return_value={"duration_seconds": 5.0, "width": 1536, "height": 864, "fps": 24}):
            created = ui_backend.create_action(
                {
                    "job_name": "scene",
                    "fps": 24,
                    "seed": 1,
                    "global_prompt": "test",
                    "segments": [
                        {
                            "upload_path": str(self.image),
                            "original_name": "source.png",
                            "prompt": "walk",
                            "seconds": 5,
                            "order": 1,
                        }
                    ],
                }
            )
        request = json.loads((self.jobs / created["job_id"] / "request.json").read_text())
        self.assertEqual(request["resolution"], {"width": 1536, "height": 864, "label": "1536 × 864"})

    @patch("ui_backend.probe_video", return_value={"duration_seconds": 5.0, "width": 1536, "height": 864, "fps": 24})
    def test_candidate_selection_does_not_create_upscale(self, _probe):
        candidate_set = ui_backend.create_candidates_action(self.candidate_payload())
        self.complete_candidate_set(candidate_set)
        batch = batch_manager.load_batch(self.root, candidate_set["batch_id"])
        batch_manager.mark_batch_generation_complete(self.root, batch)

        selected_id = candidate_set["candidate_job_ids"][1]
        selected = ui_backend.select_candidate_action(
            {"candidate_set_id": candidate_set["candidate_set_id"], "job_id": selected_id}
        )
        self.assertEqual(selected["selected_job_id"], selected_id)
        self.assertEqual(selected["status"], "selected")
        self.assertIsNone(selected.get("final_review_batch_id"))
        self.assertNotIn("queued_upscale_job_id", selected)
        self.assertEqual(len(list(self.jobs.iterdir())), 3)

    @patch("ui_backend.probe_video", return_value={"duration_seconds": 5.0, "width": 1536, "height": 864, "fps": 24})
    def test_register_candidate_final_review_uses_selected_job(self, _probe):
        candidate_set = ui_backend.create_candidates_action(self.candidate_payload())
        self.complete_candidate_set(candidate_set)
        batch = batch_manager.load_batch(self.root, candidate_set["batch_id"])
        batch_manager.mark_batch_generation_complete(self.root, batch)
        selected_id = candidate_set["candidate_job_ids"][0]
        ui_backend.select_candidate_action(
            {"candidate_set_id": candidate_set["candidate_set_id"], "job_id": selected_id}
        )

        registered = ui_backend.register_candidate_final_review_action(
            {"candidate_set_id": candidate_set["candidate_set_id"]}
        )
        self.assertEqual(registered["status"], "final_review_queued")
        self.assertEqual(registered["review_job_id"], selected_id)

        review_batch = batch_manager.load_batch(self.root, registered["batch_id"])
        self.assertEqual(review_batch["batch_mode"], "final_review")
        self.assertEqual(review_batch["status"], "ready_for_review_preparation")
        self.assertEqual(review_batch["review_job_ids"], [selected_id])

        payload = ui_backend.load_candidate_set(candidate_set["candidate_set_id"])
        self.assertEqual(payload["status"], "final_review_queued")
        self.assertEqual(payload["final_review_batch_id"], registered["batch_id"])

    @patch("ui_backend.probe_video", return_value={"duration_seconds": 8.0, "width": 1536, "height": 864, "fps": 24})
    def test_register_composition_final_review_uses_assemble_job(self, _probe):
        candidate_set = ui_backend.create_candidates_action(self.candidate_payload())
        self.complete_candidate_set(candidate_set)
        clip_job_id = candidate_set["candidate_job_ids"][0]
        composition = ui_backend.create_composition_action(
            {
                "name": "assembly_test",
                "clips": [
                    {
                        "source_job_id": clip_job_id,
                        "start_seconds": 0,
                        "end_seconds": 5,
                        "order": 1,
                    },
                    {
                        "source_job_id": candidate_set["candidate_job_ids"][1],
                        "start_seconds": 0,
                        "end_seconds": 3,
                        "order": 2,
                    },
                ],
            }
        )
        assembled = ui_backend.assemble_composition_action(
            {"composition_id": composition["composition_id"]}
        )
        assemble_job_id = assembled["assemble_job_id"]
        update_status(self.jobs / assemble_job_id, "completed", stage="완료", progress=1.0)
        artifacts = self.jobs / assemble_job_id / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        output = artifacts / "assembled_master.mp4"
        output.write_bytes(b"fake-assembled")
        manifest = json.loads((self.jobs / assemble_job_id / "manifest.json").read_text())
        manifest.update(status="completed", review_video_local_path=str(output), outputs=[])
        atomic_write_json(self.jobs / assemble_job_id / "manifest.json", manifest)
        payload = ui_backend.load_composition(composition["composition_id"])
        payload["status"] = "assembled"
        payload["assembled_video_path"] = str(output)
        ui_backend.save_composition(payload)

        registered = ui_backend.register_composition_final_review_action(
            {"composition_id": composition["composition_id"]}
        )
        self.assertEqual(registered["review_job_id"], assemble_job_id)
        review_batch = batch_manager.load_batch(self.root, registered["batch_id"])
        self.assertEqual(review_batch["batch_mode"], "final_review")
        self.assertEqual(review_batch["review_job_ids"], [assemble_job_id])

    def test_delete_candidate_set_removes_jobs_and_files(self):
        candidate_set = ui_backend.create_candidates_action(self.candidate_payload())
        self.complete_candidate_set(candidate_set)
        batch = batch_manager.load_batch(self.root, candidate_set["batch_id"])
        batch_manager.mark_batch_generation_complete(self.root, batch)

        deleted = ui_backend.delete_candidate_set_action(
            {"candidate_set_id": candidate_set["candidate_set_id"]}
        )
        self.assertEqual(len(deleted["deleted_job_ids"]), 3)
        for job_id in candidate_set["candidate_job_ids"]:
            self.assertFalse((self.jobs / job_id).exists())

    def test_delete_candidate_set_blocks_active_jobs(self):
        candidate_set = ui_backend.create_candidates_action(self.candidate_payload())
        update_status(
            self.jobs / candidate_set["candidate_job_ids"][0],
            "running",
            stage="ComfyUI 실행 중",
        )
        with self.assertRaisesRegex(RuntimeError, "실행 중인 작업"):
            ui_backend.delete_candidate_set_action(
                {"candidate_set_id": candidate_set["candidate_set_id"]}
            )

    @patch("ui_backend.probe_video", return_value={"duration_seconds": 5.0, "width": 1536, "height": 864, "fps": 24})
    def test_candidate_gate_blocks_selection_until_all_batches_complete(self, _probe):
        first = ui_backend.create_candidates_action(self.candidate_payload())
        second_payload = self.candidate_payload()
        second_payload["seed"] = 200
        second = ui_backend.create_candidates_action(second_payload)
        self.complete_candidate_set(first)
        with self.assertRaisesRegex(RuntimeError, "모두 끝난 뒤"):
            ui_backend.select_candidate_action(
                {
                    "candidate_set_id": first["candidate_set_id"],
                    "job_id": first["candidate_job_ids"][0],
                }
            )

    @patch("ui_backend.probe_video", return_value={"duration_seconds": 5.0, "width": 1536, "height": 864, "fps": 24})
    def test_final_review_batch_advances_in_fifo_order(self, _probe):
        first = ui_backend.create_candidates_action(self.candidate_payload())
        second_payload = self.candidate_payload()
        second_payload["seed"] = 200
        second = ui_backend.create_candidates_action(second_payload)
        self.complete_candidate_set(first)
        self.complete_candidate_set(second)
        batch_manager.mark_batch_generation_complete(
            self.root, batch_manager.load_batch(self.root, first["batch_id"])
        )
        batch_manager.mark_batch_generation_complete(
            self.root, batch_manager.load_batch(self.root, second["batch_id"])
        )
        ui_backend.select_candidate_action(
            {
                "candidate_set_id": first["candidate_set_id"],
                "job_id": first["candidate_job_ids"][0],
            }
        )
        ui_backend.select_candidate_action(
            {
                "candidate_set_id": second["candidate_set_id"],
                "job_id": second["candidate_job_ids"][0],
            }
        )
        first_registered = ui_backend.register_candidate_final_review_action(
            {"candidate_set_id": first["candidate_set_id"]}
        )
        second_registered = ui_backend.register_candidate_final_review_action(
            {"candidate_set_id": second["candidate_set_id"]}
        )
        self.assertNotEqual(first_registered["batch_id"], second_registered["batch_id"])

        with patch.object(worker, "ENGINE_ROOT", self.root), patch.object(worker, "JOBS_ROOT", self.jobs):
            with patch.object(worker, "prepare_direct_video_review_batch", side_effect=lambda batch: batch):
                review_batch = worker.advance_review_batches()
        self.assertEqual(review_batch["batch_id"], first_registered["batch_id"])

    def test_oldest_candidate_batch_waits_grace_before_next_batch(self):
        first = ui_backend.create_candidates_action(self.candidate_payload())
        second = ui_backend.create_candidates_action(self.candidate_payload())
        self.complete_candidate_set(first)
        with patch.object(worker, "ENGINE_ROOT", self.root), patch.object(worker, "JOBS_ROOT", self.jobs):
            with patch.object(worker, "get_comfy_queue_state", return_value=(True, 0, 0, None)):
                waiting = worker.maybe_finalize_open_batch()
        self.assertEqual(waiting["batch_id"], first["batch_id"])
        self.assertEqual(waiting["stage"], "batch_idle_grace")
        batch_manager.update_batch(self.root, first["batch_id"], idle_since_epoch=0)
        with patch.object(worker, "ENGINE_ROOT", self.root), patch.object(worker, "JOBS_ROOT", self.jobs):
            with patch.object(worker, "get_comfy_queue_state", return_value=(True, 0, 0, None)):
                completed = worker.maybe_finalize_open_batch()
        self.assertEqual(completed["status"], "awaiting_candidate_selection")
        self.assertEqual(batch_manager.load_batch(self.root, second["batch_id"])["status"], "open")

    @patch("ui_backend.probe_video", return_value={"duration_seconds": 12.0, "width": 1536, "height": 864, "fps": 24})
    def test_manual_composition_upload_without_enhance(self, _probe):
        upload = self.root / "edited_master.mp4"
        upload.write_bytes(b"fake-edited-video")
        imported = ui_backend.import_composition_video_action(
            {
                "upload_path": str(upload),
                "name": "manual_edit",
            }
        )
        self.assertEqual(imported["duration_seconds"], 12.0)
        composition = ui_backend.load_composition(imported["composition_id"])
        self.assertEqual(composition["status"], "assembled")
        self.assertEqual(composition["assembly_source"], "manual_upload")
        self.assertNotIn("upscale_job_id", composition)


if __name__ == "__main__":
    unittest.main()
