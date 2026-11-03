const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const app = fs.readFileSync(path.join(__dirname, '../web/public/app.js'), 'utf8');
const resolutions = app.match(/^const h3R2VProductionResolutions=.*;$/m)[0];
const controls = app.match(/^function h3ResultRerenderControls\(.*$/m)[0];
const context = vm.createContext({esc: value => String(value).replace(/"/g, '&quot;'), h3RerenderRiskMessage: (w, h) => `risk:${w}x${h}`});
vm.runInContext(resolutions + '\n' + controls, context);
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage();
    for (const [width, height, expected] of [[608, 352, '1280x704'], [832, 480, '1280x704'], [1024, 576, '1280x704'], [1280, 704, '1280x736'], [1280, 736, '1344x768']]) {
      const html = context.h3ResultRerenderControls({}, {width, height}, false, 'source');
      await page.setContent(html);
      assert.equal(await page.locator('select').inputValue(), expected);
      assert.equal(await page.locator('option[selected]').count(), 1);
      assert.equal(await page.locator('[data-h3-resolution-risk]').textContent(), 'risk:' + expected);
      assert.equal(await page.locator('[data-h3-resolution-rerender]').count(), 1);
      assert.equal(await page.locator('[data-h3-resolution-rerender-random]').count(), 1);
      if (width === 608) {
        await page.locator('select').selectOption('1344x768');
        assert.equal(await page.locator('select').inputValue(), '1344x768');
        await page.locator('select').selectOption('1024x576');
        assert.equal(await page.locator('select').inputValue(), '1024x576');
      }
    }
    assert(context.h3ResultRerenderControls({}, {width: 1344, height: 768}, false, 'source').includes('최고 해상도'));
    assert.equal(context.h3ResultRerenderControls({}, {width: 608, height: 352}, true, 'source'), '');
    console.log('PASS results default: 1280x704, single selected option, risk alignment, manual choice, higher-source fallback, highest/I2V unchanged');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
