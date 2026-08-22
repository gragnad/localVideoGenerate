from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "deploy/windows-prompt-agent/prompt_revision_agent.py"
SPEC = importlib.util.spec_from_file_location("prompt_revision_agent", MODULE_PATH)
assert SPEC and SPEC.loader
AGENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AGENT)


class PromptRevisionAgentContractTest(unittest.TestCase):
    def test_remote_authoring_uses_scenario_not_source_prompt(self):
        text = AGENT._prompt({
            "expected_variant_ids": ["D", "E", "F"],
            "feedback": "대사와 달리는 행동을 같은 샷에서 보여줘.",
            "clip_context": {
                "scenario_ko": "루아가 달리며 경고하고 창으로 길을 연다.",
                "reference_contract": [{
                    "picture_index": 1,
                    "role": "lua",
                    "description": "루아 캐릭터 시트",
                }],
            },
            "source_prompt_variants": [{
                "video_prompt": "OLD_PROMPT_MUST_NOT_BE_SENT"
            }] * 3,
        })

        self.assertNotIn("OLD_PROMPT_MUST_NOT_BE_SENT", text)
        self.assertIn("brand-new", text)
        self.assertIn("dialogue and visible action coincide", text)
        self.assertIn("preparation, whole-body execution", text)
        self.assertIn("scenario_ko", text)


if __name__ == "__main__":
    unittest.main()
