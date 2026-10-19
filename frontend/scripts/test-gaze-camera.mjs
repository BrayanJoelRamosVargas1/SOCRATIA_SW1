import fs from "node:fs/promises";
import path from "node:path";
import {chromium} from "playwright";

// Real models + real appearance endpoint + real UI. Only generated/rendered
// video is supplied; session reads/WS are intercepted to prevent mutations.

const output=path.join(process.env.TEMP??".","socratia-camera-provider-validation");await fs.mkdir(output,{recursive:true});
const fixtures=path.join(process.env.TEMP??".","socratia-gaze-validation");
const browser=await chromium.launch({channel:"msedge",headless:true});
try{
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  await context.addInitScript(()=>{
    navigator.mediaDevices.getUserMedia=async options=>{
      if(!options.video)throw new DOMException("Micrófono excluido de la prueba visual.","NotAllowedError");
      let image=new Image(),columns=3,present=true;image.src="/images/jury/academic-panel.png";await image.decode();
      const canvas=document.createElement("canvas");canvas.width=640;canvas.height=480;const ctx=canvas.getContext("2d");
      const draw=()=>{ctx.fillStyle="#ddd";ctx.fillRect(0,0,640,480);if(present){const sourceWidth=image.width/columns;const scale=Math.min(640/sourceWidth,480/image.height);const width=sourceWidth*scale,height=image.height*scale;ctx.drawImage(image,0,0,sourceWidth,image.height,(640-width)/2,(480-height)/2,width,height);}requestAnimationFrame(draw);};draw();
      window.cameraFixture={setPresent:value=>present=value,setSource:async source=>{const next=new Image();next.src=source;await next.decode();image=next;columns=1;}};
      return canvas.captureStream(15);
    };
  });
  const page=await context.newPage();
  const meta={id:"gaze-camera-fixture",status:"ACTIVE",camera_ready:true,microphone_ready:false,document:{name:"Prueba de mirada"},jury_profile:{name:"Tribunal",strictness:3,focus_type:"TECHNICAL"}};const id=meta.id,started=new Date().toISOString();
  const snapshot={simulation_id:id,status:"ACTIVE",turn_state:"WAITING_STUDENT",current_question:{id:"fixture-question",position:1,text:"Validación del seguimiento visual",source:"BANK"},answered_questions:0,total_questions:12,last_sequence:1,questions_exhausted:false,started_at:started,finished_at:null,transcript:[]};
  await page.route(`**/api/v1/simulations/${id}/session`,route=>route.fulfill({json:snapshot}));
  await page.route(`**/api/v1/simulations/${id}`,route=>route.fulfill({json:meta}));
  await page.routeWebSocket(`**/ws/simulations/${id}`,ws=>{ws.send(JSON.stringify({type:"session.snapshot",payload:snapshot}));ws.onMessage(()=>{});});
  const results=[];
  page.on("response",async response=>{if(response.url().endsWith("/appearance")){const body=await response.json();const torso=response.request().postDataJSON().torso_in_frame;results.push({status:response.status(),torso,...body});console.log("Appearance",JSON.stringify(results.at(-1)));}});
  await page.route(`**/api/v1/simulations/${id}/appearance`,r=>r.fulfill({json:{person_present:true,upper_body_visible:true,jacket:true,collared_shirt:true,tie:false,upper_body_covered:true,presentation:"formal",confidence:.99,feedback:"Prueba"}}));
  await page.goto(`http://localhost:3000/simulations/${id}/live`,{waitUntil:"networkidle",timeout:90000});
  await page.locator(".room-diagnostics > summary").click();
  await page.locator(".room-appearance-details > summary").click();
  await page.getByRole("checkbox",{name:"Avisos de voz al detectar un problema"}).uncheck();
  await page.getByText("Presentación formal observada",{exact:true}).waitFor({timeout:40000});
  await page.getByRole("checkbox",{name:"Revisión automática de ropa (Gemini)"}).uncheck();
  const source=async name=>"data:image/png;base64,"+(await fs.readFile(path.join(fixtures,name+".png"))).toString("base64");
  for(const [name,label] of [["front","Mirada centrada"],["eyes_left","Mirada apartada"],["eyes_right","Mirada apartada"],["eyes_down","Mirada apartada"],["front","Mirada centrada"]]){
    await page.evaluate(data=>window.cameraFixture.setSource(data),await source(name));
    await page.getByText(label,{exact:true}).waitFor({timeout:10000}).catch(async error=>{console.log(name,await page.locator("body").innerText());throw error;});
  }
  console.log("PASS: actual UI camera detects centered → left → right → down → centered using preserved video aspect ratio.");
}finally{await browser.close();}
