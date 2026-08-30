"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { getCurrentUser } from "@/features/auth/api";
import { getSimulation, saveCalibration } from "@/features/simulations/api";
import { ApiError } from "@/lib/api";
import type { Simulation } from "@/types/simulation";
import type { User } from "@/types/user";

const WASM_URL = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm";
const MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

function mediaError(error: unknown): string {
  if (error instanceof DOMException && error.name === "NotAllowedError") return "No se puede continuar porque no diste permiso a la cámara o al micrófono. Habilítalos en el navegador y vuelve a intentar.";
  if (error instanceof DOMException && error.name === "NotFoundError") return "No encontramos una cámara o micrófono disponible en este equipo.";
  return "No pudimos iniciar los dispositivos. Comprueba que ninguna otra aplicación los esté usando.";
}

export function CalibrationPage() {
  const params = useParams<{ id: string }>(); const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null); const streamRef = useRef<MediaStream | null>(null); const audioFrameRef = useRef(0); const visionFrameRef = useRef(0); const audioRef = useRef<AudioContext | null>(null);
  const [user, setUser] = useState<User | null>(null); const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [cameraReady, setCameraReady] = useState(false); const [microphoneReady, setMicrophoneReady] = useState(false); const [visionReady, setVisionReady] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0); const [devices, setDevices] = useState<MediaDeviceInfo[]>([]); const [microphoneId, setMicrophoneId] = useState("");
  const [checking, setChecking] = useState(false); const [saving, setSaving] = useState(false); const [error, setError] = useState("");

  const stop = useCallback(() => { cancelAnimationFrame(audioFrameRef.current); cancelAnimationFrame(visionFrameRef.current); streamRef.current?.getTracks().forEach((track) => track.stop()); streamRef.current = null; void audioRef.current?.close(); audioRef.current = null; }, []);
  useEffect(() => { Promise.all([getCurrentUser(), getSimulation(params.id)]).then(([current, item]) => { setUser(current); setSimulation(item); }).catch(() => router.replace("/simulations")); return stop; }, [params.id, router, stop]);

  async function calibrate() {
    stop(); setChecking(true); setError(""); setCameraReady(false); setMicrophoneReady(false); setVisionReady(false); setAudioLevel(0);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 960 }, height: { ideal: 540 } }, audio: microphoneId ? { deviceId: { exact: microphoneId } } : true });
      streamRef.current = stream;
      if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play(); }
      setCameraReady(stream.getVideoTracks().length > 0);
      const available = await navigator.mediaDevices.enumerateDevices(); setDevices(available.filter((item) => item.kind === "audioinput"));
      const context = new AudioContext(); audioRef.current = context; const source = context.createMediaStreamSource(stream); const analyser = context.createAnalyser(); analyser.fftSize = 256; source.connect(analyser); const data = new Uint8Array(analyser.frequencyBinCount);
      const readAudio = () => { analyser.getByteFrequencyData(data); const level = Math.min(100, Math.round(data.reduce((sum, value) => sum + value, 0) / data.length)); setAudioLevel(level); if (level >= 6) setMicrophoneReady(true); audioFrameRef.current = requestAnimationFrame(readAudio); }; readAudio();
      const { FilesetResolver, PoseLandmarker } = await import("@mediapipe/tasks-vision");
      const fileset = await FilesetResolver.forVisionTasks(WASM_URL); let pose;
      try { pose = await PoseLandmarker.createFromOptions(fileset, { baseOptions: { modelAssetPath: MODEL_URL, delegate: "GPU" }, runningMode: "VIDEO", numPoses: 1 }); }
      catch { pose = await PoseLandmarker.createFromOptions(fileset, { baseOptions: { modelAssetPath: MODEL_URL }, runningMode: "VIDEO", numPoses: 1 }); }
      const detect = () => { const video = videoRef.current; if (video && video.readyState >= 2) { const result = pose.detectForVideo(video, performance.now()); if (result.landmarks.length > 0) setVisionReady(true); } visionFrameRef.current = requestAnimationFrame(detect); }; detect();
    } catch (caught) { setError(mediaError(caught)); stop(); }
    finally { setChecking(false); }
  }

  async function confirm() {
    if (!cameraReady || !microphoneReady || !visionReady || saving) return;
    setSaving(true); setError("");
    try { await saveCalibration(params.id, { camera_ready: true, microphone_ready: true, vision_ready: true }); stop(); router.push(`/simulations/${params.id}`); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "No pudimos guardar la calibración."); setSaving(false); }
  }

  if (!user || !simulation) return <main className="loading-screen"><div className="loading-orbit" /><p>Preparando calibración…</p></main>;
  return <main className="dashboard-layout"><AppSidebar user={user} active="simulations" /><section className="dashboard-content simulations-content"><Link className="detail-back" href={`/simulations/${simulation.id}`}>← Preparación</Link><header className="dashboard-header"><div><p className="eyebrow">CU14 · Privacidad local</p><h1>Calibrar cámara y micrófono</h1><p>El vídeo y el audio se analizan en tu navegador. Socratia sólo guarda el resultado de disponibilidad.</p></div></header>{error && <p className="form-error calibration-error" role="alert">{error}</p>}<div className="calibration-grid"><section className="camera-panel"><video ref={videoRef} muted playsInline /><div className="privacy-badge">🔒 Vídeo local · no se envía</div>{!cameraReady && <div className="camera-placeholder">Activa tus dispositivos para ver la previsualización</div>}</section><section className="device-panel"><h2>Comprobaciones</h2><label>Micrófono<select value={microphoneId} onChange={(event) => setMicrophoneId(event.target.value)}><option value="">Predeterminado</option>{devices.map((device) => <option key={device.deviceId} value={device.deviceId}>{device.label || "Micrófono disponible"}</option>)}</select></label><div className="audio-meter"><span style={{ width: `${audioLevel}%` }} /></div><small>Habla durante unos segundos · nivel {audioLevel}%</small><ul className="calibration-checks"><li className={cameraReady ? "ready" : ""}>{cameraReady ? "✓" : "○"} Cámara funcionando</li><li className={microphoneReady ? "ready" : ""}>{microphoneReady ? "✓" : "○"} Nivel de audio suficiente</li><li className={visionReady ? "ready" : ""}>{visionReady ? "✓" : "○"} Persona detectable con MediaPipe</li></ul><button className="button" type="button" disabled={checking} onClick={() => void calibrate()}>{checking ? "Inicializando…" : cameraReady ? "Volver a comprobar" : "Comprobar dispositivos"}</button><button className="button button-primary" type="button" disabled={!cameraReady || !microphoneReady || !visionReady || saving} onClick={() => void confirm()}>{saving ? "Guardando…" : "Confirmar calibración"}</button></section></div></section></main>;
}
