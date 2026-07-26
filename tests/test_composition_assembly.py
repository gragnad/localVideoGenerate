from __future__ import annotations

import unittest
from unittest.mock import patch

import ui_backend


class CompositionAssemblyTests(unittest.TestCase):
    def test_normalized_clip_rows_enforces_limits(self):
        clips = [
            {
                "source_job_id": "job_a",
                "start_seconds": 0,
                "end_seconds": 31,
                "order": 1,
            },
            {
                "source_job_id": "job_b",
                "start_seconds": 0,
                "end_seconds": 31,
                "order": 2,
            },
        ]
        meta = {
            "source_job_id": "job_a",
            "candidate_set_id": "cset_test",
            "candidate_index": 1,
            "job_name": "job_a",
            "batch_id": "batch_test",
            "fps": 24,
            "resolution": {"width": 1280, "height": 704},
            "duration_seconds": 40.0,
            "video_url": "/api/jobs/job_a/video",
            "source_path": "/tmp/job_a.mp4",
        }

        def fake_job(job_id: str):
            return {
                "job_id": job_id,
                "dir": ui_backend.ROOT / "jobs" / job_id,
                "request": {
                    "candidate_set_id": "cset_test",
                    "candidate_index": 1 if job_id == "job_a" else 2,
                    "job_name": job_id,
                    "batch_id": "batch_test",
                    "fps": 24,
                    "resolution": {"width": 1280, "height": 704},
                },
                "manifest": {},
                "status": {"status": "completed"},
            }

        with patch.object(ui_backend, "job", side_effect=fake_job), patch.object(
            ui_backend, "source_video_path", return_value=ui_backend.ROOT / "tmp.mp4"
        ), patch.object(
            ui_backend,
            "probe_video",
            return_value={
                "duration_seconds": 40.0,
                "fps": 24,
                "width": 1280,
                "height": 704,
            },
        ):
            with self.assertRaisesRegex(ValueError, "60"):
                ui_backend._normalized_clip_rows(clips)

    def test_normalized_clip_rows_blocks_resolution_mismatch(self):
        clips = [
            {"source_job_id": "job_a", "start_seconds": 0, "end_seconds": 5, "order": 1},
            {"source_job_id": "job_b", "start_seconds": 0, "end_seconds": 5, "order": 2},
        ]

        def fake_job(job_id: str):
            width = 1280 if job_id == "job_a" else 1024
            return {
                "job_id": job_id,
                "dir": ui_backend.ROOT / "jobs" / job_id,
                "request": {
                    "candidate_set_id": "cset_test",
                    "candidate_index": 1,
                    "job_name": job_id,
                    "batch_id": "batch_test",
                    "fps": 24,
                    "resolution": {"width": width, "height": 704},
                },
                "manifest": {},
                "status": {"status": "completed"},
            }

        with patch.object(ui_backend, "job", side_effect=fake_job), patch.object(
            ui_backend, "source_video_path", return_value=ui_backend.ROOT / "tmp.mp4"
        ), patch.object(
            ui_backend,
            "probe_video",
            side_effect=lambda path: {
                "duration_seconds": 10.0,
                "fps": 24,
                "width": 1280 if "job_a" in str(path) else 1024,
                "height": 704,
            },
        ):
            with self.assertRaisesRegex(ValueError, "해상도"):
                ui_backend._normalized_clip_rows(clips)


if __name__ == "__main__":
    unittest.main()
