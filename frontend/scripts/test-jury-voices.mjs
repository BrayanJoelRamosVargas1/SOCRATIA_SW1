import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
function load(name){const exports={};const code=ts.transpileModule(readFileSync(new URL('../src/features/simulations/'+name,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;vm.runInNewContext(code,{exports,setTimeout,clearTimeout,Promise});return exports;}
const {juryVoice}=load('jury-voices.ts');
const voices=['Microsoft Pablo','Microsoft Helena','Microsoft Jorge'].map(name=>({name,lang:'es-ES',voiceURI:name}));
assert.equal(new Set([0,1,2].map(i=>juryVoice(voices,i).voice.name)).size,3);
assert.equal(juryVoice(voices,1).voice.name,'Microsoft Helena');
assert.equal(juryVoice(voices,0).voice.name,'Microsoft Pablo');
assert.equal(juryVoice(voices,2).voice.name,'Microsoft Jorge');
assert.equal(juryVoice([{name:'English',lang:'en-US'}],0).voice,undefined);
assert.equal(juryVoice([voices[0]],2).distinctVoice,false);
const {waitForJuryRenderer,setJuryRendererReady}=load('jury-renderer-ready.ts');
const wait=waitForJuryRenderer(0,100);setJuryRendererReady(1,true);
setJuryRendererReady(0,true);assert.equal(await wait,true);
setJuryRendererReady(0,false);assert.equal(await waitForJuryRenderer(0,1),false);
assert.equal(await waitForJuryRenderer(1,1),true);
console.log('PASS: distinct Spanish voices, truthful fallback, renderer-specific handshake and bounded wait.');
