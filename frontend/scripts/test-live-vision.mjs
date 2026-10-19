import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

// Exercise the actual local MediaPipe models and 3D renderer without changing
// an account, session, transcript, or evaluation in the database.
const origin = process.env.SOCRATIA_TEST_ORIGIN ?? "http://localhost:3000";
const output = process.env.SOCRATIA_TEST_OUTPUT ?? path.join(process.env.TEMP ?? ".", "socratia-vision-validation");
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "msedge", headless: true, args: ["--autoplay-policy=no-user-gesture-required"] });
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await context.addInitScript(() => {
    const originalPlay=HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play=function(...args){if(this.tagName==="AUDIO")this.addEventListener("playing",()=>window.juryAudioStartedAt=performance.now(),{once:true});return originalPlay.apply(this,args);};
    const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async options => {
      if (!options.video) return original(options);
      const image = new Image(); image.src = "/images/jury/academic-panel.png"; await image.decode();
      const canvas = document.createElement("canvas"); canvas.width = 640; canvas.height = 480;
      const ctx = canvas.getContext("2d"); let present = true, enabled = true, mode="normal";
      function draw() {
        if (!enabled) return;
        if(mode==="frozen"){requestAnimationFrame(draw);return;}
        ctx.fillStyle = mode==="dark" ? "#080808" : mode==="bright" ? "#fff" : "#ddd"; ctx.fillRect(0, 0, 640, 480);
        if (present && !["dark","bright"].includes(mode)) {if(mode==="multiple"){ctx.drawImage(image,0,0,image.width/3,image.height,0,0,320,480);ctx.drawImage(image,image.width/3,0,image.width/3,image.height,320,0,320,480);}else ctx.drawImage(image,0,0,image.width/3,image.height,80,0,480,480);}
        requestAnimationFrame(draw);
      }
      draw();
      window.cameraFixture = { setPresent(value) { present = value; }, setMode(value){mode=value;} };
      const stream = canvas.captureStream(15);
      stream.getVideoTracks()[0].addEventListener("ended", () => { enabled = false; });
      return stream;
    };
  });
  const page = await context.newPage();
  const errors = []; page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error" && /TensorFlow|mediapipe|WebGL/i.test(message.text())) errors.push(message.text()); });
  const started = new Date().toISOString();
  const snapshot = { simulation_id: "vision-fixture", status: "ACTIVE", turn_state: "WAITING_STUDENT", current_question: { id: "question", position: 1, text: "Explique cómo validó la metodología de su investigación.", source: "BANK" }, answered_questions: 0, total_questions: 12, last_sequence: 1, questions_exhausted: false, started_at: started, finished_at: null, transcript: [] };
  const meta = { id: "vision-fixture", status: "ACTIVE", planned_duration_minutes: 30, camera_ready: true, microphone_ready: false, vision_ready: true, question_count: 12, document: { id: "fixture", name: "Validación visual" }, jury_profile: { id: "jury", name: "Tribunal de práctica", description: "", focus_type: "TECHNICAL", strictness: 3, interruption_level: "LOW" }, started_at: started, finished_at: null, created_at: started, updated_at: started };
  await page.route("**/api/v1/simulations/vision-fixture/session", route => route.fulfill({ json: snapshot }));
  await page.route("**/api/v1/simulations/vision-fixture", route => route.fulfill({ json: meta }));
  let channel;
  await page.routeWebSocket("**/ws/simulations/vision-fixture", ws => {
    channel = ws; ws.send(JSON.stringify({ type: "session.snapshot", payload: snapshot }));
    ws.onMessage(message => { if (typeof message === "string" && JSON.parse(message).type === "ping") ws.send(JSON.stringify({ type: "pong" })); });
  });
  let appearanceRequests = 0, appearanceKind = "formal";
  await page.route("**/api/v1/simulations/vision-fixture/appearance", async route => {
    appearanceRequests++;
    if(appearanceKind==="error"){await route.fulfill({status:503,json:{detail:"Proveedor no disponible en esta prueba."}});return;}
    const image = route.request().postDataJSON().image_base64;
    assert.ok(image.startsWith("/9j/") && image.length < 500000);
    await route.fulfill({ json: { person_present:true,upper_body_visible:true,jacket:appearanceKind==="formal",collared_shirt:appearanceKind==="formal",tie:false,upper_body_covered:appearanceKind!=="incomplete",presentation:appearanceKind,confidence:.95,feedback:"Prendas revisadas en este fotograma." } });
  });
  await page.goto(`${origin}/simulations/vision-fixture/live`, { waitUntil: "networkidle", timeout: 90000 });
  await page.locator(".room-diagnostics > summary").click();
  await page.locator(".room-appearance-details > summary").click();
  await page.locator('.room-presence[data-state="present"]').waitFor({ timeout: 60000 });
  await page.waitForFunction(() => document.querySelectorAll('.jury-character[data-ready="true"]').length === 3, null, { timeout: 60000 });
  assert.equal(await page.getByText("Detectado", { exact: true }).count(), 1);
  await page.screenshot({ path: path.join(output, "person-present.png"), fullPage: true });
  await page.evaluate(() => window.cameraFixture.setPresent(false));
  await page.locator('.room-presence[data-state="absent"]').waitFor({ timeout: 8000 });
  assert.equal(await page.getByText("Detectado", { exact: true }).count(), 0);
  assert.equal(await page.getByRole("button", { name: "Revisar vestimenta" }).isDisabled(), true);
  await page.screenshot({ path: path.join(output, "person-absent.png"), fullPage: true });
  await page.evaluate(() => window.cameraFixture.setPresent(true));
  await page.locator('.room-presence[data-state="present"]').waitFor({ timeout: 10000 });

  await page.getByText("Presentación formal observada", { exact: true }).waitFor();
  assert.ok(appearanceRequests >= 1, "Clothing review must start automatically");
  await page.getByRole("checkbox", { name: "Revisión automática de ropa (Gemini)" }).uncheck();
  await page.getByRole("checkbox", { name: "Avisos de voz al detectar un problema" }).uncheck();
  appearanceKind = "incomplete";
  await page.getByRole("button", { name: "Revisar vestimenta", exact:true }).click();
  await page.getByText("Falta una prenda en el torso", { exact: true }).waitFor();
  await page.getByText("No se observa una prenda en el torso. Ponte una camisa o blusa para practicar la defensa.", {exact:true}).first().waitFor();
  appearanceKind = "casual";
  await page.getByRole("button", { name: "Revisar vestimenta", exact:true }).click();
  await page.getByText("Ropa casual: revisa tu presentación", { exact:true }).waitFor();
  await page.getByText("Tu vestimenta es casual. Para ensayar una presentación formal, usa una camisa, blusa o saco.", {exact:true}).waitFor();

  appearanceKind="error";
  await page.getByRole("button",{name:"Revisar vestimenta",exact:true}).click();
  await page.getByText("Ropa: error de análisis",{exact:true}).waitFor();
  assert.equal(await page.getByText("Ropa casual: revisa tu presentación",{exact:true}).count(),0,"Provider errors must clear the prior clothing verdict");
  appearanceKind="formal";
  await page.getByRole("button",{name:"Revisar vestimenta",exact:true}).click();
  await page.getByText("Presentación formal observada",{exact:true}).waitFor();

  await page.evaluate(()=>window.cameraFixture.setMode("dark"));
  await page.locator('.live-visual-coach[data-lighting="dim"]').waitFor();
  await page.getByText("La imagen está oscura. Añade una luz delante de ti para poder revisar rostro y postura.",{exact:true}).waitFor();
  await page.evaluate(()=>window.cameraFixture.setMode("bright"));
  await page.locator('.live-visual-coach[data-lighting="bright"]').waitFor();
  await page.evaluate(()=>window.cameraFixture.setMode("multiple"));
  await page.locator('.live-visual-coach[data-faces="2"]').waitFor({timeout:12000});
  await page.getByText("Se detectan varios rostros. Quédate solo en el encuadre para medir tu mirada y postura.",{exact:true}).waitFor();
  assert.equal(await page.getByRole("button",{name:"Revisar vestimenta",exact:true}).isDisabled(),true);
  await page.evaluate(()=>window.cameraFixture.setMode("normal"));
  await page.locator('.live-visual-coach[data-faces="1"]').waitFor();
  await page.evaluate(()=>{window.cameraFixture.setMode("frozen");const video=document.querySelector(".room-camera-preview video");const time=video.currentTime;Object.defineProperty(video,"currentTime",{configurable:true,get:()=>time});});
  await page.locator('.live-visual-coach[data-freshness="stale"]').waitFor({timeout:10000});
  assert.equal(await page.getByRole("button",{name:"Calibrar mirando a la lente",exact:true}).isDisabled(),true);
  await page.evaluate(()=>{delete document.querySelector(".room-camera-preview video").currentTime;window.cameraFixture.setMode("normal");});
  await page.locator('.live-visual-coach[data-freshness="live"][data-faces="1"]').waitFor();

  await page.getByRole("button",{name:"Reiniciar cámara",exact:true}).click();
  await page.locator('.live-visual-coach[data-freshness="waiting"]').waitFor();
  await page.locator('.live-visual-coach[data-freshness="live"][data-faces="1"]').waitFor({timeout:60000});

  // Feed the same audio event path as real TTS, including a silent interval.
  const sampleRate = 16000, seconds = 6;
  const wav = Buffer.alloc(44 + sampleRate * seconds * 2);
  wav.write("RIFF"); wav.writeUInt32LE(wav.length - 8, 4); wav.write("WAVEfmt ", 8);
  wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(sampleRate, 24); wav.writeUInt32LE(sampleRate * 2, 28); wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34);
  wav.write("data", 36); wav.writeUInt32LE(wav.length - 44, 40);
  for (let i = 0; i < sampleRate * seconds; i++) {
    const time = i / sampleRate;
    wav.writeInt16LE(time < 1.8 || time > 3.8 ? Math.round(Math.sin(time * 2 * Math.PI * 210) * 9000) : 0, 44 + i * 2);
  }
  await page.evaluate(()=>{
    window.mouthSamples=[];const started=performance.now();
    window.mouthTimer=setInterval(()=>{const node=document.querySelector('.jury-character[data-speaking="true"] .jury-character-canvas');if(node)window.mouthSamples.push({t:performance.now()-(window.juryAudioStartedAt??started),value:Number(node.dataset.mouth)});},40);
  });
  channel.send(JSON.stringify({ type: "jury.speaking" }));
  channel.send(wav);
  channel.send(JSON.stringify({ type: "jury.finished", payload: { text: "Explique su metodología." } }));
  await page.locator('.jury-character[data-speaking="true"]').waitFor({ timeout: 8000 });
  await page.waitForFunction(() => Number(document.querySelector('.jury-character[data-speaking="true"] .jury-character-canvas')?.dataset.mouth) > .1);
  await page.waitForFunction(() => document.querySelectorAll('.jury-character[data-speaking="true"]').length === 0, null, { timeout: 10000 });
  const samples=await page.evaluate(()=>{clearInterval(window.mouthTimer);return window.mouthSamples;});
  assert.ok(samples.some(sample=>sample.value>.1),"Mouth must move during actual audio");
  assert.ok(samples.some(sample=>sample.t>2100&&sample.t<3500&&sample.value<.02),"Mouth must close during the interior silent interval");
  await page.screenshot({ path: path.join(output, "visual-coach-verified.png"), fullPage: true });
  assert.deepEqual(errors, []);
  console.log("PASS: actual video detection: person → empty → person; 3 loaded human rigs; TTS mouth movement, silence and speech end; darkness, overexposure, multiple faces, stale timestamps and restart; automatic clothing review, shirtless/casual alerts and manual controls; no native errors.");
  console.log(`Evidence: ${output}`);
} finally {
  await browser.close();
}
