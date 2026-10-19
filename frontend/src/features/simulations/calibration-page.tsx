"use client";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";
import Link from "next/link";
import {useParams,useRouter} from "next/navigation";
import {useCallback,useEffect,useState} from "react";
import {ArrowLeft,Camera,Mic,CheckCircle2,ScanLine,ShieldCheck} from "lucide-react";
import {AppSidebar} from "@/components/layout/app-sidebar";
import {getCurrentUser} from "@/features/auth/api";
import {getSimulation,saveCalibration} from "./api";
import {LiveVisualCoach} from "./live-visual-coach";
import {CameraTrackingOverlay} from "./camera-tracking-overlay";
import {AppearanceFeedback,type AppearanceStatus} from "./appearance-feedback";
import {torsoFitsFrame} from "./practice-signals";
import {VisualFeedback} from "./visual-feedback";
import {usePracticeCamera} from "./use-practice-camera";
import type {Simulation} from "@/types/simulation";
import type {User} from "@/types/user";
export function CalibrationPage() {
  const {id} = useParams<{id:string}>();
  const router = useRouter();
  const [user,setUser] = useState<User|null>(null);
  const [simulation,setSimulation] = useState<Simulation|null>(null);
  const [appearance,setAppearance]=useState<AppearanceStatus>({state:"waiting",result:null,message:"",time:""});
  const [cameraDeviceId,setCameraDeviceId]=useState("");
  const [enabled,setEnabled] = useState(false);
  const [microphoneId,setMicrophoneId] = useState("");
  const [devices,setDevices] = useState<MediaDeviceInfo[]>([]);
  const [micReady,setMicReady] = useState(false);
  const [level,setLevel] = useState(0);
  const [error,setError] = useState("");
  const [saving,setSaving] = useState(false);
  const {videoRef,presence,signals,status,error:cameraError,faceSignals,torsoTilt,faceError,tracking,calibrateGaze,gazeCalibrated,quality,restart,cameras} = usePracticeCamera(enabled,cameraDeviceId);
  const speakNotice=useCallback((text:string)=>{if(!("speechSynthesis" in window)||window.speechSynthesis.speaking)return;const speech=new SpeechSynthesisUtterance(text);speech.lang="es-ES";window.speechSynthesis.speak(speech);},[]);
  useEffect(() => {
    let active = true;
    Promise.all([getCurrentUser(),getSimulation(id)]).then(([current,item]) => {
      if (!active) return;
      if (["ACTIVE","COMPLETED"].includes(item.status)) {router.replace(`/simulations/${id}`); return;}
      setUser(current); setSimulation(item);
    }).catch(err => {if (active) setError(err instanceof Error ? err.message : "No pudimos cargar tu preparación.");});
    return () => {active = false;};
  },[id,router]);
  useEffect(() => {
    if (!enabled) return;
    let active = true, stream:MediaStream|undefined, context:AudioContext|undefined, frame=0, voiceFrames=0;
    async function start() {
      setMicReady(false); setLevel(0); setError("");
      try {
        stream = await navigator.mediaDevices.getUserMedia({audio:microphoneId ? {deviceId:{exact:microphoneId}} : true});
        if (!active) {stream.getTracks().forEach(track => track.stop()); return;}
        const available = await navigator.mediaDevices.enumerateDevices();
        if (!active) return;
        setDevices(available.filter(device => device.kind === "audioinput"));
        context = new AudioContext();
        const analyzer = context.createAnalyser(); analyzer.fftSize=512;
        context.createMediaStreamSource(stream).connect(analyzer);
        const data = new Uint8Array(analyzer.fftSize);
        const read = () => {
          if (!active) return;
          analyzer.getByteTimeDomainData(data);
          const rms = Math.sqrt(data.reduce((sum,value) => sum+((value-128)/128)**2,0)/data.length);
          setLevel(Math.min(100,Math.round(rms*400)));
          voiceFrames = rms > .025 ? voiceFrames+1 : Math.max(0,voiceFrames-1);
          if (voiceFrames >= 10) setMicReady(true);
          frame=requestAnimationFrame(read);
        };
        frame=requestAnimationFrame(read);
      } catch(err) {if (active) setError(err instanceof DOMException && err.name === "NotAllowedError" ? "Permiso de micrófono denegado. Habilítalo para completar la comprobación." : "No pudimos iniciar tu micrófono. Revisa el dispositivo seleccionado.");}
    }
    void start();
    return () => {active=false; cancelAnimationFrame(frame); stream?.getTracks().forEach(track => track.stop()); void context?.close().catch(() => undefined);};
  },[enabled,microphoneId]);
  const cameraReady = status === "ready";
  const allReady = enabled && cameraReady && presence === "present" && signals.reliable && faceSignals.detected && quality.faces===1 && quality.lighting==="usable" && micReady;
  async function confirm() {
    if (!allReady || saving) return;
    setSaving(true); setError("");
    try {await saveCalibration(id,{camera_ready:true,microphone_ready:true,vision_ready:true}); setEnabled(false); router.push(`/simulations/${id}`);}
    catch(err) {setError(err instanceof Error ? err.message : "No se pudo guardar la comprobación."); setSaving(false);}
  }
  return <main className="dashboard-layout"><AppSidebar user={user} active="simulations"/><section className="dashboard-content"><Link href={`/simulations/${id}`} className="detail-back"><ArrowLeft size={15}/> Preparación</Link><header className="dashboard-header"><div><p className="eyebrow">ANTES DE ENTRAR A LA SALA</p><h1>Probemos tu espacio.</h1><p>Encuadra tus hombros y di una frase para comprobar el micrófono.</p></div></header>{error && <div className="workspace-notice" role="alert">{error}</div>}{cameraError && <div className="workspace-notice" role="alert">{cameraError}</div>}
    {!simulation && !error ? <LoadingSkeleton label="Preparando tu espacio…" rows={2}/> : simulation && <><LiveVisualCoach quality={quality} presence={presence} face={faceSignals} pose={signals} torsoTilt={torsoTilt} status={status} appearance={appearance} frames={tracking.frames} busy={!enabled||!micReady} onSpeak={speakNotice} voiceInitiallyEnabled={false}/><div className="setup-grid"><section className="setup-camera"><video ref={videoRef} muted autoPlay playsInline/><CameraTrackingOverlay videoRef={videoRef} face={tracking.face} pose={tracking.pose} away={faceSignals.direction==="away"}/>{!enabled && <div><Camera size={32}/><h2>Aquí aparecerá tu cámara</h2><p>Los dispositivos se activan cuando tú lo decidas.</p></div>}<span><ShieldCheck size={14}/> Vista local en tu navegador</span></section><section className="setup-checks"><p className="eyebrow">COMPROBACIÓN DE DISPOSITIVOS</p><h2>Todo listo, paso a paso.</h2>{[{icon:Camera,title:"Cámara",ready:cameraReady,detail:cameraReady ? "Imagen disponible" : "Activa tu cámara"},{icon:ScanLine,title:"Encuadre",ready:signals.reliable && faceSignals.detected && quality.faces===1,detail:signals.reliable ? "Rostro y hombros visibles" : faceSignals.detected ? "Rostro detectado; muestra los hombros para medir postura" : "Busca buena luz y muestra tus hombros"},{icon:Mic,title:"Micrófono",ready:enabled && micReady,detail:enabled && micReady ? "Se recibió señal de audio" : "Di una frase en voz alta"}].map(({icon:Icon,...check}) => <div className="setup-check" key={check.title}><Icon size={19}/><div><strong>{check.title}</strong><span>{check.detail}</span></div>{check.ready && <CheckCircle2 size={18}/>}</div>)}<section className="room-signal-card">{enabled && <button type="button" className="room-text-button" onClick={restart}>Reiniciar cámara</button>}<VisualFeedback face={faceSignals} torsoTilt={torsoTilt} error={faceError}/><button type="button" className="room-text-button" disabled={!faceSignals.gaze} onClick={()=>{if(!calibrateGaze())setError("Mira a la lente y mantén el rostro quieto durante dos segundos antes de calibrar.");else setError("");}}>{gazeCalibrated?"Recalibrar mirada":"Calibrar mirando a la lente"}</button><AppearanceFeedback key={`appearance-v3-${id}`} simulationId={id} videoRef={videoRef} torsoInFrame={torsoFitsFrame(tracking.pose,tracking.aspectRatio??4/3)} available={cameraReady&&presence==="present"&&quality.faces===1} onStatus={setAppearance}/></section>{cameras.length>1 && <label className="camera-device-picker">Cámara<select value={cameraDeviceId} onChange={event=>setCameraDeviceId(event.target.value)}><option value="">Predeterminada</option>{cameras.map((device,index)=><option key={device.deviceId||index} value={device.deviceId}>{device.label||`Cámara ${index+1}`}</option>)}</select></label>}<div className="setup-level"><i style={{width:`${level}%`}}/></div>{devices.length > 0 && <label className="simulation-field">Entrada de audio<select value={microphoneId} onChange={event => setMicrophoneId(event.target.value)}><option value="">Predeterminado del sistema</option>{devices.map((device,index) => <option key={device.deviceId || index} value={device.deviceId}>{device.label || `Micrófono ${index+1}`}</option>)}</select></label>}<p>Esta comprobación valida señales visibles y audio; no certifica identidad ni presencia mediante biometría.</p></section></div><footer className="setup-footer"><p>La preparación inicial requiere cámara, micrófono y detección visual. Durante la práctica puedes desactivar la cámara y responder por texto.</p><div><button className="button button-ghost" disabled={saving} onClick={() => setEnabled(!enabled)}>{enabled ? "Detener dispositivos" : "Activar dispositivos"}</button><button className="button button-primary" disabled={!allReady || saving} onClick={() => void confirm()}>{saving ? "Guardando…" : "Guardar y continuar"}</button></div></footer></>}
  </section></main>;
}
