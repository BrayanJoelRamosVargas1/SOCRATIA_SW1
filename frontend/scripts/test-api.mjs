import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const source = fs.readFileSync(new URL('../src/lib/api.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022}}).outputText;
function harness(fetch) {
  const exports = {};
  vm.runInNewContext(compiled, {exports, require: () => ({API_URL: 'http://test/api'}), fetch, Headers, FormData, Promise, Error});
  return exports;
}
let refreshes = 0, valid = false;
const api = harness(async url => {
  if (url.endsWith('/auth/refresh')) {
    refreshes++;
    await new Promise(resolve => setTimeout(resolve, 20));
    valid = true;
    return new Response('{}');
  }
  return valid ? new Response('{"ok":true}') : new Response('{}', {status:401});
});
const results = await Promise.all([api.apiRequest('/documents'), api.apiRequest('/simulations'), api.apiRequest('/subscription')]);
assert.equal(refreshes, 1);
assert.ok(results.every(result => result.ok));
let attempts = 0;
const denied = harness(async () => { attempts++; return new Response('{"error":{"message":"Denied"}}', {status:403}); });
await assert.rejects(denied.apiRequest('/admin/users'), error => error.status === 403 && error.message === 'No tienes permiso para realizar esta acción.');
assert.equal(attempts, 1);
const empty = harness(async () => new Response(null, {status:204}));
assert.equal(await empty.apiRequest('/documents/1', {method:'DELETE'}), undefined);
let renewals = 0;
const failed = harness(async url => {
  if (url.endsWith('/auth/refresh')) { renewals++; await new Promise(resolve => setTimeout(resolve, 20)); }
  return new Response('{}', {status:401});
});
await Promise.allSettled([failed.apiRequest('/documents'), failed.apiRequest('/simulations')]);
assert.equal(renewals, 1);
await assert.rejects(failed.apiRequest('/documents'));
assert.equal(renewals, 2);
console.log('PASS: concurrent refresh, authorization errors, empty responses, refresh failure recovery');

for (const body of ['{"detail":"Not Found"}','{"detail":[{"msg":"Field required"}]}','null']) {
 const broken=harness(async()=>new Response(body,{status:404}));
 await assert.rejects(broken.apiRequest('/missing'),e=>e.message==='No se encontró el recurso solicitado.' && e.status===404);
}
const offline=harness(async()=>{throw new TypeError('Failed to fetch');});
await assert.rejects(offline.apiRequest('/documents'),e=>e.status===0 && e.code==='network_error' && !e.message.includes('fetch'));
const spanish=harness(async()=>new Response('{"error":{"message":"Ya existe un plan con este nombre"}}',{status:400}));
await assert.rejects(spanish.apiRequest('/plans'),e=>e.message==='Ya existe un plan con este nombre');
const abort=new Error('cancelled');abort.name='AbortError';
await assert.rejects(harness(async()=>{throw abort;}).apiRequest('/documents'),e=>e===abort);
console.log('PASS: Spanish server/network errors, malformed payloads and unchanged cancellation semantics');

let downloadRefreshes = 0, downloadValid = false;
const binary = harness(async (url, options) => {
  assert.equal(options.credentials, 'include');
  if (url.endsWith('/auth/refresh')) {
    downloadRefreshes++;
    await new Promise(resolve => setTimeout(resolve, 10));
    downloadValid = true;
    return new Response('{}');
  }
  assert.equal(options.cache, 'no-store');
  if (!downloadValid) return new Response('{}', {status:401});
  return new Response(new Uint8Array([0, 255, 37, 80, 68, 70]), {headers:{'Content-Type':'application/pdf'}});
});
const binaries = await Promise.all([binary.apiDownload('/documents/1/questions/export'), binary.apiDownload('/documents/1/presentation/export')]);
assert.equal(downloadRefreshes, 1);
for (const blob of binaries) assert.deepEqual([...new Uint8Array(await blob.arrayBuffer())], [0, 255, 37, 80, 68, 70]);
let rejectedRefreshes = 0;
const expiredDownload = harness(async url => {
  if (url.endsWith('/auth/refresh')) rejectedRefreshes++;
  return new Response('{}', {status:401});
});
await assert.rejects(expiredDownload.apiDownload('/documents/1/questions/export'), error => error.status === 401);
assert.equal(rejectedRefreshes, 1);
console.log('PASS: binary downloads preserve bytes, renew one shared session and stop on expired refresh');
