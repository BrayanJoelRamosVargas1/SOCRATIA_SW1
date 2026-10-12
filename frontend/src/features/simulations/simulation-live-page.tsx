"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { getSimulationSession } from "@/features/simulations/api";
import { simulationWebSocketUrl } from "@/lib/config";
import type { SessionSnapshot } from "@/types/simulation";

import { TalkingJuryAvatar } from "./talking-jury-avatar";

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
  const [dressCode, setDressCode] = useState("Analizando vestimenta...");
  const [dressIsFormal, setDressIsFormal] = useState(true);
  const [gesturesLabel, setGesturesLabel] = useState("Gesticulación activa");

  // Reactive Tribunal Observations
  const [juryObservation, setJuryObservation] = useState<{
    type: "posture" | "dress" | "praise";
    message: string;
  } | null>(null);
  const observationTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const badPostureStartRef = useRef<number | null>(null);
  const hadBadPostureRef = useRef<boolean>(false);

  const speakCurrentQuestion = useCallback(() => {
    if (!snapshot?.current_question) return;
    window.speechSynthesis.cancel();
    if (juryAudioRef.current) {
      juryAudioRef.current.pause();
      juryAudioRef.current = null;
    }
    const textToSpeak = snapshot.current_question.text;
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = "es-ES";
    utterance.rate = 1.0;
    utterance.onstart = () => {
      setIsJuryAudioPlaying(true);
      setServerState("jury.speaking");
    };
    utterance.onend = () => {
      setIsJuryAudioPlaying(false);
      setServerState("jury.idle");
    };
    utterance.onerror = () => {
      setIsJuryAudioPlaying(false);
      setServerState("jury.idle");
    };
    window.speechSynthesis.speak(utterance);
  }, [snapshot?.current_question]);

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
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
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

        const offscreenCanvas = document.createElement("canvas");
        offscreenCanvas.width = 160;
        offscreenCanvas.height = 120;
        const offscreenCtx = offscreenCanvas.getContext("2d", { willReadFrequently: true });

        timer = setInterval(() => {
          if (!active || !liveVideoRef.current || liveVideoRef.current.readyState < 2 || !pose) return;
          try {
            const video = liveVideoRef.current;
            const result = pose.detectForVideo(video, performance.now());
            if (result.landmarks && result.landmarks.length > 0) {
              const lm = result.landmarks[0];
              const nose = lm[0];
              const leftEye = lm[2];
              const rightEye = lm[5];
              const leftShoulder = lm[11];
              const rightShoulder = lm[12];
              const leftWrist = lm[15];
              const rightWrist = lm[16];

              // 1. Dynamic Posture Calculation
              let computedPosture = 92;
              let postureText = "Erguida";
              if (leftShoulder && rightShoulder && nose) {
                const tilt = Math.abs(leftShoulder.y - rightShoulder.y);
                const midShoulderX = (leftShoulder.x + rightShoulder.x) / 2;
                const neckAlignment = Math.abs(nose.x - midShoulderX);
                computedPosture = Math.max(35, Math.min(98, Math.round(100 - (tilt * 420 + neckAlignment * 340))));
                if (computedPosture >= 85) postureText = "Erguida";
                else if (computedPosture >= 70) postureText = "Inclinada";
                else postureText = "Encorvada";
                setPostureScore(computedPosture);
                setPostureLabel(postureText);
              }

              // 2. Dynamic Eye Contact Calculation
              let computedEye = 90;
              let eyeText = "Directo al Tribunal";
              if (nose && leftEye && rightEye) {
                const eyeCenter = (leftEye.x + rightEye.x) / 2;
                const gazeDiff = Math.abs(nose.x - eyeCenter);
                computedEye = Math.max(30, Math.min(98, Math.round(100 - gazeDiff * 650)));
                if (computedEye >= 82) eyeText = "Directo al Tribunal";
                else if (computedEye >= 65) eyeText = "Mirada Periférica";
                else eyeText = "Mirada Desviada";
                setEyeContactScore(computedEye);
                setEyeContactLabel(eyeText);
              }

              // 3. Gestures
              let gestureText = "Postura neutral";
              if (leftWrist && rightWrist && leftShoulder && rightShoulder) {
                if (leftWrist.y < leftShoulder.y + 0.15 || rightWrist.y < rightShoulder.y + 0.15) {
                  gestureText = "Gesticulación activa";
                }
                setGesturesLabel(gestureText);
              }

              // 4. Real Dynamic Dress Code Pixel Sampling
              let detectedDress = "👔 Formal (Camisa / Traje)";
              let detectedScore = 95;
              let isFormal = true;

              if (offscreenCtx && video.videoWidth > 0 && leftShoulder && rightShoulder && nose) {
                offscreenCtx.drawImage(video, 0, 0, 160, 120);

                const midShoulderX = (leftShoulder.x + rightShoulder.x) / 2;
                const shoulderDist = Math.abs(rightShoulder.x - leftShoulder.x);

                // Sample upper chest and neckline between chin and chest
                const roiTopNorm = Math.max(0, Math.min(0.9, nose.y + (leftShoulder.y - nose.y) * 0.5));
                const roiBottomNorm = Math.max(0.1, Math.min(1.0, leftShoulder.y + shoulderDist * 0.45));
                const roiLeftNorm = Math.max(0, Math.min(0.9, midShoulderX - shoulderDist * 0.28));
                const roiRightNorm = Math.max(0.1, Math.min(1.0, midShoulderX + shoulderDist * 0.28));

                const rx = Math.floor(roiLeftNorm * 160);
                const ry = Math.floor(roiTopNorm * 120);
                const rw = Math.max(8, Math.floor((roiRightNorm - roiLeftNorm) * 160));
                const rh = Math.max(8, Math.floor((roiBottomNorm - roiTopNorm) * 120));

                const imgData = offscreenCtx.getImageData(rx, ry, Math.min(rw, 160 - rx), Math.min(rh, 120 - ry));
                const p = imgData.data;

                let skinCount = 0;
                let sampleCount = 0;
                let totalSat = 0;
                let totalBright = 0;

                for (let i = 0; i < p.length; i += 16) {
                  const r = p[i];
                  const g = p[i + 1];
                  const b = p[i + 2];
                  sampleCount++;

                  const mx = Math.max(r, g, b);
                  const mn = Math.min(r, g, b);
                  const delta = mx - mn;
                  const sat = mx === 0 ? 0 : delta / mx;
                  const br = (r + g + b) / 3;

                  totalSat += sat;
                  totalBright += br;

                  // Human skin detection heuristic
                  if (r > 80 && g > 35 && b > 20 && delta > 12 && r > g && r > b && (r - g) > 10) {
                    skinCount++;
                  }
                }

                const skinRatio = sampleCount > 0 ? skinCount / sampleCount : 0;
                const avgSat = sampleCount > 0 ? totalSat / sampleCount : 0;
                const avgBright = sampleCount > 0 ? totalBright / sampleCount : 0;

                if (skinRatio > 0.40) {
                  // Bare chest / shoulders / without shirt
                  detectedDress = "⚠️ Informal (Torso / Pecho descubierto)";
                  detectedScore = 40;
                  isFormal = false;
                } else if (avgSat > 0.38) {
                  // Saturated sports / casual t-shirt
                  detectedDress = "⚠️ Informal (Camiseta Casual / Deportiva)";
                  detectedScore = 65;
                  isFormal = false;
                } else if (avgBright < 80 && avgSat < 0.32) {
                  // Dark formal suit or dark button-down shirt
                  detectedDress = "👔 Formal (Saco / Camisa oscura)";
                  detectedScore = 95;
                  isFormal = true;
                } else if (avgBright > 165 && avgSat < 0.22) {
                  // White or light formal dress shirt
                  detectedDress = "👔 Formal (Camisa blanca / clara)";
                  detectedScore = 98;
                  isFormal = true;
                } else if (avgSat < 0.28) {
                  // Business formal neutral tones
                  detectedDress = "👔 Formal (Vestimenta formal de tribunal)";
                  detectedScore = 92;
                  isFormal = true;
                } else {
                  // Casual t-shirt
                  detectedDress = "⚠️ Informal (Camiseta casual detectada)";
                  detectedScore = 68;
                  isFormal = false;
                }

                setDressCode(detectedDress);
                setDressIsFormal(isFormal);
              }

              // 5. Reactive Tribunal Interventions on Posture and Protocol
              if (computedPosture < 65) {
                if (badPostureStartRef.current === null) {
                  badPostureStartRef.current = Date.now();
                } else if (Date.now() - badPostureStartRef.current > 3000 && !hadBadPostureRef.current) {
                  hadBadPostureRef.current = true;
                  setJuryObservation({
                    type: "posture",
                    message: "Postulante, le solicitamos mantener una postura erguida y la vista hacia el jurado examinador.",
                  });
                }
              } else if (computedPosture >= 85 && hadBadPostureRef.current) {
                hadBadPostureRef.current = false;
                badPostureStartRef.current = null;
                setJuryObservation({
                  type: "praise",
                  message: "Postura corregida adecuadamente. Puede continuar con su argumentación.",
                });
                if (observationTimeoutRef.current) clearTimeout(observationTimeoutRef.current);
                observationTimeoutRef.current = setTimeout(() => {
                  setJuryObservation(null);
                }, 4000);
              } else if (!isFormal && !hadBadPostureRef.current && !juryObservation) {
                setJuryObservation({
                  type: "dress",
                  message: "Observación de Protocolo: La defensa formal de grado requiere vestimenta formal (camisa o saco).",
                });
              }

              try {
                localStorage.setItem(`socratia_vision_${id}`, JSON.stringify({
                  dressCode: detectedDress,
                  dressScore: detectedScore,
                  isFormal: isFormal,
                  postureScore: computedPosture,
                  postureLabel: postureText,
                  eyeContactScore: computedEye,
                  eyeContactLabel: eyeText,
                  gesturesLabel: gestureText,
                  nonverbalScore: Math.round(computedPosture * 0.4 + computedEye * 0.35 + detectedScore * 0.25),
                  communicationScore: 88,
                }));
              } catch {}
            }
          } catch {}
        }, 350);
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
    </div>

    {/* Stage del Tribunal Académico con Avatar Animado y Lip-Sync */}
    <TalkingJuryAvatar
      juryName="Dr. Roberto Méndez"
      focusType="Presidente del Tribunal Examinador"
      isSpeaking={isJuryAudioPlaying || serverState === "jury.speaking"}
      isListening={canAnswer || isRecording}
      isThinking={serverState === "jury.thinking" || sending}
      observation={juryObservation}
      onSpeakQuestion={speakCurrentQuestion}
      canSpeakQuestion={snapshot.status !== "COMPLETED" && !!snapshot.current_question}
    />

    <article className="live-question">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
        <span>{snapshot.status === "COMPLETED" ? "Sistema" : "Pregunta Formulada por el Tribunal"}</span>
        {snapshot.status !== "COMPLETED" && snapshot.current_question && (
          <button
            type="button"
            className="button button-secondary"
            style={{ fontSize: "0.75rem", padding: "0.25rem 0.65rem", display: "flex", alignItems: "center", gap: "0.3rem" }}
            onClick={speakCurrentQuestion}
            disabled={isJuryAudioPlaying || isRecording}
          >
            {isJuryAudioPlaying ? "🔊 Reproduciendo..." : "🔊 Escuchar Pregunta"}
          </button>
        )}
      </div>
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

  <section className="answer-panel"><label htmlFor="simulation-answer">Tu respuesta escrita</label><textarea id="simulation-answer" value={answer} onChange={(event) => setAnswer(event.target.value)} maxLength={10000} disabled={snapshot.status === "COMPLETED" || snapshot.questions_exhausted || isRecording} placeholder="O usa el modo texto (siempre disponible)..." /><div><small>{answer.length}/10000 · El modo texto siempre permanece disponible</small><button className="button button-secondary" type="button" disabled={!canAnswer || !answer.trim() || isRecording} onClick={submit}>{sending ? "Enviando…" : "Enviar texto"}</button></div></section></div><aside className="live-transcript"><div style={{ marginBottom: "1.25rem", padding: "0.85rem", background: "var(--surface-color, white)", borderRadius: "12px", border: "1px solid var(--border-color, #e2e8f0)", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}><div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}><span style={{ fontSize: "0.82rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--brand-dark, #0f172a)" }}><span style={{ width: 8, height: 8, borderRadius: "50%", background: isCameraActive ? "#22c55e" : "#94a3b8" }} />Biomecánica & Vestimenta en Vivo</span><span style={{ fontSize: "0.7rem", color: "#0f766e", background: "#ccfbf1", padding: "2px 6px", borderRadius: "8px", fontWeight: 600 }}>MediaPipe AI</span></div><div style={{ position: "relative", width: "100%", height: "135px", background: "#0f172a", borderRadius: "8px", overflow: "hidden", marginBottom: "0.6rem" }}><video ref={liveVideoRef} autoPlay playsInline muted style={{ width: "100%", height: "100%", objectFit: "cover" }} /><div style={{ position: "absolute", bottom: "6px", left: "6px", right: "6px", background: dressIsFormal ? "rgba(15,23,42,0.88)" : "rgba(185,28,28,0.92)", color: "#f8fafc", padding: "3px 8px", borderRadius: "6px", fontSize: "0.68rem", fontWeight: 600, display: "flex", justifyContent: "space-between", alignItems: "center", boxShadow: "0 2px 6px rgba(0,0,0,0.3)" }}><span>{dressCode}</span><span style={{ fontSize: "0.62rem", opacity: 0.9 }}>{dressIsFormal ? "Protocolo OK" : "Atención"}</span></div></div>{!dressIsFormal && isCameraActive && (<div style={{ marginBottom: "0.6rem", padding: "5px 8px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "6px", color: "#991b1b", fontSize: "0.68rem", lineHeight: 1.3 }}>⚠️ <strong>Alerta:</strong> Se detectó vestimenta informal o torso descubierto. Para la defensa de tesis formal se recomienda camisa o saco.</div>)}<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.4rem", fontSize: "0.75rem" }}><div style={{ background: "var(--bg-muted, #f8fafc)", padding: "6px 8px", borderRadius: "6px", border: "1px solid var(--border-color, #e2e8f0)" }}><div style={{ color: "#64748b", fontSize: "0.7rem" }}>Postura Corporal</div><strong style={{ color: postureScore >= 80 ? "#16a34a" : postureScore >= 65 ? "#ca8a04" : "#dc2626", fontSize: "0.8rem" }}>{postureScore}% · {postureLabel}</strong></div><div style={{ background: "var(--bg-muted, #f8fafc)", padding: "6px 8px", borderRadius: "6px", border: "1px solid var(--border-color, #e2e8f0)" }}><div style={{ color: "#64748b", fontSize: "0.7rem" }}>Contacto Visual</div><strong style={{ color: eyeContactScore >= 80 ? "#16a34a" : eyeContactScore >= 65 ? "#ca8a04" : "#dc2626", fontSize: "0.8rem" }}>{eyeContactScore}% · {eyeContactLabel}</strong></div></div><div style={{ marginTop: "0.4rem", fontSize: "0.7rem", color: "#64748b", textAlign: "center" }}>🖐️ {gesturesLabel}</div></div><h2>Transcript</h2><p>{snapshot.answered_questions} respuestas confirmadas</p><ol>{snapshot.transcript.map((turn) => <li key={turn.id} className={`turn-${turn.speaker.toLowerCase()}`}><span>#{turn.sequence} · {turn.speaker === "JURY" ? "Jurado" : turn.speaker === "STUDENT" ? "Tú" : "Sistema"}</span><p>{turn.content}</p></li>)}</ol></aside></section></main>;
}
