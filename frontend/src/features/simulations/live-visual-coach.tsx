"use client";
import {useEffect,useRef,useState} from "react";
import {Eye,Camera,Shirt,ScanLine,AlertTriangle,CheckCircle2} from "lucide-react";
import type {FaceSignals,VisualSignals} from "./practice-signals";
import {EMPTY_QUALITY,type CameraQuality} from "./camera-quality";
import {getObservations,ObservationTracker,type Observation} from "./coach-observations";
import type {AppearanceStatus} from "./appearance-feedback";

export function LiveVisualCoach({presence,face,pose,torsoTilt,status,appearance,frames,busy,onSpeak,voiceInitiallyEnabled=true,quality=EMPTY_QUALITY}:{
  presence:"present"|"absent"|"unknown";face:FaceSignals;pose:VisualSignals;torsoTilt:number|null;
  status:"off"|"starting"|"ready"|"error";appearance:AppearanceStatus;frames:number;
  busy:boolean;onSpeak:(text:string)=>void;voiceInitiallyEnabled?:boolean;quality?:CameraQuality;
}) {
  const [voice,setVoice]=useState(voiceInitiallyEnabled);
  const spoken=useRef(new Map<string,number>());
  const lastSpoken=useRef(0);
  const tracker=useRef(new ObservationTracker());
  const [warnings,setWarnings]=useState<Observation[]>([]);
  const candidates=JSON.stringify(getObservations({presence,face,pose,torsoTilt,status,appearance,quality}));
  useEffect(()=>{
    const observations=JSON.parse(candidates) as Observation[];
    const update=()=>{
      const next=tracker.current.update(observations,Date.now());
      setWarnings(current=>JSON.stringify(current)===JSON.stringify(next) ? current : next);
    };
    update();const timer=setInterval(update,250);return ()=>clearInterval(timer);
  },[candidates]);
  useEffect(()=>{
    if(!voice||busy||!warnings.length)return;
    const speak=()=>{
      const now=Date.now();if(now-lastSpoken.current<20000)return;
      const item=warnings.find(item=>now-(spoken.current.get(item.id+item.text)??0)>=60000);
      if(!item)return;
      lastSpoken.current=now;spoken.current.set(item.id+item.text,now);onSpeak(item.text);
    };
    const timer=setInterval(speak,1000);return ()=>clearInterval(timer);
  },[voice,busy,warnings,onSpeak]);

  const gaze=(quality.faces??0)>1 ? "Mirada sin verificar" : face.direction==="away" ? "Mirada apartada" : face.direction==="camera" ? "Mirada centrada" : face.eyes==="closed" ? "Ojos cerrados" : face.detected ? "Mirada sin verificar" : "Rostro no visible";
  const clothing=appearance.state==="result" && presence==="present" && quality.faces===1 ? appearance.result?.presentation : undefined;
  const clothingText=appearance.state==="analyzing" ? "Analizando ropa…" : clothing==="incomplete" ? "Falta prenda superior" : clothing==="casual" ? "Ropa casual" : clothing==="formal" ? "Ropa formal observada" : appearance.state==="off" ? "Ropa: análisis apagado" : appearance.state==="error" ? "Ropa: error de análisis" : clothing==="uncertain" ? "Ropa: no verificable" : "Ropa: esperando captura";
  const framingText=presence!=="present" ? "Encuadre sin verificar" : face.framing==="cropped" ? "Rostro cortado" : face.framing==="near" || pose.framing==="near" ? "Demasiado cerca" : face.framing==="far" || pose.framing==="far" ? "Demasiado lejos" : pose.centered===false ? "Fuera del centro" : pose.reliable && face.framing==="ready" ? "Encuadre centrado" : "Encuadre sin verificar";
  const handsText=pose.handsVisible==null ? "Manos sin verificar" : (pose.handsNearFace??0)>0 ? "Mano cerca del rostro" : pose.handsVisible===0 ? "Manos fuera del encuadre" : `${pose.handsVisible} ${pose.handsVisible===1?"mano visible":"manos visibles"}`;
  const cards=[
    {Icon:Camera,text:(quality.faces??0)>1 ? "Varios rostros en cámara" : presence==="present" ? "Persona en cámara" : presence==="absent" ? "No estás en cámara" : status==="starting" ? "Cargando detectores…" : "Cámara sin medición",state:presence==="present" && quality.faces===1 ? "good" : "warning"},
    {Icon:Eye,text:gaze,state:face.direction==="camera" ? "good" : "warning"},
    {Icon:ScanLine,text:!pose.reliable ? "Postura sin verificar" : (pose.shoulderTilt??0)>10 || (torsoTilt??0)>12 || (face.headTilt??0)>15 ? "Revisa tu postura" : "Hombros nivelados",state:pose.reliable && (pose.shoulderTilt??0)<=10 && (torsoTilt??0)<=12 && (face.headTilt??0)<=15 ? "good" : "warning"},
    {Icon:Camera,text:framingText,state:framingText==="Encuadre centrado" ? "good" : "warning"},
    {Icon:ScanLine,text:handsText,state:pose.handsVisible!=null && pose.handsVisible>0 && !pose.handsNearFace ? "good" : "neutral"},
    {Icon:Camera,text:quality.freshness==="stale" ? "Cámara congelada" : quality.lighting==="dim" ? "Poca iluminación" : quality.lighting==="bright" ? "Imagen sobreexpuesta" : quality.lighting==="backlit" ? "Rostro a contraluz" : quality.lighting==="usable" ? "Exposición utilizable" : "Iluminación sin verificar",state:quality.lighting==="usable" ? "good" : "warning"},
    {Icon:Shirt,text:clothingText,state:clothing==="formal" && appearance.state==="result" ? "good" : "warning"},
  ];
  return <section className="live-visual-coach" aria-label="Comprobación visual en vivo" data-faces={quality.faces??"unknown"} data-lighting={quality.lighting} data-freshness={quality.freshness}>
    <header><strong><span className={frames>0&&quality.freshness==="live"?"coach-live-dot":""}/> Tu presentación en vivo</strong><span>{quality.freshness==="live" ? "Seguimiento activo" : quality.freshness==="stale" ? "Sin imágenes nuevas" : "Esperando cámara"}</span></header>
    <div className="coach-status-grid">{cards.map(({Icon,text,state})=><div key={text} data-state={state}><Icon size={18}/><strong>{text}</strong></div>)}</div>
    <div className="coach-alerts" aria-live="polite">{warnings.map(item=><p key={item.id} role="status"><AlertTriangle size={17}/>{item.text}</p>)}{!warnings.length && status==="ready" && <p className="coach-neutral"><CheckCircle2 size={17}/>{presence!=="present" || quality.faces!==1 || quality.lighting!=="usable" || face.direction==="unknown" || !pose.reliable || torsoTilt===null || face.framing==="unknown" || !appearance.result ? "Todavía hay señales sin verificar. No se dan por correctas." : "Sin avisos en las señales verificadas."}</p>}</div>
    <label className="coach-voice-toggle"><input type="checkbox" checked={voice} onChange={event=>setVoice(event.target.checked)}/> Avisos de voz al detectar un problema</label>
  </section>;
}
