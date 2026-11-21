import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import {helpDestination} from '../src/policy.mjs';
const source=ts.transpileModule(fs.readFileSync(new URL('../src/help.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.events={};this.value='';this.checked=false;this.textContent='';}
 append(...items){this.children.push(...items);}replaceChildren(...items){this.children=items;this.textContent='';}
 setAttribute(){}addEventListener(name,handler){this.events[name]=handler;}
}
function all(node){return [node,...node.children.flatMap(all)];}
function setup(reply){const main=new Element('main'),calls=[],exports={};vm.runInNewContext(source,{exports,document:{createElement:tag=>new Element(tag),createTextNode:value=>Object.assign(new Element('text'),{textContent:value})},require:name=>name==='./api'?{SERVER:'https://socratia.example',api:async(...args)=>{calls.push(args);return reply;}}:{helpDestination}});exports.mountHelp(main,()=>{});return {main,calls};}
test('Android help sends its platform and renders provider text as text, with no arbitrary navigation',async()=>{
 const {main,calls}=setup({answer:'Consulta tus documentos.',explanation:'<img src=x onerror=alert(1)>',url:'https://foreign.example',engine:'groq',platform:'android'});
 const form=all(main).find(x=>x.tag==='form'),input=all(main).find(x=>x.tag==='textarea');input.value='Mis materiales';
 form.events.submit({preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(calls[0][0],'/help/ask');assert.equal(calls[0][2].platform,'android');assert.equal(calls[0][2].use_ai,false);
 assert.ok(all(main).some(x=>x.textContent==='<img src=x onerror=alert(1)>'));
 assert.equal(all(main).filter(x=>x.textContent==='Ir a ese apartado'||x.textContent==='Abrir en la web').length,0);
 assert.equal(all(main).find(x=>x.type==='submit').disabled,false);
});

test('an older web-only help API cannot silently give Android instructions',async()=>{
 const {main}=setup({answer:'Pulsa Generar banco de preguntas.',url:'/documents',engine:'guia_local'});
 all(main).find(x=>x.tag==='textarea').value='Ayuda';all(main).find(x=>x.tag==='form').events.submit({preventDefault(){}});
 await new Promise(resolve=>setImmediate(resolve));
 assert.ok(all(main).some(x=>x.textContent.includes('actualización del servidor')));
 assert.ok(!all(main).some(x=>x.textContent==='Pulsa Generar banco de preguntas.'));
});
