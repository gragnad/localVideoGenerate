const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn,execFileSync}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root=path.resolve(__dirname,'..'),fixture=fs.mkdtempSync(path.join(os.tmpdir(),'result-count-filter-')),python=path.join(root,'.venv/bin/python'),port=18658,origin='http://127.0.0.1:'+port;
execFileSync(python,['-c',`
import sys
from pathlib import Path
import h3_queue
from tests.test_results_rerender_filter import ResultRerenderFilterTests
t=ResultRerenderFilterTests();t.root=Path(sys.argv[1]);t.paths=h3_queue.roots(t.root)
for i in range(16):
 sid,jid=t._candidate(i,selected=True)
 for n in range(i%8):t.rerender(sid,jid,str(n),['queued','running','completed'][n%3])
 t.rerender(sid,jid,'failed','failed');t.rerender(sid,jid,'cancelled','cancelled')
`,fixture],{cwd:root});
const server=spawn(process.execPath,[path.join(root,'web/server.mjs')],{env:{...process.env,VIDEO_UI_HOST:'127.0.0.1',VIDEO_UI_PORT:String(port),VIDEO_UI_ACCESS_KEY:'filter-test',VIDEO_ENGINE_ROOT:fixture,VIDEO_ENGINE_PYTHON:python},stdio:['ignore','pipe','pipe']});
let logs='';server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{let browser;try{
 for(let i=0;i<80;i++){try{await fetch(origin+'/app.js');break;}catch{await wait(100);}}
 browser=await chromium.launch({headless:true});
 for(const viewport of [{width:1280,height:889},{width:1024,height:768},{width:768,height:1024}]){
  const context=await browser.newContext({viewport,hasTouch:true}),page=await context.newPage(),errors=[],writes=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.addInitScript(()=>{sessionStorage.setItem('h3-key','filter-test');window.EventSource=class{addEventListener(){}close(){}};});
  await page.route(origin+'/api/**',async route=>{
   const req=route.request(),name=new URL(req.url()).pathname;
   if(req.method()!=='GET')writes.push(name);
   if(['/api/h3/results-page','/api/h3/candidate-page','/api/h3/state','/api/h3/selected-screening'].includes(name))return route.continue();
   if(name.endsWith('/video-thumbnail'))return route.fulfill({status:204});
   const data=name==='/api/h3/config'?{adapters:[]}:name==='/api/h3/projects'?{projects:[]}:name==='/api/h3/action-assets'?{assets:[],presets:{}}:{};
   return route.fulfill({json:data});
  });
  await page.goto(origin+'/#results');
  await page.waitForFunction(()=>h3ResultsPageData?.pagination.total===16);
  const filter=page.locator('#h3ResultRerenderCountFilter');
  assert.deepEqual(await filter.locator('option').evaluateAll(opts=>opts.map(o=>o.value)),['','0','1','2','3','4','5','n']);
  for(const value of ['0','1','2','3','4','5','n']){
   await filter.selectOption(value);
   await page.waitForFunction(({value,total})=>h3ResultsPageData?.pagination.total===total&&h3ResultsPageData?.rerender_count_filter===value,{value,total:value==='n'?4:2});
   assert.equal(await page.locator('#h3SelectedResults [data-h3-selected-job]').count(),value==='n'?4:2);
   assert.equal(await page.evaluate(()=>h3ResultsPage),1);
  }
  await filter.selectOption('0');await page.waitForFunction(()=>h3ResultsPageData?.rerender_count_filter==='0');
  const names=await page.locator('#h3SelectedResults [data-h3-selected-job]').evaluateAll(els=>els.map(el=>el.dataset.h3SelectedJob).sort());
  assert.deepEqual(names,['job-00','job-08']);
  await page.locator('#refreshH3Results').tap();await page.waitForFunction(()=>h3ResultsPageData?.rerender_count_filter==='0');
  assert.equal(await filter.inputValue(),'0');
  await page.locator('#h3ResultProjectFilter').selectOption('project-a');await page.locator('#h3ResultSceneFilter').selectOption('scene-2');
  await page.waitForFunction(()=>h3ResultsPageData?.pagination.total===2&&document.querySelector('#h3ResultSceneFilter').value==='scene-2');
  await filter.selectOption('5');await page.waitForFunction(()=>h3ResultsPageData?.pagination.total===0&&h3ResultsPageData?.rerender_count_filter==='5');
  assert((await page.locator('#h3SelectedResults').textContent()).includes('필터'));
  await page.locator('#resetH3ResultFilters').tap();
  await page.waitForFunction(()=>h3ResultsPageData?.pagination.total===16&&h3ResultsPageData?.rerender_count_filter==='');
  assert.equal(await filter.inputValue(),'');assert.equal(await page.locator('#h3ResultProjectFilter').inputValue(),'');assert.equal(await page.locator('#h3ResultSceneFilter').inputValue(),'');
  await page.evaluate(()=>goH3ResultsPage(2));assert.equal(await page.evaluate(()=>h3ResultsPage),2);
  await filter.selectOption('0');await page.waitForFunction(()=>h3ResultsPageData?.rerender_count_filter==='0'&&h3ResultsPage===1);
  const bounds=await page.evaluate(()=>{
   const panel=document.querySelector('[data-view=results] .h3-source-filters'),r=panel.getBoundingClientRect();
   return {panel:{x:r.x,right:r.right},controls:[...panel.querySelectorAll('button,select')].map(el=>{const b=el.getBoundingClientRect();return {id:el.id,x:b.x,right:b.right,h:b.height};}),overflow:document.documentElement.scrollWidth>innerWidth};
  });
  for(const c of bounds.controls){assert(c.x>=bounds.panel.x&&c.right<=bounds.panel.right+1,JSON.stringify(bounds));assert(c.h>=44,JSON.stringify(c));}
  assert(!bounds.overflow,JSON.stringify(bounds));
  await page.screenshot({path:'/tmp/result-filter-'+viewport.width+'.png'});
  await page.locator('#h3ResultProjectFilter').selectOption('project-a');
  await page.locator('#openSelectedScreening').tap();await page.waitForFunction(()=>document.querySelector('#screeningDialog')?.open);await page.locator('#screeningClose').tap();
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);console.log('PASS result count filter',viewport,bounds);await context.close();
 }
}catch(e){console.error(logs);throw e;}finally{if(browser)await browser.close();server.kill();fs.rmSync(fixture,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1;});
