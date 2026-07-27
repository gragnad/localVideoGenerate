from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import ui_backend
from job_queue import atomic_write_json


class SourceImageLibraryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.jobs = self.root / "jobs"
        self.jobs.mkdir()
        self.originals = {"ROOT": ui_backend.ROOT, "JOBS": ui_backend.JOBS}
        ui_backend.ROOT = self.root
        ui_backend.JOBS = self.jobs

    def tearDown(self):
        for key, value in self.originals.items():
            setattr(ui_backend, key, value)
        self.temp.cleanup()

    def write_job(self, job_id: str, image_name: str, image_bytes: bytes, created_at: str):
        job_dir = self.jobs / job_id
        source_dir = job_dir / "source_images"
        source_dir.mkdir(parents=True)
        stored = f"01_{image_name}"
        path = source_dir / stored
        path.write_bytes(image_bytes)
        atomic_write_json(
            job_dir / "request.json",
            {
                "created_at": created_at,
                "segments": [
                    {
                        "original_name": image_name,
                        "stored_name": stored,
                        "source_path": str(path),
                        "sha256": hashlib.sha256(image_bytes).hexdigest(),
                        "prompt": "scene",
                        "seconds": 5,
                        "order": 1,
                    }
                ],
            },
        )

    def test_library_dedupes_by_sha256(self):
        data = b"shared-image-bytes"
        self.write_job("job_a", "hero.png", data, "2026-07-26T10:00:00+09:00")
        self.write_job("job_b", "hero-copy.png", data, "2026-07-26T11:00:00+09:00")

        payload = ui_backend.source_image_library_action({})
        images = payload["images"]

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["ref_count"], 2)
        self.assertEqual(images[0]["latest_job_id"], "job_b")
        self.assertEqual(images[0]["size_bytes"], len(data))

    def test_source_image_file_action_returns_existing_path(self):
        data = b"preview-image"
        self.write_job("job_preview", "preview.png", data, "2026-07-26T12:00:00+09:00")
        digest = hashlib.sha256(data).hexdigest()

        out = ui_backend.source_image_file_action({"sha256": digest})

        self.assertTrue(Path(out["path"]).is_file())
        self.assertEqual(Path(out["path"]).read_bytes(), data)

    def test_delete_source_image_removes_all_copies(self):
        data = b"delete-me"
        self.write_job("job_one", "one.png", data, "2026-07-26T09:00:00+09:00")
        self.write_job("job_two", "two.png", data, "2026-07-26T10:00:00+09:00")
        digest = hashlib.sha256(data).hexdigest()
        paths = [
            self.jobs / "job_one" / "source_images" / "01_one.png",
            self.jobs / "job_two" / "source_images" / "01_two.png",
        ]
        for path in paths:
            self.assertTrue(path.is_file())

        out = ui_backend.delete_source_image_action({"sha256": digest})

        self.assertTrue(out["deleted"])
        self.assertEqual(out["deleted_files"], 2)
        for path in paths:
            self.assertFalse(path.exists())
        self.assertEqual(ui_backend.source_image_library_action({})["images"], [])

    def test_source_image_preview_creates_cached_jpeg(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        import io

        buffer = io.BytesIO()
        Image.new("RGB", (800, 450), color=(20, 40, 80)).save(buffer, format="PNG")
        data = buffer.getvalue()
        self.write_job("job_thumb", "scene.png", data, "2026-07-27T12:00:00+09:00")

        out = ui_backend.source_image_preview_action(
            {"job_id": "job_thumb", "index": 0, "max": 320}
        )
        preview = Path(out["path"])

        self.assertTrue(preview.is_file())
        self.assertEqual(preview.suffix, ".jpg")
        self.assertLess(preview.stat().st_size, len(data))
        with Image.open(preview) as image:
            self.assertLessEqual(max(image.size), 320)


if __name__ == "__main__":
    unittest.main()
