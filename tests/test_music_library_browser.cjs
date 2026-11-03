const assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const {spawn,execFileSync} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || '/home/nalstudio/local-ai/opencode-web/node_modules/playwright');
const root=path.resolve(__dirname,'..'),fixture=fs.mkdtempSync(path.join(os.tmpdir(),'music-library-'));
const python=path.join(root,'.venv/bin/python'),port=18656,origin=`http://127.0.0.1:${port}`,key='music-test';
const server=spawn(process.execPath,[path.join(root,'web/server.mjs')],{env:{...process.env,VIDEO_UI_HOST:'127.0.0.1',VIDEO_UI_PORT:String(port),VIDEO_UI_ACCESS_KEY:key,VIDEO_ENGINE_ROOT:fixture,VIDEO_ENGINE_PYTHON:python},stdio:['ignore','pipe','pipe']});
let logs='';server.stdout.on('data',v=>logs+=v);server.stderr.on('data',v=>logs+=v);
const wait=ms=>new Promise(r=>setTimeout(r,ms));
function populate(){execFileSync(python,['-c',`
import sys,wave
from pathlib import Path
import music_library
r=Path(sys.argv[1]);source=r/'test.wav'
with wave.open(str(source),'wb') as w:
 w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\\0\\0'*32000)
for i in range(1,27):
 music_library.register(r,source,dict(title=f'곡 {i:02d}',description='회상 음악 <img src=x onerror=alert(1)>',mood='잔잔함',genre='ambient',instruments='피아노',use_case='해안 회상 장면',tags=['회상','피아노'],instrumental=True,bpm=72,model='MiniMax Music 3',prompt='Global Metadata: ambient; no vocals',seed='18446744073709551615'))
`,fixture],{cwd:root});}
(async()=>{
 let browser;
 try{
  for(let i=0;i<80;i++){try{await fetch(origin+'/music-library.js');break;}catch{await wait(100);}}
  assert.equal((await fetch(origin+'/api/music-library')).status,401);
  assert.equal((await fetch(origin+'/api/music-library/music_'+'0'.repeat(32)+'/download')).status,401);
  assert.equal((await fetch(origin+'/api/music-library/music_'+'0'.repeat(32)+'/audio')).status,401);
  assert.equal((await fetch(origin+'/api/music-library',{method:'POST',headers:{'x-access-key':key}})).status,405);
  browser=await chromium.launch({headless:true});
  let populated=false;
  for(const viewport of [{width:1024,height:768},{width:768,height:1024}]){
   const context=await browser.newContext({viewport,hasTouch:true,acceptDownloads:true}),page=await context.newPage(),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>{sessionStorage.setItem('h3-key','music-test');window.EventSource=class{addEventListener(){}close(){}};});
   let failNext=false,failAudio=false,holdQuery=false,held,release,mutations=[];
   await page.route(origin+'/api/**',async route=>{
    const url=new URL(route.request().url()),name=url.pathname;
    if(route.request().method()!=='GET')mutations.push(name);
    if(name==='/api/music-library'&&failNext){failNext=false;return route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({error:'조회 실패 테스트'})});}
    if(name.endsWith('/audio')&&failAudio)return route.fulfill({status:500,contentType:'audio/wav',body:'broken audio'});
    if(name==='/api/music-library'&&holdQuery&&url.searchParams.get('q')==='기다림'){
     holdQuery=false;const response=await route.fetch();held();await new Promise(r=>release=r);return route.fulfill({response});
    }
    if(name.startsWith('/api/music-library'))return route.continue();
    return route.fulfill({contentType:'application/json',body:JSON.stringify(name==='/api/h3/config'?{adapters:[]}:name==='/api/h3/projects'?{projects:[]}:name==='/api/h3/action-assets'?{assets:[],presets:{}}:{})});
   });
   await page.goto(origin+'/#music');
   assert.equal(await page.locator('#title').textContent(),'음악 라이브러리');
   assert(await page.locator('[data-page=music]').isVisible());
   if(await page.locator('#sidebarToggle').getAttribute('aria-expanded')==='true') await page.locator('#sidebarToggle').tap();
   if(!populated){await page.waitForFunction(()=>document.querySelector('#musicList').textContent.includes('아직 등록된 음악'));populate();populated=true;await page.locator('#musicRefresh').tap();}
   await page.waitForFunction(()=>document.querySelectorAll('.music-card').length===24);
   assert((await page.locator('#musicPage').textContent()).includes('26곡'));
   assert.equal(await page.locator('#musicList img').count(),0);
   await page.locator('#musicSort').selectOption('name');
   await page.waitForFunction(()=>document.querySelector('.music-card h3').textContent==='곡 01');
   await page.locator('#musicNext').tap();await page.waitForFunction(()=>document.querySelectorAll('.music-card').length===2);
   assert((await page.locator('#musicPage').textContent()).startsWith('2 / 2'));
   await page.locator('#musicPrevious').tap();await page.waitForFunction(()=>document.querySelectorAll('.music-card').length===24);
   const first=page.locator('.music-card').first();await first.locator('summary').tap();
   assert((await first.textContent()).includes('18446744073709551615'));
   assert((await first.locator('pre').textContent()).includes('no vocals'));
   assert((await first.textContent()).includes('설정 BPM'));
   const previewHref=await first.locator('audio').getAttribute('src');
   const partial=await page.request.get(origin+previewHref,{headers:{Range:'bytes=0-15'}});
   assert.equal(partial.status(),206);assert.equal((await partial.body()).length,16);
   assert(partial.headers()['content-disposition'].startsWith('inline;'));
   const sourceBytes=fs.readFileSync(path.join(fixture,'test.wav'));
   const suffix=await page.request.get(origin+previewHref,{headers:{Range:'bytes=-16'}});
   assert.equal(suffix.status(),206);assert.deepEqual(await suffix.body(),sourceBytes.subarray(sourceBytes.length-16));
   assert.equal((await page.request.get(origin+previewHref,{headers:{Range:`bytes=${sourceBytes.length+10}-`}})).status(),416);
   await first.locator('[data-music-preview]').tap();
   await page.waitForFunction(()=>document.querySelector('.music-card audio').currentTime>.1&&!document.querySelector('.music-card audio').paused);
   await page.evaluate(()=>{window.musicPlayer=document.querySelector('.music-card audio');window.musicTime=musicPlayer.currentTime;});
   await page.locator('#musicRefresh').tap();await page.waitForFunction(()=>document.querySelector('#musicStatus').textContent.startsWith('음악 26곡'));
   assert(await page.evaluate(()=>musicPlayer===document.querySelector('.music-card audio')&&!musicPlayer.paused&&musicPlayer.currentTime>=musicTime));
   await first.locator('[data-music-preview]').tap();assert(await first.locator('audio').evaluate(a=>a.paused));
   await first.locator('audio').evaluate(a=>a.currentTime=2);
   await page.waitForFunction(()=>Math.abs(document.querySelector('.music-card audio').currentTime-2)<.1);
   await first.locator('[data-music-preview]').tap();
   await page.locator('.music-card').nth(1).locator('[data-music-preview]').tap();
   await page.waitForFunction(()=>document.querySelectorAll('.music-card audio')[0].paused&&!document.querySelectorAll('.music-card audio')[1].paused);
   await page.evaluate(()=>goPage('compare'));assert(await page.locator('.music-card audio').evaluateAll(a=>a.every(x=>x.paused)));
   await page.evaluate(()=>goPage('music'));await page.waitForFunction(()=>document.querySelectorAll('.music-card').length===24);
   assert(await page.locator('.music-card audio').evaluateAll(a=>a.every(x=>x.paused)));
   const third=page.locator('.music-card').nth(2);failAudio=true;await third.locator('[data-music-preview]').tap();
   await page.waitForFunction(()=>document.querySelectorAll('.music-preview-status')[2].textContent.length>0);
   assert(await third.locator('.music-download').isVisible());failAudio=false;await third.locator('[data-music-preview]').tap();
   await page.waitForFunction(()=>!document.querySelectorAll('.music-card audio')[2].paused&&document.querySelectorAll('.music-card audio')[2].currentTime>.1);
   await third.locator('[data-music-preview]').tap();
   const href=await first.locator('.music-download').getAttribute('href');
   const raw=await page.request.get(origin+href);assert.equal(raw.status(),200);assert.equal(raw.headers()['content-type'],'audio/wav');
   assert(raw.headers()['content-disposition'].includes("filename*=UTF-8''"));assert.deepEqual(await raw.body(),fs.readFileSync(path.join(fixture,'test.wav')));
   const pending=page.waitForEvent('download');await first.locator('.music-download').tap();const download=await pending;
   assert.equal(download.suggestedFilename(),'곡 01.wav');assert.deepEqual(fs.readFileSync(await download.path()),fs.readFileSync(path.join(fixture,'test.wav')));
   await page.locator('#musicSearch').fill('없는 음악');await page.locator('#musicSearchForm button[type=submit]').tap();
   await page.waitForFunction(()=>document.querySelector('#musicList').textContent.includes('검색 조건에 맞는'));
   const started=new Promise(r=>held=r);holdQuery=true;await page.locator('#musicSearch').fill('기다림');await page.locator('#musicSearchForm button[type=submit]').tap();await started;
   // The shared feedback layer blocks duplicate submits while that same button is busy;
   // a distinct refresh action still starts a newer read and must win over the held response.
   await page.locator('#musicSearch').fill('피아노');await page.locator('#musicRefresh').tap();
   await page.waitForFunction(()=>document.querySelectorAll('.music-card').length===24);release();await wait(100);
   assert.equal(await page.locator('.music-card').count(),24);
   failNext=true;await page.locator('#musicRefresh').tap();await page.waitForFunction(()=>document.querySelector('#musicStatus').dataset.error==='true');
   assert.equal(await page.locator('.music-card').count(),24);await page.locator('#musicRefresh').tap();
   await page.waitForFunction(()=>document.querySelector('#musicStatus').dataset.error==='false');
   const track=await first.getAttribute('id'),audio=path.join(fixture,'runtime/music_library/tracks',track,'audio.wav');
   fs.renameSync(audio,audio+'.held');await page.locator('#musicRefresh').tap();
   await page.waitForFunction(()=>document.querySelector('.music-missing'));
   assert.equal(await first.locator('.music-download').count(),0);assert((await first.textContent()).includes('회상 음악'));
   assert.equal((await page.request.get(origin+href)).status(),400);fs.renameSync(audio+'.held',audio);
   await page.locator('#musicRefresh').tap();await first.locator('.music-download').waitFor();
   await page.waitForFunction(()=>document.querySelector('#musicStatus').textContent.startsWith('음악 26곡'));
   assert.equal(await page.locator('[data-view=music] audio').count(),24);
   assert.equal(await page.locator('[data-view=music] video').count(),0);
   assert.deepEqual(mutations,[]);assert.deepEqual(errors,[]);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.evaluate(()=>scrollTo(0,0));
   await page.screenshot({path:`/tmp/h3-music-library-${viewport.width}.png`});
   console.log(`PASS ${viewport.width}×${viewport.height}: library/search/details/download, authenticated audio ranges/seek/play/pause/exclusive playback/refresh preservation/page exit/error retry, missing audio, no generation writes`);
   await context.close();
  }
 }catch(error){console.error(logs);throw error;}
 finally{if(browser)await browser.close();server.kill();fs.rmSync(fixture,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
