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
await assert.rejects(denied.apiRequest('/admin/users'), error => error.status === 403 && error.message === 'Denied');
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
