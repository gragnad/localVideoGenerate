from __future__ import annotations

import json
import hashlib
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import h3_queue
import h3_prompt_projects
import h3_worker
import model_test_registry
import model_test_r2v
import workflow_adapter
from job_queue import atomic_write_json
from job_queue import read_json, update_status


class H3QueueTests(unittest.TestCase):
    def test_candidate_reference_path_serves_only_the_archived_set_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            set_dir = root / "runtime/h3/candidate_sets/set-1"
            source = set_dir / "sources/picture_01.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"storyboard")
            atomic_write_json(set_dir / "candidate_set.json", {
                "candidate_set_id": "set-1",
                "references": [{
                    "picture_index": 1,
                    "role": "complete_six_panel_storyboard",
                    "source_path": str(source),
                }],
            })

            self.assertEqual(
                source.resolve(), h3_queue.candidate_reference_path(root, "set-1", 1)
            )

            outside = root / "current-project-storyboard.png"
            outside.write_bytes(b"changed")
            atomic_write_json(set_dir / "candidate_set.json", {
                "candidate_set_id": "set-1",
                "references": [{
                    "picture_index": 1,
                    "role": "complete_six_panel_storyboard",
                    "source_path": str(outside),
                }],
            })
            with self.assertRaisesRegex(FileNotFoundError, "보관본 바깥"):
                h3_queue.candidate_reference_path(root, "set-1", 1)

    def test_superseded_prompt_project_is_blocked_before_candidate_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "prompt_projects" / "old_combined"
            project.mkdir(parents=True)
            (project / "manifest.json").write_text(json.dumps({
                "generation_blocked": True,
                "generation_block_reason": "Use the separated projects.",
                "replacement_project_ids": ["ep00_action", "ep01_story"],
            }), encoding="utf-8")
            image = root / "picture.png"
            image.write_bytes(b"image")

            with self.assertRaisesRegex(ValueError, "separated projects"):
                h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a",
                    "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image)}],
                    "candidate_count": 1,
                    "source_project_id": "old_combined",
                })

            self.assertFalse((root / "runtime/h3/candidate_sets").exists())

    def test_candidate_jobs_use_windows_comfy_render_target_from_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "picture.png"
            image.write_bytes(b"image")
            with mock.patch.dict(
                os.environ,
                {"H3_CANDIDATE_COMFY_URL": "http://100.78.202.37:8189"},
                clear=False,
            ), mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(
                    {},
                    [],
                    {
                        "workflow_profile_id": "w",
                        "workflow_filename": "h3.json",
                    },
                ),
            ):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a",
                    "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image)}],
                    "candidate_count": 1,
                })
                state = h3_queue.state(root)

            request = read_json(
                root / "runtime/h3/jobs" / result["candidate_job_ids"][0] / "request.json"
            )
            self.assertEqual("http://100.78.202.37:8189", request["comfy_url"])
            self.assertEqual("windows_comfy", request["render_target"])
            self.assertEqual("windows_candidate", request["queue_lane"])
            self.assertEqual("windows_comfy", result["render_target"])
            self.assertEqual("windows_candidate", result["queue_lane"])
            self.assertEqual(1280, result["width"])
            self.assertEqual(704, result["height"])
            self.assertEqual("remote_windows_comfy", state["candidate_render"]["mode"])

    def test_candidate_jobs_can_explicitly_use_local_generation_lane(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "picture.png"
            image.write_bytes(b"image")
            with mock.patch.dict(
                os.environ,
                {
                    "COMFY_URL": "http://127.0.0.1:8188",
                    "H3_CANDIDATE_COMFY_URL": "http://100.78.202.37:8189",
                },
                clear=False,
            ), mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(
                    {},
                    [],
                    {
                        "workflow_profile_id": "w",
                        "workflow_filename": "h3.json",
                    },
                ),
            ):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a",
                    "queue_lane": "local_generation",
                    "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image)}],
                    "candidate_count": 1,
                })

            request = read_json(
                root / "runtime/h3/jobs" / result["candidate_job_ids"][0] / "request.json"
            )
            self.assertEqual("http://127.0.0.1:8188", request["comfy_url"])
            self.assertEqual("local_comfy", request["render_target"])
            self.assertEqual("local_generation", request["queue_lane"])
            self.assertEqual("local_comfy", result["render_target"])
            self.assertEqual("local_generation", result["queue_lane"])

    def test_update_attention_r2v_compiles_nine_direct_picture_slots(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows = root / "workflows"
            workflows.mkdir()
            workflow = {
                "92": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output"}},
                "129": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}},
                "132": {"class_type": "PrimitiveFloat", "inputs": {"value": 5}},
                "136": {
                    "class_type": "MiniMaxH3ReferenceToVideo",
                    "inputs": {
                        f"ref_images.ref_image_{index}": [source, 0]
                        for index, source in enumerate(("137", "139", "145", "149", "147"))
                    },
                },
                "138": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": "prompt"}},
                "141": {"class_type": "PrimitiveInt", "inputs": {"value": 832}},
                "142": {"class_type": "PrimitiveInt", "inputs": {"value": 480}},
            }
            loader_ids = ["137", "139", "145", "149", "147"]
            for loader_id in loader_ids:
                workflow[loader_id] = {
                    "class_type": "LoadImage",
                    "inputs": {"image": f"picture_{loader_id}.png"},
                }
            workflow_path = workflows / model_test_r2v.R2V_UPDATE_ATTN_WORKFLOW_FILENAME
            workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
            model_test_registry.register_model(root, {
                "provider": "MiniMax", "family": "H3",
                "display_name": "MiniMax H3", "version": "1",
            })
            model_test_registry.ensure_h3_r2v_adapter(root, workflows)
            adapter = next(
                row for row in h3_queue.available_adapters(root)["adapters"]
                if row["workflow_filename"] == workflow_path.name
            )
            self.assertEqual(9, adapter["max_references"])

            compiled, patches, metadata = h3_queue._compile_workflow(
                root,
                adapter["adapter_id"],
                {
                    "prompt": "Lua faces the Deep Sea King.",
                    "seed": 7,
                    "width": 832,
                    "height": 480,
                    "fps": 24,
                    "duration_seconds": 5,
                    "filename_prefix": "video/h3/nine-pictures",
                },
                9,
                "r2v",
            )
            self.assertEqual("r2v", metadata["generation_mode"])
            self.assertEqual(9, len(patches))
            conditioner = compiled["136"]["inputs"]
            for slot in range(6, 10):
                loader_id = f"h3_ref_{slot}"
                self.assertEqual(
                    f"__H3_REFERENCE_{slot}__",
                    compiled[loader_id]["inputs"]["image"],
                )
                self.assertEqual(
                    [loader_id, 0],
                    conditioner[f"ref_images.ref_image_{slot - 1}"],
                )

            with model_test_registry.open_registry(root) as connection:
                legacy_adapter = workflow_adapter.register_adapter(connection, {
                    "workflow_profile_id": adapter["workflow_profile_id"],
                    "adapter_name": adapter["adapter_name"],
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
                        "loader_node_ids": loader_ids,
                        "loader_template_node_id": "137",
                        "max_slots": 5,
                    },
                })
            visible = [
                row for row in h3_queue.available_adapters(root)["adapters"]
                if row["workflow_filename"] == workflow_path.name
            ]
            self.assertEqual(1, len(visible))
            self.assertEqual(9, visible[0]["max_references"])
            upgraded, upgraded_patches, upgraded_metadata = (
                h3_queue._compile_workflow(
                    root,
                    legacy_adapter["adapter_id"],
                    {
                        "prompt": "Lua faces the Deep Sea King.",
                        "seed": 8,
                        "width": 832,
                        "height": 480,
                        "fps": 24,
                        "duration_seconds": 5,
                        "filename_prefix": "video/h3/legacy-adapter-upgrade",
                    },
                    9,
                    "r2v",
                )
            )
            self.assertEqual(adapter["adapter_id"], upgraded_metadata["adapter_id"])
            self.assertEqual(9, len(upgraded_patches))
            self.assertNotIn("h3_ref_source_9", upgraded)
            self.assertEqual(
                ["h3_ref_9", 0],
                upgraded["136"]["inputs"]["ref_images.ref_image_8"],
            )

    def test_i2v_adapter_compiles_first_frame_and_candidate_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows = root / "workflows"
            workflows.mkdir()
            workflow_path = workflows / model_test_registry.H3_I2V_WORKFLOW_FILENAME
            workflow_path.write_text(json.dumps({
                "92": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output"}},
                "114": {"class_type": "LoadImage", "inputs": {"image": "opening.png"}},
                "131": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}},
                "133": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"prompt": "prompt", "first_frame": ["114", 0]}},
                "135": {"class_type": "PrimitiveFloat", "inputs": {"value": 5}},
                "137": {"class_type": "PrimitiveInt", "inputs": {"value": 1280}},
                "138": {"class_type": "PrimitiveInt", "inputs": {"value": 704}},
            }), encoding="utf-8")
            model_test_registry.register_model(root, {
                "provider": "MiniMax", "family": "H3", "display_name": "MiniMax H3", "version": "1",
            })
            registered = model_test_registry.ensure_h3_i2v_adapter(root, workflows)
            self.assertIsNotNone(registered)
            adapter = next(row for row in h3_queue.available_adapters(root)["adapters"] if row["generation_mode"] == "i2v")
            compiled, patches, metadata = h3_queue._compile_workflow(root, adapter["adapter_id"], {
                "prompt": "The hero steps forward.", "seed": 7, "width": 832, "height": 480,
                "duration_seconds": 5, "filename_prefix": "video/i2v-test",
            }, 1, "i2v")
            self.assertEqual("i2v", metadata["generation_mode"])
            self.assertEqual("__H3_START_IMAGE__", compiled["114"]["inputs"]["image"])
            self.assertEqual([{"node_id": "114", "input": "image"}], patches)
            self.assertEqual("The hero steps forward.", compiled["133"]["inputs"]["prompt"])
            self.assertEqual(832, compiled["137"]["inputs"]["value"])
            with self.assertRaisesRegex(ValueError, "한 장"):
                h3_queue._compile_workflow(root, adapter["adapter_id"], {
                    "prompt": "x", "seed": 1, "width": 832, "height": 480,
                    "duration_seconds": 5, "filename_prefix": "video/invalid",
                }, 2, "i2v")

            image = root / "opening.png"
            image.write_bytes(b"image")
            candidate = h3_queue.enqueue_candidate_set(root, {
                "adapter_id": adapter["adapter_id"], "generation_mode": "i2v",
                "prompt": "The hero steps forward.", "references": [{"upload_path": str(image), "role": "start_frame", "reference_kind": "keyframe"}],
                "candidate_count": 1, "seed": -1, "width": 1376, "height": 768,
            })
            request = read_json(root / "runtime/h3/jobs" / candidate["candidate_job_ids"][0] / "request.json")
            self.assertEqual("i2v", candidate["generation_mode"])
            self.assertEqual("i2v", request["generation_mode"])
            self.assertEqual("h3_r2v_generate", request["job_type"])
            self.assertEqual("start_frame", request["references"][0]["role"])
            self.assertEqual("keyframe", request["references"][0]["reference_kind"])
            self.assertEqual((1376, 768), (request["width"], request["height"]))
            queued_workflow = read_json(
                root / "runtime/h3/jobs" / candidate["candidate_job_ids"][0] / "workflow_api.json"
            )
            self.assertEqual(1376, queued_workflow["137"]["inputs"]["value"])
            self.assertEqual(768, queued_workflow["138"]["inputs"]["value"])

    def test_i2v_turbo_adapter_is_registered_as_separate_production_option(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows = root / "workflows"
            workflows.mkdir()
            common = {
                "92": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output"}},
                "114": {"class_type": "LoadImage", "inputs": {"image": "opening.png"}},
                "131": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}},
                "133": {
                    "class_type": "MiniMaxH3ImageToVideo",
                    "inputs": {"prompt": "prompt", "first_frame": ["114", 0]},
                },
                "135": {"class_type": "PrimitiveFloat", "inputs": {"value": 5}},
                "137": {"class_type": "PrimitiveInt", "inputs": {"value": 1280}},
                "138": {"class_type": "PrimitiveInt", "inputs": {"value": 704}},
            }
            (workflows / model_test_registry.H3_I2V_WORKFLOW_FILENAME).write_text(
                json.dumps(common), encoding="utf-8"
            )
            turbo = {
                **common,
                "144": {
                    "class_type": "MiniMaxH3TurboLoRA",
                    "inputs": {
                        "lora_name": "minimax_h3_turbo_v4_step600_ema.safetensors",
                        "strength": 1.0,
                        "low_vram": False,
                    },
                },
                "146": {"class_type": "MiniMaxH3TurboSampler", "inputs": {}},
            }
            (workflows / model_test_registry.H3_I2V_TURBO8_WORKFLOW_FILENAME).write_text(
                json.dumps(turbo), encoding="utf-8"
            )
            fflf = json.loads(json.dumps(turbo))
            fflf["147"] = {
                "class_type": "LoadImage",
                "inputs": {"image": "ending.png"},
            }
            fflf["133"]["inputs"]["last_frame"] = ["147", 0]
            (
                workflows
                / model_test_registry.H3_I2V_TURBO8_FFLF_WORKFLOW_FILENAME
            ).write_text(json.dumps(fflf), encoding="utf-8")
            model_test_registry.register_model(root, {
                "provider": "MiniMax", "family": "H3",
                "display_name": "MiniMax H3", "version": "1",
            })

            model_test_registry.ensure_h3_i2v_adapter(root, workflows)
            adapters = [
                row for row in h3_queue.available_adapters(root)["adapters"]
                if row["generation_mode"] == "i2v"
            ]
            self.assertEqual(3, len(adapters))
            turbo_adapter = next(
                row for row in adapters if "Turbo 8-step" in row["adapter_name"]
            )
            compiled, _, metadata = h3_queue._compile_workflow(
                root,
                turbo_adapter["adapter_id"],
                {
                    "prompt": "The hero steps forward.", "seed": 7,
                    "width": 832, "height": 480, "duration_seconds": 5,
                    "filename_prefix": "video/i2v-turbo-test",
                },
                1,
                "i2v",
            )
            self.assertEqual("MiniMaxH3TurboLoRA", compiled["144"]["class_type"])
            self.assertEqual("MiniMaxH3TurboSampler", compiled["146"]["class_type"])
            self.assertEqual(
                model_test_registry.H3_I2V_TURBO8_WORKFLOW_FILENAME,
                metadata["workflow_filename"],
            )
            fflf_adapter = next(
                row for row in adapters if "FFLF" in row["adapter_name"]
            )
            self.assertTrue(fflf_adapter["supports_last_frame"])
            self.assertEqual(1, fflf_adapter["required_references"])
            self.assertEqual(2, fflf_adapter["max_references"])

            one_frame, one_patches, _ = h3_queue._compile_workflow(
                root,
                fflf_adapter["adapter_id"],
                {
                    "prompt": "The hero steps forward.", "seed": 7,
                    "width": 832, "height": 480, "duration_seconds": 5,
                    "filename_prefix": "video/i2v-fflf-one-frame",
                },
                1,
                "i2v",
            )
            self.assertNotIn("147", one_frame)
            self.assertNotIn("last_frame", one_frame["133"]["inputs"])
            self.assertEqual(["114"], [row["node_id"] for row in one_patches])

            two_frames, two_patches, _ = h3_queue._compile_workflow(
                root,
                fflf_adapter["adapter_id"],
                {
                    "prompt": "The hero steps forward.", "seed": 7,
                    "width": 832, "height": 480, "duration_seconds": 5,
                    "filename_prefix": "video/i2v-fflf-two-frames",
                },
                2,
                "i2v",
            )
            self.assertEqual("__H3_LAST_IMAGE__", two_frames["147"]["inputs"]["image"])
            self.assertEqual(["147", 0], two_frames["133"]["inputs"]["last_frame"])
            self.assertEqual(["114", "147"], [row["node_id"] for row in two_patches])

    @staticmethod
    def _full_prompt(action: str) -> str:
        return f"""subject_definitions:
<Subject 1> is Hero from <Picture 1>. Preserve the exact identity and clothing.

summary:
[reference generation] The hero performs this event: {action}.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - Preserve the exact identity and clothing.

detailed_description:
[Shot 1] A medium-wide view frames <Subject 1> Hero as the character braces, turns the whole body toward the threat, and completes this action: {action}.

overall_soundscape:
Wind, cloth movement, and one boot scraping stone.

non_diegetic_music:
A restrained low string pulse."""

    def _write_clip(
        self,
        root: Path,
        *,
        scene_id: str,
        clip_id: str,
        sequence: int,
    ) -> None:
        project = root / "prompt_projects" / "dragon"
        payload = {
            "schema_version": 1,
            "prompt_contract_version": "h3_ref_minimal_v1",
            "workflow": "h3_r2v_production",
            "project_id": "dragon",
            "scene_id": scene_id,
            "clip_id": clip_id,
            "sequence": sequence,
            "duration_seconds": 5,
            "video_prompt": self._full_prompt(f"Dragon action {sequence}"),
            "references": [{
                "picture_index": 1,
                "role": "hero",
                "required": True,
                "source_path": "assets/hero.png",
            }],
        }
        (project / scene_id / f"{clip_id}.md").write_text(
            "## Machine Payload\n\n```json\n" + json.dumps(payload) + "\n```\n",
            encoding="utf-8",
        )

    def _write_project(self, root: Path) -> None:
        project = root / "prompt_projects" / "dragon"
        (project / "assets").mkdir(parents=True)
        (project / "assets" / "hero.png").write_bytes(b"image")
        (project / "manifest.json").write_text(json.dumps({
            "project_kind": "h3_r2v_production", "title": "Dragon Season 1",
        }), encoding="utf-8")
        for index, scene_id in enumerate(("SCENE_001", "SCENE_002"), start=1):
            (project / scene_id).mkdir()
            self._write_clip(
                root,
                scene_id=scene_id,
                clip_id=f"CLIP_{index:03d}",
                sequence=index,
            )

    def test_enqueue_is_batch_free_and_uses_separate_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            compiled = {"1": {"class_type": "LoadImage", "inputs": {"image": "placeholder"}}}
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(compiled, [{"node_id": "1", "input": "image"}], {"workflow_profile_id": "workflow_h3", "workflow_filename": "h3.json"}),
            ):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "adapter_h3", "prompt": "Shot 1: The hero runs.",
                    "references": [{"upload_path": str(image), "role": "character"}],
                    "candidate_count": 2, "seed": -1, "width": 1280, "height": 704,
                })
            self.assertEqual(2, len(result["candidate_job_ids"]))
            self.assertFalse((root / "jobs").exists())
            self.assertFalse((root / "runtime/batches").exists())
            for job_id in result["candidate_job_ids"]:
                request = read_json(root / "runtime/h3/jobs" / job_id / "request.json")
                self.assertEqual("h3_generation", request["queue_name"])
                self.assertEqual("h3_r2v_generate", request["job_type"])
                self.assertNotIn("batch_id", request)
                self.assertNotIn("automation", request)
                self.assertGreaterEqual(request["seed"], 0)

    def test_individual_r2v_candidate_preserves_fractional_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            compiled_durations = []

            def compile_workflow(_root, _adapter_id, values, _count, expected=None, _settings=None):
                compiled_durations.append(values["duration_seconds"])
                return (
                    {"1": {"class_type": "Duration", "inputs": {"value": values["duration_seconds"]}}},
                    [],
                    {
                        "workflow_profile_id": "workflow_h3",
                        "workflow_filename": "h3.json",
                        "generation_mode": expected or "r2v",
                        "workflow_settings": {},
                    },
                )

            with mock.patch.object(h3_queue, "_compile_workflow", side_effect=compile_workflow):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "adapter_h3",
                    "prompt": "Shot 1: The hero runs.",
                    "references": [{"upload_path": str(image), "role": "character"}],
                    "candidate_count": 1,
                    "seed": 1234,
                    "width": 1280,
                    "height": 704,
                    "duration_seconds": 6.5,
                })

            request = read_json(
                root / "runtime/h3/jobs" / result["candidate_job_ids"][0] / "request.json"
            )
            self.assertEqual(6.5, request["duration_seconds"])
            self.assertEqual([6.5], compiled_durations)

    def test_r2v_608_resolution_and_selected_resolution_rerender_preserve_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"immutable-reference")
            seed = 317375066245886502

            def compile_workflow(_root, adapter_id, values, _count, expected=None, _settings=None):
                use_default = adapter_id == "adapter_default"
                return (
                    {
                        "1": {
                            "class_type": "LoadImage",
                            "inputs": {"image": "__H3_REFERENCE_1__"},
                        },
                        "2": {
                            "class_type": "Resolution",
                            "inputs": {
                                "width": values["width"],
                                "height": values["height"],
                                "seed": values["seed"],
                                "filename_prefix": values["filename_prefix"],
                            },
                        },
                    },
                    [{"node_id": "1", "input": "image"}],
                    {
                        "adapter_id": adapter_id,
                        "workflow_profile_id": (
                            "workflow_default" if use_default else "workflow_h3"
                        ),
                        "workflow_filename": (
                            "int8_turbo.json" if use_default else "h3.json"
                        ),
                        "generation_mode": expected or "r2v",
                        "workflow_settings": {},
                    },
                )

            # 운영과 같은 환경: Windows 후보 주소가 설정돼 있어도 재생성은 로컬 8188로 간다.
            with mock.patch.dict(os.environ, {
                "COMFY_URL": "http://127.0.0.1:8188",
                "H3_CANDIDATE_COMFY_URL": "http://100.78.202.37:8189",
            }, clear=False), mock.patch.object(
                h3_queue, "_compile_workflow", side_effect=compile_workflow
            ), mock.patch.object(
                h3_queue,
                "_current_default_r2v_adapter",
                return_value={
                    "adapter_id": "adapter_default",
                    "workflow_profile_id": "workflow_default",
                    "workflow_filename": "int8_turbo.json",
                },
            ):
                source = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "adapter_h3",
                    "prompt": "Shot 1: The hero runs.",
                    "references": [{
                        "upload_path": str(image),
                        "role": "character",
                    }],
                    "candidate_count": 1,
                    "seed": seed,
                    "width": 608,
                    "height": 352,
                    "duration_seconds": 6,
                    "source_project_id": "dragon",
                    "source_scene_id": "scene-1",
                    "source_clip_id": "clip-1",
                })
                source_job_id = source["candidate_job_ids"][0]
                paths = h3_queue.roots(root)
                update_status(paths["jobs"] / source_job_id, "completed", stage="done")
                h3_queue.select_candidate(root, source["candidate_set_id"], source_job_id)

                rerender = h3_queue.enqueue_selected_candidate_rerender(
                    root,
                    source["candidate_set_id"],
                    {
                        "source_job_id": source_job_id,
                        "width": 1024,
                        "height": 576,
                    },
                )
                duplicate = h3_queue.enqueue_selected_candidate_rerender(
                    root,
                    source["candidate_set_id"],
                    {
                        "source_job_id": source_job_id,
                        "width": 1024,
                        "height": 576,
                    },
                )
                random_rerender = h3_queue.enqueue_selected_candidate_rerender(
                    root,
                    source["candidate_set_id"],
                    {
                        "source_job_id": source_job_id,
                        "width": 1024,
                        "height": 576,
                        "randomize_seed": True,
                    },
                )

            self.assertFalse(rerender["already_exists"])
            self.assertTrue(duplicate["already_exists"])
            self.assertEqual(rerender["candidate_set_id"], duplicate["candidate_set_id"])
            self.assertNotEqual(
                rerender["candidate_set_id"], random_rerender["candidate_set_id"]
            )
            self.assertEqual("resolution_rerender", rerender["render_purpose"])
            self.assertEqual("current_default", rerender["rerender_workflow_policy"])
            self.assertEqual("workflow_h3", rerender["source_workflow_profile_id"])
            self.assertEqual("h3.json", rerender["source_workflow_filename"])
            self.assertEqual("preserved", rerender["seed_mode"])
            self.assertEqual(seed, rerender["source_seed"])
            self.assertEqual(seed, rerender["rerender_seed"])
            self.assertEqual(source["candidate_set_id"], rerender["source_candidate_set_id"])
            self.assertEqual(source_job_id, rerender["source_selected_job_id"])
            self.assertEqual({"width": 608, "height": 352}, rerender["source_resolution"])
            self.assertEqual({"width": 1024, "height": 576}, rerender["target_resolution"])

            rerender_job_id = rerender["candidate_job_ids"][0]
            random_job_id = random_rerender["candidate_job_ids"][0]
            source_request = read_json(paths["jobs"] / source_job_id / "request.json")
            rerender_request = read_json(paths["jobs"] / rerender_job_id / "request.json")
            random_request = read_json(paths["jobs"] / random_job_id / "request.json")
            self.assertEqual("random", random_request["seed_mode"])
            self.assertEqual(seed, random_request["source_seed"])
            self.assertNotEqual(seed, random_request["seed"])
            self.assertEqual(random_request["seed"], random_request["rerender_seed"])
            self.assertEqual("local_generation", rerender_request["queue_lane"])
            self.assertEqual("local_comfy", rerender_request["render_target"])
            self.assertEqual("http://127.0.0.1:8188", rerender_request["comfy_url"])
            self.assertEqual("local_generation", rerender["queue_lane"])
            self.assertEqual("adapter_default", rerender_request["adapter_id"])
            self.assertEqual("workflow_default", rerender_request["workflow_profile_id"])
            self.assertEqual("int8_turbo.json", rerender_request["workflow_filename"])
            self.assertEqual({}, rerender_request["workflow_settings"])
            for key in (
                "prompt",
                "seed",
                "duration_seconds",
                "generation_mode",
                "source_project_id",
                "source_scene_id",
                "source_clip_id",
            ):
                self.assertEqual(source_request[key], rerender_request[key], key)
            self.assertEqual((608, 352), (source_request["width"], source_request["height"]))
            self.assertEqual((1024, 576), (rerender_request["width"], rerender_request["height"]))
            self.assertEqual(
                source_request["references"][0]["sha256"],
                rerender_request["references"][0]["sha256"],
            )
            self.assertNotEqual(
                source_request["references"][0]["source_path"],
                rerender_request["references"][0]["source_path"],
            )
            state_job = next(
                row for row in h3_queue.state(root)["jobs"]
                if row["job_id"] == source_job_id
            )
            self.assertEqual(str(seed), state_job["request"]["seed_text"])
            stored_source = read_json(
                paths["candidate_sets"] / source["candidate_set_id"] / "candidate_set.json"
            )
            self.assertEqual(source_job_id, stored_source["selected_job_id"])
            self.assertEqual(
                [source_job_id],
                [row["job_id"] for row in stored_source["selected_jobs"]],
            )

    def test_selected_portrait_i2v_result_queues_direct_1080x1920_upscale(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = h3_queue.roots(root)
            set_id, job_id = "h3set_i2v", "h3job_i2v"
            atomic_write_json(
                paths["candidate_sets"] / set_id / "candidate_set.json",
                {"candidate_set_id": set_id, "candidate_job_ids": [job_id], "generation_mode": "i2v",
                 "selected_job_id": job_id, "selected_jobs": [{"job_id": job_id}], "source_clip_id": "hello"},
            )
            video = root / "i2v.mp4"
            video.write_bytes(b"i2v-video")
            job_dir = paths["jobs"] / job_id
            atomic_write_json(job_dir / "request.json", {"job_id": job_id, "width": 576, "height": 1024})
            atomic_write_json(job_dir / "manifest.json", {"local_video_path": str(video),
                              "output_sha256": hashlib.sha256(b"i2v-video").hexdigest()})
            update_status(job_dir, "completed", stage="done")
            with mock.patch.dict(os.environ, {"H3_CANDIDATE_COMFY_URL": "http://100.78.202.37:8189"}, clear=False):
                queued = h3_queue.enqueue_selected_candidate_upscale(root, set_id, {"source_selected_job_id": job_id})
                duplicate = h3_queue.enqueue_selected_candidate_upscale(root, set_id, {"source_selected_job_id": job_id})
            self.assertTrue(duplicate["already_exists"])
            self.assertEqual({"width": 1080, "height": 1920}, queued["target_resolution"])
            request = read_json(paths["jobs"] / queued["job_id"] / "request.json")
            workflow = read_json(paths["jobs"] / queued["job_id"] / "workflow_api.json")
            self.assertEqual(str(video), request["source_video_path"])
            self.assertIsNone(request["source_rerender_job_id"])
            self.assertEqual("selected_i2v", request["upscale_source"])
            self.assertEqual((1080, 1920), (workflow["2"]["inputs"]["resize_type.width"],
                                            workflow["2"]["inputs"]["resize_type.height"]))

    def test_completed_spark_result_queues_one_windows_h264_upscale_and_worker_runs_it(self):
        class Client:
            def upload_input(self, *, filename, content, subfolder, overwrite=True):
                self.uploaded = content
                return {"name": filename, "subfolder": subfolder, "type": "input"}

            def queue_prompt(self, workflow):
                self.workflow = workflow
                return {"prompt_id": "upscale-prompt-1"}

            def get_queue(self):
                return {"queue_running": [], "queue_pending": []}

            def get_history(self, prompt_id):
                return {prompt_id: {"outputs": {}}}

            def _raise_on_execution_error(self, item):
                return None

            def extract_output_files(self, history, prompt_id):
                return [{"filename": "upscale.mp4", "subfolder": "h3", "type": "output"}]

            def download_file_to_path(self, output, target):
                path = Path(target)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"h264-upscale-output")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = h3_queue.roots(root)
            source_set_id = "h3set_source"
            selected_job_id = "h3job_selected"
            rerender_set_id = "h3set_spark"
            rerender_job_id = "h3job_spark"
            atomic_write_json(
                paths["candidate_sets"] / source_set_id / "candidate_set.json",
                {
                    "candidate_set_id": source_set_id,
                    "candidate_job_ids": [selected_job_id],
                    "selected_job_id": selected_job_id,
                    "selected_jobs": [{"job_id": selected_job_id}],
                    "source_project_id": "dragon",
                    "source_scene_id": "scene-1",
                    "source_clip_id": "clip-1",
                },
            )
            atomic_write_json(
                paths["candidate_sets"] / rerender_set_id / "candidate_set.json",
                {
                    "candidate_set_id": rerender_set_id,
                    "candidate_job_ids": [rerender_job_id],
                    "render_purpose": "resolution_rerender",
                    "source_candidate_set_id": source_set_id,
                    "source_selected_job_id": selected_job_id,
                },
            )
            video = root / "spark.mp4"
            video.write_bytes(b"spark-rerender-video")
            sha256 = hashlib.sha256(video.read_bytes()).hexdigest()
            rerender_job_dir = paths["jobs"] / rerender_job_id
            atomic_write_json(
                rerender_job_dir / "request.json",
                {"job_id": rerender_job_id, "width": 1024, "height": 576},
            )
            atomic_write_json(
                rerender_job_dir / "manifest.json",
                {"local_video_path": str(video), "output_sha256": sha256},
            )
            update_status(rerender_job_dir, "completed", stage="Spark done")

            with mock.patch.dict(
                os.environ,
                {"H3_CANDIDATE_COMFY_URL": "http://100.78.202.37:8189"},
                clear=False,
            ):
                queued = h3_queue.enqueue_selected_candidate_upscale(
                    root,
                    source_set_id,
                    {
                        "source_selected_job_id": selected_job_id,
                        "source_rerender_job_id": rerender_job_id,
                    },
                )
                duplicate = h3_queue.enqueue_selected_candidate_upscale(
                    root,
                    source_set_id,
                    {
                        "source_selected_job_id": selected_job_id,
                        "source_rerender_job_id": rerender_job_id,
                    },
                )

            self.assertFalse(queued["already_exists"])
            self.assertTrue(duplicate["already_exists"])
            self.assertEqual(queued["job_id"], duplicate["job_id"])
            upscale_dir = paths["jobs"] / queued["job_id"]
            request = read_json(upscale_dir / "request.json")
            workflow = read_json(upscale_dir / "workflow_api.json")
            self.assertEqual("h3_video_upscale", request["job_type"])
            self.assertEqual("windows_candidate", request["queue_lane"])
            self.assertEqual("windows_comfy", request["render_target"])
            self.assertEqual({"width": 1920, "height": 1080}, request["target_resolution"])
            self.assertEqual(60, request["target_fps"])
            self.assertEqual("video/h264-mp4", workflow["8"]["inputs"]["format"])
            self.assertEqual("yuv420p", workflow["8"]["inputs"]["pix_fmt"])

            client = Client()
            with (
                mock.patch.object(h3_worker, "ROOT", root),
                mock.patch.object(h3_worker, "PATHS", paths),
                mock.patch.object(h3_worker, "_ensure_client", return_value=client),
            ):
                h3_worker.process_job(upscale_dir)

            status = read_json(upscale_dir / "status.json")
            manifest = read_json(upscale_dir / "manifest.json")
            runtime_workflow = read_json(upscale_dir / "workflow_api_runtime.json")
            self.assertEqual("completed", status["status"])
            self.assertEqual("h264", manifest["output_codec"])
            self.assertEqual(1920, manifest["output_width"])
            self.assertEqual(1080, manifest["output_height"])
            self.assertEqual(60, manifest["output_fps"])
            self.assertTrue(Path(manifest["local_video_path"]).is_file())
            self.assertEqual(b"spark-rerender-video", client.uploaded)
            self.assertEqual(
                f"h3_upscale_jobs/{queued['job_id']}/{video.name}",
                runtime_workflow["7"]["inputs"]["video"],
            )
            self.assertEqual("video/h264-mp4", client.workflow["8"]["inputs"]["format"])

    def test_terminal_candidate_set_can_requeue_same_inputs_with_fresh_seeds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"immutable-reference")

            def compile_workflow(
                _root, _adapter_id, values, _count, expected=None, settings=None
            ):
                return (
                    {"1": {"inputs": dict(values)}},
                    [],
                    {
                        "workflow_profile_id": "workflow_h3",
                        "workflow_filename": "h3.json",
                        "generation_mode": expected or "r2v",
                        "workflow_settings": dict(settings or {}),
                    },
                )

            with mock.patch.object(
                h3_queue, "_compile_workflow", side_effect=compile_workflow
            ):
                source = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "adapter_h3",
                    "generation_mode": "r2v",
                    "prompt": "Shot 1: The hero runs.",
                    "references": [{
                        "upload_path": str(image),
                        "role": "character",
                    }],
                    "candidate_count": 2,
                    "seed": 100,
                    "width": 608,
                    "height": 352,
                    "duration_seconds": 6,
                    "workflow_settings": {"sol_attn": {"tau": 1.3}},
                    "source_project_id": "dragon_ep01",
                    "source_scene_id": "EP01-S01",
                    "source_clip_id": "EP01-S01-C01",
                })
                with self.assertRaisesRegex(ValueError, "모든 기존 후보 작업이 끝난 뒤"):
                    h3_queue.requeue_candidate_set(
                        root, source["candidate_set_id"]
                    )

                paths = h3_queue.roots(root)
                for job_id in source["candidate_job_ids"]:
                    update_status(paths["jobs"] / job_id, "completed", stage="done")
                with mock.patch.object(
                    h3_queue.secrets, "randbits", side_effect=[700, 701]
                ):
                    requeued = h3_queue.requeue_candidate_set(
                        root, source["candidate_set_id"]
                    )

            self.assertNotEqual(
                source["candidate_set_id"], requeued["candidate_set_id"]
            )
            self.assertEqual(
                source["candidate_set_id"],
                requeued["requeued_from_candidate_set_id"],
            )
            self.assertTrue(requeued["fresh_random_seeds"])
            self.assertEqual("candidate_rerun", requeued["render_purpose"])
            self.assertEqual(
                source["candidate_set_id"], requeued["source_candidate_set_id"]
            )
            self.assertEqual(2, requeued["candidate_count"])

            source_request = read_json(
                paths["jobs"] / source["candidate_job_ids"][0] / "request.json"
            )
            requests = [
                read_json(paths["jobs"] / job_id / "request.json")
                for job_id in requeued["candidate_job_ids"]
            ]
            self.assertEqual([700, 701], [row["seed"] for row in requests])
            for request in requests:
                for key in (
                    "adapter_id",
                    "generation_mode",
                    "prompt",
                    "width",
                    "height",
                    "duration_seconds",
                    "workflow_settings",
                    "source_project_id",
                    "source_scene_id",
                    "source_clip_id",
                ):
                    self.assertEqual(source_request[key], request[key], key)
                self.assertEqual(
                    source_request["references"][0]["sha256"],
                    request["references"][0]["sha256"],
                )
                self.assertNotEqual(
                    source_request["references"][0]["source_path"],
                    request["references"][0]["source_path"],
                )

    def test_608_resolution_is_not_enabled_for_i2v_production(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "start.png"
            image.write_bytes(b"image")
            with self.assertRaisesRegex(ValueError, "I2V 출력 해상도"):
                h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "adapter_i2v",
                    "generation_mode": "i2v",
                    "prompt": "The hero steps forward.",
                    "references": [{"upload_path": str(image), "role": "start_frame"}],
                    "candidate_count": 1,
                    "seed": 7,
                    "width": 608,
                    "height": 352,
                })

    def test_selected_resolution_rerender_rejects_i2v_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "start.png"
            image.write_bytes(b"image")
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(
                    {},
                    [],
                    {
                        "workflow_profile_id": "workflow_i2v",
                        "workflow_filename": "i2v.json",
                        "generation_mode": "i2v",
                        "workflow_settings": {},
                    },
                ),
            ):
                source = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "adapter_i2v",
                    "generation_mode": "i2v",
                    "prompt": "The hero steps forward.",
                    "references": [{"upload_path": str(image), "role": "start_frame"}],
                    "candidate_count": 1,
                    "seed": 7,
                    "width": 832,
                    "height": 480,
                })
            paths = h3_queue.roots(root)
            source_job_id = source["candidate_job_ids"][0]
            update_status(paths["jobs"] / source_job_id, "completed", stage="done")
            h3_queue.select_candidate(root, source["candidate_set_id"], source_job_id)
            with self.assertRaisesRegex(ValueError, "R2V 결과만 지원"):
                h3_queue.enqueue_selected_candidate_rerender(
                    root,
                    source["candidate_set_id"],
                    {"width": 1280, "height": 704},
                )

    def test_selected_resolution_rerender_rejects_unselected_sibling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(
                    {},
                    [],
                    {
                        "workflow_profile_id": "workflow_h3",
                        "workflow_filename": "h3.json",
                    },
                ),
            ):
                source = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "adapter_h3",
                    "prompt": "Shot 1: The hero runs.",
                    "references": [{"upload_path": str(image)}],
                    "candidate_count": 2,
                    "width": 608,
                    "height": 352,
                })

            paths = h3_queue.roots(root)
            selected_job_id, sibling_job_id = source["candidate_job_ids"]
            for job_id in source["candidate_job_ids"]:
                update_status(paths["jobs"] / job_id, "completed", stage="done")
            h3_queue.select_candidate(
                root, source["candidate_set_id"], selected_job_id
            )

            with self.assertRaisesRegex(ValueError, "현재 선택된 후보가 아닙니다"):
                h3_queue.enqueue_selected_candidate_rerender(
                    root,
                    source["candidate_set_id"],
                    {
                        "source_job_id": sibling_job_id,
                        "width": 1280,
                        "height": 704,
                    },
                )

    def test_reconcile_and_select_derive_state_from_jobs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=({}, [], {"workflow_profile_id": "w", "workflow_filename": "h3.json"}),
            ):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a", "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image)}], "candidate_count": 1,
                })
            job_id = result["candidate_job_ids"][0]
            job_dir = root / "runtime/h3/jobs" / job_id
            update_status(job_dir, "completed", stage="done")
            reconciled = h3_queue.reconcile(root, result["candidate_set_id"])[0]
            self.assertEqual("awaiting_candidate_selection", reconciled["status"])
            selected = h3_queue.select_candidate(root, result["candidate_set_id"], job_id)
            self.assertEqual("selected", selected["status"])
            self.assertEqual(job_id, selected["selected_job_id"])

    def test_candidate_set_selection_is_exclusive_and_can_be_cleared(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(
                    {},
                    [],
                    {"workflow_profile_id": "w", "workflow_filename": "h3.json"},
                ),
            ):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a",
                    "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image)}],
                    "candidate_count": 2,
                })

            paths = h3_queue.roots(root)
            first_job_id, second_job_id = result["candidate_job_ids"]
            for job_id in result["candidate_job_ids"]:
                update_status(paths["jobs"] / job_id, "completed", stage="done")

            first = h3_queue.select_candidate(
                root, result["candidate_set_id"], first_job_id
            )
            second = h3_queue.select_candidate(
                root, result["candidate_set_id"], second_job_id
            )
            duplicate = h3_queue.select_candidate(
                root, result["candidate_set_id"], second_job_id
            )

            self.assertEqual([first_job_id], [
                row["job_id"] for row in first["selected_jobs"]
            ])
            self.assertEqual([second_job_id], [
                row["job_id"] for row in second["selected_jobs"]
            ])
            self.assertEqual([second_job_id], [
                row["job_id"] for row in duplicate["selected_jobs"]
            ])
            self.assertEqual(second_job_id, second["selected_job_id"])
            self.assertEqual(
                "selected",
                h3_queue.reconcile(root, result["candidate_set_id"])[0]["status"],
            )

            cleared = h3_queue.clear_candidate_selection(
                root, result["candidate_set_id"], first_job_id
            )
            self.assertFalse(cleared["selection_cleared"])
            self.assertEqual([], cleared["cleared_job_ids"])
            self.assertEqual([second_job_id], [
                row["job_id"] for row in cleared["selected_jobs"]
            ])
            self.assertEqual(second_job_id, cleared["selected_job_id"])
            self.assertEqual("selected", cleared["status"])

            final = h3_queue.clear_candidate_selection(
                root, result["candidate_set_id"], second_job_id
            )
            self.assertEqual([], final["selected_jobs"])
            self.assertIsNone(final["selected_job_id"])
            self.assertEqual("awaiting_candidate_selection", final["status"])

    def test_h3_video_path_requires_completed_status_and_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = h3_queue.roots(root)
            job_id = "h3job_video_path"
            job_dir = paths["jobs"] / job_id
            job_dir.mkdir(parents=True)
            video = root / "candidate.mp4"
            video.write_bytes(b"video")
            atomic_write_json(job_dir / "manifest.json", {
                "job_id": job_id,
                "status": "completed",
                "local_video_path": str(video),
            })
            update_status(job_dir, "running", stage="generating")

            with self.assertRaises(FileNotFoundError):
                h3_queue.video_path(root, job_id)
            update_status(job_dir, "completed", stage="done")
            self.assertEqual(video, h3_queue.video_path(root, job_id))
            video.unlink()
            with self.assertRaises(FileNotFoundError):
                h3_queue.video_path(root, job_id)

    def test_clear_selection_is_idempotent_preserves_outputs_and_allows_reselection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=({}, [], {"workflow_profile_id": "w", "workflow_filename": "h3.json"}),
            ):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a", "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image)}], "candidate_count": 2,
                })

            paths = h3_queue.roots(root)
            for index, job_id in enumerate(result["candidate_job_ids"], start=1):
                job_dir = paths["jobs"] / job_id
                video = paths["outputs"] / result["candidate_set_id"] / f"{job_id}.mp4"
                video.parent.mkdir(parents=True, exist_ok=True)
                video.write_bytes(f"video-{index}".encode())
                manifest = read_json(job_dir / "manifest.json")
                manifest.update(
                    status="completed",
                    local_video_path=str(video),
                    generation_seconds=100.0 + index,
                    completed_at="2026-08-07T22:00:00+09:00",
                )
                atomic_write_json(job_dir / "manifest.json", manifest)
                update_status(job_dir, "completed", stage="done")

            selected_job_id, other_job_id = result["candidate_job_ids"]
            h3_queue.select_candidate(root, result["candidate_set_id"], selected_job_id)
            before_jobs = {
                path.relative_to(root): path.read_bytes()
                for path in paths["jobs"].rglob("*")
                if path.is_file()
            }
            before_videos = {
                path.relative_to(root): path.read_bytes()
                for path in paths["outputs"].rglob("*")
                if path.is_file()
            }

            cleared = h3_queue.clear_candidate_selection(root, result["candidate_set_id"])
            self.assertTrue(cleared["selection_cleared"])
            self.assertEqual(selected_job_id, cleared["previous_selected_job_id"])
            self.assertIsNone(cleared["selected_job_id"])
            self.assertIsNone(cleared["selected_at"])
            self.assertEqual("awaiting_candidate_selection", cleared["status"])
            stored = read_json(
                paths["candidate_sets"] / result["candidate_set_id"] / "candidate_set.json"
            )
            self.assertNotIn("selection_cleared", stored)
            self.assertEqual(before_jobs, {
                path.relative_to(root): path.read_bytes()
                for path in paths["jobs"].rglob("*")
                if path.is_file()
            })
            self.assertEqual(before_videos, {
                path.relative_to(root): path.read_bytes()
                for path in paths["outputs"].rglob("*")
                if path.is_file()
            })

            duplicate = h3_queue.clear_candidate_selection(root, result["candidate_set_id"])
            self.assertFalse(duplicate["selection_cleared"])
            self.assertIsNone(duplicate["previous_selected_job_id"])
            self.assertEqual("awaiting_candidate_selection", duplicate["status"])
            reselected = h3_queue.select_candidate(root, result["candidate_set_id"], other_job_id)
            self.assertEqual("selected", reselected["status"])
            self.assertEqual(other_job_id, reselected["selected_job_id"])

    def test_clear_selection_returns_to_generating_while_another_candidate_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=({}, [], {"workflow_profile_id": "w", "workflow_filename": "h3.json"}),
            ):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a", "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image)}], "candidate_count": 2,
                })

            selected_job_id, running_job_id = result["candidate_job_ids"]
            paths = h3_queue.roots(root)
            update_status(paths["jobs"] / selected_job_id, "completed", stage="done")
            update_status(paths["jobs"] / running_job_id, "running", stage="generating")
            h3_queue.select_candidate(root, result["candidate_set_id"], selected_job_id)

            cleared = h3_queue.clear_candidate_selection(root, result["candidate_set_id"])
            self.assertEqual("generating", cleared["status"])
            self.assertIsNone(cleared["selected_job_id"])
            self.assertIsNone(cleared["selected_at"])

    def test_reconcile_cannot_overwrite_a_concurrent_candidate_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(
                    {},
                    [],
                    {"workflow_profile_id": "w", "workflow_filename": "h3.json"},
                ),
            ):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a",
                    "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image)}],
                    "candidate_count": 2,
                })

            selected_job_id, running_job_id = result["candidate_job_ids"]
            paths = h3_queue.roots(root)
            update_status(paths["jobs"] / selected_job_id, "completed", stage="done")
            update_status(paths["jobs"] / running_job_id, "running", stage="generating")
            candidate_path = (
                paths["candidate_sets"]
                / result["candidate_set_id"]
                / "candidate_set.json"
            )
            reconcile_entered = threading.Event()
            allow_reconcile_write = threading.Event()
            selection_finished = threading.Event()
            errors: list[BaseException] = []

            def delayed_reconcile(_paths, path):
                stale = read_json(path)
                reconcile_entered.set()
                if not allow_reconcile_write.wait(timeout=2):
                    raise TimeoutError("동시성 테스트 reconcile 해제 대기 실패")
                stale.update(status="generating")
                atomic_write_json(path, stale)
                return stale

            def run_reconcile():
                try:
                    h3_queue.reconcile(root, result["candidate_set_id"])
                except BaseException as exc:  # pragma: no cover - assertion below
                    errors.append(exc)

            def run_selection():
                try:
                    h3_queue.select_candidate(
                        root, result["candidate_set_id"], selected_job_id
                    )
                except BaseException as exc:  # pragma: no cover - assertion below
                    errors.append(exc)
                finally:
                    selection_finished.set()

            with mock.patch.object(
                h3_queue, "_reconcile_candidate_path", side_effect=delayed_reconcile
            ):
                reconcile_thread = threading.Thread(target=run_reconcile)
                reconcile_thread.start()
                self.assertTrue(reconcile_entered.wait(timeout=2))
                selection_thread = threading.Thread(target=run_selection)
                selection_thread.start()
                time.sleep(0.05)
                self.assertFalse(selection_finished.is_set())
                allow_reconcile_write.set()
                reconcile_thread.join(timeout=2)
                selection_thread.join(timeout=2)

            self.assertFalse(reconcile_thread.is_alive())
            self.assertFalse(selection_thread.is_alive())
            self.assertEqual([], errors)
            stored = read_json(candidate_path)
            self.assertEqual("selected", stored["status"])
            self.assertEqual(selected_job_id, stored["selected_job_id"])

    def test_candidate_selection_clear_route_and_bridge_are_registered(self):
        project_root = Path(__file__).resolve().parents[1]
        server = (project_root / "web/server.mjs").read_text(encoding="utf-8")
        backend = (project_root / "ui_backend.py").read_text(encoding="utf-8")
        self.assertIn("/selection$/", server)
        self.assertIn("req.method === 'DELETE' && candidateSelection", server)
        self.assertIn("python('clear_h3_candidate_selection'", server)
        self.assertIn('"clear_h3_candidate_selection": clear_h3_candidate_selection', backend)

    def test_candidate_set_delete_rejects_any_nonterminal_job(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(
                    {},
                    [],
                    {"workflow_profile_id": "w", "workflow_filename": "h3.json"},
                ),
            ):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a",
                    "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image)}],
                    "candidate_count": 2,
                })

            paths = h3_queue.roots(root)
            completed_job, running_job = result["candidate_job_ids"]
            update_status(paths["jobs"] / completed_job, "completed", stage="done")
            update_status(paths["jobs"] / running_job, "running", stage="generating")
            candidate_path = (
                paths["candidate_sets"]
                / result["candidate_set_id"]
                / "candidate_set.json"
            )
            before = candidate_path.read_bytes()

            with self.assertRaisesRegex(RuntimeError, "강제종료"):
                h3_queue.delete_candidate_set(root, result["candidate_set_id"])

            self.assertEqual(before, candidate_path.read_bytes())
            self.assertFalse(read_json(candidate_path).get("deleted", False))
            self.assertTrue((paths["jobs"] / running_job).is_dir())

    def test_force_stop_then_soft_delete_hides_set_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(
                    {},
                    [],
                    {"workflow_profile_id": "w", "workflow_filename": "h3.json"},
                ),
            ):
                result = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a",
                    "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image)}],
                    "candidate_count": 3,
                })

            paths = h3_queue.roots(root)
            completed_job, queued_job, running_job = result["candidate_job_ids"]
            update_status(paths["jobs"] / completed_job, "completed", stage="done")
            update_status(paths["jobs"] / queued_job, "queued", stage="waiting")
            update_status(
                paths["jobs"] / running_job,
                "running",
                stage="generating",
                prompt_id="prompt-running",
            )
            running_manifest_path = paths["jobs"] / running_job / "manifest.json"
            running_manifest = read_json(running_manifest_path)
            running_manifest["prompt_id"] = "prompt-running"
            atomic_write_json(running_manifest_path, running_manifest)
            h3_queue.select_candidate(
                root, result["candidate_set_id"], completed_job
            )

            with mock.patch.object(
                h3_queue.ComfyClient,
                "cancel_prompt",
                return_value={"running_interrupted": True},
            ) as cancel:
                stopped = h3_queue.force_stop_group(
                    root, result["candidate_set_id"]
                )
            self.assertEqual("cancelling", stopped["status"])
            self.assertEqual([queued_job], stopped["cancelled_job_ids"])
            self.assertEqual([running_job], stopped["cancel_requested_job_ids"])
            cancel.assert_called_once_with("prompt-running")
            with self.assertRaisesRegex(RuntimeError, "강제종료"):
                h3_queue.delete_candidate_set(root, result["candidate_set_id"])

            update_status(
                paths["jobs"] / running_job,
                "cancelled",
                stage="force stop complete",
            )
            reconciled = h3_queue.reconcile(
                root, result["candidate_set_id"]
            )[0]
            self.assertEqual("cancelled", reconciled["status"])
            with self.assertRaisesRegex(RuntimeError, "선택된 후보"):
                h3_queue.delete_candidate_set(root, result["candidate_set_id"])
            cleared = h3_queue.clear_candidate_selection(
                root, result["candidate_set_id"], completed_job
            )
            self.assertTrue(cleared["selection_cleared"])

            output = paths["outputs"] / result["candidate_set_id"] / "selected.mp4"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"selected-video")
            benchmark_job = "h3bench_unrelated"
            benchmark_dir = paths["jobs"] / benchmark_job
            benchmark_dir.mkdir(parents=True)
            atomic_write_json(benchmark_dir / "request.json", {
                "job_id": benchmark_job,
                "job_type": "h3_r2v_benchmark",
                "queue_name": "h3_generation",
                "test_queue_id": "h3testq_keep",
                # Even malformed legacy metadata must not hide model-test jobs.
                "candidate_set_id": result["candidate_set_id"],
            })
            atomic_write_json(benchmark_dir / "manifest.json", {
                "job_id": benchmark_job,
                "status": "completed",
            })
            update_status(benchmark_dir, "completed", stage="benchmark done")
            source_files = {
                path.relative_to(root): path.read_bytes()
                for path in (
                    paths["candidate_sets"] / result["candidate_set_id"] / "sources"
                ).rglob("*")
                if path.is_file()
            }
            job_files = {
                path.relative_to(root): path.read_bytes()
                for path in paths["jobs"].rglob("*")
                if path.is_file()
            }
            output_files = {
                path.relative_to(root): path.read_bytes()
                for path in paths["outputs"].rglob("*")
                if path.is_file()
            }

            deleted = h3_queue.delete_candidate_set(
                root, result["candidate_set_id"]
            )
            self.assertTrue(deleted["soft_deleted"])
            self.assertFalse(deleted["already_deleted"])
            self.assertTrue(deleted["jobs_preserved"])
            candidate_path = (
                paths["candidate_sets"]
                / result["candidate_set_id"]
                / "candidate_set.json"
            )
            stored = read_json(candidate_path)
            self.assertTrue(stored["deleted"])
            self.assertEqual("deleted", stored["status"])
            self.assertEqual("cancelled", stored["status_before_delete"])
            self.assertTrue(stored["deleted_at"])
            self.assertEqual([], h3_queue.reconcile(root, result["candidate_set_id"]))
            current_state = h3_queue.state(root)
            self.assertNotIn(
                result["candidate_set_id"],
                {
                    row["candidate_set_id"]
                    for row in current_state["candidate_sets"]
                },
            )
            visible_job_ids = {row["job_id"] for row in current_state["jobs"]}
            self.assertTrue(set(result["candidate_job_ids"]).isdisjoint(visible_job_ids))
            self.assertIn(benchmark_job, visible_job_ids)
            with self.assertRaises(FileNotFoundError):
                h3_queue.select_candidate(
                    root, result["candidate_set_id"], completed_job
                )
            with self.assertRaises(FileNotFoundError):
                h3_queue.clear_candidate_selection(root, result["candidate_set_id"])
            with self.assertRaises(FileNotFoundError):
                h3_queue.force_stop_group(root, result["candidate_set_id"])

            duplicate = h3_queue.delete_candidate_set(
                root, result["candidate_set_id"]
            )
            self.assertTrue(duplicate["already_deleted"])
            self.assertEqual(source_files, {
                path.relative_to(root): path.read_bytes()
                for path in (
                    paths["candidate_sets"] / result["candidate_set_id"] / "sources"
                ).rglob("*")
                if path.is_file()
            })
            self.assertEqual(job_files, {
                path.relative_to(root): path.read_bytes()
                for path in paths["jobs"].rglob("*")
                if path.is_file()
            })
            self.assertEqual(output_files, {
                path.relative_to(root): path.read_bytes()
                for path in paths["outputs"].rglob("*")
                if path.is_file()
            })

    def test_candidate_set_delete_route_uses_confirmed_bridge_without_password(self):
        project_root = Path(__file__).resolve().parents[1]
        server = (project_root / "web/server.mjs").read_text(encoding="utf-8")
        backend = (project_root / "ui_backend.py").read_text(encoding="utf-8")
        route = server.split("const candidateSet =", 1)[1].split(
            "const candidateSelect =", 1
        )[0]
        bridge = backend.split("def delete_h3_candidate_set", 1)[1].split(
            "def h3_video", 1
        )[0]
        self.assertIn("req.method === 'DELETE' && candidateSet", route)
        self.assertIn("...(await bodyJson(req))", route)
        self.assertIn("python('delete_h3_candidate_set'", route)
        self.assertNotIn("_require_deletion_password(data)", bridge)
        self.assertIn("h3_queue.delete_candidate_set", bridge)
        self.assertIn('"delete_h3_candidate_set": delete_h3_candidate_set', backend)

    def test_project_test_set_delete_route_uses_confirmed_bridge_without_password(self):
        project_root = Path(__file__).resolve().parents[1]
        server = (project_root / "web/server.mjs").read_text(encoding="utf-8")
        backend = (project_root / "ui_backend.py").read_text(encoding="utf-8")
        route = server.split("const projectTestSet =", 1)[1].split(
            "const projectTestQueue =", 1
        )[0]
        bridge = backend.split("def delete_h3_project_test_set", 1)[1].split(
            "def queue_h3_scene_candidates", 1
        )[0]
        self.assertIn("req.method === 'DELETE' && projectTestSet", route)
        self.assertIn("...(await bodyJson(req))", route)
        self.assertIn("python('delete_h3_project_test_set'", route)
        self.assertIn("project_test_set_id: decodeURIComponent", route)
        self.assertNotIn("_require_deletion_password(data)", bridge)
        self.assertIn("h3_queue.delete_project_test_set", bridge)
        self.assertIn(
            '"delete_h3_project_test_set": delete_h3_project_test_set',
            backend,
        )

    def test_h3_video_thumbnail_route_caches_refreshes_and_rejects_incomplete(self):
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = h3_queue.roots(root)
            completed_job = "h3job_thumbnail_completed"
            running_job = "h3job_thumbnail_running"
            video = root / "candidate.mp4"
            video.write_bytes(b"video-v1")
            for job_id, status in (
                (completed_job, "completed"),
                (running_job, "running"),
            ):
                job_dir = paths["jobs"] / job_id
                job_dir.mkdir(parents=True)
                atomic_write_json(job_dir / "request.json", {
                    "job_id": job_id,
                    "job_type": "h3_r2v_generate",
                    "queue_name": "h3_generation",
                })
                atomic_write_json(job_dir / "manifest.json", {
                    "job_id": job_id,
                    "status": "completed",
                    "local_video_path": str(video),
                })
                update_status(job_dir, status, stage=status)

            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            counter = root / "ffmpeg-count.txt"
            ffmpeg = fake_bin / "ffmpeg"
            ffmpeg.write_text(
                "#!/usr/bin/env python3\n"
                "import os, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "source = pathlib.Path(args[args.index('-i') + 1])\n"
                "target = pathlib.Path(args[-1])\n"
                "target.write_bytes(b'thumbnail:' + source.read_bytes())\n"
                "counter = pathlib.Path(os.environ['FAKE_FFMPEG_COUNT'])\n"
                "count = int(counter.read_text()) if counter.exists() else 0\n"
                "counter.write_text(str(count + 1))\n",
                encoding="utf-8",
            )
            ffmpeg.chmod(0o755)

            try:
                listener = socket.socket()
            except PermissionError:
                self.skipTest("sandbox blocks local sockets")
            with listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            environment = {
                **os.environ,
                "VIDEO_ENGINE_ROOT": str(root),
                "VIDEO_ENGINE_PYTHON": str(project_root / ".venv/bin/python"),
                "VIDEO_UI_HOST": "127.0.0.1",
                "VIDEO_UI_PORT": str(port),
                "VIDEO_UI_ACCESS_KEY": "",
                "FAKE_FFMPEG_COUNT": str(counter),
                "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
            }
            process = subprocess.Popen(
                ["node", "web/server.mjs"],
                cwd=project_root,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            base = f"http://127.0.0.1:{port}"
            try:
                deadline = time.monotonic() + 5
                while True:
                    try:
                        with urllib.request.urlopen(f"{base}/", timeout=0.5):
                            break
                    except (OSError, urllib.error.URLError):
                        if process.poll() is not None or time.monotonic() >= deadline:
                            stdout, stderr = process.communicate(timeout=1)
                            self.fail(f"H3 UI test server failed: {stdout}\n{stderr}")
                        time.sleep(0.05)

                thumbnail_url = (
                    f"{base}/api/h3/jobs/{completed_job}/video-thumbnail"
                )
                with urllib.request.urlopen(thumbnail_url, timeout=3) as response:
                    self.assertEqual(b"thumbnail:video-v1", response.read())
                    self.assertEqual("public, max-age=3600", response.headers["cache-control"])
                self.assertEqual("1", counter.read_text())

                with urllib.request.urlopen(thumbnail_url, timeout=3) as response:
                    self.assertEqual(b"thumbnail:video-v1", response.read())
                self.assertEqual("1", counter.read_text())

                cached = paths["base"] / "thumbnail_cache" / f"{completed_job}.jpg"
                self.assertTrue(cached.is_file())
                video.write_bytes(b"video-v2")
                newer = cached.stat().st_mtime + 2
                os.utime(video, (newer, newer))
                with urllib.request.urlopen(thumbnail_url, timeout=3) as response:
                    self.assertEqual(b"thumbnail:video-v2", response.read())
                self.assertEqual("2", counter.read_text())

                with self.assertRaises(urllib.error.HTTPError) as rejected:
                    urllib.request.urlopen(
                        f"{base}/api/h3/jobs/{running_job}/video-thumbnail",
                        timeout=3,
                    )
                self.assertEqual(404, rejected.exception.code)
                route_source = (project_root / "web/server.mjs").read_text(
                    encoding="utf-8"
                ).split("const h3VideoThumbnail =", 1)[1].split(
                    "const h3Video =", 1
                )[0]
                self.assertIn("serveH3VideoThumbnail", route_source)
                self.assertNotIn("python('h3_video'", route_source)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=3)
                for stream in (process.stdout, process.stderr):
                    if stream is not None and not stream.closed:
                        stream.close()

    def test_project_test_set_is_created_without_queue_then_queues_every_clip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            test_set = h3_queue.create_project_test_set(root, {"project_id": "dragon"})
            self.assertEqual("ready_to_queue", test_set["status"])
            self.assertEqual("project", test_set["scope"])
            self.assertIsNone(test_set["scene_id"])
            self.assertEqual(2, test_set["scene_count"])
            self.assertEqual(2, test_set["clip_count"])
            self.assertEqual([], test_set["candidate_set_ids"])
            self.assertFalse((root / "runtime/h3/jobs").exists())

            duplicate = h3_queue.create_project_test_set(root, {"project_id": "dragon"})
            self.assertTrue(duplicate["already_exists"])
            self.assertEqual(test_set["project_test_set_id"], duplicate["project_test_set_id"])

            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=({}, [], {"workflow_profile_id": "w", "workflow_filename": "h3.json"}),
            ):
                queued = h3_queue.queue_project_test_set(root, test_set["project_test_set_id"], {
                    "adapter_id": "a", "candidate_count": 1, "seed": -1,
                })
            self.assertEqual("queued", queued["status"])
            self.assertEqual(2, len(queued["candidate_set_ids"]))
            self.assertEqual(2, queued["job_count"])
            state = h3_queue.state(root)
            self.assertEqual(test_set["project_test_set_id"], state["project_test_sets"][0]["project_test_set_id"])
            for candidate_set_id in queued["candidate_set_ids"]:
                candidate = next(row for row in state["candidate_sets"] if row["candidate_set_id"] == candidate_set_id)
                self.assertEqual(test_set["project_test_set_id"], candidate["project_test_set_id"])

    def test_r2v_prompt_project_delete_blocks_dependencies_then_removes_source_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            project = next(
                row
                for row in h3_prompt_projects.list_projects(root)["projects"]
                if row["project_id"] == "dragon"
            )
            self.assertTrue(project["deletable"])

            registration = h3_queue.create_project_test_set(
                root, {"project_id": "dragon"}
            )
            with self.assertRaisesRegex(ValueError, "테스트 세트"):
                h3_queue.delete_prompt_project(root, "dragon")
            h3_queue.delete_project_test_set(
                root, registration["project_test_set_id"]
            )

            paths = h3_queue.roots(root)
            set_id, job_id = "h3set_project_delete", "h3job_project_delete"
            atomic_write_json(
                paths["candidate_sets"] / set_id / "candidate_set.json",
                {
                    "candidate_set_id": set_id,
                    "source_project_id": "dragon",
                    "candidate_job_ids": [job_id],
                    "status": "generating",
                },
            )
            atomic_write_json(
                paths["jobs"] / job_id / "status.json",
                {"job_id": job_id, "status": "queued"},
            )
            with self.assertRaisesRegex(ValueError, "후보 큐"):
                h3_queue.delete_prompt_project(root, "dragon")
            update_status(paths["jobs"] / job_id, "cancelled")

            deleted = h3_queue.delete_prompt_project(root, "dragon")
            self.assertTrue(deleted["deleted"])
            self.assertFalse(deleted["recoverable"])
            self.assertTrue(deleted["candidate_results_preserved"])
            self.assertGreater(deleted["deleted_file_count"], 0)
            self.assertFalse((root / "prompt_projects/dragon").exists())
            self.assertTrue(
                (paths["candidate_sets"] / set_id / "candidate_set.json").is_file()
            )
            with self.assertRaises(FileNotFoundError):
                h3_queue.delete_prompt_project(root, "dragon")

    def test_prompt_project_delete_protects_templates_and_rejects_i2v_page_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = root / "prompt_projects/H3_PROJECT_TEMPLATE"
            template.mkdir(parents=True)
            (template / "manifest.json").write_text(
                json.dumps({"project_kind": "h3_r2v_production"}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "템플릿"):
                h3_queue.delete_prompt_project(root, "H3_PROJECT_TEMPLATE")

            i2v = root / "prompt_projects/i2v_only"
            i2v.mkdir(parents=True)
            (i2v / "manifest.json").write_text(
                json.dumps({"project_kind": "h3_i2v_production"}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "I2V"):
                h3_queue.delete_prompt_project(root, "i2v_only")

    def test_prompt_project_delete_blocks_cross_project_asset_references(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "prompt_projects/source"
            dependent = root / "prompt_projects/dependent"
            source.mkdir(parents=True)
            dependent.mkdir(parents=True)
            (source / "manifest.json").write_text(
                json.dumps({"project_kind": "h3_r2v_production"}),
                encoding="utf-8",
            )
            (dependent / "manifest.json").write_text(
                json.dumps({
                    "project_kind": "h3_r2v_production",
                    "asset_source_project": "source",
                }),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "독립화"):
                h3_queue.delete_prompt_project(root, "source")

    def test_project_test_set_soft_delete_tombstones_history_and_allows_reregister(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            first = h3_queue.create_project_test_set(
                root, {"project_id": "dragon"}
            )

            first_clip = (
                root
                / "prompt_projects/dragon/SCENE_001/CLIP_001.md"
            )
            first_clip.write_text(
                first_clip.read_text(encoding="utf-8").replace(
                    "Dragon action 1", "Dragon action 101"
                ),
                encoding="utf-8",
            )
            second = h3_queue.create_project_test_set(
                root, {"project_id": "dragon"}
            )
            self.assertNotEqual(
                first["project_test_set_id"], second["project_test_set_id"]
            )
            self.assertEqual(2, len(h3_queue.list_project_test_sets(root)))

            marker_root = root / "runtime/h3/project_test_sets"
            sentinel_paths = []
            for marker in (first, second):
                sentinel = (
                    marker_root
                    / marker["project_test_set_id"]
                    / "preserved.txt"
                )
                sentinel.write_text(
                    f"preserve:{marker['project_test_set_id']}",
                    encoding="utf-8",
                )
                sentinel_paths.append(sentinel)
            project_files = {
                path.relative_to(root): path.read_bytes()
                for path in (root / "prompt_projects/dragon").rglob("*")
                if path.is_file()
            }

            deleted = h3_queue.delete_project_test_set(
                root, second["project_test_set_id"]
            )
            self.assertTrue(deleted["deleted"])
            self.assertTrue(deleted["soft_deleted"])
            self.assertFalse(deleted["already_deleted"])
            self.assertEqual(2, deleted["newly_tombstoned_count"])
            self.assertEqual(
                {first["project_test_set_id"], second["project_test_set_id"]},
                set(deleted["tombstoned_project_test_set_ids"]),
            )
            for key in (
                "sessions_preserved",
                "results_preserved",
                "assets_preserved",
                "queues_preserved",
                "files_preserved",
            ):
                self.assertTrue(deleted[key])
            self.assertEqual([], h3_queue.list_project_test_sets(root))
            self.assertEqual([], h3_queue.state(root)["project_test_sets"])
            for marker, sentinel in zip((first, second), sentinel_paths):
                marker_path = (
                    marker_root
                    / marker["project_test_set_id"]
                    / "project_test_set.json"
                )
                payload = read_json(marker_path, {})
                self.assertTrue(marker_path.is_file())
                self.assertTrue(payload["deleted"])
                self.assertEqual("deleted", payload["status"])
                self.assertEqual("ready_to_queue", payload["status_before_delete"])
                self.assertTrue(payload["deleted_at"])
                self.assertEqual(
                    f"preserve:{marker['project_test_set_id']}",
                    sentinel.read_text(encoding="utf-8"),
                )
            self.assertEqual(project_files, {
                path.relative_to(root): path.read_bytes()
                for path in (root / "prompt_projects/dragon").rglob("*")
                if path.is_file()
            })

            duplicate = h3_queue.delete_project_test_set(
                root, first["project_test_set_id"]
            )
            self.assertTrue(duplicate["already_deleted"])
            self.assertEqual(0, duplicate["newly_tombstoned_count"])
            self.assertEqual([], h3_queue.list_project_test_sets(root))

            replacement = h3_queue.create_project_test_set(
                root, {"project_id": "dragon"}
            )
            self.assertNotIn(
                replacement["project_test_set_id"],
                {first["project_test_set_id"], second["project_test_set_id"]},
            )
            self.assertEqual(
                second["source_signature"], replacement["source_signature"]
            )
            self.assertFalse(replacement.get("already_exists", False))
            visible = h3_queue.state(root)["project_test_sets"]
            self.assertEqual(
                [replacement["project_test_set_id"]],
                [row["project_test_set_id"] for row in visible],
            )
            self.assertEqual(3, len(list(marker_root.glob("*/project_test_set.json"))))

            stale_retry = h3_queue.delete_project_test_set(
                root, first["project_test_set_id"]
            )
            self.assertTrue(stale_retry["already_deleted"])
            self.assertEqual(0, stale_retry["newly_tombstoned_count"])
            self.assertEqual(
                [replacement["project_test_set_id"]],
                [
                    row["project_test_set_id"]
                    for row in h3_queue.list_project_test_sets(root)
                ],
            )

    def test_project_test_set_delete_is_scope_specific_and_protects_official_suite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            project_set = h3_queue.create_project_test_set(
                root, {"project_id": "dragon"}
            )
            scene_set = h3_queue.create_project_test_set(root, {
                "project_id": "dragon",
                "scene_id": "SCENE_001",
            })

            h3_queue.delete_project_test_set(
                root, project_set["project_test_set_id"]
            )
            visible = h3_queue.list_project_test_sets(root)
            self.assertEqual(
                [scene_set["project_test_set_id"]],
                [row["project_test_set_id"] for row in visible],
            )
            self.assertEqual("scene", visible[0]["scope"])

            official_id = "official_project_marker"
            official_dir = (
                root / "runtime/h3/project_test_sets" / official_id
            )
            official_dir.mkdir(parents=True)
            official_payload = {
                "schema_version": 2,
                "project_test_set_id": official_id,
                "project_id": model_test_r2v.DRAGON_SEASON_1_PROJECT_ID,
                "scope": "project",
                "scene_id": None,
                "status": "ready_to_queue",
            }
            atomic_write_json(
                official_dir / "project_test_set.json", official_payload
            )
            with self.assertRaisesRegex(ValueError, "기본 제공 세트"):
                h3_queue.delete_project_test_set(root, official_id)
            self.assertEqual(
                official_payload,
                read_json(official_dir / "project_test_set.json", {}),
            )

    def test_scene_candidate_queue_uses_selected_workflow_count_and_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            self._write_clip(
                root,
                scene_id="SCENE_001",
                clip_id="CLIP_003",
                sequence=3,
            )
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(
                    {"1": {"class_type": "LoadImage", "inputs": {"image": "placeholder"}}},
                    [{"node_id": "1", "input": "image"}],
                    {"workflow_profile_id": "workflow_h3", "workflow_filename": "h3.json"},
                ),
            ):
                result = h3_queue.enqueue_scene_candidate_sets(root, {
                    "project_id": "dragon",
                    "scene_id": "SCENE_001",
                    "adapter_id": "adapter_h3",
                    "candidate_count": 2,
                    "width": 832,
                    "height": 480,
                    "seed": -1,
                })
            self.assertEqual(2, result["clip_count"])
            self.assertEqual(2, result["candidate_count"])
            self.assertEqual(4, result["job_count"])
            self.assertEqual((832, 480), (result["width"], result["height"]))
            self.assertEqual(2, len(result["candidate_set_ids"]))
            self.assertFalse((root / "runtime/h3/project_test_sets").exists())
            source_clip_ids = set()
            state = h3_queue.state(root)
            for candidate_set_id in result["candidate_set_ids"]:
                candidate = next(
                    row for row in state["candidate_sets"]
                    if row["candidate_set_id"] == candidate_set_id
                )
                self.assertIsNone(candidate["project_test_set_id"])
            for job_id in result["job_ids"]:
                request = read_json(root / "runtime/h3/jobs" / job_id / "request.json")
                self.assertEqual("SCENE_001", request["source_scene_id"])
                source_clip_ids.add(request["source_clip_id"])
                self.assertIsNone(request["project_test_set_id"])
                self.assertEqual((832, 480), (request["width"], request["height"]))
                self.assertGreaterEqual(request["seed"], 0)
            self.assertEqual({"CLIP_001", "CLIP_003"}, source_clip_ids)

    def test_scene_candidate_queue_preflight_prevents_partial_registration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            self._write_clip(
                root,
                scene_id="SCENE_001",
                clip_id="CLIP_003",
                sequence=3,
            )
            compiled = (
                {"1": {"class_type": "LoadImage", "inputs": {"image": "placeholder"}}},
                [{"node_id": "1", "input": "image"}],
                {"workflow_profile_id": "workflow_h3", "workflow_filename": "h3.json"},
            )
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                side_effect=[compiled, ValueError("참조 이미지는 1~5장이어야 합니다.")],
            ) as compile_mock:
                with self.assertRaisesRegex(ValueError, "아무 후보군도 등록하지 않았습니다"):
                    h3_queue.enqueue_scene_candidate_sets(root, {
                        "project_id": "dragon",
                        "scene_id": "SCENE_001",
                        "adapter_id": "adapter_h3",
                        "candidate_count": 3,
                        "width": 832,
                        "height": 480,
                    })
            self.assertEqual(2, compile_mock.call_count)
            self.assertFalse((root / "runtime/h3/candidate_sets").exists())

    def test_scene_candidate_queue_uses_single_project_prompt_for_every_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            request_root = h3_queue.roots(root)["prompt_revision_requests"]
            for round_number, request_id, letters in (
                (2, "revision_v2", ("D", "E", "F")),
                (3, "revision_v3", ("G", "H", "I")),
            ):
                directory = request_root / request_id
                directory.mkdir(parents=True)
                atomic_write_json(directory / "request.json", {
                    "prompt_revision_request_id": request_id,
                    "source_project_id": "dragon",
                    "source_scene_id": "SCENE_002",
                    "source_clip_id": "CLIP_002",
                    "next_candidate_round": round_number,
                    "updated_at": f"2026-08-15T00:0{round_number}:00+00:00",
                })
                atomic_write_json(directory / "authored_variants.json", {
                    "prompt_variants": [
                        {
                            "variant_id": letter,
                            "label": f"latest {letter}",
                            "rationale": "complete feedback rewrite",
                            "video_prompt": self._full_prompt(
                                f"new round {round_number} prompt {letter}"
                            ),
                        }
                        for letter in letters
                    ],
                })

            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                return_value=(
                    {"1": {"class_type": "LoadImage", "inputs": {"image": "placeholder"}}},
                    [{"node_id": "1", "input": "image"}],
                    {"workflow_profile_id": "workflow_h3", "workflow_filename": "h3.json"},
                ),
            ):
                result = h3_queue.enqueue_scene_candidate_sets(root, {
                    "project_id": "dragon",
                    "scene_id": "SCENE_002",
                    "adapter_id": "adapter_h3",
                    "candidate_count": 3,
                    "width": 832,
                    "height": 480,
                    "seed": -1,
                })

            self.assertEqual(3, result["job_count"])
            self.assertEqual([{
                "clip_id": "CLIP_002",
                "source": "project_prompt",
            }], result["prompt_sources"])
            requests = [
                read_json(root / "runtime/h3/jobs" / job_id / "request.json")
                for job_id in result["job_ids"]
            ]
            self.assertEqual(
                [1, 2, 3],
                [row["candidate_index"] for row in requests],
            )
            self.assertEqual(
                [self._full_prompt("Dragon action 2")] * 3,
                [row["prompt"] for row in requests],
            )
            self.assertTrue(all("clip_version" not in row for row in requests))
            self.assertTrue(all("candidate_round" not in row for row in requests))
            self.assertTrue(all("prompt_variant_id" not in row for row in requests))

    def test_scene_test_set_dispatch_is_scene_scoped_deduplicated_and_job_free(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_project(root)
            self._write_clip(
                root,
                scene_id="SCENE_001",
                clip_id="CLIP_003",
                sequence=3,
            )

            scene_test_set = h3_queue.create_project_test_set(root, {
                "project_id": "dragon",
                "scene_id": "SCENE_001",
            })
            self.assertEqual("scene", scene_test_set["scope"])
            self.assertEqual("SCENE_001", scene_test_set["scene_id"])
            self.assertEqual(["CLIP_001", "CLIP_003"], scene_test_set["clip_ids"])
            self.assertEqual(2, scene_test_set["clip_count"])
            self.assertFalse((root / "runtime/h3/jobs").exists())

            duplicate = h3_queue.create_project_test_set(root, {
                "project_id": "dragon",
                "scene_id": "SCENE_001",
            })
            self.assertTrue(duplicate["already_exists"])
            self.assertEqual(
                scene_test_set["project_test_set_id"],
                duplicate["project_test_set_id"],
            )
            other_scene = h3_queue.create_project_test_set(root, {
                "project_id": "dragon",
                "scene_id": "SCENE_002",
            })
            project_test_set = h3_queue.create_project_test_set(
                root, {"project_id": "dragon"}
            )
            self.assertEqual(3, project_test_set["clip_count"])
            self.assertEqual(3, len({
                scene_test_set["project_test_set_id"],
                other_scene["project_test_set_id"],
                project_test_set["project_test_set_id"],
            }))

    def test_h3_worker_records_r2v_benchmark_result(self):
        class Client:
            def __init__(self):
                self.history_calls = 0

            def health(self):
                return {}

            def upload_image(self, *, filename, content, subfolder, overwrite=True):
                return {"name": filename, "subfolder": subfolder, "type": "input"}

            def queue_prompt(self, workflow):
                return {"prompt_id": "prompt-1"}

            def get_queue(self):
                return {"queue_running": [], "queue_pending": []}

            def get_history(self, prompt_id):
                self.history_calls += 1
                if self.history_calls == 1:
                    raise h3_worker.requests.ReadTimeout("temporary ComfyUI delay")
                return {prompt_id: {"outputs": {}}}

            def _raise_on_execution_error(self, item):
                return None

            def extract_output_files(self, history, prompt_id):
                return [{"filename": "video.mp4", "subfolder": "h3", "type": "output"}]

            def download_file_to_path(self, output, target):
                path = Path(target)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"video")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = h3_queue.roots(root)
            job_id, queue_id = "h3bench_case_1", "h3testq_demo"
            job_dir = paths["jobs"] / job_id
            job_dir.mkdir(parents=True)
            image = root / "picture.png"
            image.write_bytes(b"picture")
            request = {
                "job_id": job_id, "job_type": "h3_r2v_benchmark", "queue_name": "h3_generation",
                "test_queue_id": queue_id, "test_session_id": "session-1", "run_id": "run-1",
                "references": [{"source_path": str(image), "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}],
                "reference_patches": [{"node_id": "1", "input": "image"}],
            }
            atomic_write_json(job_dir / "request.json", request)
            atomic_write_json(job_dir / "workflow_api.json", {"1": {"class_type": "LoadImage", "inputs": {"image": "placeholder"}}})
            atomic_write_json(job_dir / "manifest.json", {"job_id": job_id, "status": "queued", "outputs": []})
            update_status(job_dir, "queued")
            queue_dir = paths["test_queues"] / queue_id
            queue_dir.mkdir(parents=True)
            atomic_write_json(queue_dir / "queue.json", {"test_queue_id": queue_id, "status": "queued", "job_ids": [job_id]})
            client = Client()
            with mock.patch.object(h3_worker, "ROOT", root), mock.patch.object(h3_worker, "PATHS", paths), mock.patch.object(h3_worker, "POLL_SECONDS", 0), mock.patch.object(h3_worker, "_ensure_client", return_value=client), mock.patch.object(h3_worker.benchmark_jobs, "record_result") as record:
                h3_worker.process_job(job_dir)
            self.assertEqual("completed", read_json(job_dir / "status.json")["status"])
            self.assertEqual(2, client.history_calls)
            self.assertTrue(Path(read_json(job_dir / "manifest.json")["local_video_path"]).is_file())
            record.assert_called_once()
            self.assertEqual("completed", record.call_args.kwargs["status"])
            self.assertEqual("completed", h3_queue.reconcile_test_queues(root, queue_id)[0]["status"])

    def test_h3_worker_waits_for_existing_comfy_work_before_submission(self):
        class Client:
            def __init__(self):
                self.calls = 0

            def get_queue(self):
                self.calls += 1
                if self.calls == 1:
                    return {"queue_running": [[1, "existing-prompt"]], "queue_pending": [[2, "waiting-prompt"]]}
                return {"queue_running": [], "queue_pending": []}

        with tempfile.TemporaryDirectory() as temp:
            job_dir = Path(temp) / "job"
            update_status(job_dir, "preparing")
            client = Client()
            with mock.patch.object(h3_worker, "POLL_SECONDS", 0), mock.patch.object(h3_worker, "STOP_REQUESTED", False), mock.patch.object(h3_worker, "_worker_status"):
                h3_worker._wait_for_comfy_submission_slot(
                    job_dir,
                    client,
                    label="H3 R2V 생성",
                )
            self.assertEqual(2, client.calls)
            status = read_json(job_dir / "status.json")
            self.assertEqual("preparing", status["status"])
            self.assertEqual(1, status["comfy_running_count"])
            self.assertEqual(1, status["comfy_pending_count"])

    def test_force_stop_group_cancels_pending_requests_active_and_preserves_completed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = h3_queue.roots(root)
            group_id = "h3set_force_stop"
            job_states = {
                "job_queued": "queued",
                "job_running": "running",
                "job_completed": "completed",
            }
            for job_id, status in job_states.items():
                job_dir = paths["jobs"] / job_id
                job_dir.mkdir(parents=True)
                atomic_write_json(job_dir / "request.json", {
                    "job_id": job_id,
                    "job_type": "h3_r2v_benchmark",
                    "run_id": f"run_{job_id}",
                    "test_session_id": "session-force-stop",
                    "comfy_url": "http://comfy.test",
                })
                manifest = {"job_id": job_id, "status": status}
                if status == "running":
                    manifest["prompt_id"] = "prompt-running"
                atomic_write_json(job_dir / "manifest.json", manifest)
                update_status(job_dir, status, prompt_id=manifest.get("prompt_id"))
            group_dir = paths["candidate_sets"] / group_id
            group_dir.mkdir(parents=True)
            atomic_write_json(group_dir / "candidate_set.json", {
                "candidate_set_id": group_id,
                "status": "generating",
                "candidate_job_ids": list(job_states),
            })

            with mock.patch.object(h3_queue.ComfyClient, "cancel_prompt", return_value={"running_interrupted": True}) as cancel, mock.patch("benchmark_jobs.record_result") as record_result:
                result = h3_queue.force_stop_group(root, group_id)

            self.assertEqual(["job_queued"], result["cancelled_job_ids"])
            self.assertEqual(["job_running"], result["cancel_requested_job_ids"])
            self.assertEqual("cancelled", read_json(paths["jobs"] / "job_queued" / "status.json")["status"])
            running = read_json(paths["jobs"] / "job_running" / "status.json")
            self.assertEqual("running", running["status"])
            self.assertTrue(running["cancel_requested"])
            self.assertEqual("completed", read_json(paths["jobs"] / "job_completed" / "status.json")["status"])
            self.assertEqual("cancelling", read_json(group_dir / "candidate_set.json")["status"])
            cancel.assert_called_once_with("prompt-running")
            record_result.assert_called_once()
            self.assertEqual("cancelled", record_result.call_args.kwargs["status"])
            self.assertEqual(1, result["benchmark_cancelled_count"])

    def test_queued_only_force_stop_skips_group_after_any_job_starts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = h3_queue.roots(root)
            group_id = "h3set_page_guard"
            for job_id, status in {
                "job_waiting": "queued",
                "job_started": "running",
            }.items():
                job_dir = paths["jobs"] / job_id
                job_dir.mkdir(parents=True)
                atomic_write_json(job_dir / "request.json", {"job_id": job_id})
                atomic_write_json(job_dir / "manifest.json", {
                    "job_id": job_id,
                    "status": status,
                })
                update_status(job_dir, status)
            group_dir = paths["candidate_sets"] / group_id
            group_dir.mkdir(parents=True)
            atomic_write_json(group_dir / "candidate_set.json", {
                "candidate_set_id": group_id,
                "status": "generating",
                "candidate_job_ids": ["job_waiting", "job_started"],
            })

            result = h3_queue.force_stop_group(
                root,
                group_id,
                queued_only=True,
            )

            self.assertEqual("skipped_running", result["status"])
            self.assertEqual(["job_started"], result["running_job_ids"])
            self.assertEqual([], result["cancelled_job_ids"])
            self.assertEqual(
                "queued",
                read_json(paths["jobs"] / "job_waiting" / "status.json")["status"],
            )
            self.assertFalse(
                (read_json(group_dir / "candidate_set.json") or {}).get(
                    "cancel_requested"
                )
            )

    def test_h3_worker_stops_before_work_when_group_cancel_is_requested(self):
        with tempfile.TemporaryDirectory() as temp:
            job_dir = Path(temp) / "job_cancelled"
            job_dir.mkdir()
            atomic_write_json(job_dir / "request.json", {
                "job_id": job_dir.name,
                "job_type": "h3_r2v_generate",
                "queue_name": "h3_generation",
            })
            atomic_write_json(job_dir / "workflow_api.json", {"1": {"inputs": {}}})
            update_status(job_dir, "preparing", cancel_requested=True)
            with self.assertRaises(h3_worker.H3JobCancelled):
                h3_worker.process_job(job_dir)

    def test_three_prompt_variants_create_independent_jobs_and_restore_version(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")
            variants = [
                {
                    "variant_id": letter,
                    "label": label,
                    "rationale": f"{letter} reason",
                    "video_prompt": f"detailed_description:\n[{letter}] independent action.\n\noverall_soundscape:\nWind.",
                }
                for letter, label in zip(
                    ("A", "B", "C"),
                    ("사건 명료도", "긴장과 규모", "동작과 카메라"),
                )
            ]
            with mock.patch.object(
                h3_queue,
                "_compile_workflow",
                side_effect=lambda _r, _a, values, _c, expected=None, _settings=None: (
                    {"1": {"inputs": {"prompt": values["prompt"], "seed": values["seed"]}}},
                    [],
                    {
                        "workflow_profile_id": "w",
                        "workflow_filename": "h3.json",
                        "generation_mode": expected or "r2v",
                        "workflow_settings": {},
                    },
                ),
            ), mock.patch.object(
                h3_queue.secrets, "randbits", side_effect=[101, 202, 303]
            ):
                candidate = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a",
                    "prompt_variants": variants,
                    "references": [{"upload_path": str(image)}],
                    "seed": -1,
                    "source_project_id": "dragon",
                    "source_scene_id": "EP00-S01",
                    "source_clip_id": "EP00-S01-NC01",
                })
            requests = [
                read_json(h3_queue.roots(root)["jobs"] / job_id / "request.json")
                for job_id in candidate["candidate_job_ids"]
            ]
            self.assertTrue(candidate["independent_prompts"])
            self.assertEqual(1, candidate["clip_version"])
            self.assertEqual(["A", "B", "C"], [row["prompt_variant_id"] for row in requests])
            self.assertEqual([101, 202, 303], [row["seed"] for row in requests])
            self.assertEqual(3, len({row["prompt"] for row in requests}))

            paths = h3_queue.roots(root)
            for job_id in candidate["candidate_job_ids"]:
                update_status(paths["jobs"] / job_id, "completed", stage="done")
            h3_queue.select_candidate(root, candidate["candidate_set_id"], candidate["candidate_job_ids"][1])
            restored = h3_queue.restore_candidate_version(root, candidate["candidate_set_id"])
            self.assertNotEqual(candidate["candidate_set_id"], restored["candidate_set_id"])
            self.assertEqual(2, restored["clip_version"])
            self.assertEqual("version_restore", restored["render_purpose"])
            self.assertEqual(candidate["candidate_job_ids"], restored["candidate_job_ids"])
            self.assertEqual(candidate["candidate_job_ids"][1], restored["selected_job_id"])

    def test_feedback_revision_saves_only_then_codex_prompts_can_be_applied(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "character.png"
            image.write_bytes(b"image")

            def full_prompt(direction):
                return f"""subject_definitions:
<Subject 1> is Lua from <Picture 1>. Preserve her exact identity and clothing.

summary:
[reference generation] <Subject 1> braces, evades one strike, and answers aloud.

retention_analysis:
<Subject 1> (appears in [Shot 1], [Shot 2]): fully_preserved - Retain her exact identity and clothing.

detailed_description:
[Shot 1] A locked wide view frames <Subject 1> Lua bracing while {direction}.

[Shot 2] At 00:02.000, a medium tracking view follows <Subject 1> Lua as she evades the strike without stopping, turns her shoulders toward the attacker, and shouts <Subject 1> (S1) <d>[Korean]비켜!</d> while driving the spear forward.

overall_soundscape:
Wind, footsteps, and one impact.

non_diegetic_music:
Low tense strings."""

            variants = [
                {
                    "variant_id": letter,
                    "label": f"candidate {letter}",
                    "video_prompt": full_prompt(f"source direction {letter}"),
                }
                for letter in ("A", "B", "C")
            ]
            compiled = lambda _r, _a, values, _c, expected=None, _settings=None: (
                {"1": {"inputs": dict(values)}}, [],
                {
                    "workflow_profile_id": "w", "workflow_filename": "h3.json",
                    "generation_mode": expected or "r2v", "workflow_settings": {},
                },
            )
            with mock.patch.object(h3_queue, "_compile_workflow", side_effect=compiled):
                source = h3_queue.enqueue_candidate_set(root, {
                    "adapter_id": "a", "prompt_variants": variants,
                    "references": [{"upload_path": str(image), "role": "lua"}],
                    "source_project_id": "dragon", "source_scene_id": "EP00-S01",
                    "source_clip_id": "EP00-S01-NC01", "width": 608, "height": 352,
                })
                paths = h3_queue.roots(root)
                for job_id in source["candidate_job_ids"]:
                    update_status(paths["jobs"] / job_id, "completed", stage="done")
                job_count_before = len(list(paths["jobs"].iterdir()))
                with mock.patch.dict(
                    os.environ, {"H3_PROMPT_REVISION_REMOTE_URL": ""}
                ):
                    saved = h3_queue.save_prompt_revision_request(
                        root, source["candidate_set_id"],
                        {"feedback": "회피를 빠르게 하고 적의 크기를 더 크게 보여줘."},
                    )
                self.assertEqual("awaiting_codex_authoring", saved["status"])
                self.assertEqual("codex_conversation", saved["authoring_mode"])
                self.assertIs(saved["local_model_execution"], False)
                self.assertEqual(["D", "E", "F"], saved["expected_variant_ids"])
                self.assertEqual(0, saved["jobs_created"])
                self.assertEqual(job_count_before, len(list(paths["jobs"].iterdir())))
                self.assertEqual(
                    saved["prompt_revision_request_id"],
                    h3_queue.state(root)["prompt_revision_requests"][0]["prompt_revision_request_id"],
                )

                updated = h3_queue.save_prompt_revision_request(
                    root, source["candidate_set_id"],
                    {"feedback": "회피 속도와 적의 압도적인 체급 차이를 더 분명하게 보여줘."},
                )
                self.assertEqual(saved["prompt_revision_request_id"], updated["prompt_revision_request_id"])
                self.assertTrue(updated["feedback_updated"])

                authored = [
                    {
                        "variant_id": letter,
                        "label": f"revision {letter}",
                        "rationale": "피드백 반영",
                        "video_prompt": full_prompt(f"Codex-authored direction {letter}"),
                    }
                    for letter in ("D", "E", "F")
                ]
                revised = h3_queue.apply_authored_prompt_revision(
                    root,
                    saved["prompt_revision_request_id"],
                    {"prompt_variants": authored},
                )
            self.assertEqual(2, revised["candidate_round"])
            self.assertEqual(2, revised["clip_version"])
            self.assertEqual(source["candidate_set_id"], revised["parent_candidate_set_id"])
            self.assertEqual(["D", "E", "F"], [row["variant_id"] for row in revised["prompt_variants"]])
            self.assertEqual(3, len(revised["candidate_job_ids"]))
            applied = read_json(
                paths["prompt_revision_requests"]
                / saved["prompt_revision_request_id"]
                / "request.json"
            )
            self.assertEqual("applied_and_queued", applied["status"])
            self.assertEqual("codex_conversation", applied["authored_by"])
            self.assertEqual(revised["candidate_set_id"], applied["result_candidate_set_id"])

            atomic_write_json(
                paths["prompt_revision_requests"]
                / saved["prompt_revision_request_id"]
                / "authored_variants.json",
                {"prompt_variants": authored},
            )
            listed = h3_queue.list_prompt_revision_requests(root)[0]
            self.assertTrue(listed["authored_draft_available"])
            self.assertEqual(
                ["D", "E", "F"], listed["authored_variant_ids"]
            )
            self.assertEqual(3, len(listed["authored_prompt_variants"]))
            self.assertFalse(listed["result_candidate_set_deleted"])

            stopped = h3_queue.force_stop_group(
                root, revised["candidate_set_id"]
            )
            self.assertEqual(3, len(stopped["cancelled_job_ids"]))
            h3_queue.delete_candidate_set(root, revised["candidate_set_id"])
            listed = h3_queue.list_prompt_revision_requests(root)[0]
            self.assertTrue(listed["result_candidate_set_deleted"])
            self.assertEqual("deleted", listed["result_candidate_set_status"])
            self.assertEqual(2, listed["result_clip_version"])
            self.assertEqual(2, listed["result_candidate_round"])

            with mock.patch.dict(
                os.environ,
                {"H3_PROMPT_REVISION_REMOTE_URL": "http://100.78.202.37:8765"},
            ):
                remote = h3_queue.save_prompt_revision_request(
                    root,
                    source["candidate_set_id"],
                    {"feedback": "이번 수정은 원격 Codex API에서 작성해줘."},
                )
            self.assertEqual("awaiting_remote_authoring", remote["status"])
            self.assertEqual("remote_codex_api", remote["authoring_mode"])
            self.assertEqual(0, remote["remote_attempts"])


if __name__ == "__main__":
    unittest.main()
