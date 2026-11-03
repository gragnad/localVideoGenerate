const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn,execFileSync}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root=path.resolve(__dirname,'..'),fixture=fs.mkdtempSync(path.join(os.tmpdir(),'multi-screening-')),python=path.join(root,'.venv/bin/python'),port=18659,origin='http://127.0.0.1:'+port,key='multi-test';
const video=path.join(fixture,'test.mp4');
execFileSync('ffmpeg',['-v','error','-f','lavfi','-i','color=blue:s=160x90:d=4','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',video]);
execFileSync(python,['-c',`
import sys
from pathlib import Path
import h3_queue
from job_queue import atomic_write_json
root=Path(sys.argv[1]);p=h3_queue.roots(root)
for project in ['A','B','C']:
 for n in range(1,13):
  ids=[f'{project}-{n}']
  if project=='A' and n==1:ids.append('A-1-alt')
  sid=f'set-{project}-{n}';scene='S1' if project=='A' else 'S2'
  for i,jid in enumerate(ids):
   atomic_write_json(p['jobs']/jid/'request.json',dict(job_id=jid,job_type='h3_r2v_generate',candidate_set_id=sid,source_project_id=project,source_scene_id=scene,source_clip_id=f'C{n}',candidate_index=i+1,seed=n))
   atomic_write_json(p['jobs']/jid/'status.json',dict(status='completed'))
   atomic_write_json(p['jobs']/jid/'manifest.json',dict(local_video_path=str(root/'test.mp4')))
  atomic_write_json(p['candidate_sets']/sid/'candidate_set.json',dict(candidate_set_id=sid,candidate_job_ids=ids,source_project_id=project,source_scene_id=scene,source_clip_id=f'C{n}',selected_jobs=[dict(job_id=jid) for jid in ids]))
`,fixture],{cwd:root});
const server=spawn(process.execPath,[path.join(root,'web/server.mjs')],{env:{...process.env,VIDEO_UI_HOST:'127.0.0.1',VIDEO_UI_PORT:String(port),VIDEO_UI_ACCESS_KEY:key,VIDEO_ENGINE_ROOT:fixture,VIDEO_ENGINE_PYTHON:python},stdio:['ignore','pipe','pipe']});
let logs='';server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function request(query){const res=await fetch(origin+'/api/h3/selected-screening?'+query,{headers:{'x-access-key':key}});assert(res.ok,await res.clone().text());return res.json();}
(async()=>{let browser;try{
 for(let i=0;i<80;i++){try{await fetch(origin+'/selected-screening.js');break;}catch{await wait(100);}}
 assert.equal((await fetch(origin+'/api/h3/selected-screening?project_id=A&project_id=B')).status,401);
 browser=await chromium.launch({headless:true});
 for(const viewport of [{width:1024,height:768},{width:768,height:1024}]){
  const context=await browser.newContext({viewport,hasTouch:true}),page=await context.newPage(),errors=[],writes=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.addInitScript(()=>{sessionStorage.setItem('h3-key','multi-test');window.EventSource=class{addEventListener(){}close(){}};});
  await page.route(origin+'/api/**',async route=>{
   const req=route.request(),name=new URL(req.url()).pathname;
   if(req.method()!=='GET')writes.push([req.method(),name]);
   if(['/api/h3/selected-screening','/api/h3/results-page','/api/h3/candidate-page','/api/h3/state'].includes(name))return route.continue();
   if(name.endsWith('/video'))return route.fulfill({contentType:'video/mp4',body:fs.readFileSync(video)});
   if(name.endsWith('/video-thumbnail'))return route.fulfill({status:204});
   return route.fulfill({json:name==='/api/h3/config'?{adapters:[]}:name==='/api/h3/projects'?{projects:[]}:name==='/api/h3/action-assets'?{assets:[],presets:{}}:{}});
  });
  await page.goto(origin+'/#results');await page.waitForFunction(()=>document.querySelector('#h3ResultProjectFilter').options.length===4);
  await page.locator('#h3ResultProjectFilter').selectOption('A');await page.locator('#h3ResultSceneFilter').selectOption('S1');
  await page.locator('#openSelectedScreening').tap();await page.waitForFunction(()=>document.querySelectorAll('#screeningList li').length===13);
  await page.locator('#screeningProjectPicker').evaluate(el=>el.open=true);
  await page.locator('[data-screen-project="B"]').check();await page.locator('#screeningApplyProjects').tap();
  await page.waitForFunction(()=>document.querySelectorAll('#screeningList li').length===25);
  assert.deepEqual(await page.locator('#screeningList [data-screen-play]').evaluateAll(els=>els.slice(0,3).map(el=>el.dataset.screenPlay)),['A-1','A-1-alt','B-1']);
  assert((await page.locator('#screeningList li').filter({has:page.locator('[data-screen-play="B-1"]')}).textContent()).includes('B / S2 / C1'));
  assert((await page.locator('#screeningScope').textContent()).includes('전체 씬'));
  const api=await request('project_id=B&project_id=A');assert.equal(api.items.length,25);assert.equal(new Set(api.items.map(i=>i.job_id)).size,25);
  await page.locator('[data-screen-exclude="A-1-alt"]').tap();
  await page.locator('[data-screen-play="A-1"]').tap();await page.waitForFunction(()=>document.querySelector('#screeningVideo').readyState>=1);
  await page.locator('#screeningPlay').tap();await page.evaluate(()=>document.querySelector('#screeningVideo').currentTime=3.8);
  await page.waitForFunction(()=>document.querySelector('#screeningVideo').src.includes('/B-1/'));await page.locator('#screeningPause').tap();
  await page.locator('[data-screen-play="A-1"]').tap();await page.locator('#screeningIssue').fill('A에서 B 연결 확인');
  await page.locator('[data-screen-up="B-2"]').tap();await page.locator('#screeningSave').tap();
  await page.waitForFunction(()=>document.querySelector('#screeningStatus').textContent.includes('서버에'));
  const saved=(await request('project_id=A&project_id=B')).review;
  assert(saved.excluded.includes('A-1-alt'));assert.equal(saved.issues['A-1\nB-1'],'A에서 B 연결 확인');
  assert.equal((await request('project_id=A')).review.revision,0);
  await page.locator('#screeningClose').tap();await page.locator('#openSelectedScreening').tap();await page.waitForFunction(()=>document.querySelectorAll('#screeningList li').length===25);
  assert.equal(await page.locator('[data-screen-exclude="A-1-alt"]').getAttribute('aria-pressed'),'true');
  await page.locator('#screeningProjectPicker').evaluate(el=>el.open=true);
  await page.locator('[data-screen-project="A"]').uncheck();await page.locator('[data-screen-project="B"]').uncheck();
  assert(await page.locator('#screeningApplyProjects').isDisabled());
  await page.locator('[data-screen-project="A"]').check();await page.locator('[data-screen-project="B"]').check();await page.locator('#screeningApplyProjects').tap();
  await page.waitForFunction(()=>document.querySelectorAll('#screeningList li').length===25);
  await page.locator('#screeningSortName').tap();await page.locator('[data-screen-play="A-1"]').tap();
  await page.locator('#screeningSave').tap();await page.waitForFunction(()=>document.querySelector('#screeningStatus').textContent.includes('서버에'));
  await page.screenshot({path:'/tmp/multi-project-screening-'+viewport.width+'.png'});
  assert(await page.locator('#screeningDialog').evaluate(el=>el.scrollWidth<=el.clientWidth+1));
  await page.locator('#screeningCompare').tap();await page.waitForFunction(()=>document.querySelector('#compareLeft video').src.includes('/A-1/')&&document.querySelector('#compareRight video').src.includes('/B-1/'));
  await page.evaluate(()=>goPage('results'));await page.reload();await page.waitForFunction(()=>document.querySelector('#h3ResultProjectFilter').options.length===4);
  await page.locator('#openSelectedScreening').tap();assert(await page.locator('#screeningProjectPicker').evaluate(el=>el.open));
  await page.locator('[data-screen-project="A"]').check();await page.locator('[data-screen-project="B"]').check();await page.locator('#screeningApplyProjects').tap();
  await page.waitForFunction(()=>document.querySelectorAll('#screeningList li').length===25);
  assert.equal(await page.locator('[data-screen-exclude="A-1-alt"]').getAttribute('aria-pressed'),'true');
  assert(writes.every(([method,name])=>method==='PUT'&&name==='/api/h3/selected-screening'));assert.deepEqual(errors,[]);
  // Reset only the isolated multi-scope review between viewports; legacy state must remain untouched.
  const current=(await request('project_id=A&project_id=B')).review;
  await fetch(origin+'/api/h3/selected-screening',{method:'PUT',headers:{'x-access-key':key,'content-type':'application/json'},body:JSON.stringify({...current,order:[],excluded:[],issues:{}})});
  console.log('PASS multi-project screening',viewport);await context.close();
 }
}catch(e){console.error(logs);throw e;}finally{if(browser)await browser.close();server.kill();fs.rmSync(fixture,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1;});
