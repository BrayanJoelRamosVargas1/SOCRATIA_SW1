import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Exercise the actual message adapter without a GPU or provider calls.
const listeners = {}, timers = new Map();
let id = 0, draws = 0, plays = 0, audioSets = 0;
let now = 0;
const parent = {postMessage() {}};
const video = {currentTime:.5,duration:5,readyState:4,addEventListener(_event, callback) { callback(); },play:async()=>{}};
const context = vm.createContext({
  location:{origin:'http://localhost',search:'?index=2'}, parent,
  window:{addEventListener(type, fn) {listeners[type] = fn;},socratiaFrameHandle:1},
  document:{body:{dataset:{}}},CONFIG:{},
  Module:{_malloc:()=>0,_free(){},HEAPU8:new Uint8Array(2000000),_setAudioBuffer(){audioSets++;}},
  videoProcessor:{video,pause(){},play(){plays++;}},
  canvas_video:{width:200,height:300},ctx_video:{clearRect(){},drawImage(){draws++;}},
  processChromaKey:()=>video,processVideoFrames(){},isPaused:false,
  setupBackgroundVideo(){},createQtAppInstance:async()=>{},newVideoTask:async()=>{},
  cancelAnimationFrame(){},setTimeout(fn, ms){timers.set(++id,{fn,ms});return id;},clearTimeout(key){timers.delete(key);},
  ArrayBuffer,Uint8Array,DataView,URLSearchParams,
  performance:{now:()=>now},
});
vm.runInContext(readFileSync(new URL('../public/vendor/dh-live/bridge.js',import.meta.url),'utf8'),context);
await new Promise(resolve=>setImmediate(resolve));
assert.equal(context.isPaused,true,'idle examples must not loop');
assert.equal(context.CONFIG.videoSrc,'daniel-fictional/01.mp4?v=20261018-3');
assert.equal(context.CONFIG.socratiaVariant,false);
const send = (data, origin='http://localhost', source=parent) => listeners.message({data,origin,source});
const wav = readFileSync(new URL('../public/vendor/dh-live/common/alex-es.wav',import.meta.url));
const buffer = wav.buffer.slice(wav.byteOffset,wav.byteOffset+wav.byteLength);
send({type:'socratia.audio',wav:buffer},'https://other.example');
assert.equal(audioSets,0,'foreign origins cannot animate the juror');
send({type:'socratia.audio',wav:buffer});
assert.equal(context.document.body.dataset.speaking,'true');
assert.equal(context.isPaused,false);
assert.equal(plays,1);
assert.ok([...timers.values()][0].ms > 1000,'read WAV chunks including SAPI extended fmt');
send({type:'socratia.stop'});
assert.equal(context.document.body.dataset.speaking,'false');
assert.equal(context.isPaused,true);
assert.equal(timers.size,0,'interrupted speech must not leave an ending timer');
send({type:'socratia.pause',paused:false});
assert.equal(context.isPaused,true,'resume must not animate an inactive juror');
assert.ok(draws >= 2,'return to the neutral frame at each stop');
let idleTime=2.74, active=true;
context.window.socratiaListeningMotion={isAvailable:()=>true,getTime:()=>idleTime,
  seekTo(time){idleTime=time;},setActive(value){active=value;}};
send({type:'socratia.audio',wav:buffer});
assert.equal(video.currentTime,2.74,'speech inherits the listening head position');
assert.equal(active,false,'only the speech renderer draws while speaking');
const durationMs = [...timers.values()][0].ms;
now = 500;
send({type:'socratia.pause',paused:true});
assert.equal(timers.size,0,'a paused voice must not finish in the background');
now = 4500;
send({type:'socratia.pause',paused:false});
assert.equal([...timers.values()][0].ms,durationMs-500,'resume retains the remaining speech time');
video.currentTime=3.6;
send({type:'socratia.audio',wav:buffer});
assert.equal(video.currentTime,3.6,'additional audio does not rewind the head');
send({type:'socratia.stop'});
assert.equal(idleTime,3.6,'listening continues from the final speech pose');
assert.equal(active,true);
send({type:'socratia.pause',paused:true});
assert.equal(active,false);
console.log('PASS: idle, origin guard, WAV duration, exclusive stop and neutral reset.');
