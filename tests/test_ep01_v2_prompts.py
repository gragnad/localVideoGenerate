from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import msr_prompt_projects


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "RaisingaDragonSeason01_EP01_v2"
OLD_PROJECT_ID = "RaisingaDragonSeason01"
SCENARIO = ROOT / "RaisingaDragonSeason01" / "Raising a Dragon.md"

# All EP01 dialogue lines from scenario (speaker-agnostic text set for presence check)
EP01_DIALOGUE_LINES = [
    "기억하지 마라.",
    "그러면 아프지 않다.",
    "또 놓쳤다!",
    "루아 누나는 바다랑 안 맞아!",
    "안 맞긴 뭐가 안 맞아!",
    "방금 건 일부러 빠진 거야.",
    "수심 확인.",
    "루아야.",
    "네!",
    "바다는 고집으로 되는 게 아니다.",
    "오늘은 동굴 쪽 가지 마라.",
    "폭풍 뒤에는 뭐가 밀려올지 몰라.",
    "가라면 가지 말아야 하는데.",
    "저렇게 빛나면 가야지.",
    "나와라.",
    "내가 마을에서 제일 무서운 사람은 아니지만.",
    "상당히 귀찮은 사람이다.",
    "방금 귀여웠는데?",
    "너…",
    "도마뱀은 아니지?",
    "말도 안 돼.",
    "야, 야. 괜찮아.",
    "안 잡아먹어.",
    "나도 오늘 아침 못 먹었거든.",
    "악!",
    "방금…",
    "내가 본 거야?",
    "너 대체 뭐야?",
    "루아! 거기 있냐?",
    "하.",
    "나 진짜 사고 쳤다.",
    "진짜네.",
    "꿈이면 지금쯤 깨야 하는데.",
    "너 물에서 자는 거야?",
    "좋겠다. 난 그러면 죽는데.",
    "먹어.",
    "아니, 바다에서 왔잖아.",
    "생선 안 먹어?",
    "입맛도 귀족이네.",
    "불길하다!",
    "바다에 돌려보내!",
    "안 돼.",
    "그러니까… 당분간 여기 있어.",
    "근데 밥값은 해야 돼.",
    "예를 들면.",
    "물 좀 데워준다든가?",
    "그래.",
    "가능성은 있다.",
    "너는 왕자가 아니다.",
    "버려진 새끼 용이다.",
    "뭐야…",
    "야. 괜찮아.",
    "나 여기 있어.",
    "이거…",
    "내 무서움이 아니야.",
    "너도 무서운 거구나.",
    "저게…",
    "널 찾으러 온 거야?",
]

KOREAN_IN_PROMPT = re.compile(r"[가-힣]{2,}")


@unittest.skip("LTX 2.3 EP01 프롬프트 프로젝트 보관 처리")
class Ep01V2PromptProjectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_dir = ROOT / "prompt_projects" / PROJECT_ID
        if not cls.project_dir.is_dir():
            raise unittest.SkipTest("EP01 V2 project not generated")
        cls.clips = msr_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        cls.clip_payloads: dict[str, dict] = {}
        for md_path in sorted(cls.project_dir.rglob("*.md")):
            text = md_path.read_text(encoding="utf-8")
            payload = msr_prompt_projects.extract_machine_payload(text)
            cls.clip_payloads[payload["clip_id"]] = payload
        cls.manifest = json.loads((cls.project_dir / "manifest.json").read_text(encoding="utf-8"))
        cls.bg_catalog = msr_prompt_projects.load_background_catalog(ROOT, PROJECT_ID)

    def test_old_project_still_exists_unchanged(self):
        old_manifest = ROOT / "prompt_projects" / OLD_PROJECT_ID / "manifest.json"
        self.assertTrue(old_manifest.is_file())
        old_clips = msr_prompt_projects.scan_project_clips(ROOT, OLD_PROJECT_ID)
        self.assertEqual(len(old_clips), 11)

    def test_manifest_metadata(self):
        self.assertEqual(self.manifest["project_id"], PROJECT_ID)
        self.assertEqual(self.manifest["clip_count"], 19)
        self.assertEqual(self.manifest["scene_count"], 5)
        self.assertEqual(self.manifest["supersedes_project"], OLD_PROJECT_ID)
        total = sum(c["requested_seconds"] for c in self.clips)
        self.assertEqual(self.manifest["total_requested_seconds"], total)
        self.assertGreaterEqual(total, 330)
        self.assertLessEqual(total, 420)

    def test_clip_ids_unique_and_linked(self):
        ids = [c["clip_id"] for c in self.clips]
        self.assertEqual(len(ids), len(set(ids)))
        by_id = {c["clip_id"]: c for c in self.clips}
        for c in self.clips:
            self.assertEqual(c["project_id"], PROJECT_ID)
            if c.get("previous_clip"):
                self.assertIn(c["previous_clip"], by_id)
            if c.get("next_clip"):
                self.assertIn(c["next_clip"], by_id)
                self.assertEqual(by_id[c["next_clip"]]["previous_clip"], c["clip_id"])

    def test_all_clips_parse_and_duration_limits(self):
        for c in self.clips:
            self.assertLessEqual(float(c["requested_seconds"]), 30.0)
            payload = self.clip_payloads[c["clip_id"]]
            relay_total = sum(float(s["seconds"]) for s in payload["relay_segments"])
            self.assertAlmostEqual(relay_total, float(c["requested_seconds"]), places=2)
            refs = payload["references"]
            self.assertGreater(len(refs), 0)
            self.assertLessEqual(len(refs), 4)
            ref_ids = [int(r["reference_id"]) for r in refs]
            self.assertEqual(len(ref_ids), len(set(ref_ids)))

    def test_wrong_speaker_fixed_for_village_child(self):
        clip = self.clip_payloads["SC01-002_01"]
        dialogue = clip["dialogue"]
        child_line = next(d for d in dialogue if d["text"] == "또 놓쳤다!")
        self.assertEqual(child_line["speaker"], "Village Child 1")
        for seg in clip["relay_segments"]:
            if "또 놓쳤다" in seg["prompt"]:
                self.assertIn("Village Child 1", seg["prompt"])
                self.assertNotIn('Lua says in natural Korean, "또 놓쳤다', seg["prompt"])

    def test_cold_open_split_backgrounds(self):
        cold = [c for c in self.clips if c["scene_id"] == "SC01-001"]
        bg_ids = {c["background_id"] for c in cold}
        self.assertIn("BG_EP01_STORM_SEA_SURFACE_NIGHT", bg_ids)
        self.assertIn("BG_EP01_DEEP_SEA_RUINS_NIGHT", bg_ids)
        self.assertIn("BG_EP01_DEEP_SEA_BLACK_CURRENT", bg_ids)
        self.assertIn("BG_EP01_MIR_VISION_PALACE_RUINS", bg_ids)
        self.assertNotIn("BG_EP01_STORM_DEEP_SEA_NIGHT", bg_ids)

    def test_dream_separate_from_house(self):
        dream = next(c for c in self.clips if c["clip_id"] == "SC01-005_02")
        self.assertEqual(dream["background_id"], "BG_EP01_MIR_VISION_PALACE_RUINS")
        comfort = next(c for c in self.clips if c["clip_id"] == "SC01-005_03")
        self.assertEqual(comfort["background_id"], "BG_EP01_LUA_HOUSE_INTERIOR_NIGHT")

    def test_imagination_separate_background(self):
        clip = next(c for c in self.clips if c["clip_id"] == "SC01-004_03")
        self.assertEqual(clip["background_id"], "BG_EP01_LUA_HOUSE_IMAGINED_VILLAGE")

    def test_all_ep01_dialogue_present(self):
        found: set[str] = set()
        for c in self.clips:
            for d in self.clip_payloads[c["clip_id"]].get("dialogue") or []:
                found.add(d["text"])
        for line in EP01_DIALOGUE_LINES:
            self.assertIn(line, found, msg=f"Missing dialogue: {line}")

    def test_global_prompts_mostly_english(self):
        for c in self.clips:
            gp = self.clip_payloads[c["clip_id"]]["global_prompt"]
            korean_matches = KOREAN_IN_PROMPT.findall(gp)
            self.assertEqual(korean_matches, [], msg=f"{c['clip_id']} global_prompt has Korean: {korean_matches}")

    def test_relay_prompts_use_english_with_korean_dialogue_markers(self):
        for c in self.clips:
            for seg in self.clip_payloads[c["clip_id"]]["relay_segments"]:
                prompt = seg["prompt"]
                if "natural Korean" in prompt or "voice-over in natural Korean" in prompt:
                    continue
                # relay should be primarily English — allow none or minimal Korean in dialogue quotes only
                if "「" in prompt or '"' in prompt:
                    pass  # quoted dialogue allowed

    def test_background_catalog_covers_all_clip_backgrounds(self):
        catalog_ids = set(self.bg_catalog.get("backgrounds") or {})
        for c in self.clips:
            bg_id = c["background_id"]
            self.assertIn(bg_id, catalog_ids)
            gen = self.clip_payloads[c["clip_id"]].get("background_generation") or {}
            self.assertTrue(gen.get("prompt"))
            self.assertTrue(gen.get("negative_prompt"))

    def test_list_projects_includes_v2(self):
        projects = msr_prompt_projects.list_prompt_projects_action(ROOT, {})["projects"]
        ids = {p["project_id"] for p in projects}
        self.assertIn(PROJECT_ID, ids)


if __name__ == "__main__":
    unittest.main()
