from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import h3_queue
import model_test_registry
from job_queue import read_json


def _fflf_graph() -> dict:
    """Build the FFLF I2V Turbo 8-step graph with a last-frame loader."""
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
    graph = {
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
    graph["147"] = {
        "class_type": "LoadImage",
        "inputs": {"image": "ending.png"},
    }
    graph["133"]["inputs"]["last_frame"] = ["147", 0]
    return graph


def _register_fflf(root: Path, workflows: Path) -> dict:
    """Register the H3 model + FFLF I2V adapter, return the FFLF adapter row."""
    (workflows / model_test_registry.H3_I2V_TURBO8_FFLF_WORKFLOW_FILENAME).write_text(
        json.dumps(_fflf_graph()), encoding="utf-8"
    )
    model_test_registry.register_model(root, {
        "provider": "MiniMax", "family": "H3",
        "display_name": "MiniMax H3", "version": "1",
    })
    model_test_registry.ensure_h3_i2v_adapter(root, workflows)
    adapters = [
        row for row in h3_queue.available_adapters(root)["adapters"]
        if row["generation_mode"] == "i2v" and row["supports_last_frame"]
    ]
    assert len(adapters) == 1, adapters
    return adapters[0]


class H3AvatarPortraitTests(unittest.TestCase):
    def _make_image(self, name: str, payload: bytes) -> Path:
        image = self.root / name
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(payload)
        return image

    def test_p1a_portrait_fflf_enqueue_accepts_576x1024(self):
        with tempfile.TemporaryDirectory() as temp:
            self.root = Path(temp)
            workflows = self.root / "workflows"
            workflows.mkdir()
            fflf = _register_fflf(self.root, workflows)
            image = self._make_image("base.png", b"portrait-bytes")

            candidate = h3_queue.enqueue_candidate_set(
                self.root,
                {
                    "adapter_id": fflf["adapter_id"],
                    "prompt": "The partner nods gently.",
                    "references": [
                        {"upload_path": str(image)},
                        {"upload_path": str(image)},
                    ],
                    "candidate_count": 1,
                    "generation_mode": "i2v",
                    "width": 576,
                    "height": 1024,
                    "duration_seconds": 5,
                    "queue_lane": "local_generation",
                },
            )

            self.assertEqual(1, candidate["candidate_count"])
            self.assertEqual("i2v", candidate["generation_mode"])
            self.assertEqual(576, candidate["width"])
            self.assertEqual(1024, candidate["height"])
            self.assertEqual(1, len(candidate["candidate_job_ids"]))

            job_id = candidate["candidate_job_ids"][0]
            job_dir = self.root / "runtime/h3/jobs" / job_id
            request = read_json(job_dir / "request.json")
            self.assertEqual(576, request["width"])
            self.assertEqual(1024, request["height"])
            self.assertEqual("i2v", request["generation_mode"])
            self.assertEqual(2, len(request["references"]))

            # Two reference patches: start frame (114) + last frame (147).
            self.assertEqual(
                ["114", "147"],
                [row["node_id"] for row in request["reference_patches"]],
            )

            queued = read_json(job_dir / "workflow_api.json")
            self.assertEqual(576, queued["137"]["inputs"]["value"])
            self.assertEqual(1024, queued["138"]["inputs"]["value"])
            self.assertEqual("MiniMaxH3ImageToVideo", queued["133"]["class_type"])
            self.assertEqual(["114", 0], queued["133"]["inputs"]["first_frame"])
            self.assertEqual(["147", 0], queued["133"]["inputs"]["last_frame"])
            self.assertEqual("__H3_START_IMAGE__", queued["114"]["inputs"]["image"])
            self.assertEqual("__H3_LAST_IMAGE__", queued["147"]["inputs"]["image"])

            # Both logical references point at the identical source bytes.
            refs = request["references"]
            self.assertEqual(image.read_bytes(), refs[0]["source_path"] and Path(refs[0]["source_path"]).read_bytes())
            self.assertEqual(image.read_bytes(), Path(refs[1]["source_path"]).read_bytes())
            self.assertEqual(refs[0]["sha256"], refs[1]["sha256"])

    def test_p1b_landscape_sizes_still_enqueue(self):
        for width, height in ((832, 480), (1280, 704), (1376, 768)):
            with tempfile.TemporaryDirectory() as temp:
                self.root = Path(temp)
                workflows = self.root / "workflows"
                workflows.mkdir()
                fflf = _register_fflf(self.root, workflows)
                image = self._make_image("base.png", b"landscape-bytes")
                candidate = h3_queue.enqueue_candidate_set(
                    self.root,
                    {
                        "adapter_id": fflf["adapter_id"],
                        "prompt": "The partner nods gently.",
                        "references": [{"upload_path": str(image)}],
                        "candidate_count": 1,
                        "generation_mode": "i2v",
                        "width": width,
                        "height": height,
                        "duration_seconds": 5,
                        "queue_lane": "local_generation",
                    },
                )
                self.assertEqual((width, height), (candidate["width"], candidate["height"]))

    def test_p1b_unsupported_480x832_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            self.root = Path(temp)
            workflows = self.root / "workflows"
            workflows.mkdir()
            fflf = _register_fflf(self.root, workflows)
            image = self._make_image("base.png", b"portrait-bytes")

            with self.assertRaises(ValueError) as caught:
                h3_queue.enqueue_candidate_set(
                    self.root,
                    {
                        "adapter_id": fflf["adapter_id"],
                        "prompt": "The partner nods gently.",
                        "references": [{"upload_path": str(image)}],
                        "candidate_count": 1,
                        "generation_mode": "i2v",
                        "width": 480,
                        "height": 832,
                        "duration_seconds": 5,
                        "queue_lane": "local_generation",
                    },
                )
            self.assertIn("576 × 1024", str(caught.exception))

            jobs_root = self.root / "runtime/h3/jobs"
            sets_root = self.root / "runtime/h3/candidate_sets"
            self.assertFalse(jobs_root.exists() or list(jobs_root.iterdir()) if jobs_root.exists() else False)
            self.assertFalse(sets_root.exists() or list(sets_root.iterdir()) if sets_root.exists() else False)


if __name__ == "__main__":
    unittest.main()
