from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import h3_frame_export
from job_queue import atomic_write_json, update_status


ROOT = Path(__file__).resolve().parents[1]
JOB_ID = "h3job_20260930_000000_01_test"


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
class H3FrameExportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        job_dir = self.root / "runtime/h3/jobs" / JOB_ID
        job_dir.mkdir(parents=True)
        self.video = self.root / "runtime/h3/outputs/clip.mp4"
        self.video.parent.mkdir(parents=True)
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                "-i", "testsrc=size=320x176:rate=24:duration=2.1",
                "-pix_fmt", "yuv420p", str(self.video),
            ],
            check=True,
        )
        atomic_write_json(job_dir / "request.json", {
            "job_type": "h3_r2v_generate",
            "candidate_set_id": "h3set_test",
            "candidate_index": 2,
            "source_clip_id": "EP04_20",
            "seed": 7,
        })
        atomic_write_json(job_dir / "manifest.json", {"local_video_path": str(self.video)})
        update_status(job_dir, "completed", stage="done")

    def tearDown(self):
        self.temp.cleanup()

    def test_intervals_pick_exact_source_frames(self):
        expected = {
            "0.25": [0, 6, 12, 18, 24, 30, 36, 42, 48],
            "0.5": [0, 12, 24, 36, 48],
            "1": [0, 24, 48],
        }
        for interval, indices in expected.items():
            with self.subTest(interval=interval):
                out = h3_frame_export.export_frames(self.root, JOB_ID, interval)
                self.assertEqual(indices, [row["frame_index"] for row in out["frames"]])
                self.assertEqual(
                    [round(index / 24, 3) for index in indices],
                    [row["time_seconds"] for row in out["frames"]],
                )
                first = out["frames"][0]["filename"]
                self.assertEqual("EP04_20_cand2_t000.000s_f0000.png", first)
                export_dir = Path(out["export_dir"])
                for row in out["frames"]:
                    self.assertTrue((export_dir / row["filename"]).is_file())
                    self.assertTrue((export_dir / row["preview_filename"]).is_file())
                with zipfile.ZipFile(export_dir / out["zip_filename"]) as archive:
                    names = archive.namelist()
                self.assertEqual("frames.json", names[0])
                self.assertEqual([row["filename"] for row in out["frames"]], names[1:])

    def test_labeled_frames_add_caption_strip_without_covering_picture(self):
        out = h3_frame_export.export_frames(self.root, JOB_ID, "0.5")
        frame = out["frames"][2]
        self.assertEqual("EP04_20   cand2   t=1.000s   f0024", frame["label_text"])
        export_dir = Path(out["export_dir"])
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                "-of", "csv=p=0", str(export_dir / frame["labeled_filename"]),
            ],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual("320,204", probe)
        with zipfile.ZipFile(export_dir / out["labeled_zip_filename"]) as archive:
            self.assertEqual(
                [row["labeled_filename"] for row in out["frames"]],
                archive.namelist()[1:],
            )
        result = h3_frame_export.selection_zip(
            self.root, JOB_ID, "0p5s", [frame["filename"]], labeled=True,
        )
        self.assertTrue(result["labeled"])
        self.assertIn("_labeled_", result["zip_filename"])
        path = h3_frame_export.export_file(self.root, JOB_ID, "0p5s", result["zip_filename"])
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(["frames.json", frame["labeled_filename"]], archive.namelist())
        self.assertTrue(
            h3_frame_export.export_file(
                self.root, JOB_ID, "0p5s", frame["labeled_filename"]
            ).is_file()
        )

    def test_second_request_reuses_export_until_video_changes(self):
        first = h3_frame_export.export_frames(self.root, JOB_ID, 0.5)
        self.assertFalse(first["cached"])
        self.assertTrue(h3_frame_export.export_frames(self.root, JOB_ID, "0.5")["cached"])
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                "-i", "testsrc=size=320x176:rate=24:duration=1.1",
                "-pix_fmt", "yuv420p", str(self.video),
            ],
            check=True,
        )
        rebuilt = h3_frame_export.export_frames(self.root, JOB_ID, "0.5")
        self.assertFalse(rebuilt["cached"])
        self.assertEqual([0, 12, 24], [row["frame_index"] for row in rebuilt["frames"]])

    def test_selection_zip_contains_only_picked_frames_in_time_order(self):
        out = h3_frame_export.export_frames(self.root, JOB_ID, "0.25")
        picked = [out["frames"][4]["filename"], out["frames"][1]["filename"]]
        result = h3_frame_export.selection_zip(self.root, JOB_ID, "0p25s", picked)
        self.assertEqual(2, result["frame_count"])
        path = h3_frame_export.export_file(self.root, JOB_ID, "0p25s", result["zip_filename"])
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(["frames.json", *reversed(picked)], archive.namelist())
            manifest = json.loads(archive.read("frames.json"))
        self.assertEqual([6, 24], [row["frame_index"] for row in manifest["frames"]])
        with self.assertRaisesRegex(ValueError, "한 장 이상"):
            h3_frame_export.selection_zip(self.root, JOB_ID, "0p25s", [])
        with self.assertRaisesRegex(ValueError, "추출 목록에 없는"):
            h3_frame_export.selection_zip(self.root, JOB_ID, "0p25s", ["../../x.png"])

    def test_rejects_unknown_interval_files_and_incomplete_jobs(self):
        with self.assertRaisesRegex(ValueError, "0.25, 0.5, 1초"):
            h3_frame_export.export_frames(self.root, JOB_ID, "0.1")
        h3_frame_export.export_frames(self.root, JOB_ID, "1")
        with self.assertRaises(FileNotFoundError):
            h3_frame_export.export_file(self.root, JOB_ID, "1s", "frames.json")
        with self.assertRaises(FileNotFoundError):
            h3_frame_export.export_file(self.root, JOB_ID, "2s", "x.png")
        update_status(self.root / "runtime/h3/jobs" / JOB_ID, "running", stage="run")
        with self.assertRaises(FileNotFoundError):
            h3_frame_export.export_frames(self.root, JOB_ID, "0.5")


class H3FrameExportUIContractTest(unittest.TestCase):
    def test_video_dialog_exposes_user_triggered_frame_export(self):
        index = (ROOT / "web/public/index.html").read_text(encoding="utf-8")
        app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        server = (ROOT / "web/server.mjs").read_text(encoding="utf-8")
        dialog = index.split('<dialog id="h3CandidateVideoDialog"', 1)[1].split("</dialog>", 1)[0]
        for marker in (
            'id="h3FrameInterval"', 'value="0.25"', 'value="0.5" selected', 'value="1"',
            'id="h3FrameExtract"', 'id="h3FrameDownloadSelected"', 'id="h3FrameDownloadAll"',
            'id="h3FrameLabeled" checked',
        ):
            self.assertIn(marker, dialog)
        self.assertIn("$('#h3FrameExtract')?.addEventListener('click',extractH3Frames)", app)
        self.assertIn("resetH3FrameExport(jobId);dialog.showModal()", app)
        self.assertIn("'h3_frame_export'", server)
        self.assertIn("'h3_frame_selection_zip'", server)
        self.assertIn("content-disposition", server)
        self.assertIn("labeled:h3FrameLabeled()", app)
        self.assertIn("labeled: data.labeled === true", server)


if __name__ == "__main__":
    unittest.main()
