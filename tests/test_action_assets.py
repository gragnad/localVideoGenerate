from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import action_assets
import h3_queue
import h3_worker
import model_test_registry
import workflow_adapter
from job_queue import atomic_write_json, read_json, update_status


class ActionAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "runtime/ui-uploads").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def make_video(
        self,
        path: Path,
        *,
        width: int = 320,
        height: int = 180,
        duration: float = 2.2,
        audio: bool = True,
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i",
            f"color=c=blue:s={width}x{height}:r=24:d={duration}",
        ]
        if audio:
            command += [
                "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
                "-shortest",
            ]
        command += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
        if audio:
            command += ["-c:a", "aac"]
        command.append(str(path))
        subprocess.run(command, check=True, capture_output=True, timeout=60)
        return path

    @staticmethod
    def metadata(**updates):
        payload = {
            "title": "옆으로 피하기",
            "description": "준비 자세에서 오른쪽으로 회피하고 균형을 회복한다.",
            "category": "evasion",
            "action_type": "옆으로 피하기",
            "participant_count": 1,
            "participant_a": {
                "role": "evader",
                "body_type": "humanoid",
                "description": "회피자",
            },
            "handedness": "right",
            "weapon_type": "sword",
            "attack_start_direction": "left",
            "attack_end_direction": "right",
            "screen_direction": "left_to_right",
            "timing": {
                "preparation": 0.0,
                "execution": 0.5,
                "contact": 1.0,
                "recoil": 1.5,
            },
            "camera": {"angle": "eye_level", "framing": "full_body"},
            "contact_type": "miss",
            "source_type": "direct_upload",
            "commercial_use_confirmed": True,
            "ai_reference_use_confirmed": True,
        }
        payload.update(updates)
        return payload

    def test_external_registration_preserves_original_and_makes_silent_h3_copy(self):
        source = self.make_video(self.root / "runtime/ui-uploads/incoming/action.mp4")
        original_bytes = source.read_bytes()
        asset = action_assets.register_external(
            self.root,
            self.metadata(upload_path=str(source), original_name="owned-action.mp4"),
        )

        self.assertEqual("motion_only", asset["reference_role"])
        self.assertEqual("available", asset["availability_state"])
        self.assertTrue(asset["h3_usable"])
        self.assertEqual(original_bytes, Path(asset["original_file"]).read_bytes())
        self.assertEqual(hashlib.sha256(original_bytes).hexdigest(), asset["original_sha256"])
        self.assertEqual(1024, asset["h3_media"]["width"])
        self.assertEqual(576, asset["h3_media"]["height"])
        self.assertAlmostEqual(24, asset["h3_media"]["fps"], places=1)
        self.assertEqual("h264", asset["h3_media"]["codec"])
        self.assertTrue(asset["original_media"]["has_audio"])
        self.assertFalse(asset["h3_media"]["has_audio"])
        self.assertEqual(
            Path(asset["h3_input_file"]),
            action_assets.media_path(self.root, asset["action_asset_id"]),
        )

        with self.assertRaisesRegex(ValueError, "이미 등록"):
            action_assets.register_external(
                self.root,
                self.metadata(upload_path=str(source), title="중복"),
            )

    def test_external_license_requires_explicit_rights_review_and_can_be_archived(self):
        source = self.make_video(self.root / "runtime/ui-uploads/stock.mp4", audio=False)
        asset = action_assets.register_external(
            self.root,
            self.metadata(
                upload_path=str(source),
                source_type="external_licensed",
                source_url="https://stock.example/action",
                creator="Creator",
                license_name="Stock License",
                license_evidence="receipt-42",
            ),
        )
        self.assertEqual("rights_review_required", asset["rights_state"])
        self.assertEqual("rights_review_required", asset["availability_state"])
        self.assertFalse(action_assets.get_asset(self.root, asset["action_asset_id"])["h3_usable"])

        updated = action_assets.update_asset(self.root, asset["action_asset_id"], {
            "rights_state": "confirmed",
            "availability_state": "available",
            "commercial_use_confirmed": True,
            "ai_reference_use_confirmed": True,
        })
        self.assertTrue(updated["h3_usable"])
        archived = action_assets.update_asset(
            self.root,
            asset["action_asset_id"],
            {"archived": True, "active": False},
        )
        self.assertFalse(archived["h3_usable"])
        with self.assertRaisesRegex(ValueError, "현재 H3"):
            action_assets.get_asset(
                self.root, asset["action_asset_id"], require_usable=True
            )

    def test_blender_video_registration_records_provenance_and_accepts_avi(self):
        source = self.make_video(
            self.root / "runtime/ui-uploads/blender/lua-harpoon.avi",
            audio=False,
        )
        asset = action_assets.register_external(
            self.root,
            self.metadata(
                upload_path=str(source),
                source_type="blender_render",
                original_name="lua-harpoon.avi",
                blender_source={
                    "project_file": "../lua_actions_v1.blend",
                    "scene_name": "LUA_ACTION_STAGE",
                    "action_name": "Lua_Harpoon_Swing",
                    "blender_version": "4.0.2",
                    "render_engine": "EEVEE",
                },
            ),
        )

        self.assertEqual("blender_render", asset["source_type"])
        self.assertEqual("blender_video_upload", asset["source_registration"])
        self.assertEqual("lua_actions_v1.blend", asset["blender_source"]["project_file"])
        self.assertEqual("LUA_ACTION_STAGE", asset["blender_source"]["scene_name"])
        self.assertEqual("Lua_Harpoon_Swing", asset["blender_source"]["action_name"])
        self.assertEqual("4.0.2", asset["blender_source"]["blender_version"])
        self.assertEqual("EEVEE", asset["blender_source"]["render_engine"])
        self.assertEqual(".avi", Path(asset["original_file"]).suffix)
        self.assertEqual("h264", asset["h3_media"]["codec"])
        self.assertFalse(asset["h3_media"]["has_audio"])
        self.assertIn(
            "blender_render",
            action_assets.list_assets(self.root)["presets"]["source_types"],
        )

    def test_external_registration_blocks_path_traversal_extension_and_corruption(self):
        outside = self.make_video(self.root / "outside.mp4", audio=False)
        with self.assertRaisesRegex(ValueError, "임시 영역 밖"):
            action_assets.register_external(
                self.root, self.metadata(upload_path=str(outside))
            )
        wrong = self.root / "runtime/ui-uploads/action.txt"
        wrong.write_bytes(outside.read_bytes())
        with self.assertRaisesRegex(ValueError, "MP4"):
            action_assets.register_external(
                self.root, self.metadata(upload_path=str(wrong))
            )
        corrupt = self.root / "runtime/ui-uploads/corrupt.mp4"
        corrupt.write_bytes(b"not a video")
        with self.assertRaisesRegex(ValueError, "손상"):
            action_assets.register_external(
                self.root, self.metadata(upload_path=str(corrupt))
            )
        with self.assertRaises(ValueError):
            action_assets.get_asset(self.root, "../outside")

    def _write_rerender_job(
        self,
        job_id: str,
        *,
        project_kind: str = "action_asset_project",
        status: str = "completed",
        width: int = 1024,
        height: int = 576,
    ) -> Path:
        project = self.root / "prompt_projects/action_project"
        project.mkdir(parents=True, exist_ok=True)
        atomic_write_json(project / "manifest.json", {
            "project_kind": project_kind,
            "workflow": "h3_r2v_production",
        })
        video = self.make_video(
            self.root / f"runtime/h3/outputs/{job_id}.mp4",
            width=1024,
            height=576,
            audio=True,
        )
        job = self.root / "runtime/h3/jobs" / job_id
        job.mkdir(parents=True)
        atomic_write_json(job / "request.json", {
            "job_id": job_id,
            "render_purpose": "resolution_rerender",
            "width": width,
            "height": height,
            "source_project_id": "action_project",
            "source_scene_id": "SC01",
            "source_clip_id": "AC01",
            "source_candidate_set_id": "set-source",
            "source_selected_job_id": "job-source",
        })
        update_status(job, status)
        atomic_write_json(job / "manifest.json", {
            "local_video_path": str(video),
            "output_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        })
        return video

    def test_only_completed_action_project_1024_rerender_registers_independently(self):
        original = self._write_rerender_job("rerender-ok")
        asset = action_assets.register_rerender(
            self.root,
            {
                **self.metadata(
                    title="내부 두 명 전투",
                    category="two_participant_combat",
                    action_type="공격-회피",
                    participant_count=2,
                    participant_a={"role": "attacker", "body_type": "humanoid"},
                    participant_b={"role": "evader", "body_type": "tentacle"},
                ),
                "rerender_job_id": "rerender-ok",
            },
        )
        self.assertEqual("internal_generated", asset["source_type"])
        self.assertEqual(2, asset["participant_count"])
        self.assertTrue(asset["original_media"]["has_audio"])
        self.assertFalse(asset["h3_media"]["has_audio"])
        self.assertNotEqual(Path(asset["original_file"]), original)
        self.assertNotEqual(Path(asset["h3_input_file"]), original)

        shutil.rmtree(self.root / "runtime/h3/jobs/rerender-ok")
        shutil.rmtree(self.root / "prompt_projects/action_project")
        original.unlink()
        self.assertTrue(action_assets.media_path(self.root, asset["action_asset_id"]).is_file())

        self._write_rerender_job("rerender-pending", status="running")
        with self.assertRaisesRegex(ValueError, "완료된"):
            action_assets.register_rerender(
                self.root,
                {**self.metadata(), "rerender_job_id": "rerender-pending"},
            )
        self._write_rerender_job("rerender-wrong-size", width=832, height=480)
        with self.assertRaisesRegex(ValueError, "1024×576"):
            action_assets.register_rerender(
                self.root,
                {**self.metadata(), "rerender_job_id": "rerender-wrong-size"},
            )
        self._write_rerender_job("rerender-normal", project_kind="h3_r2v_production")
        with self.assertRaisesRegex(ValueError, "액션 자산 프로젝트"):
            action_assets.register_rerender(
                self.root,
                {**self.metadata(), "rerender_job_id": "rerender-normal"},
            )


class ActionReferenceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        self.workflow = {
            "92": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output"}},
            "129": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}},
            "132": {"class_type": "PrimitiveFloat", "inputs": {"value": 5}},
            "136": {
                "class_type": "MiniMaxH3ReferenceToVideo",
                "inputs": {
                    "ref_images.ref_image_0": ["137", 0],
                    "ref_images.ref_image_1": ["139", 0],
                    "ref_videos.ref_video_0": ["167", 0],
                },
            },
            "137": {"class_type": "LoadImage", "inputs": {"image": "one.png"}},
            "139": {"class_type": "LoadImage", "inputs": {"image": "two.png"}},
            "138": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": "prompt"}},
            "141": {"class_type": "PrimitiveInt", "inputs": {"value": 832}},
            "142": {"class_type": "PrimitiveInt", "inputs": {"value": 480}},
            "167": {
                "class_type": "VHS_LoadVideo",
                "inputs": {
                    "video": "__H3_ACTION_VIDEO_1__",
                    "force_rate": 24,
                    "force_size": "Disabled",
                    "custom_width": 0,
                    "custom_height": 0,
                    "frame_load_cap": 0,
                    "skip_first_frames": 0,
                    "select_every_nth": 1,
                },
            },
        }
        path = self.workflows / "action_api.json"
        path.write_text(json.dumps(self.workflow), encoding="utf-8")
        model_id = model_test_registry.register_model(self.root, {
            "provider": "MiniMax", "family": "H3",
            "display_name": "MiniMax H3", "version": "1",
        })["model_id"]
        profile_id = model_test_registry.register_workflow(
            self.root,
            self.workflows,
            {
                "model_id": model_id,
                "workflow_filename": path.name,
                "profile_kind": "optimized_variant",
                "name": "Action reference",
            },
        )["workflow_profile_id"]
        with model_test_registry.open_registry(self.root) as connection:
            self.adapter_id = workflow_adapter.register_adapter(connection, {
                "workflow_profile_id": profile_id,
                "adapter_name": "motion-only action",
                "adapter_version": "1",
                "bindings": {
                    "prompt": {"node_id": "138", "input": "value"},
                    "seed": {"node_id": "129", "input": "noise_seed"},
                    "width": {"node_id": "141", "input": "value"},
                    "height": {"node_id": "142", "input": "value"},
                    "duration_seconds": {"node_id": "132", "input": "value"},
                    "filename_prefix": {"node_id": "92", "input": "filename_prefix"},
                },
                "multi_reference": {
                    "conditioning_node_id": "136",
                    "input_prefix": "ref_images.ref_image_",
                    "loader_node_ids": ["137", "139"],
                    "loader_template_node_id": "137",
                    "loader_input": "image",
                    "max_slots": 9,
                },
                "action_reference": {
                    "conditioning_node_id": "136",
                    "conditioning_input": "ref_videos.ref_video_0",
                    "loader_node_id": "167",
                    "loader_input": "video",
                },
            })["adapter_id"]

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def values(prompt="Lua follows participant A motion from <Video 1>."):
        return {
            "prompt": prompt,
            "seed": 7,
            "width": 832,
            "height": 480,
            "fps": 24,
            "duration_seconds": 5,
            "filename_prefix": "video/action-test",
        }

    def write_asset(self, *, participant_count: int = 2) -> dict:
        asset_id = "action-test"
        directory = self.root / "runtime/h3/action_assets" / asset_id
        video = directory / "h3/action.mp4"
        video.parent.mkdir(parents=True)
        video.write_bytes(b"immutable action video")
        digest = hashlib.sha256(video.read_bytes()).hexdigest()
        metadata = {
            "action_asset_id": asset_id,
            "title": "공격-회피",
            "reference_role": "motion_only",
            "participant_count": participant_count,
            "participant_a": {"role": "attacker", "body_type": "humanoid"},
            "participant_b": (
                {"role": "evader", "body_type": "tentacle"}
                if participant_count == 2 else None
            ),
            "availability_state": "available",
            "active": True,
            "archived": False,
            "h3_input_file": str(video),
            "sha256": digest,
            "created_at": "2026-09-05T00:00:00+09:00",
        }
        atomic_write_json(directory / "metadata.json", metadata)
        return metadata

    def test_compile_keeps_picture_and_video_namespaces_independent(self):
        compiled, patches, profile = h3_queue._compile_workflow(
            self.root,
            self.adapter_id,
            self.values(),
            2,
            "r2v",
            action_reference_count=1,
        )
        self.assertTrue(profile["supports_action_reference"])
        self.assertEqual(
            [
                {"node_id": "137", "input": "image"},
                {"node_id": "139", "input": "image"},
                {"node_id": "167", "input": "video", "media_type": "video", "video_index": 1},
            ],
            patches,
        )
        conditioner = compiled["136"]["inputs"]
        self.assertEqual(["137", 0], conditioner["ref_images.ref_image_0"])
        self.assertEqual(["139", 0], conditioner["ref_images.ref_image_1"])
        self.assertEqual(["167", 0], conditioner["ref_videos.ref_video_0"])
        self.assertFalse(any(key.startswith("ref_video_audios.") for key in conditioner))
        self.assertEqual(24, compiled["167"]["inputs"]["force_rate"])
        with self.assertRaisesRegex(ValueError, "한 개"):
            h3_queue._compile_workflow(
                self.root, self.adapter_id, self.values(), 2, "r2v",
                action_reference_count=0,
            )

    def test_queue_saves_two_participant_mapping_and_blocks_bad_video_references(self):
        asset = self.write_asset()
        pictures = []
        for index in (1, 2):
            path = self.root / f"picture-{index}.png"
            path.write_bytes(f"picture-{index}".encode())
            pictures.append({"upload_path": str(path)})
        prompt = (
            "Lua follows participant A attack motion from <Video 1>. "
            "Jellyfish follows participant B evasion motion from <Video 1>."
        )
        queued = h3_queue.enqueue_candidate_set(self.root, {
            "adapter_id": self.adapter_id,
            "generation_mode": "r2v",
            "prompt": prompt,
            "references": pictures,
            "action_references": [{
                "action_asset_id": asset["action_asset_id"],
                "participant_mapping": {
                    "participant_a": "Lua",
                    "participant_b": "Jellyfish",
                },
            }],
            "candidate_count": 1,
            "width": 832,
            "height": 480,
        })
        request = read_json(
            self.root / "runtime/h3/jobs" / queued["candidate_job_ids"][0] / "request.json"
        )
        self.assertEqual(2, len(request["references"]))
        self.assertEqual(1, len(request["action_references"]))
        self.assertEqual(3, len(request["media_references"]))
        self.assertEqual("motion_only", request["action_references"][0]["reference_role"])
        self.assertEqual(
            {"participant_a": "Lua", "participant_b": "Jellyfish"},
            request["action_references"][0]["participant_mapping"],
        )

        base = {
            "adapter_id": self.adapter_id,
            "prompt": prompt,
            "references": pictures,
            "candidate_count": 1,
            "width": 832,
            "height": 480,
        }
        one = {
            "action_asset_id": asset["action_asset_id"],
            "participant_mapping": {"participant_a": "Lua", "participant_b": "Jellyfish"},
        }
        with self.assertRaisesRegex(ValueError, "한 개"):
            h3_queue.enqueue_candidate_set(
                self.root, {**base, "action_references": [one, one]}
            )
        with self.assertRaisesRegex(ValueError, "<Video 1>"):
            h3_queue.enqueue_candidate_set(
                self.root,
                {**base, "prompt": "Lua and Jellyfish move.", "action_references": [one]},
            )
        with self.assertRaisesRegex(ValueError, "<Video 1>만"):
            h3_queue.enqueue_candidate_set(
                self.root,
                {**base, "prompt": prompt.replace("<Video 1>", "<Video 2>"), "action_references": [one]},
            )
        Path(asset["h3_input_file"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "해시"):
            h3_queue.enqueue_candidate_set(
                self.root, {**base, "action_references": [one]}
            )

    def test_worker_uploads_video_as_input_and_uses_returned_windows_filename(self):
        class Client:
            def __init__(self):
                self.image_uploads = []
                self.video_uploads = []

            def upload_image(self, **kwargs):
                self.image_uploads.append(kwargs["filename"])
                return {"name": "remote-picture.png", "subfolder": "remote", "type": "input"}

            def upload_input(self, **kwargs):
                self.video_uploads.append(kwargs["filename"])
                return {"name": "remote-action.mp4", "subfolder": "remote", "type": "input"}

            def get_queue(self):
                return {"queue_running": [], "queue_pending": []}

            def queue_prompt(self, workflow):
                return {"prompt_id": "prompt-action"}

            def get_history(self, prompt_id):
                return {prompt_id: {"outputs": {}}}

            def _raise_on_execution_error(self, item):
                return None

            def extract_output_files(self, history, prompt_id):
                return [{"filename": "result.mp4", "subfolder": "h3", "type": "output"}]

            def download_file_to_path(self, output, target):
                path = Path(target)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"rendered")

        job_dir = self.root / "runtime/h3/jobs/job-action"
        job_dir.mkdir(parents=True)
        image = self.root / "picture.png"
        video = self.root / "action.mp4"
        image.write_bytes(b"image")
        video.write_bytes(b"video")
        refs = [
            {"source_path": str(image), "sha256": hashlib.sha256(image.read_bytes()).hexdigest()},
            {
                "source_path": str(video),
                "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                "media_type": "video",
                "reference_role": "motion_only",
            },
        ]
        atomic_write_json(job_dir / "request.json", {
            "job_id": "job-action",
            "candidate_set_id": "set-action",
            "job_type": "h3_r2v_generate",
            "queue_name": "h3_generation",
            "generation_mode": "r2v",
            "media_references": refs,
            "reference_patches": [
                {"node_id": "1", "input": "image"},
                {"node_id": "2", "input": "video", "media_type": "video"},
            ],
        })
        atomic_write_json(job_dir / "workflow_api.json", {
            "1": {"class_type": "LoadImage", "inputs": {"image": "placeholder"}},
            "2": {"class_type": "VHS_LoadVideo", "inputs": {"video": "placeholder"}},
        })
        atomic_write_json(job_dir / "manifest.json", {"job_id": "job-action", "outputs": []})
        update_status(job_dir, "queued")
        set_dir = self.root / "runtime/h3/candidate_sets/set-action"
        set_dir.mkdir(parents=True)
        atomic_write_json(set_dir / "candidate_set.json", {
            "candidate_set_id": "set-action",
            "candidate_job_ids": ["job-action"],
            "status": "generating",
        })
        client = Client()
        with mock.patch.object(h3_worker, "ROOT", self.root), mock.patch.object(
            h3_worker, "PATHS", h3_queue.roots(self.root)
        ), mock.patch.object(h3_worker, "POLL_SECONDS", 0), mock.patch.object(
            h3_worker, "_ensure_client", return_value=client
        ):
            h3_worker.process_job(job_dir)
        runtime = read_json(job_dir / "workflow_api_runtime.json")
        self.assertEqual(["picture.png"], client.image_uploads)
        self.assertEqual(["action.mp4"], client.video_uploads)
        self.assertEqual("remote/remote-picture.png", runtime["1"]["inputs"]["image"])
        self.assertEqual("remote/remote-action.mp4", runtime["2"]["inputs"]["video"])


if __name__ == "__main__":
    unittest.main()
