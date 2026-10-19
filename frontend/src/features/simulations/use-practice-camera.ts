"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { createCameraWorker } from "./camera-worker-client";
import { presenceFromSignals, EMPTY_SIGNALS, EMPTY_FACE, measureFace, measureTorso, measurePose, type FaceSignals, type VisualSignals, type GazeReference, type Landmark } from "./practice-signals";
import {EMPTY_QUALITY, measureExposure, type CameraQuality} from "./camera-quality";
// MediaPipe sends this one informational native message to stderr. Keep actual errors visible.
let logUsers = 0;
let restoreNativeLog: (() => void) | undefined;
function routeNativeInfo() {
  if (logUsers++ === 0) {
    const original = console.error;
    const filtered = (...args: unknown[]) => {
      if (args.length === 1 && typeof args[0] === "string" && /^INFO: Created TensorFlow Lite XNNPACK delegate for CPU\.\s*$/.test(args[0])) { console.info(args[0]); return; }
      original(...args);
    };
    console.error = filtered;
    restoreNativeLog = () => { if (console.error === filtered) console.error = original; };
  }
  return () => { if (--logUsers === 0) { restoreNativeLog?.(); restoreNativeLog = undefined; } };
}
export function usePracticeCamera(enabled: boolean, deviceId = "") {
  const videoRef = useRef<HTMLVideoElement>(null);
  const samples = useRef<number[]>([]);
  const [signals, setSignals] = useState<VisualSignals>(EMPTY_SIGNALS);
  const [status, setStatus] = useState<"off" | "starting" | "ready" | "error">("off");
  const [faceSignals, setFaceSignals] = useState<FaceSignals>(EMPTY_FACE);
  const [torsoTilt, setTorsoTilt] = useState<number | null>(null);
  const [faceError, setFaceError] = useState("");
  const [error, setError] = useState("");
  const [baseline, setBaseline] = useState<number | null>(null);
  const [presence, setPresence] = useState<"unknown" | "present" | "absent">("unknown");
  const gazeReference = useRef<GazeReference | null>(null);
  const gazeSamples = useRef<GazeReference[]>([]);
  const [gazeCalibrated, setGazeCalibrated] = useState(false);
  const [tracking, setTracking] = useState<{face:Landmark[];pose:Landmark[];updatedAt:number;frames:number;aspectRatio?:number}>({face:[],pose:[],updatedAt:0,frames:0});
  const [restartCount,setRestartCount]=useState(0);
  const restart=useCallback(()=>setRestartCount(value=>value+1),[]);
  const [quality,setQuality]=useState<CameraQuality>(EMPTY_QUALITY);
  const [cameras,setCameras]=useState<MediaDeviceInfo[]>([]);
  const calibrateGaze = useCallback(() => {
    const data=gazeSamples.current;
    if (data.length<6) return false;
    const mean=(key:keyof GazeReference) => data.reduce((sum,item)=>sum+item[key],0)/data.length;
    if (["horizontal","vertical","yaw","pitch"].some(key=>{const values=data.map(item=>item[key as keyof GazeReference]);return Math.max(...values)-Math.min(...values)>(key==="horizontal" ? .06 : .08);})) return false;
    gazeReference.current={horizontal:mean("horizontal"),vertical:mean("vertical"),yaw:mean("yaw"),pitch:mean("pitch")};
    setGazeCalibrated(true);
    return true;
  }, []);
  const recalibrate = useCallback(() => {
    if (samples.current.length < 10) return false;
    setBaseline(samples.current.reduce((a,b) => a+b,0) / samples.current.length);
    return true;
  }, []);
  useEffect(() => {
    if (!enabled) return;
    const releaseNativeLog = routeNativeInfo();
    let startupFinished=false,logReleased=false;
    const releaseLog=()=>{if(!logReleased){logReleased=true;releaseNativeLog();}};
    const refreshDevices=()=>{void navigator.mediaDevices.enumerateDevices().then(devices=>{if(active)setCameras(devices.filter(device=>device.kind==="videoinput"));}).catch(()=>undefined);};
    navigator.mediaDevices?.addEventListener("devicechange",refreshDevices);
    let active = true, busy = false;
    let stream: MediaStream | undefined;
    let detector: ReturnType<typeof createCameraWorker> | undefined;
    let absentFrames = 0;
    let frames = 0;
    const exposureCanvas=document.createElement("canvas");exposureCanvas.width=96;exposureCanvas.height=72;
    const exposureContext=exposureCanvas.getContext("2d",{willReadFrequently:true});
    const clearMeasurements=(stale=false)=>{
      samples.current=[];gazeSamples.current=[];
      setTracking({face:[],pose:[],updatedAt:0,frames});setPresence("unknown");setSignals(EMPTY_SIGNALS);setFaceSignals(EMPTY_FACE);setTorsoTilt(null);
      setQuality({...EMPTY_QUALITY,freshness:stale ? "stale" : "waiting"});
    };
    let lastVideoTime=-1,lastNewFrameAt=Date.now();
    let timer: ReturnType<typeof setInterval> | undefined;
    async function start() {
      setQuality(EMPTY_QUALITY); setStatus("starting"); setPresence("unknown"); setError(""); setSignals(EMPTY_SIGNALS); setFaceSignals(EMPTY_FACE); setTorsoTilt(null); setFaceError(""); setBaseline(null); samples.current = []; gazeReference.current=null;gazeSamples.current=[];setGazeCalibrated(false);setTracking({face:[],pose:[],updatedAt:0,frames:0});
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: {width: {ideal:640}, height: {ideal:480},frameRate:{ideal:15,max:24},...(deviceId ? {deviceId:{exact:deviceId}} : {})}, audio:false });
        if (!active) { stream.getTracks().forEach(track => track.stop()); return; }
        const video = videoRef.current;
        if (!video) throw new Error("No encontramos la vista de cámara.");
        for(const track of stream.getVideoTracks())track.addEventListener("ended",()=>{if(active){if(timer)clearInterval(timer);clearMeasurements(true);setError("La cámara se desconectó. Conéctala de nuevo o elige otra y pulsa Reiniciar cámara.");setStatus("error");}},{once:true});
        video.srcObject = stream;
        await video.play();
        if (!active) return;
        const devices=await navigator.mediaDevices.enumerateDevices();
        if (!active) return;
        if(active)setCameras(devices.filter(device=>device.kind==="videoinput"));
        detector = createCameraWorker();
        const capabilities = await detector.ready;
        if (!active) return;
        if (!capabilities.pose) setError("No pudimos cargar el detector de postura. El rostro sigue disponible.");
        if (!capabilities.face) setFaceError("No se pudo cargar el análisis facial. La postura sigue disponible.");
        setStatus("ready");
        let nextFrameAt = 0;
        timer = setInterval(async () => {
          if (!active || busy || document.hidden || performance.now() < nextFrameAt) return;
          if (!stream?.active || video.readyState < 2 || video.paused) {
            clearMeasurements(); return;
          }
          if(video.currentTime===lastVideoTime){
            if(Date.now()-lastNewFrameAt>2000){clearMeasurements(true);setError("La cámara dejó de enviar imágenes nuevas. Reiníciala o selecciona otra cámara.");}
            return;
          }
          lastVideoTime=video.currentTime;lastNewFrameAt=Date.now();
          busy = true;
          try {
            const timestamp=performance.now();
            const detected = await detector!.detect(video,timestamp);
            if (!active) return;
            // Keep at most four analyses/second, slower when inference is expensive.
            nextFrameAt=performance.now()+Math.max(0,Math.min(750,detected.elapsed*2)-250);
            let current = EMPTY_SIGNALS;
            let currentFace = EMPTY_FACE;
            let frameSucceeded = false;
            let faceCount:number|null=null;
            let facePoints:Landmark[]=[],posePoints:Landmark[]=[];
            if (capabilities.pose) {
              try {
                const result = detected.pose;
                if (!result) throw new Error("Postura no disponible");
                posePoints=result.landmarks[0] ?? [];
                current = measurePose(result.landmarks[0] ?? [], video.videoWidth / video.videoHeight);
                setTorsoTilt(measureTorso(result.landmarks[0] ?? [], video.videoWidth/video.videoHeight));
                setError(""); frameSucceeded = true;
              } catch { setTorsoTilt(null); setError("No pudimos medir la postura. Revisa la luz y el encuadre."); }
            }
            setSignals(current);
            if (capabilities.face) {
              try {
                const facial = detected.face;
                if (!facial) throw new Error("Rostro no disponible");
                faceCount=facial.faceLandmarks.length;
                // Never combine a pose and gaze from different people.
                facePoints=faceCount===1 ? facial.faceLandmarks[0] : [];
                currentFace = measureFace(facePoints, facial.faceBlendshapes[0]?.categories ?? [],video.videoWidth/video.videoHeight,gazeReference.current);
                if (currentFace.gaze && currentFace.eyes === "open") {gazeSamples.current.push(currentFace.gaze);if(gazeSamples.current.length>8)gazeSamples.current.shift();} else gazeSamples.current=[];
                setFaceSignals(currentFace); frameSucceeded = true;
                setFaceError("");
              } catch { gazeSamples.current=[];setFaceSignals(EMPTY_FACE); setFaceError("No se pudo medir el rostro en este fotograma."); }
            }
            if(faceCount!==null && faceCount>1){posePoints=[];current=EMPTY_SIGNALS;setSignals(current);setTorsoTilt(null);gazeSamples.current=[];}
            let exposure:Pick<CameraQuality,"lighting"|"brightness"|"faceBrightness">={lighting:"unknown",brightness:null,faceBrightness:null};
            try {if(exposureContext){exposureContext.drawImage(video,0,0,96,72);exposure=measureExposure(exposureContext.getImageData(0,0,96,72).data,96,72,facePoints);}}catch{/* A failed exposure read never becomes a positive result. */}
            setQuality({...exposure,faces:faceCount,freshness:"live"});
            setTracking({face:facePoints,pose:posePoints,updatedAt:Date.now(),frames:++frames,aspectRatio:video.videoWidth/video.videoHeight});
            if (!frameSucceeded) setPresence("unknown");
            else if ((faceCount??0)>1 || presenceFromSignals(current, currentFace) === "present") { absentFrames = 0; setPresence("present"); }
            else if (++absentFrames >= 3) setPresence("absent");
            if (current.reliable && current.shoulderTilt !== null) { samples.current.push(current.shoulderTilt); if (samples.current.length > 15) samples.current.shift(); }
            else samples.current = [];
          } catch { if(active){clearMeasurements(); setError("No pudimos medir este fotograma. Ajusta la luz o reinicia la cámara.");} }
          finally { busy = false; }
        }, 250);
      } catch (err) {
        stream?.getTracks().forEach(track => track.stop());
        detector?.close();
        if (active) { setStatus("error"); setError(err instanceof DOMException && err.name === "NotAllowedError" ? "Permiso de cámara denegado. Habilítalo en el navegador y pulsa Reiniciar cámara." : err instanceof DOMException && err.name === "NotFoundError" ? "No se encontró una cámara. Conecta una y vuelve a intentarlo." : err instanceof DOMException && err.name === "NotReadableError" ? "No se pudo abrir la cámara. Revisa si otra aplicación la está usando y vuelve a intentarlo." : err instanceof DOMException && err.name === "OverconstrainedError" ? "La cámara seleccionada ya no está disponible. Elige otra cámara." : "No pudimos iniciar el análisis visual. Puedes reiniciar la cámara o seguir con voz o texto."); }
      }
    }
    void start().finally(()=>{startupFinished=true;if(!active)releaseLog();});
    return () => { active = false; if(startupFinished)releaseLog(); navigator.mediaDevices?.removeEventListener("devicechange",refreshDevices); if (timer) clearInterval(timer); stream?.getTracks().forEach(track => track.stop()); detector?.close(); };
  }, [enabled,deviceId,restartCount]);
  return {videoRef,cameras,restart, quality:enabled && status==="ready" ? quality : EMPTY_QUALITY, tracking:enabled ? tracking : {face:[],pose:[],updatedAt:0,frames:0}, gazeCalibrated,calibrateGaze,presence: enabled && status === "ready" ? presence : "unknown" as const, faceSignals: enabled && status === "ready" ? faceSignals : EMPTY_FACE, torsoTilt: enabled && status === "ready" ? torsoTilt : null, faceError: enabled ? faceError : "", signals: enabled && status === "ready" ? signals : EMPTY_SIGNALS, status: enabled ? status : "off", error: enabled ? error : "", baseline, recalibrate};
}
