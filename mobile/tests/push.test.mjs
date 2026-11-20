import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import {safeNotificationDocument} from '../src/policy.mjs';

const compiled=ts.transpileModule(fs.readFileSync(new URL('../src/push.ts',import.meta.url),'utf8'),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},
}).outputText;
function harness({permission='granted',registered=false,preference,unregisterFails=false}={}){
  const listeners=new Map(),storage=new Map(),calls=[],channels=[];
  if(preference!==undefined)storage.set('socratia.notifications.enabled',preference);
  let registrations=0,prompts=0;
  const push={
    createChannel:async channel=>channels.push(channel),
    addListener:async(name,callback)=>{listeners.set(name,callback);return {remove:async()=>listeners.delete(name)};},
    register:async()=>{registrations++;listeners.get('registration')?.({value:'fixture-device-token'});},
    unregister:async()=>{if(unregisterFails)throw new Error('Unavailable');},
    checkPermissions:async()=>({receive:permission}),
    requestPermissions:async()=>{prompts++;return {receive:permission};},
  };
  const api=async(path,method='GET',data)=>{
    calls.push({path,method,data});
    if(path==='/push/native/status')return {registered};
    return {enabled:true};
  };
  const exports={};
  vm.runInNewContext(compiled,{exports,require:name=>name.includes('push-notifications')?{PushNotifications:push}:name==='./api'?{api}:{safeNotificationDocument},
    localStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value)},setTimeout,clearTimeout});
  return {module:exports,calls,channels,listeners,storage,registrations:()=>registrations,prompts:()=>prompts};
}

test('foreground notifications have a channel and notification taps accept only own app paths',async()=>{
  const h=harness(),targets=[];
  await h.module.initializePush(id=>targets.push(id),()=>{});
  assert.equal(h.channels[0].importance,4);
  assert.equal(h.channels[0].visibility,0);
  const tap=h.listeners.get('pushNotificationActionPerformed');
  tap({notification:{data:{url:'https://foreign.example'}}});
  tap({notification:{data:{url:'/documents'}}});
  tap({notification:{data:{url:'/documents/doc-123'}}});
  assert.deepEqual(targets,[null,'doc-123']);
});

test('status checks do not subscribe a new device or store its token',async()=>{
  const h=harness();
  assert.equal((await h.module.getPushState()).enabled,false);
  assert.equal(h.calls.filter(call=>call.path==='/push/native'&&call.method==='POST').length,0);
  assert.equal([...h.storage.values()].includes('fixture-device-token'),false);
});

test('existing registration is recognized and restored without another permission prompt',async()=>{
  const h=harness({registered:true});
  assert.equal((await h.module.getPushState()).enabled,true);
  await h.module.restorePush();
  assert.equal(h.prompts(),0);
  assert.equal(h.calls.filter(call=>call.path==='/push/native'&&call.method==='POST').length,1);
});

test('explicitly disabled notifications are never restored',async()=>{
  const h=harness({preference:'false',registered:true});
  await h.module.restorePush();
  assert.equal((await h.module.getPushState()).enabled,false);
  assert.equal(h.registrations(),0);
});

test('restoring does not prompt after permission has been revoked',async()=>{
  const h=harness({preference:'true',permission:'prompt'});
  await assert.rejects(h.module.restorePush());
  assert.equal(h.prompts(),0);
  assert.equal(h.registrations(),0);
});

test('a native unregister error cannot silently re-enable a server-removed device',async()=>{
  const h=harness({preference:'true',unregisterFails:true});
  await assert.rejects(h.module.disablePush());
  assert.equal(h.calls[0].method,'DELETE');
  assert.equal(h.storage.get('socratia.notifications.enabled'),'false');
  h.calls.length=0;
  await h.module.restorePush();
  assert.equal(h.calls.length,0);
});
