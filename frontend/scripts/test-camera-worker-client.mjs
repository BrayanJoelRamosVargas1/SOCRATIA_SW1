import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const code=ts.transpileModule(readFileSync(new URL('../src/features/simulations/camera-worker-client.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
let instance,resolveCapture,closed=0;
const registry={};
const timers=new Map();let timer=0;
class Worker {
 constructor(){Object.assign(registry,{instance:this});this.messages=[];}
 postMessage(message,transfer){this.messages.push({message,transfer});}
 terminate(){this.terminated=true;}
}
const exports={};vm.runInNewContext(code,{exports,Worker,Error,Promise,
 createImageBitmap:()=>new Promise(resolve=>{resolveCapture=()=>resolve({close(){closed++;}});}),
 setTimeout(fn){timers.set(++timer,fn);return timer;},clearTimeout(id){timers.delete(id);}});
const detector=exports.createCameraWorker();
instance=registry.instance;
instance.onmessage({data:{type:'ready',face:true,pose:true}});await detector.ready;
const pending=detector.detect({},1);
await assert.rejects(detector.detect({},2),/no disponible/);
resolveCapture();await new Promise(resolve=>setImmediate(resolve));
const message=instance.messages.at(-1);
assert.equal(message.message.type,'frame');assert.equal(message.transfer[0],message.message.bitmap);
instance.onmessage({data:{type:'result',id:message.message.id,pose:null,face:null,elapsed:20}});
assert.equal((await pending).elapsed,20);assert.equal(timers.size,0);
const cancelled=detector.detect({},3);detector.close();resolveCapture();
await assert.rejects(cancelled,/detenido/);assert.equal(closed,1);assert.equal(instance.terminated,true);
console.log('PASS: one frame in flight, transferred bitmap, timers cleaned, capture released on teardown.');
