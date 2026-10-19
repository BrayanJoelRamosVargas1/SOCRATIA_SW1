import assert from 'node:assert/strict';
import {chromium} from 'playwright';
const browser=await chromium.launch({channel:'msedge',headless:true});
try {
const page=await browser.newPage();
await page.addInitScript(()=>{window.spoken=[];window.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};Object.defineProperty(window,'speechSynthesis',{value:{getVoices:()=>[],cancel:()=>{},speak:u=>{window.spoken.push(u.text);u.onstart?.();setTimeout(()=>u.onend?.(),20);}}});});
const snap={simulation_id:'dialogue-fixture',status:'ACTIVE',turn_state:'WAITING_STUDENT',current_question:{id:'q1',position:1,text:'Primera pregunta.',source:'BANK'},answered_questions:0,total_questions:12,last_sequence:1,questions_exhausted:false,started_at:new Date().toISOString(),finished_at:null,transcript:[]};
await page.route('**/api/v1/simulations/dialogue-fixture/session',r=>r.fulfill({json:snap}));
await page.route('**/api/v1/simulations/dialogue-fixture',r=>r.fulfill({json:{camera_ready:false,document:{name:'Prueba'},jury_profile:{name:'Tribunal',strictness:3,focus_type:'TECHNICAL'}}}));
let ws;
await page.routeWebSocket('**/ws/simulations/dialogue-fixture',s=>{ws=s;s.send(JSON.stringify({type:'session.snapshot',payload:snap}));s.onMessage(()=>{});});
await page.goto('http://localhost:3000/simulations/dialogue-fixture/live');
await page.waitForFunction(()=>window.spoken.length===1);
assert.match(await page.evaluate(()=>window.spoken[0]),/Bienvenido.*Primera pregunta/s);
ws.send(JSON.stringify({type:'session.snapshot',payload:snap}));
snap.current_question={id:'q2',position:2,text:'Segunda pregunta.'};snap.answered_questions=1;
ws.send(JSON.stringify({type:'session.state',payload:snap}));
await page.waitForFunction(()=>window.spoken.length===2);
assert.equal(await page.evaluate(()=>window.spoken[1]),'Segunda pregunta.');
snap.current_question={id:'q3',position:3,text:'Tercera pregunta.'};
ws.send(JSON.stringify({type:'session.state',payload:snap}));ws.send(JSON.stringify({type:'tts.fallback',payload:{text:'Tercera pregunta.'}}));
await page.waitForFunction(()=>window.spoken.length===3);await page.waitForTimeout(800);
assert.equal(await page.evaluate(()=>window.spoken.length),3);
await page.getByRole('button',{name:'Repetir pregunta'}).click();await page.waitForFunction(()=>window.spoken.length===4);
console.log('PASS: automatic welcome, first and subsequent questions, deduplication, server voice priority and replay.');
}finally{await browser.close();}
