from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import evaluation_db


class EvaluationDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.entries = self.root / "runtime/candidate_reviews/entries"
        self.entries.mkdir(parents=True)
        self.db_path = self.root / evaluation_db.DEFAULT_DB_PATH

    def tearDown(self):
        self.temp.cleanup()

    def payload(self, revision: int = 1) -> dict:
        return {
            "schema_version": 1,
            "review_id": "cset_test__job_test",
            "candidate_set_id": "cset_test",
            "job_id": "job_test",
            "candidate_index": 1,
            "created_at": "2026-08-01T10:00:00+09:00",
            "updated_at": f"2026-08-01T10:0{revision}:00+09:00",
            "revision": revision,
            "verdict": "needs_improvement",
            "positive_note": "한국어 대사가 자연스럽다.",
            "overall_note": "지면 접촉을 개선해야 한다.",
            "issues": [{
                "issue_id": "issue_contact",
                "category": "motion_physics",
                "subcategory": "ground_contact_missing",
                "severity": "major",
                "start_seconds": 2.5,
                "end_seconds": 4.0,
                "expected": "발이 바닥에 닿아야 한다.",
                "observed": "몸이 공중에 떠서 이동한다.",
                "difference": "접지와 무게감이 없다.",
                "cause_hypothesis": "동작 설명이 모호했을 수 있다.",
                "suggestion": "접촉 순서를 명시한다.",
            }],
            "generation_snapshot": {
                "workflow_kind": "msr_sequence_v2",
                "workflow_filename": "workflow.json",
                "workflow_sha256": "a" * 64,
                "prompt_strategy": "msr_continuity_v1",
                "seed": 18446744073709551615,
                "seed_mode": "fixed",
                "resolution": {"width": 1280, "height": 704},
                "fps": 24,
                "review_intent_ko": "루아가 미끄러져 물에 빠진다.",
                "global_prompt": "A coastal fantasy world.",
                "segments": [{"order": 1, "role": "anchor", "sha256": "b" * 64}],
                "relay_segments": [{"order": 1, "prompt": "Lua slips.", "seconds": 5}],
            },
        }

    def write_review(self, payload: dict) -> Path:
        path = self.entries / "review.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_schema_and_legacy_review_are_imported(self):
        self.write_review(self.payload())
        report = evaluation_db.import_from_root(self.root)
        self.assertEqual(report.as_dict() | {"messages": []}, {
            "scanned": 1,
            "imported": 1,
            "unchanged": 0,
            "conflicts": 0,
            "failed": 0,
            "messages": [],
        })

        with evaluation_db.connect(self.db_path) as connection:
            run = connection.execute("SELECT * FROM generation_runs").fetchone()
            self.assertEqual(run["seed_text"], "18446744073709551615")
            self.assertEqual(run["width"], 1280)
            review = connection.execute("SELECT * FROM reviews").fetchone()
            self.assertEqual(review["positive_note"], "한국어 대사가 자연스럽다.")
            issue = connection.execute("SELECT * FROM review_issues").fetchone()
            self.assertEqual(issue["subcategory"], "ground_contact_missing")
            model = connection.execute("SELECT * FROM models").fetchone()
            self.assertEqual(model["model_id"], evaluation_db.LEGACY_MODEL_ID)

    def test_reimport_is_idempotent(self):
        self.write_review(self.payload())
        first = evaluation_db.import_from_root(self.root)
        second = evaluation_db.import_from_root(self.root)
        self.assertEqual(first.imported, 1)
        self.assertEqual(second.unchanged, 1)
        with evaluation_db.connect(self.db_path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM review_issues").fetchone()[0], 1)

    def test_new_source_revision_is_preserved_as_review_version(self):
        self.write_review(self.payload(1))
        evaluation_db.import_from_root(self.root)
        self.write_review(self.payload(2))
        report = evaluation_db.import_from_root(self.root)
        self.assertEqual(report.imported, 1)
        with evaluation_db.connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT revision FROM reviews ORDER BY revision"
            ).fetchall()
            self.assertEqual([row["revision"] for row in rows], [1, 2])

    def test_invalid_json_is_reported_without_aborting_other_files(self):
        self.write_review(self.payload())
        (self.entries / "broken.json").write_text("{broken", encoding="utf-8")
        report = evaluation_db.import_from_root(self.root)
        self.assertEqual(report.scanned, 2)
        self.assertEqual(report.imported, 1)
        self.assertEqual(report.failed, 1)
        self.assertIn("broken.json", report.messages[0])


if __name__ == "__main__":
    unittest.main()
