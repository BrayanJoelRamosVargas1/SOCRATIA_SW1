"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { getSimulationSession } from "@/features/simulations/api";
import { simulationWebSocketUrl } from "@/lib/config";
import type { SessionSnapshot } from "@/types/simulation";

type ConnectionState = "connecting" | "connected" | "reconnecting" | "offline";
type PendingAnswer = { type: "answer.submit"; message_id: string; payload: { question_id: string; content: string } };
type VoiceStartMessage = { type: "voice.utterance.start"; message_id: string; payload: { mime_type: string } };
type VoiceEndMessage = { type: "voice.utterance.end"; message_id: string };
type ServerEvent = { type: string; payload?: SessionSnapshot | { message_id?: string }; code?: string; message?: string; text?: string };
const RETRY_DELAYS = [1000, 2000, 4000, 8000, 10000];

function elapsedLabel(startedAt: string, now: number) {
  const seconds = Math.max(0, Math.floor((now - new Date(startedAt).getTime()) / 1000));
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

export function SimulationLivePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [answer, setAnswer] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [now, setNow] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const pendingRef = useRef<PendingAnswer | null>(null);
  const retryRef = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stoppedRef = useRef(false);
  const connectRef = useRef<() => void>(() => undefined);
  
  // Voice recording state
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const voiceMessageIdRef = useRef<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const ttsChunksRef = useRef<Blob[]>([]);
  const [serverState, setServerState] = useState<string>("");

  const connect = useCallback(() => {
    if (stoppedRef.current) return;
    setConnection(retryRef.current ? "reconnecting" : "connecting");
    const socket = new WebSocket(simulationWebSocketUrl(id));
    socketRef.current = socket;
    socket.onopen = () => {
      retryRef.current = 0;
      setConnection("connected");
      setError("");
      if (pendingRef.current) socket.send(JSON.stringify(pendingRef.current));
    };
    socket.onmessage = (message) => {
      if (message.data instanceof Blob) {
        ttsChunksRef.current.push(message.data);
        return;
      }
      const event = JSON.parse(message.data) as ServerEvent;
      if (event.type === "session.snapshot" || event.type === "session.state") {
        setSnapshot(event.payload as SessionSnapshot);
      } else if (event.type === "answer.accepted") {
        const accepted = event.payload as { message_id?: string };
        if (pendingRef.current?.message_id === accepted.message_id) {
          pendingRef.current = null;
          setSending(false);
          setAnswer("");
        }
      } else if (event.type === "voice.transcription") {
        setSending(false); // Transcribed
      } else if (event.type === "error") {
        pendingRef.current = null;
        setSending(false);
        setError(event.message ?? `Error de sesión: ${event.code ?? "desconocido"}`);
      } else if (event.type === "jury.speaking") {
        setServerState("jury.speaking");
        ttsChunksRef.current = [];
      } else if (event.type === "jury.finished") {
        setServerState("jury.finished");
        if (ttsChunksRef.current.length > 0) {
          const blob = new Blob(ttsChunksRef.current, { type: "audio/mpeg" });
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.play().catch(console.error);
        } else {
          // Fallback to speechSynthesis if no audio bytes were received
          const textToSpeak = snapshot?.current_question?.text;
          if (textToSpeak) {
             const utterance = new SpeechSynthesisUtterance(textToSpeak);
             utterance.lang = "es-ES";
             window.speechSynthesis.speak(utterance);
          }
        }
      } else {
        setServerState(event.type);
      }
    };
    socket.onclose = () => {
      if (stoppedRef.current) return;
      setConnection("reconnecting");
      const delay = RETRY_DELAYS[Math.min(retryRef.current, RETRY_DELAYS.length - 1)];
      retryRef.current += 1;
      reconnectTimer.current = setTimeout(() => connectRef.current(), delay);
    };
    socket.onerror = () => socket.close();
  }, [id]);

  useEffect(() => {
    stoppedRef.current = false;
    connectRef.current = connect;
    getSimulationSession(id).then(setSnapshot).catch(() => router.replace(`/simulations/${id}`));
    connect();
    const heartbeat = setInterval(() => {
      if (socketRef.current?.readyState === WebSocket.OPEN) socketRef.current.send(JSON.stringify({ type: "heartbeat" }));
    }, 25000);
    const clock = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      stoppedRef.current = true;
      setConnection("offline");
      clearInterval(heartbeat); clearInterval(clock);
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      socketRef.current?.close();
    };
  }, [connect, id, router]);

  function submit() {
    const content = answer.trim();
    if (!content || !snapshot?.current_question || pendingRef.current) return;
    const message: PendingAnswer = { type: "answer.submit", message_id: crypto.randomUUID(), payload: { question_id: snapshot.current_question.id, content } };
    pendingRef.current = message;
    setSending(true);
    setError("");
    if (socketRef.current?.readyState === WebSocket.OPEN) socketRef.current.send(JSON.stringify(message));
    else setConnection("reconnecting");
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      const messageId = crypto.randomUUID();
      voiceMessageIdRef.current = messageId;
      
      const startMsg: VoiceStartMessage = {
        type: "voice.utterance.start",
        message_id: messageId,
        payload: { mime_type: mimeType }
      };
      
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify(startMsg));
      }
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0 && socketRef.current?.readyState === WebSocket.OPEN) {
          socketRef.current.send(e.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop());
        if (socketRef.current?.readyState === WebSocket.OPEN && voiceMessageIdRef.current) {
          const endMsg: VoiceEndMessage = { type: "voice.utterance.end", message_id: voiceMessageIdRef.current };
          socketRef.current.send(JSON.stringify(endMsg));
          setSending(true);
        }
      };
      
      // Request data every 500ms to send chunks
      mediaRecorder.start(500);
      setIsRecording(true);
      setError("");
    } catch (err) {
      console.error(err);
      setError("No se pudo acceder al micrófono.");
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }

  if (!snapshot) return <main className="loading-screen"><div className="loading-orbit" /><p>Recuperando la sesión…</p></main>;
  const canAnswer = connection === "connected" && snapshot.turn_state === "WAITING_STUDENT" && !!snapshot.current_question && !sending;
  
  let statusText = "";
  if (sending || serverState === "voice.transcribing") statusText = "Transcribiendo/Enviando...";
  else if (serverState === "voice.listening" || isRecording) statusText = "Te escuchamos...";
  else if (serverState === "jury.thinking") statusText = "Jurado pensando...";
  else if (serverState === "jury.speaking") statusText = "Jurado hablando...";
  
  return <main className="live-shell"><header className="live-header"><Link href={`/simulations/${id}`}>SR · Socratia</Link><div><span className={`connection-dot connection-${connection}`} />{connection === "connected" ? "Conectado" : connection === "offline" ? "Sin conexión" : "Reconectando…"}</div><time>{elapsedLabel(snapshot.started_at, now)}</time></header><section className="live-workspace"><div className="live-main"><div className="live-progress"><span>Pregunta {snapshot.current_question?.position ?? snapshot.total_questions} de {snapshot.total_questions}</span><div><i style={{ width: `${(snapshot.answered_questions / snapshot.total_questions) * 100}%` }} /></div></div><article className="live-question"><span>Jurado</span><h1>{snapshot.current_question?.text ?? "Has respondido las 12 preguntas del banco."}</h1>{snapshot.questions_exhausted && <p>La sesión sigue activa. El cierre y las preguntas de seguimiento se incorporarán en CU19.</p>}</article>{error && <p className="form-error" role="alert">{error}</p>}
  
  <section className="voice-panel" style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem', padding: '1rem', background: 'var(--surface-color)', borderRadius: '12px' }}>
    <button className={`button ${isRecording ? 'button-danger' : 'button-primary'}`} type="button" disabled={!canAnswer && !isRecording} onClick={isRecording ? stopRecording : startRecording}>
      {isRecording ? "⏹️ Detener Grabación" : "🎤 Hablar al Jurado"}
    </button>
    <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{statusText}</span>
  </section>

  <section className="answer-panel"><label htmlFor="simulation-answer">Tu respuesta escrita</label><textarea id="simulation-answer" value={answer} onChange={(event) => setAnswer(event.target.value)} maxLength={10000} disabled={snapshot.questions_exhausted || isRecording} placeholder="O usa el modo texto (siempre disponible)..." /><div><small>{answer.length}/10000 · El modo texto siempre permanece disponible</small><button className="button button-secondary" type="button" disabled={!canAnswer || !answer.trim() || isRecording} onClick={submit}>{sending ? "Enviando…" : "Enviar texto"}</button></div></section></div><aside className="live-transcript"><h2>Transcript</h2><p>{snapshot.answered_questions} respuestas confirmadas</p><ol>{snapshot.transcript.map((turn) => <li key={turn.id} className={`turn-${turn.speaker.toLowerCase()}`}><span>#{turn.sequence} · {turn.speaker === "JURY" ? "Jurado" : turn.speaker === "STUDENT" ? "Tú" : "Sistema"}</span><p>{turn.content}</p></li>)}</ol></aside></section></main>;
}
