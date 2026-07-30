from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MSRSequenceUITest(unittest.TestCase):
    def test_page_exposes_clean_slate_continuity_editor(self):
        html = (ROOT / "web/public/index.html").read_text(encoding="utf-8")
        self.assertIn("MSR CONTINUITY V1", html)
        self.assertIn("Director 프롬프트를 상속하지 않습니다", html)
        self.assertIn('name="world_prompt"', html)
        self.assertIn("캐릭터 1 · 필수", html)
        self.assertIn("캐릭터 2 · 선택", html)
        self.assertIn("소품 3 · 선택", html)
        self.assertIn("소품 4 · 선택", html)
        self.assertIn("통합 앵커 이미지", html)
        self.assertIn("최대 20초 프롬프트 릴레이", html)

    def test_browser_submits_only_new_strategy_endpoint(self):
        app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn("prompt_strategy:'msr_continuity_v1'", app)
        self.assertIn("workflow:'msr_sequence_v2'", app)
        self.assertIn("director_prompt_inheritance:false", app)
        self.assertIn("/api/msr-sequence-v2/candidate-sets", app)
        self.assertIn("/api/msr-sequence-projects", app)
        self.assertNotIn("api('/api/msr-v2/candidate-sets'", app)
        self.assertIn("기존 Director/MSR 방식입니다", app)
        self.assertIn("등록 즉시 생성 가능", app)
        self.assertIn("즉시 생성 가능합니다", app)
        self.assertIn("reviewed:'생성 가능'", app)
        self.assertIn("awaiting_background:'앵커 미등록'", app)
        self.assertNotIn("검수 상태는 대기로 초기화되었습니다", app)

    def test_server_routes_new_action_separately(self):
        server = (ROOT / "web/server.mjs").read_text(encoding="utf-8")
        backend = (ROOT / "ui_backend.py").read_text(encoding="utf-8")
        self.assertIn("/api/msr-sequence-v2/candidate-sets", server)
        self.assertIn("/api/msr-sequence-projects", server)
        self.assertIn("create_msr_sequence_candidates", server)
        self.assertIn("list_msr_sequence_projects", server)
        self.assertIn('"create_msr_sequence_candidates":create_msr_sequence_candidates_action', backend)


if __name__ == "__main__":
    unittest.main()
