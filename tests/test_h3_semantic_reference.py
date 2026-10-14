from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import h3_queue


class H3SemanticReferenceSettingsTests(unittest.TestCase):
    def test_linked_reference_remaps_project_indexes_and_keeps_sol_attn(self):
        refs = [{"project_id": "p", "clip_id": "c", "project_picture_index": n}
                for n in [6, 2]]
        with patch.object(h3_queue.h3_prompt_projects, "load_clip", return_value={
            "workflow_settings": {"semantic_reference_indexes": [6]}
        }) as load:
            settings = h3_queue._linked_reference_settings(Path('.'), refs, {"sol_attn": {"tau": 0.1}})
        self.assertEqual([1], settings['semantic_reference_indexes'])
        self.assertEqual({"tau": 0.1}, settings['sol_attn'])
        self.assertEqual(1, load.call_count)

    def test_removed_semantic_reference_is_not_carried_to_another_picture(self):
        with patch.object(h3_queue.h3_prompt_projects, "load_clip", return_value={
            "workflow_settings": {"semantic_reference_indexes": [6]}
        }):
            settings = h3_queue._linked_reference_settings(Path('.'), [
                {"project_id": "p", "clip_id": "c", "project_picture_index": 2}
            ])
        self.assertEqual({}, settings)

    def test_writes_required_empty_semantic_picture_input(self):
        workflow = {
            "136": {
                "class_type": "MiniMaxH3ReferenceToVideo",
                "inputs": {},
            }
        }

        settings = h3_queue._production_workflow_settings(workflow)

        self.assertEqual({}, settings)
        self.assertEqual("", workflow["136"]["inputs"]["semantic_ref_indexes"])

    def test_marks_selected_picture_as_semantic_only(self):
        workflow = {
            "136": {
                "class_type": "MiniMaxH3ReferenceToVideo",
                "inputs": {},
            }
        }

        settings = h3_queue._production_workflow_settings(
            workflow,
            {"semantic_reference_indexes": [4]},
        )

        self.assertEqual([4], settings["semantic_reference_indexes"])
        self.assertEqual("4", workflow["136"]["inputs"]["semantic_ref_indexes"])

    def test_rejects_out_of_range_semantic_picture(self):
        workflow = {
            "136": {
                "class_type": "MiniMaxH3ReferenceToVideo",
                "inputs": {},
            }
        }

        with self.assertRaisesRegex(ValueError, "Picture 1~9"):
            h3_queue._production_workflow_settings(
                workflow,
                {"semantic_reference_indexes": [10]},
            )


if __name__ == "__main__":
    unittest.main()
