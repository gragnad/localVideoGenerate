# SESSION HANDOFF

## Current goal

The production path is MiniMax H3 only: project/scene input → H3 FIFO queue → candidate selection →
selected-result confirmation.
Model management, general model tests, R2V tests, and human review remain. AI review was retired on
2026-09-27 (see "AI review retirement" below).

## Current architecture

- UI/API: `web/server.mjs`, `web/public/`, `ui_backend.py`
- H3 projects and generation: `h3_prompt_projects.py`, `h3_queue.py`, `h3_worker.py`
- Model tests: `model_test_registry.py`, `model_test_r2v.py`, `benchmark_jobs.py`
- Review: `model_test_reviews.py` (human reviews; archived AI reviews are read-only), `review_contract.py`
- DB: `evaluation_db.py`, schema 10
- Services: `deploy/h3-video-ui.service`, `deploy/h3-video-worker.service` (local lane), and
  `deploy/h3-windows-candidate-worker.service` (Windows lane).
- GPU sharing: `engine_switch.py` + `engine_scheduler.py` external lease. The Qwen server on 8091 is
  used only by external clients (`director-agent`); an active lease blocks the local lane only.

## Windows candidate-only rendering and managed power

- Prompt A/B/C authoring remains outside the Windows render host. Production R2V/I2V candidates,
  feedback-derived candidates, reruns, and selected-result resolution rerenders use
  `H3_CANDIDATE_COMFY_URL`; general benchmarks keep using Linux `COMFY_URL`.
- `h3_queue.py` persists the chosen ComfyUI URL and `render_target` in every candidate request.
  `h3_worker.py` uploads immutable Picture inputs and the compiled API graph to Windows, polls the
  remote history, and downloads the completed video into the normal Linux H3 output directory.
- `remote_render_power.py` wakes the managed host before a render if its API is offline. Only a host
  woken by this Worker is eligible for automatic hibernation, and the Worker checks both the local H3
  queue and remote ComfyUI queue before calling the authenticated power API after the idle grace period.
- The target is Tailscale `100.78.202.37`, LAN `172.30.1.71`, wired MAC `b0:82:e2:37:a1:8a`, and
  broadcast `172.30.1.255`. Port `41641` is Tailscale UDP transport. TCP `8188` is occupied by another
  Go HTTP service, so Windows ComfyUI uses TCP `8189`; the existing power API uses TCP `8766`.
- The elevated Windows installer is under `deploy/windows-comfy-render/`. It runs the existing ComfyUI
  at logon with `--listen 100.78.202.37 --port 8189`, restricts the firewall source to Linux Tailscale
  `100.124.246.93`, and verifies `/system_stats`.
- The production-only power companion is under `deploy/windows-render-agent/` and packaged as
  `deploy/windows-render-agent-v4.zip`. It defaults to TCP `8766`, reuses the existing bearer token,
  removes the legacy prompt-agent scheduled task, and exposes only health/GPU power plus authenticated
  hibernation. Agent v4 releases stale hibernation locks, exposes the last command result, and the
  Linux worker requires three consecutive offline checks before recording success. The sidebar calls
  `GET /api/windows-render-status` every five seconds and shows `절전 상태`, NVIDIA GPU board power,
  and manual `PC 켜기` / `PC 끄기 · 최대 절전` controls. The manual off path requires confirmation
  and refuses to hibernate while a Windows-lane H3 job or remote ComfyUI queue item is active. An
  unreachable host is shown as `최대 절전/오프라인` with no invented wattage. The controls reuse the
  existing WOL and authenticated power-agent paths and do not replace automatic Worker power handling.
  Installer v4 disables the Windows AC idle standby/hibernate timers, removes the
  scheduled task's 72-hour execution limit, enables Task Scheduler Operational events, and persists a
  rotating agent log, 30-second lifecycle heartbeat, clean-exit marker, and fatal Python crash dump.
  Failed task processes retry up to ten times at Windows Task Scheduler's one-minute minimum interval;
  Linux-managed explicit hibernation remains enabled.
- The old prompt revision dispatcher is not part of this render path. Keep it disabled and leave
  `H3_PROMPT_REVISION_REMOTE_URL` unset so Windows performs video rendering only.

The UI exposes `01 H3 R2V 생성`, `02 H3 I2V 생성`, `03 큐 · 진행`, `04 후보 선택`, `05 결과 확인`,
`06 액션 자산`, `07 모델 관리`, `08 모델 테스트`, and `09 R2V 테스트`.

## Blender action video uploads

- `06 액션 자산` accepts `blender_render` as a distinct motion-only source alongside internal
  generation, direct uploads, and externally licensed footage.
- Blender uploads preserve the original video and record the `.blend` project filename, scene,
  action, Blender version, and render engine. The normal action pipeline creates the independent
  1024x576, 24fps, H.264 silent H3 copy and retains duplicate/hash and rights checks.
- MP4, MOV, WEBM, MKV, and Blender AVI outputs are accepted. The action library can filter Blender
  sources and displays their provenance on each card.

## Legacy removal completed in source

The old LTX/MSR production worker, batch manager, automatic review/Retake chain, final master,
editing/assembly, source-image library, Director/MSR project editors, repair scripts, and their tests
were removed. New DB initialization no longer creates the old batch/source-library tables.

Historical `jobs`, `runtime/batches`, evaluation DB rows, prompt projects, generated media, and assets
were deliberately not deleted. The generic historical video endpoint remains read-only so old model-test
results can still play.

## Verification

- Python and JavaScript syntax checks pass.
- Full unit suite: 208 tests pass, 1 skipped.
- The stale schema 8, removed batch UI event, and old R2V v2 prompt-phrase expectations were updated
  without changing generation prompts.
- `h3-video-ui` and `h3-video-worker` are active and enabled. The retired background
  `model-test-review-worker` is disabled. UI authentication rejects unauthenticated API calls,
  port 8502 has one listener, and ComfyUI is reachable on 8188.

## Scene-scoped R2V test registration

- `01 H3 생성` now keeps `선택한 씬 전체 후보군 등록` as the direct production queue action and
  exposes a separate `선택한 씬 R2V 테스트 등록` action.
- Scene test registration writes only a schema 2 test-set marker. It creates no H3 generation job or
  candidate set; workflow, resolution, repetitions, and execution are selected later in `08 R2V 테스트`.
- Each scene registration has a stable project+scene R2V suite ID and contains only the clip IDs captured
  at registration. A later source clip is included only after the scene is registered again.
- The latest schema 2 registration wins per project/scope. Scope-less schema 1 markers remain compatible
  as project-wide registrations, and the legacy Official full-project suite keeps its ID, name, and live
  full-project behavior.
- Project IDs are included in dynamic suite names so projects sharing a display title and scene ID cannot
  collide with the evaluation DB's unique suite-name constraint.
- Regression coverage verifies no-queue registration, scene/project/other-scene separation, duplicate
  registration, prompt preservation, two-Picture asset/order propagation through preflight and the H3
  benchmark request, registration membership pinning, old-marker compatibility, and suite-name uniqueness.

## H3 selected-result confirmation

- Candidate sets now persist `selected_jobs` so any number of completed candidates can be selected.
  `selected_job_id` remains as the latest-selection compatibility field for older callers and records
  without `selected_jobs` are normalized from that legacy scalar on read.
- `05 결과 확인` flattens all current selections into one card per selected job, newest selection
  first. Each card reuses the existing selected H3 output and shows project/scene/clip, candidate
  index, seed, resolution, Picture count, measured generation time, selection time, and prompt.
- `04 후보 선택` and `05 결과 확인` render 10 candidate-set/result cards per page. Matching pagination
  controls appear above and below each list; previous/next and direct numbered-page buttons use compact
  ellipses for long page ranges and clamp the current page after an item is removed. Results preserve
  newest-selection-first ordering.
- Both pages expose independent project and scene filters before pagination. The full
  `source_project_id` is used as the project key without extracting or grouping an `EPnn` token;
  choosing a project narrows the scene choices, filter changes return to page 1, and records without
  project metadata remain available under `직접 입력` / `씬 정보 없음`.
- `04 후보 선택` shows per-candidate Worker processing time. Completed jobs use
  `manifest.generation_seconds`; live/older records fall back to `status.elapsed_seconds`, and records
  without either value show `측정 기록 없음`. The timing excludes only H3 FIFO wait before Worker claim.
- One selection can be cleared from either page through
  `DELETE /api/h3/candidate-sets/:id/selection/:job_id`; the legacy collection route clears all
  selections. These change only candidate-set selection fields; generated videos and job
  request/status/manifest files remain intact. Clearing is idempotent and the candidate-set state is
  re-derived from its jobs.
- Candidate-set reconcile/select/clear writes share a filesystem lock so a final Worker reconcile cannot
  overwrite a simultaneous user selection.
- H3 candidate/result media containers are not rebuilt by SSE refresh while a video is playing, and
  videos are paused when their page is hidden.

## H3 selected-result resolution rerender

- Generation now has two independent queue lanes over the same durable job store. Production candidates
  and candidate reruns use `windows_candidate` and `h3-windows-candidate-worker.service`; model tests use
  `local_generation` and `h3-video-worker.service`. Atomic filtered claims prevent either Worker from
  taking the other lane, so Windows candidates and local generation can run concurrently.
- `05 결과 확인` resolution rerenders are deliberately routed to `local_generation` with local
  `COMFY_URL`, even when their source candidate was rendered on Windows. Local model-review locking
  blocks only local generation; Windows candidate rendering remains independent.
- `03 큐 · 진행` displays separate Windows candidate and local generation Worker cards, metrics,
  running jobs, and wait order. `/api/h3/state` exposes both statuses under `workers` while the legacy
  `worker` field remains the local Worker for compatibility.

- R2V production candidates support `608 × 352`, `832 × 480`, `960 × 544`, `1280 × 704`, and
  `1280 × 736`. The `1280 × 704` production default remains unchanged; `1280 × 736` is also available
  for direct creation, scene-wide queues, selected-result resolution rerenders, and R2V test sessions.
  I2V production resolutions remain unchanged and I2V selected results cannot request a rerender.
- `05 결과 확인` uses cached JPEG thumbnails instead of inline video elements. The selected original
  and the latest resolution rerender share one card and open in the common H3 playback dialog.
- `05 결과 확인` additionally supports `1024 × 576` for resolution rerenders and selects it by default
  whenever it is higher than the source result. Direct `01 H3 R2V 생성` resolutions are unchanged.
  Results already rendered at `1280 × 736` keep the highest-resolution notice instead of showing the selector.
- Each selected completed R2V result can independently queue one higher-resolution render while preserving the exact
  server-side prompt, integer seed, duration, Picture order and SHA, and source project/scene/clip metadata.
  The adapter and workflow-specific settings are replaced by the currently registered default R2V workflow;
  the browser never round-trips the seed.
- Resolution rerenders are stored as linked one-job candidate sets with `render_purpose`, source IDs,
  and source/target resolutions. They stay out of `04 후보 선택`; duplicate active requests for the
  same source job and target resolution are idempotent.
- Rerender registration verifies that the source Pictures are intact and the current default R2V adapter
  can compile the requested target resolution before it queues the job.

## Default H3 R2V INT8 + Alibaba Turbo workflow

- The supplied API graph is installed in ComfyUI as
  `(basic)video_minimax_h3_r2v_int8_turbo_api.json` and registered as
  `MiniMax H3 R2V INT8 + Alibaba Turbo`.
- This adapter is the default R2V choice and is sorted first with a `기본` label in production and
  `08 R2V 테스트`. The prior Update Attention, baseline, and PINT8/Sol-Attn workflows remain selectable.
- The graph preserves the INT8 ConvRot Ref2VA UNet, NVFP4/AWQ CLIP, Alibaba
  `MiniMax-H3-Ref2VA-Acc-8Step` PDD adapter, NFE 8, LoRA/head strength 1.0,
  SigmaShift 12/3, Euler sampler, PDD sigmas, and fail-closed off-grid checks.
- It accepts up to nine ordered Pictures. Nodes `137` and `139` provide the first two LoadImage
  slots; runtime compilation clones node `137` for slots 3 through 9 and connects every loader
  directly to `MiniMaxH3ReferenceToVideo`.
- `05 결과 확인` resolution rerenders always compile the currently registered default R2V adapter.
  Historical results therefore switch to INT8 + Alibaba Turbo for rerender while retaining their saved
  Prompt, Seed (unless explicitly randomized), Picture order/files, and duration.

## H3 candidate lifecycle and production resolution

- Queue-group force stop now uses a browser confirmation only. The UI sends an empty JSON body and
  `force_stop_h3_group` no longer performs a second deletion-password check; normal UI access-key
  authentication remains in place.
- Terminal candidate-set cards on `04 후보 선택` expose `다시 후보로 등록하기`. The server clones
  the saved prompt, immutable Picture files and hashes, generation mode, adapter/workflow settings,
  resolution, duration, source metadata, and candidate count into a new `candidate_rerun` set while
  assigning fresh random seeds. The original candidate set, selections, jobs, and outputs are retained;
  non-terminal sets and resolution-rerender sets are rejected.
- `04 후보 선택` exposes `현재 큐 강제종료` while any candidate job is non-terminal. Candidate-set
  deletion stays disabled until every job is `completed`, `failed`, or `cancelled`.
- `DELETE /api/h3/candidate-sets/:id` requires the deletion password and rechecks terminal job states
  on the server. It is a soft delete: the set and its H3 generation jobs disappear from UI state, while
  job directories, generated videos, and copied Picture sources remain preserved on disk.
- Force-stop and candidate-set mutations share consistent filesystem lock ordering. A selected set being
  stopped reports `cancelling` and then `cancelled`, after which it can be deleted.
- The direct `01 H3 생성` form now selects either `1280 × 704` (production default) or `832 × 480`
  (quick check). The chosen value is compiled into the workflow width/height inputs. Loading a project
  clip does not overwrite the user's current resolution choice.
- Linked Picture thumbnails loaded into `01 H3 R2V 생성` are buttons that open a dedicated large,
  aspect-preserving image preview dialog. It closes by its button, Escape, backdrop click, page change,
  or page unload without changing the linked project asset.
- `04 후보 선택` renders completed candidates as lazy-loaded JPEG thumbnails instead of one inline
  video element per card. Clicking a thumbnail opens one shared playback dialog; closing it, changing
  pages, or leaving the document pauses playback and clears the video source. `05 결과 확인` reuses
  the same thumbnail endpoint and shared playback dialog.
- Candidate-set card titles include the source clip ID in parentheses after the candidate-set ID;
  direct-input sets without clip metadata keep the candidate-set ID alone.
- `GET /api/h3/jobs/:id/video-thumbnail` accepts completed H3 jobs only. It reuses the common ffmpeg
  thumbnail cache, writes new JPEGs through a unique temporary file plus atomic rename, and regenerates
  stale cache entries when the source video mtime changes.

## PINT8 Patch Sol-Attn controls

- `08 R2V 테스트` exposes a collapsed Patch Sol-Attn settings panel only for the registered
  `(basic)video_minimax_h3_r2v_pint8_api.json` profile. The baseline R2V workflow cannot submit it.
- The form reads initial values from the hash-verified API workflow's unique `SolAttnPatch` node.
  `tau_profile` is not exposed because it is not present in the current API workflow.
- Settings are stored once per test session and applied only to a deep-copied execution graph. They are
  preserved in H3 requests, manifests, generation runs, runtime identity, follow-up sessions, and results.
- Pre-schema-10 PINT8 sessions with `{}` settings resolve to the graph's actual defaults. Workflow
  comparisons split different Sol-Attn configurations instead of averaging them together.

## Service migration completed

The former LTX-named UI/worker units, obsolete command wrappers, source backup files, and batch-manager
lock were moved out of active paths to the recoverable archive
`/home/nalstudio/.local/share/Trash/files/video-engine-legacy-20260807-2136`.
The active services use `/home/nalstudio/.config/h3-video-engine/runtime.env` (mode 0600).

The remaining `/home/nalstudio/.config/ltx-video-ui` directory contains only Qwen/review-engine settings
still consumed by the separate review-engine project. Do not remove it until that project is migrated.

## Safety notes

- Do not reset the dirty worktree. It contains user-owned asset and prompt-project changes.
- Do not delete assets, prompt projects, old result media, or runtime history during source cleanup.
- Keep R2V prompt/test-set contents unchanged unless the user explicitly asks for prompt work.

## H3 first-frame I2V production

- `02 H3 I2V 생성` follows the project → scene → clip and direct-input flow of the R2V page, but
  requires exactly one start image per clip. A linked project image can be detached and replaced by a
  direct PNG/JPEG/WEBP upload.
- I2V prompt projects use `project_kind`/`workflow` = `h3_i2v_production` and a single
  `start_image` object. `prompt_projects/H3_I2V_PROJECT_TEMPLATE` is the source-only template.
- The production adapter auto-registers `(basic)video_minimax_h3_i2v_api.json` and binds prompt,
  seed, width, height, duration, output prefix, and node 114's first-frame image. Only MiniMax H3
  adapters are exposed on the H3 production pages.
- I2V candidates use the existing batch-free H3 FIFO worker and candidate/result pages. Requests retain
  `job_type: h3_r2v_generate` for compatibility with a worker already running older source, while
  `generation_mode: i2v` carries the actual mode. Do not restart a busy worker solely for this UI change.

## Scene-scoped I2V test registration

- `02 H3 I2V 생성` can register the selected scene as an I2V test set without creating candidate jobs.
  The marker pins the current clip IDs, original prompts, and one linked start image per clip.
- Registered I2V scene suites appear only in `07 모델 테스트` with `i2v_fixed_anchor` contracts; they do
  not enter `08 R2V 테스트`. Execution resolution, repetitions, preflight, and queue submission remain
  explicit 07-page actions.
- R2V and I2V registration identities are separate. The page mode is validated against the project kind,
  and dynamic I2V suites can be soft-deleted while original projects, start images, sessions, and results
  remain preserved.

## General model-test responsive history

- The `07 모델 테스트` session-history panel is a native `details` element and is closed by default.
  Its summary shows the current session count without requiring the table to be expanded.
- The expanded history table keeps readable, non-breaking values and scrolls horizontally inside its own
  panel. It no longer widens the page or splits resolution, plan, status, and session IDs into vertical text
  on narrow windows.

## H3 R2V prompt translation preview

- `01 H3 R2V 생성` exposes `한국어 번역 보기` beside the actual H3 video-input prompt. The result is
  rendered in a separate read-only panel; the original English prompt remains the only value submitted to
  H3 generation.
- Translation uses the desktop browser's built-in English-to-Korean Translator API. First-use language-pack
  download and long-prompt chunk progress are shown in the panel, and editing or loading another clip clears
  stale translated text.
- Unsupported browsers and insecure non-local HTTP origins report an actionable message instead of changing
  the prompt or invoking the GPU review engine.
- The production H3 UI is available to tailnet members at
  `https://ltx-ai.tailf94d93.ts.net:8443/` through persistent Tailscale Serve HTTPS termination and a
  reverse proxy to `http://127.0.0.1:8502`. The pre-existing `https://ltx-ai.tailf94d93.ts.net/` mapping
  on port 443 continues to proxy port 8501 and was not changed. The H3 API access key remains required.

## LTX review-history-only cleanup

- LTX model/workflow/adapter/session/review rows remain in `runtime/evaluation/evaluation.db` for past
  comparison and result viewing. Dashboard rows are marked `legacy_read_only`; LTX is excluded from new
  model/workflow/adapter/session/follow-up execution paths and from available ComfyUI workflow choices.
- Both reviewed LTX sessions remain intact: 234 generation job directories and all 233 recorded output
  videos exist at their original paths. Existing result playback and review data remain available.
- Old Director/MSR prompt projects, five non-review LTX assembly jobs, empty obsolete DB placeholders,
  38 LTX/MSR ComfyUI workflow JSONs, and non-review files under the old LTX workspace were moved to the
  recoverable archive `/home/nalstudio/.local/share/Trash/files/video-engine-ltx-legacy-20260808-134543`.
  H3 outputs and the complete `outputs/video/model-tests` tree were explicitly preserved.

## AI review retirement (2026-09-27)

- Removed the candidate AI review (04) and model-test Qwen/R2V AI review (07/08) paths: UI buttons,
  status chip/progress, `PUT /api/h3/candidate-ai-review`, `POST|DELETE /api/model-tests/sessions/:id/ai-review`,
  SSE watchers for both review queues, the `/api/status` `review_worker` field, and the scheduler's
  review-queue claim/blocking. Candidate-set soft delete no longer touches review queues.
- Modules, their tests, `deploy/model-test-review-worker.service`, the Qwen3.8 worker drop-in/env,
  and the one-off `local_first_pass_round1.py` were moved to `archive/retired_ai_review_20260927/`.
  The installed user unit was moved there as well; `runtime.env` lost only the dead
  `VLLM_MODEL`/`VLLM_REVIEW_*` keys (backup kept outside the repo).
- Kept: human review, the `reviews` DB rows (AI rows are shown read-only as `보관된 AI 검수`),
  `runtime/model_test_review_queue` and `runtime/h3/candidate_review_queue` history on disk,
  and `engine_switch`/external lease for `director-agent`.
- Legacy session states (`ai_review_queued`, `ai_reviewing`, ...) no longer block session deletion;
  stale review-queue directories for a deleted session are moved to trash with it.

