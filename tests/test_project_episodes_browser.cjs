const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root = path.resolve(__dirname, '..');
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    for (const viewport of [{width:1024,height:768},{width:768,height:1024}]) {
      const context = await browser.newContext({viewport,hasTouch:true}), page = await context.newPage(), errors = [];
      const p7='Dragon_EP07B1_V1', p72='Dragon_EP07B2_V2', p9='Dragon_EP09A_V1', p12='Dragon_EP12_V1';
      let projects = [p7,p72,p9,'Template','Dragon_EP02_V1'].map(project_id=>({project_id,title:project_id,generation_mode:'r2v',scene_count:1,clip_count:1}));
      projects.push({project_id:'Dragon_EP99_I2V',title:'I2V',generation_mode:'i2v'});
      let hold=false, release=null, writes=0;
      const clip = project_id=>({project_id,scene_id:'S1',clip_id:'C1',ready:true,video_prompt:'test prompt',duration_seconds:5,references:[]});
      const job={job_id:'queued',request:{source_project_id:p7,source_scene_id:'S1',source_clip_id:'C1',generation_mode:'r2v',queue_lane:'local_generation',job_type:'h3_r2v_generate'},status:{status:'running'}};
      page.on('pageerror',e=>errors.push(e.message));
      await page.addInitScript(()=>{window.EventSource=class{addEventListener(){}close(){}};});
      await page.route('http://audit.local/**',async route=>{
        const req=route.request(), name=new URL(req.url()).pathname;
        if(!name.startsWith('/api/')){
          const file=path.join(root,'web/public',name==='/'?'index.html':name.slice(1));
          return route.fulfill({status:fs.existsSync(file)?200:404,contentType:name.endsWith('.js')?'application/javascript':name.endsWith('.css')?'text/css':'text/html',body:fs.existsSync(file)?fs.readFileSync(file):''});
        }
        if(req.method()!=='GET')writes++;
        let data={};
        if(name==='/api/h3/projects')data={projects};
        else if(name==='/api/h3/config')data={adapters:[{adapter_id:'r2v',generation_mode:'r2v',adapter_name:'R2V',supports_action_reference:false}]};
        else if(name==='/api/h3/state')data={jobs:[job],candidate_sets:[],test_queues:[],worker:{current_job_id:'queued'},workers:{local_generation:{current_job_id:'queued'}}};
        else if(name==='/api/h3/action-assets')data={assets:[],presets:{}};
        else if(/^\/api\/h3\/projects\/[^/]+\/clips(?:\/[^/]+)?$/.test(name)){
          const id=decodeURIComponent(name.split('/')[4]);
          if(hold&&id===p72)await new Promise(resolve=>{release=resolve;});
          data=name.endsWith('/clips')?{scenes:[{scene_id:'S1',clips:[clip(id)]}]}:clip(id);
        }
        return route.fulfill({json:data});
      });
      await page.goto('http://audit.local/#create');
      await page.waitForSelector('#h3Episode option[value="EP07"]',{state:'attached'});
      const values=()=>page.locator('#h3Project option').evaluateAll(options=>options.map(o=>o.value).filter(Boolean));
      assert.deepEqual(await page.locator('#h3Episode option').evaluateAll(options=>options.map(o=>o.value)),['','EP02','EP07','EP09','__other__']);
      assert.equal((await values()).length,5);
      await page.locator('#h3Episode').selectOption('EP07');
      assert.deepEqual(await values(),[p7,p72]);
      await page.locator('#h3Project').selectOption(p7);
      await page.waitForFunction(()=>!document.querySelector('#queueH3ProjectCandidates').disabled);
      await page.locator('#h3Scene').selectOption('S1');
      await page.locator('#h3Clip').selectOption('C1');
      await page.waitForFunction(()=>!document.querySelector('#loadH3ProjectClip').disabled);
      await page.locator('#h3CreateForm [name=prompt]').fill('MY DRAFT');
      await page.locator('#refreshH3Projects').click();
      await page.waitForFunction(id=>document.querySelector('#h3Project').value===id,p7);
      assert.equal(await page.locator('#h3Episode').inputValue(),'EP07');
      assert.equal(await page.locator('#h3Clip').inputValue(),'C1');
      await page.locator('#h3Episode').selectOption('EP09');
      assert.equal(await page.locator('#h3Project').inputValue(),'');
      assert(await page.locator('#h3Scene').isDisabled());assert(await page.locator('#h3Clip').isDisabled());
      assert(await page.locator('#createH3ProjectTestSet').isDisabled());
      assert(await page.locator('#queueH3ProjectCandidates').isDisabled());
      assert(await page.locator('#queueH3SceneCandidates').isDisabled());
      assert.equal(await page.locator('#h3CreateForm [name=prompt]').inputValue(),'MY DRAFT');
      projects.push({project_id:p12,title:p12,generation_mode:'r2v'});
      await page.locator('#refreshH3Projects').click();
      await page.waitForSelector('#h3Episode option[value="EP12"]',{state:'attached'});
      assert.equal(await page.locator('#h3Episode').inputValue(),'EP09');
      await page.locator('#h3Episode').selectOption('EP12');assert.deepEqual(await values(),[p12]);
      await page.locator('#h3Episode').selectOption('__other__');assert.deepEqual(await values(),['Template']);
      await page.locator('#h3Episode').selectOption('');assert.equal((await values()).length,6);
      // A delayed old project response must not resurrect its clips after changing episode.
      await page.locator('#h3Episode').selectOption('EP07');hold=true;
      await page.locator('#h3Project').selectOption(p72);
      await page.waitForFunction(()=>document.querySelector('#h3Project').value.endsWith('B2_V2'));
      while(!release)await new Promise(r=>setTimeout(r,10));
      await page.locator('#h3Episode').selectOption('EP09');hold=false;release();
      await page.waitForTimeout(150);
      assert.equal(await page.locator('#h3Project').inputValue(),'');assert(await page.locator('#h3Scene').isDisabled());
      // Queue navigation must reveal a project outside the currently filtered episode.
      await page.evaluate(()=>goPage('queue'));
      await page.locator('#activeBatch [data-queue-open-job="queued"]').click();
      await page.waitForFunction(()=>currentPage==='create'&&document.querySelector('#h3Clip').value==='C1');
      assert.equal(await page.locator('#h3Episode').inputValue(),'EP07');
      assert.equal(await page.locator('#h3Project').inputValue(),p7);
      assert.deepEqual(await values(),[p7,p72]);
      assert.equal(await page.locator('#h3CreateForm [name=prompt]').inputValue(),'MY DRAFT');
      const box=await page.locator('#h3Episode').boundingBox();assert(box.height>=44&&box.x>=0&&box.x+box.width<=viewport.width);
      await page.screenshot({path:`/tmp/project-episodes-${viewport.width}.png`});
      assert.equal(writes,0);assert.deepEqual(errors,[]);
      console.log('PASS project episodes',viewport);await context.close();
    }
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
