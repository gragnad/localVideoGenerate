const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const pages=['create','i2v-create','queue','candidates','results','action-assets','model-management','model-tests','r2v-tests','music'];
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const viewport of [{width:1024,height:768},{width:768,height:1024}]){
   const context=await browser.newContext({viewport,hasTouch:true}),page=await context.newPage(),errors=[],writes=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>{window.EventSource=class{addEventListener(){}close(){}};});
   await page.route('http://audit.local/**',async route=>{
    const req=route.request(),name=new URL(req.url()).pathname;
    if(!name.startsWith('/api/')){
     const file=path.join(root,'web/public',name==='/'?'index.html':name.slice(1));
     return route.fulfill({status:fs.existsSync(file)?200:404,contentType:name.endsWith('.js')?'application/javascript':name.endsWith('.css')?'text/css':'text/html',body:fs.existsSync(file)?fs.readFileSync(file):''});
    }
    if(req.method()!=='GET')writes.push(name);
    let data={};
    if(name==='/api/h3/config')data={adapters:[]};
    else if(name==='/api/h3/state')data={jobs:[],candidate_sets:[],worker:{},workers:{},test_queues:[]};
    else if(name==='/api/h3/projects')data={projects:[]};
    else if(name==='/api/h3/action-assets')data={assets:[],presets:{}};
    else if(['/api/h3/candidate-page','/api/h3/results-page'].includes(name))data={jobs:[],candidate_sets:[],pagination:{page:1,total:0,total_pages:1},filters:{projects:[]}};
    else if(name==='/api/model-tests')data={models:[],workflows:[],adapters:[],case_assets:[],case_asset_requirements:[],available_workflows:[],suites:[],sessions:[]};
    else if(name==='/api/model-tests/comparison')data={groups:[],score_dimensions:{}};
    else if(name==='/api/feedback-notes')data={notes:[]};
    return route.fulfill({json:data});
   });
   await page.goto('http://audit.local/#create');
   assert.equal(await page.locator('main > section > .heading').count(),0);
   for(const name of pages){
    await page.evaluate(name=>goPage(name),name);
    const section=page.locator(`[data-view="${name}"]`);
    assert(await section.isVisible(),name);
    assert(await page.locator('main > header').isVisible(),name);
    assert(await page.locator('#sidebarToggle').isVisible(),name);
    assert(await page.locator('main > header #refresh').isVisible(),name);
    assert.equal(await page.locator('#title').textContent(),await page.evaluate(name=>pageTitles[name],name));
    assert(await section.locator('button,input,select,textarea').count()>0,name);
    const layout=await section.evaluate(el=>({top:el.getBoundingClientRect().top,header:document.querySelector('main > header').getBoundingClientRect().bottom}));
    assert(layout.top-layout.header<=50,JSON.stringify({name,layout}));
    if(['i2v-create','results'].includes(name)){await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:`/tmp/compact-${name}-${viewport.width}.png`});}
   }
   // Section descriptions, input guidance and warnings are not page introductions.
   assert((await page.locator('.h3-reference-head').allTextContents()).some(text=>text.includes('클립마다 정확히 한 장')));
   assert((await page.locator('body').textContent()).includes('FFLF 워크플로우에서만 사용'));
   for(const name of ['feedback','compare']){
    await page.evaluate(name=>goPage(name),name);
    assert(await page.locator(`[data-view="${name}"]`).isVisible());
    assert.equal(await page.locator('main > header').isVisible(),false);
   }
   assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);
   console.log('PASS compact pages: all 12 views, header/actions/guidance retained',viewport);
   await context.close();
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
