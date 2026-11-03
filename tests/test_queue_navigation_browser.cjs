const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn,execFileSync}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root=path.resolve(__dirname,'..'),fixture=fs.mkdtempSync(path.join(os.tmpdir(),'queue-navigation-'));
const python=path.join(root,'.venv/bin/python'),port=18657,origin='http://127.0.0.1:'+port,key='queue-test';
execFileSync(python,['-c',`
import sys
from pathlib import Path
import h3_queue
from job_queue import atomic_write_json
p=h3_queue.roots(Path(sys.argv[1]))
def job(jid,request,status):
 atomic_write_json(p['jobs']/jid/'request.json',dict(job_id=jid,**request))
 atomic_write_json(p['jobs']/jid/'status.json',dict(status=status,progress=.35,stage='test generation'))
for i in range(12):
 jid=f'original-{i:02d}';sid=f'source-{i:02d}';stamp=f'2026-10-25T00:{i:02d}:00+00:00'
 job(jid,dict(job_type='h3_r2v_generate',candidate_set_id=sid,source_project_id='P',source_scene_id='S1',source_clip_id=f'C{i}',candidate_index=1,width=608,height=352),'completed')
 atomic_write_json(p['candidate_sets']/sid/'candidate_set.json',dict(candidate_set_id=sid,candidate_job_ids=[jid],source_project_id='P',source_scene_id='S1',source_clip_id=f'C{i}',created_at=stamp,updated_at=stamp,selected_jobs=[dict(job_id=jid,selected_at=stamp)]))
job('highres',dict(job_type='h3_r2v_generate',queue_lane='local_generation',candidate_set_id='rerender',render_purpose='resolution_rerender',source_candidate_set_id='source-00',source_selected_job_id='original-00',source_project_id='P',source_scene_id='S1',source_clip_id='C0',width=1280,height=704),'running')
atomic_write_json(p['candidate_sets']/'rerender'/'candidate_set.json',dict(candidate_set_id='rerender',render_purpose='resolution_rerender',source_candidate_set_id='source-00',source_selected_job_id='original-00',candidate_job_ids=['highres'],source_project_id='P',source_scene_id='S1',source_clip_id='C0',target_resolution=dict(width=1280,height=704)))
for jid,req in [
 ('regular',dict(source_project_id='P',source_scene_id='S1',source_clip_id='C0')),
 ('i2v',dict(source_project_id='PI',source_scene_id='S1',source_clip_id='C0',generation_mode='i2v')),
 ('gone',dict(source_project_id='DELETED',source_scene_id='S1',source_clip_id='C0')),
 ('direct',dict(prompt='<script>unsafe</script>')),
 ('orphan-rerender',dict(render_purpose='resolution_rerender',source_selected_job_id='not-selected',source_project_id='P',source_scene_id='S1',source_clip_id='C0')),
 ('test-r2v',dict(job_type='h3_r2v_benchmark',test_session_id='TEST-R')),
 ('test-i2v',dict(job_type='h3_model_benchmark',test_session_id='TEST-I',generation_mode='i2v')),
]:
 req.setdefault('job_type','h3_r2v_generate');req.setdefault('queue_lane','windows_candidate')
 job(jid,req,'queued')
`,fixture],{cwd:root});
const server=spawn(process.execPath,[path.join(root,'web/server.mjs')],{env:{...process.env,VIDEO_UI_HOST:'127.0.0.1',VIDEO_UI_PORT:String(port),VIDEO_UI_ACCESS_KEY:key,VIDEO_ENGINE_ROOT:fixture,VIDEO_ENGINE_PYTHON:python},stdio:['ignore','pipe','pipe']});
let logs='';server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{let browser;try{
 for(let i=0;i<80;i++){try{await fetch(origin+'/queue-navigation.js');break;}catch{await wait(100);}}
 browser=await chromium.launch({headless:true});
 for(const viewport of [{width:1024,height:768},{width:768,height:1024}]){
  const context=await browser.newContext({viewport,hasTouch:true}),page=await context.newPage(),errors=[],writes=[];
  let hold=false,release,held,fail=false;
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.addInitScript(()=>{sessionStorage.setItem('h3-key','queue-test');window.EventSource=class{addEventListener(){}close(){}};});
  await page.route(origin+'/api/**',async route=>{
   const req=route.request(),url=new URL(req.url()),name=url.pathname;
   if(req.method()!=='GET')writes.push(name);
   if(['/api/h3/state','/api/h3/results-page','/api/h3/candidate-page'].includes(name))return route.continue();
   if(name.endsWith('/feedback-context'))return route.continue();
   if(name==='/api/h3/projects/DELETED/clips'||name==='/api/h3/projects/DELETED/clips/C0')return route.fulfill({status:404,json:{error:'project deleted'}});
   if(name==='/api/h3/projects/P/clips'&&hold){held();await new Promise(r=>release=r);}
   if(name==='/api/h3/projects/P/clips'&&fail)return route.abort('failed');
   if(/^\/api\/h3\/projects\/(P|PI)\/clips/.test(name)){
    const project=name.split('/')[4],clip={project_id:project,generation_mode:project==='PI'?'i2v':'r2v',scene_id:'S1',clip_id:'C0',video_prompt:'ARCHIVED PROJECT PROMPT',duration_seconds:5,references:[],errors:[],ready:true};
    return route.fulfill({json:name.endsWith('/C0')?clip:{project_id:project,generation_mode:clip.generation_mode,scenes:[{scene_id:'S1',clips:[clip]}]}});
   }
   if(name==='/api/h3/projects')return route.fulfill({json:{projects:[{project_id:'P',title:'Project P',generation_mode:'r2v'},{project_id:'PI',title:'Project I',generation_mode:'i2v'}]}});
   const match=name.match(/^\/api\/model-tests\/sessions\/(TEST-[RI])\/results$/);
   if(match)return route.fulfill({json:{session:{session_id:match[1],input_mode:match[1]==='TEST-R'?'h3_r2v_multi_reference':'i2v'},runs:[{run_id:'run-'+match[1],job_id:match[1]==='TEST-R'?'test-r2v':'test-i2v',status:'queued',ordering:1,title:'Test run',contract:{required_events:[],forbidden_failures:[]}}]}});
   let data={};
   if(name==='/api/h3/config')data={adapters:[]};
   else if(name==='/api/h3/action-assets')data={assets:[],presets:{}};
   else if(name==='/api/model-tests')data={models:[],workflows:[],adapters:[],case_assets:[],case_asset_requirements:[],available_workflows:[],suites:[],sessions:[]};
   else if(name==='/api/model-tests/comparison')data={groups:[],score_dimensions:{}};
   return route.fulfill({json:data});
  });
  const go=async name=>{await page.evaluate(name=>goPage(name),name);};
  const open=async id=>{
   const details=page.locator('#queueWork details[data-job-id="'+id+'"]');
   if(!await details.evaluate(el=>el.open))await details.locator(':scope>summary').tap();
   const button=details.locator('[data-queue-open-job]');
   assert((await button.boundingBox()).height>=44);
   await button.tap();
  };
  await page.goto(origin+'/#queue');await page.waitForSelector('#queueWork details[data-job-id="highres"]');
  await page.evaluate(()=>{document.querySelector('#h3CreateForm').elements.prompt.value='MY R2V DRAFT';document.querySelector('#i2vCreateForm').elements.prompt.value='MY I2V DRAFT';});
  // Current local worker has a direct link, without opening the collapsible queue detail.
  await page.evaluate(()=>document.querySelector('#h3ResultRerenderCountFilter').value='0');
  await page.locator('#activeBatch [data-queue-open-job="highres"]').tap();
  await page.waitForFunction(()=>currentPage==='results'&&h3ResultsPage===2);
  assert.equal(await page.locator('#h3ResultRerenderCountFilter').inputValue(),'');
  const card=page.locator('[data-h3-selected-job="original-00"]');
  assert(await card.isVisible());assert((await card.getAttribute('class')).includes('queue-navigation-target'));
  assert((await card.locator('.queue-navigation-context').textContent()).includes('1280 × 704'));
  assert(await card.locator('.h3-rerender-history-row.queue-navigation-target').count());
  assert.equal(await page.locator('#h3ResultProjectFilter').inputValue(),'P');assert.equal(await page.locator('#h3ResultSceneFilter').inputValue(),'S1');
  await page.evaluate(()=>refreshH3State());assert(await card.locator('.queue-navigation-context').count());
  await page.screenshot({path:'/tmp/queue-result-navigation-'+viewport.width+'.png'});
  await go('queue');await open('regular');await page.waitForFunction(()=>currentPage==='create'&&document.querySelector('#h3Clip').value==='C0');
  assert.equal(await page.locator('#h3Project').inputValue(),'P');assert.equal(await page.locator('#h3Scene').inputValue(),'S1');
  assert.equal(await page.locator('#h3CreateForm [name=prompt]').inputValue(),'MY R2V DRAFT');
  await go('queue');await open('i2v');await page.waitForFunction(()=>currentPage==='i2v-create'&&document.querySelector('#i2vClip').value==='C0');
  assert.equal(await page.locator('#i2vProject').inputValue(),'PI');assert.equal(await page.locator('#i2vCreateForm [name=prompt]').inputValue(),'MY I2V DRAFT');
  await go('queue');await open('gone');await page.waitForFunction(()=>document.querySelector('#queueJobRecord')?.open);
  assert.equal(await page.evaluate(()=>currentPage),'queue');await page.locator('#queueJobRecord button').tap();
  await open('direct');await page.waitForFunction(()=>document.querySelector('#queueJobRecord')?.open);
  assert((await page.locator('#queueJobRecord pre').textContent()).includes('<script>unsafe</script>'));
  assert.equal(await page.locator('#queueJobRecord script').count(),0);await page.locator('#queueJobRecord button').tap();
  await open('orphan-rerender');await page.waitForFunction(()=>document.querySelector('#queueJobRecord')?.open);
  assert((await page.locator('#queueJobRecord p').textContent()).includes('선택 해제'));await page.locator('#queueJobRecord button').tap();
  for(const [id,dest]of [['test-r2v','r2v-tests'],['test-i2v','model-tests']]){
   await go('queue');await open(id);await page.waitForFunction(dest=>currentPage===dest,dest);
   await page.waitForSelector('[data-model-test-run][open]');
  }
  await go('queue');
  // Late project responses may not hijack a page the user explicitly moved to.
  hold=true;const blocked=new Promise(r=>held=r);await open('regular');await blocked;await go('results');release();hold=false;
  await wait(300);assert.equal(await page.evaluate(()=>currentPage),'results');
  await go('queue');fail=true;await open('regular');await page.waitForFunction(()=>document.querySelector('#queueJobRecord')?.open);
  assert.equal(await page.evaluate(()=>currentPage),'queue');await page.locator('#queueJobRecord button').tap();fail=false;
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);console.log('PASS queue navigation',viewport);await context.close();
 }
}catch(e){console.error(logs);throw e;}finally{if(browser)await browser.close();server.kill();fs.rmSync(fixture,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1;});
