from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import h3_queue
from job_queue import atomic_write_json


class H3ServerPagingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = h3_queue.roots(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def _candidate(
        self, index: int, *, selected: bool = False, prompt: str | None = None
    ) -> tuple[str, str]:
        set_id = f"set-{index:02d}"
        job_id = f"job-{index:02d}"
        stamp = f"2026-08-23T00:{index:02d}:00+00:00"
        atomic_write_json(self.paths["jobs"] / job_id / "request.json", {
            "job_id": job_id,
            "job_type": "h3_r2v_generate",
            "candidate_set_id": set_id,
            "source_project_id": "project-a" if index < 10 else "project-b",
            "source_scene_id": "scene-1" if index % 2 else "scene-2",
            "source_clip_id": f"clip-{index:02d}",
            "prompt": prompt or "large prompt " * 100,
            "references": [{"role": "hero"}],
            "seed": index,
            "width": 960,
            "height": 544,
        })
        atomic_write_json(self.paths["jobs"] / job_id / "status.json", {
            "status": "completed", "updated_at": stamp,
        })
        atomic_write_json(self.paths["jobs"] / job_id / "manifest.json", {
            "generation_seconds": 12.5,
            "uploads": [{"path": "large" * 100}],
        })
        payload = {
            "candidate_set_id": set_id,
            "candidate_job_ids": [job_id],
            "source_project_id": "project-a" if index < 10 else "project-b",
            "source_scene_id": "scene-1" if index % 2 else "scene-2",
            "source_clip_id": f"clip-{index:02d}",
            "prompt": "candidate prompt " * 100,
            "prompt_variants": [{"variant_id": "A", "video_prompt": "detail"}],
            "references": [{"role": "hero"}],
            "created_at": stamp,
            "updated_at": stamp,
        }
        if selected:
            payload.update(
                selected_job_id=job_id,
                selected_jobs=[{"job_id": job_id, "selected_at": stamp}],
            )
        atomic_write_json(
            self.paths["candidate_sets"] / set_id / "candidate_set.json",
            payload,
        )
        return set_id, job_id

    def test_candidate_page_filters_and_returns_ten_detailed_sets(self):
        for index in range(12):
            self._candidate(index)

        first = h3_queue.candidate_page(self.root, {"page": 1, "page_size": 10})
        filtered = h3_queue.candidate_page(self.root, {
            "project_id": "project-b", "page": 1, "page_size": 10,
        })

        self.assertEqual(12, first["pagination"]["total"])
        self.assertEqual(10, len(first["candidate_sets"]))
        self.assertIn("references", first["candidate_sets"][0])
        self.assertEqual(2, first["pagination"]["total_pages"])
        self.assertEqual(2, filtered["pagination"]["total"])
        self.assertEqual(["project-a", "project-b"], filtered["filters"]["projects"])

    def test_results_page_contains_only_page_selection_lineage(self):
        for index in range(12):
            self._candidate(index, selected=True)

        result = h3_queue.results_page(self.root, {"page": 2, "page_size": 10})

        source_sets = [
            row for row in result["candidate_sets"]
            if row.get("render_purpose") != "resolution_rerender"
        ]
        self.assertEqual(12, result["pagination"]["total"])
        self.assertEqual(2, len(source_sets))
        self.assertEqual(2, len(result["jobs"]))

    def test_results_page_omits_failed_and_cancelled_rerender_history(self):
        source_set_id, source_job_id = self._candidate(1, selected=True)
        statuses = {
            "completed": "completed",
            "running": "running",
            "failed": "failed",
            "cancelled": "cancelled",
        }
        for suffix, status in statuses.items():
            set_id = f"rerender-{suffix}"
            job_id = f"rerender-job-{suffix}"
            atomic_write_json(self.paths["jobs"] / job_id / "request.json", {
                "job_id": job_id,
                "job_type": "h3_r2v_generate",
                "candidate_set_id": set_id,
                "render_purpose": "resolution_rerender",
            })
            atomic_write_json(self.paths["jobs"] / job_id / "status.json", {
                "status": status,
                "updated_at": "2026-08-23T01:00:00+00:00",
            })
            atomic_write_json(self.paths["candidate_sets"] / set_id / "candidate_set.json", {
                "candidate_set_id": set_id,
                "candidate_job_ids": [job_id],
                "render_purpose": "resolution_rerender",
                "source_candidate_set_id": source_set_id,
                "source_selected_job_id": source_job_id,
                "created_at": "2026-08-23T01:00:00+00:00",
            })

        result = h3_queue.results_page(self.root, {"page": 1, "page_size": 10})
        rerender_ids = {
            row["candidate_set_id"]
            for row in result["candidate_sets"]
            if row.get("render_purpose") == "resolution_rerender"
        }

        self.assertEqual(
            {"rerender-completed", "rerender-running"},
            rerender_ids,
        )
        returned_job_ids = {row["job_id"] for row in result["jobs"]}
        self.assertNotIn("rerender-job-failed", returned_job_ids)
        self.assertNotIn("rerender-job-cancelled", returned_job_ids)

    def test_rerender_estimate_uses_exact_duration_and_picture_count(self):
        samples = [
            {
                "job_id": "ep02-fast",
                "status": "completed",
                "width": 1280,
                "height": 736,
                "duration_seconds": 15.0,
                "reference_count": 4,
                "elapsed_seconds": 2309.4,
                "source_clip_id": "EP02_E001",
                "error_kind": "",
            },
            {
                "job_id": "ep01-slow",
                "status": "completed",
                "width": 1280,
                "height": 736,
                "duration_seconds": 15.0,
                "reference_count": 4,
                "elapsed_seconds": 3754.0,
                "source_clip_id": "EP01_C39_V4",
                "error_kind": "",
            },
            {
                "job_id": "old-timeout",
                "status": "failed",
                "width": 1280,
                "height": 736,
                "duration_seconds": 15.0,
                "reference_count": 4,
                "elapsed_seconds": 303.0,
                "source_clip_id": "EP02_E002",
                "error_kind": "ReadTimeout",
            },
        ]

        estimate = h3_queue._rerender_estimate(
            samples,
            width=1280,
            height=736,
            duration_seconds=15.0,
            reference_count=4,
        )

        self.assertEqual("exact", estimate["method"])
        self.assertEqual(2, estimate["exact_success_count"])
        self.assertEqual(1, estimate["exact_failure_count"])
        self.assertEqual(4, estimate["max_successful_reference_count"])
        self.assertEqual(
            ["EP02_E001", "EP01_C39_V4"],
            [row["clip_id"] for row in estimate["examples"]],
        )
        self.assertEqual(["ReadTimeout"], estimate["failure_kinds"])

    def test_candidate_page_exposes_compact_embedding_effect_metadata(self):
        self._candidate(
            1,
            prompt=(
                "embedding:minimaxh3_storm_magic\n\n"
                "The storm gathers around the subject."
            ),
        )
        self._candidate(2, prompt="The subject crosses a quiet room.")

        result = h3_queue.candidate_page(self.root, {"page": 1, "page_size": 10})
        requests = {row["job_id"]: row["request"] for row in result["jobs"]}

        self.assertTrue(requests["job-01"]["embedding_effect_applied"])
        self.assertEqual(
            ["minimaxh3_storm_magic"], requests["job-01"]["embedding_effects"]
        )
        self.assertFalse(requests["job-02"]["embedding_effect_applied"])
        self.assertEqual([], requests["job-02"]["embedding_effects"])
        self.assertNotIn("prompt", requests["job-01"])

    def test_compact_state_excludes_ai_review_and_large_detail_fields(self):
        self._candidate(1)

        result = h3_queue.state(self.root, compact=True)

        self.assertNotIn("candidate_ai_review", result)
        self.assertNotIn("prompt", result["candidate_sets"][0])
        self.assertNotIn("references", result["candidate_sets"][0])
        self.assertNotIn("prompt", result["jobs"][0]["request"])
        self.assertEqual({"generation_seconds": 12.5}, result["jobs"][0]["manifest"])


if __name__ == "__main__":
    unittest.main()
