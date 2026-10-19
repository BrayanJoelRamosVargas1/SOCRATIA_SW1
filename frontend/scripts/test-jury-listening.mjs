import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const events = {}, mediaEvents = {}, callbacks = new Map();
let id = 0, draws = 0, plays = 0;
const reduced = {matches:false,addEventListener(_type,callback){events.reduced=callback;}};
const video = {readyState:4,currentTime:0,duration:4,dataset:{},
  addEventListener(type,callback){mediaEvents[type]=callback;},
  pause(){},async play(){plays++;}};
const document = {hidden:false,body:{dataset:{},append(){}},createElement:()=>video,
  addEventListener(type,callback){events[type]=callback;}};
const window = {addEventListener(type,callback){events[type]=callback;}};
const context = vm.createContext({document,window,parent:{postMessage(){}},location:{search:'?index=2',origin:'http://localhost'},
  URLSearchParams,matchMedia:()=>reduced,
  requestAnimationFrame(callback){callbacks.set(++id,callback);return id;},
  cancelAnimationFrame(key){callbacks.delete(key);},
  canvas_video:{width:576,height:768},ctx_video:{clearRect(){},drawImage(){draws++;}},
  processChromaKey:()=>video,
});
vm.runInContext(readFileSync(new URL('../public/vendor/dh-live/listening-motion.js',import.meta.url),'utf8'),context);
const motion=window.socratiaListeningMotion;
motion.load('daniel-fictional');
assert.equal(video.src,'daniel-fictional/listening.mp4?v=20261018-3');
motion.setActive(true);
assert.equal(plays,0,'wait for a decoded clip instead of blanking the neutral portrait');
mediaEvents.loadeddata();
await Promise.resolve();
assert.equal(video.currentTime,2.74,'independent starting phase');
assert.equal(motion.isAvailable(),true);
motion.seekTo(5.25);
assert.equal(motion.getTime(),1.25,'handoff preserves the phase within the loop');
assert.ok(draws>0);
assert.equal(video.muted,true,'listening never plays an audio track');
motion.setActive(false);
assert.equal(callbacks.size,0,'speaking cancels the idle renderer');
const before=draws;
motion.setActive(true);
await Promise.resolve();
document.hidden=true;events.visibilitychange();
assert.equal(callbacks.size,0,'hidden jurors stop rendering');
document.hidden=false;events.visibilitychange();await Promise.resolve();
reduced.matches=true;events.reduced();
assert.equal(callbacks.size,0,'respect reduced motion');
mediaEvents.error();
assert.equal(motion.isAvailable(),false);
assert.equal(document.body.dataset.facialMotion,'unavailable');
assert.ok(draws>=before);
console.log('PASS: silent listening clips, independent phase, speech handoff, visibility and reduced motion.');
