const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root = path.resolve(__dirname, '..');
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 1024, height: 768}, hasTouch: true});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setContent('<div id="notice"></div><button id="save">후보 선택</button><button id="cancel" disabled>사용 불가</button><dialog><button id="modalSave">서버 저장</button></dialog>');
    await page.addStyleTag({content: fs.readFileSync(path.join(root, 'web/public/interaction-feedback.css'), 'utf8')});
    await page.addScriptTag({content: fs.readFileSync(path.join(root, 'web/public/interaction-feedback.js'), 'utf8')});
    const app = fs.readFileSync(path.join(root, 'web/public/app.js'), 'utf8');
    await page.addScriptTag({content: app.slice(0, app.indexOf('async function copyTextToClipboard'))});
    await page.evaluate(() => {
      Object.defineProperty(window, 'sessionStorage', {value: {getItem: () => '', setItem() {}, removeItem() {}}});
      window.calls = 0;
      window.fetch = () => { window.calls++; return new Promise(resolve => { window.respond = resolve; }); };
      for (const id of ['save', 'modalSave']) document.getElementById(id).onclick = async () => {
        try { await api('/test'); note('선택을 저장했습니다.'); }
        catch (error) { note(error.message, true); }
      };
    });
    assert.equal(await page.locator('#save').evaluate(el => getComputedStyle(el).minHeight), '44px');
    await page.locator('#save').tap();
    assert.equal(await page.locator('#save').getAttribute('aria-busy'), 'true');
    assert.match(await page.locator('#save').evaluate(el => getComputedStyle(el, '::after').content), /처리 중/);
    await page.locator('#save').tap();
    assert.equal(await page.evaluate(() => calls), 1);
    await page.evaluate(() => respond({status: 200, ok: true, json: async () => ({saved: true})}));
    await page.waitForFunction(() => document.querySelector('.interaction-notice').textContent === '선택을 저장했습니다.');
    assert.equal(await page.locator('#save').getAttribute('aria-busy'), null);
    await page.evaluate(() => document.querySelector('dialog').showModal());
    await page.locator('#modalSave').tap();
    assert.equal(await page.locator('dialog .interaction-notice').count(), 1);
    await page.evaluate(() => respond({status: 500, ok: false, json: async () => ({error: '서버 저장 실패'})}));
    await page.waitForFunction(() => document.querySelector('.interaction-notice').dataset.kind === 'error');
    assert.equal(await page.locator('.interaction-notice').textContent(), '서버 저장 실패');
    assert.equal(await page.locator('#modalSave').getAttribute('aria-busy'), null);
    await page.setViewportSize({width: 768, height: 1024});
    const bounds = await page.locator('.interaction-notice').boundingBox();
    assert(bounds.x >= 0 && bounds.x + bounds.width <= 768 && bounds.y + bounds.height <= 1024);
    assert.deepEqual(errors, []);
    console.log('PASS: 터치 브라우저 · 실제 API 연결 · 44px · 진행 표시 · 반복 입력 방지 · 성공/실패 · 모달 · 세로 화면');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
