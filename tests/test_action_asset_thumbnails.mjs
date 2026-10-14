import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {mkdtemp,mkdir,stat,rename,rm,utimes} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {randomUUID} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
const exec=promisify(execFile);
const app=readFileSync(new URL('../web/public/app.js',import.meta.url),'utf8');
const elements=[];
function element(tag){return {tag,attrs:{},events:{},children:[],setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this[k]},append(...xs){this.children.push(...xs)},addEventListener(k,f){this.events[k]=f},showModal(){this.shown=true},play(){this.played=true;return Promise.resolve()},pause(){this.paused=true},load(){this.unloaded=true},remove(){this.removed=true},close(){this.events.close?.()}}}
const ui={esc:s=>String(s).replaceAll('"','&quot;').replaceAll('<','&lt;'),h3ActionState:{assets:[{action_asset_id:'id/1',title:'<test>'}]},note:()=>{},document:{querySelector:()=>elements.find(e=>e.tag==='dialog'&&!e.removed),createElement:tag=>{const e=element(tag);elements.push(e);return e},body:{append:()=>{}}}};
vm.createContext(ui);vm.runInContext(app.slice(app.indexOf('function h3ActionThumbnail('),app.indexOf('function renderH3ActionAssets()')),ui);
const html=ui.h3ActionThumbnail(ui.h3ActionState.assets[0]);assert(!html.includes('<video'));assert(html.includes('loading="lazy"'));assert(html.includes('id%2F1/thumbnail'));assert(!html.includes('/video"'));
assert.equal(elements.length,0);ui.playH3ActionAsset('id/1');const first=elements.find(e=>e.tag==='video');assert(first.played);assert(first.src.endsWith('id%2F1/video'));
ui.playH3ActionAsset('id/1');assert(first.paused&&first.unloaded);assert.equal(first.src,undefined);assert.equal(elements.filter(e=>e.tag==='dialog'&&!e.removed).length,1);
elements.find(e=>e.tag==='dialog'&&!e.removed).close();assert.equal(elements.filter(e=>e.tag==='dialog'&&!e.removed).length,0);
console.log('목록 영상 미생성·이미지 지연 로딩·단일 재생·닫기 해제 통과');
const root=await mkdtemp(join(tmpdir(),'action-thumb-test-'));
try{
 const video=join(root,'source.mp4');await exec('ffmpeg',['-v','error','-f','lavfi','-i','color=c=blue:s=640x360:r=24:d=1','-c:v','libx264','-threads','1',video]);
 let generations=0;
 const server=readFileSync(new URL('../web/server.mjs',import.meta.url),'utf8');
 const ctx={join,stat,mkdir,rename,rm,randomUUID,H3_THUMBNAIL_CACHE:join(root,'cache'),safeId:s=>s,exec:async(...args)=>{generations++;return exec(...args)},json:(_res,status,data)=>({status,...data}),stream:async path=>({path}),setTimeout};
 vm.createContext(ctx);vm.runInContext(server.slice(server.indexOf('let actionThumbnailActive'),server.indexOf('async function serveVideoThumbnail(jobId')),ctx);
 const out=await ctx.serveVideoThumbnailPath(video,'asset',{}, {},480);assert(out.path);const probe=await exec('ffprobe',['-v','error','-show_entries','stream=width','-of','json',out.path]);assert.equal(JSON.parse(probe.stdout).streams[0].width,480);
 await ctx.serveVideoThumbnailPath(video,'asset',{}, {},480);assert.equal(generations,1);
 await utimes(out.path,new Date(0),new Date(0));await ctx.serveVideoThumbnailPath(video,'asset',{}, {},480);assert.equal(generations,2);
 const missing=await ctx.serveVideoThumbnailPath(join(root,'missing'),'bad',{},{});assert.equal(missing.status,404);
 let active=0,peak=0;
 await Promise.allSettled(Array.from({length:8},(_,i)=>ctx.withActionThumbnailSlot(async()=>{active++;peak=Math.max(peak,active);await new Promise(r=>setTimeout(r,5));active--;if(i===2)throw Error('test')})));
 assert.equal(peak,2);assert.equal(active,0);await ctx.withActionThumbnailSlot(async()=>{});
 console.log('480px 실제 썸네일 생성·캐시 재사용/갱신·누락 처리·동시 2개 제한 통과');
}finally{await rm(root,{recursive:true,force:true})}
