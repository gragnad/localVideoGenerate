from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UIAccessKeyTest(unittest.TestCase):
    def test_parallel_unauthorized_requests_share_one_prompt(self):
        app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn("let accessKeyPromptPromise=null", app)
        self.assertIn("if(accessKeyPromptPromise)return accessKeyPromptPromise", app)
        self.assertEqual(app.count("prompt('VIDEO UI 접근 키')"), 1)
        self.assertGreaterEqual(app.count("await requestAccessKey()"), 2)

    def test_model_test_delete_waits_for_server_and_deletes_local_artifacts(self):
        app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertNotIn("deletedModelTestSessionIds", app)
        self.assertIn("테스트 세션 완전 삭제", app)
        self.assertIn("생성 영상·ComfyUI 출력 파일이 함께 삭제", app)
        self.assertIn("const out=await api", app)

    def test_model_test_review_refresh_preserves_scroll_and_open_card(self):
        app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn("function modelTestOpenRunIds()", app)
        self.assertIn("#r2vTestResults details[data-model-test-run][open]", app)
        self.assertIn("data-model-test-run", app)
        self.assertIn("{scroll:false,preserveOpen:true}", app)
        self.assertIn("requestAnimationFrame(()=>window.scrollTo(scrollX,scrollY))", app)

    def test_model_test_ai_review_can_stop_and_rerun(self):
        app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        server = (ROOT / "web/server.mjs").read_text(encoding="utf-8")
        self.assertIn("현재 검수 중단", app)
        self.assertIn("새 기준 재검수 실행", app)
        self.assertIn('method:"DELETE"', app)
        self.assertIn("cancel_model_test_ai_review", server)

    def test_model_test_page_uses_safe_lists_collapsible_cases_and_video_thumbnails(self):
        app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        server = (ROOT / "web/server.mjs").read_text(encoding="utf-8")
        index = (ROOT / "web/public/index.html").read_text(encoding="utf-8")
        self.assertNotIn(" $('[data-test-results]').forEach", app)
        self.assertNotIn(" $('[data-test-ai-review-cancel]').forEach", app)
        self.assertIn("toggleModelTestCases", index)
        self.assertIn("modelTestCasesCollapsed", app)
        self.assertIn("model-test-video-thumbnail", app)
        self.assertIn("/video-thumbnail", app)
        self.assertIn("serveJobVideoThumbnail", server)

    def test_create_page_is_clean_h3_release_placeholder(self):
        index = (ROOT / "web/public/index.html").read_text(encoding="utf-8")
        self.assertIn("01 H3 생성", index)
        self.assertIn("H3 공식 워크플로우 공개 대기", index)
        self.assertIn('id="legacyCreateCompatibility" hidden', index)
        visible = index.split('<section data-view="create">', 1)[1].split('<div id="legacyCreateCompatibility"', 1)[0]
        self.assertNotIn("createForm", visible)
        self.assertNotIn("후보군 생성", visible)

    def test_model_test_plan_selects_and_displays_resolution(self):
        index = (ROOT / "web/public/index.html").read_text(encoding="utf-8")
        app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn('id="testSessionResolution"', index)
        self.assertIn('value="832x480"', index)
        self.assertIn('isMiniMaxH3TestModel', app)
        self.assertIn("select.value='832x480'", app)
        self.assertIn("resolutionMatch", app)
        self.assertIn("item.resolution.width", app)
        self.assertIn("syncModelTestSelects();syncModelTestAdapterControls()", app)
        self.assertIn("중복 바인딩을 해제하세요", app)
        self.assertIn("modelTestReferencePromptHtml", app)
        self.assertIn("data-copy-r2v-reference-all", app)
        self.assertIn("R2V 레퍼런스 이미지 생성 Prompt", app)
        self.assertIn("$$('[data-test-case-setting]').forEach", app)
        self.assertIn("$$('[data-test-binding]').forEach", app)
        self.assertNotIn("$('[data-test-case-setting]').forEach", app.replace("$$('[data-test-case-setting]').forEach", ""))

    def test_browser_cache_version_changed(self):
        index = (ROOT / "web/public/index.html").read_text(encoding="utf-8")
        self.assertIn("/app.js?v=20260806-40", index)

    def test_r2v_benchmark_has_a_separate_page_and_session_controls(self):
        index = (ROOT / "web/public/index.html").read_text(encoding="utf-8")
        app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.assertIn('data-page="r2v-tests"', index)
        self.assertIn('data-view="r2v-tests"', index)
        self.assertIn('id="r2vTestSessionForm"', index)
        self.assertIn('id="r2vTestCases"', index)
        self.assertIn('id="r2vTestSessions"', index)
        self.assertIn('id="r2vTestResults"', index)
        self.assertIn("generalModelTestSuites()", app)
        self.assertIn("r2vModelTestSuites()", app)
        self.assertIn("sessions.filter(isR2VSession)", app)
        self.assertIn("R2V 전용 AI 검수", app)


if __name__ == "__main__":
    unittest.main()
