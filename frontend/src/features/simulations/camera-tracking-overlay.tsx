"use client";
import {useEffect,useRef,type RefObject} from "react";
import type {Landmark} from "./practice-signals";

export function CameraTrackingOverlay({videoRef,face,pose,away}:{videoRef:RefObject<HTMLVideoElement|null>;face:Landmark[];pose:Landmark[];away:boolean}) {
  const canvas=useRef<HTMLCanvasElement>(null);
  useEffect(()=>{
    const target=canvas.current,video=videoRef.current;
    if(!target || !video)return;
    target.width=video.videoWidth || 640;target.height=video.videoHeight || 480;
    const ctx=target.getContext("2d");if(!ctx)return;
    ctx.clearRect(0,0,target.width,target.height);
    const point=(p:Landmark|undefined)=>p && Number.isFinite(p.x) && Number.isFinite(p.y) && p.x>=0 && p.x<=1 && p.y>=0 && p.y<=1;
    const dot=(p:Landmark|undefined,color:string,r=3)=>{if(!point(p))return;ctx.fillStyle=color;ctx.beginPath();ctx.arc(p!.x*target.width,p!.y*target.height,r,0,Math.PI*2);ctx.fill();};
    const line=(a:Landmark|undefined,b:Landmark|undefined,color:string)=>{if(!point(a)||!point(b))return;ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(a!.x*target.width,a!.y*target.height);ctx.lineTo(b!.x*target.width,b!.y*target.height);ctx.stroke();};
    const color=away?"#ffc265":"#79e5b1";
    for(const [a,b] of [[33,133],[159,145],[362,263],[386,374]])line(face[a],face[b],color);
    dot(face[468],"#fff",4);dot(face[473],"#fff",4);dot(face[1],color);
    if(face.length){const points=face.filter(point);if(points.length){const xs=points.map(p=>p.x*target.width),ys=points.map(p=>p.y*target.height);ctx.strokeStyle=color;ctx.lineWidth=2;ctx.strokeRect(Math.min(...xs)-7,Math.min(...ys)-7,Math.max(...xs)-Math.min(...xs)+14,Math.max(...ys)-Math.min(...ys)+14);}}
    const visible=(p:Landmark|undefined)=>point(p)&&(p!.visibility??0)>.65;
    for(const [a,b] of [[11,12],[11,23],[12,24],[23,24]])if(visible(pose[a])&&visible(pose[b]))line(pose[a],pose[b],"#91c8ff");
    for(const i of [11,12,15,16,23,24])if(visible(pose[i]))dot(pose[i],"#91c8ff");
  },[videoRef,face,pose,away]);
  return <canvas ref={canvas} className="camera-tracking-overlay" aria-label="Seguimiento en vivo de rostro, iris y hombros"/>;
}
