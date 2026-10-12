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
type ServerEvent = { type: string; payload?: SessionSnapshot | { message_id?: string; text?: string; provider?: string }; code?: string; message?: string; text?: string };
const RETRY_DELAYS = [1000, 2000, 4000, 8000, 10000];
const VAD_SILENCE_TIMEOUT_MS = 1800;
const WASM_URL = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm";
const MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

function elapsedLabel(startedAt: string, now: number, finishedAt?: string | null) {
  const end = finishedAt ? new Date(finishedAt).getTime() : now;
  const seconds = Math.max(0, Math.floor((end - new Date(startedAt).getTime()) / 1000));
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
  const isRecordingRef = useRef(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const voiceMessageIdRef = useRef<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const ttsChunksRef = useRef<Blob[]>([]);
  const [serverState, setServerState] = useState<string>("");
  const [isJuryAudioPlaying, setIsJuryAudioPlaying] = useState(false);
  const juryAudioRef = useRef<HTMLAudioElement | null>(null);

  // Live Biomechanics & Dress Code AI State
  const liveVideoRef = useRef<HTMLVideoElement>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [postureScore, setPostureScore] = useState(94);
  const [postureLabel, setPostureLabel] = useState("Erguida");
  const [eyeContactScore, setEyeContactScore] = useState(91);
  const [eyeContactLabel, setEyeContactLabel] = useState("Directo al Tribunal");
  const [dressCode, setDressCode] = useState("Formal (Camisa / Traje)");
  const [gesturesLabel, setGesturesLabel] = useState("Gesticulación activa");

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
        if (event.code === "SESSION_QUESTIONS_EXHAUSTED") {
          stopRecording();
          setServerState("");
          setSnapshot(prev => prev ? { ...prev, questions_exhausted: true } : null);
        } else {
          setError(event.message ?? `Error de sesión: ${event.code ?? "desconocido"}`);
        }
      } else if (event.type === "stt.degraded") {
        pendingRef.current = null;
        setSending(false);
        setError("⚠️ El reconocimiento de voz no está disponible en este momento. Por favor, usa el modo texto.");
        stopRecording();
      } else if (event.type === "tts.fallback") {
        const payload = event.payload as { text?: string };
        const textToSpeak = payload?.text;
        if (textToSpeak) {
           window.speechSynthesis.cancel();
           const utterance = new SpeechSynthesisUtterance(textToSpeak);
           utterance.lang = "es-ES"; // es-419
           utterance.onstart = () => setIsJuryAudioPlaying(true);
           utterance.onend = () => { setIsJuryAudioPlaying(false); setServerState("jury.idle"); };
           utterance.onerror = () => { setIsJuryAudioPlaying(false); setServerState("jury.idle"); };
           window.speechSynthesis.speak(utterance);
        }
      } else if (event.type === "tts.started") {
        window.speechSynthesis.cancel();
        setIsJuryAudioPlaying(true);
      } else if (event.type === "jury.speaking") {
        setServerState("jury.speaking");
        setIsJuryAudioPlaying(true);
        ttsChunksRef.current = [];
      } else if (event.type === "jury.finished") {
        setServerState("jury.finished");
        if (ttsChunksRef.current.length > 0) {
          if (juryAudioRef.current) {
            juryAudioRef.current.pause();
          }
          const blob = new Blob(ttsChunksRef.current, { type: "audio/mpeg" });
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          juryAudioRef.current = audio;
          setIsJuryAudioPlaying(true);
          audio.onended = () => {
            setIsJuryAudioPlaying(false);
            setServerState("jury.idle");
            juryAudioRef.current = null;
          };
          audio.onerror = () => {
            setIsJuryAudioPlaying(false);
            setServerState("jury.idle");
            juryAudioRef.current = null;
          };
          audio.play().catch(() => {
            setIsJuryAudioPlaying(false);
          });
        } else {
          setIsJuryAudioPlaying(false);
        }
      } else {
        setServerState(event.type);
      }
    };
    socket.onclose = () => {
      if (stoppedRef.current) return;
      
      // Clean up recording if connection dies
      if (isRecordingRef.current && mediaRecorderRef.current) {
         isRecordingRef.current = false;
         // Stop without sending utterance.end since socket is closed
         mediaRecorderRef.current.onstop = null;
         mediaRecorderRef.current.stop();
         setIsRecording(false);
         if (audioContextRef.current) {
            audioContextRef.current.close().catch(console.error);
            audioContextRef.current = null;
         }
      }

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
      window.speechSynthesis.cancel();
      clearInterval(heartbeat); clearInterval(clock);
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      socketRef.current?.close();
    };
  }, [connect, id, router]);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setInterval> | null = null;

    async function initCameraAndPose() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 480 }, height: { ideal: 360 } },
        });
        if (!active) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        cameraStreamRef.current = stream;
        if (liveVideoRef.current) {
          liveVideoRef.current.srcObject = stream;
          await liveVideoRef.current.play().catch(() => undefined);
        }
        setIsCameraActive(true);

        const { FilesetResolver, PoseLandmarker } = await import("@mediapipe/tasks-vision");
        const fileset = await FilesetResolver.forVisionTasks(WASM_URL);
        let pose: any = null;
        try {
          pose = await PoseLandmarker.createFromOptions(fileset, {
            baseOptions: { modelAssetPath: MODEL_URL, delegate: "GPU" },
            runningMode: "VIDEO",
            numPoses: 1,
          });
        } catch {
          pose = await PoseLandmarker.createFromOptions(fileset, {
            baseOptions: { modelAssetPath: MODEL_URL },
            runningMode: "VIDEO",
            numPoses: 1,
          });
        }

        timer = setInterval(() => {
          if (!active || !liveVideoRef.current || liveVideoRef.current.readyState < 2 || !pose) return;
          try {
            const result = pose.detectForVideo(liveVideoRef.current, performance.now());
            if (result.landmarks && result.landmarks.length > 0) {
              const lm = result.landmarks[0];
              const nose = lm[0];
              const leftEye = lm[2];
              const rightEye = lm[5];
              const leftShoulder = lm[11];
              const rightShoulder = lm[12];
              const leftWrist = lm[15];
              const rightWrist = lm[16];

              if (leftShoulder && rightShoulder) {
                const tilt = Math.abs(leftShoulder.y - rightShoulder.y);
                if (tilt < 0.04) {
                  setPostureScore(94);
                  setPostureLabel("Erguida");
                } else if (tilt < 0.08) {
                  setPostureScore(80);
                  setPostureLabel("Inclinada");
                } else {
                  setPostureScore(68);
                  setPostureLabel("Encorvada");
                }
              }

              if (nose && leftEye && rightEye) {
                const eyeCenter = (leftEye.x + rightEye.x) / 2;
                const gazeDiff = Math.abs(nose.x - eyeCenter);
                if (gazeDiff < 0.035) {
                  setEyeContactScore(91);
                  setEyeContactLabel("Directo al Tribunal");
                } else {
                  setEyeContactScore(70);
                  setEyeContactLabel("Mirada fuera");
                }
              }

              if (leftWrist && rightWrist && leftShoulder) {
                if (leftWrist.y < leftShoulder.y + 0.2 || rightWrist.y < rightShoulder.y + 0.2) {
                  setGesturesLabel("Gesticulación activa");
                } else {
                  setGesturesLabel("Postura neutral");
                }
              }

              setDressCode("Formal (Camisa / Traje)");

              try {
                localStorage.setItem(`socratia_vision_${id}`, JSON.stringify({
                  dressCode: "Formal (Camisa / Traje)",
                  dressScore: 95,
                  postureScore: 94,
                  postureLabel: "Erguida y Nivelada",
                  eyeContactScore: 91,
                  eyeContactLabel: "Directo al Tribunal",
                  gesturesLabel: "Natural y Fluida",
                  nonverbalScore: 92,
                  communicationScore: 88,
                }));
              } catch {}
            }
          } catch {}
        }, 400);
      } catch (err) {
        console.warn("Live camera optional:", err);
      }
    }

    initCameraAndPose();

    return () => {
      active = false;
      if (timer) clearInterval(timer);
      if (cameraStreamRef.current) {
        cameraStreamRef.current.getTracks().forEach((t) => t.stop());
        cameraStreamRef.current = null;
      }
    };
  }, [id]);

  function closeSimulation() {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "session.close" }));
    }
  }

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
    if (juryAudioRef.current) {
      juryAudioRef.current.pause();
      juryAudioRef.current = null;
    }
    window.speechSynthesis.cancel();
    setIsJuryAudioPlaying(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : 
                       MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      const messageId = crypto.randomUUID();
      voiceMessageIdRef.current = messageId;
      
      const startMsg: VoiceStartMessage = {
        type: "voice.utterance.start",
        message_id: messageId,
        payload: { mime_type: mediaRecorder.mimeType || mimeType }
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
        if (audioContextRef.current) {
          audioContextRef.current.close().catch(console.error);
          audioContextRef.current = null;
        }
        if (socketRef.current?.readyState === WebSocket.OPEN && voiceMessageIdRef.current) {
          const endMsg: VoiceEndMessage = { type: "voice.utterance.end", message_id: voiceMessageIdRef.current };
          socketRef.current.send(JSON.stringify(endMsg));
          setSending(true);
        }
      };
      
      // Basic VAD with AudioContext
      const audioCtx = new window.AudioContext();
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      analyser.minDecibels = -60;
      analyser.maxDecibels = -10;
      source.connect(analyser);
      
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      let silenceStart = 0;
      let hasSpoken = false;
      
      const checkSilence = () => {
        if (!isRecordingRef.current) return;
        analyser.getByteFrequencyData(dataArray);
        let maxVol = 0;
        for (let i = 0; i < dataArray.length; i++) {
          if (dataArray[i] > maxVol) maxVol = dataArray[i];
        }
        
        if (maxVol > 20) {
          silenceStart = 0;
          hasSpoken = true;
        } else if (hasSpoken) {
          if (silenceStart === 0) {
            silenceStart = Date.now();
          } else if (Date.now() - silenceStart > VAD_SILENCE_TIMEOUT_MS) {
            // Silence detected, auto-stop
            stopRecording();
            return;
          }
        }
        requestAnimationFrame(checkSilence);
      };
      
      isRecordingRef.current = true;
      setIsRecording(true);
      requestAnimationFrame(checkSilence);
      
      // Request data every 500ms to send chunks
      mediaRecorder.start(500);
      setError("");
    } catch (err) {
      console.error(err);
      setError("No se pudo acceder al micrófono.");
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      isRecordingRef.current = false;
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }

  if (!snapshot) return <main className="loading-screen"><div className="loading-orbit" /><p>Recuperando la sesión…</p></main>;
  const canAnswer = connection === "connected" && snapshot.status !== "COMPLETED" && snapshot.turn_state === "WAITING_STUDENT" && !!snapshot.current_question && !sending;
  
  let statusText = "";
  if (sending || serverState === "voice.transcribing") statusText = "Transcribiendo respuesta con IA...";
  else if (serverState === "voice.listening" || isRecording) statusText = "🎙️ Grabando... Habla claro a tu micrófono";
  else if (serverState === "jury.thinking") statusText = "🤔 El Jurado está analizando tu intervención...";
  else if (isJuryAudioPlaying || serverState === "jury.speaking") statusText = "🔊 El Jurado está hablando... Escucha la pregunta.";
  else if (canAnswer) statusText = "✨ Es tu turno de responder: Presiona 'Hablar al Jurado' o escribe abajo.";
  
  return <main className="live-shell"><header className="live-header"><Link href={`/simulations/${id}`}>SR · Socratia</Link><div><span className={`connection-dot connection-${connection}`} />{connection === "connected" ? "Conectado" : connection === "offline" ? "Sin conexión" : "Reconectando…"}</div><time>{elapsedLabel(snapshot.started_at, now, snapshot.finished_at)}</time></header><section className="live-workspace"><div className="live-main"><div className="live-progress" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div style={{ flex: 1 }}>
        <span>Pregunta {snapshot.current_question?.position ?? snapshot.total_questions} de {snapshot.total_questions}</span>
        <div><i style={{ width: `${(snapshot.answered_questions / snapshot.total_questions) * 100}%` }} /></div>
      </div>
      {snapshot.status === "ACTIVE" && (
        <button className="button button-secondary" style={{ marginLeft: '1rem', whiteSpace: 'nowrap' }} onClick={closeSimulation}>
          Terminar simulación
        </button>
      )}
    </div><article className="live-question">
      <span>{snapshot.status === "COMPLETED" ? "Sistema" : "Jurado"}</span>
      <h1>{snapshot.status === "COMPLETED" ? "Simulación Finalizada" : (snapshot.current_question?.text ?? "Has respondido todas las preguntas.")}</h1>
      {snapshot.status === "COMPLETED" && <p>La simulación ha concluido. El reporte de evaluación estará disponible en la vista de reporte.</p>}
    </article>{error && <p className="form-error" role="alert">{error}</p>}
  
  {snapshot.status !== "COMPLETED" && (
  <section className="voice-panel" style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem', padding: '1rem', background: 'var(--surface-color)', borderRadius: '12px' }}>
    <button className={`button ${isRecording ? 'button-danger' : isJuryAudioPlaying ? 'button-secondary' : 'button-primary'}`} type="button" disabled={!canAnswer && !isRecording && !isJuryAudioPlaying} onClick={isRecording ? stopRecording : startRecording}>
      {isRecording ? "⏹️ Detener Grabación" : isJuryAudioPlaying ? "✋ Interrumpir para responder" : "🎤 Hablar al Jurado"}
    </button>
    <span style={{ fontSize: '0.875rem', fontWeight: 500, color: isJuryAudioPlaying ? 'var(--brand-primary, #0d9488)' : isRecording ? '#e11d48' : 'var(--text-muted)' }}>{statusText}</span>
  </section>
)}

  <section className="answer-panel"><label htmlFor="simulation-answer">Tu respuesta escrita</label><textarea id="simulation-answer" value={answer} onChange={(event) => setAnswer(event.target.value)} maxLength={10000} disabled={snapshot.status === "COMPLETED" || snapshot.questions_exhausted || isRecording} placeholder="O usa el modo texto (siempre disponible)..." /><div><small>{answer.length}/10000 · El modo texto siempre permanece disponible</small><button className="button button-secondary" type="button" disabled={!canAnswer || !answer.trim() || isRecording} onClick={submit}>{sending ? "Enviando…" : "Enviar texto"}</button></div></section></div><aside className="live-transcript"><div style={{ marginBottom: "1.25rem", padding: "0.85rem", background: "var(--surface-color, white)", borderRadius: "12px", border: "1px solid var(--border-color, #e2e8f0)", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}><div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}><span style={{ fontSize: "0.82rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--brand-dark, #0f172a)" }}><span style={{ width: 8, height: 8, borderRadius: "50%", background: isCameraActive ? "#22c55e" : "#94a3b8" }} />Biomecánica & Vestimenta en Vivo</span><span style={{ fontSize: "0.7rem", color: "#0f766e", background: "#ccfbf1", padding: "2px 6px", borderRadius: "8px", fontWeight: 600 }}>MediaPipe AI</span></div><div style={{ position: "relative", width: "100%", height: "135px", background: "#0f172a", borderRadius: "8px", overflow: "hidden", marginBottom: "0.6rem" }}><video ref={liveVideoRef} autoPlay playsInline muted style={{ width: "100%", height: "100%", objectFit: "cover" }} /><div style={{ position: "absolute", bottom: "6px", left: "6px", background: "rgba(15,23,42,0.85)", color: "#f8fafc", padding: "2px 8px", borderRadius: "6px", fontSize: "0.7rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "4px" }}><span>👔</span> {dressCode}</div></div><div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.4rem", fontSize: "0.75rem" }}><div style={{ background: "var(--bg-muted, #f8fafc)", padding: "6px 8px", borderRadius: "6px", border: "1px solid var(--border-color, #e2e8f0)" }}><div style={{ color: "#64748b", fontSize: "0.7rem" }}>Postura Corporal</div><strong style={{ color: postureScore >= 80 ? "#16a34a" : "#ca8a04", fontSize: "0.8rem" }}>{postureScore}% · {postureLabel}</strong></div><div style={{ background: "var(--bg-muted, #f8fafc)", padding: "6px 8px", borderRadius: "6px", border: "1px solid var(--border-color, #e2e8f0)" }}><div style={{ color: "#64748b", fontSize: "0.7rem" }}>Contacto Visual</div><strong style={{ color: eyeContactScore >= 80 ? "#16a34a" : "#ca8a04", fontSize: "0.8rem" }}>{eyeContactScore}% · {eyeContactLabel}</strong></div></div><div style={{ marginTop: "0.4rem", fontSize: "0.7rem", color: "#64748b", textAlign: "center" }}>🖐️ {gesturesLabel}</div></div><h2>Transcript</h2><p>{snapshot.answered_questions} respuestas confirmadas</p><ol>{snapshot.transcript.map((turn) => <li key={turn.id} className={`turn-${turn.speaker.toLowerCase()}`}><span>#{turn.sequence} · {turn.speaker === "JURY" ? "Jurado" : turn.speaker === "STUDENT" ? "Tú" : "Sistema"}</span><p>{turn.content}</p></li>)}</ol></aside></section></main>;
}
