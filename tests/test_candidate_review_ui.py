from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CandidateReviewUITest(unittest.TestCase):
    def test_candidate_cards_expose_structured_review_editor(self):
        html = (ROOT / "web/public/index.html").read_text(encoding="utf-8")
        js = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn('id="candidateReviewDialog"', html)
        self.assertIn('id="candidateReviewAddIssue"', html)
        self.assertIn("data-candidate-review", js)
        self.assertIn("의도한 표현", js)
        self.assertIn("영상의 실제 출력", js)
        self.assertIn("원인 추정", js)
        self.assertIn("다음 프롬프트·설정 개선 제안", js)
        self.assertIn("motion_physics", js)
        self.assertIn("environment_reaction_missing", js)
        self.assertIn("over_smoothed_motion", js)
        self.assertIn("expected_default_ko", js)
        self.assertIn("blankCandidateReviewIssue(candidateReviewContext?.expectedDefaultKo)", js)

    def test_review_api_supports_get_and_put(self):
        server = (ROOT / "web/server.mjs").read_text(encoding="utf-8")
        self.assertIn("candidateReview=url.pathname.match", server)
        self.assertIn("get_candidate_review", server)
        self.assertIn("save_candidate_review", server)
        self.assertIn("req.method==='PUT'", server)

    def test_review_draft_is_preserved_locally(self):
        js = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn("ltx-candidate-review-drafts-v1", js)
        self.assertIn("persistCandidateReviewDraft", js)
        self.assertIn("저장하지 않은 로컬 초안 복원", js)


if __name__ == "__main__":
    unittest.main()
