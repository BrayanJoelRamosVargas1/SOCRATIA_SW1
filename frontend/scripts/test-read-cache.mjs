import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const code=ts.transpileModule(readFileSync(new URL('../src/lib/api.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
function harness(fetch,browser=true){
 let now=0;const events={},exports={};
 const context={exports,require:()=>({API_URL:'https://test/api'}),fetch,Headers,FormData,Response,Error,Promise,
 Date:class extends Date{static now(){return now;}}};
 if(browser)context.window={addEventListener(type,fn){events[type]=fn;},localStorage:{setItem(){}}};
 vm.runInNewContext(code,context);
 return {api:exports,events,advance(value){now+=value;}};
}
let reads=0;
const client=harness(async()=>{reads++;return new Response(JSON.stringify({version:reads}));});
const [first,second]=await Promise.all([client.api.apiRequest('/documents'),client.api.apiRequest('/documents')]);
assert.equal(reads,1);assert.equal(first.version,second.version);
await client.api.apiRequest('/documents');assert.equal(reads,1,'fresh browser read reuses its result');
client.advance(10001);await client.api.apiRequest('/documents');assert.equal(reads,2,'expiry queries the server');
await client.api.apiRequest('/documents/1',{method:'DELETE'});await client.api.apiRequest('/documents');assert.equal(reads,4,'writes invalidate private reads');
client.events.storage({key:'socratia.session.changed'});await client.api.apiRequest('/documents');assert.equal(reads,5,'account changes in other tabs clear memory');
await Promise.all([client.api.apiRequest('/simulations/1/session'),client.api.apiRequest('/simulations/1/session')]);assert.equal(reads,7,'live session state is never cached');
let serverReads=0;const server=harness(async()=>{serverReads++;return new Response('{}');},false);
await Promise.all([server.api.apiRequest('/profile'),server.api.apiRequest('/profile')]);assert.equal(serverReads,2,'SSR has no shared private cache');
let release,profileReads=0;
const race=harness(async url=>{
 if(url.endsWith('/profile')){profileReads++;if(profileReads===1)return new Promise(resolve=>{release=()=>resolve(new Response('{"user":"old"}'));});return new Response('{"user":"new"}');}
 return new Response('{}');
});
const old=race.api.apiRequest('/profile');await race.api.apiRequest('/auth/logout',{method:'POST'});release();await old;
assert.equal((await race.api.apiRequest('/profile')).user,'new','late old-session responses never repopulate cache');
console.log('PASS: coalesced reads, expiry, writes, cross-tab logout, no live/SSR cache and stale-response isolation.');
