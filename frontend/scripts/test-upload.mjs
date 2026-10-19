import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const code=ts.transpileModule(readFileSync(new URL('../src/lib/api.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
function harness(statuses){
 let sends=0,refreshes=0;const progress=[];
 class XHR {
  upload={};open(method,url){this.method=method;this.url=url;}
  send(){const status=statuses[Math.min(sends++,statuses.length-1)];queueMicrotask(()=>{
   this.upload.onprogress?.({lengthComputable:true,loaded:50,total:100});
   if(status===0){this.onerror();return;}
   this.status=status;this.responseText=status===201?'\u007b"id":"uploaded"\u007d':'\u007b"detail":"denied"\u007d';
   void this.onload();
  });}
 }
 const exports={};vm.runInNewContext(code,{exports,require:()=>({API_URL:'https://test/api'}),XMLHttpRequest:XHR,Headers,FormData,Response,Promise,Error,
 fetch:async()=>{refreshes++;return new Response('{}');}});
 return {api:exports,progress,counts:()=>({sends,refreshes})};
}
const normal=harness([201]);
assert.equal((await normal.api.apiUpload('/documents',new FormData(),value=>normal.progress.push(value))).id,'uploaded');
assert.deepEqual(normal.progress,[50]);assert.deepEqual(normal.counts(),{sends:1,refreshes:0});
const expired=harness([401,201]);
assert.equal((await expired.api.apiUpload('/documents',new FormData())).id,'uploaded');
assert.deepEqual(expired.counts(),{sends:2,refreshes:1});
const broken=harness([0]);await assert.rejects(broken.api.apiUpload('/documents',new FormData()),error=>error.status===0);
assert.deepEqual(broken.counts(),{sends:1,refreshes:0});
console.log('PASS: measured upload progress, single auth refresh and no blind network retry.');
