import json
import subprocess
import sys
import tempfile
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import music_library as music
from job_queue import atomic_write_json


class MusicLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "원본.wav"
        with wave.open(str(self.source), "wb") as handle:
            handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(8000)
            handle.writeframes(b"\0\0" * 8000)
        self.meta = {"title": "해안의 기억", "description": "잔잔한 회상 음악\n피아노와 현악", "tags": ["회상", "피아노"],
                     "instrumental": True, "model": "MiniMax Music 3", "seed": 18446744073709551615}

    def register(self, **changes):
        return music.register(self.root, self.source, {**self.meta, **changes})

    def test_register_copy_and_download_metadata(self):
        original = self.source.read_bytes()
        track = self.register()["track"]
        self.assertEqual(track["metadata"]["seed"], "18446744073709551615")
        self.assertEqual(track["audio"]["duration_seconds"], 1)
        self.assertEqual(track["audio"]["sample_rate"], 8000)
        file = music.download(self.root, track)
        self.assertEqual(Path(file["path"]).read_bytes(), original)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(file["filename"], "해안의 기억.wav")
        public = music.listing(self.root, {})["tracks"][0]
        self.assertNotIn(str(self.source), json.dumps(public, ensure_ascii=False))
        self.assertNotIn("path", public)

    def test_idempotent_concurrent_registration_and_new_description(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(lambda _: self.register(), range(2)))
        self.assertEqual(rows[0]["track"]["track_id"], rows[1]["track"]["track_id"])
        self.assertEqual(sum(row["already_exists"] for row in rows), 1)
        new = self.register(description="다른 설명")
        self.assertNotEqual(new["track"]["track_id"], rows[0]["track"]["track_id"])
        self.assertEqual(music.listing(self.root, {})["pagination"]["total"], 2)

    def test_search_pagination_and_sort(self):
        self.register(title="나무")
        self.register(title="가을", tags=["바다"])
        page = music.listing(self.root, {"sort": "name", "page_size": 1})
        self.assertEqual(page["tracks"][0]["metadata"]["title"], "가을")
        self.assertEqual(page["pagination"]["total_pages"], 2)
        self.assertEqual(music.listing(self.root, {"q": "바다"})["pagination"]["total"], 1)
        self.assertEqual(music.listing(self.root, {"q": "없음"})["pagination"]["total"], 0)

    def test_bad_metadata_and_non_audio_create_no_records(self):
        for changes in ({"title": ""}, {"description": ""}, {"tags": "oops"}, {"instrumental": "yes"},
                        {"bpm": float("nan")}, {"seed": False}, {"unknown": "x"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.register(**changes)
        bad = self.root / "fake.mp3"; bad.write_text("not audio")
        with self.assertRaises(subprocess.CalledProcessError):
            music.register(self.root, bad, self.meta)
        self.assertEqual(music.listing(self.root, {})["pagination"]["total"], 0)
        self.assertFalse(list(music.tracks_root(self.root).glob(".import-*")))
        self.assertTrue(self.source.is_file())

    def test_source_change_aborts_and_preserves_source(self):
        copy = music.shutil.copyfile
        def changed(source, target):
            result = copy(source, target)
            with source.open("ab") as handle:
                handle.write(b"extra")
            return result
        with patch.object(music.shutil, "copyfile", side_effect=changed), self.assertRaisesRegex(ValueError, "원본이 변경"):
            self.register()
        self.assertTrue(self.source.read_bytes().endswith(b"extra"))
        self.assertEqual(music.listing(self.root, {})["pagination"]["total"], 0)

    def test_missing_original_keeps_description(self):
        track = self.register()["track"]
        Path(music.download(self.root, track)["path"]).unlink()
        found = music.listing(self.root, {})["tracks"][0]
        self.assertFalse(found["available"])
        self.assertEqual(found["metadata"]["description"], self.meta["description"])
        with self.assertRaises(FileNotFoundError):
            music.download(self.root, track)

    def test_path_traversal_and_symlink_rejected(self):
        for value in ("../secret", "music_../", "", "/etc/passwd"):
            with self.assertRaises(ValueError):
                music.download(self.root, {"track_id": value})
        track = self.register()["track"]
        path = Path(music.download(self.root, track)["path"])
        path.unlink(); path.symlink_to(self.source)
        self.assertFalse(music.listing(self.root, {})["tracks"][0]["available"])
        with self.assertRaises(ValueError):
            music.download(self.root, track)
        record = music.read_record(self.root, track["track_id"])
        record["audio"]["filename"] = "../../原本.wav"
        atomic_write_json(music.folder(self.root, track["track_id"]) / "track.json", record)
        with self.assertRaises(ValueError):
            music.download(self.root, track)
        self.assertEqual(music.listing(self.root, {})["invalid_count"], 1)

    def test_corrupt_record_count_not_silent(self):
        track = self.register()["track"]
        (music.folder(self.root, track["track_id"]) / "track.json").write_text("broken")
        page = music.listing(self.root, {})
        self.assertEqual(page["invalid_count"], 1)
        self.assertEqual(page["pagination"]["total"], 0)

    def test_cli_contract_and_duplicate_retry(self):
        meta = self.root / "metadata.json"; meta.write_text(json.dumps(self.meta, ensure_ascii=False))
        script = Path(__file__).resolve().parents[1] / "scripts/register_music.py"
        args = [sys.executable, str(script), "--root", str(self.root), "--audio", str(self.source), "--metadata", str(meta)]
        first = json.loads(subprocess.check_output(args, text=True))
        again = json.loads(subprocess.check_output(args, text=True))
        self.assertEqual(first["track"]["track_id"], again["track"]["track_id"])
        self.assertTrue(again["already_exists"])


if __name__ == "__main__":
    unittest.main()
