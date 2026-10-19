"use client";

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { Shirt } from "lucide-react";
import { apiRequest } from "@/lib/api";
import {readSessionPreferences,saveSessionPreferences} from "./session-preferences";

export type AppearanceResult = {
  person_present: boolean; upper_body_visible: boolean;
  jacket: boolean | null; collared_shirt: boolean | null; tie: boolean | null;
  upper_body_covered?: boolean | null;
  presentation: "formal" | "casual" | "incomplete" | "uncertain"; confidence: number; feedback: string;
};

export type AppearanceStatus = {state:"off"|"waiting"|"analyzing"|"result"|"error";result:AppearanceResult|null;message:string;time:string};
export function AppearanceFeedback({ simulationId, videoRef, available, onStatus, torsoInFrame, compact = false }: {
  simulationId: string; videoRef: RefObject<HTMLVideoElement | null>; available: boolean; onStatus?: (status:AppearanceStatus)=>void;torsoInFrame:boolean; compact?:boolean;
}) {
  const [result, setResult] = useState<AppearanceResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [time, setTime] = useState("");
  const [continuous, setContinuous] = useState(process.env.NEXT_PUBLIC_APPEARANCE_AUTO !== "false");
  useEffect(() => {
    const saved = readSessionPreferences(simulationId).appearanceContinuous;
    if (saved === undefined) return;
    const timer = setTimeout(() => setContinuous(saved), 0);
    return () => clearTimeout(timer);
  }, [simulationId]);
  const configuredInterval=Number(process.env.NEXT_PUBLIC_APPEARANCE_INTERVAL_SECONDS ?? 10);
  const intervalSeconds=Number.isFinite(configuredInterval) ? Math.max(10,Math.min(300,configuredInterval)) : 10;
  const request = useRef<AbortController | null>(null);
  const currentTorso=useRef(torsoInFrame);
  useEffect(()=>{currentTorso.current=torsoInFrame;},[torsoInFrame]);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (available && continuous) return;
    request.current?.abort();
    const reset = setTimeout(() => { setResult(null); setTime(""); setError(""); }, 0);
    return () => clearTimeout(reset);
  }, [available,continuous]);

  const analyze = useCallback(async () => {
    const video = videoRef.current;
    if (!available || !video || !video.videoWidth || request.current) return;
    setBusy(true); setError("");
    const controller = new AbortController(); request.current = controller;
    let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try {
      const canvas = document.createElement("canvas");
      const scale=Math.min(640/video.videoWidth,640/video.videoHeight,1);
      canvas.width = Math.round(video.videoWidth*scale);
      canvas.height = Math.round(video.videoHeight*scale);
      const context = canvas.getContext("2d");
      if (!context) throw new Error("No pudimos capturar el encuadre.");
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const image = canvas.toDataURL("image/jpeg", .75).split(",")[1];
      canvas.width = canvas.height = 0;
      const response = await apiRequest<AppearanceResult>(`/simulations/${simulationId}/appearance`, {
        method: "POST", body: JSON.stringify({image_base64: image,torso_in_frame:currentTorso.current}), signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      setResult(response); setTime(new Date().toLocaleTimeString("es", {hour:"2-digit", minute:"2-digit"}));
    } catch (err) {
      if (!controller.signal.aborted || timedOut) {setResult(null);setTime("");setError(timedOut ? "La revisión tardó demasiado. La detección local sigue activa; puedes reintentar." : err instanceof Error ? err.message : "No se pudo revisar la vestimenta.");}
    } finally {
      clearTimeout(timeout);
      if (request.current === controller) { request.current = null; setBusy(false); }
    }
  }, [available, simulationId, videoRef]);

  useEffect(() => {
    if (!continuous || !available) return;
    const first=setTimeout(() => void analyze(),500);
    const timer = setInterval(() => void analyze(), intervalSeconds * 1000);
    return () => {clearTimeout(first);clearInterval(timer);};
  }, [continuous, available, analyze, intervalSeconds]);

  useEffect(()=>{
    const state=busy ? "analyzing" : !available ? (!continuous ? "off" : "waiting") : error ? "error" : result ? "result" : !continuous ? "off" : "waiting";
    onStatus?.({state,result:available?result:null,message:error,time});
  },[continuous,available,busy,error,result,time,onStatus]);
  const garment = (value: boolean | null) => value === null ? "No concluyente" : value ? "Visible" : "No visible";
  const resultDetails = result && <div role="status"><p>Última revisión · {time}</p><strong>{result.presentation === "formal" ? "Presentación formal observada" : result.presentation === "casual" ? "Ropa casual: revisa tu presentación" : result.presentation === "incomplete" ? "Falta una prenda en el torso" : "No se puede verificar la ropa"}</strong><dl><div><dt>Saco / blazer</dt><dd>{garment(result.jacket)}</dd></div><div><dt>Camisa con cuello</dt><dd>{garment(result.collared_shirt)}</dd></div><div><dt>Corbata</dt><dd>{garment(result.tie)}</dd></div></dl><p>{result.feedback}</p></div>;
  return <section className="room-dress-card">
    <strong><Shirt size={15} /> Vestimenta para la defensa</strong>
    <p>Revisión automática cada {intervalSeconds} segundos mientras estás en cámara. Envía una captura a Gemini y no la guarda en Socratia. Puedes apagarla aquí.</p>
    <button className="room-text-button" disabled={!available || busy} onClick={() => void analyze()}>{busy ? "Revisando prendas…" : "Revisar vestimenta"}</button>
    <label className="room-dress-continuous"><input type="checkbox" checked={continuous} disabled={!available && !continuous} onChange={event => { setContinuous(event.target.checked); saveSessionPreferences(simulationId,{appearanceContinuous:event.target.checked}); }} /> Revisión automática de ropa (Gemini)</label>
    {!continuous && <p>Revisión de vestimenta apagada.</p>}
    {continuous && !available && <p>Esperando un único rostro visible y una cámara activa.</p>}
    {error && <p role="alert">{error}</p>}
    {compact ? <details className="room-appearance-details"><summary>Ver detalle de prendas{time ? ` · ${time}` : ""}</summary>{resultDetails || <p>Aún no hay una revisión disponible.</p>}</details> : resultDetails}
  </section>;
}
