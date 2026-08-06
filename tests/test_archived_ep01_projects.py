from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import director_prompt_projects
import msr_prompt_projects


class ArchivedEP01ProjectsTest(unittest.TestCase):
    def test_ep01_projects_are_hidden_but_other_projects_remain_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            director_base = root / "director_prompt_projects"
            prompt_base = root / "prompt_projects"
            archived_director = director_base / "RaisingaDragonSeason01"
            archived_prompt = prompt_base / "RaisingaDragonSeason01_EP01_v4"
            archived_director.mkdir(parents=True)
            archived_prompt.mkdir(parents=True)
            (archived_director / director_prompt_projects.ARCHIVE_MARKER_FILE).write_text(
                "archived", encoding="utf-8"
            )
            (archived_prompt / msr_prompt_projects.ARCHIVE_MARKER_FILE).write_text(
                "archived", encoding="utf-8"
            )
            (director_base / "ActiveDirectorProject").mkdir(parents=True)
            (prompt_base / "ActivePromptProject").mkdir(parents=True)

            director_ids = {
                item["project_id"]
                for item in director_prompt_projects.list_projects_action(root)["projects"]
            }
            prompt_ids = {
                item["project_id"]
                for item in msr_prompt_projects.list_prompt_projects_action(root)["projects"]
            }

        self.assertEqual(director_ids, {"ActiveDirectorProject"})
        self.assertEqual(prompt_ids, {"ActivePromptProject"})

    def test_direct_ep01_access_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            director_project = root / "director_prompt_projects" / "RaisingaDragonSeason01"
            prompt_project = root / "prompt_projects" / "RaisingaDragonSeason01_EP01_v4"
            director_project.mkdir(parents=True)
            prompt_project.mkdir(parents=True)
            (director_project / director_prompt_projects.ARCHIVE_MARKER_FILE).write_text(
                "archived", encoding="utf-8"
            )
            (prompt_project / msr_prompt_projects.ARCHIVE_MARKER_FILE).write_text(
                "archived", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                director_prompt_projects.DirectorPromptProjectError, "보관 처리된 EP01"
            ):
                director_prompt_projects.list_clips_action(
                    root, {"project_id": "RaisingaDragonSeason01"}
                )
            with self.assertRaisesRegex(
                msr_prompt_projects.PromptProjectError, "보관 처리된 EP01"
            ):
                msr_prompt_projects.list_prompt_project_clips_action(
                    root, {"project_id": "RaisingaDragonSeason01_EP01_v4"}
                )


if __name__ == "__main__":
    unittest.main()
