import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import http from "node:http";
import {fileURLToPath} from "node:url";
import ts from "typescript";
import {chromium} from "playwright";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const output=path.join(process.env.TEMP??".","socratia-gaze-validation");await fs.mkdir(output,{recursive:true});
const source=await fs.readFile(path.join(root,"src/features/simulations/practice-signals.ts"),"utf8");
const signals=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const html=`<!doctype html><html><body style="margin:0"><script type="importmap">{"imports":{"three":"/node_modules/three/build/three.module.js","three/addons/":"/node_modules/three/examples/jsm/"}}</script><script type="module">
import * as THREE from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {FilesetResolver,FaceLandmarker} from '/node_modules/@mediapipe/tasks-vision/vision_bundle.mjs';import {measureFace} from '/signals.js';
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(640,480);renderer.setPixelRatio(1);renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.setClearColor('#cbd3d5');document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.add(new THREE.HemisphereLight(0xffffff,0x526878,2));const key=new THREE.DirectionalLight(0xffffff,2.5);key.position.set(1,2,3);scene.add(key);
const gltf=await new GLTFLoader().loadAsync('/public/avatars/alex.glb');scene.add(gltf.scene);gltf.scene.updateMatrixWorld(true);
const head=gltf.scene.getObjectByName('Head'),left=gltf.scene.getObjectByName('LeftEye'),right=gltf.scene.getObjectByName('RightEye');
const center=new THREE.Vector3();head.getWorldPosition(center);const camera=new THREE.PerspectiveCamera(35,640/480,.01,20);camera.position.set(center.x,center.y-.12,1.05);camera.lookAt(center.x,center.y-.12,0);
const bareBody=new THREE.Group();const skin=new THREE.MeshStandardMaterial({color:'#dfb69e',roughness:.7});
const torso=new THREE.Mesh(new THREE.SphereGeometry(1,40,28),skin);torso.scale.set(.245,.32,.13);torso.position.set(center.x,center.y-.43,center.z-.015);bareBody.add(torso);
for(const side of [-1,1]){const arm=new THREE.Mesh(new THREE.CapsuleGeometry(.065,.23,6,20),skin);arm.position.set(center.x+side*.245,center.y-.45,center.z-.015);arm.rotation.z=side*.12;bareBody.add(arm);}
bareBody.visible=false;scene.add(bareBody);
const original={head:head.quaternion.clone(),left:left.quaternion.clone(),right:right.quaternion.clone()};
const files=await FilesetResolver.forVisionTasks('/public/vision/wasm');const detector=await FaceLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:'/public/vision/models/face.task'},runningMode:'VIDEO',numFaces:2,outputFaceBlendshapes:true,minFaceDetectionConfidence:.5});
window.inspectPose=async function({eyeYaw=0,eyePitch=0,headYaw=0,bare=false}){
head.quaternion.copy(original.head);left.quaternion.copy(original.left);right.quaternion.copy(original.right);
head.rotateY(headYaw);left.rotateY(eyeYaw);right.rotateY(eyeYaw);left.rotateX(eyePitch);right.rotateX(eyePitch);
gltf.scene.traverse(node=>{if(node.name==='outfit_top')node.visible=!bare;});bareBody.visible=bare;
let result;
for(let i=0;i<8;i++){await new Promise(requestAnimationFrame);renderer.render(scene,camera);const facial=detector.detectForVideo(renderer.domElement,performance.now());result=measureFace(facial.faceLandmarks[0]??[],facial.faceBlendshapes[0]?.categories??[],4/3);}
return {result,image:renderer.domElement.toDataURL('image/png')};};window.fixtureReady=true;
</script></body></html>`;
const server=http.createServer(async(req,res)=>{
  try {
    if(req.url==="/"){res.setHeader("Content-Type","text/html");res.end(html);return;}
    if(req.url==="/signals.js"){res.setHeader("Content-Type","text/javascript");res.end(signals);return;}
    const relative=decodeURIComponent(new URL(req.url,"http://localhost").pathname).slice(1);
    if(!["node_modules/three/","node_modules/@mediapipe/tasks-vision/","public/vision/","public/avatars/"].some(prefix=>relative.startsWith(prefix)))throw new Error("Not allowed");
    const filename=path.resolve(root,relative);if(!filename.startsWith(root+path.sep))throw new Error("Not allowed");
    res.setHeader("Content-Type",filename.endsWith(".wasm")?"application/wasm":/\.m?js$/.test(filename)?"text/javascript":"application/octet-stream");res.end(await fs.readFile(filename));
  }catch{res.statusCode=404;res.end();}
});
await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
const browser=await chromium.launch({channel:"msedge",headless:true});
try{
  const page=await browser.newPage();page.on("pageerror",error=>console.log("PAGE ERROR",error.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/`);await page.waitForFunction(()=>window.fixtureReady,null,{timeout:60000});
  const cases={front:{},eyes_left:{eyeYaw:.35},eyes_right:{eyeYaw:-.35},eyes_down:{eyePitch:.3},head_side:{headYaw:.5},bare:{bare:true}};
  const results={};
  for(const [name,pose] of Object.entries(cases)){
    const {result,image}=await page.evaluate(pose=>window.inspectPose(pose),pose);
    results[name]=result;await fs.writeFile(path.join(output,name+".png"),Buffer.from(image.split(",")[1],"base64"));console.log(name,JSON.stringify(result));
  }
  await fs.writeFile(path.join(output,"results.json"),JSON.stringify(results,null,2));
  assert.ok(results.front.detected,"The real model must detect the rendered face");
  for(const name of ["eyes_left","eyes_right","eyes_down","head_side"])assert.equal(results[name].direction,"away",name+" must not pass as camera contact");
  console.log("PASS: actual FaceLandmarker on controlled human rig: eyes left/right/down with fixed head, and head turned.");
  console.log("Evidence:",output);
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
