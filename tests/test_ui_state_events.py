from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class UIStateEventsTest(unittest.TestCase):
    def test_server_watches_only_h3_state(self):
        server = (ROOT / "web/server.mjs").read_text(encoding="utf-8")
        self.assertIn("text/event-stream", server)
        self.assertIn("state_changed", server)
        for kind in ("h3_job", "h3_candidate_set", "h3_test_queue"):
            self.assertIn(kind, server)
        for kind in ("h3_candidate_review", "model_review_queue"):
            self.assertNotIn(kind, server)
        self.assertNotIn("runtime/batches", server)

    def test_frontend_uses_one_debounced_h3_state_refresh(self):
        js = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn("new EventSource('/api/events')", js)
        self.assertIn("scheduleH3StateEventRefresh", js)
        self.assertIn("await refreshH3State()", js)
        self.assertNotIn("setInterval(refreshH3State", js)


if __name__ == "__main__":
    unittest.main()
