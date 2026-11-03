/* Deterministic decoder-delay regression: seeking itself can create the next drift. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
let now=0;
class Control {
 constructor(){this.value='';this.checked=false;this.disabled=false;this.textContent='';}
}
class Video {
 constructor(duration){this.duration=duration;this.readyState=4;this.hidden=false;this.paused=false;this.ended=false;this.error=null;this.seeking=false;this.time=0;this.rate=1;this.handlers={};this.seeks=[];this.rateWrites=0;this.blockedUntil=0;}
 addEventListener(name,fn){(this.handlers[name] ||= []).push(fn);}
 emit(name){for(const fn of this.handlers[name]||[])fn();}
 getAttribute(){return 'test.mp4';}
 get currentTime(){return this.time;}
 set currentTime(time){this.time=time;this.seeks.push([now,time]);this.blockedUntil=now+240;}
 get playbackRate(){return this.rate;}
 set playbackRate(rate){this.rateWrites++;this.rate=rate;}
 pause(){this.paused=true;}
 play(){this.paused=false;return Promise.resolve();}
 advance(ms){if(!this.paused&&now>=this.blockedUntil)this.time+=ms/1000*this.rate;}
}
global.window={};global.document={hidden:false};global.requestAnimationFrame=()=>1;global.cancelAnimationFrame=()=>{};
global.performance={now:()=>now};
vm.runInThisContext(fs.readFileSync(require('node:path').join(__dirname,'../web/public/dual-playback.js'),'utf8'),{filename:'dual-playback.js'});
function fixture(ratio=false){
 now=0;
 const controls=new Map(),root={closest:()=>({hidden:false}),querySelector(selector){if(!controls.has(selector))controls.set(selector,new Control());return controls.get(selector);}};
 const a=new Video(20),b=new Video(ratio?30:20),player=new window.H3DualPlayback(root,[a,b]);
 player.q('mode').value=ratio?'ratio':'seconds';player.q('from').value='0';player.q('to').value='';player.q('audio').value='0';player.q('link').checked=true;
 return {a,b,player};
}
for(const ratio of [false,true]){
 const {a,b,player}=fixture(ratio),scale=ratio?1.5:1;
 a.time=1;b.time=.75*scale;player.running=true;
 for(now=0;now<6000;now+=16){a.advance(16);b.advance(16);player.tick();}
 assert.equal(b.seeks.length,0,'Small drift must not trigger repeated decoder-flushing seeks');
 assert(Math.abs(a.currentTime-b.currentTime/scale)<.11,'Small drift converges smoothly');
 assert(b.rateWrites<50,'Do not rewrite playbackRate every animation frame');
 player.stop();assert.equal(b.playbackRate,1);
 console.log('PASS smooth sync',ratio?'ratio':'seconds',b.rateWrites);
}
{
 const {a,b,player}=fixture();a.time=3;player.running=true;
 for(now=0;now<4000;now+=16){a.advance(16);b.advance(16);player.tick();}
 assert(b.seeks.length>=1&&b.seeks.length<=2,'Sustained large drift has bounded hard recovery');
 assert(b.seeks[0][0]>=800,'Do not jump immediately on a transient scheduling delay');
 console.log('PASS bounded large drift',b.seeks.length);
}
{
 const {a,b,player}=fixture();player.seek(4);assert.equal(a.currentTime,4);assert.equal(b.currentTime,4);
 player.q('mode').value='ratio';b.duration=30;player.seek(2);assert.equal(a.currentTime,2);assert.equal(b.currentTime,3);
 now=100;a.time=2.1;a.seeking=true;a.emit('seeking');
 assert.equal(b.currentTime,3,'Queued programmatic seeking events must not echo back to the other player');
 b.time=1;b.seeking=true;b.emit('seeking');
 assert(Math.abs(a.currentTime-2/3)<.01,'A new manual scrub must propagate even while a previous seek is pending');
 console.log('PASS explicit scrub and seek echo suppression');
}
