from __future__ import annotations

import json
import base64
from io import BytesIO
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

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
                "action_flow_status": "verified",
                "pacing_status": "verified",
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

    def test_v7_rubric_makes_storyboard_and_action_flow_primary_axes(self):
        self.assertEqual(reviewer.RUBRIC_VERSION, "r2v_storyboard_action_flow_v7")
        self.assertIn("storyboard", reviewer.SYSTEM_PROMPT.lower())
        self.assertIn("Storyboard adherence", reviewer.SYSTEM_PROMPT)
        self.assertIn("Prompt understanding", reviewer.SYSTEM_PROMPT)
        self.assertIn("Action execution", reviewer.SYSTEM_PROMPT)
        self.assertIn("action_flow_status", reviewer.SYSTEM_PROMPT)
        self.assertIn("slow motion", reviewer.SYSTEM_PROMPT)
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

    def test_reference_media_includes_storyboard_and_preserves_picture_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.png"
            second = root / "second.jpg"
            storyboard = root / "storyboard.png"
            first.write_bytes(b"png")
            second.write_bytes(b"jpg")
            storyboard.write_bytes(b"storyboard")
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
                    {"role": "reference_image_2", "source_path": str(storyboard), "sha256": "storyboard"},
                    {"role": "reference_image_1", "source_path": str(first), "sha256": "a"},
                ],
            }
            media, descriptions = reviewer._reference_media(request)
        self.assertEqual([item["picture_index"] for item in descriptions], [1, 2, 3])
        self.assertEqual(len(media), 3)
        self.assertIn("identity only", media[0]["label"])
        self.assertTrue(media[0]["url"].startswith("data:image/png;base64,"))
        self.assertEqual("storyboard", descriptions[1]["reference_kind"])

    def test_review_reference_copy_is_bounded_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "large.png"
            Image.new("RGB", (1672, 941), "navy").save(source)
            original = source.read_bytes()

            data_url = reviewer._review_reference_data_url(source)
            encoded = base64.b64decode(data_url.split(",", 1)[1])
            with Image.open(BytesIO(encoded)) as review_image:
                self.assertLessEqual(max(review_image.size), 960)

            self.assertEqual(source.read_bytes(), original)

    def test_review_prompt_preserves_storyboard_instructions_and_shot_actions(self):
        prompt = """<Picture 3> is the storyboard reference for [Shot 1], [Shot 2], and [Shot 3].
[Shot 1] The opening composition follows the 1st storyboard frame in <Picture 3>. Subject 1 runs.
[Shot 2] The cut follows the 2nd storyboard frame in <Picture 3>; Subject 1 dodges.
[Shot 3] The cut follows the 3rd storyboard frame in <Picture 3>; Subject 1 exits."""
        cleaned = reviewer._general_review_prompt(prompt)
        self.assertIn("storyboard", cleaned.lower())
        self.assertIn("[Shot 1] The opening composition follows", cleaned)
        self.assertIn("[Shot 2] The cut follows", cleaned)
        self.assertEqual(reviewer._expected_shot_count(cleaned, []), 3)

    def test_review_request_sends_storyboard_context_and_media_to_ai(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "video.mp4"
            character = root / "character.png"
            storyboard = root / "storyboard.png"
            video.write_bytes(b"video")
            character.write_bytes(b"image")
            storyboard.write_bytes(b"storyboard")
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
                        {"picture_index": 2, "role": "reference_image_2", "label_ko": "액션 스토리보드", "instruction_en": "shot plan", "reference_kind": "storyboard", "storyboard_panel_count": 3, "storyboard_reading_order": "left_to_right"},
                    ],
                    "required_events": ["열쇠 전달"],
                    "forbidden_failures": ["열쇠 복제"],
                    "dialogue": [],
                },
                "assets": [
                    {"role": "reference_image_1", "source_path": str(character), "sha256": "visual"},
                    {"role": "reference_image_2", "source_path": str(storyboard), "sha256": "storyboard"},
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
                mock.patch.object(
                    reviewer.omni, "_response_json", side_effect=response_json,
                ) as response_mock,
            ):
                result = reviewer.review_benchmark_video(
                    video_path=video, request=request, review_queue_id="review-queue", job_id="job",
                )

        context = json.loads(captured["user_text"].split("\n", 1)[1])
        context_text = json.dumps(context, ensure_ascii=False).lower()
        self.assertIn("storyboard", context_text)
        self.assertIn("스토리보드", context_text)
        self.assertEqual([item["picture_index"] for item in context["reference_contract"]], [1, 2])
        self.assertEqual(context["expected_shot_count"], 3)
        self.assertEqual(len(captured["image_data_urls"]), 2)
        self.assertEqual(result["review_mode"], "qwen_omni_r2v_storyboard_action_flow_v7")
        self.assertEqual(result["reference_count"], 2)
        self.assertEqual(result["review_queue_id"], "review-queue")
        self.assertNotIn("batch_id", result)
        self.assertIsNone(result["observation"])
        response_mock.assert_called_once()

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

    def test_action_restart_between_storyboard_shots_is_hard_failure(self):
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["shot_structure_check"].update(
            action_flow_status="contradicted",
            evidence_ko="각 컷에서 방패 접촉 전 준비 자세로 되돌아가 동작이 반복 시작된다.",
        )
        result = self.normalize(payload)
        self.assertEqual(result["verdict"], "reject")
        self.assertTrue(result["enforcement"]["shot_structure_hard_failure"])

    def test_unrequested_slow_pacing_needs_improvement_not_reject(self):
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["shot_structure_check"].update(
            pacing_status="contradicted",
            evidence_ko="빠른 압박 동작 사이에 긴 정지와 슬로모션이 반복된다.",
        )
        result = self.normalize(payload)
        self.assertEqual(result["verdict"], "needs_improvement")
        self.assertFalse(result["enforcement"]["shot_structure_hard_failure"])
        self.assertTrue(result["enforcement"]["shot_structure_soft_failure"])

    def test_storyboard_panel_contradiction_is_a_hard_failure(self):
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
        self.assertEqual(result["verdict"], "reject")
        self.assertEqual(result["enforcement"]["reference_total"], 2)
        self.assertEqual([item["picture_index"] for item in result["reference_checks"]], [1, 3])
        self.assertEqual(result["enforcement"]["storyboard_panel_total"], 3)
        self.assertEqual(result["enforcement"]["storyboard_panel_contradicted"], 1)

    def test_all_storyboard_panels_verified_can_pass_the_gate(self):
        references = [
            *self.references,
            {
                "picture_index": 2,
                "role": "reference_image_2",
                "label_ko": "4패널 스토리보드",
                "role_limit_en": "defines four ordered visual checkpoints",
                "reference_kind": "storyboard",
                "storyboard_panel_count": 4,
            },
        ]
        payload = self.payload()
        payload["event_checks"][0]["status"] = "verified"
        payload["reference_checks"].append({
            "picture_index": 2,
            "status": "matched",
            "evidence_ko": "네 패널의 행동 상태와 순서가 모두 확인된다.",
            "panel_beat_checks": [
                {
                    "panel_index": index,
                    "status": "verified",
                    "evidence_ko": f"패널 {index} 상태가 해당 구간에 재현된다.",
                    "start_seconds": index - 1,
                    "end_seconds": index,
                }
                for index in range(1, 5)
            ],
        })
        payload["shot_structure_check"]["storyboard_layout_leak"] = "absent"
        result = reviewer._normalize(
            payload, duration=7, intent_ko="네 패널을 순서대로 재현한다.",
            required_events=["열쇠 전달"], forbidden_failures=["열쇠 복제"],
            references=references, expected_shot_count=4,
        )
        self.assertEqual(result["verdict"], "acceptable")
        self.assertEqual(result["enforcement"]["storyboard_panel_verified"], 4)
        self.assertEqual(result["enforcement"]["storyboard_panel_total"], 4)

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
