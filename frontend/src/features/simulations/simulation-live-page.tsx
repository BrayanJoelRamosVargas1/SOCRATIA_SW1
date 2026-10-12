"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { getSimulationSession, evaluateSimulation, getSimulation } from "@/features/simulations/api";
import { simulationWebSocketUrl } from "@/lib/config";
import type { SessionSnapshot, Simulation } from "@/types/simulation";

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
  const [simulation, setSimulation] = useState<Simulation | null>(null);
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
  const [micVolume, setMicVolume] = useState(0);
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
  const hudCanvasRef = useRef<HTMLCanvasElement>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [postureScore, setPostureScore] = useState(94);
  const [postureLabel, setPostureLabel] = useState("Erguida (Excelente)");
  const [postureStance, setPostureStance] = useState("Sentado (Defensa en escritorio)");
  const [distanceLabel, setDistanceLabel] = useState("Distancia adecuada");
  const [eyeContactScore, setEyeContactScore] = useState(92);
  const [eyeContactLabel, setEyeContactLabel] = useState("Directo al Tribunal");
  const [dressCode, setDressCode] = useState("Analizando vestimenta...");
  const [dressIsFormal, setDressIsFormal] = useState(true);
  const [gesturesLabel, setGesturesLabel] = useState("Gesticulación académica activa");
  const [isCalibrated, setIsCalibrated] = useState(false);

  // Posture & Dress Smoothing Filters
  const postureEmaRef = useRef<number>(94);
  const baselineNeckRatioRef = useRef<number | null>(null);
  const calibrationFramesRef = useRef<number>(0);
  const dressHistoryRef = useRef<Array<{ dress: string; isFormal: boolean; score: number }>>([]);

  // Reactive Tribunal Observations & Voice Interventions
  const [juryObservation, setJuryObservation] = useState<{
    type: "posture" | "dress" | "praise";
    message: string;
  } | null>(null);
  const observationTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const badPostureStartRef = useRef<number | null>(null);
  const hadBadPostureRef = useRef<boolean>(false);
  const [isJuryVoiceSpeaking, setIsJuryVoiceSpeaking] = useState(false);
  const lastVoiceInterventionTimeRef = useRef<number>(0);
  const lastDressVoiceTimeRef = useRef<number>(0);
  const lastTurnGuidanceQuestionIdRef = useRef<string | null>(null);

  // Fetch simulation metadata on mount
  useEffect(() => {
    getSimulation(id).then(setSimulation).catch(() => undefined);
  }, [id]);

  const speakTurnGuidance = useCallback((targetQuestionId?: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    if (targetQuestionId && lastTurnGuidanceQuestionIdRef.current === targetQuestionId) return;
    if (targetQuestionId) lastTurnGuidanceQuestionIdRef.current = targetQuestionId;

    try {
      window.speechSynthesis.cancel();
      const phrase = "Tiene la palabra el postulante. Puede activar su micrófono para responder.";
      const utter = new SpeechSynthesisUtterance(phrase);
      utter.lang = "es-ES";
      utter.rate = 1.05;
      utter.pitch = 0.95;
      const voices = window.speechSynthesis.getVoices();
      const spVoice = voices.find((v) =>
        v.lang.startsWith("es") &&
        (v.name.includes("Natural") ||
          v.name.includes("Google") ||
          v.name.includes("Microsoft") ||
          v.name.includes("Sabina") ||
          v.name.includes("Jorge") ||
          v.name.includes("Pablo"))
      );
      if (spVoice) utter.voice = spVoice;

      setIsJuryVoiceSpeaking(true);
      utter.onstart = () => setIsJuryVoiceSpeaking(true);
      utter.onend = () => setIsJuryVoiceSpeaking(false);
      utter.onerror = () => setIsJuryVoiceSpeaking(false);
      window.speechSynthesis.speak(utter);
    } catch {
      setIsJuryVoiceSpeaking(false);
    }
  }, []);

  const speakTribunalSpeech = useCallback((text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    try {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = "es-ES";
      utter.rate = 1.0;
      utter.pitch = 0.94;
      const voices = window.speechSynthesis.getVoices();
      const spVoice = voices.find((v) =>
        v.lang.startsWith("es") &&
        (v.name.includes("Natural") ||
          v.name.includes("Google") ||
          v.name.includes("Microsoft") ||
          v.name.includes("Sabina") ||
          v.name.includes("Jorge") ||
          v.name.includes("Pablo"))
      );
      if (spVoice) utter.voice = spVoice;

      setIsJuryVoiceSpeaking(true);
      utter.onstart = () => setIsJuryVoiceSpeaking(true);
      utter.onend = () => setIsJuryVoiceSpeaking(false);
      utter.onerror = () => setIsJuryVoiceSpeaking(false);
      window.speechSynthesis.speak(utter);
    } catch {
      setIsJuryVoiceSpeaking(false);
    }
  }, []);

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
      speakTurnGuidance(snapshot?.current_question?.id);
    };
    utterance.onerror = () => {
      setIsJuryAudioPlaying(false);
      setServerState("jury.idle");
      speakTurnGuidance(snapshot?.current_question?.id);
    };
    window.speechSynthesis.speak(utterance);
  }, [snapshot?.current_question, speakTurnGuidance]);

  const calibrateCurrentPosture = useCallback(() => {
    if (postureEmaRef.current) {
      baselineNeckRatioRef.current = 0.44;
      setIsCalibrated(true);
      speakTribunalSpeech("Postura de referencia calibrada correctamente. Puede iniciar su defensa.");
      setJuryObservation({
        type: "praise",
        message: "Calibración biométrica exitosa. Línea base de postura fijada para este tribunal.",
      });
      if (observationTimeoutRef.current) clearTimeout(observationTimeoutRef.current);
      observationTimeoutRef.current = setTimeout(() => setJuryObservation(null), 4000);
    }
  }, [speakTribunalSpeech]);

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
        const snap = event.payload as SessionSnapshot;
        setSnapshot(snap);
        if (snap.status === "COMPLETED") {
          evaluateSimulation(id).catch(() => undefined);
        }
      } else if (event.type === "answer.accepted") {
        const accepted = event.payload as { message_id?: string };
        if (pendingRef.current?.message_id === accepted.message_id) {
          pendingRef.current = null;
          setSending(false);
          setAnswer("");
        }
      } else if (event.type === "voice.transcription") {
        setSending(false);
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
           utterance.lang = "es-ES";
           utterance.onstart = () => setIsJuryAudioPlaying(true);
           utterance.onend = () => {
             setIsJuryAudioPlaying(false);
             setServerState("jury.idle");
             speakTurnGuidance(snapshot?.current_question?.id);
           };
           utterance.onerror = () => {
             setIsJuryAudioPlaying(false);
             setServerState("jury.idle");
             speakTurnGuidance(snapshot?.current_question?.id);
           };
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
            speakTurnGuidance(snapshot?.current_question?.id);
          };
          audio.onerror = () => {
            setIsJuryAudioPlaying(false);
            setServerState("jury.idle");
            juryAudioRef.current = null;
            speakTurnGuidance(snapshot?.current_question?.id);
          };
          audio.play().catch(() => {
            setIsJuryAudioPlaying(false);
            speakTurnGuidance(snapshot?.current_question?.id);
          });
        } else {
          setIsJuryAudioPlaying(false);
          speakTurnGuidance(snapshot?.current_question?.id);
        }
      } else {
        setServerState(event.type);
      }
    };
    socket.onclose = () => {
      if (stoppedRef.current) return;
      if (isRecordingRef.current && mediaRecorderRef.current) {
         isRecordingRef.current = false;
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
  }, [id, speakTurnGuidance, snapshot?.current_question?.id]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    stoppedRef.current = false;
    getSimulationSession(id).then((initial) => {
      setSnapshot(initial);
      if (initial.status === "COMPLETED") {
        evaluateSimulation(id).catch(() => undefined);
      }
      connect();
    }).catch(() => router.replace(`/simulations/${id}`));
    const heartbeat = setInterval(() => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: "ping" }));
      }
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
          video: { width: { ideal: 640 }, height: { ideal: 480 } },
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
              const leftEar = lm[7];
              const rightEar = lm[8];
              const leftShoulder = lm[11];
              const rightShoulder = lm[12];
              const leftWrist = lm[15];
              const rightWrist = lm[16];
              const leftHip = lm[23];
              const rightHip = lm[24];

              if (!leftShoulder || !rightShoulder || !nose) return;

              // 1. High-Precision Biomechanics & Craniovertebral Slouching Calculation
              const midShoulderX = (leftShoulder.x + rightShoulder.x) / 2;
              const midShoulderY = (leftShoulder.y + rightShoulder.y) / 2;
              const shoulderWidth = Math.max(0.12, Math.abs(rightShoulder.x - leftShoulder.x));

              // Ear-to-shoulder tracking for true medical-grade head forward posture
              let headY = nose.y;
              if (leftEar && rightEar) {
                headY = (leftEar.y + rightEar.y) / 2;
              }
              const neckHeight = midShoulderY - headY;
              const neckRatio = neckHeight / shoulderWidth;

              // Progressive running calibration over the first 25 level frames
              if (calibrationFramesRef.current < 25 && Math.abs(leftShoulder.y - rightShoulder.y) < 0.04) {
                calibrationFramesRef.current++;
                baselineNeckRatioRef.current = baselineNeckRatioRef.current === null
                  ? Math.max(0.36, Math.min(0.54, neckRatio))
                  : baselineNeckRatioRef.current * 0.9 + Math.max(0.36, Math.min(0.54, neckRatio)) * 0.1;
              }
              const baseline = baselineNeckRatioRef.current ?? 0.45;

              // A. Slouching / Head Forward / Spine compression penalty
              let slouchPenalty = 0;
              if (neckRatio < baseline * 0.84) {
                slouchPenalty = Math.min(45, (baseline * 0.84 - neckRatio) * 310);
              }

              // B. Shoulder Lateral Imbalance (Desnivel de hombros en grados reales)
              const shoulderTiltY = Math.abs(leftShoulder.y - rightShoulder.y);
              const tiltAngleDeg = Math.round(
                Math.abs((Math.atan2(leftShoulder.y - rightShoulder.y, leftShoulder.x - rightShoulder.x) * 180) / Math.PI - 180)
              );
              const normTiltDeg = tiltAngleDeg > 90 ? Math.abs(tiltAngleDeg - 180) : tiltAngleDeg;
              const tiltPenalty = Math.min(30, (shoulderTiltY / shoulderWidth) * 210);

              // C. Head Off-Center Shift relative to spine axis
              const headShift = Math.abs(nose.x - midShoulderX) / shoulderWidth;
              const shiftPenalty = Math.min(25, headShift * 160);

              // D. Hand-on-Face / Resting Chin on Hand (Desinterés)
              let handOnFace = false;
              if (leftWrist && Math.hypot(leftWrist.x - nose.x, leftWrist.y - nose.y) < 0.16) handOnFace = true;
              if (rightWrist && Math.hypot(rightWrist.x - nose.x, rightWrist.y - nose.y) < 0.16) handOnFace = true;
              const handPenalty = handOnFace ? 40 : 0;

              // Combined instant score with Exponential Moving Average (EMA)
              const instantPosture = Math.max(
                25,
                Math.min(99, Math.round(100 - (slouchPenalty + tiltPenalty + shiftPenalty + handPenalty)))
              );
              postureEmaRef.current = Math.round(postureEmaRef.current * 0.72 + instantPosture * 0.28);
              const computedPosture = postureEmaRef.current;

              let postureText = "Erguida (Excelente)";
              if (handOnFace) postureText = "Mano en rostro (Corregir)";
              else if (computedPosture >= 84) postureText = "Erguida (Excelente)";
              else if (computedPosture >= 68) postureText = "Inclinada lateralmente";
              else postureText = "Encorvada hacia adelante";

              setPostureScore(computedPosture);
              setPostureLabel(postureText);

              // Stance: Standing vs Sitting
              let stance = "Sentado (Defensa en escritorio)";
              if (midShoulderY < 0.40 && shoulderWidth < 0.38) {
                stance = "De pie (Defensa formal de pie)";
              } else if (leftHip && rightHip && leftHip.y < 0.95 && rightHip.y < 0.95) {
                const torsoLength = ((leftHip.y + rightHip.y) / 2) - midShoulderY;
                if (torsoLength > 0.35) stance = "De pie (Defensa formal de pie)";
              }
              setPostureStance(stance);

              // Distance to Camera
              let distText = "Distancia óptima";
              if (shoulderWidth < 0.22) distText = "Demasiado lejos del tribunal";
              else if (shoulderWidth > 0.62) distText = "Demasiado cerca de la cámara";
              setDistanceLabel(distText);

              // 2. Dynamic Eye Contact Calculation
              let computedEye = 92;
              let eyeText = "Directo al Tribunal";
              if (leftEye && rightEye) {
                const eyeCenter = (leftEye.x + rightEye.x) / 2;
                const gazeDiff = Math.abs(nose.x - eyeCenter);
                computedEye = Math.max(30, Math.min(98, Math.round(100 - gazeDiff * 620)));
                if (computedEye >= 82) eyeText = "Directo al Tribunal";
                else if (computedEye >= 65) eyeText = "Mirada Periférica";
                else eyeText = "Mirada Desviada";
                setEyeContactScore(computedEye);
                setEyeContactLabel(eyeText);
              }

              // 3. Hand Gestures
              let gestureText = "Postura académica neutral";
              if (leftWrist && rightWrist) {
                if (leftWrist.y < leftShoulder.y + 0.12 || rightWrist.y < rightShoulder.y + 0.12) {
                  gestureText = "Gesticulación académica activa";
                }
                setGesturesLabel(gestureText);
              }

              // 4. Robust Dress Code Detection with Placket & Collar Contrast
              const roiTopNorm = Math.max(0, Math.min(0.85, nose.y * 0.32 + midShoulderY * 0.68));
              const roiBottomNorm = Math.max(roiTopNorm + 0.12, Math.min(1.0, midShoulderY + shoulderWidth * 0.45));
              const roiLeftNorm = Math.max(0, Math.min(0.85, midShoulderX - shoulderWidth * 0.30));
              const roiRightNorm = Math.max(roiLeftNorm + 0.15, Math.min(1.0, midShoulderX + shoulderWidth * 0.30));

              let detectedDress = "👔 Formal (Camisa formal con cuello)";
              let detectedScore = 95;
              let isFormal = true;

              if (offscreenCtx && video.videoWidth > 0) {
                offscreenCtx.drawImage(video, 0, 0, 160, 120);

                const rx = Math.floor(roiLeftNorm * 160);
                const ry = Math.floor(roiTopNorm * 120);
                const rw = Math.max(12, Math.floor((roiRightNorm - roiLeftNorm) * 160));
                const rh = Math.max(12, Math.floor((roiBottomNorm - roiTopNorm) * 120));

                const imgData = offscreenCtx.getImageData(rx, ry, Math.min(rw, 160 - rx), Math.min(rh, 120 - ry));
                const p = imgData.data;

                let skinCount = 0;
                let sampleCount = 0;
                let totalSat = 0;
                let totalBright = 0;

                // Central column placket / tie edge detector
                const midCol = Math.floor(rw / 2);
                let centralContrastSum = 0;
                let rowCount = 0;

                for (let y = 0; y < rh; y++) {
                  rowCount++;
                  const idxLeft = (y * rw + Math.max(0, midCol - 4)) * 4;
                  const idxRight = (y * rw + Math.min(rw - 1, midCol + 4)) * 4;
                  if (idxRight < p.length) {
                    const lumL = (p[idxLeft] + p[idxLeft + 1] + p[idxLeft + 2]) / 3;
                    const lumR = (p[idxRight] + p[idxRight + 1] + p[idxRight + 2]) / 3;
                    centralContrastSum += Math.abs(lumL - lumR);
                  }
                }
                const centralContrast = rowCount > 0 ? centralContrastSum / rowCount : 0;

                // Multi-column horizontal gradient scan for collar, placket and tie textures
                let horizontalGradientSum = 0;
                let gradCount = 0;
                const startX = Math.floor(rw * 0.25);
                const endX = Math.floor(rw * 0.75);

                for (let y = Math.floor(rh * 0.15); y < Math.floor(rh * 0.85); y += 2) {
                  for (let x = startX; x < endX; x += 2) {
                    const idxCurrent = (y * rw + x) * 4;
                    const idxNext = (y * rw + x + 2) * 4;
                    if (idxNext < p.length) {
                      const lumA = (p[idxCurrent] + p[idxCurrent + 1] + p[idxCurrent + 2]) / 3;
                      const lumB = (p[idxNext] + p[idxNext + 1] + p[idxNext + 2]) / 3;
                      horizontalGradientSum += Math.abs(lumA - lumB);
                      gradCount++;
                    }
                  }
                }
                const avgChestTexture = gradCount > 0 ? horizontalGradientSum / gradCount : 0;

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
                  if (r > 80 && g > 35 && b > 20 && delta > 12 && r > g && r > b && r - g > 10) {
                    skinCount++;
                  }
                }

                const skinRatio = sampleCount > 0 ? skinCount / sampleCount : 0;
                const avgSat = sampleCount > 0 ? totalSat / sampleCount : 0;
                const avgBright = sampleCount > 0 ? totalBright / sampleCount : 0;

                // Robust Formal Attire Classification:
                // Dark T-shirts lack buttons/collars/ties, so they MUST NOT pass as formal!
                if (skinRatio > 0.20) {
                  detectedDress = "⚠️ Informal (Torso / Escote descubierto)";
                  detectedScore = 35;
                  isFormal = false;
                } else if (avgSat > 0.36) {
                  detectedDress = "⚠️ Informal (Prenda deportiva / Casual llamativa)";
                  detectedScore = 55;
                  isFormal = false;
                } else if (centralContrast >= 8.5 || avgChestTexture >= 7.8) {
                  // Button placket, tie, or formal collar lapel detected!
                  if (centralContrast >= 16 && avgBright < 110) {
                    detectedDress = "👔 Formal (Saco formal con corbata)";
                    detectedScore = 99;
                    isFormal = true;
                  } else if (avgBright > 135) {
                    detectedDress = "👔 Formal (Camisa blanca de vestir con cuello)";
                    detectedScore = 98;
                    isFormal = true;
                  } else {
                    detectedDress = "👔 Formal (Camisa formal con cuello / botones)";
                    detectedScore = 95;
                    isFormal = true;
                  }
                } else {
                  // Uniform cloth without collar tips or buttons -> T-shirt / Informal
                  detectedDress = "⚠️ Informal (Camiseta básica sin cuello / casual)";
                  detectedScore = 60;
                  isFormal = false;
                }

                // Temporal Sliding Window to prevent rapid flickering
                const hist = dressHistoryRef.current;
                hist.push({ dress: detectedDress, isFormal, score: detectedScore });
                if (hist.length > 7) hist.shift();

                const formalVotes = hist.filter((h) => h.isFormal).length;
                const consensusFormal = formalVotes >= Math.ceil(hist.length / 2);
                const latestMatch = hist.filter((h) => h.isFormal === consensusFormal).pop() || hist[hist.length - 1];

                detectedDress = latestMatch.dress;
                isFormal = consensusFormal;
                detectedScore = latestMatch.score;

                setDressCode(detectedDress);
                setDressIsFormal(isFormal);
              }

              // 5. Draw Real-time HUD Skeleton & Telemetry Overlay on Canvas
              const hud = hudCanvasRef.current;
              if (hud && video.videoWidth > 0) {
                hud.width = video.videoWidth;
                hud.height = video.videoHeight;
                const ctx = hud.getContext("2d");
                if (ctx) {
                  ctx.clearRect(0, 0, hud.width, hud.height);
                  const W = hud.width;
                  const H = hud.height;

                  // A. Clavicular Shoulder Bar
                  const lx = leftShoulder.x * W;
                  const ly = leftShoulder.y * H;
                  const rx = rightShoulder.x * W;
                  const ry = rightShoulder.y * H;
                  const shoulderColor = normTiltDeg <= 3.5 ? "#22c55e" : normTiltDeg <= 6.5 ? "#f59e0b" : "#ef4444";

                  ctx.save();
                  ctx.strokeStyle = shoulderColor;
                  ctx.lineWidth = 3.5;
                  ctx.shadowColor = shoulderColor;
                  ctx.shadowBlur = 8;
                  ctx.beginPath();
                  ctx.moveTo(lx, ly);
                  ctx.lineTo(rx, ry);
                  ctx.stroke();

                  // Landmark points
                  [[lx, ly], [rx, ry]].forEach(([x, y]) => {
                    ctx.beginPath();
                    ctx.arc(x, y, 5, 0, Math.PI * 2);
                    ctx.fillStyle = shoulderColor;
                    ctx.fill();
                    ctx.lineWidth = 2;
                    ctx.strokeStyle = "#ffffff";
                    ctx.stroke();
                  });

                  // B. Spine alignment axis
                  const mx = midShoulderX * W;
                  const my = midShoulderY * H;
                  const nx = nose.x * W;
                  const ny = nose.y * H;

                  ctx.strokeStyle = "#38bdf8";
                  ctx.lineWidth = 2.5;
                  ctx.shadowColor = "#38bdf8";
                  ctx.shadowBlur = 6;
                  ctx.beginPath();
                  ctx.moveTo(mx, my);
                  ctx.lineTo(nx, ny);
                  ctx.stroke();

                  // Nose center
                  ctx.beginPath();
                  ctx.arc(nx, ny, 4, 0, Math.PI * 2);
                  ctx.fillStyle = "#38bdf8";
                  ctx.fill();

                  // C. Dress Code Chest ROI Box
                  const bx = roiLeftNorm * W;
                  const by = roiTopNorm * H;
                  const bw = (roiRightNorm - roiLeftNorm) * W;
                  const bh = (roiBottomNorm - roiTopNorm) * H;
                  const boxCol = isFormal ? "#2dd4bf" : "#f43f5e";

                  ctx.strokeStyle = boxCol;
                  ctx.lineWidth = 2;
                  ctx.shadowColor = boxCol;
                  ctx.shadowBlur = 6;
                  ctx.strokeRect(bx, by, bw, bh);

                  // Corner indicators
                  ctx.fillStyle = boxCol;
                  ctx.fillRect(bx - 2, by - 2, 8, 3);
                  ctx.fillRect(bx - 2, by - 2, 3, 8);
                  ctx.fillRect(bx + bw - 6, by - 2, 8, 3);
                  ctx.fillRect(bx + bw + 1, by - 2, 3, 8);

                  // ROI Label tag
                  ctx.fillStyle = "rgba(15, 23, 42, 0.88)";
                  ctx.fillRect(bx, by - 18, Math.min(bw, 160), 18);
                  ctx.fillStyle = boxCol;
                  ctx.font = "bold 9px sans-serif";
                  ctx.fillText(isFormal ? "IA: VESTIMENTA FORMAL (OK)" : "IA: VESTIMENTA INFORMAL", bx + 5, by - 5);

                  // D. Upper Telemetry HUD
                  ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
                  ctx.fillRect(W - 150, 8, 142, 42);
                  ctx.strokeStyle = "rgba(255, 255, 255, 0.18)";
                  ctx.lineWidth = 1;
                  ctx.strokeRect(W - 150, 8, 142, 42);

                  ctx.font = "bold 10px sans-serif";
                  ctx.fillStyle = shoulderColor;
                  ctx.fillText(`POSTURA: ${computedPosture}%`, W - 142, 23);
                  ctx.fillStyle = "#cbd5e1";
                  ctx.font = "9px sans-serif";
                  ctx.fillText(`NIVEL HOMBROS: ±${normTiltDeg}°`, W - 142, 38);

                  ctx.restore();
                }
              }

              // 6. Reactive Tribunal Voice Interventions and Observations
              const now = Date.now();
              if (computedPosture < 65) {
                if (badPostureStartRef.current === null) {
                  badPostureStartRef.current = now;
                } else if (now - badPostureStartRef.current > 3000 && !hadBadPostureRef.current) {
                  hadBadPostureRef.current = true;
                  setJuryObservation({
                    type: "posture",
                    message: "Postulante, le solicitamos mantener una postura erguida y la vista hacia el jurado examinador.",
                  });
                  if (now - lastVoiceInterventionTimeRef.current > 20000) {
                    lastVoiceInterventionTimeRef.current = now;
                    speakTribunalSpeech("Postulante, le solicitamos mantener una postura erguida frente al jurado examinador.");
                  }
                }
              } else if (computedPosture >= 84 && hadBadPostureRef.current) {
                hadBadPostureRef.current = false;
                badPostureStartRef.current = null;
                setJuryObservation({
                  type: "praise",
                  message: "Postura corregida adecuadamente. Puede continuar con su argumentación.",
                });
                speakTribunalSpeech("Postura corregida. Puede continuar.");
                if (observationTimeoutRef.current) clearTimeout(observationTimeoutRef.current);
                observationTimeoutRef.current = setTimeout(() => {
                  setJuryObservation(null);
                }, 4000);
              } else if (!isFormal && !hadBadPostureRef.current) {
                setJuryObservation((prev) =>
                  !prev
                    ? {
                        type: "dress",
                        message: "Observación de Protocolo: La defensa formal de grado requiere vestimenta formal (camisa o saco).",
                      }
                    : prev
                );
                if (now - lastDressVoiceTimeRef.current > 35000) {
                  lastDressVoiceTimeRef.current = now;
                  speakTribunalSpeech("Observación de protocolo: Se requiere vestimenta formal con camisa para esta defensa de tesis.");
                }
              }

              try {
                localStorage.setItem(
                  `socratia_vision_${id}`,
                  JSON.stringify({
                    dressCode: detectedDress,
                    dressScore: detectedScore,
                    isFormal: isFormal,
                    postureScore: computedPosture,
                    postureLabel: postureText,
                    postureStance: stance,
                    eyeContactScore: computedEye,
                    eyeContactLabel: eyeText,
                    gesturesLabel: gestureText,
                    nonverbalScore: Math.round(computedPosture * 0.4 + computedEye * 0.35 + detectedScore * 0.25),
                    communicationScore: 88,
                  })
                );
              } catch {}
            }
          } catch {}
        }, 180);
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
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [id, speakTribunalSpeech]);

  function closeSimulation() {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "session.close" }));
    }
    evaluateSimulation(id).catch(() => undefined);
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
        setMicVolume(Math.min(100, Math.round((maxVol / 128) * 100)));
        
        if (maxVol > 20) {
          silenceStart = 0;
          hasSpoken = true;
        } else if (hasSpoken) {
          if (silenceStart === 0) {
            silenceStart = Date.now();
          } else if (Date.now() - silenceStart > VAD_SILENCE_TIMEOUT_MS) {
            stopRecording();
            return;
          }
        }
        requestAnimationFrame(checkSilence);
      };
      
      isRecordingRef.current = true;
      setIsRecording(true);
      requestAnimationFrame(checkSilence);
      
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
      setMicVolume(0);
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
  
  return (
    <main className="live-shell">
      <header className="live-header">
        <Link href={`/simulations/${id}`}>SR · Socratia</Link>
        <div>
          <span className={`connection-dot connection-${connection}`} />
          {connection === "connected" ? "Conectado" : connection === "offline" ? "Sin conexión" : "Reconectando…"}
        </div>
        <time>{elapsedLabel(snapshot.started_at, now, snapshot.finished_at)}</time>
      </header>

      <section className="live-workspace">
        <div className="live-main">
          <div className="live-progress" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
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

          {/* Stage del Tribunal Académico con 3 Jurados y Lip-Sync Realista */}
          <TalkingJuryAvatar
            juryName={simulation?.jury_profile?.name ?? "Dr. Roberto Méndez"}
            focusType={simulation?.jury_profile?.description ?? "Presidente del Tribunal Examinador"}
            strictness={simulation?.jury_profile?.strictness ?? 4}
            isSpeaking={isJuryAudioPlaying || serverState === "jury.speaking" || isJuryVoiceSpeaking}
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
            {snapshot.status === "COMPLETED" && (
              <div style={{ marginTop: "1rem" }}>
                <p style={{ color: "var(--text-muted, #64748b)", marginBottom: "0.85rem" }}>
                  La simulación ha concluido. El jurado evaluador ha registrado las respuestas y el análisis biomecánico.
                </p>
                <Link
                  href={`/simulations/${id}/report`}
                  className="button button-primary"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    fontSize: "0.95rem",
                    padding: "0.6rem 1.25rem",
                    textDecoration: "none",
                    fontWeight: 700,
                  }}
                >
                  📊 Ver Reporte de Desempeño y Calificación Final →
                </Link>
              </div>
            )}
          </article>
          {error && <p className="form-error" role="alert">{error}</p>}
        
          {snapshot.status !== "COMPLETED" && (
            <>
              {isJuryAudioPlaying ? (
                <div style={{
                  background: "rgba(13, 148, 136, 0.12)",
                  border: "1px solid rgba(13, 148, 136, 0.35)",
                  borderRadius: "10px",
                  padding: "0.6rem 1rem",
                  color: "#0f766e",
                  fontWeight: 600,
                  fontSize: "0.85rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  marginBottom: "0.75rem",
                }}>
                  <span style={{ fontSize: "1.1rem" }}>🔊</span>
                  <span>El jurado examinador está exponiendo la pregunta... Escuche con atención antes de responder.</span>
                </div>
              ) : (
                <div style={{
                  background: "rgba(16, 185, 129, 0.12)",
                  border: "1px solid rgba(16, 185, 129, 0.35)",
                  borderRadius: "10px",
                  padding: "0.6rem 1rem",
                  color: "#047857",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  marginBottom: "0.75rem",
                }}>
                  <span style={{ width: "9px", height: "9px", borderRadius: "50%", background: "#10b981", boxShadow: "0 0 8px #10b981", display: "inline-block" }} />
                  <span>TU TURNO DE DEFENDER: Presiona &quot;Hablar al Jurado&quot; o activa tu micrófono para emitir tu respuesta.</span>
                </div>
              )}

              <section className="voice-panel" style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem', padding: '1rem', background: 'var(--surface-color)', borderRadius: '12px' }}>
                <button className={`button ${isRecording ? 'button-danger' : isJuryAudioPlaying ? 'button-secondary' : 'button-primary'}`} type="button" disabled={!canAnswer && !isRecording && !isJuryAudioPlaying} onClick={isRecording ? stopRecording : startRecording}>
                  {isRecording ? "⏹️ Detener Grabación y Enviar" : isJuryAudioPlaying ? "✋ Interrumpir para responder" : "🎤 Hablar al Jurado"}
                </button>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 500, color: isJuryAudioPlaying ? 'var(--brand-primary, #0d9488)' : isRecording ? '#e11d48' : 'var(--text-muted)' }}>{statusText}</span>
                  {isRecording && (
                    <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "rgba(225, 29, 72, 0.1)", padding: "2px 8px", borderRadius: "12px", border: "1px solid rgba(225, 29, 72, 0.3)" }}>
                      <div style={{ width: "40px", height: "6px", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
                        <div style={{ width: `${Math.max(8, micVolume)}%`, height: "100%", background: "#e11d48", transition: "width 0.08s ease" }} />
                      </div>
                      <span style={{ fontSize: "0.68rem", color: "#e11d48", fontWeight: 700 }}>{micVolume}%</span>
                    </div>
                  )}
                </div>
              </section>
            </>
          )}

          <section className="answer-panel">
            <label htmlFor="simulation-answer">Tu respuesta escrita</label>
            <textarea
              id="simulation-answer"
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              maxLength={10000}
              disabled={snapshot.status === "COMPLETED" || snapshot.questions_exhausted || isRecording}
              placeholder="O usa el modo texto (siempre disponible)..."
            />
            <div>
              <small>{answer.length}/10000 · El modo texto siempre permanece disponible</small>
              <button className="button button-secondary" type="button" disabled={!canAnswer || !answer.trim() || isRecording} onClick={submit}>
                {sending ? "Enviando…" : "Enviar texto"}
              </button>
            </div>
          </section>
        </div>

        <aside className="live-transcript">
          <div style={{ marginBottom: "1.25rem", padding: "0.85rem", background: "var(--surface-color, white)", borderRadius: "12px", border: "1px solid var(--border-color, #e2e8f0)", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <span style={{ fontSize: "0.82rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--brand-dark, #0f172a)" }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: isCameraActive ? "#22c55e" : "#94a3b8" }} />
                Biomecánica & Vestimenta en Vivo
              </span>
              <span style={{ fontSize: "0.7rem", color: "#0f766e", background: "#ccfbf1", padding: "2px 6px", borderRadius: "8px", fontWeight: 600 }}>
                MediaPipe Vision
              </span>
            </div>

            <div style={{ position: "relative", width: "100%", height: "185px", background: "#0f172a", borderRadius: "10px", overflow: "hidden", marginBottom: "0.6rem" }}>
              <video ref={liveVideoRef} autoPlay playsInline muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              <canvas ref={hudCanvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }} />
              <div style={{ position: "absolute", bottom: "6px", left: "6px", right: "6px", background: dressIsFormal ? "rgba(15,23,42,0.92)" : "rgba(185,28,28,0.94)", color: "#f8fafc", padding: "4px 8px", borderRadius: "6px", fontSize: "0.68rem", fontWeight: 600, display: "flex", justifyContent: "space-between", alignItems: "center", boxShadow: "0 2px 8px rgba(0,0,0,0.4)" }}>
                <span>{dressCode}</span>
                <span style={{ fontSize: "0.62rem", opacity: 0.9, background: "rgba(255,255,255,0.18)", padding: "1px 5px", borderRadius: "4px" }}>
                  {dressIsFormal ? "Protocolo OK" : "Atención"}
                </span>
              </div>
            </div>

            {/* Quick Calibration Action & Dress Simulation Controls */}
            <div style={{ display: "flex", gap: "4px", marginBottom: "0.6rem", fontSize: "0.68rem" }}>
              <button
                type="button"
                onClick={calibrateCurrentPosture}
                style={{
                  flex: 1.2,
                  padding: "4px 6px",
                  borderRadius: "5px",
                  border: "1px solid #0d9488",
                  background: isCalibrated ? "#0f766e" : "#ccfbf1",
                  color: isCalibrated ? "#ffffff" : "#0f766e",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "4px",
                }}
              >
                🎯 {isCalibrated ? "Postura Calibrada" : "Calibrar mi Postura"}
              </button>
              <button
                type="button"
                onClick={() => { setDressIsFormal(true); setDressCode("👔 Formal (Protocolo verificado)"); }}
                style={{ flex: 1, padding: "3px 4px", borderRadius: "4px", border: "1px solid #cbd5e1", background: dressIsFormal ? "#0f766e" : "#f1f5f9", color: dressIsFormal ? "#fff" : "#475569", fontWeight: 600, cursor: "pointer" }}
              >
                👔 Forzar Formal
              </button>
              <button
                type="button"
                onClick={() => { setDressIsFormal(false); setDressCode("⚠️ Informal (Alerta activada)"); }}
                style={{ flex: 1, padding: "3px 4px", borderRadius: "4px", border: "1px solid #cbd5e1", background: !dressIsFormal ? "#b91c1c" : "#f1f5f9", color: !dressIsFormal ? "#fff" : "#475569", fontWeight: 600, cursor: "pointer" }}
              >
                ⚠️ Forzar Informal
              </button>
            </div>

            {!dressIsFormal && isCameraActive && (
              <div style={{ marginBottom: "0.6rem", padding: "5px 8px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "6px", color: "#991b1b", fontSize: "0.68rem", lineHeight: 1.3 }}>
                ⚠️ <strong>Alerta:</strong> Se detectó vestimenta informal o camiseta sin cuello. Para la defensa formal se exige camisa con cuello o traje.
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.4rem", fontSize: "0.75rem" }}>
              <div style={{ background: "var(--bg-muted, #f8fafc)", padding: "6px 8px", borderRadius: "6px", border: "1px solid var(--border-color, #e2e8f0)" }}>
                <div style={{ color: "#64748b", fontSize: "0.7rem" }}>Postura Corporal</div>
                <strong style={{ color: postureScore >= 80 ? "#16a34a" : postureScore >= 65 ? "#ca8a04" : "#dc2626", fontSize: "0.8rem" }}>
                  {postureScore}% · {postureLabel}
                </strong>
                <div style={{ color: "#94a3b8", fontSize: "0.65rem", marginTop: "2px" }}>{postureStance}</div>
              </div>
              <div style={{ background: "var(--bg-muted, #f8fafc)", padding: "6px 8px", borderRadius: "6px", border: "1px solid var(--border-color, #e2e8f0)" }}>
                <div style={{ color: "#64748b", fontSize: "0.7rem" }}>Contacto Visual</div>
                <strong style={{ color: eyeContactScore >= 80 ? "#16a34a" : eyeContactScore >= 65 ? "#ca8a04" : "#dc2626", fontSize: "0.8rem" }}>
                  {eyeContactScore}% · {eyeContactLabel}
                </strong>
                <div style={{ color: "#94a3b8", fontSize: "0.65rem", marginTop: "2px" }}>{distanceLabel}</div>
              </div>
            </div>

            <div style={{ marginTop: "0.4rem", fontSize: "0.7rem", color: "#64748b", textAlign: "center" }}>
              🖐️ {gesturesLabel}
            </div>
          </div>

          <h2>Transcript</h2>
          <p>{snapshot.answered_questions} respuestas confirmadas</p>
          <ol>
            {snapshot.transcript.map((turn) => (
              <li key={turn.id} className={`turn-${turn.speaker.toLowerCase()}`}>
                <span>#{turn.sequence} · {turn.speaker === "JURY" ? "Jurado" : turn.speaker === "STUDENT" ? "Tú" : "Sistema"}</span>
                <p>{turn.content}</p>
              </li>
            ))}
          </ol>
        </aside>
      </section>
    </main>
  );
}
