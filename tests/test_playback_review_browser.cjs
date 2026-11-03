const assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root = path.resolve(__dirname, '..'), fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'playback-review-'));
const python = path.join(root, '.venv/bin/python'), port = 18655, origin = `http://127.0.0.1:${port}`, key = 'playback-test';
execFileSync(python, ['-c', `
import sys
from pathlib import Path
import h3_queue
from job_queue import atomic_write_json
root=Path(sys.argv[1]);p=h3_queue.roots(root)
for project in ['A','B']:
 for i in range(1,13):
  jid=f'{project}-{i}';sid=f'set-{jid}'
  atomic_write_json(p['jobs']/jid/'request.json',dict(job_id=jid,candidate_set_id=sid,job_type='h3_r2v_generate',source_project_id=project,source_scene_id='S1',source_clip_id=f'C{i}',candidate_index=1,seed=i))
  atomic_write_json(p['jobs']/jid/'status.json',dict(status='completed'))
  atomic_write_json(p['jobs']/jid/'manifest.json',dict(local_video_path=str(root/f'{project}.mp4')))
  atomic_write_json(p['candidate_sets']/sid/'candidate_set.json',dict(candidate_set_id=sid,candidate_job_ids=[jid],source_project_id=project,source_scene_id='S1',source_clip_id=f'C{i}',selected_jobs=[dict(job_id=jid,selected_at='2026-10-22T00:00:00+00:00')]))
`, fixture], {cwd: root});
for (const [name, duration] of [['A',4],['B',6]]) execFileSync('ffmpeg', ['-v','error','-f','lavfi','-i',`color=${name === 'A' ? 'blue' : 'red'}:s=160x90:d=${duration}`,'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',path.join(fixture,name+'.mp4')]);
const server = spawn(process.execPath, [path.join(root,'web/server.mjs')], {env:{...process.env,VIDEO_UI_HOST:'127.0.0.1',VIDEO_UI_PORT:String(port),VIDEO_UI_ACCESS_KEY:key,VIDEO_ENGINE_ROOT:fixture,VIDEO_ENGINE_PYTHON:python},stdio:['ignore','pipe','pipe']});
let logs=''; server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function request(url, options={}) {
 const res=await fetch(origin+url,{...options,headers:{'x-access-key':key,'content-type':'application/json'}});
 assert(res.ok,await res.clone().text());return res.json();
}
(async()=>{
 let browser;
 try {
  for(let i=0;i<80;i++){try{await fetch(origin+'/dual-playback.js');break;}catch{await wait(100);}}
  assert.equal((await fetch(origin+'/api/h3/selected-screening?project_id=A')).status,401);
  browser=await chromium.launch({headless:true});
  for(const viewport of [{width:1024,height:768},{width:768,height:1024}]) {
   const context=await browser.newContext({viewport,hasTouch:true}),page=await context.newPage(),errors=[];
   page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
   await page.addInitScript(()=>{sessionStorage.setItem('h3-key','playback-test');window.EventSource=class{addEventListener(){}close(){}};});
   let failSave=false;
   await page.route(origin+'/api/**',async route=>{
    const name=new URL(route.request().url()).pathname;
    if(name==='/api/h3/selected-screening' && route.request().method()==='PUT' && failSave) return route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({error:'저장 실패 시험'})});
    if(name.endsWith('/video')) {
     const job=name.split('/')[4],body=fs.readFileSync(path.join(fixture,job.startsWith('B')?'B.mp4':'A.mp4'));
     const range=route.request().headers().range?.match(/bytes=(\d+)-(\d*)/);
     if(range){const start=Number(range[1]),end=range[2]?Math.min(Number(range[2]),body.length-1):body.length-1;return route.fulfill({status:206,contentType:'video/mp4',headers:{'accept-ranges':'bytes','content-range':`bytes ${start}-${end}/${body.length}`},body:body.subarray(start,end+1)});}
     return route.fulfill({contentType:'video/mp4',headers:{'accept-ranges':'bytes'},body});
    }
    if(name.endsWith('/video-thumbnail'))return route.fulfill({contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=','base64')});
    if(['/api/h3/candidate-page','/api/h3/results-page','/api/h3/state','/api/h3/selected-screening'].includes(name)||name.startsWith('/api/project-comparisons'))return route.continue();
    return route.fulfill({contentType:'application/json',body:JSON.stringify(name==='/api/h3/config'?{adapters:[]}:name==='/api/h3/projects'?{projects:[]}:name==='/api/h3/action-assets'?{assets:[],presets:{}}:{})});
   });
   const l=role=>page.locator(`#compareLeft [data-role="${role}"]`),r=role=>page.locator(`#compareRight [data-role="${role}"]`),dual=name=>page.locator(`[data-dual="${name}"]`);
   async function go(name){await page.evaluate(name=>goPage(name),name);}
   await page.goto(origin+'/#compare');
   await page.waitForFunction(()=>document.querySelector('#compareProjectA').options.length===3);
   assert(await dual('play').isDisabled());
   await page.locator('#compareProjectA').selectOption('A');await page.locator('#compareProjectB').selectOption('B');
   await page.waitForFunction(()=>!document.querySelector('#comparePosition').disabled&&[...document.querySelectorAll('.compare-review-video video')].every(v=>v.readyState>=1));
   await page.locator('#compareOptions').evaluate(el=>el.open=true);
   await dual('pause').tap();
   assert.deepEqual(await page.locator('.compare-review-video video').evaluateAll(v=>v.map(x=>x.muted)),[false,true]);
   await dual('audio').selectOption('1');assert.deepEqual(await page.locator('.compare-review-video video').evaluateAll(v=>v.map(x=>x.muted)),[true,false]);
   await dual('play').tap();await wait(450);await dual('pause').tap();
   let times=await page.locator('.compare-review-video video').evaluateAll(v=>v.map(x=>({paused:x.paused,time:x.currentTime})));
   assert(times.every(v=>v.paused));assert(times[0].time>.15,JSON.stringify(times));assert(Math.abs(times[0].time-times[1].time)<.25);
   // Inject a small follower-clock lag without seeking. It must not trigger recurring hard jumps.
   await page.locator('#compareOptions').evaluate(el=>el.open=false);
   await page.locator('#comparePlay').tap();
   await page.evaluate(()=>{
    const b=document.querySelector('#compareRight video'),property=Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype,'currentTime');
    window.syncTrace={seeks:0,framesBefore:b.getVideoPlaybackQuality().totalVideoFrames};
    Object.defineProperty(b,'currentTime',{configurable:true,get(){return property.get.call(this)-.25;},set(value){window.syncTrace.seeks++;property.set.call(this,value);}});
   });
   await wait(1100);
   const smooth=await page.evaluate(()=>{const b=document.querySelector('#compareRight video');return {...window.syncTrace,rate:b.playbackRate,framesAfter:b.getVideoPlaybackQuality().totalVideoFrames};});
   assert.equal(smooth.seeks,0,JSON.stringify(smooth));assert(smooth.rate>1&&smooth.rate<=1.051,JSON.stringify(smooth));
   assert(smooth.framesAfter>smooth.framesBefore,JSON.stringify(smooth));
   await page.locator('#comparePause').tap();await page.evaluate(()=>delete document.querySelector('#compareRight video').currentTime);
   await page.locator('#compareOptions').evaluate(el=>el.open=true);
   await page.evaluate(()=>{const s=document.querySelector('[data-dual=seek]');s.value='500';s.dispatchEvent(new Event('input'));});
   await page.waitForFunction(()=>[...document.querySelectorAll('.compare-review-video video')].every(v=>Math.abs(v.currentTime-2)<.1));
   await dual('link').check();
   await page.evaluate(()=>document.querySelector('#compareRight video').currentTime=1);
   await page.waitForFunction(()=>Math.abs(document.querySelector('#compareLeft video').currentTime-1)<.1);
   await page.locator('#comparePlayback details').evaluate(el=>el.open=true);
   await dual('mode').selectOption('ratio');
   await page.evaluate(()=>{const s=document.querySelector('[data-dual=seek]');s.value='500';s.dispatchEvent(new Event('input'));});
   await page.waitForFunction(()=>Math.abs(document.querySelector('#compareLeft video').currentTime-2)<.1&&Math.abs(document.querySelector('#compareRight video').currentTime-3)<.1);
   await dual('from').fill('0.5');await dual('to').fill('1.2');await dual('loop').check();
   await dual('play').tap();await wait(1400);
   times=await page.locator('.compare-review-video video').evaluateAll(v=>v.map(x=>x.currentTime));
   assert(times[0]>=.45&&times[0]<1.3,JSON.stringify(times));assert(Math.abs(times[1]-times[0]*1.5)<.35);
   await dual('pause').tap();
   await page.evaluate(()=>{const v=document.querySelector('#compareRight video');window.savedPlay=v.play;v.play=()=>Promise.reject(new DOMException('test','NotAllowedError'));});
   await dual('play').tap();await page.waitForFunction(()=>document.querySelector('[data-dual=status]').textContent.includes('허용하지'));
   assert(await page.locator('.compare-review-video video').evaluateAll(v=>v.every(x=>x.paused)));
   await page.evaluate(()=>{document.querySelector('#compareRight video').play=window.savedPlay;});
   await dual('to').fill('99');await dual('play').tap();assert((await dual('status').textContent()).includes('반복 시작'));
   await dual('loop').uncheck();
   await page.locator('#compareOptions').evaluate(el=>el.open=false);
   // Leaving comparison always stops both players.
   await page.locator('#comparePlay').tap();await go('results');assert(await page.locator('.compare-review-video video').evaluateAll(v=>v.every(x=>x.paused)));
   await page.waitForFunction(()=>document.querySelector('#h3ResultProjectFilter').options.length===3);
   await page.locator('#h3ResultProjectFilter').selectOption('A');await page.locator('#openSelectedScreening').tap();
   await page.waitForFunction(()=>document.querySelectorAll('#screeningList li').length===12);
   assert((await page.locator('#screeningList li').nth(1).textContent()).includes('C2'));
   await page.locator('[data-screen-play="A-1"]').tap();
   await page.waitForFunction(()=>document.querySelector('#screeningVideo').readyState>=1);
   await page.locator('#screeningPlay').tap();await page.evaluate(()=>document.querySelector('#screeningVideo').currentTime=3.8);
   await page.waitForFunction(()=>document.querySelector('#screeningVideo').src.includes('/A-2/'));
   await page.locator('#screeningPause').tap();await page.locator('[data-screen-play="A-1"]').tap();
   await page.locator('#screeningBoundarySeconds').selectOption('1');await page.locator('#screeningBoundary').tap();
   await page.waitForFunction(()=>document.querySelector('#screeningVideo').src.includes('/A-2/'));
   await page.waitForFunction(()=>document.querySelector('#screeningVideo').src.includes('/A-1/'));
   assert((await page.locator('#screeningEdge').textContent()).includes('C1'));
   await page.locator('#screeningPause').tap();await page.locator('#screeningIssue').fill('시선 연결을 확인');
   failSave=true;await page.locator('#screeningSave').tap();await page.waitForFunction(()=>document.querySelector('#screeningStatus').dataset.error==='true');
   assert.equal(await page.locator('#screeningIssue').inputValue(),'시선 연결을 확인');
   failSave=false;await page.locator('#screeningSave').tap();await page.waitForFunction(()=>document.querySelector('#screeningStatus').textContent.includes('서버에'));
   let review=(await request('/api/h3/selected-screening?project_id=A')).review;
   assert.equal(review.issues['A-1\nA-2'],'시선 연결을 확인');
   await page.locator('[data-screen-exclude="A-12"]').tap();await page.locator('[data-screen-up="A-3"]').tap();
   await page.locator('#screeningSave').tap();await page.waitForFunction(()=>document.querySelector('#screeningStatus').textContent.includes('서버에'));
   await page.locator('#screeningClose').tap();await page.locator('#openSelectedScreening').tap();
   await page.waitForFunction(()=>document.querySelectorAll('#screeningList li').length===12);
   assert((await page.locator('#screeningList li').nth(1).textContent()).includes('C3'));
   assert.equal(await page.locator('[data-screen-exclude="A-12"]').getAttribute('aria-pressed'),'true');
   // Name sorting replaces a saved manual order, without dropping exclusions or edge notes.
   await page.locator('#screeningSortName').tap();
   assert.deepEqual(await page.locator('#screeningList [data-screen-play]').evaluateAll(buttons=>buttons.map(button=>button.dataset.screenPlay)),Array.from({length:12},(_,i)=>`A-${i+1}`));
   assert.equal(await page.locator('[data-screen-exclude="A-12"]').getAttribute('aria-pressed'),'true');
   assert.equal(await page.locator('#screeningIssue').inputValue(),'시선 연결을 확인');
   await page.locator('#screeningSave').tap();await page.waitForFunction(()=>document.querySelector('#screeningStatus').textContent.includes('서버에'));
   await page.locator('#screeningClose').tap();await page.locator('#openSelectedScreening').tap();
   await page.waitForFunction(()=>document.querySelectorAll('#screeningList li').length===12);
   assert.deepEqual(await page.locator('#screeningList [data-screen-play]').evaluateAll(buttons=>buttons.map(button=>button.dataset.screenPlay)),Array.from({length:12},(_,i)=>`A-${i+1}`));
   await page.locator('#screeningPlay').tap();await page.waitForFunction(()=>document.querySelector('#screeningVideo').readyState>=1);
   await page.evaluate(()=>document.querySelector('#screeningVideo').currentTime=3.8);
   await page.waitForFunction(()=>document.querySelector('#screeningVideo').src.includes('/A-2/'));await page.locator('#screeningPause').tap();
   // Restore the manual order for the existing conflict/recovery scenarios below.
   await page.locator('[data-screen-up="A-3"]').tap();await page.locator('[data-screen-play="A-1"]').tap();
   await page.locator('#screeningSave').tap();await page.waitForFunction(()=>document.querySelector('#screeningStatus').textContent.includes('서버에'));
   // A stale writer must not overwrite newer server notes.
   review=(await request('/api/h3/selected-screening?project_id=A')).review;
   await request('/api/h3/selected-screening',{method:'PUT',body:JSON.stringify({...review,issues:{...review.issues,'A-1\nA-3':'다른 화면 기록'}})});
   await page.locator('#screeningIssue').fill('이 화면 입력 보존');await page.locator('#screeningSave').tap();
   await page.waitForFunction(()=>document.querySelector('#screeningStatus').textContent.includes('다른 화면'));
   assert.equal(await page.locator('#screeningIssue').inputValue(),'이 화면 입력 보존');
   assert.equal((await request('/api/h3/selected-screening?project_id=A')).review.issues['A-1\nA-3'],'다른 화면 기록');
   await page.locator('#screeningClose').tap();await page.locator('#openSelectedScreening').tap();
   await page.waitForFunction(()=>!document.querySelector('#screeningRestoreDraft').hidden);
   await page.locator('#screeningRestoreDraft').tap();assert.equal(await page.locator('#screeningIssue').inputValue(),'이 화면 입력 보존');
   await page.locator('#screeningSave').tap();await page.waitForFunction(()=>document.querySelector('#screeningStatus').textContent.includes('서버에'));
   await page.screenshot({path:`/tmp/h3-selected-screening-${viewport.width}.png`});
   await page.locator('#screeningCompare').tap();await page.waitForFunction(()=>!document.querySelector('#screeningDialog').open);
   await page.waitForFunction(()=>document.querySelector('#compareLeft video').src.includes('/A-1/')&&document.querySelector('#compareRight video').src.includes('/A-3/'));
   assert.equal((await request('/api/project-comparisons')).pagination.total,0);
   const selections=await request('/api/h3/selected-screening?project_id=A');assert.equal(selections.items.length,12);
   assert.deepEqual(errors,[]);
   await page.screenshot({path:`/tmp/h3-playback-review-${viewport.width}.png`});
   console.log(`PASS ${viewport.width}×${viewport.height}: pair play/pause/seek/ratio/loop/audio, full playlist, boundary loop, persistence/retry/conflict/draft, candidate navigation`);
   // Reset review only in the isolated test fixture for the next viewport.
   const saved=(await request('/api/h3/selected-screening?project_id=A')).review;
   await request('/api/h3/selected-screening',{method:'PUT',body:JSON.stringify({...saved,order:[],excluded:[],issues:{}})});
   await go('results');
   fs.renameSync(path.join(fixture,'A.mp4'),path.join(fixture,'A.mp4.held'));
   await page.locator('#openSelectedScreening').tap();await page.waitForFunction(()=>document.querySelectorAll('#screeningList li').length===12);
   assert((await page.locator('#screeningStatus').textContent()).includes('원본 없는 후보 12개'));
   assert(await page.locator('[data-screen-play="A-1"]').isDisabled());
   await page.locator('#screeningClose').tap();fs.renameSync(path.join(fixture,'A.mp4.held'),path.join(fixture,'A.mp4'));
   // Start directly in results: comparison metadata must load before assigning the requested pair.
   await page.goto(origin+'/#results');
   await page.waitForFunction(()=>document.querySelector('#h3ResultProjectFilter').options.length===3);
   await page.locator('#h3ResultProjectFilter').selectOption('A');await page.locator('#openSelectedScreening').tap();
   await page.waitForFunction(()=>document.querySelectorAll('#screeningList li').length===12);
   await page.locator('#screeningCompare').tap();
   await page.waitForFunction(()=>document.querySelector('#compareProjectA').value==='A'&&document.querySelector('#compareProjectB').value==='A');
   await page.waitForFunction(()=>document.querySelector('#compareLeft video').src.includes('/A-1/')&&document.querySelector('#compareRight video').src.includes('/A-2/'));
   assert.deepEqual(errors,[]);
   await context.close();
  }
 }catch(error){console.error(logs);throw error;}
 finally{if(browser)await browser.close();server.kill();fs.rmSync(fixture,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
