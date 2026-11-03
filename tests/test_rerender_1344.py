import tempfile
import unittest
from pathlib import Path
from unittest import mock

import h3_queue
from job_queue import read_json, update_status


class Rerender1344Tests(unittest.TestCase):
    def test_rerender_1344_preserves_source_and_supports_both_seed_actions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "reference.png"
            image.write_bytes(b"immutable reference")
            profile = {"adapter_id": "r2v", "workflow_profile_id": "r2v", "workflow_filename": "h3.json", "generation_mode": "r2v"}
            with mock.patch.object(h3_queue, "_compile_workflow", return_value=({}, [], profile)), mock.patch.object(h3_queue, "_current_default_r2v_adapter", return_value=profile):
                source = h3_queue.enqueue_candidate_set(root, {"adapter_id": "r2v", "prompt": "Shot 1: Run.",
                    "references": [{"upload_path": str(image), "role": "character"}], "candidate_count": 1,
                    "seed": 123, "width": 1280, "height": 736, "duration_seconds": 5})
                paths = h3_queue.roots(root)
                jid = source["candidate_job_ids"][0]
                update_status(paths["jobs"] / jid, "completed", stage="done")
                h3_queue.select_candidate(root, source["candidate_set_id"], jid)
                before = read_json(paths["jobs"] / jid / "request.json")
                self.assertIn("1344x768", h3_queue.results_page(root, {})["candidate_sets"][0]["rerender_estimates"])
                for randomize in (False, True):
                    out = h3_queue.enqueue_selected_candidate_rerender(root, source["candidate_set_id"],
                        {"source_job_id": jid, "width": 1344, "height": 768, "randomize_seed": randomize})
                    request = read_json(paths["jobs"] / out["candidate_job_ids"][0] / "request.json")
                    self.assertEqual((1344, 768), (request["width"], request["height"]))
                    self.assertEqual("local_generation", request["queue_lane"])
                    self.assertEqual(jid, request["source_selected_job_id"])
                    for key in ("prompt", "duration_seconds"):
                        self.assertEqual(before[key], request[key])
                    self.assertEqual(before["references"][0]["sha256"], request["references"][0]["sha256"])
                    if randomize:
                        self.assertNotEqual(123, request["seed"])
                    else:
                        self.assertEqual(123, request["seed"])
                self.assertEqual(before, read_json(paths["jobs"] / jid / "request.json"))
                self.assertNotIn((1344, 768), h3_queue.R2V_OUTPUT_RESOLUTIONS)


if __name__ == "__main__":
    unittest.main()
