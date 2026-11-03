import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import feedback_notes as notes
import h3_queue
import ui_backend


class FeedbackNotesTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def create(self, **extra):
        return notes.save(self.root, {"title": "EP06 피드백", "body": "## 확인\n- [ ] 손 위치", "expected_revision": None, **extra})

    def test_independent_roundtrip_history_and_no_parent_required(self):
        record = self.create(project_id="does-not-exist", candidate_set_id="missing")
        self.assertNotIn("project_id", record)
        self.assertNotIn("candidate_set_id", record)
        self.assertFalse((self.root / "prompt_projects").exists())
        self.assertEqual(notes.load(self.root, record), record)
        changed = notes.save(self.root, {"note_id": record["note_id"], "expected_revision": record["revision"], "body": "- [x] 반영 완료"})
        self.assertEqual(changed["created_at"], record["created_at"])
        self.assertNotEqual(changed["revision"], record["revision"])
        self.assertEqual(notes.load(self.root, {"note_id": record["note_id"], "revision": record["revision"]}), record)
        self.assertEqual([r["revision"] for r in notes.history(self.root, record)["revisions"]], [changed["revision"], record["revision"]])
        self.assertNotIn("body", notes.listing(self.root, {})["notes"][0])

    def test_same_contents_are_idempotent_and_lost_response_is_conflict(self):
        record = self.create()
        same = notes.save(self.root, {**record, "expected_revision": record["revision"]})
        self.assertEqual(same["revision"], record["revision"])
        conflict = notes.save(self.root, {**record, "expected_revision": None})
        self.assertTrue(conflict["conflict"])
        self.assertEqual(conflict["current"], record)
        self.assertEqual(len(notes.history(self.root, record)["revisions"]), 1)

    def test_concurrent_saves_have_one_winner(self):
        record = self.create()
        with ThreadPoolExecutor(max_workers=2) as pool:
            out = list(pool.map(lambda text: notes.save(self.root, {"note_id": record["note_id"], "expected_revision": record["revision"], "body": text}), ["첫 번째", "두 번째"]))
        self.assertEqual(sum(bool(r.get("conflict")) for r in out), 1)
        self.assertEqual(len(notes.history(self.root, record)["revisions"]), 2)

    def test_archive_restore_and_revision_restore_keep_original(self):
        record = self.create()
        archived = notes.save(self.root, {"note_id": record["note_id"], "expected_revision": record["revision"], "archived": True})
        self.assertEqual(notes.listing(self.root, {})["notes"], [])
        self.assertEqual(len(notes.listing(self.root, {"archived": True})["notes"]), 1)
        restored = notes.save(self.root, {**record, "expected_revision": archived["revision"]})
        self.assertFalse(restored["archived"])
        self.assertNotEqual(restored["revision"], record["revision"])
        self.assertEqual(len(notes.history(self.root, record)["revisions"]), 3)

    def test_failed_head_commit_does_not_expose_uncommitted_history(self):
        record = self.create()
        original = notes.atomic_write_json
        def write(path, payload):
            if path.name == "note.json":
                raise OSError("disk failure")
            return original(path, payload)
        with mock.patch.object(notes, "atomic_write_json", side_effect=write):
            with self.assertRaises(OSError):
                notes.save(self.root, {"note_id": record["note_id"], "expected_revision": record["revision"], "body": "never committed"})
        self.assertEqual(notes.load(self.root, record), record)
        self.assertEqual(len(notes.history(self.root, record)["revisions"]), 1)

    def test_corrupted_record_is_not_overwritten(self):
        record = self.create()
        path = notes.directory(self.root, record["note_id"]) / "note.json"
        path.write_text("broken")
        with self.assertRaises(ValueError):
            notes.save(self.root, {"note_id": record["note_id"], "expected_revision": None})
        self.assertEqual(path.read_text(), "broken")

    def test_validation_and_missing(self):
        for data in ({"note_id": "../escape", "expected_revision": None}, {"title": "x" * 201, "expected_revision": None}, {"body": "x" * 500001, "expected_revision": None}, {"archived": 1, "expected_revision": None}, {}):
            with self.assertRaises(ValueError):
                notes.save(self.root, data)
        missing = {"note_id": "note_" + "0" * 32}
        self.assertTrue(notes.load(self.root, missing)["not_found"])
        self.assertTrue(notes.history(self.root, missing)["not_found"])
        with self.assertRaises(ValueError):
            notes.load(self.root, {**missing, "revision": "../escape"})

    def test_legacy_feedback_execution_is_removed_but_history_untouched(self):
        legacy = self.root / "runtime/h3/prompt_revision_requests/old/request.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps({"feedback": "old", "candidate_set_id": "old"}))
        before = legacy.read_bytes()
        self.create()
        state = h3_queue.state(self.root)
        self.assertNotIn("prompt_revision_requests", state)
        self.assertNotIn("prompt_authoring", state)
        for name in ("save_h3_prompt_revision_request", "revise_h3_candidate_set", "apply_h3_prompt_revision"):
            self.assertNotIn(name, ui_backend.ACTIONS)
        for name in ("save_prompt_revision_request", "apply_authored_prompt_revision", "list_prompt_revision_requests"):
            self.assertFalse(hasattr(h3_queue, name))
        self.assertTrue(callable(h3_queue.restore_candidate_version))
        self.assertTrue(callable(h3_queue.requeue_candidate_set))
        self.assertEqual(legacy.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
