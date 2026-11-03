const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root = path.resolve(__dirname, '..');
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jR1kAAAAASUVORK5CYII=', 'base64');

(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    for (const viewport of [{width: 1024, height: 768}, {width: 768, height: 1024}]) {
      const context = await browser.newContext({viewport, hasTouch: true});
      const page = await context.newPage(), errors = [];
      page.on('pageerror', error => errors.push(error.message));
      const jobs = Array.from({length: 12}, (_, i) => ({job_id: `j${i}`, request: {candidate_index: 1, width: 608, height: 352}, status: {status: 'completed'}, manifest: {}}));
      let sets = jobs.slice(0, 10).map((job, i) => ({candidate_set_id: `s${i}`, status: 'completed', generation_mode: 'r2v', candidate_job_ids: [job.job_id], references: [{picture_index: 1, reference_kind: 'event_anchor', role: 'single_full_frame_event_anchor', original_name: 'anchor.png'}], prompt: 'test', source_clip_id: `clip${i}`}));
      const adapter = {adapter_id: 'r2v', generation_mode: 'r2v', workflow_filename: '(basic)video_minimax_h3_r2v_int8_turbo_api.json', model_name: 'test', adapter_name: 'H3', adapter_version: '1', default_for_generation: true};
      let holdNext = false, heldResponse = null;
      await page.route('http://audit.local/**', async route => {
        const url = new URL(route.request().url()), pathname = url.pathname;
        if (pathname.startsWith('/api/')) {
          if (pathname.endsWith('/video-thumbnail') || pathname.includes('/pictures/')) return route.fulfill({contentType: 'image/png', body: png});
          let data = {};
          if (pathname === '/api/h3/config') data = {adapters: [adapter]};
          else if (pathname === '/api/h3/state') data = {jobs, candidate_sets: sets, worker: {}, workers: {}, test_queues: []};
          else if (pathname === '/api/h3/candidate-page' || pathname === '/api/h3/results-page') {
            data = {jobs, candidate_sets: sets.slice(0, 10), pagination: {page: 1, total_pages: 2, total: sets.length, start: 1, end: 10}};
            if (holdNext) {
              holdNext = false;
              const snapshot = JSON.stringify(data);
              await new Promise(resolve => { heldResponse = () => { route.fulfill({contentType: 'application/json', body: snapshot}).then(resolve); }; });
              return;
            }
          } else if (pathname === '/api/h3/projects') data = {projects: []};
          else if (pathname === '/api/h3/action-assets') data = {assets: [], presets: {}};
          else if (pathname.endsWith('/select')) {
            const id = pathname.split('/')[4], job = JSON.parse(route.request().postData()).job_id;
            sets = sets.map(set => set.candidate_set_id === id ? {...set, selected_job_id: job, selected_jobs: [{job_id: job}]} : set);
          } else if (pathname.includes('/selection/')) {
            const id = pathname.split('/')[4];
            sets = sets.map(set => set.candidate_set_id === id ? {...set, selected_job_id: null, selected_jobs: []} : set);
          }
          return route.fulfill({contentType: 'application/json', body: JSON.stringify(data)});
        }
        const file = path.join(root, 'web/public', pathname === '/' ? 'index.html' : pathname.slice(1));
        if (!fs.existsSync(file)) return route.fulfill({status: 404, body: ''});
        return route.fulfill({contentType: pathname.endsWith('.js') ? 'application/javascript' : pathname.endsWith('.css') ? 'text/css' : 'text/html', body: fs.readFileSync(file)});
      });
      await page.addInitScript(() => { window.EventSource = class {addEventListener() {} close() {}}; });
      page.on('dialog', dialog => dialog.accept());
      await page.goto('http://audit.local/#candidates');
      await page.waitForSelector('[data-h3-candidate-set="s6"]');
      const article = page.locator('[data-h3-candidate-set="s6"]');
      await article.scrollIntoViewIfNeeded();
      await page.evaluate(() => {
        window.oldArticle = document.querySelector('[data-h3-candidate-set="s6"]');
        window.oldImage = oldArticle.querySelector('[data-h3-candidate-play] img');
        window.oldVisual = oldArticle.querySelector('[data-h3-candidate-storyboard]');
        window.oldButton = oldArticle.querySelector('[data-h3-select]');
        oldButton.focus({preventScroll: true});
      });
      let y = await page.evaluate(() => scrollY);
      await page.evaluate(() => refreshH3State());
      assert(Math.abs(await page.evaluate(() => scrollY) - y) <= 2);
      assert(await page.evaluate(() => oldArticle.isConnected && oldImage.isConnected && oldVisual.isConnected && oldButton === document.activeElement));
      // Insert a new candidate above the reader, preserving the same card's offset.
      let top = (await article.boundingBox()).y;
      sets = [{...sets[0], candidate_set_id: 'newer', candidate_job_ids: ['j10']}, ...sets];
      await page.evaluate(() => refreshH3State());
      assert(Math.abs((await article.boundingBox()).y - top) <= 2);
      // Selecting/cancelling must preserve position and update the actual controls.
      await page.locator('[data-h3-select="s6:j6"]').scrollIntoViewIfNeeded();
      top = (await article.boundingBox()).y;
      await page.locator('[data-h3-select="s6:j6"]').tap();
      await page.waitForSelector('[data-h3-clear-selection="s6"][data-h3-clear-selection-job="j6"]');
      assert(Math.abs((await article.boundingBox()).y - top) <= 2);
      await page.locator('[data-h3-clear-selection="s6"][data-h3-clear-selection-job="j6"]').tap();
      await page.waitForSelector('[data-h3-select="s6:j6"]');
      assert(Math.abs((await article.boundingBox()).y - top) <= 2);
      // A modal's opener remains attached while background status updates arrive.
      await article.locator('[data-h3-candidate-storyboard]').scrollIntoViewIfNeeded();
      top = (await article.boundingBox()).y;
      await article.locator('[data-h3-candidate-storyboard]').tap();
      await page.waitForFunction(() => document.querySelector('#h3PicturePreviewDialog').open);
      await page.evaluate(() => refreshH3State());
      assert(await page.evaluate(() => oldVisual.isConnected));
      await page.locator('#h3PicturePreviewClose').tap();
      assert(Math.abs((await article.boundingBox()).y - top) <= 2);
      // Late responses cannot replace a newer candidate page or rewind user scroll.
      holdNext = true;
      await page.evaluate(() => { window.slowRefresh = refreshH3PagedState('candidates'); });
      while (!heldResponse) await new Promise(resolve => setTimeout(resolve, 10));
      sets = [{...sets[0], candidate_set_id: 'latest', candidate_job_ids: ['j11']}, ...sets];
      await page.evaluate(() => refreshH3PagedState('candidates'));
      await page.evaluate(() => scrollBy(0, -100));
      y = await page.evaluate(() => scrollY);
      heldResponse();
      await page.evaluate(() => slowRefresh);
      assert.equal(await page.locator('[data-h3-candidate-set="latest"]').count(), 1);
      assert(Math.abs(await page.evaluate(() => scrollY) - y) <= 2);
      // The results view keeps expanded prompts and its original thumbnail nodes.
      sets = sets.map(set => ({...set, selected_job_id: set.candidate_job_ids[0], selected_jobs: [{job_id: set.candidate_job_ids[0]}]}));
      await page.evaluate(() => goPage('results'));
      await page.waitForSelector('[data-h3-selected-job="j6"]');
      const resultCard = page.locator('[data-h3-selected-job="j6"]');
      await resultCard.locator('.h3-result-prompt summary').scrollIntoViewIfNeeded();
      await resultCard.locator('.h3-result-prompt summary').tap();
      await page.evaluate(() => {
        window.oldResult = document.querySelector('[data-h3-selected-job="j6"]');
        window.oldPrompt = oldResult.querySelector('.h3-result-prompt');
        window.oldResultImage = oldResult.querySelector('img');
      });
      y = await page.evaluate(() => scrollY);
      await page.evaluate(() => refreshH3State());
      assert(Math.abs(await page.evaluate(() => scrollY) - y) <= 2);
      assert(await page.evaluate(() => oldResult.isConnected && oldPrompt.isConnected && oldPrompt.open && oldResultImage.isConnected));
      // Generation-page refresh preserves options, user input and fixed notices.
      await page.evaluate(() => goPage('create'));
      await page.locator('#h3CreateForm button.primary').first().scrollIntoViewIfNeeded();
      await page.evaluate(() => {
        window.oldOption = document.querySelector('#h3Adapter option');
        document.querySelector('#h3PromptInput').value = '작성 중인 프롬프트';
      });
      y = await page.evaluate(() => scrollY);
      await page.evaluate(() => { note('후보 큐 등록 완료'); });
      await page.evaluate(() => refreshH3State());
      assert(Math.abs(await page.evaluate(() => scrollY) - y) <= 2);
      assert(await page.evaluate(() => oldOption.isConnected));
      assert.equal(await page.locator('#h3PromptInput').inputValue(), '작성 중인 프롬프트');
      assert.deepEqual(errors, []);
      console.log(`PASS ${viewport.width}×${viewport.height}: 자동 갱신·DOM 유지·신규 후보 삽입·선택/취소·팝업·응답 순서·사용자 스크롤·결과 펼침·생성 입력/안내`);
      await context.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
