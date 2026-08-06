from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class UIStateEventsTest(unittest.TestCase):
    def test_server_exposes_event_stream_from_state_file_changes(self):
        server = (ROOT / "web/server.mjs").read_text(encoding="utf-8")
        self.assertIn("text/event-stream", server)
        self.assertIn("state_changed", server)
        self.assertIn("startStateEventWatchers", server)
        self.assertIn("status.json", server)
        self.assertIn("candidate_set.json", server)

    def test_candidate_page_refreshes_only_after_event(self):
        js = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn("new EventSource('/api/events')", js)
        self.assertIn("refreshCandidatesFromEvent", js)
        self.assertIn("currentPage==='candidates'", js)
        self.assertIn("['job','candidate_set'].includes(detail.resource)", js)
        self.assertNotIn("setInterval(refreshCandidatesFromEvent", js)

    def test_state_read_reconciles_candidate_set_statuses(self):
        server = (ROOT / "web/server.mjs").read_text(encoding="utf-8")
        self.assertIn("await python('sync_candidate_sets',{})", server)
        self.assertIn("async function candidateSets()", server)


if __name__ == "__main__":
    unittest.main()
