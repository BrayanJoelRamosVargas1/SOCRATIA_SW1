import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const compiled = ts.transpileModule(fs.readFileSync(new URL('../src/lib/product-chat.ts', import.meta.url), 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022},
}).outputText;
const exports = {};
vm.runInNewContext(compiled, {exports});
const {chatHistory, engineLabel} = exports;
const messages = Array.from({length: 20}, (_, i) => ({role: i % 2 ? 'assistant' : 'user', content: `turn ${i}`}));
messages.push({role: 'assistant', content: 'Connection failed', failed: true});
const history = chatHistory(messages);
assert.equal(history.length, 8);
assert.equal(history[0].content, 'turn 12');
assert.ok(!history.some(turn => turn.content === 'Connection failed'));
assert.equal(chatHistory([{role: 'assistant', content: 'x'.repeat(1400)}])[0].content.length, 1200);
assert.equal(chatHistory([{role: 'assistant', content: 'Pasos', reply: {explanation: 'Contexto'}}])[0].content, 'Pasos\nContexto');
assert.match(engineLabel('guia_local_modelo_no_configurado'), /no está conectado/);
assert.match(engineLabel('guia_local_modelo_no_configurado'), /no se llamó a una IA externa/);
assert.match(engineLabel('groq'), /externa/);
assert.match(engineLabel('modelo_propio'), /propia/);
assert.match(engineLabel('guia_local'), /sin inferencia/);
console.log('PASS: bounded conversation history, failed-turn exclusion, supplemental context and honest engine labels');
