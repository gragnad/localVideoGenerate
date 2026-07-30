from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

import msr_prompt_projects


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "RaisingaDragonSeason01_EP01_v4"
V3_PROJECT_ID = "RaisingaDragonSeason01_EP01_v3"
SCENARIO_DIR = ROOT / "RaisingaDragonSeason01"

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
META_LABEL = re.compile(
    r"^(Environment establishing|Character preparation|Main action|Dialogue beat|Consequence|Recovery):",
    re.M,
)
SPEAR_CLIPS = {"SC01-002_01", "SC01-002_02", "SC01-003_01", "SC01-003_02"}
LUA_MIR_ANATOMY_MARKERS = [
    "exactly two distinct subjects",
    "no dragon wings",
    "small dragon",
    "do not merge",
    "do not transfer",
]

CHARACTER_SHEET_HASHES: dict[str, str] = {}


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Ep01V4PromptProjectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_dir = ROOT / "prompt_projects" / PROJECT_ID
        if not cls.project_dir.is_dir():
            raise unittest.SkipTest("EP01 V3 project not generated")
        cls.clips = msr_prompt_projects.scan_project_clips(ROOT, PROJECT_ID)
        cls.clip_payloads: dict[str, dict] = {}
        for md_path in sorted(cls.project_dir.rglob("*.md")):
            text = md_path.read_text(encoding="utf-8")
            payload = msr_prompt_projects.extract_machine_payload(text)
            cls.clip_payloads[payload["clip_id"]] = payload
        cls.manifest = json.loads((cls.project_dir / "manifest.json").read_text(encoding="utf-8"))
        cls.bg_catalog = msr_prompt_projects.load_background_catalog(ROOT, PROJECT_ID)
        for name in ("Lua.png", "YoungMir.png"):
            p = SCENARIO_DIR / name
            if p.is_file():
                CHARACTER_SHEET_HASHES[name] = _file_hash(p)

    def test_v3_project_unchanged(self):
        v3_manifest = ROOT / "prompt_projects" / V3_PROJECT_ID / "manifest.json"
        self.assertTrue(v3_manifest.is_file())
        v3_clips = msr_prompt_projects.scan_project_clips(ROOT, V3_PROJECT_ID)
        self.assertEqual(len(v3_clips), 24)

    def test_manifest_metadata(self):
        self.assertEqual(self.manifest["project_id"], PROJECT_ID)
        self.assertEqual(self.manifest["clip_count"], 24)
        self.assertEqual(self.manifest["supersedes_project"], V3_PROJECT_ID)
        self.assertTrue(self.manifest["policy"].get("identity_lock"))
        total = sum(c["requested_seconds"] for c in self.clips)
        self.assertEqual(self.manifest["total_requested_seconds"], total)
        self.assertGreaterEqual(total, 330)
        self.assertLessEqual(total, 420)
        self.assertIn("BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY", self.manifest["new_backgrounds_required"])
        self.assertIn("BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW", self.manifest["new_backgrounds_required"])

    def test_clip_chain_and_limits(self):
        ids = [c["clip_id"] for c in self.clips]
        self.assertEqual(len(ids), len(set(ids)))
        by_id = {c["clip_id"]: c for c in self.clips}
        for c in self.clips:
            if c.get("previous_clip"):
                self.assertIn(c["previous_clip"], by_id)
            if c.get("next_clip"):
                self.assertIn(c["next_clip"], by_id)
                self.assertEqual(by_id[c["next_clip"]]["previous_clip"], c["clip_id"])
            self.assertLessEqual(float(c["requested_seconds"]), 30.0)
            payload = self.clip_payloads[c["clip_id"]]
            relay_total = sum(float(s["seconds"]) for s in payload["relay_segments"])
            self.assertAlmostEqual(relay_total, float(c["requested_seconds"]), places=2)
            refs = payload["references"]
            self.assertGreater(len(refs), 0)
            self.assertLessEqual(len(refs), 4)
            ref_ids = [int(r["reference_id"]) for r in refs]
            self.assertEqual(ref_ids, list(range(1, len(ref_ids) + 1)))

    def test_spear_reference_on_required_clips(self):
        for clip_id in SPEAR_CLIPS:
            refs = self.clip_payloads[clip_id]["references"]
            spear = next((r for r in refs if r.get("role") == "hero_prop"), None)
            self.assertIsNotNone(spear, msg=clip_id)
            self.assertEqual(spear["source_path"], "RaisingaDragonSeason01/spear.png")
            self.assertTrue((ROOT / spear["source_path"]).is_file())

    def test_black_tide_separated_from_background(self):
        clip = self.clip_payloads["SC01-001_03"]
        self.assertEqual(clip["background"]["background_id"], "BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY")
        names = {r["character_name"] for r in clip["references"]}
        self.assertIn("Black Tide", names)
        self.assertIn("Young Mir", names)
        bg_prompt = clip["background_generation"]["prompt"].lower()
        self.assertIn("no black tide", bg_prompt)
        exclusions = clip.get("background_exclusions") or []
        self.assertIn("Black Tide", exclusions)

    def test_jellyfish_separated_from_background(self):
        clip = self.clip_payloads["SC01-005_04"]
        self.assertEqual(clip["background"]["background_id"], "BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW")
        jelly = next(r for r in clip["references"] if r["character_name"] == "Black Jellyfish")
        self.assertEqual(jelly["role"], "dynamic_entity")
        bg_prompt = clip["background_generation"]["prompt"].lower()
        self.assertIn("no jellyfish", bg_prompt)
        exclusions = clip.get("background_exclusions") or []
        self.assertIn("Black Jellyfish", exclusions)

    def test_sc01_003_contact_split(self):
        cave_clips = sorted(c["clip_id"] for c in self.clips if c["scene_id"] == "SC01-003")
        self.assertEqual(len(cave_clips), 9)
        self.assertEqual(cave_clips[0], "SC01-003_01")
        self.assertEqual(cave_clips[-1], "SC01-003_09")
        vision = self.clip_payloads["SC01-003_07"]
        self.assertEqual(vision["background"]["background_id"], "BG_EP01_MIR_VISION_PALACE_RUINS")
        contact = self.clip_payloads["SC01-003_04"]
        prompts = " ".join(s["prompt"] for s in contact["relay_segments"]).lower()
        self.assertIn("picture 2", prompts)
        self.assertIn("picture 1", prompts)

    def test_shell_needs_confirmation(self):
        clip = self.clip_payloads["SC01-004_02"]
        scanned = next(c for c in self.clips if c["clip_id"] == "SC01-004_02")
        self.assertEqual(scanned["status"], "needs_confirmation")
        self.assertIn("prop_generation", clip)
        prop = clip["prop_generation"]
        self.assertTrue(prop.get("required"))
        self.assertEqual(prop.get("asset_role"), "interactive_prop")
        warnings = clip["review"].get("warnings") or []
        self.assertTrue(any("shell" in w.lower() or "조개" in w for w in warnings))

    def test_global_prompts_no_deprecated_pattern(self):
        for c in self.clips:
            gp = self.clip_payloads[c["clip_id"]]["global_prompt"]
            self.assertNotIn("Fixed appearance:", gp, msg=c["clip_id"])
            self.assertNotRegex(gp, r"Picture \d+ = \w+\s*$", msg=c["clip_id"])
            korean = KOREAN_IN_PROMPT.findall(gp)
            self.assertEqual(korean, [], msg=f"{c['clip_id']} global_prompt has Korean")

    def test_lua_mir_anatomy_separation(self):
        lua_mir_clips = []
        for c in self.clips:
            payload = self.clip_payloads[c["clip_id"]]
            refs = payload["references"]
            has_lua = any(r["character_name"] == "Lua" for r in refs)
            has_mir = any(r["character_name"] == "Young Mir" for r in refs)
            if has_lua and has_mir:
                lua_mir_clips.append(c["clip_id"])
                gp = payload["global_prompt"].lower()
                for marker in LUA_MIR_ANATOMY_MARKERS:
                    self.assertIn(marker, gp, msg=f"{c['clip_id']} missing {marker}")
                review = payload["review"].get("character_review") or {}
                self.assertTrue(review.get("lua_fully_human"))
                self.assertTrue(review.get("young_mir_small_dragon"))
                self.assertTrue(review.get("lua_no_wings"))
                self.assertTrue(review.get("anatomy_does_not_transfer"))
        self.assertGreaterEqual(len(lua_mir_clips), 10)

    def test_relay_prompts_ltx_style(self):
        overcrowded = {
            "SC01-002_02": {5, 6},
            "SC01-003_01": {3},
        }
        for c in self.clips:
            payload = self.clip_payloads[c["clip_id"]]
            for seg in payload["relay_segments"]:
                prompt = seg["prompt"]
                self.assertIsNone(META_LABEL.search(prompt), msg=f"{c['clip_id']} seg {seg['order']}")
                if seg["seconds"] <= 6:
                    dialogue_count = prompt.count("natural Korean")
                    self.assertLessEqual(dialogue_count, 2, msg=f"{c['clip_id']} seg {seg['order']}")

    def test_sc01_002_02_segment4_split(self):
        clip = self.clip_payloads["SC01-002_02"]
        self.assertEqual(len(clip["relay_segments"]), 6)
        seg5 = clip["relay_segments"][4]
        seg6 = clip["relay_segments"][5]
        self.assertIn("동굴", seg5["prompt"] + seg6["prompt"])
        self.assertLessEqual(seg5["prompt"].count("natural Korean"), 2)

    def test_all_dialogue_preserved(self):
        found: set[str] = set()
        for c in self.clips:
            for d in self.clip_payloads[c["clip_id"]].get("dialogue") or []:
                found.add(d["text"])
        for line in EP01_DIALOGUE_LINES:
            self.assertIn(line, found, msg=f"Missing: {line}")

    def test_reference_files_exist(self):
        for c in self.clips:
            for ref in self.clip_payloads[c["clip_id"]]["references"]:
                path = ROOT / ref["source_path"]
                self.assertTrue(path.is_file(), msg=f"{c['clip_id']}: {ref['source_path']}")

    def test_character_sheets_unchanged(self):
        for name, expected in CHARACTER_SHEET_HASHES.items():
            current = _file_hash(SCENARIO_DIR / name)
            self.assertEqual(current, expected, msg=f"{name} was modified")

    def test_character_identity_registry(self):
        registry_path = self.project_dir / "character_identity_registry.json"
        self.assertTrue(registry_path.is_file())
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        chars = registry["characters"]
        self.assertIn("CHAR_LUA", chars)
        self.assertIn("CHAR_VILLAGE_CHILD_1", chars)
        self.assertIn("CHAR_VILLAGE_CHILD_2", chars)
        self.assertIn("CHAR_OLD_FISHERMAN", chars)
        self.assertIn("CHAR_YOUNG_MIR", chars)
        lua = chars["CHAR_LUA"]
        self.assertIn("white shell pendant", " ".join(lua["unique_identity_anchors"]).lower())
        self.assertIn("blue marking", " ".join(lua["unique_identity_anchors"]).lower())

    def test_lua_identity_in_all_lua_clips(self):
        for c in self.clips:
            payload = self.clip_payloads[c["clip_id"]]
            if not any(r["character_name"] == "Lua" for r in payload["references"]):
                continue
            gp = payload["global_prompt"].lower()
            self.assertIn("high loose bun", gp, msg=c["clip_id"])
            self.assertIn("white shell pendant", gp, msg=c["clip_id"])
            self.assertIn("blue marking", gp, msg=c["clip_id"])
            self.assertIn("beige tunic", gp, msg=c["clip_id"])

    def test_sc01_002_01_three_children_identity_lock(self):
        clip = self.clip_payloads["SC01-002_01"]
        gp = clip["global_prompt"].lower()
        self.assertIn("exactly three distinct human children", gp)
        self.assertIn("village child 1 alone has short tousled", gp)
        self.assertIn("village child 2 alone has the high dark ponytail", gp)
        self.assertIn("woven shoulder basket", gp)
        self.assertIn("identity_review", clip["review"])
        relay1 = clip["relay_segments"][0]["prompt"].lower()
        self.assertIn("picture 1", relay1)
        self.assertIn("picture 2", relay1)
        self.assertIn("picture 3", relay1)
        self.assertIn("shoulder basket", relay1)

    def test_village_children_exclusive_traits(self):
        gp002 = self.clip_payloads["SC01-002_01"]["global_prompt"].lower()
        self.assertIn("village child 1 alone has short tousled", gp002)
        self.assertIn("village child 2 alone has the high dark ponytail", gp002)
        self.assertIn("no shoulder basket", gp002.split("picture 2")[1].split("picture 3")[0])
        self.assertIn("woven shoulder basket", gp002.split("picture 3")[1].split("keep all three")[0])

    def test_old_fisherman_adult_distinction(self):
        clip = self.clip_payloads["SC01-002_02"]
        gp = clip["global_prompt"].lower()
        self.assertIn("gray beard", gp)
        self.assertIn("adult proportions", gp)
        self.assertIn("identity_review", clip["review"])

    def test_multi_ref_clips_have_identity_review(self):
        for c in self.clips:
            payload = self.clip_payloads[c["clip_id"]]
            if len(payload["references"]) >= 2:
                self.assertIn("identity_review", payload["review"], msg=c["clip_id"])

    def test_list_projects_includes_v4(self):
        projects = msr_prompt_projects.list_prompt_projects_action(ROOT, {})["projects"]
        ids = {p["project_id"] for p in projects}
        self.assertIn(PROJECT_ID, ids)
        self.assertIn(V3_PROJECT_ID, ids)

    def test_no_reviewed_without_backgrounds(self):
        for c in self.clips:
            self.assertNotEqual(c["status"], "reviewed", msg=c["clip_id"])


if __name__ == "__main__":
    unittest.main()
