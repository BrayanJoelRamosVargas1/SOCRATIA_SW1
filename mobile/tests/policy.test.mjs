import { test } from 'node:test';
import assert from 'node:assert/strict';
import { apiPath, safeNotificationDocument } from '../src/policy.mjs';
test('companion allows reading materials but rejects simulations, uploads and arbitrary URLs', () => {
  assert.equal(apiPath('/documents/abc/questions/export'), '/api/v1/documents/abc/questions/export');
  assert.equal(apiPath('/simulations/abc/evaluation'), '/api/v1/simulations/abc/evaluation');
  for (const path of ['/simulations/abc/start','/simulations/new','/admin/users','https://example.org','/documents/../admin','/documents/abc/process']) assert.throws(() => apiPath(path));
  assert.throws(() => apiPath('/simulations', 'POST'));
  assert.throws(() => apiPath('/documents', 'POST'));
  assert.throws(() => apiPath('/documents/abc', 'DELETE'));
  assert.equal(apiPath('/auth/login', 'POST'), '/api/v1/auth/login');
  assert.equal(apiPath('/push/native', 'DELETE'), '/api/v1/push/native');
});
test('notification navigation never opens foreign links or executes input', () => {
  assert.equal(safeNotificationDocument('/documents/abc-123'), 'abc-123');
  for (const value of ['https://evil.example','/simulations/abc','/documents/../../admin',null]) assert.equal(safeNotificationDocument(value), null);
});
