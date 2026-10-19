import assert from "node:assert/strict";
import path from "node:path";
import {fileURLToPath} from "node:url";
import sharp from "sharp";
import {request} from "playwright";

// Opt-in integration test: sends only generated/rendered fixture images.
// It never reads a physical camera or writes a user's simulation.
const email=process.env.SOCRATIA_APPEARANCE_TEST_EMAIL,password=process.env.SOCRATIA_APPEARANCE_TEST_PASSWORD;
if(!email||!password)throw new Error("Provide SOCRATIA_APPEARANCE_TEST_EMAIL and SOCRATIA_APPEARANCE_TEST_PASSWORD for a local test account.");
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const fixtureDir=path.join(process.env.TEMP??".","socratia-gaze-validation");
const api=await request.newContext({baseURL:process.env.SOCRATIA_TEST_API??"http://localhost:8000/api/v1/"});
try{
  const login=await api.post("auth/login",{data:{email,password}});assert.equal(login.status(),200);
  const simulations=await(await api.get("simulations")).json();assert.ok(simulations.length,"Test account needs an existing simulation");
  const image=sharp(path.join(root,"public/images/jury/academic-panel.png"));const meta=await image.metadata();
  const formal=await image.extract({left:0,top:0,width:Math.floor(meta.width/3),height:meta.height}).resize({width:640,height:640,fit:"inside"}).jpeg({quality:75}).toBuffer();
  const frames={formal,casual:await sharp(path.join(fixtureDir,"front.png")).jpeg({quality:75}).toBuffer(),incomplete:await sharp(path.join(fixtureDir,"bare.png")).jpeg({quality:75}).toBuffer()};
  for(const [expected,jpeg] of Object.entries(frames)){
    const response=await api.post(`simulations/${simulations[0].id}/appearance`,{data:{image_base64:jpeg.toString("base64"),torso_in_frame:true},timeout:40000});
    const result=await response.json();console.log(expected,response.status(),JSON.stringify(result));
    assert.equal(response.status(),200);assert.equal(result.presentation,expected);
  }
  console.log("PASS: real provider distinguishes a blazer/shirt, a T-shirt, and a visible bare torso in test fixtures.");
}finally{await api.dispose();}
