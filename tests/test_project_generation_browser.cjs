const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root=path.resolve(__dirname,'..'),fixture=fs.mkdtempSync(path.join(os.tmpdir(),'project-generation-')),port=18660,origin='http://127.0.0.1:'+port;
const server=spawn(process.execPath,[path.join(root,'web/server.mjs')],{env:{...process.env,VIDEO_UI_HOST:'127.0.0.1',VIDEO_UI_PORT:String(port),VIDEO_UI_ACCESS_KEY:'generation-test',VIDEO_ENGINE_ROOT:fixture,VIDEO_ENGINE_PYTHON:path.join(root,'.venv/bin/python')},stdio:['ignore','pipe','pipe']});
let logs='';server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{let browser;try{
 for(let i=0;i<80;i++){try{await fetch(origin+'/app.js');break;}catch{await wait(100);}}
 assert.equal((await fetch(origin+'/api/h3/projects/candidate-sets',{method:'POST',headers:{'content-type':'application/json'},body:'{}'})).status,401);
 browser=await chromium.launch({headless:true});
 for(const viewport of [{width:1024,height:768},{width:768,height:1024}]){
  const context=await browser.newContext({viewport,hasTouch:true}),page=await context.newPage(),errors=[],posts=[],confirms=[];
  let accept=false,fail=false;
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>{confirms.push(d.message());accept?d.accept():d.dismiss();});
  await page.addInitScript(()=>{sessionStorage.setItem('h3-key','generation-test');window.EventSource=class{addEventListener(){}close(){}};});
  await page.route(origin+'/api/**',async route=>{
   const req=route.request(),name=new URL(req.url()).pathname;
   if(req.method()==='POST'){
    const payload=req.postDataJSON();posts.push({name,payload});
    return route.fulfill({status:fail?500:201,json:fail?{error:'test failure'}:{scene_count:2,clip_count:name.includes('/scenes/')?2:3,job_count:name.includes('/scenes/')?4:6,scene_id:payload.scene_id}});
   }
   let data={};
   if(name==='/api/h3/config')data={adapters:[{adapter_id:'r2v',generation_mode:'r2v',adapter_name:'R2V workflow',supports_action_reference:false}]};
   else if(name==='/api/h3/state')data={jobs:[],candidate_sets:[],test_queues:[],project_test_sets:[],workers:{},worker:{}};
   else if(name==='/api/h3/projects')data={projects:[{project_id:'P',title:'Project P',generation_mode:'r2v'},{project_id:'BAD',title:'Unready project',generation_mode:'r2v'}]};
   else if(/^\/api\/h3\/projects\/(P|BAD)\/clips$/.test(name)){
    const bad=name.includes('/BAD/'),clip=(id,scene,seq,ready=true)=>({clip_id:id,scene_id:scene,sequence:seq,ready,duration_seconds:5,references:[]});
    data={generation_mode:'r2v',scenes:[{scene_id:'S1',clips:[clip('C1','S1',1),clip('C3','S1',3)]},{scene_id:'S2',clips:[clip('C2','S2',2,!bad)]}]};
   }else if(name==='/api/h3/action-assets')data={assets:[],presets:{}};
   return route.fulfill({json:data});
  });
  await page.goto(origin+'/#create');await page.waitForFunction(()=>document.querySelector('#h3Project').options.length===3);
  const windows=page.locator('#queueH3ProjectCandidates'),local=page.locator('#queueH3ProjectCandidatesLocal');
  assert(await windows.isDisabled());assert(await local.isDisabled());
  await page.locator('#h3Project').selectOption('P');await page.waitForFunction(()=>!document.querySelector('#queueH3ProjectCandidates').disabled);
  assert.equal(await page.locator('#h3Scene').inputValue(),'');
  assert(await page.locator('#queueH3SceneCandidates').isDisabled());
  await page.locator('#h3SceneResolution').selectOption('832x480');await page.locator('#h3SceneCandidateCount').selectOption('2');
  assert((await page.locator('#h3ProjectCandidateMeta').textContent()).includes('6개 작업'));
  await page.locator('#h3CreateForm [name=prompt]').fill('KEEP MY MANUAL PROMPT');
  await windows.tap();assert.equal(posts.length,0);assert(confirms.at(-1).includes('3개 클립'));assert(confirms.at(-1).includes('6개 작업'));
  accept=true;await windows.tap();await page.waitForFunction(()=>!document.querySelector('#queueH3ProjectCandidates').disabled);
  assert.equal(posts.length,1);assert.equal(posts[0].name,'/api/h3/projects/candidate-sets');
  assert.deepEqual(posts[0].payload,{project_id:'P',adapter_id:'r2v',generation_mode:'r2v',candidate_count:2,width:832,height:480,seed:-1,queue_lane:'windows_candidate'});
  await local.tap();await page.waitForFunction(()=>!document.querySelector('#queueH3ProjectCandidatesLocal').disabled);
  assert.equal(posts[1].payload.queue_lane,'local_generation');
  assert.equal(await page.locator('#h3CreateForm [name=prompt]').inputValue(),'KEEP MY MANUAL PROMPT');
  await page.locator('#h3Scene').selectOption('S1');await page.locator('#queueH3SceneCandidates').tap();
  await page.waitForFunction(()=>!document.querySelector('#queueH3SceneCandidates').disabled);
  assert.equal(posts[2].name,'/api/h3/scenes/candidate-sets');assert.equal(posts[2].payload.scene_id,'S1');
  fail=true;await local.tap();await page.waitForFunction(()=>!document.querySelector('#queueH3ProjectCandidatesLocal').disabled);fail=false;
  assert((await page.locator('#h3ProjectCandidateMeta').textContent()).includes('6개 작업'));
  const bounds=await page.locator('#h3ProjectCandidateControls').evaluate(el=>({panel:el.getBoundingClientRect().toJSON(),buttons:[...el.querySelectorAll('button')].map(b=>b.getBoundingClientRect().toJSON())}));
  for(const b of bounds.buttons){assert(b.height>=44);assert(b.x>=bounds.panel.x&&b.right<=bounds.panel.right+1);}
  await page.screenshot({path:'/tmp/project-generation-'+viewport.width+'.png'});
  await page.locator('#h3Project').selectOption('BAD');await page.waitForFunction(()=>document.querySelector('#h3Scene').options.length===3&&document.querySelector('#queueH3ProjectCandidates').disabled);
  assert(await local.isDisabled());assert((await page.locator('#h3ProjectCandidateMeta').textContent()).includes('2/3'));
  assert.deepEqual(errors,[]);console.log('PASS project generation',viewport);await context.close();
 }
}catch(e){console.error(logs);throw e;}finally{if(browser)await browser.close();server.kill();fs.rmSync(fixture,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1;});
