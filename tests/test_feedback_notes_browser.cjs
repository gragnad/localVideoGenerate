const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root = path.resolve(__dirname, '..');
const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'feedback-notes-'));
const port = 18653, origin = `http://127.0.0.1:${port}`, key = 'notes-test';
const videoFile = path.join(fixture, 'test.mp4');
execFileSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=black:s=160x90:d=3', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', videoFile]);
const job = {job_id: 'ja', status: {status: 'completed'}, request: {source_project_id: 'P1', source_scene_id: 'S1', source_clip_id: 'C1', candidate_index: 1, seed: 123}};
const secondJob = {...job, job_id: 'jb', request: {...job.request, candidate_index: 2}};
const jobFolder = path.join(fixture, 'runtime/h3/jobs/ja'); fs.mkdirSync(jobFolder, {recursive: true});
fs.writeFileSync(path.join(jobFolder, 'request.json'), JSON.stringify(job.request));
fs.writeFileSync(path.join(jobFolder, 'status.json'), JSON.stringify(job.status));
const server = spawn(process.execPath, [path.join(root, 'web/server.mjs')], {env: {...process.env, VIDEO_UI_HOST: '127.0.0.1', VIDEO_UI_PORT: String(port), VIDEO_UI_ACCESS_KEY: key, VIDEO_ENGINE_ROOT: fixture, VIDEO_ENGINE_PYTHON: path.join(root, '.venv/bin/python')}, stdio: ['ignore', 'pipe', 'pipe']});
let logs = ''; server.stdout.on('data', b => logs += b); server.stderr.on('data', b => logs += b);
async function request(route, options = {}) {
  const response = await fetch(origin + route, {...options, headers: {'x-access-key': key, 'content-type': 'application/json', ...options.headers}});
  return {response, body: await response.json()};
}
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
async function reveal(page, id) {
  const control = page.locator('#' + id);
  const menu = control.locator('xpath=ancestor::details[contains(@class,"feedback-menu")][1]');
  if (await menu.count() && !await menu.evaluate(el => el.open)) await menu.locator(':scope > summary').tap();
  return control;
}
(async () => {
  let browser;
  try {
    for (let i = 0; i < 60; i++) { try { await fetch(origin + '/feedback-notes.js'); break; } catch { await wait(100); } }
    assert.equal((await fetch(origin + '/api/feedback-notes')).status, 401);
    assert.equal((await request('/api/feedback-notes/invalid')).response.status, 404);
    browser = await chromium.launch({headless: true});
    for (const viewport of [{width: 1024, height: 768}, {width: 768, height: 1024}]) {
      const context = await browser.newContext({viewport, hasTouch: true}), page = await context.newPage(), errors = [];
      let failSave = false, candidateRequests = 0;
      page.on('pageerror', e => errors.push(e.message));
      page.on('dialog', d => d.accept());
      await page.addInitScript(() => { sessionStorage.setItem('h3-key', 'notes-test'); window.EventSource = class {addEventListener() {} close() {}}; });
      await page.route(origin + '/api/**', async route => {
        const url = new URL(route.request().url()), name = url.pathname;
        if (name.startsWith('/api/feedback-notes')) {
          if (failSave && route.request().method() === 'PUT') return route.abort('failed');
          return route.continue();
        }
        if (name.endsWith('/feedback-context')) return route.continue();
        if (name.endsWith('/video')) return route.fulfill({contentType: 'video/mp4', body: fs.readFileSync(videoFile)});
        if (name.endsWith('/video-thumbnail')) return route.fulfill({status: 204});
        let data = {};
        if (name === '/api/h3/config') data = {adapters: []};
        else if (name === '/api/h3/state') data = {jobs: [job], candidate_sets: [], worker: {}, workers: {}, test_queues: []};
        else if (name === '/api/h3/projects') data = {projects: []};
        else if (name === '/api/h3/action-assets') data = {assets: [], presets: {}};
        else if (name === '/api/h3/candidate-page') {
          candidateRequests++;
          const project = url.searchParams.get('project_id') || 'P1';
          data = {jobs: [job, secondJob], candidate_sets: [{candidate_set_id: project + '_set', source_project_id: project, source_scene_id: 'S1', source_clip_id: 'C1', candidate_job_ids: ['ja', 'jb']}], pagination: {page: 1, total_pages: 1, total: 1}, filters: {projects: ['P1', 'P2'], scenes_by_project: {P1: ['S1'], P2: ['S1']}, clips_by_project_scene: {P1: {S1: ['C1']}, P2: {S1: ['C1']}}}};
        }
        return route.fulfill({contentType: 'application/json', body: JSON.stringify(data)});
      });
      await page.goto(origin + '/#feedback');
      await page.waitForSelector('[data-feedback-job="ja"]');
      assert.equal(await page.locator('#sidebarToggle').getAttribute('aria-expanded'), 'false');
      assert.equal(await page.locator('main').evaluate(el => el.getBoundingClientRect().x), 0);
      await page.locator('#sidebarToggle').tap();
      assert.equal(await page.locator('#sidebarToggle').getAttribute('aria-expanded'), 'true');
      assert(await page.locator('#studioSidebar').isVisible());
      await page.locator('#sidebarBackdrop').tap({position: {x: viewport.width - 20, y: 150}});
      assert.equal(await page.locator('#sidebarToggle').getAttribute('aria-expanded'), 'false');
      assert.equal(await page.locator('main > header').isVisible(), false);
      assert.equal(await page.locator('#sidebarToggle').evaluate(el => el.parentElement.id), 'feedbackNavigation');
      await (await reveal(page, 'feedbackFontSize')).selectOption('10');
      assert.equal(await page.locator('#feedbackNoteBody').evaluate(el => getComputedStyle(el).fontSize), '10px');
      const fontPanel = await page.locator('.feedback-menu[open] .feedback-menu-panel').boundingBox();
      assert(fontPanel.x >= 0 && fontPanel.x + fontPanel.width <= viewport.width);
      assert.equal(await page.locator('#feedbackFontSize option').count(), 15);
      await (await reveal(page, 'feedbackFontSize')).selectOption('24');
      assert.equal(await page.locator('#feedbackNoteBody').evaluate(el => getComputedStyle(el).fontSize), '24px');
      await (await reveal(page, 'feedbackNew')).tap();
      const title = '독립 노트 ' + viewport.width;
      await (await reveal(page, 'feedbackNoteTitle')).fill(title);
      await page.locator('#feedbackNoteBody').fill('## 확인\n- [ ] 손 위치 수정\n\n프로젝트와 별도 저장');
      await page.locator('.feedback-menu > summary').filter({hasText: '편집'}).tap();
      await page.locator('[data-feedback-prefix="- "]').tap();
      assert.equal(await page.locator('.feedback-menu[open]').count(), 0);
      assert(await page.locator('#feedbackNoteBody').evaluate(el => el === document.activeElement));
      await page.waitForFunction(() => document.querySelector('#feedbackSaveStatus').dataset.state === 'saved');
      await page.locator('#feedbackNoteBody').tap();
      await page.keyboard.press('ControlOrMeta+End');
      await page.keyboard.type(' touch keyboard');
      await page.keyboard.press('Enter');
      await page.keyboard.type('abc');
      await page.keyboard.press('ArrowLeft');
      await page.keyboard.press('Backspace');
      await page.waitForFunction(() => document.querySelector('#feedbackSaveStatus').dataset.state === 'saved');
      const first = (await request('/api/feedback-notes')).body.notes.find(n => n.title === title);
      assert(first);
      assert((await request('/api/feedback-notes/' + first.note_id)).body.body.includes('touch keyboard\nac'));
      await page.locator('[data-feedback-job="ja"]').tap();
      await page.waitForFunction(() => document.querySelector('#feedbackVideo').readyState >= 1);
      assert.equal(await page.locator('#feedbackVideoTitle').textContent(), 'C1 (후보 1)');
      await page.locator('[data-feedback-job="jb"]').tap();
      assert.equal(await page.locator('#feedbackVideoTitle').textContent(), 'C1 (후보 2)');
      await page.locator('[data-feedback-job="ja"]').tap();
      assert.equal(await page.locator('#feedbackVideoMeta').isVisible(), false);
      await page.locator('#feedbackVideos > .feedback-options > summary').tap();
      await page.locator('#feedbackProject').selectOption('P2');
      await page.locator('#feedbackVideos > .feedback-options > summary').tap();
      assert.equal(await page.locator('#feedbackNoteTitle').inputValue(), title);
      assert.equal(await page.locator('#feedbackNoteList').inputValue(), first.note_id);
      await page.locator('#feedbackNoteBody').fill('동작 확인\n' + '작성 중인 내용\n'.repeat(80));
      await page.evaluate(() => {
        window.editor = document.querySelector('#feedbackNoteBody'); editor.focus(); editor.setSelectionRange(7, 9); editor.scrollTop = 200;
        window.savedCursor = [editor.selectionStart, editor.selectionEnd, editor.scrollTop];
        window.savedVideoSrc = document.querySelector('#feedbackVideo').getAttribute('src');
        window.dispatchEvent(new CustomEvent('h3-feedback-refresh'));
      });
      const before = candidateRequests; await page.waitForFunction(() => document.querySelector('#feedbackSaveStatus').dataset.state === 'saved');
      while (candidateRequests <= before) await wait(30);
      assert(await page.evaluate(() => editor === document.querySelector('#feedbackNoteBody') && savedCursor[0] === editor.selectionStart && savedCursor[1] === editor.selectionEnd && Math.abs(savedCursor[2] - editor.scrollTop) < 2 && savedVideoSrc === document.querySelector('#feedbackVideo').getAttribute('src')));
      // Native touch and mouse drags change only pane widths, never the editor/player lifecycle.
      await page.evaluate(() => {
        const video = document.querySelector('#feedbackVideo'); video.pause(); video.currentTime = 1.25;
      });
      await page.waitForFunction(() => !document.querySelector('#feedbackVideo').seeking);
      await page.evaluate(() => {
        window.splitSnapshot = {editor: document.querySelector('#feedbackNoteBody'), video: document.querySelector('#feedbackVideo')};
        Object.assign(splitSnapshot, {body: splitSnapshot.editor.value, start: splitSnapshot.editor.selectionStart,
          end: splitSnapshot.editor.selectionEnd, scroll: splitSnapshot.editor.scrollTop,
          src: splitSnapshot.video.src, time: splitSnapshot.video.currentTime});
      });
      const handle = page.locator('#feedbackResizer');
      assert(await handle.isVisible());
      assert.equal(await handle.evaluate(el => getComputedStyle(el).touchAction), 'none');
      const divider = await handle.boundingBox();
      const cdp = await context.newCDPSession(page);
      const touch = (type, x) => cdp.send('Input.dispatchTouchEvent', {type, touchPoints: type === 'touchEnd' || type === 'touchCancel' ? [] : [{x, y: divider.y + divider.height / 2, id: 1}]});
      // Grab beside the visible line, inside its wider 44px touch target.
      await touch('touchStart', divider.x + divider.width / 2 + 18);
      await touch('touchMove', divider.x + divider.width / 2 + 18 + 65);
      await touch('touchEnd');
      const touchedRatio = Number(await handle.getAttribute('aria-valuenow'));
      assert(touchedRatio > 50);
      assert.equal(Number(await page.locator('#feedbackSplit').inputValue()), touchedRatio);
      assert.equal(await page.evaluate(() => document.querySelector('#feedbackWorkspace').classList.contains('is-resizing')), false);
      assert(await page.evaluate(() => {
        const s = splitSnapshot, e = document.querySelector('#feedbackNoteBody'), v = document.querySelector('#feedbackVideo');
        return e === s.editor && v === s.video && e.value === s.body && e.selectionStart === s.start && e.selectionEnd === s.end &&
          Math.abs(e.scrollTop - s.scroll) < 2 && document.activeElement === e && v.src === s.src && Math.abs(v.currentTime - s.time) < .05 && v.paused;
      }));
      assert.equal(await page.evaluate(() => localStorage.getItem('h3-feedback-split')), String(touchedRatio));
      const movedDivider = await handle.boundingBox();
      await page.mouse.move(movedDivider.x + movedDivider.width / 2, movedDivider.y + 100);
      await page.mouse.down(); await page.mouse.move(1, movedDivider.y + 100, {steps: 8}); await page.mouse.up();
      assert.equal(await handle.getAttribute('aria-valuenow'), await handle.getAttribute('aria-valuemin'));
      for (const pane of ['#feedbackVideos', '#feedbackNotebook']) assert((await page.locator(pane).boundingBox()).width >= 299);
      await handle.focus(); await page.keyboard.press('End');
      assert.equal(await handle.getAttribute('aria-valuenow'), await handle.getAttribute('aria-valuemax'));
      for (const pane of ['#feedbackVideos', '#feedbackNotebook']) assert((await page.locator(pane).boundingBox()).width >= 299);
      await page.keyboard.press('ArrowLeft');
      assert.equal(Number(await handle.getAttribute('aria-valuenow')), Number(await handle.getAttribute('aria-valuemax')) - 1);
      // Cancellation and stacked/mobile layout must release capture and leave the document intact.
      const cancelDivider = await handle.boundingBox();
      const cancelPoint = {x: cancelDivider.x + 8, y: cancelDivider.y + 80, id: 2};
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [cancelPoint]});
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchCancel', touchPoints: []});
      assert.equal(await page.locator('#feedbackWorkspace').evaluate(el => el.classList.contains('is-resizing')), false);
      await page.setViewportSize({width: 390, height: 844});
      assert.equal(await handle.isVisible(), false);
      await page.waitForFunction(() => document.querySelector('#feedbackResizer').getAttribute('aria-disabled') === 'true');
      await page.setViewportSize(viewport);
      await page.waitForFunction(() => document.querySelector('#feedbackResizer').getAttribute('aria-disabled') === 'false');
      await page.evaluate(async () => {
        const video = document.querySelector('#feedbackVideo'); video.currentTime = .1; await video.play(); window.playingTime = video.currentTime;
      });
      const playingDivider = await handle.boundingBox();
      await page.mouse.move(playingDivider.x + 8, playingDivider.y + 100);
      await page.mouse.down(); await page.mouse.move(playingDivider.x - 20, playingDivider.y + 100, {steps: 4}); await page.mouse.up();
      assert(await page.evaluate(() => !splitSnapshot.video.paused && splitSnapshot.video.currentTime >= playingTime));
      await page.evaluate(() => { splitSnapshot.video.pause(); splitSnapshot.video.currentTime = splitSnapshot.time; });
      await page.waitForFunction(() => !document.querySelector('#feedbackVideo').seeking);
      await page.evaluate(() => {
        const range = document.querySelector('#feedbackSplit'); range.value = '55'; range.dispatchEvent(new Event('input', {bubbles: true}));
      });
      assert.equal(await handle.getAttribute('aria-valuenow'), '55');
      assert(await page.evaluate(() => splitSnapshot.editor === document.querySelector('#feedbackNoteBody') && splitSnapshot.video === document.querySelector('#feedbackVideo') && splitSnapshot.editor.value === splitSnapshot.body && splitSnapshot.video.src === splitSnapshot.src && Math.abs(splitSnapshot.video.currentTime - splitSnapshot.time) < .05));
      await cdp.detach();
      // Failed saves preserve a draft across a full reload, then retry on reconnect.
      failSave = true;
      await page.locator('#feedbackNoteBody').fill('연결이 끊겨도 남아야 하는 초안');
      await page.waitForFunction(() => document.querySelector('#feedbackSaveStatus').dataset.state === 'error');
      await page.reload();
      assert.equal(await page.locator('#feedbackFontSize').inputValue(), '24');
      assert.equal(await page.locator('#sidebarToggle').getAttribute('aria-expanded'), 'false');
      await page.waitForFunction(() => document.querySelector('#feedbackResizer').getAttribute('aria-valuenow') === '55');
      await page.waitForFunction(() => document.querySelector('#feedbackNoteBody').value === '연결이 끊겨도 남아야 하는 초안');
      failSave = false;
      await page.evaluate(() => dispatchEvent(new Event('online')));
      await page.waitForFunction(() => document.querySelector('#feedbackSaveStatus').dataset.state === 'saved');
      let record = (await request('/api/feedback-notes/' + first.note_id)).body;
      assert.equal(record.body, '연결이 끊겨도 남아야 하는 초안');
      // A concurrent writer wins only its own CAS; the local editor keeps its text.
      const remote = await request('/api/feedback-notes/' + first.note_id, {method: 'PUT', body: JSON.stringify({expected_revision: record.revision, body: '다른 기기의 수정 내용'})});
      assert.equal(remote.response.status, 200);
      await page.locator('#feedbackNoteBody').fill('내 초안은 별도로 보존');
      await page.waitForSelector('#feedbackConflict:not([hidden])');
      assert.equal(await page.locator('#feedbackNoteBody').inputValue(), '내 초안은 별도로 보존');
      assert.equal((await request('/api/feedback-notes/' + first.note_id)).body.body, '다른 기기의 수정 내용');
      await page.locator('#feedbackShowServer').tap();
      await page.waitForSelector('#feedbackHistoryDialog[open]');
      assert.match(await page.locator('#feedbackRevisionBody').textContent(), /다른 기기의 수정 내용/);
      await page.locator('#feedbackHistoryClose').tap();
      await page.locator('#feedbackCopyConflict').tap();
      await page.waitForFunction(id => document.querySelector('#feedbackNoteList').value !== id && document.querySelector('#feedbackSaveStatus').dataset.state === 'saved', first.note_id);
      const copyId = await page.locator('#feedbackNoteList').inputValue();
      assert.equal((await request('/api/feedback-notes/' + copyId)).body.body, '내 초안은 별도로 보존');
      await page.locator('#feedbackNoteBody').fill('수정한 두 번째 내용');
      await page.waitForFunction(() => document.querySelector('#feedbackSaveStatus').dataset.state === 'saved');
      const history = (await request('/api/feedback-notes/' + copyId + '/history')).body.revisions;
      assert(history.length >= 2);
      await (await reveal(page, 'feedbackHistory')).tap();
      await page.waitForSelector('#feedbackHistoryDialog[open]');
      await page.locator('#feedbackRevisionList').selectOption(history.at(-1).revision);
      await page.waitForFunction(() => document.querySelector('#feedbackRevisionBody').textContent.includes('내 초안은 별도로 보존'));
      await page.locator('#feedbackRestoreRevision').tap();
      await page.waitForFunction(() => !document.querySelector('#feedbackHistoryDialog').open);
      assert.equal((await request('/api/feedback-notes/' + copyId)).body.body, '내 초안은 별도로 보존');
      assert.equal((await request('/api/feedback-notes/' + copyId + '/history')).body.revisions.length, history.length + 1);
      // Checkboxes and optional candidate/timestamp bookmarks never own the note.
      await page.locator('#feedbackNoteBody').fill('- [ ] 반영 확인');
      await (await reveal(page, 'feedbackPreview')).tap();
      await page.locator('[data-feedback-check="0"]').check();
      await page.waitForFunction(() => document.querySelector('#feedbackSaveStatus').dataset.state === 'saved');
      assert.equal((await request('/api/feedback-notes/' + copyId)).body.body, '- [x] 반영 확인');
      await page.locator('[data-feedback-job="ja"]').tap();
      await page.locator('#feedbackInsertReference').tap();
      await page.waitForFunction(() => document.querySelector('#feedbackNoteBody').value.includes('feedback_job=ja'));
      await (await reveal(page, 'feedbackPreview')).tap();
      const bookmark = page.locator('#feedbackNotePreview a');
      await page.evaluate(() => {
        const player = document.querySelector('#feedbackVideo'); player.pause(); player.currentTime = 2;
        const link = document.querySelector('#feedbackNotePreview a'), url = new URL(link.href);
        url.searchParams.set('feedback_time', '0'); link.href = url.href;
      });
      await bookmark.tap();
      await page.waitForFunction(() => document.querySelector('#feedbackVideo').currentTime < 1);
      assert.equal(await page.locator('#feedbackNoteList').inputValue(), copyId);
      await (await reveal(page, 'feedbackArchive')).tap();
      await page.waitForFunction(() => document.querySelector('#feedbackArchive').textContent === '보관 해제');
      assert.equal((await request('/api/feedback-notes/' + copyId)).body.archived, true);
      assert(await page.locator('#feedbackReadOnly').isVisible());
      if (await page.locator('#feedbackNoteBody').isHidden()) await (await reveal(page, 'feedbackPreview')).tap();
      const archivedBody = await page.locator('#feedbackNoteBody').inputValue();
      await page.locator('#feedbackNoteBody').tap();
      await page.keyboard.type('must not edit');
      assert.equal(await page.locator('#feedbackNoteBody').inputValue(), archivedBody);
      await page.locator('#feedbackEditArchived').tap();
      await page.waitForFunction(() => document.querySelector('#feedbackArchive').textContent === '노트 보관');
      await page.waitForFunction(() => document.querySelector('#feedbackNoteBody').getAttribute('aria-readonly') === 'false');
      assert.equal(await page.locator('#feedbackNoteBody').getAttribute('aria-readonly'), 'false');
      assert.equal(await page.locator('#feedbackReadOnly').isVisible(), false);
      await page.locator('#feedbackNoteBody').tap();
      await page.keyboard.press('ControlOrMeta+End');
      await page.keyboard.type(' keyboard works after unarchive');
      await page.waitForFunction(() => document.querySelector('#feedbackSaveStatus').dataset.state === 'saved');
      const left = await page.locator('#feedbackVideos').boundingBox(), right = await page.locator('#feedbackNotebook').boundingBox();
      assert(left.x + left.width <= right.x + 1);
      assert(right.width > 200 && right.x + right.width <= viewport.width);
      const bodyText = (await request('/api/feedback-notes/' + copyId)).body.body;
      assert(bodyText.includes('feedback_job=ja'));
      assert(bodyText.includes('keyboard works after unarchive'));
      const editorBounds = await page.locator('#feedbackNoteBody').boundingBox();
      assert(editorBounds.height >= 300);
      assert(editorBounds.height > viewport.height * .65);
      assert((await page.locator('#feedbackWorkspace').boundingBox()).y < 20);
      await (await reveal(page, 'feedbackNoteTitle')).tap();
      await page.keyboard.press('End');
      await page.keyboard.type(' keyboard title');
      await page.waitForFunction(() => document.querySelector('#feedbackSaveStatus').dataset.state === 'saved');
      assert((await page.locator('#feedbackNoteTitle').inputValue()).includes('keyboard title'));
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#feedbackFileMenu').evaluate(el => el.open), false);
      await page.locator('#feedbackNoteBody').tap();
      await page.locator('#sidebarToggle').tap();
      await page.locator('#studioSidebar [data-page="queue"]').tap();
      assert(await page.locator('main > header').isVisible());
      assert.equal(await page.locator('#sidebarToggle').evaluate(el => el.parentElement.tagName), 'HEADER');
      await page.locator('#studioSidebar [data-page="feedback"]').tap();
      await page.locator('#sidebarBackdrop').tap({position: {x: viewport.width - 20, y: 150}});
      assert.equal(await page.locator('main > header').isVisible(), false);
      assert.deepEqual(errors, []);
      await page.screenshot({path: `/tmp/video-engine-feedback-notes-${viewport.width}.png`});
      console.log(`PASS ${viewport.width}×${viewport.height}: 터치/마우스 분할 드래그·최소 너비·키보드/취소·비율 저장/복원·회전/모바일·영상/노트/커서 유지·메뉴·실제 저장 API·오프라인/충돌 복구`);
      await context.close();
    }
  } catch (error) { console.error(logs); throw error; }
  finally { if (browser) await browser.close(); server.kill(); fs.rmSync(fixture, {recursive: true, force: true}); }
})().catch(error => { console.error(error); process.exitCode = 1; });
