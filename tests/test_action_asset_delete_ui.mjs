import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const source=readFileSync(new URL('../web/public/app.js',import.meta.url),'utf8');
const fn=source.slice(source.indexOf('async function deleteH3ActionAsset('),source.indexOf('async function refreshH3ActionAssets(){'));
for(const mode of ['cancel','success','error']){
 const calls=[];const button={disabled:false};
 const ctx={h3ActionState:{assets:[{action_asset_id:'a/b',title:'테스트'}]},confirm:()=>mode!=='cancel',api:async(path,options)=>{calls.push([path,options.method]);assert.equal(button.disabled,true);if(mode==='error')throw Error('실패')},refreshH3ActionAssets:async()=>calls.push('refresh'),note:(...args)=>calls.push(args)};
 vm.createContext(ctx);vm.runInContext(fn,ctx);
 await ctx.deleteH3ActionAsset({dataset:{actionAssetId:'a/b'}},button);
 assert.equal(button.disabled,false);
 if(mode==='cancel')assert.equal(calls.length,0);
 else {assert.equal(calls[0][0],'/api/h3/action-assets/a%2Fb');assert.equal(calls[0][1],'DELETE');assert.equal(calls.includes('refresh'),mode==='success');}
}
console.log('삭제 UI: 취소·성공·실패 처리 통과');
