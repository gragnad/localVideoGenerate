const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root = path.resolve(__dirname, '..');
const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'frame-annotations-'));
const python = path.join(root, '.venv/bin/python');
execFileSync(python, ['-c', `
import json,sys
from pathlib import Path
from PIL import Image
root=Path(sys.argv[1]); export=root/'runtime/h3/frame_exports/test-job/0p5s';export.mkdir(parents=True)
frames=[]
for i in range(2):
 name=f'frame_{i}.png';label=f'label_{i}.png'
 Image.new('RGB',(608,352),'#aabbcc').save(export/name)
 Image.new('RGB',(608,392),'#aabbcc').save(export/label)
 frames.append(dict(filename=name,labeled_filename=label,preview_filename=name,time_seconds=i*.5,frame_index=i*12,label_text=f'TEST candidate 2 - {i*.5}s - frame {i*12}'))
(export/'frames.json').write_text(json.dumps(dict(job_id='test-job',interval_tag='0p5s',source_video_size=123,source_video_mtime_ns=123,frames=frames)))
`, fixture]);
const frames = JSON.parse(fs.readFileSync(path.join(fixture,'runtime/h3/frame_exports/test-job/0p5s/frames.json'))).frames;
const port = 18652;
const server = spawn(process.execPath, [path.join(root,'web/server.mjs')], {env: {...process.env, VIDEO_UI_HOST:'127.0.0.1',VIDEO_UI_PORT:String(port),VIDEO_UI_ACCESS_KEY:'',VIDEO_ENGINE_ROOT:fixture,VIDEO_ENGINE_PYTHON:python}, stdio:['ignore','pipe','pipe']});
let logs='';server.stderr.on('data',d=>logs+=d);server.stdout.on('data',d=>logs+=d);
const origin=`http://127.0.0.1:${port}`;
(async()=>{
 let browser;
 try{
  for(let i=0;i<60;i++){try{await fetch(origin+'/frame-annotations.js');break;}catch{await new Promise(r=>setTimeout(r,100));}}
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1024,height:768},hasTouch:true});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const html=fs.readFileSync(path.join(root,'web/public/index.html'),'utf8');
  const editor=html.slice(html.indexOf('<dialog id="frameAnnotationDialog"'),html.indexOf('<script src="/app.js'));
  const candidate=html.slice(html.indexOf('<dialog id="h3CandidateVideoDialog"'),html.indexOf('<dialog id="modelTestReviewDialog"'));
  const app=fs.readFileSync(path.join(root,'web/public/app.js'),'utf8');
  const frameCode=app.slice(app.indexOf('let h3FrameExportState='),app.indexOf('let h3PicturePreviewDownload='));
  await page.route(origin+'/',route=>route.fulfill({contentType:'text/html',body:`<!doctype html><head><meta charset="utf-8"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/review.css"><link rel="stylesheet" href="/frame-annotations.css"></head><body>${candidate}${editor}<script>const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=s=>String(s),note=()=>{};async function api(url,options){const r=await fetch(url,options);if(!r.ok)throw Error('API failed');return r.json()};${frameCode}</script><script src="/frame-annotations.js"></script></body>`}));
  await page.goto(origin);
  await page.evaluate(frames=>{h3FrameExportState={jobId:'test-job',export:{interval_tag:'0p5s',frames},selected:new Set(),busy:false};renderH3FrameExport();document.querySelector('#h3CandidateVideoDialog').showModal();},frames);
  await page.locator('[data-h3-frame-annotate]').first().click();
  await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('펜슬로'));
  const canvas=page.locator('#frameAnnotationDialog canvas');
  async function stroke(){const box=await canvas.boundingBox();await page.mouse.move(box.x+box.width*.2,box.y+box.height*.2);await page.mouse.down();await page.mouse.move(box.x+box.width*.7,box.y+box.height*.6,{steps:12});await page.mouse.up();}
  await stroke();
  await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('서버 저장 완료'));
  const endpoint=origin+'/api/h3/jobs/test-job/frames/0p5s/frame_0.png/annotation';
  let record=await (await fetch(endpoint)).json();assert.equal(record.strokes.length,1);assert.ok(record.revision);
  const png=await fetch(origin+record.image_url);assert.equal(png.status,200);assert.equal(png.headers.get('content-type'),'image/png');
  assert.match(await page.locator('[data-h3-frame-annotate]').first().textContent(),/저장됨/);
  // Undo, redo, and zoom/rotation must preserve normalized coordinates.
  await page.locator('[data-undo]').click();await page.locator('[data-redo]').click();
  await page.setViewportSize({width:768,height:1024});
  await page.locator('[data-save]').click();
  await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('서버 저장 완료'));
  assert.deepEqual((await (await fetch(endpoint)).json()).strokes,record.strokes);
  // Touch pans, but creates no accidental ink; synthetic pen input does create ink.
  const before=await canvas.boundingBox();
  await page.evaluate(()=>{const stage=document.querySelector('.frame-annotation-stage');stage.setPointerCapture=()=>{};const rect=stage.getBoundingClientRect();for(const [type,x] of [['pointerdown',100],['pointermove',140],['pointerup',140]])stage.dispatchEvent(new PointerEvent(type,{pointerId:42,pointerType:'touch',clientX:rect.x+x,clientY:rect.y+100,bubbles:true}));});
  const after=await canvas.boundingBox();assert.ok(after.x>before.x+30);
  await page.evaluate(()=>{const stage=document.querySelector('.frame-annotation-stage'),rect=stage.getBoundingClientRect();for(const [type,id,x] of [['pointerdown',50,200],['pointerdown',51,300],['pointermove',51,400],['pointerup',50,200],['pointerup',51,400]])stage.dispatchEvent(new PointerEvent(type,{pointerId:id,pointerType:'touch',clientX:rect.x+x,clientY:rect.y+180,bubbles:true}));});
  assert.ok((await canvas.boundingBox()).width > after.width*1.8);
  await page.locator('[data-fit]').click();
  await page.locator('[data-next]').click();
  await page.waitForFunction(()=>document.querySelector('[data-position]').textContent==='2 / 2');
  await page.evaluate(()=>{const stage=document.querySelector('.frame-annotation-stage'),rect=document.querySelector('#frameAnnotationDialog canvas').getBoundingClientRect();for(const [type,x] of [['pointerdown',.2],['pointermove',.5],['pointerup',.5]])stage.dispatchEvent(new PointerEvent(type,{pointerId:0,pointerType:'pen',clientX:rect.x+rect.width*x,clientY:rect.y+rect.height*.4,bubbles:true}));});
  await page.locator('[data-prev]').click();
  await page.waitForFunction(()=>document.querySelector('[data-position]').textContent==='1 / 2');
  record=await (await fetch(endpoint)).json();assert.equal(record.strokes.length,1);
  // Eraser removes a whole hit stroke, redo works after reopening.
  await page.locator('[data-tool]').selectOption('erase');
  const box=await canvas.boundingBox();await page.mouse.click(box.x+box.width*.2,box.y+box.height*.2);
  await page.locator('[data-save]').click();
  await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('서버 저장 완료'));
  assert.equal((await (await fetch(endpoint)).json()).strokes.length,0);
  await page.locator('[data-undo]').click();await page.locator('[data-save]').click();
  await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('서버 저장 완료'));
  // Offline failure cannot mark saved or discard changes during navigation/close.
  await page.locator('[data-tool]').selectOption('pen');
  await page.route('**/annotation',route=>route.request().method()==='PUT'?route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'테스트 연결 실패'})}):route.continue());
  await stroke();await page.locator('[data-next]').click();
  await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('이동하지 않았습니다'));
  assert.equal(await page.locator('[data-position]').textContent(),'1 / 2');
  await page.locator('[data-close]').click();assert.ok(await page.locator('#frameAnnotationDialog').isVisible());
  await page.unroute('**/annotation');await page.locator('[data-save]').click();
  await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('서버 저장 완료'));
  assert.equal((await (await fetch(endpoint)).json()).strokes.length,2);
  // Stale revision from a second device never silently overwrites server data.
  record=await (await fetch(endpoint)).json();
  await fetch(endpoint,{method:'PUT',headers:{'content-type':'application/json'},body:JSON.stringify({expected_revision:record.revision,strokes:[]})});
  await stroke();await page.locator('[data-save]').click();
  await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('다른 화면'));
  assert.equal((await (await fetch(endpoint)).json()).strokes.length,0);
  page.once('dialog',dialog=>dialog.accept());await page.locator('[data-server-version]').click();
  await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('불러옴'));
  await page.screenshot({path:'/tmp/frame-annotations-ui.png'});
  await page.locator('[data-close]').click();
  await page.locator('[data-h3-frame-annotate]').first().click();
  await page.waitForFunction(()=>document.querySelector('[data-status]').textContent.includes('불러옴'));
  assert.equal(errors.length,0,errors.join('\n'));
  console.log('PASS: integrated frame button, auto/manual server save, PNG, reopen, undo/redo, eraser, touch pan, portrait rotation, next/previous, offline retention, concurrent conflict');
 }finally{await browser?.close();server.kill('SIGTERM');fs.rmSync(fixture,{recursive:true,force:true});}
})().catch(e=>{console.error(e);console.error(logs.slice(-2500));process.exitCode=1;});
