from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import model_test_r2v_ai_reviewer as reviewer


class R2VAiReviewerTest(unittest.TestCase):
    def setUp(self):
        self.references = [{
            "picture_index": 1,
            "role": "reference_image_1",
            "label_ko": "캐릭터 A 시트",
            "role_limit_en": "defines identity only",
        }]

    def payload(self):
        return {
            "positive_note": "정체성이 대체로 유지된다.",
            "overall_note": "동작 일부가 가려진다.",
            "scores": {
                "reference_adherence": 4,
                "event_execution": 3,
                "style_fidelity": 4,
            },
            "reference_checks": [{
                "picture_index": 1,
                "status": "matched",
                "evidence_ko": "얼굴과 의상 색이 유지된다.",
            }],
            "subject_binding_checks": [{
                "subject_index": 1,
                "status": "matched",
                "evidence_ko": "캐릭터 역할이 올바르게 유지된다.",
            }],
            "shot_structure_check": {
                "shot_count_order_status": "verified",
                "cut_timing_status": "verified",
                "screen_direction_status": "verified",
                "camera_plan_status": "verified",
                "evidence_ko": "요구된 샷 순서와 컷, 카메라 동작이 맞는다.",
            },
            "event_checks": [{
                "requirement_ko": "열쇠 전달",
                "status": "uncertain",
                "evidence_ko": "손이 잠시 가려진다.",
                "start_seconds": 2,
                "end_seconds": 3,
            }],
            "forbidden_checks": [{
                "failure_ko": "열쇠 복제",
                "status": "absent",
                "evidence_ko": "복제는 보이지 않는다.",
            }],
            "issues": [],
        }

    def normalize(self, payload):
        return reviewer._normalize(
            payload,
            duration=7,
            intent_ko="열쇠를 전달한다.",
            required_events=["열쇠 전달"],
            forbidden_failures=["열쇠 복제"],
            references=self.references,
        )

    def test_v5_rubric_is_general_and_has_no_storyboard_schema(self):
        self.assertEqual(reviewer.RUBRIC_VERSION, "r2v_general_reference_grounded_v5")
        self.assertNotIn("storyboard", reviewer.SYSTEM_PROMPT.lower())
        self.assertIn("Prompt understanding", reviewer.SYSTEM_PROMPT)
        self.assertIn("Action execution", reviewer.SYSTEM_PROMPT)
        self.assertIn("Camera and shot structure", reviewer.SYSTEM_PROMPT)

    def test_uncertainty_requests_human_review_instead_of_reject(self):
        result = self.normalize(self.payload())
        self.assertEqual(result["verdict"], "needs_improvement")
        self.assertTrue(result["enforcement"]["human_review_required"])
        self.assertEqual(result["enforcement"]["required_contradicted"], 0)

    def test_evidenced_major_reference_mismatch_rejects(self):
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["reference_checks"][0].update(
            status="major_mismatch",
            evidence_ko="얼굴형과 의상 색이 기준 인물과 명확히 다르다.",
        )
        result = self.normalize(payload)
        self.assertEqual(result["verdict"], "reject")
        self.assertEqual(result["enforcement"]["reference_major_mismatch"], 1)

    def test_major_mismatch_without_evidence_becomes_uncertain(self):
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["reference_checks"][0].update(status="major_mismatch", evidence_ko="")
        result = self.normalize(payload)
        self.assertEqual(result["verdict"], "needs_improvement")
        self.assertEqual(result["enforcement"]["reference_major_mismatch"], 0)
        self.assertEqual(result["enforcement"]["reference_uncertain"], 1)

    def test_reference_media_excludes_storyboard_and_preserves_visual_picture_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.png"
            second = root / "second.jpg"
            storyboard = root / "missing-storyboard.png"
            first.write_bytes(b"png")
            second.write_bytes(b"jpg")
            request = {
                "benchmark_contract": {
                    "reference_slots": [
                        {"picture_index": 1, "role": "reference_image_1", "label_ko": "인물", "instruction_en": "identity only"},
                        {"picture_index": 2, "role": "reference_image_2", "label_ko": "액션 스토리보드", "instruction_en": "shot plan", "reference_kind": "storyboard"},
                        {"picture_index": 3, "role": "reference_image_3", "label_ko": "배경", "instruction_en": "geometry only"},
                    ],
                },
                "assets": [
                    {"role": "reference_image_3", "source_path": str(second), "sha256": "b"},
                    {"role": "reference_image_2", "source_path": str(storyboard), "sha256": "excluded"},
                    {"role": "reference_image_1", "source_path": str(first), "sha256": "a"},
                ],
            }
            media, descriptions = reviewer._reference_media(request)
        self.assertEqual([item["picture_index"] for item in descriptions], [1, 3])
        self.assertEqual(len(media), 2)
        self.assertIn("identity only", media[0]["label"])
        self.assertTrue(media[0]["url"].startswith("data:image/png;base64,"))
        self.assertFalse(any("storyboard" in str(item).lower() for item in descriptions))

    def test_general_review_prompt_removes_storyboard_scaffolding_but_keeps_shot_actions(self):
        prompt = """<Picture 3> is the storyboard reference for [Shot 1], [Shot 2], and [Shot 3].
[Shot 1] The opening composition follows the 1st storyboard frame in <Picture 3>. Subject 1 runs.
[Shot 2] The cut follows the 2nd storyboard frame in <Picture 3>; Subject 1 dodges.
[Shot 3] The cut follows the 3rd storyboard frame in <Picture 3>; Subject 1 exits."""
        cleaned = reviewer._general_review_prompt(prompt)
        self.assertNotIn("storyboard", cleaned.lower())
        self.assertIn("[Shot 1] Subject 1 runs.", cleaned)
        self.assertIn("[Shot 2] After the cut, Subject 1 dodges.", cleaned)
        self.assertEqual(reviewer._expected_shot_count(cleaned, []), 3)

    def test_review_request_sends_only_general_visual_context_to_ai(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "video.mp4"
            character = root / "character.png"
            video.write_bytes(b"video")
            character.write_bytes(b"image")
            request = {
                "case_title": "공통 R2V",
                "canonical_prompt": (
                    "<Picture 2> is the storyboard reference for [Shot 1], [Shot 2], and [Shot 3].\n"
                    "[Shot 1] The opening composition follows the 1st storyboard frame in <Picture 2>. Subject 1 runs.\n"
                    "[Shot 2] The cut follows the 2nd storyboard frame in <Picture 2>; Subject 1 dodges.\n"
                    "[Shot 3] The cut follows the 3rd storyboard frame in <Picture 2>; Subject 1 exits."
                ),
                "review_intent_ko": "달리고 회피한 뒤 퇴장한다.",
                "benchmark_contract": {
                    "input_mode": "h3_r2v_multi_reference",
                    "visual_style": "stylized_3d",
                    "reference_slots": [
                        {"picture_index": 1, "role": "reference_image_1", "label_ko": "인물", "instruction_en": "identity only"},
                        {"picture_index": 2, "role": "reference_image_2", "label_ko": "액션 스토리보드", "instruction_en": "shot plan", "reference_kind": "storyboard"},
                    ],
                    "required_events": ["열쇠 전달"],
                    "forbidden_failures": ["열쇠 복제"],
                    "dialogue": [],
                },
                "assets": [
                    {"role": "reference_image_1", "source_path": str(character), "sha256": "visual"},
                    {"role": "reference_image_2", "source_path": str(root / "missing-storyboard.png"), "sha256": "excluded"},
                ],
            }
            captured = {}

            def response_json(**kwargs):
                captured.update(kwargs)
                payload = self.payload()
                payload["event_checks"][0]["status"] = "verified"
                return payload, "ok", "{}"

            with (
                mock.patch.object(reviewer.omni, "probe_video", return_value={"has_video": True, "duration_seconds": 7}),
                mock.patch.object(reviewer.omni, "_should_use_audio", return_value=False),
                mock.patch.object(reviewer.omni, "_direct_video_data_url", return_value=("data:video/mp4;base64,dmlkZW8=", {})),
                mock.patch.object(reviewer.omni, "_model_id", return_value="test-model"),
                mock.patch.object(reviewer.omni, "VLLM_VIDEO_REVIEW_TWO_PASS", False),
                mock.patch.object(reviewer.omni, "_response_json", side_effect=response_json),
            ):
                result = reviewer.review_benchmark_video(
                    video_path=video, request=request, batch_id="batch", job_id="job",
                )

        context = json.loads(captured["user_text"].split("\n", 1)[1])
        context_text = json.dumps(context, ensure_ascii=False).lower()
        self.assertNotIn("storyboard", context_text)
        self.assertNotIn("스토리보드", context_text)
        self.assertEqual([item["picture_index"] for item in context["reference_contract"]], [1])
        self.assertEqual(context["expected_shot_count"], 3)
        self.assertEqual(len(captured["image_data_urls"]), 1)
        self.assertEqual(result["review_mode"], "qwen_omni_r2v_general_reference_grounded_v5")
        self.assertEqual(result["reference_count"], 1)

    def test_text_multishot_plan_ignores_only_legacy_no_cut_failure(self):
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["forbidden_checks"] = [
            {"failure_ko": "장면 컷 전환", "status": "observed", "evidence_ko": "두 번 컷됨"},
            {"failure_ko": "열쇠 복제", "status": "absent", "evidence_ko": "복제 없음"},
        ]
        result = reviewer._normalize(
            payload, duration=7, intent_ko="세 샷 액션", required_events=["열쇠 전달"],
            forbidden_failures=["장면 컷 전환", "열쇠 복제"], references=self.references,
            expected_shot_count=3,
        )
        self.assertEqual(result["verdict"], "acceptable")
        self.assertEqual([item["failure_ko"] for item in result["forbidden_checks"]], ["열쇠 복제"])
        self.assertEqual(result["enforcement"]["ignored_legacy_forbidden"], ["장면 컷 전환"])

    def test_missing_or_reordered_text_shot_is_hard_failure(self):
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["shot_structure_check"].update(
            shot_count_order_status="contradicted",
            evidence_ko="Shot 2가 누락되어 Shot 1에서 Shot 3으로 바로 전환된다.",
        )
        result = self.normalize(payload)
        self.assertEqual(result["verdict"], "reject")
        self.assertTrue(result["enforcement"]["shot_structure_hard_failure"])

    def test_small_cut_timing_drift_needs_improvement_not_reject(self):
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["shot_structure_check"].update(
            cut_timing_status="minor_drift",
            evidence_ko="두 번째 컷이 계획보다 약간 늦지만 샷 순서와 행동 경계는 유지된다.",
        )
        result = self.normalize(payload)
        self.assertEqual(result["verdict"], "needs_improvement")
        self.assertFalse(result["enforcement"]["shot_structure_hard_failure"])
        self.assertTrue(result["enforcement"]["shot_structure_soft_failure"])

    def test_storyboard_contract_and_payload_checks_are_ignored(self):
        references = [
            *self.references,
            {
                "picture_index": 3,
                "role": "reference_image_3",
                "label_ko": "액션 스토리보드",
                "role_limit_en": "defines chronological action only",
                "reference_kind": "storyboard",
                "storyboard_panel_count": 3,
            },
        ]
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["reference_checks"].append({
            "picture_index": 3, "status": "major_mismatch", "evidence_ko": "무시 대상",
            "panel_beat_checks": [
                {"panel_index": 1, "status": "contradicted", "evidence_ko": "무시 대상"},
            ],
        })
        result = reviewer._normalize(
            payload, duration=7, intent_ko="액션을 수행한다.", required_events=["열쇠 전달"],
            forbidden_failures=["열쇠 복제"], references=references,
        )
        self.assertEqual(result["verdict"], "acceptable")
        self.assertEqual(result["enforcement"]["reference_total"], 1)
        self.assertEqual([item["picture_index"] for item in result["reference_checks"]], [1])
        self.assertFalse(any("storyboard" in key for key in result["enforcement"]))

    def test_dialogue_wrong_speaker_is_hard_failure_and_legacy_layout_field_is_ignored(self):
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["dialogue_checks"] = [{
            "speaker": "A", "speaker_identity_status": "contradicted",
            "exact_text_status": "verified", "order_status": "verified",
            "lip_sync_status": "verified", "non_speaker_mouth_status": "verified",
            "evidence_ko": "B의 얼굴에서 A의 대사가 발화된다.",
        }]
        payload["shot_structure_check"].update(
            storyboard_layout_leak="observed",
            evidence_ko="화자가 잘못 연결된다.",
        )
        result = reviewer._normalize(
            payload, duration=7, intent_ko="대화", required_events=["열쇠 전달"],
            forbidden_failures=["열쇠 복제"], references=self.references,
            dialogue=[{"speaker": "A", "line_ko": "준비됐어?"}],
        )
        self.assertEqual(result["verdict"], "reject")
        self.assertEqual(result["enforcement"]["dialogue_hard_contradicted"], 1)
        self.assertFalse(result["enforcement"]["shot_structure_hard_failure"])
        self.assertNotIn("storyboard_layout_leak", result["shot_structure_check"])

    def test_lip_sync_contradiction_is_improvement_not_reject(self):
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["dialogue_checks"] = [{
            "speaker": "A", "speaker_identity_status": "verified",
            "exact_text_status": "verified", "order_status": "verified",
            "lip_sync_status": "contradicted", "non_speaker_mouth_status": "verified",
            "evidence_ko": "입 모양이 음성보다 약 0.4초 늦다.",
        }]
        result = reviewer._normalize(
            payload, duration=7, intent_ko="대화", required_events=["열쇠 전달"],
            forbidden_failures=["열쇠 복제"], references=self.references,
            dialogue=[{"speaker": "A", "line_ko": "준비됐어?"}],
        )
        self.assertEqual(result["verdict"], "needs_improvement")
        self.assertEqual(result["enforcement"]["dialogue_soft_contradicted"], 1)


if __name__ == "__main__":
    unittest.main()
