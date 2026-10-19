import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const events={}, media={}, timers=new Map();
let timerId=0, draws=0, pauses=0;
const pixels = new Uint8ClampedArray([10,180,10,255,180,120,100,255]);
const context2d={drawImage(){draws++;},getImageData(){return {data:pixels};},putImageData(){}};
const video={readyState:4,duration:8,currentTime:0,addEventListener(type,fn){media[type]=fn;},
  async play(){},pause(){pauses++;}};
const canvas={width:288,height:384,getContext:()=>context2d};
const document={hidden:false,querySelector:selector=>selector==='video'?video:canvas,
  addEventListener(type,fn){events[type]=fn;}};
const reduced={matches:false,addEventListener(type,fn){events.reduced=fn;}};
const parent={};
const runtime=vm.createContext({document,window:{addEventListener(type,fn){events[type]=fn;}},
  location:{origin:'https://socratia.example',search:'?index=0'},parent,URLSearchParams,
  matchMedia:()=>reduced,setTimeout(fn){timers.set(++timerId,fn);return timerId;},
  clearTimeout(id){timers.delete(id);}});
vm.runInContext(readFileSync(new URL('../public/vendor/dh-live/portrait.js',import.meta.url),'utf8'),runtime);
assert.equal(video.src,'assets/listening.mp4?v=20261018-3');
media.loadeddata(); await Promise.resolve();
assert.ok(draws>0,'human frame draws without loading the inference engine');
assert.equal(pixels[3],0,'green backdrop removed');
assert.equal(pixels[7],255,'skin remains visible');
assert.equal(timers.size,1,'only one bounded drawing timer');
events.message({origin:'https://other.example',source:parent,data:{type:'socratia.pause',paused:true}});
assert.equal(timers.size,1,'untrusted origins cannot control the portrait');
events.message({origin:runtime.location.origin,source:parent,data:{type:'socratia.pause',paused:true}});
assert.equal(timers.size,0,'pause stops rendering');
events.message({origin:runtime.location.origin,source:parent,data:{type:'socratia.pause',paused:false}});
await Promise.resolve();
document.hidden=true;events.visibilitychange();
assert.equal(timers.size,0,'hidden tabs do no canvas work');
assert.ok(pauses>0);
document.hidden=false;reduced.matches=true;events.reduced();
assert.equal(timers.size,0,'reduced motion draws a still frame');
console.log('PASS: human startup, chroma key, origin guard, pause, hidden tab and reduced motion.');
