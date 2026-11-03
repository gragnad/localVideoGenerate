const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root = path.resolve(__dirname, '..');
const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'feedback-selection-'));
const video = path.join(fixture, 'video.mp4');
execFileSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=black:s=160x90:d=10', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', video]);
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    for (const viewport of [{width: 1024, height: 768}, {width: 768, height: 1024}]) {
      const context = await browser.newContext({viewport, hasTouch: true});
      const page = await context.newPage(), errors = [], writes = [];
      let selected = [], fail = false, held = null, hold = false, accept = true;
      const jobs = ['ja', 'jb', 'jc'].map((id, i) => ({job_id: id, request: {candidate_index: i + 1, source_project_id: 'P', source_scene_id: 'S', source_clip_id: 'C'}, status: {status: i === 2 ? 'running' : 'completed'}}));
      const noteId = 'note_' + 'a'.repeat(32);
      let note = {note_id: noteId, title: '독립 검토', body: '기존 내용\n'.repeat(100), revision: 1, archived: false};
      const set = () => ({candidate_set_id: 's', candidate_job_ids: jobs.map(j => j.job_id), selected_jobs: selected.map(job_id => ({job_id})), source_project_id: 'P', source_scene_id: 'S', source_clip_id: 'C', generation_mode: 'r2v', status: 'completed'});
      page.on('pageerror', e => errors.push(e.message));
      page.on('dialog', d => accept ? d.accept() : d.dismiss());
      await page.addInitScript(id => { localStorage.setItem('h3-independent-note-last', id); window.EventSource = class {addEventListener() {} close() {}}; }, noteId);
      await page.route('http://audit.local/**', async route => {
        const req = route.request(), name = new URL(req.url()).pathname;
        if (!name.startsWith('/api/')) {
          const file = path.join(root, 'web/public', name === '/' ? 'index.html' : name.slice(1));
          return route.fulfill({status: fs.existsSync(file) ? 200 : 404, contentType: name.endsWith('.js') ? 'application/javascript' : name.endsWith('.css') ? 'text/css' : 'text/html', body: fs.existsSync(file) ? fs.readFileSync(file) : ''});
        }
        if (name.endsWith('/video')) {
          const bytes = fs.readFileSync(video), range = req.headers().range;
          if (range) {
            const match = /bytes=(\d+)-(\d*)/.exec(range);
            const start = Number(match[1]), end = match[2] ? Math.min(Number(match[2]), bytes.length - 1) : bytes.length - 1;
            return route.fulfill({status: 206, headers: {'content-type': 'video/mp4', 'accept-ranges': 'bytes', 'content-range': `bytes ${start}-${end}/${bytes.length}`}, body: bytes.subarray(start, end + 1)});
          }
          return route.fulfill({contentType: 'video/mp4', headers: {'accept-ranges': 'bytes'}, body: bytes});
        }
        if (name.endsWith('/video-thumbnail')) return route.fulfill({status: 204});
        let data = {};
        if (name === '/api/h3/config') data = {adapters: []};
        else if (name === '/api/h3/state') data = {jobs, candidate_sets: [set()], worker: {}, workers: {}, test_queues: []};
        else if (name === '/api/h3/projects') data = {projects: []};
        else if (name === '/api/h3/action-assets') data = {assets: [], presets: {}};
        else if (name === '/api/h3/candidate-page' || name === '/api/h3/results-page') data = {jobs, candidate_sets: [set()], pagination: {page: 1, total_pages: 1, total: selected.length || 1}, filters: {projects: ['P'], scenes_by_project: {P: ['S']}, clips_by_project_scene: {P: {S: ['C']}}}};
        else if (name === '/api/feedback-notes') data = {notes: [note]};
        else if (name === '/api/feedback-notes/' + noteId) {
          if (req.method() === 'PUT') note = {...note, ...req.postDataJSON(), revision: note.revision + 1};
          data = note;
        } else if (name.startsWith('/api/h3/candidate-sets/s/')) {
          writes.push({method: req.method(), name, body: req.postDataJSON()});
          if (hold) await new Promise(resolve => { held = resolve; });
          if (fail) return route.fulfill({status: 500, contentType: 'application/json', body: JSON.stringify({error: '선택 저장 실패'})});
          if (name.endsWith('/select')) selected = [...new Set([...selected, req.postDataJSON().job_id])];
          else selected = selected.filter(id => id !== name.split('/').at(-1));
          data = {candidate_set: set()};
        }
        return route.fulfill({contentType: 'application/json', body: JSON.stringify(data)});
      });
      await page.goto('http://audit.local/#feedback');
      const action = id => page.locator(`[data-feedback-select-job="${id}"]`);
      await page.waitForSelector('[data-feedback-select-job="ja"]');
      await page.waitForFunction(() => !document.querySelector('#feedbackNoteBody').disabled);
      assert(await action('jc').isDisabled());
      assert.equal(await action('ja').textContent(), '이 후보 선택');
      await page.locator('[data-feedback-job="ja"]').tap();
      await page.waitForFunction(() => document.querySelector('#feedbackVideo').readyState >= 1);
      await page.locator('#feedbackNoteBody').fill('작성 중\n' + '검토 내용\n'.repeat(100));
      await page.waitForFunction(() => document.querySelector('#feedbackSaveStatus').dataset.state === 'saved');
      await page.evaluate(() => {
        const e = document.querySelector('#feedbackNoteBody'), v = document.querySelector('#feedbackVideo');
        e.focus(); e.setSelectionRange(5, 7); e.scrollTop = 200; v.pause(); v.currentTime = 2;
        window.snapshot = {e, v, body: e.value, start: e.selectionStart, end: e.selectionEnd, scroll: e.scrollTop, src: v.getAttribute('src')};
      });
      await page.waitForFunction(() => !document.querySelector('#feedbackVideo').seeking);
      hold = true;
      await action('ja').tap();
      await page.waitForFunction(() => document.querySelector('[data-feedback-select-job="jb"]').disabled);
      await action('ja').evaluate(el => { el.click(); el.click(); });
      assert.equal(writes.length, 1);
      while (!held) await wait(10);
      hold = false; held();
      await page.waitForFunction(() => document.querySelector('[data-feedback-select-job="ja"]').getAttribute('aria-pressed') === 'true' && !document.querySelector('[data-feedback-select-job="ja"]').disabled);
      assert.equal(await action('ja').textContent(), '선택됨 · 선택 취소');
      assert.deepEqual(selected, ['ja']);
      assert(await page.evaluate(() => {
        const s = snapshot, e = document.querySelector('#feedbackNoteBody'), v = document.querySelector('#feedbackVideo');
        return s.e === e && s.v === v && s.body === e.value && s.start === e.selectionStart && s.end === e.selectionEnd && Math.abs(s.scroll - e.scrollTop) < 2 && s.src === v.getAttribute('src') && Math.abs(v.currentTime - 2) < .1;
      }));
      const box = await action('jb').boundingBox(); assert(box.height >= 44 && box.x >= 0 && box.x + box.width <= viewport.width);
      await action('jb').tap();
      await page.waitForFunction(() => document.querySelector('[data-feedback-select-job="jb"]').getAttribute('aria-pressed') === 'true');
      assert.deepEqual(selected, ['ja', 'jb']);
      accept = false; await action('ja').tap(); await wait(100); assert.deepEqual(selected, ['ja', 'jb']);
      accept = true; await action('ja').tap();
      await page.waitForFunction(() => document.querySelector('[data-feedback-select-job="ja"]').getAttribute('aria-pressed') === 'false');
      assert.deepEqual(selected, ['jb']);
      assert(writes.some(w => w.method === 'DELETE' && w.name === '/api/h3/candidate-sets/s/selection/ja'));
      fail = true; await action('ja').tap();
      await page.waitForFunction(() => document.querySelector('#feedbackCandidateStatus').textContent.includes('선택 저장 실패'));
      assert.equal(await action('ja').getAttribute('aria-pressed'), 'false');
      assert.equal(await page.locator('#feedbackSaveStatus').getAttribute('data-state'), 'saved');
      fail = false;
      // Existing pages consume the same selection contract; external page-04 edits refresh page 10.
      await page.evaluate(() => goPage('results'));
      await page.waitForSelector('[data-h3-selected-job="jb"]');
      await page.evaluate(() => goPage('candidates'));
      await page.waitForSelector('[data-h3-clear-selection-job="jb"]');
      selected = ['ja'];
      await page.evaluate(() => goPage('feedback'));
      await page.waitForFunction(() => document.querySelector('[data-feedback-select-job="ja"]').getAttribute('aria-pressed') === 'true');
      assert.equal(await action('jb').getAttribute('aria-pressed'), 'false');
      await page.reload();
      await page.waitForSelector('[data-feedback-select-job="ja"][aria-pressed="true"]');
      assert((await page.locator('#feedbackNoteBody').inputValue()).startsWith('작성 중'));
      await page.screenshot({path: `/tmp/feedback-selection-${viewport.width}.png`});
      assert.deepEqual(errors, []);
      await context.close();
      console.log(`feedback selection ${viewport.width}: passed`);
    }
  } finally { await browser.close(); fs.rmSync(fixture, {recursive: true, force: true}); }
})().catch(e => { console.error(e); process.exitCode = 1; });
