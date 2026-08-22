from __future__ import annotations

import unittest

import review_contract


class ReviewContractTest(unittest.TestCase):
    def payload(self):
        return {
            "verdict": "needs_improvement",
            "positive_note": "정체성은 유지됨",
            "overall_note": "접촉 동작을 개선해야 함",
            "issues": [{
                "category": "motion_physics",
                "subcategory": "ground_contact_missing",
                "severity": "major",
                "start_seconds": 1.23456,
                "end_seconds": 2.5,
                "expected": "손이 바닥에 닿는다.",
                "observed": "손이 바닥 위에 떠 있다.",
            }],
        }

    def test_review_is_normalized_for_human_and_ai_savers(self):
        review = review_contract.normalize_review(self.payload())
        self.assertEqual("issue_01", review["issues"][0]["issue_id"])
        self.assertEqual(1.235, review["issues"][0]["start_seconds"])
        self.assertEqual("needs_improvement", review["verdict"])

    def test_invalid_category_and_time_range_are_rejected(self):
        payload = self.payload()
        payload["issues"][0]["category"] = "unknown"
        with self.assertRaisesRegex(ValueError, "문제 유형"):
            review_contract.normalize_review(payload)
        payload = self.payload()
        payload["issues"][0]["end_seconds"] = 0.5
        with self.assertRaisesRegex(ValueError, "종료 시간"):
            review_contract.normalize_review(payload)

    def test_issue_count_and_text_limits_are_enforced(self):
        payload = self.payload()
        payload["issues"] *= review_contract.MAX_ISSUES + 1
        with self.assertRaisesRegex(ValueError, "최대"):
            review_contract.normalize_review(payload)
        payload = self.payload()
        payload["overall_note"] = "x" * (review_contract.MAX_TEXT + 1)
        with self.assertRaisesRegex(ValueError, "이하여야"):
            review_contract.normalize_review(payload)


if __name__ == "__main__":
    unittest.main()
