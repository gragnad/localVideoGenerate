const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn,execFileSync}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root=path.resolve(__dirname,'..'),fixture=fs.mkdtempSync(path.join(os.tmpdir(),'project-review-')),port=18654,origin='http://127.0.0.1:'+port;
const python=path.join(root,'.venv/bin/python'),video=path.join(fixture,'test.mp4');
execFileSync('ffmpeg',['-v','error','-f','lavfi','-i','color=blue:s=160x90:d=4','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',video]);
const server=spawn(process.execPath,[path.join(root,'web/server.mjs')],{env:{...process.env,VIDEO_UI_HOST:'127.0.0.1',VIDEO_UI_PORT:String(port),VIDEO_UI_ACCESS_KEY:'review-test',VIDEO_ENGINE_ROOT:fixture,VIDEO_ENGINE_PYTHON:python},stdio:['ignore','pipe','pipe']});
let logs='';server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const sets={},jobs={};
for(const project of ['A','B','V2']){
 sets[project]=[];jobs[project]=[];
 for(let n=1;n<=55;n++){
  if(project==='B'&&n===2)continue;
  const clip=(project==='V2'?'V2_':'C')+n, sid=project+'-set-'+n,ids=[];
  for(let c=1;c<=3;c++){
   const id=project+'-'+n+'-'+c;ids.push(id);
   jobs[project].push({job_id:id,status:{status:c===3?'queued':'completed'},request:{source_project_id:project,source_scene_id:'S1',source_clip_id:clip,candidate_index:c}});
  }
  sets[project].push({candidate_set_id:sid,source_clip_id:clip,source_scene_id:'S1',candidate_job_ids:ids,created_at:'2026-10-24'});
 }
 // Duplicate sets must remain available, not silently discarded.
 sets[project].push({...sets[project][0],candidate_set_id:project+'-older',created_at:'2026-10-20'});
}
(async()=>{let browser;try{
 for(let n=0;n<80;n++){try{await fetch(origin+'/project-compare.js');break;}catch{await wait(100);}}
 browser=await chromium.launch({headless:true});
 for(const viewport of [{width:1280,height:889},{width:1024,height:768},{width:768,height:1024}]){
  const context=await browser.newContext({viewport,hasTouch:true}),page=await context.newPage(),errors=[],writes=[],pages=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.addInitScript(()=>{sessionStorage.setItem('h3-key','review-test');window.EventSource=class{addEventListener(){}close(){}};});
  let fail=false;
  await page.route(origin+'/api/**',async route=>{
   const request=route.request(),url=new URL(request.url()),name=url.pathname;
   if(request.method()!=='GET'&&!name.startsWith('/api/feedback-notes'))writes.push(name);
   if(name.startsWith('/api/feedback-notes')){
    if(fail&&request.method()==='PUT')return route.abort('failed');
    return route.continue();
   }
   if(name.endsWith('/video'))return route.fulfill({contentType:'video/mp4',body:fs.readFileSync(video)});
   let data={jobs:[],candidate_sets:[],test_queues:[],items:[],pagination:{page:1,total_pages:1,total:0},filters:{}};
   if(name==='/api/h3/candidate-page'){
    const project=url.searchParams.get('project_id'),p=Number(url.searchParams.get('page')||1),size=Number(url.searchParams.get('page_size')||10);
    pages.push([project,p]);const all=sets[project]||[],slice=all.slice((p-1)*size,p*size),ids=new Set(slice.flatMap(s=>s.candidate_job_ids));
    data={candidate_sets:slice,jobs:(jobs[project]||[]).filter(j=>ids.has(j.job_id)),filters:{projects:['A','B','V2']},pagination:{total_pages:Math.max(1,Math.ceil(all.length/size))}};
   }else if(name==='/api/h3/config')data={adapters:[]};
   else if(name==='/api/h3/projects')data={projects:[]};
   else if(name==='/api/h3/action-assets')data={assets:[],presets:{}};
   return route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
  });
  await page.goto(origin+'/#compare');
  await page.waitForFunction(()=>document.querySelector('#compareProjectA').options.length===4);
  assert.equal(await page.locator('main>header').isVisible(),false);
  assert.equal(await page.locator('#sidebarToggle').evaluate(e=>e.parentElement.id),'compareNavigation');
  assert.equal(await page.locator('#feedbackNotebook').evaluate(e=>e.parentElement.id),'compareNotebookHost');
  assert.equal(await page.locator('#compareLikeLeft').count(),0);
  await page.locator('#compareProjectA').selectOption('A');await page.locator('#compareProjectB').selectOption('B');
  await page.waitForFunction(()=>document.querySelector('#comparePosition').options.length===55&&!document.querySelector('#comparePosition').disabled);
  assert(pages.some(([p,n])=>p==='A'&&n===2));assert(pages.some(([p,n])=>p==='B'&&n===2));
  assert((await page.locator('#compareLeft [data-role=title]').textContent()).includes('C1'));
  assert.equal(await page.locator('#compareLeft [data-role=set] option').count(),2);
  await page.locator('#compareLeft [data-job="A-1-2"]').tap();
  assert((await page.locator('#compareLeft video').getAttribute('src')).includes('A-1-2'));
  assert(await page.locator('#compareLeft [data-job="A-1-3"]').isDisabled());
  await page.locator('#feedbackFileMenu>summary').tap();await page.locator('#feedbackNew').tap();
  await page.locator('#feedbackFileMenu>summary').tap();await page.locator('#feedbackNoteTitle').fill('검토 '+viewport.width);await page.locator('#feedbackNoteBody').fill('공유 노트: 첫 번째 기록');
  await page.waitForFunction(()=>document.querySelector('#feedbackSaveStatus').dataset.state==='saved');
  await page.locator('#compareNext').tap();
  assert((await page.locator('#compareLeft [data-role=title]').textContent()).includes('C2'));
  assert.equal(await page.locator('#compareRight [data-role=empty]').textContent(),'대응 영상 없음');
  await page.locator('#compareNext').tap();
  assert((await page.locator('#compareRight [data-role=title]').textContent()).includes('C3'));
  assert.equal(await page.locator('#feedbackNoteBody').inputValue(),'공유 노트: 첫 번째 기록');
  await page.locator('#compareFirst').tap();
  await page.waitForFunction(()=>[...document.querySelectorAll('.compare-review-video video')].every(v=>v.readyState>=1));
  await page.locator('#comparePlay').tap();await wait(350);await page.locator('#comparePause').tap();
  assert(await page.locator('.compare-review-video video').evaluateAll(v=>v.every(e=>e.paused&&e.currentTime>.05)));
  const geometry=await page.evaluate(()=>{
   const rect=id=>{const r=document.getElementById(id).getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,b:r.bottom};};
   return {left:rect('compareLeft'),right:rect('compareRight'),note:rect('feedbackNoteBody'),workspace:rect('compareWorkspace'),overflow:document.documentElement.scrollWidth>innerWidth};
  });
  assert(geometry.right.y>geometry.left.y);assert(geometry.note.x>geometry.left.x);
  assert(geometry.note.h>viewport.height*.6,JSON.stringify(geometry));assert(!geometry.overflow,JSON.stringify(geometry));
  const old=await page.locator('#compareResizer').getAttribute('aria-valuenow');
  await page.locator('#compareResizer').focus();await page.keyboard.press('ArrowRight');
  assert(Number(await page.locator('#compareResizer').getAttribute('aria-valuenow'))>=Number(old));
  await page.locator('#feedbackNoteBody').tap();await page.keyboard.press('End');await page.keyboard.type(' keyboard');
  const caret=await page.locator('#feedbackNoteBody').evaluate(e=>[e.selectionStart,e.selectionEnd]);
  await page.evaluate(()=>{window.editorNode=document.getElementById('feedbackNoteBody');goPage('feedback');});
  assert.equal(await page.locator('#feedbackNotebook').evaluate(e=>e.parentElement.id),'feedbackWorkspace');
  assert((await page.locator('#feedbackNoteBody').inputValue()).includes('keyboard'));
  await page.evaluate(()=>goPage('compare'));
  assert(await page.evaluate(()=>window.editorNode===document.getElementById('feedbackNoteBody')));
  assert.deepEqual(await page.locator('#feedbackNoteBody').evaluate(e=>[e.selectionStart,e.selectionEnd]),caret);
  await page.locator('#compareProjectB').selectOption('V2');
  await page.waitForFunction(()=>document.querySelector('#comparePosition').options.length===110&&!document.querySelector('#comparePosition').disabled);
  assert.equal(await page.locator('#compareRight video').isVisible(),false);
  await page.locator('#compareOptions>summary').tap();await page.locator('#compareMatch').selectOption(JSON.stringify(['S1','V2_1']));await page.locator('#compareSaveMatch').tap();
  assert((await page.locator('#compareRight [data-role=title]').textContent()).includes('V2_1'));
  await page.locator('#compareOptions>summary').tap();
  fail=true;await page.locator('#feedbackNoteBody').fill('오프라인 초안 유지');
  await page.waitForFunction(()=>document.querySelector('#feedbackSaveStatus').dataset.state==='error');
  await page.locator('#compareNext').tap();assert.equal(await page.locator('#feedbackNoteBody').inputValue(),'오프라인 초안 유지');
  fail=false;await page.evaluate(()=>dispatchEvent(new Event('online')));
  await page.waitForFunction(()=>document.querySelector('#feedbackSaveStatus').dataset.state==='saved');
  await page.reload();await page.waitForFunction(()=>document.querySelector('#feedbackNoteBody').value==='오프라인 초안 유지'&&!document.querySelector('#comparePosition').disabled);
  await page.locator('#compareFirst').tap();assert((await page.locator('#compareRight [data-role=title]').textContent()).includes('V2_1'));
  await page.waitForFunction(()=>[...document.querySelectorAll('.compare-review-video video')].every(v=>v.readyState>=2));
  await page.screenshot({path:'/tmp/project-review-'+viewport.width+'.png'});
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);
  console.log('PASS review',viewport,geometry);await context.close();
 }
}catch(e){console.error(logs);throw e;}finally{if(browser)await browser.close();server.kill();fs.rmSync(fixture,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1;});
