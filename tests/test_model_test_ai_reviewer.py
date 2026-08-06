from __future__ import annotations

import unittest

import model_test_ai_reviewer


class ModelTestAiReviewerTest(unittest.TestCase):
    def test_normalize_clamps_scores_times_and_verdict(self):
        result = model_test_ai_reviewer._normalize(
            {
                "verdict": "acceptable",
                "positive_note": "동작 시작은 보인다.",
                "overall_note": "접촉 실패",
                "scores": {
                    "prompt_adherence": 8,
                    "motion_physics": -2,
                    "not_supported": 4,
                    "camera_control": None,
                },
                "issues": [{
                    "category": "motion_physics",
                    "subcategory": "ground_contact_missing",
                    "severity": "major",
                    "start_seconds": 7,
                    "end_seconds": 2,
                    "expected": "손이 지면에 닿는다.",
                    "observed": "손이 떠 있다.",
                }],
            },
            duration=5.0,
            intent_ko="손이 지면에 닿아야 한다.",
        )
        self.assertEqual(result["verdict"], "needs_improvement")
        self.assertEqual(result["scores"]["prompt_adherence"], 5.0)
        self.assertEqual(result["scores"]["motion_physics"], 0.0)
        self.assertNotIn("not_supported", result["scores"])
        self.assertNotIn("camera_control", result["scores"])
        self.assertEqual(result["issues"][0]["start_seconds"], 2.0)
        self.assertEqual(result["issues"][0]["end_seconds"], 5.0)

    def test_unknown_values_fall_back_safely(self):
        result = model_test_ai_reviewer._normalize(
            {
                "verdict": "unknown",
                "scores": {},
                "issues": [{
                    "category": "invented",
                    "subcategory": "",
                    "severity": "invented",
                    "observed": "이상 현상",
                }],
            },
            duration=4.0,
            intent_ko="의도",
        )
        self.assertEqual(result["verdict"], "needs_improvement")
        self.assertEqual(result["issues"][0]["category"], "other")
        self.assertEqual(result["issues"][0]["severity"], "major")
        self.assertEqual(result["issues"][0]["expected"], "의도")


    def test_strict_gate_accepts_only_fully_verified_contract(self):
        result = model_test_ai_reviewer._normalize(
            {
                "scores": {"prompt_adherence": 4.5, "visual_quality": 4.0},
                "event_checks": [{
                    "requirement_ko": "루아가 작살을 던진다.", "status": "verified",
                    "evidence_ko": "2초에 손을 떠난 작살이 앞으로 날아간다.",
                    "start_seconds": 1.8, "end_seconds": 2.3,
                }],
                "forbidden_checks": [{
                    "failure_ko": "작살이 손에 붙어 있다.", "status": "absent",
                    "evidence_ko": "던진 뒤 작살이 손에서 분리된다.",
                    "start_seconds": 2.0, "end_seconds": 2.8,
                }],
                "issues": [],
            },
            duration=5.0, intent_ko="루아가 작살을 던진다.",
            required_events=["루아가 작살을 던진다."],
            forbidden_failures=["작살이 손에 붙어 있다."],
        )
        self.assertEqual(result["verdict"], "acceptable")
        self.assertTrue(result["enforcement"]["gate_passed"])

    def test_missing_required_event_cannot_pass(self):
        result = model_test_ai_reviewer._normalize(
            {
                "scores": {"prompt_adherence": 5.0},
                "event_checks": [{
                    "requirement_ko": "첫 행동", "status": "verified",
                    "evidence_ko": "1초에 확인됨", "start_seconds": 1.0,
                    "end_seconds": 1.2,
                }],
                "issues": [],
            },
            duration=5.0, intent_ko="행동 두 개",
            required_events=["첫 행동", "두 번째 행동"],
        )
        self.assertEqual(result["verdict"], "needs_improvement")
        self.assertEqual(result["scores"]["prompt_adherence"], 3.0)
        self.assertEqual(result["enforcement"]["required_unresolved"], 1)
        self.assertEqual(result["issues"][0]["subcategory"], "event_missing")

    def test_two_missing_events_or_observed_forbidden_failure_rejects(self):
        unresolved = model_test_ai_reviewer._normalize(
            {"scores": {"prompt_adherence": 5.0}, "issues": []},
            duration=5.0, intent_ko="연속 행동",
            required_events=["첫 행동", "두 번째 행동"],
        )
        self.assertEqual(unresolved["verdict"], "reject")
        self.assertEqual(unresolved["scores"]["prompt_adherence"], 2.0)
        forbidden = model_test_ai_reviewer._normalize(
            {
                "scores": {"prompt_adherence": 5.0},
                "forbidden_checks": [{
                    "failure_ko": "인물이 복제된다.", "status": "observed",
                    "evidence_ko": "3초에 동일 인물이 두 명으로 보인다.",
                    "start_seconds": 3.0, "end_seconds": 3.4,
                }],
                "issues": [],
            },
            duration=5.0, intent_ko="한 명만 등장",
            forbidden_failures=["인물이 복제된다."],
        )
        self.assertEqual(forbidden["verdict"], "reject")
        self.assertEqual(forbidden["scores"]["prompt_adherence"], 1.0)

    def test_verified_without_evidence_or_timestamp_becomes_uncertain(self):
        result = model_test_ai_reviewer._normalize(
            {
                "scores": {"prompt_adherence": 5.0},
                "event_checks": [{"requirement_ko": "문을 연다.", "status": "verified"}],
                "issues": [],
            },
            duration=5.0, intent_ko="문을 연다.",
            required_events=["문을 연다."],
        )
        self.assertEqual(result["event_checks"][0]["status"], "uncertain")
        self.assertEqual(result["verdict"], "needs_improvement")


if __name__ == "__main__":
    unittest.main()
