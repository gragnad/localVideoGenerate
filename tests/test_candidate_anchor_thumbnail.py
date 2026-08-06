from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CandidateAnchorThumbnailTests(unittest.TestCase):
    def test_server_selects_msr_anchor_for_thumbnail(self):
        server = (ROOT / "web/server.mjs").read_text(encoding="utf-8")
        self.assertIn("async function serveJobThumbnail", server)
        self.assertIn("item?.role||'')==='anchor'", server)
        self.assertIn("/thumbnail$/", server)

    def test_candidate_preview_uses_thumbnail_endpoint(self):
        app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn("/thumbnail?max=${max}", app)
        self.assertNotIn("/source-images/0?max=${max}", app)
        self.assertIn(">썸네일로</button>", app)


if __name__ == "__main__":
    unittest.main()
