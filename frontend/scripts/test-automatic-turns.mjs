import assert from 'node:assert/strict';
import {chromium} from 'playwright';
const browser=await chromium.launch({channel:'msedge',headless:true,args:['--autoplay-policy=no-user-gesture-required']});
try{
 const page=await browser.newPage();
 await page.addInitScript(()=>{
  window.spoken=[];window.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
  Object.defineProperty(window,'speechSynthesis',{value:{getVoices:()=>[],cancel:()=>{},speak:u=>{window.spoken.push(u.text);u.onstart?.();setTimeout(()=>u.onend?.(),100);}}});
  navigator.mediaDevices.getUserMedia=async()=>{const context=new AudioContext();await context.resume();const oscillator=context.createOscillator(),gain=context.createGain(),destination=context.createMediaStreamDestination();oscillator.frequency.value=240;gain.gain.value=.12;oscillator.connect(gain);gain.connect(destination);oscillator.start();window.testMicrophone={gain,context};return destination.stream;};
 });
 const snapshot={simulation_id:'auto-turn-fixture',status:'ACTIVE',turn_state:'WAITING_STUDENT',current_question:{id:'q1',position:1,text:'Pregunta inicial.',source:'BANK'},answered_questions:0,total_questions:12,last_sequence:1,questions_exhausted:false,started_at:new Date().toISOString(),finished_at:null,transcript:[]};
 await page.route('**/api/v1/simulations/auto-turn-fixture/session',r=>r.fulfill({json:snapshot}));
 await page.route('**/api/v1/simulations/auto-turn-fixture',r=>r.fulfill({json:{microphone_ready:true,camera_ready:false,document:{name:'Prueba oral'},jury_profile:{name:'Tribunal',strictness:3,focus_type:'TECHNICAL'}}}));
 const events=[];let binary=0;
 await page.routeWebSocket('**/ws/simulations/auto-turn-fixture',ws=>{
  ws.send(JSON.stringify({type:'session.snapshot',payload:snapshot}));
  ws.onMessage(message=>{
   if(typeof message!=='string'){binary++;return;}
   const data=JSON.parse(message);events.push(data.type);
   if(data.type==='voice.utterance.end'){
    snapshot.answered_questions++;snapshot.last_sequence++;snapshot.current_question={id:'q'+(snapshot.answered_questions+1),position:snapshot.answered_questions+1,text:'Pregunta siguiente.',source:'BANK'};
    ws.send(JSON.stringify({type:'voice.transcription',text:'Respuesta oral de prueba.'}));
    ws.send(JSON.stringify({type:'session.state',payload:snapshot}));
   }
  });
 });
 await page.goto('http://localhost:3000/simulations/auto-turn-fixture/live');
 await page.getByRole('button',{name:'Enviar respuesta',exact:true}).waitFor();
 assert.equal(events.filter(x=>x==='voice.utterance.start').length,1,'Microphone must open automatically after greeting');
 await page.waitForTimeout(2000);await page.evaluate(()=>window.testMicrophone.gain.gain.value=0);
 try{await page.waitForFunction(()=>window.spoken.length===2,null,{timeout:12000});}catch(error){console.log(JSON.stringify({events,binary,spoken:await page.evaluate(()=>window.spoken),body:await page.locator('body').innerText()}));throw error;}
 assert.equal(events.filter(x=>x==='voice.utterance.end').length,1);assert.ok(binary>0,'Actual MediaRecorder audio must be sent');
 await page.getByRole('button',{name:'Enviar respuesta',exact:true}).waitFor();
 assert.equal(events.filter(x=>x==='voice.utterance.start').length,2,'Next jury turn must reopen the microphone');
 await page.getByRole('checkbox',{name:'Conversación automática'}).uncheck();
 await page.getByRole('button',{name:'Enviar respuesta',exact:true}).click();
 await page.waitForFunction(()=>window.spoken.length===3);
 await page.waitForTimeout(1500);
 assert.equal(events.filter(x=>x==='voice.utterance.start').length,2,'Manual mode must stop automatic reopening');
 console.log('PASS: greeting → automatic microphone → actual audio → silence submission → next question → microphone reopened; manual mode respected.');
}finally{await browser.close();}
