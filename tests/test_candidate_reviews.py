from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import candidate_reviews
import ui_backend
from job_queue import atomic_write_json


class CandidateReviewsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.jobs = self.root / "jobs"
        self.jobs.mkdir()
        self.set_id = "cset_test"
        self.job_id = "candidate_job_1"
        job_dir = self.jobs / self.job_id
        job_dir.mkdir()
        self.request = {
            "job_id": self.job_id,
            "job_type": "generate",
            "candidate_set_id": self.set_id,
            "candidate_index": 1,
            "workflow_kind": "msr_sequence_v2",
            "workflow_filename": "multiGuide.json",
            "prompt_strategy": "msr_continuity_v1",
            "seed": 123,
            "seed_mode": "fixed",
            "resolution": {"width": 1280, "height": 704},
            "fps": 24,
            "review_intent_ko": "루아가 젖은 바닥에서 미끄러진다.",
            "global_prompt": "World and character identity.",
            "relay_segments": [{"order": 1, "prompt": "Lua slips.", "seconds": 8}],
            "segments": [{"role": "character_1", "slot": 1, "sha256": "a" * 64}],
        }
        atomic_write_json(job_dir / "request.json", self.request)
        atomic_write_json(job_dir / "manifest.json", {"status": "completed"})
        atomic_write_json(job_dir / "status.json", {"status": "completed"})
        atomic_write_json(job_dir / "selected_workflow_api.json", {"1": {"class_type": "Test"}})
        set_path = self.root / "runtime/candidate_sets" / self.set_id / "candidate_set.json"
        set_path.parent.mkdir(parents=True)
        atomic_write_json(set_path, {
            "candidate_set_id": self.set_id,
            "candidate_job_ids": [self.job_id],
            "status": "awaiting_candidate_selection",
        })
        self.originals = {
            "ROOT": ui_backend.ROOT,
            "JOBS": ui_backend.JOBS,
            "CANDIDATE_SETS": ui_backend.CANDIDATE_SETS,
        }
        ui_backend.ROOT = self.root
        ui_backend.JOBS = self.jobs
        ui_backend.CANDIDATE_SETS = self.root / "runtime/candidate_sets"

    def tearDown(self):
        for name, value in self.originals.items():
            setattr(ui_backend, name, value)
        self.temp.cleanup()

    def review_payload(self):
        return {
            "candidate_set_id": self.set_id,
            "job_id": self.job_id,
            "verdict": "needs_improvement",
            "positive_note": "초반 구도는 좋음",
            "overall_note": "물리 동작과 물 표현을 개선해야 함",
            "issues": [
                {
                    "category": "motion_physics",
                    "subcategory": "weight_and_ground_contact",
                    "severity": "major",
                    "start_seconds": 5.4,
                    "end_seconds": 7.2,
                    "expected": "발이 젖은 바닥을 딛고 균형을 잃으며 미끄러짐",
                    "observed": "몸이 뜬 채 일정한 속도로 이동함",
                    "difference": "지면 접촉과 무게감이 없음",
                    "cause_hypothesis": "미끄러진다는 표현이 추상적이었을 가능성",
                    "suggestion": "발 접촉, 무게중심 붕괴, 손으로 짚는 반응을 순서대로 명시",
                }
            ],
        }

    def test_review_is_saved_with_generation_snapshot_and_candidate_summary(self):
        result = ui_backend.save_candidate_review_action(self.review_payload())
        review = result["review"]
        self.assertEqual(review["issues"][0]["category"], "motion_physics")
        self.assertEqual(review["generation_snapshot"]["seed"], 123)
        self.assertEqual(review["generation_snapshot"]["workflow_kind"], "msr_sequence_v2")
        self.assertEqual(result["summary"]["issue_count"], 1)

        saved_set = json.loads((
            self.root / "runtime/candidate_sets" / self.set_id / "candidate_set.json"
        ).read_text())
        self.assertEqual(saved_set["candidate_reviews"][self.job_id]["issue_count"], 1)

        durable = candidate_reviews.review_path(self.root, self.set_id, self.job_id)
        self.assertTrue(durable.is_file())
        loaded = ui_backend.get_candidate_review_action({
            "candidate_set_id": self.set_id,
            "job_id": self.job_id,
        })
        self.assertEqual(loaded["review"]["positive_note"], "초반 구도는 좋음")
        self.assertEqual(
            loaded["expected_default_ko"],
            "루아가 젖은 바닥에서 미끄러진다.",
        )

    def test_expected_default_falls_back_to_korean_source_summary(self):
        self.assertEqual(
            candidate_reviews.expected_default_ko({
                "source_scene_refs": "EP01 S#2 — 루아가 물고기를 놓치고 물에 빠진다"
            }),
            "루아가 물고기를 놓치고 물에 빠진다",
        )

    def test_review_revision_increments(self):
        first = ui_backend.save_candidate_review_action(self.review_payload())["review"]
        payload = self.review_payload()
        payload["overall_note"] = "수정된 메모"
        second = ui_backend.save_candidate_review_action(payload)["review"]
        self.assertEqual(first["revision"], 1)
        self.assertEqual(second["revision"], 2)
        self.assertEqual(first["created_at"], second["created_at"])

    def test_invalid_time_range_is_rejected(self):
        payload = self.review_payload()
        payload["issues"][0]["start_seconds"] = 8
        payload["issues"][0]["end_seconds"] = 2
        with self.assertRaisesRegex(ValueError, "종료 시간"):
            ui_backend.save_candidate_review_action(payload)

    def test_review_rejects_job_outside_candidate_set(self):
        payload = self.review_payload()
        payload["job_id"] = "other_job"
        with self.assertRaisesRegex(ValueError, "속하지 않는"):
            ui_backend.save_candidate_review_action(payload)


if __name__ == "__main__":
    unittest.main()
