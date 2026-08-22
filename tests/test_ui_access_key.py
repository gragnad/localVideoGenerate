from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class UIContractTest(unittest.TestCase):
    def setUp(self):
        self.app = (ROOT / "web/public/app.js").read_text(encoding="utf-8")
        self.index = (ROOT / "web/public/index.html").read_text(encoding="utf-8")
        self.styles = (ROOT / "web/public/styles.css").read_text(encoding="utf-8")
        self.server = (ROOT / "web/server.mjs").read_text(encoding="utf-8")

    def test_access_key_is_consistent_for_api_and_exports(self):
        self.assertIn("let accessKeyPromptPromise=null", self.app)
        self.assertEqual(1, self.app.count("prompt('VIDEO UI 접근 키')"))
        self.assertGreaterEqual(self.app.count("sessionStorage.getItem('h3-key')"), 2)
        self.assertNotIn("ltx-key", self.app)

    def test_navigation_contains_only_current_h3_and_model_pages(self):
        pages = {
            "create": "01 H3 R2V 생성",
            "i2v-create": "02 H3 I2V 생성",
            "queue": "03 큐 · 진행",
            "candidates": "04 후보 선택",
            "results": "05 결과 확인",
            "model-management": "06 모델 관리",
            "model-tests": "07 모델 테스트",
            "r2v-tests": "08 R2V 테스트",
        }
        for page, label in pages.items():
            self.assertIn(f'data-page="{page}"', self.index)
            self.assertIn(label, self.index)
            self.assertIn(f'data-view="{page}"', self.index)
        for removed in (
            "msr-v2", "master", "revision", "assembly",
            "source-images", "automation",
        ):
            self.assertNotIn(f'data-page="{removed}"', self.index)
            self.assertNotIn(f'data-view="{removed}"', self.index)

    def test_h3_queue_candidate_and_model_review_controls_remain(self):
        for marker in (
            'id="h3CreateForm"', 'id="h3Project"', 'id="h3Scene"',
            'id="i2vCreateForm"', 'id="i2vProject"', 'id="i2vStartImage"',
            'id="h3CandidateSets"', 'id="r2vSharedAssetsPanel"',
            'id="modelTestReviewDialog"', 'id="r2vTestSessionForm"',
        ):
            self.assertIn(marker, self.index)
        self.assertIn("data-force-h3-group", self.app)
        self.assertIn("/api/h3/queue-groups/", self.app)
        self.assertIn("/api/model-tests/sessions/", self.app)
        self.assertIn("AI 검수 큐 등록", self.app)
        self.assertIn("canAi=(item.run_count||0)>0", self.app)

        backend = (ROOT / "ui_backend.py").read_text(encoding="utf-8")
        h3_config = backend.split("def h3_config", 1)[1].split(
            "def h3_state", 1
        )[0]
        self.assertIn(
            "model_test_registry.ensure_h3_r2v_adapter(ROOT, WORKFLOW_DIR)",
            h3_config,
        )
        self.assertIn(
            "model_test_registry.ensure_h3_i2v_adapter(ROOT, WORKFLOW_DIR)",
            h3_config,
        )

    def test_candidate_page_has_continuous_local_ai_review_toggle_and_feedback(self):
        self.assertIn('id="h3CandidateAiReviewToggle"', self.index)
        self.assertIn('id="h3CandidateAiReviewStatus"', self.index)
        self.assertIn("/api/h3/candidate-ai-review", self.app)
        self.assertIn("function toggleH3CandidateAiReview", self.app)
        self.assertIn("function decorateH3CandidateAiReviews", self.app)
        self.assertIn("검수 AI 수정의견", self.app)
        self.assertIn("candidate_story_continuity_v3", self.app)
        self.assertIn("현재 시나리오 연출", self.app)
        self.assertIn("이전 클립 연결", self.app)
        self.assertIn("다음 클립 연결", self.app)
        self.assertIn("검수 AI 시나리오·연결 의견", self.app)
        self.assertIn("수정 의견에 반영", self.app)
        self.assertIn("h3_candidate_review", self.server)
        self.assertIn("'set_h3_candidate_ai_review'", self.server)
        backend = (ROOT / "ui_backend.py").read_text(encoding="utf-8")
        self.assertIn("def set_h3_candidate_ai_review", backend)
        self.assertIn('"set_h3_candidate_ai_review": set_h3_candidate_ai_review', backend)
        self.assertIn("candidate_ai_review", (ROOT / "h3_queue.py").read_text(encoding="utf-8"))
        self.assertIn(".h3-candidate-ai-feedback{", self.styles)

    def test_individual_h3_r2v_duration_allows_half_seconds(self):
        r2v_form = self.index.split('<form id="h3CreateForm"', 1)[1].split(
            "</form>", 1
        )[0]
        self.assertIn(
            '<option value="608x352" selected>608 × 352 · 초고속 후보</option>',
            r2v_form,
        )
        self.assertNotIn('<option value="1280x704" selected>', r2v_form)
        self.assertIn(
            'name="duration_seconds" type="number" min="1" max="15" step="0.5"',
            r2v_form,
        )
        self.assertIn("duration_seconds:Number(form.get('duration_seconds'))", self.app)

    def test_r2v_allows_matching_candidate_prompts_feedback_rounds_and_versions(self):
        for marker in (
            'name="prompt_a"', 'name="prompt_b"', 'name="prompt_c"',
            'id="h3ClipVersionPanel"', 'id="h3ClipVersionList"',
        ):
            self.assertIn(marker, self.index)
        self.assertIn("prompt_variants:promptVariants", self.app)
        self.assertNotIn("new Set(prompts).size!==3", self.app)
        self.assertNotIn("서로 다른 독립 프롬프트여야 합니다", self.app)
        self.assertIn("function saveH3FeedbackRevisionRequest", self.app)
        self.assertIn("/revision-requests`,", self.app)
        self.assertIn("로컬 언어 모델과 영상 생성은 실행되지 않습니다", self.app)
        self.assertIn("prompt_revision_requests", self.app)
        self.assertIn("authored_prompt_variants", self.app)
        self.assertIn("function h3AuthoredPromptVersionsForClip", self.app)
        self.assertIn("function h3ProjectPromptSelection", self.app)
        self.assertIn("function selectH3ClipPromptVersion", self.app)
        self.assertIn("if(authored.length)h3SelectedClipPromptVersion={kind:'authored'", self.app)
        self.assertIn("if(!h3SelectedClipPromptVersion&&authored.length)", self.app)
        self.assertIn("data-h3-select-authored-version", self.app)
        self.assertIn("사용할 Prompt 버전을 선택하세요", self.app)
        self.assertIn("promptVariantMeta", self.app)
        self.assertIn("function restoreH3ClipVersion", self.app)
        self.assertIn("/restore`,", self.app)
        self.assertIn("data-h3-feedback-revision", self.app)
        self.assertIn("data-h3-restore-version", self.app)
        self.assertIn(".h3-prompt-variants{", self.styles)
        self.assertIn(".h3-clip-version-panel{", self.styles)
        self.assertIn(".h3-candidate-revision{", self.styles)
        self.assertNotIn("data-h3-authored-revision-draft", self.app)
        self.assertIn("python('save_h3_prompt_revision_request'", self.server)
        self.assertIn("python('apply_h3_prompt_revision'", self.server)
        self.assertIn("python('restore_h3_candidate_version'", self.server)

    def test_h3_r2v_project_can_be_deleted_with_confirmation_and_backend_checks(self):
        self.assertIn('id="deleteH3Project"', self.index)
        self.assertIn("function syncH3ProjectDeleteButton()", self.app)
        self.assertIn("function deleteH3Project()", self.app)
        self.assertIn(
            "프로젝트의 클립 프롬프트와 이미지 자산은 복구할 수 없습니다",
            self.app,
        )
        self.assertIn("method:'DELETE'", self.app)
        self.assertIn(
            "/api/h3/projects/${encodeURIComponent(projectId)}", self.app
        )
        route = self.server.split("const h3Project =", 1)[1].split(
            "const projectClips =", 1
        )[0]
        self.assertIn("req.method === 'DELETE'", route)
        self.assertIn("python('delete_h3_project'", route)
        backend = (ROOT / "ui_backend.py").read_text(encoding="utf-8")
        bridge = backend.split("def delete_h3_project", 1)[1].split(
            "def h3_project_clips", 1
        )[0]
        self.assertIn("h3_queue.delete_prompt_project", bridge)
        self.assertIn('"delete_h3_project": delete_h3_project', backend)

    def test_h3_i2v_page_requires_start_image_and_allows_optional_last_image(self):
        for marker in (
            'data-view="i2v-create"', 'id="refreshI2VProjects"',
            'id="i2vProjectPreview"', 'id="i2vSceneAdapter"',
            'id="i2vSceneImagePreview"', 'id="i2vSceneImagePreviewGrid"',
            'id="createI2VSceneTestSet"',
            'id="queueI2VSceneCandidates"', 'id="i2vStartImageBox"',
            'id="clearI2VLinkedStartImage"', 'id="i2vLastImageSection"',
            'id="i2vLastImage"', 'id="i2vLastImageBox"',
            'id="i2vLinkedLastImage"', 'id="clearI2VLinkedLastImage"',
        ):
            self.assertIn(marker, self.index)
        self.assertIn("h3Adapters.filter(row=>row.generation_mode==='i2v')", self.app)
        self.assertIn("function setI2VLinkedStartImage", self.app)
        self.assertIn("function setI2VLinkedLastImage", self.app)
        self.assertIn("function orderedI2VSceneClips", self.app)
        self.assertIn("function renderI2VSceneImagePreview", self.app)
        self.assertIn("data-i2v-preview-clip", self.app)
        self.assertIn("function resetI2VLastImage", self.app)
        self.assertIn("generation_mode:'i2v'", self.app)
        self.assertIn("role:'start_frame'", self.app)
        self.assertIn("body.set('reference_0',file)", self.app)
        self.assertIn("function syncI2VReferenceMode()", self.app)
        self.assertIn("supports_last_frame", self.app)
        self.assertIn("body.set('reference_1',lastFile)", self.app)
        self.assertIn("lastBox.dataset.projectId", self.app)
        self.assertIn("project_picture_index:Number(lastBox.dataset.pictureIndex||2)", self.app)
        self.assertIn("/api/h3/scenes/candidate-sets", self.app)
        self.assertIn(".i2v-start-image-box{", self.styles)
        self.assertIn(".i2v-scene-image-preview-grid{", self.styles)
        self.assertIn(".i2v-last-image-section[hidden]", self.styles)

    def test_selected_i2v_scene_can_register_a_general_test_set_without_queueing(self):
        self.assertIn("function createI2VSceneTestSet()", self.app)
        self.assertIn("선택한 씬 I2V 테스트 등록", self.index)
        registration = self.app.split(
            "async function createI2VSceneTestSet()", 1
        )[1].split("async function queueI2VSceneCandidates()", 1)[0]
        self.assertIn("/api/h3/project-test-sets", registration)
        self.assertIn("generation_mode:'i2v'", registration)
        self.assertNotIn("/api/h3/scenes/candidate-sets", registration)
        self.assertNotIn("/queue", registration)
        self.assertIn("function renderI2VTestSetDeleteControl(suite)", self.app)
        self.assertIn("function deleteI2VProjectTestSet(projectTestSetId,button)", self.app)

    def test_general_model_test_history_is_collapsed_and_scrolls_inside_panel(self):
        self.assertIn(
            '<details id="modelTestSessionHistory" class="panel r2v-collapse-panel model-test-session-history">',
            self.index,
        )
        history = self.index.split('id="modelTestSessionHistory"', 1)[1].split(
            "</details>", 1
        )[0]
        self.assertNotIn(" open", history.split(">", 1)[0])
        self.assertIn('id="modelTestSessionHistoryMeta"', history)
        self.assertIn('id="modelTestSessions"', history)
        self.assertIn('class="model-test-table-scroll"', self.app)
        self.assertIn('class="issues model-test-session-table"', self.app)
        self.assertIn(".model-test-session-history", self.styles)
        self.assertIn(".model-test-session-table th", self.styles)
        self.assertIn("overflow-x:auto", self.styles)
        self.assertIn("white-space:nowrap", self.styles)

    def test_selected_scene_can_register_a_test_set_without_queueing(self):
        self.assertIn("createH3SceneTestSet", self.app)
        self.assertIn("선택한 씬 R2V 테스트 등록", self.app)
        self.assertIn("JSON.stringify({project_id:projectId,scene_id:sceneId})", self.app)
        self.assertIn("ready===clips.length", self.app)
        scene_registration = self.app.split("async function createH3SceneTestSet()", 1)[1].split(
            "async function queueH3SceneCandidates()", 1
        )[0]
        self.assertIn("/api/h3/project-test-sets", scene_registration)
        self.assertNotIn("/api/h3/scenes/candidate-sets", scene_registration)
        self.assertNotIn("/queue", scene_registration)

    def test_r2v_dynamic_test_set_can_be_deleted_after_confirmation(self):
        self.assertIn("function renderR2VTestSetDeleteControl(suite)", self.app)
        self.assertIn(
            "suite?.deletable===true&&suite?.project_test_set_id",
            self.app,
        )
        self.assertIn("data-delete-r2v-project-test-set", self.app)
        self.assertIn("테스트 세트 삭제", self.app)
        self.assertIn(
            "async function deleteR2VProjectTestSet(projectTestSetId,button)",
            self.app,
        )
        self.assertIn(
            "원본 프로젝트와 Picture 이미지, 프롬프트, 기존 테스트 세션 및 생성·검수 결과는 모두 보존됩니다.",
            self.app,
        )
        self.assertIn(
            "if(!confirm('이 R2V 테스트 세트를 목록에서 삭제할까요?",
            self.app,
        )
        self.assertIn(
            "/api/h3/project-test-sets/${encodeURIComponent(projectTestSetId)}`",
            self.app,
        )
        delete_function = self.app.split(
            "async function deleteR2VProjectTestSet", 1
        )[1].split("async function deleteModelTestSession", 1)[0]
        self.assertIn("method:'DELETE'", delete_function)
        self.assertNotIn("deletion_password", delete_function)
        self.assertIn("body:'{}'", delete_function)
        self.assertIn("await refreshModelTests()", delete_function)
        self.assertIn(
            "session?.input_mode==='h3_r2v_multi_reference'",
            self.app,
        )

        route = self.server.split("const projectTestSet =", 1)[1].split(
            "const projectTestQueue =", 1
        )[0]
        self.assertIn("req.method === 'DELETE' && projectTestSet", route)
        self.assertIn("python('delete_h3_project_test_set'", route)
        self.assertIn("...(await bodyJson(req))", route)
        backend = (ROOT / "ui_backend.py").read_text(encoding="utf-8")
        bridge = backend.split("def delete_h3_project_test_set", 1)[1].split(
            "def queue_h3_scene_candidates", 1
        )[0]
        self.assertNotIn("_require_deletion_password(data)", bridge)
        self.assertIn("h3_queue.delete_project_test_set", bridge)
        self.assertIn(
            '"delete_h3_project_test_set": delete_h3_project_test_set',
            backend,
        )

        self.assertIn(".r2v-test-set-delete{", self.styles)
        self.assertIn(".r2v-test-set-delete button{", self.styles)
        responsive = self.styles.split("@media(max-width:700px)", 1)[1]
        self.assertIn(".r2v-test-set-delete{justify-content:stretch}", responsive)
        self.assertIn(".r2v-test-set-delete button{width:100%}", responsive)

    def test_model_test_queue_registration_stays_on_current_page(self):
        queue_handler = self.app.split(
            '$$("[data-test-queue]")', 1
        )[1].split('$$("[data-test-ai-review]")', 1)[0]
        self.assertIn("await refreshH3State()", queue_handler)
        self.assertNotIn('goPage("queue")', queue_handler)

    def test_h3_force_stop_uses_confirm_without_password(self):
        force_stop = self.app.split(
            "async function forceStopH3Group", 1
        )[1].split("const h3QueueActiveStatuses", 1)[0]
        self.assertIn(
            "if(!confirm('이 H3 큐 그룹의 실행 중·대기 작업을 강제정지할까요?",
            force_stop,
        )
        self.assertIn("body:'{}'", force_stop)
        self.assertNotIn("deletion_password", force_stop)
        self.assertNotIn("askDeletionPassword", self.app)
        self.assertNotIn('id="deleteDialog"', self.index)

        backend = (ROOT / "ui_backend.py").read_text(encoding="utf-8")
        bridge = backend.split("def force_stop_h3_group", 1)[1].split(
            "def select_h3_candidate", 1
        )[0]
        self.assertNotIn("_require_deletion_password", bridge)
        self.assertIn("h3_queue.force_stop_group", bridge)

    def test_sidebar_system_metrics_use_requested_units_and_interval(self):
        self.assertIn("메모리 · 캐시 포함", self.app)
        self.assertIn("가용 메모리", self.app)
        self.assertIn("formatGiB", self.app)
        self.assertIn("setInterval(refreshSystemMetrics,5000)", self.app)

    def test_sidebar_shows_windows_sleep_state_and_gpu_power(self):
        self.assertIn('id="windowsPcStatus"', self.index)
        self.assertIn('class="sidebar-footer"', self.index)
        self.assertIn("function renderWindowsPcStatus(status)", self.app)
        self.assertIn("절전 상태", self.app)
        self.assertIn("GPU 전력", self.app)
        self.assertIn("최대 절전/오프라인", self.app)
        self.assertIn("/api/windows-render-status", self.app)
        self.assertIn("url.pathname === '/api/windows-render-status'", self.server)
        self.assertIn("async function windowsRenderStatus()", self.server)
        self.assertIn("H3_RENDER_AGENT_URL", self.server)
        self.assertIn("gpu_power_w", self.server)
        self.assertIn("rawGpuPower == null ? null", self.server)
        self.assertIn(".windows-pc-status{", self.styles)
        self.assertIn(".windows-pc-status.is-awake", self.styles)

    def test_windows_candidate_and_local_generation_queues_are_separate(self):
        self.assertIn("Windows 후보 큐와 로컬 생성 큐를 서로 독립적으로 실행합니다.", self.index)
        self.assertIn("05 해상도 재생성과 07·08 모델 테스트는 로컬", self.index)
        self.assertIn("function h3JobQueueLane(job)", self.app)
        self.assertIn("Windows 후보 큐", self.app)
        self.assertIn("로컬 생성 큐", self.app)
        self.assertIn("Windows ComfyUI · 8189", self.app)
        self.assertIn("로컬 ComfyUI · 8188", self.app)
        self.assertIn("로컬 씬 전체후보 생성", self.app)
        self.assertIn("로컬 후보생성", self.index)
        self.assertIn("queueH3SceneCandidatesTo('local_generation')", self.app)
        self.assertIn("queue_lane:queueLane", self.app)
        self.assertIn("로컬에서 해상도 재생성", self.app)
        self.assertIn("로컬 해상도 시드 랜덤 재생성", self.app)
        self.assertIn("data-h3-resolution-rerender-random", self.app)
        self.assertIn('class="h3-result-rerender-actions"', self.app)
        self.assertIn("randomize_seed:randomizeSeed", self.app)
        self.assertIn("Seed만 새로 생성합니다.", self.app)
        self.assertIn(".h3-result-rerender-actions{display:grid;grid-template-columns:1fr", self.styles)
        self.assertIn("windows_candidate_worker", self.server)
        self.assertIn(".h3-worker-lanes{", self.styles)
        self.assertIn(".queue-lane-metrics{", self.styles)

        local_service = (ROOT / "deploy/h3-video-worker.service").read_text(
            encoding="utf-8"
        )
        windows_service = (
            ROOT / "deploy/h3-windows-candidate-worker.service"
        ).read_text(encoding="utf-8")
        self.assertIn("H3_WORKER_LANE=local_generation", local_service)
        self.assertIn("H3_WORKER_LANE=windows_candidate", windows_service)

    def test_h3_selected_results_show_metadata_timing_and_clear_selection(self):
        self.assertIn('id="h3SelectedResults"', self.index)
        self.assertIn('id="refreshH3Results"', self.index)
        self.assertIn('id="h3ResultsPagination"', self.index)
        self.assertIn('id="h3ResultsPaginationTop"', self.index)
        self.assertEqual(2, self.index.count('data-h3-results-pagination'))
        self.assertIn("renderH3Candidates", self.app)
        self.assertIn("renderH3Results", self.app)
        self.assertIn("if(currentPage==='candidates'){", self.app)
        self.assertIn("if(forceMediaRender||!h3VideoIsPlaying(box))renderH3Candidates()", self.app)
        self.assertIn("if(currentPage==='results'&&(forceMediaRender||!h3VideoIsPlaying", self.app)
        self.assertIn("section.querySelectorAll('video').forEach(video=>video.pause())", self.app)
        self.assertIn("function h3SelectedJobs(set)", self.app)
        self.assertIn("flatMap(set=>h3SelectedJobs(set)", self.app)
        self.assertIn("selectedIds.has(id)", self.app)
        self.assertIn("선택 후보 ${selections.length}개", self.app)
        self.assertIn("job?.manifest?.generation_seconds", self.app)
        self.assertIn("job?.status?.elapsed_seconds", self.app)
        self.assertIn("생성 소요", self.app)
        self.assertIn("중단까지", self.app)
        self.assertIn("측정 기록 없음", self.app)
        self.assertIn("data-h3-clear-selection", self.app)
        self.assertIn("data-h3-clear-selection-job", self.app)
        self.assertIn("/selection${suffix}`,{method:'DELETE'}", self.app)
        self.assertIn("queueH3ResolutionRerender", self.app)
        self.assertIn("/resolution-rerenders`,{method:'POST'", self.app)
        self.assertIn("source_selected_job_id", self.app)
        self.assertIn("선택된 원본 후보", self.app)
        self.assertIn("해상도 재생성 결과", self.app)
        self.assertIn("data-h3-rerender-resolution", self.app)
        self.assertIn("data-h3-rerender-source-job", self.app)
        self.assertIn("source_job_id:sourceJobId", self.app)
        self.assertIn("H3 FIFO 큐 대기는 제외", self.index)
        self.assertIn(".h3-selected-results", self.styles)
        self.assertIn(".h3-result-media-grid", self.styles)

    def test_h3_selected_results_paginate_ten_cards_with_direct_page_navigation(self):
        self.assertIn("const H3_RESULTS_PAGE_SIZE=10", self.app)
        self.assertIn("function h3ResultPaginationItems", self.app)
        self.assertIn("function renderH3ResultsPagination", self.app)
        self.assertIn("function goH3ResultsPage", self.app)
        self.assertIn("selections.slice(pageStart,pageEnd)", self.app)
        self.assertIn("const paginations=$$('[data-h3-results-pagination]')", self.app)
        self.assertIn("data-h3-results-page", self.app)
        self.assertIn("aria-current=\"page\"", self.app)
        self.assertIn(">이전</button>", self.app)
        self.assertIn(">다음</button>", self.app)
        self.assertIn("Math.min(Math.max(1,h3ResultsPage),h3ResultsTotalPages)", self.app)
        self.assertIn(".h3-results-pagination{", self.styles)
        self.assertIn(".h3-results-page-numbers", self.styles)
        self.assertIn("flex-wrap:nowrap", self.styles)
        self.assertIn("width:auto;min-width:40px", self.styles)
        self.assertIn("text-align:center;white-space:nowrap", self.styles)

    def test_h3_candidate_sets_paginate_ten_cards_above_and_below(self):
        self.assertIn('id="h3CandidateSummary"', self.index)
        self.assertIn('id="h3CandidatesPaginationTop"', self.index)
        self.assertIn('id="h3CandidatesPagination"', self.index)
        self.assertEqual(2, self.index.count('data-h3-candidates-pagination'))
        self.assertIn("const H3_CANDIDATES_PAGE_SIZE=10", self.app)
        self.assertIn("function renderH3CandidatesPagination", self.app)
        self.assertIn("function goH3CandidatesPage", self.app)
        self.assertIn("sets.slice(candidatePageStart,candidatePageEnd)", self.app)
        self.assertIn("const paginations=$$('[data-h3-candidates-pagination]')", self.app)
        self.assertIn("data-h3-candidates-page", self.app)
        self.assertIn("Math.min(Math.max(1,h3CandidatesPage),h3CandidatesTotalPages)", self.app)
        self.assertIn(".h3-pagination-top{margin:0 0 18px}", self.styles)

    def test_h3_candidates_and_results_filter_by_project_and_scene(self):
        for marker in (
            'id="h3CandidateProjectFilter"',
            'id="h3CandidateSceneFilter"',
            'id="resetH3CandidateFilters"',
            'id="h3ResultProjectFilter"',
            'id="h3ResultSceneFilter"',
            'id="resetH3ResultFilters"',
        ):
            self.assertIn(marker, self.index)
        self.assertIn('전체 프로젝트', self.index)
        self.assertNotIn('h3CandidateEpisodeFilter', self.index)
        self.assertNotIn('h3ResultEpisodeFilter', self.index)
        self.assertIn("function h3SourceMetadata(set)", self.app)
        source_filters = self.app.split(
            "const h3SourceFilterConfig=", 1
        )[1].split("const renderH3CandidatesUnfiltered", 1)[0]
        self.assertIn("source_project_id", source_filters)
        self.assertIn("projectLabel", source_filters)
        self.assertNotIn("episodeMatch", source_filters)
        self.assertNotIn("EP\\d+", source_filters)
        self.assertIn("function syncH3SourceFilters(kind,sets)", self.app)
        self.assertIn("function h3FilteredSourceSets(kind,sets)", self.app)
        self.assertIn("renderH3CandidatesUnfiltered", self.app)
        self.assertIn("renderH3ResultsUnfiltered", self.app)
        self.assertIn("h3CandidatesPage=1", self.app)
        self.assertIn("h3ResultsPage=1", self.app)
        self.assertIn("선택한 필터에 해당하는 후보군이 없습니다.", self.app)
        self.assertIn("선택한 필터에 해당하는 결과가 없습니다.", self.app)
        self.assertIn(".h3-source-filters{", self.styles)

    def test_h3_candidate_set_title_includes_clip_name_in_parentheses(self):
        candidate_render = self.app.split("function renderH3Candidates()", 1)[1].split(
            "function h3ResolutionRerenderFor", 1
        )[0]
        self.assertIn("clipName=String(set.source_clip_id", candidate_render)
        self.assertIn("candidateTitle=clipName?`${set.candidate_set_id} (${clipName})`", candidate_render)
        self.assertIn("<b>${esc(candidateTitle)}</b>", candidate_render)

    def test_h3_candidate_set_displays_generation_resolution(self):
        candidate_render = self.app.split("function renderH3Candidates()", 1)[1].split(
            "function h3ResolutionRerenderFor", 1
        )[0]
        self.assertIn("set.width||set.resolution?.width||firstRequest.width", candidate_render)
        self.assertIn("set.height||set.resolution?.height||firstRequest.height", candidate_render)
        self.assertIn("`해상도 ${width} × ${height}`", candidate_render)
        self.assertIn("${sourceLabel} · ${esc(resolutionLabel)}", candidate_render)

    def test_h3_candidate_sets_can_force_stop_then_delete_when_terminal(self):
        self.assertIn("h3CandidateTerminalStatuses", self.app)
        self.assertIn("statuses.every(status=>h3CandidateTerminalStatuses.has(status))", self.app)
        self.assertIn("data-h3-force-candidate-set", self.app)
        self.assertIn("현재 큐 강제종료", self.app)
        self.assertIn("forceStopH3Group(button.dataset.h3ForceCandidateSet,true)", self.app)
        self.assertIn("data-h3-delete-candidate-set", self.app)
        self.assertIn("runtime.terminal?'':'disabled'", self.app)
        self.assertIn("async function deleteH3CandidateSet", self.app)
        self.assertIn("후보군 ${setId}을(를) 목록에서 제외할까요?", self.app)
        self.assertIn("완료된 AI 검수는 보존됩니다", self.app)
        self.assertIn("미완료 AI 검수는 취소됩니다", self.app)
        delete_function = self.app.split(
            "async function deleteH3CandidateSet", 1
        )[1].split("function renderH3Candidates", 1)[0]
        self.assertNotIn("deletion_password", delete_function)
        self.assertIn("body:'{}'", delete_function)
        self.assertIn("/api/h3/candidate-sets/${encodeURIComponent(setId)}`", self.app)
        self.assertIn("method:'DELETE'", self.app)
        self.assertIn("await refreshH3State(true)", self.app)
        self.assertIn("else syncH3CandidateSetActions(box)", self.app)
        self.assertIn(".h3-candidate-set-actions", self.styles)

    def test_h3_candidate_page_bulk_actions_follow_filter_and_page(self):
        self.assertIn('id="forceStopH3CandidatePage"', self.index)
        self.assertIn('id="deleteH3CandidatePage"', self.index)
        self.assertIn("페이지 큐 강제종료", self.index)
        self.assertIn("페이지 후보삭제", self.index)
        self.assertIn("function h3CandidatePageSets()", self.app)
        self.assertIn("h3CandidatePageSetIds=$$('#h3CandidateSets [data-h3-candidate-set]')", self.app)
        self.assertIn("function h3CandidateQueuedOnly(set)", self.app)
        self.assertIn("body:JSON.stringify({queued_only:true})", self.app)
        self.assertIn("이미 실행 중인 후보군과 완료된 결과는 건드리지 않습니다.", self.app)
        self.assertIn("filter(set=>h3CandidateSetRuntimeState(set).terminal)", self.app)
        self.assertIn(".h3-page-bulk-actions", self.styles)

    def test_h3_terminal_candidate_set_can_be_requeued_from_candidate_page(self):
        self.assertIn("async function requeueH3CandidateSet", self.app)
        self.assertIn("function mountH3CandidateRequeueButtons", self.app)
        self.assertIn("data-h3-requeue-candidate-set", self.app)
        self.assertIn("다시 후보로 등록하기", self.app)
        self.assertIn("새 랜덤 Seed", self.app)
        self.assertIn("/requeue`,{method:'POST'", self.app)
        self.assertIn("button.disabled=!state.terminal", self.app)
        self.assertIn(".h3-candidate-requeue{", self.styles)

        route = self.server.split("const candidateRequeue =", 1)[1].split(
            "const candidateSelect =", 1
        )[0]
        self.assertIn("req.method === 'POST' && candidateRequeue", route)
        self.assertIn("python('requeue_h3_candidate_set'", route)
        backend = (ROOT / "ui_backend.py").read_text(encoding="utf-8")
        self.assertIn("def requeue_h3_candidate_set", backend)
        self.assertIn("h3_queue.requeue_candidate_set", backend)
        self.assertIn(
            '"requeue_h3_candidate_set": requeue_h3_candidate_set',
            backend,
        )

    def test_h3_candidates_use_thumbnail_dialog_without_inline_video(self):
        self.assertIn('id="h3CandidateVideoDialog"', self.index)
        self.assertIn('id="h3CandidateVideoTitle"', self.index)
        self.assertIn('id="h3CandidateVideoMeta"', self.index)
        self.assertIn('aria-describedby="h3CandidateVideoMeta"', self.index)
        self.assertIn('id="h3CandidateVideo"', self.index)
        self.assertIn('id="h3CandidateVideoClose"', self.index)
        candidate_render = self.app.split("function renderH3Candidates()", 1)[1].split(
            "function renderH3Results()", 1
        )[0]
        result_render = self.app.split("function renderH3Results()", 1)[1].split(
            "function h3VideoIsPlaying", 1
        )[0]
        result_media = self.app.split("function h3ResultMedia", 1)[1].split(
            "function h3ResultRerenderControls", 1
        )[0]
        self.assertIn("data-h3-candidate-play", candidate_render)
        self.assertIn("/video-thumbnail", candidate_render)
        self.assertIn("aria-label=", candidate_render)
        self.assertIn("loading=\"lazy\"", candidate_render)
        self.assertNotIn("<video controls", candidate_render)
        self.assertIn("data-h3-candidate-play", result_media)
        self.assertIn("/video-thumbnail", result_media)
        self.assertIn("loading=\"lazy\"", result_media)
        self.assertNotIn("<video controls", result_render)
        self.assertNotIn("<video controls", result_media)
        self.assertIn("title.textContent=", self.app)
        self.assertIn("meta.textContent=", self.app)
        self.assertIn("video.src=`/api/h3/jobs/${encodeURIComponent(jobId)}/video`", self.app)
        self.assertIn("video.pause();video.removeAttribute('src');video.load()", self.app)
        self.assertIn(
            "if(page!==currentPage){closeH3CandidateVideo();closeH3PicturePreview()}",
            self.app,
        )
        self.assertIn("addEventListener('cancel'", self.app)
        self.assertIn("addEventListener('close',clearH3CandidateVideoSource)", self.app)
        self.assertIn("addEventListener('pagehide',clearH3CandidateVideoSource)", self.app)
        self.assertIn(".h3-candidate-thumbnail", self.styles)
        self.assertIn(".h3-candidate-video-dialog", self.styles)

    def test_loaded_h3_picture_opens_large_preview_dialog(self):
        for marker in (
            'id="h3PicturePreviewDialog"',
            'id="h3PicturePreviewTitle"',
            'id="h3PicturePreviewMeta"',
            'id="h3PicturePreviewImage"',
            'id="h3PicturePreviewClose"',
        ):
            self.assertIn(marker, self.index)
        self.assertIn('data-h3-picture-preview', self.app)
        self.assertIn('data-h3-reference-remove', self.app)
        self.assertIn('function openH3PicturePreview', self.app)
        self.assertIn('openH3PicturePreview(config.asset_url', self.app)
        self.assertIn('dialog.showModal()', self.app)
        self.assertIn("event.target===event.currentTarget", self.app)
        self.assertIn("addEventListener('cancel'", self.app)
        self.assertIn("addEventListener('close',clearH3PicturePreviewSource)", self.app)
        self.assertIn('.h3-linked-picture-preview{', self.styles)
        self.assertIn('.h3-picture-preview-dialog{', self.styles)
        self.assertIn('object-fit:contain', self.styles)

    def test_h3_create_uses_selected_production_resolution(self):
        self.assertIn('id="h3Resolution"', self.index)
        self.assertIn('name="resolution"', self.index)
        self.assertIn('value="1280x704" selected', self.index)
        self.assertIn('value="1280x736"', self.index)
        self.assertIn('value="960x544"', self.index)
        self.assertIn('value="832x480"', self.index)
        create_page = self.index.split('data-view="create"', 1)[1].split(
            'data-view="i2v-create"', 1
        )[0]
        self.assertIn('value="608x352"', create_page)
        self.assertIn('id="h3SceneResolution"', self.app)
        scene_resolution = self.app.split('id="h3SceneResolution"', 1)[1].split(
            "</select>", 1
        )[0]
        self.assertIn('value="608x352" selected', scene_resolution)
        self.assertNotIn('value="1280x704" selected', scene_resolution)
        self.assertIn("$('#h3SceneResolution')?.value||'608x352'", self.app)
        self.assertIn('1280 × 736 · 확장 고해상도', self.app)
        self.assertIn('960 × 544 · 1080p 후처리 권장', self.app)
        self.assertIn('608 × 352 · 초고속 후보', self.app)
        self.assertIn('{width:960,height:544}', self.app)
        self.assertIn('{width:1024,height:576}', self.app)
        self.assertIn('{width:1280,height:736}', self.app)
        self.assertIn("item.width===1024&&item.height===576?'selected':''", self.app)
        self.assertIn("form.get('resolution')", self.app)
        self.assertIn("width:resolution[0],height:resolution[1]", self.app)

    def test_h3_r2v_scene_descriptions_can_show_read_only_korean_translation(self):
        create_page = self.index.split('data-view="create"', 1)[1].split(
            'data-view="i2v-create"', 1
        )[0]
        for marker in (
            'id="h3PromptInput"', 'id="translateH3Scene"',
            'aria-controls="h3SceneTranslation"',
            'id="h3SceneTranslation"', 'id="h3SceneTranslationClips"',
            '씬 연출 한국어 번역',
            '생성에 사용하는 원문 프롬프트는 변경되지 않습니다.',
        ):
            self.assertIn(marker, create_page)
        self.assertIn("async function translateH3Scene()", self.app)
        self.assertIn("'Translator' in globalThis", self.app)
        self.assertIn("sourceLanguage:'en',targetLanguage:'ko'", self.app)
        self.assertIn("globalThis.Translator.availability(options)", self.app)
        self.assertIn("monitor.addEventListener('downloadprogress'", self.app)
        self.assertIn("await translator.translate(chunks[chunkIndex])", self.app)
        self.assertIn("cardOutput.textContent=translated", self.app)
        self.assertIn("h3SceneTranslationCache.set(cacheKey,translated)", self.app)
        self.assertIn("revision!==h3SceneTranslationRevision", self.app)
        translation_function = self.app.split(
            "async function translateH3Scene()", 1
        )[1].split("$('#translateH3Scene')", 1)[0]
        self.assertNotIn("h3PromptInput", translation_function)
        self.assertIn(".h3-scene-translation{", self.styles)

    def test_model_test_pages_offer_r2v_low_and_expanded_resolutions(self):
        model_tests = self.index.split('data-view="model-tests"', 1)[1].split(
            'data-view="r2v-tests"', 1
        )[0]
        r2v_tests = self.index.split('data-view="r2v-tests"', 1)[1].split(
            "</main>", 1
        )[0]
        self.assertIn('value="608x352"', model_tests)
        self.assertIn('value="608x352"', r2v_tests)
        self.assertIn('value="1280x736"', model_tests)
        self.assertIn('value="1280x736"', r2v_tests)

    def test_h3_r2v_create_exposes_pint8_sol_attn_controls_with_safe_defaults(self):
        create_page = self.index.split('data-view="create"', 1)[1].split(
            'data-view="i2v-create"', 1
        )[0]
        for marker in (
            'id="h3SolAttnPanel"',
            'id="h3SolAttnSettings" disabled',
            'id="h3SolAttnTau"',
            'id="h3SolAttnStart"',
            'id="h3SolAttnEnd"',
            'id="h3SolAttnMinTokens"',
            'id="h3SolAttnSink"',
            'id="h3SolAttnDenseBlocks"',
            'id="h3SolAttnInt8Qk" type="checkbox"',
            'id="h3SolAttnInt8Pv" type="checkbox"',
            'id="h3SolAttnMorton" type="checkbox"',
            'id="h3SolAttnMortonCurve"',
            'id="h3SolAttnVerbose"',
            'id="h3SolAttnUseTma"',
        ):
            self.assertIn(marker, create_page)
        self.assertNotIn('id="h3SolAttnInt8Qk" type="checkbox" checked', create_page)
        self.assertNotIn('id="h3SolAttnInt8Pv" type="checkbox" checked', create_page)
        self.assertNotIn('id="h3SolAttnMorton" type="checkbox" checked', create_page)
        self.assertIn("function syncH3SolAttnPanel()", self.app)
        self.assertIn("adapter?.sol_attn_configurable===true", self.app)
        self.assertIn("function collectH3SolAttnWorkflowSettings()", self.app)
        self.assertIn("data.workflow_settings=workflowSettings", self.app)

    def test_update_attention_r2v_workflow_is_the_default_combo_option(self):
        registry = (ROOT / "model_test_registry.py").read_text(encoding="utf-8")
        r2v = (ROOT / "model_test_r2v.py").read_text(encoding="utf-8")
        self.assertIn(
            'R2V_UPDATE_ATTN_WORKFLOW_FILENAME = (',
            r2v,
        )
        self.assertIn(
            '"(basic)video_minimax_h3_r2v_updateAttn_api.json"',
            r2v,
        )
        self.assertIn(
            "R2V_DEFAULT_WORKFLOW_FILENAME = R2V_UPDATE_ATTN_WORKFLOW_FILENAME",
            r2v,
        )
        self.assertIn(
            '"filename": model_test_r2v.R2V_UPDATE_ATTN_WORKFLOW_FILENAME',
            registry,
        )
        self.assertIn(
            "R2V_DEFAULT_WORKFLOW_FILENAME='(basic)video_minimax_h3_r2v_updateAttn_api.json'",
            self.app,
        )
        self.assertIn("row.default_for_generation?'기본 · ':''", self.app)
        self.assertIn("if(preferred)select.value=preferred.adapter_id", self.app)
        self.assertIn(
            "item.workflow_filename===R2V_DEFAULT_WORKFLOW_FILENAME",
            self.app,
        )

    def test_h3_i2v_create_offers_1376_by_768_resolution(self):
        i2v_page = self.index.split('data-view="i2v-create"', 1)[1].split(
            'data-view="queue"', 1
        )[0]
        self.assertIn('id="i2vResolution"', i2v_page)
        self.assertIn('id="i2vSceneResolution"', i2v_page)
        self.assertEqual(2, i2v_page.count('value="1376x768"'))
        self.assertNotIn('value="608x352"', i2v_page)
        self.assertIn("I2V_OUTPUT_RESOLUTIONS", (ROOT / "h3_queue.py").read_text(encoding="utf-8"))

    def test_h3_resolution_rerender_route_uses_server_side_selected_job_clone(self):
        backend = (ROOT / "ui_backend.py").read_text(encoding="utf-8")
        route = self.server.split("const candidateResolutionRerender =", 1)[1].split(
            "const candidateSelection =", 1
        )[0]
        self.assertIn("req.method === 'POST' && candidateResolutionRerender", route)
        self.assertIn("python('create_h3_resolution_rerender'", route)
        self.assertIn("candidate_set_id: decodeURIComponent", route)
        self.assertIn("source_job_id", self.app)
        self.assertIn("def create_h3_resolution_rerender", backend)
        self.assertIn("h3_queue.enqueue_selected_candidate_rerender", backend)
        self.assertIn(
            '"create_h3_resolution_rerender": create_h3_resolution_rerender',
            backend,
        )

    def test_h3_result_page_queues_windows_h264_upscale_after_spark(self):
        backend = (ROOT / "ui_backend.py").read_text(encoding="utf-8")
        workflow = json.loads(
            (ROOT / "deploy/windows-render-agent/rtx_1080p60_h264_api.json")
            .read_text(encoding="utf-8")
        )
        self.assertIn("/video-upscales", self.server)
        self.assertIn("python('create_h3_video_upscale'", self.server)
        self.assertIn("def create_h3_video_upscale", backend)
        self.assertIn("h3_queue.enqueue_selected_candidate_upscale", backend)
        self.assertIn("queueH3VideoUpscale", self.app)
        self.assertIn("h3VideoUpscaleFor", self.app)
        self.assertIn("Windows에서 1080p · 60fps · H264 업스케일", self.app)
        self.assertIn("data-h3-video-upscale", self.app)
        self.assertIn("h3ResolutionRerendersFor", self.app)
        self.assertIn("h3SelectedResolutionRerender", self.app)
        self.assertIn("h3RerenderHistory", self.app)
        self.assertIn("data-h3-rerender-source-select", self.app)
        self.assertIn("해상도 재생성 기록", self.app)
        self.assertIn("업스케일 원본으로 선택", self.app)
        self.assertIn(".h3-rerender-history-row.selected", self.styles)
        self.assertEqual("video/h264-mp4", workflow["8"]["inputs"]["format"])
        self.assertEqual("yuv420p", workflow["8"]["inputs"]["pix_fmt"])
        self.assertEqual(60, workflow["8"]["inputs"]["frame_rate"])

    def test_h3_candidate_selection_supports_individual_delete_route(self):
        backend = (ROOT / "ui_backend.py").read_text(encoding="utf-8")
        route = self.server.split("const candidateJobSelection =", 1)[1].split(
            "const candidateSelection =", 1
        )[0]
        self.assertIn("/selection\\/([^/]+)$/", route)
        self.assertIn("req.method === 'DELETE' && candidateJobSelection", route)
        self.assertIn("job_id: decodeURIComponent(candidateJobSelection[2])", route)
        self.assertIn(
            'str(data.get("job_id") or "") or None',
            backend,
        )

    def test_r2v_pint8_workflow_exposes_session_scoped_sol_attn_controls(self):
        for marker in (
            'id="r2vSolAttnPanel"',
            'id="r2vSolAttnSettings" disabled',
            'id="r2vSolAttnTau"',
            'id="r2vSolAttnStart"',
            'id="r2vSolAttnEnd"',
            'id="r2vSolAttnMinTokens"',
            'id="r2vSolAttnSink"',
            'id="r2vSolAttnDenseBlocks"',
            'id="r2vSolAttnInt8Qk"',
            'id="r2vSolAttnInt8Pv"',
            'id="r2vSolAttnMorton"',
            'id="r2vSolAttnMortonCurve"',
            'id="r2vSolAttnVerbose"',
            'id="r2vSolAttnUseTma"',
        ):
            self.assertIn(marker, self.index)
        self.assertIn(
            "R2V_SOL_ATTN_WORKFLOW_FILENAME='(basic)video_minimax_h3_r2v_pint8_api.json'",
            self.app,
        )
        self.assertIn(
            "workflow_filename===R2V_SOL_ATTN_WORKFLOW_FILENAME",
            self.app,
        )
        self.assertIn("panel.hidden=!enabled", self.app)
        self.assertIn("fieldset.disabled=!enabled", self.app)
        self.assertIn("profile?.sol_attn_configurable===true", self.app)
        self.assertIn("profile?.sol_attn_defaults", self.app)
        self.assertIn("applyR2VSolAttnDefaults(profile)", self.app)
        self.assertIn("if(!fieldset||fieldset.disabled)return null", self.app)
        self.assertIn("payload.workflow_settings=workflowSettings", self.app)
        self.assertIn("r2vSolAttnSessionSummary", self.app)
        self.assertIn("group.workflow_settings?.sol_attn", self.app)
        self.assertIn(".r2v-sol-attn-panel{", self.styles)
        self.assertIn(".r2v-sol-attn-grid{", self.styles)

    def test_server_mutation_surface_is_h3_and_model_test_only(self):
        self.assertIn("/api/h3/candidate-sets", self.server)
        self.assertIn("/api/model-tests/sessions", self.server)
        for removed_route in (
            "/api/batches", "/api/retake", "/api/compositions",
            "/api/source-images", "/api/msr",
        ):
            self.assertNotIn(removed_route, self.server)

    def test_model_review_dialog_and_document_close_correctly(self):
        self.assertIn("리뷰 revision 저장", self.index)
        self.assertIn("</form></dialog>", self.index)
        self.assertEqual(1, self.index.count("</main>"))
        self.assertIn('/styles.css?v=20260816-39', self.index)
        self.assertIn('/app.js?v=20260822-98', self.index)

    def test_initial_registry_refreshes_are_sequential(self):
        refresh_function = self.app.split(
            "async function refreshModelTests()", 1
        )[1].split("async function refreshPrimaryState()", 1)[0]
        self.assertIn("modelTestState=await api('/api/model-tests')", refresh_function)
        self.assertIn(
            "modelTestComparisonState=await api('/api/model-tests/comparison')",
            refresh_function,
        )
        self.assertNotIn("Promise.all", refresh_function)

        primary_refresh = self.app.split(
            "async function refreshPrimaryState()", 1
        )[1].split("function selectedModelTestSuite", 1)[0]
        self.assertIn("await refreshH3State()", primary_refresh)
        self.assertIn("await refreshModelTests()", primary_refresh)
        self.assertIn("refreshPrimaryState().catch", self.app)
        self.assertNotIn(
            "Promise.all([refreshH3State(),refreshModelTests()])",
            self.app,
        )


if __name__ == "__main__":
    unittest.main()
