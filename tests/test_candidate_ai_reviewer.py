from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

import candidate_ai_reviewer


class CandidateAiReviewerTest(unittest.TestCase):
    def test_scenario_context_uses_previous_current_and_latest_next_story(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "prompt_projects/dragon"
            (project / "SCENE_001").mkdir(parents=True)
            (project / "manifest.json").write_text(
                json.dumps({
                    "project_kind": "h3_r2v_production",
                    "title": "Dragon",
                }),
                encoding="utf-8",
            )

            def prompt(summary: str, action: str) -> str:
                return f"""subject_definitions:
<Subject 1> is Lua from <Picture 1>. A young spear fighter.

summary:
[reference generation] {summary}

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - Preserve Lua's identity.

detailed_description:
[Shot 1] A locked wide view frames <Subject 1> Lua. {action}

overall_soundscape:
N/A

non_diegetic_music:
N/A"""

            for sequence, clip_id, summary, action in (
                (1, "CLIP_001", "Previous summary.", "Previous ending clue remains."),
                (2, "CLIP_002", "Project middle summary.", "Project middle action."),
                (3, "CLIP_003", "Old next summary.", "Old next opening."),
            ):
                payload = {
                    "schema_version": 1,
                    "workflow": "h3_r2v_production",
                    "project_id": "dragon",
                    "scene_id": "SCENE_001",
                    "clip_id": clip_id,
                    "sequence": sequence,
                    "duration_seconds": 5,
                    "video_prompt": prompt(summary, action),
                    "references": [],
                }
                (project / "SCENE_001" / f"{clip_id}.md").write_text(
                    "## Machine Payload\n\n```json\n"
                    + json.dumps(payload)
                    + "\n```\n",
                    encoding="utf-8",
                )

            revision = root / "runtime/h3/prompt_revision_requests/revision-next"
            revision.mkdir(parents=True)
            (revision / "request.json").write_text(json.dumps({
                "source_project_id": "dragon",
                "source_scene_id": "SCENE_001",
                "source_clip_id": "CLIP_003",
                "next_candidate_round": 2,
            }), encoding="utf-8")
            (revision / "authored_variants.json").write_text(json.dumps({
                "prompt_variants": [
                    {"variant_id": letter, "video_prompt": prompt(
                        "Latest next summary.", "Latest next opening cause."
                    )}
                    for letter in ("D", "E", "F")
                ],
            }), encoding="utf-8")

            context = candidate_ai_reviewer._scenario_context(root, {
                "source_project_id": "dragon",
                "source_scene_id": "SCENE_001",
                "source_clip_id": "CLIP_002",
                "prompt": prompt(
                    "Generated current summary.",
                    "Generated current ending clue.",
                ),
            })

            self.assertEqual("CLIP_001", context["previous"]["clip_id"])
            self.assertIn(
                "Previous ending clue", context["previous"]["ending_event"]
            )
            self.assertEqual(
                "Generated current summary.", context["current"]["summary"]
            )
            self.assertEqual("CLIP_003", context["next"]["clip_id"])
            self.assertEqual(
                "Latest next summary.", context["next"]["summary"]
            )
            self.assertIn(
                "Latest next opening cause", context["next"]["opening_event"]
            )

    def test_scenario_parser_keeps_each_natural_shot_separate(self):
        prompt = """subject_definitions:
<Subject 1> is Lua from <Picture 1>. A spear fighter.

summary:
[reference generation] Lua crosses a blocked passage.

retention_analysis:
<Subject 1> (appears in [Shot 1], [Shot 2]): fully_preserved - Keep her identity.

detailed_description:
Cold moonlight reflects from wet stone.

[Shot 1] A low side view frames <Subject 1> Lua charging the spear tip.

[Shot 2] At 00:02.000, a frontal wide view frames <Subject 1> Lua as the fragments burst outward, leaving the open passage visible.

overall_soundscape:
Stone cracks and the spear hums.

non_diegetic_music:
Fast low strings."""

        scenario = candidate_ai_reviewer._scenario_from_prompt(prompt)

        self.assertEqual(2, len(scenario["shot_actions"]))
        self.assertIn("charging the spear tip", scenario["opening_event"])
        self.assertIn("open passage visible", scenario["ending_event"])

    def test_direct_video_review_normalizes_scores_timestamps_and_verdict(self):
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "candidate.mp4"
            video.write_bytes(b"video")
            response = {
                "verdict": "unexpected",
                "summary_ko": "동작은 보이지만 정체성이 흔들립니다.",
                "positive_note_ko": "카메라 이동은 읽힙니다.",
                "scenario_assessment_ko": "현재 사건은 부분적으로 읽힙니다.",
                "incoming_continuity_ko": "이전 상태는 확인할 수 없습니다.",
                "outgoing_continuity_ko": "다음 사건 단서가 약합니다.",
                "scores": {
                    "scenario_realization": 6,
                    "incoming_continuity": 2,
                    "outgoing_continuity": 4,
                    "causal_readability": 3,
                    "continuity_stability": 4,
                },
                "issues": [{
                    "severity": "unknown",
                    "start_seconds": -2,
                    "end_seconds": 99,
                    "observed_ko": "얼굴이 바뀝니다.",
                    "expected_ko": "동일 인물 유지",
                    "suggestion_ko": "정체성 고정 강화",
                }],
                "revision_feedback_ko": "주인공 얼굴 정체성 고정을 강화하세요.",
                "confidence": 2,
            }
            with (
                patch.object(
                    candidate_ai_reviewer.omni,
                    "probe_video",
                    return_value={"has_video": True, "duration_seconds": 5},
                ),
                patch.object(candidate_ai_reviewer.omni, "_should_use_audio", return_value=False),
                patch.object(
                    candidate_ai_reviewer.omni,
                    "_direct_video_data_url",
                    return_value=("data:video/mp4;base64,AA==", {"kind": "video"}),
                ),
                patch.object(candidate_ai_reviewer.omni, "_model_id", return_value="qwen-test"),
                patch.object(candidate_ai_reviewer.omni, "VLLM_REVIEW_STORE_RAW_MESSAGE", False),
                patch.object(
                    candidate_ai_reviewer.omni,
                    "_response_json",
                    return_value=(response, {}, "raw"),
                ) as response_json,
            ):
                report = candidate_ai_reviewer.review_candidate_video(
                    video_path=video,
                    request={"prompt": "Hero walks forward.", "references": []},
                    review_id="review-1",
                    job_id="job-1",
                )

            self.assertEqual("needs_revision", report["verdict"])
            self.assertEqual(5, report["scores"]["scenario_realization"])
            self.assertEqual(
                "candidate_story_continuity_v3", report["rubric_version"]
            )
            self.assertNotIn("audio_dialogue", report["scores"])
            self.assertEqual(
                [
                    "scenario_realization",
                    "causal_readability",
                    "continuity_stability",
                ],
                report["score_applicability"],
            )
            self.assertEqual(
                ["video", "image", "scenario_context"],
                report["review_capabilities"],
            )
            self.assertEqual("major", report["issues"][0]["severity"])
            self.assertEqual(0, report["issues"][0]["start_seconds"])
            self.assertEqual(5, report["issues"][0]["end_seconds"])
            self.assertEqual(1, report["confidence"])
            self.assertEqual("", report["raw_response"])
            self.assertIsNone(report["observation"])
            response_json.assert_called_once()


if __name__ == "__main__":
    unittest.main()
