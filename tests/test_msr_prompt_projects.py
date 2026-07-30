from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import msr_prompt_projects
import ui_backend


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "RaisingaDragonSeason01"
SAMPLE_MD = """---
# MSR Prompt: TEST_01

## Summary

테스트 클립

## Machine Payload

```json
{
  "schema_version": 1,
  "project_id": "RaisingaDragonSeason01",
  "scene_id": "SC99-001",
  "clip_id": "SC99-001_01",
  "sequence": 1,
  "status": "reviewed",
  "workflow": "msr_v2",
  "fps": 24,
  "resolution": {"width": 1280, "height": 704},
  "requested_seconds": 10,
  "previous_clip": null,
  "next_clip": "SC99-001_02",
  "references": [
    {
      "reference_id": 1,
      "character_name": "루아",
      "description": "바닷가 소녀",
      "source_path": "RaisingaDragonSeason01/Lua.png"
    }
  ],
  "background": {
    "description": "바닷가",
    "source_path": "RaisingaDragonSeason01/Lua.png"
  },
  "continuity": {
    "start_state": "시작",
    "end_state": "종료",
    "carry_to_next": ["연속"]
  },
  "global_prompt": "Preserve the exact visual style of the supplied animated references.",
  "relay_segments": [
    {"order": 1, "seconds": 5, "prompt": "첫 구간"},
    {"order": 2, "seconds": 5, "prompt": "둘째 구간"}
  ],
  "dialogue": [],
  "review": {
    "scenario_consistent": true,
    "dialogue_preserved": true,
    "reference_mapping_valid": true,
    "duration_valid": true,
    "animation_style_preserved": true,
    "warnings": [],
    "unresolved_questions": []
  }
}
```

## Global Prompt

테스트

## Relay Segments

테스트

## Dialogue Check

없음

## Continuity

테스트

## AI Review

테스트
---
"""


BG_SAMPLE_MD = """---
# MSR Prompt: TEST_02

## Summary

배경 대기 테스트

## Machine Payload

```json
{
  "schema_version": 1,
  "project_id": "RaisingaDragonSeason01",
  "scene_id": "SC99-002",
  "clip_id": "SC99-002_01",
  "sequence": 1,
  "status": "awaiting_background",
  "workflow": "msr_v2",
  "fps": 24,
  "resolution": {"width": 1280, "height": 704},
  "requested_seconds": 10,
  "previous_clip": null,
  "next_clip": null,
  "references": [
    {
      "reference_id": 1,
      "character_name": "루아",
      "description": "바닷가 소녀",
      "source_path": "RaisingaDragonSeason01/Lua.png"
    }
  ],
  "background": {
    "status": "missing",
    "background_id": "BG_TEST_COAST",
    "source_path": null,
    "description": "테스트 해안 배경"
  },
  "background_generation": {
    "required": true,
    "suggested_filename": "BG_TEST_COAST.png",
    "aspect_ratio": "16:9",
    "recommended_resolution": {"width": 1536, "height": 864},
    "prompt": "Animated coastal background plate.",
    "negative_prompt": "characters, text",
    "continuity_notes": ["cool morning light"]
  },
  "continuity": {
    "start_state": "시작",
    "end_state": "종료",
    "carry_to_next": ["연속"]
  },
  "global_prompt": "Preserve the exact visual style of the supplied animated references.",
  "relay_segments": [
    {"order": 1, "seconds": 5, "prompt": "첫 구간"},
    {"order": 2, "seconds": 5, "prompt": "둘째 구간"}
  ],
  "dialogue": [],
  "review": {
    "scenario_consistent": true,
    "dialogue_preserved": true,
    "reference_mapping_valid": true,
    "duration_valid": true,
    "animation_style_preserved": true,
    "warnings": [],
    "unresolved_questions": []
  }
}
```

## Global Prompt

테스트

## Relay Segments

테스트

## Dialogue Check

없음

## Continuity

테스트

## AI Review

테스트
---
"""


class MsrPromptProjectsTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.project_dir = self.root / "prompt_projects" / PROJECT_ID / "SC99-001"
        self.project_dir.mkdir(parents=True)
        self.asset_root = self.root / "RaisingaDragonSeason01"
        self.asset_root.mkdir()
        (self.asset_root / "Lua.png").write_bytes(b"fake-png")
        self.md_path = self.project_dir / "SC99-001_01.md"
        self.md_path.write_text(SAMPLE_MD, encoding="utf-8")
        (self.root / "prompt_projects" / PROJECT_ID / "manifest.json").write_text(
            json.dumps({"project_id": PROJECT_ID, "title": "Test"}),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_extract_and_validate_good_payload(self):
        payload = msr_prompt_projects.extract_machine_payload(SAMPLE_MD)
        validation = msr_prompt_projects.validate_machine_payload(self.root, payload)
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["status"], "reviewed")
        self.assertEqual(validation["relay_total_seconds"], 10)

    def test_missing_json_block(self):
        with self.assertRaises(msr_prompt_projects.PromptProjectError):
            msr_prompt_projects.extract_machine_payload("# no json")

    def test_invalid_json(self):
        broken = SAMPLE_MD.replace('"schema_version": 1', '"schema_version": 1,')
        with self.assertRaises(msr_prompt_projects.PromptProjectError):
            msr_prompt_projects.extract_machine_payload(broken)

    def test_requested_seconds_over_30(self):
        payload = msr_prompt_projects.extract_machine_payload(SAMPLE_MD)
        payload["requested_seconds"] = 31
        payload["relay_segments"] = [{"order": 1, "seconds": 31, "prompt": "길다"}]
        validation = msr_prompt_projects.validate_machine_payload(self.root, payload)
        self.assertFalse(validation["valid"])
        self.assertIn("30", validation["errors"][0])

    def test_relay_sum_mismatch(self):
        payload = msr_prompt_projects.extract_machine_payload(SAMPLE_MD)
        payload["requested_seconds"] = 10
        payload["relay_segments"][1]["seconds"] = 3
        validation = msr_prompt_projects.validate_machine_payload(self.root, payload)
        self.assertFalse(validation["valid"])
        self.assertTrue(any("일치하지 않습니다" in err for err in validation["errors"]))

    def test_invalid_reference_id(self):
        payload = msr_prompt_projects.extract_machine_payload(SAMPLE_MD)
        payload["references"].append(
            {
                "reference_id": 5,
                "character_name": "x",
                "description": "x",
                "source_path": "RaisingaDragonSeason01/Lua.png",
            }
        )
        validation = msr_prompt_projects.validate_machine_payload(self.root, payload)
        self.assertFalse(validation["valid"])

    def test_missing_image(self):
        payload = msr_prompt_projects.extract_machine_payload(SAMPLE_MD)
        payload["references"][0]["source_path"] = "RaisingaDragonSeason01/missing.png"
        validation = msr_prompt_projects.validate_machine_payload(self.root, payload)
        self.assertFalse(validation["valid"])

    def test_path_outside_root(self):
        with self.assertRaises(msr_prompt_projects.PromptProjectError):
            msr_prompt_projects.resolve_allowed_asset(self.root, "RaisingaDragonSeason01/../ui_backend.py")

    def test_dotdot_path_rejected(self):
        with self.assertRaises(msr_prompt_projects.PromptProjectError):
            msr_prompt_projects.resolve_allowed_asset(self.root, "RaisingaDragonSeason01/foo/../../../etc/passwd")

    def test_symlink_escape_blocked(self):
        outside = self.root / "outside.png"
        outside.write_bytes(b"x")
        link = self.asset_root / "link.png"
        link.symlink_to(outside)
        with self.assertRaises(msr_prompt_projects.PromptProjectError):
            msr_prompt_projects.resolve_allowed_asset(self.root, "RaisingaDragonSeason01/link.png")

    def test_needs_confirmation_status_preserved(self):
        payload = msr_prompt_projects.extract_machine_payload(SAMPLE_MD)
        payload["status"] = "needs_confirmation"
        payload["review"]["warnings"] = ["확인 필요"]
        payload["review"]["unresolved_questions"] = ["확인 필요"]
        validation = msr_prompt_projects.validate_machine_payload(self.root, payload)
        self.assertEqual(validation["status"], "needs_confirmation")

    def test_scan_sorts_by_scene_and_sequence(self):
        second = self.root / "prompt_projects" / PROJECT_ID / "SC99-002" / "SC99-002_01.md"
        second.parent.mkdir()
        second.write_text(
            SAMPLE_MD.replace("SC99-001_01", "SC99-002_01").replace('"scene_id": "SC99-001"', '"scene_id": "SC99-002"'),
            encoding="utf-8",
        )
        clips = msr_prompt_projects.scan_project_clips(self.root, PROJECT_ID)
        self.assertEqual([clip["clip_id"] for clip in clips], ["SC99-001_01", "SC99-002_01"])

    def test_corrupted_markdown_does_not_break_scan(self):
        bad = self.project_dir / "SC99-001_bad.md"
        bad.write_text("broken", encoding="utf-8")
        clips = msr_prompt_projects.scan_project_clips(self.root, PROJECT_ID)
        statuses = {clip["clip_id"]: clip["status"] for clip in clips}
        self.assertEqual(statuses["SC99-001_bad"], "invalid")
        self.assertEqual(statuses["SC99-001_01"], "reviewed")

    def test_list_and_detail_actions(self):
        second = self.root / "prompt_projects" / PROJECT_ID / "SC99-002" / "SC99-002_01.md"
        second.parent.mkdir()
        second_payload = msr_prompt_projects.extract_machine_payload(SAMPLE_MD)
        second_payload.update(
            scene_id="SC99-002",
            clip_id="SC99-002_01",
            sequence=1,
            previous_clip=None,
            next_clip=None,
        )
        second_text = SAMPLE_MD.replace("SC99-001_01", "SC99-002_01").replace('"scene_id": "SC99-001"', '"scene_id": "SC99-002"')
        second.write_text(second_text, encoding="utf-8")
        listed = msr_prompt_projects.list_prompt_projects_action(self.root)
        self.assertGreaterEqual(listed["projects"][0]["clip_count"], 2)
        detail = msr_prompt_projects.get_prompt_project_clip_action(
            self.root, {"project_id": PROJECT_ID, "clip_id": "SC99-001_01"}
        )
        self.assertEqual(detail["clip_id"], "SC99-001_01")
        self.assertIn("machine_payload", detail)
        self.assertTrue(detail["asset_urls"]["references"][0]["asset_url"].startswith("/api/msr-prompt-assets/"))

    def test_resolve_msr_upload_path_from_source_path(self):
        path = msr_prompt_projects.resolve_msr_upload_path(
            self.root,
            {"source_path": "RaisingaDragonSeason01/Lua.png"},
        )
        self.assertTrue(path.is_file())

    def _write_background_catalog(self):
        catalog = {
            "schema_version": 1,
            "project_id": PROJECT_ID,
            "backgrounds": {
                "BG_TEST_COAST": {
                    "background_id": "BG_TEST_COAST",
                    "suggested_filename": "BG_TEST_COAST.png",
                    "description": "테스트 해안 배경",
                    "aspect_ratio": "16:9",
                    "recommended_resolution": {"width": 1536, "height": 864},
                    "prompt": "Animated coastal background plate.",
                    "negative_prompt": "characters, text",
                    "continuity_notes": ["cool morning light"],
                }
            },
        }
        (self.root / "prompt_projects" / PROJECT_ID / "background_catalog.json").write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def test_awaiting_background_status_when_bg_missing(self):
        self._write_background_catalog()
        bg_dir = self.root / "prompt_projects" / PROJECT_ID / "SC99-002"
        bg_dir.mkdir(parents=True, exist_ok=True)
        (bg_dir / "SC99-002_01.md").write_text(BG_SAMPLE_MD, encoding="utf-8")
        payload = msr_prompt_projects.extract_machine_payload(BG_SAMPLE_MD)
        validation = msr_prompt_projects.validate_machine_payload(self.root, payload, project_id=PROJECT_ID)
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["status"], "awaiting_background")
        self.assertFalse(validation["background_linked"])
        clip = msr_prompt_projects.parse_clip_markdown(
            self.root,
            bg_dir / "SC99-002_01.md",
            project_id=PROJECT_ID,
        )
        self.assertEqual(clip["status"], "awaiting_background")

    def test_reviewed_when_background_linked_via_background_links(self):
        self._write_background_catalog()
        bg_dir = self.root / "prompt_projects" / PROJECT_ID / "backgrounds"
        bg_dir.mkdir(parents=True, exist_ok=True)
        (bg_dir / "BG_TEST_COAST.png").write_bytes(b"fake-png")
        msr_prompt_projects.save_background_link_action(
            self.root,
            {
                "project_id": PROJECT_ID,
                "background_id": "BG_TEST_COAST",
                "filename": "BG_TEST_COAST.png",
            },
        )
        scene_dir = self.root / "prompt_projects" / PROJECT_ID / "SC99-002"
        scene_dir.mkdir(parents=True, exist_ok=True)
        (scene_dir / "SC99-002_01.md").write_text(BG_SAMPLE_MD, encoding="utf-8")
        clip = msr_prompt_projects.parse_clip_markdown(
            self.root,
            scene_dir / "SC99-002_01.md",
            project_id=PROJECT_ID,
        )
        self.assertEqual(clip["status"], "reviewed")
        self.assertTrue(clip["background_linked"])

    def test_auto_detect_by_suggested_filename_in_backgrounds(self):
        self._write_background_catalog()
        bg_dir = self.root / "prompt_projects" / PROJECT_ID / "backgrounds"
        bg_dir.mkdir(parents=True, exist_ok=True)
        (bg_dir / "BG_TEST_COAST.png").write_bytes(b"fake-png")
        scene_dir = self.root / "prompt_projects" / PROJECT_ID / "SC99-002"
        scene_dir.mkdir(parents=True, exist_ok=True)
        (scene_dir / "SC99-002_01.md").write_text(BG_SAMPLE_MD, encoding="utf-8")
        clip = msr_prompt_projects.parse_clip_markdown(
            self.root,
            scene_dir / "SC99-002_01.md",
            project_id=PROJECT_ID,
        )
        self.assertEqual(clip["status"], "reviewed")
        self.assertTrue(clip["background_linked"])
        self.assertEqual(
            clip["payload"]["background"]["source_path"],
            "prompt_projects/RaisingaDragonSeason01/backgrounds/BG_TEST_COAST.png",
        )

    def test_background_link_save_api(self):
        self._write_background_catalog()
        bg_dir = self.root / "prompt_projects" / PROJECT_ID / "backgrounds"
        bg_dir.mkdir(parents=True, exist_ok=True)
        (bg_dir / "BG_TEST_COAST.png").write_bytes(b"fake-png")
        saved = msr_prompt_projects.save_background_link_action(
            self.root,
            {
                "project_id": PROJECT_ID,
                "background_id": "BG_TEST_COAST",
                "filename": "BG_TEST_COAST.png",
            },
        )
        self.assertEqual(saved["background_id"], "BG_TEST_COAST")
        self.assertTrue(saved["resolved"]["linked"])
        links_path = self.root / "prompt_projects" / PROJECT_ID / "background_links.json"
        self.assertTrue(links_path.is_file())
        links = json.loads(links_path.read_text(encoding="utf-8"))
        self.assertIn("BG_TEST_COAST", links["links"])

    def test_background_reupload_resets_review_status(self):
        self._write_background_catalog()
        bg_dir = self.root / "prompt_projects" / PROJECT_ID / "backgrounds"
        bg_dir.mkdir(parents=True, exist_ok=True)
        original = bg_dir / "BG_TEST_COAST.png"
        replacement = bg_dir / "BG_TEST_COAST_v2.png"
        original.write_bytes(b"fake-png")
        replacement.write_bytes(b"fake-png-v2")
        msr_prompt_projects.save_background_links(
            self.root,
            PROJECT_ID,
            {
                "BG_TEST_COAST": {
                    "filename": "BG_TEST_COAST.png",
                    "source_path": "prompt_projects/RaisingaDragonSeason01/backgrounds/BG_TEST_COAST.png",
                    "review_status": "changes_required",
                    "review_notes": ["스타일 불일치"],
                    "reviewed_at": "2026-07-27T10:00:00+00:00",
                }
            },
        )
        saved = msr_prompt_projects.save_background_link_action(
            self.root,
            {
                "project_id": PROJECT_ID,
                "background_id": "BG_TEST_COAST",
                "filename": "BG_TEST_COAST.png",
                "upload_path": str(replacement),
            },
        )
        link = saved["links"]["BG_TEST_COAST"]
        self.assertEqual(link["review_status"], "pending")
        self.assertEqual(link["review_notes"], [])
        self.assertIsNone(link["reviewed_at"])
        self.assertIn("replaced_at", link)
        self.assertEqual(link["previous_review_notes"], ["스타일 불일치"])

        scene_dir = self.root / "prompt_projects" / PROJECT_ID / "SC99-002"
        scene_dir.mkdir(parents=True, exist_ok=True)
        (scene_dir / "SC99-002_01.md").write_text(BG_SAMPLE_MD, encoding="utf-8")
        clip = msr_prompt_projects.parse_clip_markdown(
            self.root,
            scene_dir / "SC99-002_01.md",
            project_id=PROJECT_ID,
        )
        self.assertEqual(clip["status"], "awaiting_background")
        self.assertEqual(clip["payload"]["background"]["review_status"], "pending")

        detail = msr_prompt_projects.get_prompt_project_clip_action(
            self.root,
            {"project_id": PROJECT_ID, "clip_id": "SC99-002_01"},
        )
        self.assertFalse(detail["can_register_msr"])
        self.assertIn("배경 검수", detail["registration_block_reason"])

    def test_shared_background_id_updates_all_clips(self):
        self._write_background_catalog()
        bg_dir = self.root / "prompt_projects" / PROJECT_ID / "backgrounds"
        bg_dir.mkdir(parents=True, exist_ok=True)
        (bg_dir / "BG_TEST_COAST.png").write_bytes(b"fake-png")
        msr_prompt_projects.save_background_link_action(
            self.root,
            {
                "project_id": PROJECT_ID,
                "background_id": "BG_TEST_COAST",
                "filename": "BG_TEST_COAST.png",
            },
        )
        for clip_id, scene_id in [("SC99-002_01", "SC99-002"), ("SC99-003_01", "SC99-003")]:
            scene_dir = self.root / "prompt_projects" / PROJECT_ID / scene_id
            scene_dir.mkdir(parents=True, exist_ok=True)
            text = BG_SAMPLE_MD.replace("SC99-002_01", clip_id).replace('"scene_id": "SC99-002"', f'"scene_id": "{scene_id}"')
            (scene_dir / f"{clip_id}.md").write_text(text, encoding="utf-8")
        clips = msr_prompt_projects.scan_project_clips(self.root, PROJECT_ID)
        linked = [clip for clip in clips if clip.get("background_id") == "BG_TEST_COAST"]
        self.assertEqual(len(linked), 2)
        self.assertTrue(all(clip["status"] == "reviewed" for clip in linked))


class MsrPromptProjectsIntegrationTest(unittest.TestCase):
    def test_real_project_scan(self):
        if not (ROOT / "prompt_projects" / PROJECT_ID).is_dir():
            self.skipTest("prompt project not present")
        clips = msr_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        self.assertGreaterEqual(len(clips), 11)
        self.assertTrue(all(float(clip.get("requested_seconds") or 0) <= 30 for clip in clips))
        self.assertTrue(all(clip["status"] in {"reviewed", "needs_confirmation", "awaiting_background", "invalid"} for clip in clips))

    def test_create_msr_candidates_accepts_source_paths_without_upload(self):
        asset = ROOT / "RaisingaDragonSeason01" / "Lua.png"
        if not asset.is_file():
            self.skipTest("reference asset missing")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            jobs = root / "jobs"
            jobs.mkdir()
            originals = {
                "ROOT": ui_backend.ROOT,
                "JOBS": ui_backend.JOBS,
                "CANDIDATE_SETS": ui_backend.CANDIDATE_SETS,
                "COMPOSITIONS": ui_backend.COMPOSITIONS,
                "MSR_GRAPH": ui_backend.MSR_GRAPH,
            }
            try:
                ui_backend.ROOT = root
                ui_backend.JOBS = jobs
                ui_backend.CANDIDATE_SETS = root / "runtime/candidate_sets"
                ui_backend.COMPOSITIONS = root / "runtime/compositions"
                asset_root = root / "RaisingaDragonSeason01"
                asset_root.mkdir()
                (asset_root / "Lua.png").write_bytes(asset.read_bytes())
                msr_graph = ROOT / "tests" / "fixtures" / "msr_graph.json"
                if msr_graph.is_file():
                    ui_backend.MSR_GRAPH = msr_graph
                elif not ui_backend.MSR_GRAPH.is_file():
                    self.skipTest("MSR graph unavailable")
                payload = ui_backend.create_msr_candidates_action(
                    {
                        "candidate_count": 2,
                        "job_name": "msr-prompt-project-test",
                        "seed": 10,
                        "width": 1280,
                        "height": 704,
                        "global_prompt": "테스트",
                        "references": [
                            {
                                "source_path": "RaisingaDragonSeason01/Lua.png",
                                "original_name": "Lua.png",
                                "description": "루아",
                            }
                        ],
                        "background": {
                            "source_path": "RaisingaDragonSeason01/Lua.png",
                            "original_name": "Lua.png",
                            "description": "배경",
                        },
                        "relay_segments": [{"prompt": "짧은 장면", "seconds": 5}],
                    }
                )
                self.assertEqual(payload["generation_mode"], "msr_v2")
                for job_id in payload["candidate_job_ids"]:
                    request = json.loads((jobs / job_id / "request.json").read_text(encoding="utf-8"))
                    self.assertEqual(request["workflow_kind"], "msr_v2")
                    self.assertEqual(request["relay_segments"][0]["seconds"], 5)
            finally:
                for key, value in originals.items():
                    setattr(ui_backend, key, value)


if __name__ == "__main__":
    unittest.main()
