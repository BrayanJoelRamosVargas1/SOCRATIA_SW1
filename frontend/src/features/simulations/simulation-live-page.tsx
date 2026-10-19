"use client";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";
import { ArrowLeft, Camera, CameraOff, Mic, Square, Send, Keyboard, Clock3, CheckCircle2, AlertCircle, RotateCcw } from "lucide-react";
import { getSimulationSession, evaluateSimulation, getSimulation } from "./api";
import { simulationWebSocketUrl, API_URL } from "@/lib/config";
import type { SessionSnapshot, Simulation } from "@/types/simulation";
import type { SpeechMotion } from "./jury-character";
import { TalkingJuryAvatar } from "./talking-jury-avatar";
import { analyzeTranscript,torsoFitsFrame } from "./practice-signals";
import { LiveVisualCoach } from "./live-visual-coach";
import { CameraTrackingOverlay } from "./camera-tracking-overlay";
import { AppearanceFeedback, type AppearanceStatus } from "./appearance-feedback";
import { VisualFeedback } from "./visual-feedback";
import { usePracticeCamera } from "./use-practice-camera";
import {TurnEndDetector} from "./turn-end-detector";
import {juryVoice} from "./jury-voices";
import {readSessionPreferences,saveSessionPreferences} from "./session-preferences";
type Connection = "connecting" | "connected" | "reconnecting" | "offline";
type AnswerMessage = {type: "answer.submit"; message_id:string; payload:{question_id:string; content:string}};
const retryDelays = [1000,2000,4000,8000,10000];
function timeLabel(seconds: number) { return `${String(Math.floor(seconds / 60)).padStart(2,"0")}:${String(seconds % 60).padStart(2,"0")}`; }
export function SimulationLivePage() {
  const {id} = useParams<{id:string}>();
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [connection, setConnection] = useState<Connection>("connecting");
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");
  const [answer,setAnswer] = useState("");
  const [sending,setSending] = useState(false);
  const [recording,setRecording] = useState(false);
  const [autoListen,setAutoListen]=useState(true);
  const autoListenRef=useRef(true);
  const autoAttempt=useRef("");
  const activeUtterance=useRef("");
  const recordingEligibility=useRef(false);
  const [volume,setVolume] = useState(0);
  const [audioBlocked,setAudioBlocked]=useState(false);
  const [questionPending,setQuestionPending]=useState(false);
  const [speaking,setSpeaking] = useState(false);
  const [voiceLoading,setVoiceLoading] = useState(false);
  const [serverState,setServerState] = useState("");
  const [mode,setMode] = useState<"voice" | "text">("voice");
  const [appearance,setAppearance] = useState<AppearanceStatus>({state:"waiting",result:null,message:"",time:""});
  const [cameraDeviceId,setCameraDeviceId]=useState("");
  const [cameraEnabled,setCameraEnabled] = useState(false);
  const [closeDialog,setCloseDialog] = useState(false);
  const [closing,setClosing] = useState(false);
  const [now,setNow] = useState(0);
  const [transcription,setTranscription] = useState("");
  const {videoRef, presence, signals, status: cameraStatus, error: cameraError, baseline, recalibrate, faceSignals, torsoTilt, faceError, tracking, calibrateGaze, gazeCalibrated, quality, restart, cameras} = usePracticeCamera(cameraEnabled && snapshot?.status !== "COMPLETED",cameraDeviceId);
  const closeDialogRef = useRef<HTMLDivElement>(null);
  const socket = useRef<WebSocket | null>(null);
  const pending = useRef<AnswerMessage | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const recordingStream = useRef<MediaStream | null>(null);
  const voiceContext = useRef<AudioContext | null>(null);
  const volumeTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const recordingLimit = useRef<ReturnType<typeof setTimeout> | null>(null);
  const speechMotion = useRef<SpeechMotion>({analyser:null,speaking:false,text:"",charIndex:0,startedAt:0});
  const playbackContext = useRef<AudioContext | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const audioUrl = useRef<string | null>(null);
  const chunks = useRef<Blob[]>([]);
  const audioMime = useRef("audio/mpeg");
  const speechRequest = useRef<AbortController | null>(null);
  const startingRecording = useRef(false);
  const mounted = useRef(true);
  const localSpeech = useRef(false);
  const playbackGeneration = useRef(0);
  const juryText = useRef("");
  const speakerIndex = useRef(0);
  const interruptRequested = useRef(false);
  const blockedSpeech = useRef("");
  const stopPlayback = useCallback(() => {
    playbackGeneration.current++;
    setVoiceLoading(false);
    speechRequest.current?.abort(); speechRequest.current = null;
    audio.current?.pause(); audio.current = null;
    speechMotion.current.analyser = null; speechMotion.current.speaking = false; speechMotion.current.audioBuffer = undefined;
    void playbackContext.current?.close().catch(() => undefined); playbackContext.current = null;
    if (audioUrl.current) { URL.revokeObjectURL(audioUrl.current); audioUrl.current = null; }
    window.speechSynthesis?.cancel(); localSpeech.current = false; setSpeaking(false);
  }, []);
  const stopMedia = useCallback((submit = true) => {
    if (volumeTimer.current) { clearInterval(volumeTimer.current); volumeTimer.current = null; }
    if (recordingLimit.current) clearTimeout(recordingLimit.current);
    if(!submit && activeUtterance.current && socket.current?.readyState===WebSocket.OPEN)socket.current.send(JSON.stringify({type:"voice.utterance.cancel",message_id:activeUtterance.current}));
    activeUtterance.current="";
    if (recorder.current && recorder.current.state !== "inactive") {
      if (!submit) {
        recorder.current.onstop = null;recorder.current.ondataavailable=null;
      }
      recorder.current.stop();
    }
    recordingStream.current?.getTracks().forEach(track => track.stop()); recordingStream.current = null;
    void voiceContext.current?.close().catch(() => undefined); voiceContext.current = null;
    if (mounted.current) { setRecording(false); setVolume(0); }
  }, []);
  const speakText = useCallback((text: string) => {
    blockedSpeech.current="";setAudioBlocked(false);
    stopPlayback();
    const generation = playbackGeneration.current;
    const browserFallback = () => {
    if (generation !== playbackGeneration.current || !mounted.current) return;
    setVoiceLoading(false);
    if (!("speechSynthesis" in window)) { localSpeech.current=false;setSpeaking(false);setNotice("La voz del navegador no está disponible. Lee la pregunta en pantalla."); return; }
    const utterance = new SpeechSynthesisUtterance(text);
    const profile = juryVoice(window.speechSynthesis.getVoices(), speakerIndex.current);
    utterance.lang = profile.voice?.lang ?? "es-ES";
    utterance.rate = profile.rate; utterance.pitch = profile.pitch;
    if (profile.voice) utterance.voice = profile.voice;
    localSpeech.current = true;
    setSpeaking(true);
    utterance.onstart = () => { if (generation !== playbackGeneration.current) return; speechMotion.current = {analyser:null,speaking:true,text,charIndex:0,startedAt:performance.now()}; setSpeaking(true); };
    utterance.onboundary = event => {if (generation === playbackGeneration.current) speechMotion.current.charIndex = event.charIndex;};
    const finish = () => { if (generation !== playbackGeneration.current) return; localSpeech.current = false; speechMotion.current.speaking = false; if (mounted.current) {setSpeaking(false); setServerState("");} };
    utterance.onend = finish;
    utterance.onerror = event => {
      if(generation!==playbackGeneration.current)return;
      finish();
      if (mounted.current && event.error === "not-allowed") { blockedSpeech.current = text; setAudioBlocked(true);setNotice("El navegador necesita una interacción para habilitar el sonido. Haz clic en la sala y el jurado comenzará automáticamente."); }
      else if (mounted.current && !["canceled","interrupted"].includes(event.error)) setNotice("No pudimos reproducir la voz del navegador. Puedes leer la pregunta y responder normalmente.");
    };
    window.speechSynthesis.speak(utterance);
    };
    if (!juryText.current || !text.endsWith(juryText.current)) { browserFallback(); return; }
    const controller = new AbortController(); speechRequest.current = controller;
    const timeout = setTimeout(() => controller.abort(), 45000);
    setSpeaking(true); setVoiceLoading(true); localSpeech.current = true;
    void (async () => {
      try {
        const response = await fetch(`${API_URL}/simulations/${id}/speech`, {method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({text}),signal:controller.signal});
        if (!response.ok) throw new Error("local voice unavailable");
        const blob = await response.blob();
        if (generation !== playbackGeneration.current || !mounted.current) return;
        const context = new AudioContext(); playbackContext.current = context;
        const buffer = await context.decodeAudioData(await blob.arrayBuffer());
        if (generation !== playbackGeneration.current || !mounted.current) { void context.close(); return; }
        const url = URL.createObjectURL(blob); audioUrl.current = url;
        const player = new Audio(url); audio.current = player;
        const analyser = context.createAnalyser(); analyser.fftSize = 256;
        context.createMediaElementSource(player).connect(analyser); analyser.connect(context.destination);
        speechMotion.current = {analyser,speaking:true,text,charIndex:0,startedAt:performance.now(),audioBuffer:buffer};
        setVoiceLoading(false);
        player.onplaying = () => {if (generation === playbackGeneration.current) speechMotion.current.startedAt = performance.now();};
        const finish = () => { if (generation === playbackGeneration.current) {stopPlayback();setServerState("");} };
        player.onended = finish;
        player.onerror = () => {
          if (generation !== playbackGeneration.current || !mounted.current) return;
          audio.current?.pause(); audio.current = null;
          if (audioUrl.current) { URL.revokeObjectURL(audioUrl.current); audioUrl.current = null; }
          void playbackContext.current?.close().catch(() => undefined); playbackContext.current = null;
          browserFallback();
        };
        await context.resume();
        await player.play();
      } catch {
        if (generation === playbackGeneration.current && mounted.current) {
          if (audioUrl.current) {URL.revokeObjectURL(audioUrl.current);audioUrl.current=null;}
          void playbackContext.current?.close().catch(()=>undefined);playbackContext.current=null;
          browserFallback();
        }
      } finally { clearTimeout(timeout); if(speechRequest.current===controller)speechRequest.current=null; }
    })();
  }, [id, stopPlayback]);
  useEffect(() => {
    mounted.current = true;
    const preferences = readSessionPreferences(id);
    autoListenRef.current = preferences.autoListen ?? true;
    let stopped = false, retries = 0, reconnect: ReturnType<typeof setTimeout> | undefined;
    let evaluated = false;
    let introduced = false;
    let spokenQuestion = "";
    let questionTimer: ReturnType<typeof setTimeout> | undefined;
    const cancelQuestion = () => { if (questionTimer) clearTimeout(questionTimer); questionTimer = undefined; if(mounted.current)setQuestionPending(false); };
    const announce = (next: SessionSnapshot) => {
      const question = next.current_question;
      if (next.status === "COMPLETED" || next.questions_exhausted || !question || question.id === spokenQuestion) return;
      cancelQuestion();
      spokenQuestion = question.id;
      const greeting = !introduced ? next.answered_questions === 0
        ? "Bienvenido a tu defensa. Somos tu tribunal. Te haremos preguntas sobre tu investigación y escucharemos tus respuestas. Tómate un momento para organizar tus ideas. Comencemos. "
        : "Bienvenido de nuevo. Continuemos tu defensa desde la pregunta pendiente. " : "";
      introduced = true; setQuestionPending(true);
      const alreadyIntroduces = /^(buenos días|buenas tardes|buenas noches|bienvenid)/i.test(question.text.trim());
      questionTimer = setTimeout(() => { if (!stopped) {setQuestionPending(false);speakText((alreadyIntroduces ? "" : greeting) + question.text);} }, 500);
    };
    const update = (next: SessionSnapshot) => {
      speakerIndex.current = ((next.current_question?.position ?? 1) - 1) % 3;
      juryText.current = next.current_question?.text ?? "";
      setSnapshot(next);
      if (next.status === "COMPLETED") {
        cancelQuestion();
        stopMedia(false); stopPlayback(); setClosing(false);
        if (!evaluated) { evaluated = true; evaluateSimulation(id).catch(() => setNotice("La evaluación aún no pudo iniciarse. Puedes reintentar desde el reporte.")); }
      }
    };
    function connect() {
      if (stopped) return;
      setConnection(retries ? "reconnecting" : "connecting");
      const ws = new WebSocket(simulationWebSocketUrl(id)); socket.current = ws;
      ws.onopen = () => { retries = 0; setConnection("connected"); if (pending.current) ws.send(JSON.stringify(pending.current)); };
      ws.onmessage = event => {
        if (stopped) return;
        if (event.data instanceof Blob) {chunks.current.push(event.data); return;}
        let message: {type:string; payload?: unknown; text?:string; code?:string; message?:string};
        try { message = JSON.parse(event.data); } catch { setNotice("Recibimos un evento no válido; esperando el siguiente estado de sesión."); return; }
        const payload = message.payload as {message_id?:string; text?:string} | undefined;
        if (message.type === "session.snapshot" || message.type === "session.state") {const next = message.payload as SessionSnapshot; update(next); announce(next);}
        else if (message.type === "answer.accepted") {
          if (pending.current?.message_id === payload?.message_id) {pending.current = null; setAnswer(""); setSending(false);}
        } else if (message.type === "voice.transcription") {const text=message.text ?? payload?.text ?? "";setTranscription(text);setSending(false);if(!text.trim()){autoListenRef.current=false;setAutoListen(false);setNotice("No se reconoció una respuesta oral. Puedes activar de nuevo la conversación automática o responder por texto.");}}
        else if (message.type === "jury.speaking") {cancelQuestion(); stopPlayback(); chunks.current = []; setServerState("jury.speaking");}
        else if (message.type === "tts.started") {cancelQuestion(); audioMime.current=(message.payload as {mime_type?:string})?.mime_type ?? "audio/mpeg"; setServerState("jury.speaking");}
        else if (message.type === "tts.fallback") {cancelQuestion(); chunks.current = []; if (payload?.text) speakText(payload.text);}
        else if (message.type === "jury.finished") {
          setServerState("");
          if (!chunks.current.length || localSpeech.current) return;
          audio.current?.pause();
          if (audioUrl.current) URL.revokeObjectURL(audioUrl.current);
          const voiceBlob = new Blob(chunks.current,{type:audioMime.current});
          const url = URL.createObjectURL(voiceBlob); chunks.current = [];
          audioUrl.current = url;
          const player = new Audio(url); audio.current = player; setSpeaking(true);
          const generation = ++playbackGeneration.current;
          speechMotion.current = {analyser:null,speaking:true,text:payload?.text ?? juryText.current,charIndex:0,startedAt:performance.now()};
          player.onplaying = () => { if (generation === playbackGeneration.current) speechMotion.current.startedAt = performance.now(); };
          try {
            void playbackContext.current?.close().catch(() => undefined);
            const context = new AudioContext(); playbackContext.current = context;
            const analyser = context.createAnalyser(); analyser.fftSize = 256;
            context.createMediaElementSource(player).connect(analyser); analyser.connect(context.destination);
            speechMotion.current.analyser = analyser;
            void voiceBlob.arrayBuffer().then(bytes => context.decodeAudioData(bytes)).then(buffer => { if (generation === playbackGeneration.current) speechMotion.current.audioBuffer = buffer; }).catch(() => undefined);
            void context.resume();
          } catch { speechMotion.current.analyser = null; }
          const finish = () => {URL.revokeObjectURL(url); if (generation !== playbackGeneration.current) return; speechMotion.current.speaking = false; speechMotion.current.analyser = null; void playbackContext.current?.close().catch(() => undefined); playbackContext.current = null; if (audioUrl.current === url) {audioUrl.current = null; audio.current = null;} if (!stopped) setSpeaking(false);};
          player.onended = finish; player.onerror = () => {finish();if(!stopped && generation===playbackGeneration.current)speakText(payload?.text ?? juryText.current);};
          player.play().then(() => {if (!stopped && generation === playbackGeneration.current) setSpeaking(true);}).catch(() => {finish(); if (!stopped && generation === playbackGeneration.current) {blockedSpeech.current = payload?.text ?? juryText.current; setAudioBlocked(true);setNotice("Haz clic en la sala para habilitar el sonido; el jurado continuará automáticamente.");}});
        } else if (message.type === "error" || message.type === "stt.degraded") {
          pending.current = null; setSending(false); stopMedia(false); setClosing(false);
          if (message.code === "SESSION_QUESTIONS_EXHAUSTED") setSnapshot(current => current ? {...current, questions_exhausted:true} : current);
          else {setError(message.message || "No se pudo procesar la respuesta. Puedes reintentar por texto."); if (message.type === "stt.degraded") setMode("text");}
          setServerState("");
        } else if (!["pong","heartbeat.ack","voice.cancelled"].includes(message.type)) setServerState(message.type);
      };
      ws.onerror = () => setNotice("La conexión está interrumpida. Intentaremos recuperarla.");
      ws.onclose = event => {
        if (stopped) return;
        if (recorder.current?.state === "recording") setNotice("Se interrumpió la grabación al perder conexión. Vuelve a grabar tu respuesta cuando reconecte.");
        cancelQuestion(); spokenQuestion = ""; stopMedia(false); stopPlayback(); chunks.current = []; setClosing(false); setServerState("");
        if (!pending.current) setSending(false);
        if ([1008,4401,4403,4404].includes(event.code)) {setConnection("offline"); setError("No pudimos autorizar esta sesión. Vuelve a la preparación e inicia sesión nuevamente."); return;}
        setConnection("reconnecting");
        reconnect = setTimeout(connect,retryDelays[Math.min(retries++,retryDelays.length-1)]);
      };
    }
    Promise.all([getSimulationSession(id),getSimulation(id)]).then(([session,meta]) => {if (!stopped) {setMode(preferences.mode ?? "voice");setAutoListen(preferences.autoListen ?? true);update(session); setSimulation(meta); if (session.status !== "COMPLETED") {setCameraEnabled(preferences.cameraEnabled ?? meta.camera_ready); connect();}}}).catch(err => {if (!stopped) {setError(err instanceof Error ? err.message : "No se pudo recuperar la sesión."); setConnection("offline");}});
    const heartbeat = setInterval(() => {if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({type:"ping"}));},25000);
    const clock = setInterval(() => setNow(Date.now()),1000);
    return () => {stopped = true; speechRequest.current?.abort(); cancelQuestion(); blockedSpeech.current = ""; mounted.current = false; if (reconnect) clearTimeout(reconnect); clearInterval(clock); clearInterval(heartbeat); socket.current?.close(); stopMedia(false); audio.current?.pause(); if (audioUrl.current) URL.revokeObjectURL(audioUrl.current); window.speechSynthesis?.cancel(); void playbackContext.current?.close().catch(() => undefined);};
  }, [id, speakText, stopMedia, stopPlayback]);
  useEffect(() => {
    const resume = () => {
      if (!blockedSpeech.current) return;
      const text = blockedSpeech.current; blockedSpeech.current = ""; setNotice(""); speakText(text);
    };
    window.addEventListener("pointerdown", resume);
    window.addEventListener("keydown", resume);
    return () => { window.removeEventListener("pointerdown", resume); window.removeEventListener("keydown", resume); };
  }, [speakText]);
  useEffect(() => {
    if (!closeDialog) return;
    const previous = document.activeElement as HTMLElement | null;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setCloseDialog(false);
      if (event.key !== "Tab") return;
      const buttons = closeDialogRef.current?.querySelectorAll<HTMLButtonElement>("button");
      if (!buttons?.length) return;
      const first = buttons[0], last = buttons[buttons.length-1];
      if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first.focus();}
    };
    closeDialogRef.current?.querySelector("button")?.focus();
    window.addEventListener("keydown",onKey);
    return () => {window.removeEventListener("keydown",onKey); previous?.focus();};
  },[closeDialog]);
  const completed = snapshot?.status === "COMPLETED";
  const exhausted = snapshot?.questions_exhausted;
  const canAnswer = connection === "connected" && !completed && !exhausted && snapshot?.turn_state === "WAITING_STUDENT" && !!snapshot.current_question && !sending && !speaking && !audioBlocked && !questionPending && serverState !== "jury.speaking" && !closing && !closeDialog;
  useEffect(()=>{recordingEligibility.current=Boolean(canAnswer && mode==="voice");},[canAnswer,mode]);
  async function startRecording() {
    if (!canAnswer || startingRecording.current || recording) return;
    startingRecording.current = true; setError("");
    let stream: MediaStream | undefined;
    const requestedSocket=socket.current;
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") throw new Error("Este navegador no admite grabación de voz. Usa el modo texto.");
      stream = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}});
      if (!mounted.current || !recordingEligibility.current || socket.current!==requestedSocket || socket.current?.readyState !== WebSocket.OPEN) {stream.getTracks().forEach(track => track.stop()); return;}
      if(!stream.getAudioTracks().length)throw new Error("El dispositivo no está enviando audio. Selecciona un micrófono en la preparación.");
      const mime = ["audio/webm;codecs=opus","audio/webm","audio/mp4"].find(type => MediaRecorder.isTypeSupported(type));
      if (!mime) throw new Error("No hay un formato de audio compatible. Usa el modo texto.");
      stopPlayback();
      const ws = socket.current, messageId = crypto.randomUUID();
      const media = new MediaRecorder(stream,{mimeType:mime}); recorder.current = media; recordingStream.current = stream;
      activeUtterance.current=messageId;
      ws.send(JSON.stringify({type:"voice.utterance.start",message_id:messageId,payload:{mime_type:mime}}));
      media.ondataavailable = event => {if (event.data.size && ws.readyState === WebSocket.OPEN) ws.send(event.data);};
      media.onstop = () => {if (ws.readyState === WebSocket.OPEN) {ws.send(JSON.stringify({type:"voice.utterance.end",message_id:messageId})); if (mounted.current) setSending(true);}};
      media.onerror=()=>{autoListenRef.current=false;setAutoListen(false);stopMedia(false);setError("La grabación se interrumpió. Revisa el micrófono y vuelve a comenzar tu respuesta.");};
      media.start(500); setRecording(true); setTranscription("");
      // Warm only the next existing bank question while the student answers.
      // Follow-ups are still decided from the completed answer on the server.
      void fetch(`${API_URL}/simulations/${id}/speech/prewarm`,{method:"POST",credentials:"include"}).catch(()=>undefined);
      const context = new AudioContext(); voiceContext.current = context;
      void context.resume().catch(() => {
        if (voiceContext.current !== context || !mounted.current) return;
        autoListenRef.current = false; setAutoListen(false); stopMedia(false);
        setError("No se pudo activar el audio del micrófono. Intenta comenzar de nuevo o responde por texto.");
      });
      const analyzer = context.createAnalyser(); analyzer.fftSize = 512; context.createMediaStreamSource(stream).connect(analyzer);
      const samples = new Uint8Array(analyzer.fftSize);
      const endDetector=new TurnEndDetector(performance.now());
      const meter = () => {
        if (media.state !== "recording") return;
        analyzer.getByteTimeDomainData(samples);
        const rms = Math.sqrt(samples.reduce((sum,sample) => sum + ((sample-128)/128)**2,0)/samples.length);
        setVolume(Math.min(100,Math.round(rms*400)));
        if(closeDialogRef.current)endDetector.pause(performance.now());
        else if(autoListenRef.current){
          const action=endDetector.update(rms,performance.now());
          if(action==="submit"){stopMedia();setNotice("Respuesta enviada después de cuatro segundos de pausa.");return;}
          if(action==="empty"){autoListenRef.current=false;setAutoListen(false);stopMedia(false);setServerState("");setNotice("No se recibió suficiente sonido. Pausamos el micrófono automático; puedes activarlo o comenzar una respuesta cuando estés listo.");return;}
        }
      };
      // Audio turn detection must not depend on rendering frames. Sampling at
      // 12.5 Hz also avoids updating React for every display refresh.
      volumeTimer.current = setInterval(meter,80);
      recordingLimit.current = setTimeout(() => {
        if (!endDetector.hasSpeech) {
          autoListenRef.current = false; setAutoListen(false); stopMedia(false);
          setNotice("No se detectó suficiente sonido para enviar una respuesta. Revisa tu micrófono o responde por texto.");
          return;
        }
        stopMedia(); setNotice("Respuesta enviada al alcanzar dos minutos de grabación.");
      },120000);
    } catch (err) {autoListenRef.current=false;setAutoListen(false);stopMedia(false); stream?.getTracks().forEach(track => track.stop()); setError(err instanceof DOMException && err.name==="NotAllowedError" ? "Permiso de micrófono denegado. Habilítalo en el navegador o responde por texto." : err instanceof DOMException && err.name==="NotFoundError" ? "No se encontró un micrófono. Conecta uno o responde por texto." : err instanceof DOMException && err.name==="NotReadableError" ? "No se pudo abrir el micrófono. Revisa si otra aplicación lo está usando." : err instanceof Error ? err.message : "No pudimos iniciar el micrófono.");}
    finally {startingRecording.current = false;}
  }
  const beginAutomaticTurn=useEffectEvent(()=>void startRecording());
  useEffect(()=>{
    if (interruptRequested.current && canAnswer && !recording) {
      const timer=setTimeout(()=>{interruptRequested.current=false;if(mode==="voice")beginAutomaticTurn();},0);
      return ()=>clearTimeout(timer);
    }
  },[canAnswer,recording,mode]);
  useEffect(()=>{
    if(!autoListen || mode!=="voice" || !simulation?.microphone_ready || !canAnswer || recording)return;
    const turn=`${id}:${snapshot?.current_question?.id}:${snapshot?.last_sequence}`;
    if(autoAttempt.current===turn)return;
    const timer=setTimeout(()=>{autoAttempt.current=turn;beginAutomaticTurn();},2000);
    return ()=>clearTimeout(timer);
  },[autoListen,mode,simulation?.microphone_ready,canAnswer,recording,id,snapshot?.current_question?.id,snapshot?.last_sequence]);
  function submit() {
    const content = answer.trim();
    if (!canAnswer || !snapshot?.current_question || !content || pending.current || socket.current?.readyState !== WebSocket.OPEN) return;
    const message: AnswerMessage = {type:"answer.submit",message_id:crypto.randomUUID(),payload:{question_id:snapshot.current_question.id,content}};
    pending.current = message; setSending(true); setError(""); socket.current.send(JSON.stringify(message));
  }
  function closeSession() {
    if (socket.current?.readyState !== WebSocket.OPEN) {setError("Reconecta antes de finalizar la sesión."); setCloseDialog(false); return;}
    stopMedia(false); stopPlayback(); setClosing(true); setCloseDialog(false); socket.current.send(JSON.stringify({type:"session.close"}));
  }
  const speech = analyzeTranscript(transcription);
  const elapsed = snapshot ? Math.max(0,Math.floor(((snapshot.finished_at ? new Date(snapshot.finished_at).getTime() : now || new Date(snapshot.started_at).getTime()) - new Date(snapshot.started_at).getTime())/1000)) : 0;
  const progress = snapshot?.total_questions ? Math.min(100,snapshot.answered_questions/snapshot.total_questions*100) : 0;
  const statusText = completed ? "Práctica finalizada" : closing ? "Cerrando sesión…" : connection !== "connected" ? "Recuperando conexión…" : recording ? "Te escuchamos. Envía cuando termines tu idea." : voiceLoading ? "Preparando la voz del jurado…" : speaking ? "El jurado está hablando" : sending || serverState === "jury.thinking" ? "Procesando tu respuesta…" : exhausted ? "Preguntas completadas. Finaliza para consultar tu evaluación." : canAnswer ? "Tu turno. Respira, organiza tu idea y responde." : "Esperando al tribunal…";
  return <main className="defense-room"><header className="room-topbar"><Link href={`/simulations/${id}`}><ArrowLeft size={17}/> Volver a preparación</Link><span className="room-session-title">{simulation?.document.name || "Sala de práctica"}</span><span className={`room-connection ${connection}`}><i/>{completed ? "Finalizada" : {connected:"Conectado",connecting:"Conectando",reconnecting:"Reconectando",offline:"Sin conexión"}[connection]}</span></header>
    {!snapshot ? <section className="room-loading">{error ? <><AlertCircle size={30}/><h1>No pudimos abrir tu sala</h1><p role="alert">{error}</p><button className="button button-primary" onClick={() => window.location.reload()}>Reintentar</button></> : <><LoadingSkeleton label="Preparando tu tribunal…" rows={3}/></>}</section> : <div className="room-grid"><section className="room-main">
      <div className="room-session-bar"><div><p className="room-kicker">PRÁCTICA PERSONAL</p><h1>Defiende tus ideas.</h1></div><div className="room-clock"><Clock3 size={16}/>{timeLabel(elapsed)}<small>/ {simulation?.planned_duration_minutes ?? "—"} min</small></div>{!completed && <button type="button" className="room-end-button" disabled={closing || connection !== "connected" || sending} onClick={() => setCloseDialog(true)}>Finalizar</button>}</div>
      <LiveVisualCoach quality={quality} presence={presence} face={faceSignals} pose={signals} torsoTilt={torsoTilt} status={cameraStatus} appearance={appearance} frames={tracking.frames} busy={speaking||questionPending||recording||sending} onSpeak={speakText}/>
      <TalkingJuryAvatar isPreparingVoice={voiceLoading} onInterrupt={() => {interruptRequested.current=true;autoAttempt.current="";stopPlayback();setServerState("");setNotice("Has interrumpido al jurado. Continúa con tu respuesta.");}} speechMotion={speechMotion} juryName={simulation?.jury_profile.name} strictness={simulation?.jury_profile.strictness} focusType={simulation?.jury_profile.focus_type === "TECHNICAL" ? "Enfoque técnico" : simulation?.jury_profile.focus_type === "CRITICAL" ? "Enfoque crítico" : "Enfoque metodológico"} isSpeaking={speaking} isListening={Boolean(canAnswer || recording)} isThinking={sending || serverState === "jury.thinking"} activeSpeakerIndex={(snapshot.current_question?.position ?? 1)-1} onSpeakQuestion={() => snapshot.current_question && speakText(snapshot.current_question.text)} canSpeakQuestion={!completed && !recording && !!snapshot.current_question}/>
      <section className="room-question"><div className="room-question-meta"><span>{completed ? "RESUMEN DE SESIÓN" : exhausted ? "PREGUNTAS COMPLETADAS" : `PREGUNTA ${snapshot.current_question?.position ?? snapshot.answered_questions + 1}`}</span><small>{snapshot.answered_questions} / {snapshot.total_questions} respondidas</small></div><div className="room-progress" role="progressbar" aria-label="Preguntas respondidas" aria-valuenow={snapshot.answered_questions} aria-valuemax={snapshot.total_questions} aria-valuemin={0}><i style={{width:`${progress}%`}}/></div><h2>{completed ? "Cada intento te prepara mejor." : exhausted ? "Has completado las preguntas disponibles." : snapshot.current_question?.text ?? "Preparando la siguiente pregunta…"}</h2><p className="room-turn-status" role="status"><span className={recording ? "recording-indicator" : ""}/>{statusText}</p>{completed && <Link href={`/simulations/${id}/report`} className="button button-primary">Ver evaluación <CheckCircle2 size={17}/></Link>}</section>
      {error && <div className="room-alert" role="alert">{error}</div>}{notice && <div className="room-notice" role="status">{notice}<button aria-label="Cerrar aviso" onClick={() => setNotice("")}>×</button></div>}
      {!completed && !exhausted && <section className="room-response"><div className="room-mode-switch" role="group" aria-label="Modo de respuesta"><button disabled={recording || sending} aria-pressed={mode === "voice"} onClick={() => {autoAttempt.current="";setMode("voice");saveSessionPreferences(id,{mode:"voice"});}}><Mic size={16}/> Voz</button><button disabled={recording || sending} aria-pressed={mode === "text"} onClick={() => {setMode("text");saveSessionPreferences(id,{mode:"text"});}}><Keyboard size={16}/> Texto</button></div>{mode === "voice" ? <div className="room-voice-response"><div><label className="coach-voice-toggle"><input type="checkbox" checked={autoListen} onChange={event=>{autoListenRef.current=event.target.checked;autoAttempt.current="";setAutoListen(event.target.checked);saveSessionPreferences(id,{autoListen:event.target.checked});}}/> Conversación automática</label><h3>{recording ? "Tienes la palabra" : "Responde a tu ritmo"}</h3><p>{autoListen ? "El micrófono se abre en tu turno y envía tras cuatro segundos de silencio. Máximo dos minutos; también puedes enviar antes." : "Pulsa comenzar para responder y enviar al terminar; máximo dos minutos por respuesta."}</p></div><button className={`room-record-button ${recording ? "recording" : ""}`} disabled={!recording && !canAnswer} onClick={() => recording ? stopMedia() : void startRecording()}>{recording ? <Square size={18}/> : <Mic size={19}/>} {recording ? "Enviar respuesta" : "Comenzar respuesta"}</button></div> : <form onSubmit={event => {event.preventDefault(); submit();}}><label htmlFor="defense-answer">Tu respuesta</label><textarea id="defense-answer" value={answer} maxLength={10000} rows={5} disabled={!canAnswer} onChange={event => setAnswer(event.target.value)} placeholder="Explica tu argumento y relaciónalo con tu investigación…"/><div className="room-compose-footer"><small>{answer.length} / 10 000</small><button type="submit" className="button button-primary" disabled={!canAnswer || !answer.trim()}><Send size={16}/>{sending ? "Enviando…" : "Enviar respuesta"}</button></div></form>}</section>}
      <details className="room-transcript"><summary>Conversación de esta sesión <span>{snapshot.transcript.length} {snapshot.transcript.length === 1 ? "intervención" : "intervenciones"}</span></summary><ol>{snapshot.transcript.map(turn => <li className={`speaker-${turn.speaker.toLowerCase()}`} key={turn.id}><strong>{turn.speaker === "STUDENT" ? "Tú" : turn.speaker === "JURY" ? "Tribunal" : "Sesión"}</strong><p>{turn.content}</p></li>)}</ol></details>
    </section><aside className="room-insights"><section className="room-camera-card"><header><h2>Tu espacio</h2><button aria-label={cameraEnabled ? "Desactivar cámara" : "Activar cámara"} disabled={completed} onClick={() => {setCameraEnabled(!cameraEnabled);saveSessionPreferences(id,{cameraEnabled:!cameraEnabled});}} className="room-icon-button">{cameraEnabled ? <CameraOff size={17}/> : <Camera size={17}/>}</button></header>{cameras.length>1 && <label className="camera-device-picker">Cámara<select value={cameraDeviceId} onChange={event=>setCameraDeviceId(event.target.value)}><option value="">Predeterminada</option>{cameras.map((device,index)=><option key={device.deviceId||index} value={device.deviceId}>{device.label||`Cámara ${index+1}`}</option>)}</select></label>}<div className={`room-camera-preview ${cameraEnabled ? "enabled" : ""}`}><video ref={videoRef} autoPlay muted playsInline/><CameraTrackingOverlay videoRef={videoRef} face={tracking.face} pose={tracking.pose} away={faceSignals.direction==="away"}/>{!cameraEnabled && <div><CameraOff size={26}/><strong>Cámara opcional</strong><span>Actívala para revisar tu encuadre</span></div>}{cameraEnabled && cameraStatus !== "ready" && <span className="room-camera-state">{cameraStatus === "error" ? "Análisis no disponible" : "Iniciando cámara…"}</span>}</div>{cameraError && <p className="room-camera-error" role="status">{cameraError}</p>}{cameraEnabled && <button type="button" className="room-text-button" onClick={restart}>Reiniciar cámara</button>}<p className="room-privacy">Presencia, mirada y postura se procesan en tu navegador. Los avisos aparecen arriba, junto al tribunal.</p></section>
      <section className="room-signal-card"><h2>Ajustar medición</h2><p className="room-privacy">Mira a la lente para calibrar la mirada y mantén los hombros visibles para fijar tu postura.</p><details className="room-diagnostics"><summary>Ver mediciones detalladas</summary><p className="room-privacy">Fotogramas analizados: {tracking.frames}. Rostros: {quality.faces??"sin medición"}. Brillo de imagen: {quality.brightness??"sin medición"}/255. Brillo del rostro: {quality.faceBrightness??"sin medición"}/255.</p><p className="room-presence" data-state={presence}><i/>{presence === "present" ? "Estás en cámara" : presence === "absent" ? "No se detecta una persona" : cameraStatus === "starting" ? "Cargando detector…" : cameraStatus === "error" ? "Detector no disponible" : cameraStatus === "ready" ? "Esperando un fotograma válido…" : "Activa la cámara para detectar presencia"}</p><dl><div><dt>Detección</dt><dd>{cameraStatus !== "ready" ? "Sin medición" : signals.reliable ? "Rostro y hombros visibles" : faceSignals.detected ? "Rostro visible; muestra los hombros" : signals.present ? "Encuadre incompleto" : "Sin detección confiable"}</dd></div><div><dt>Encuadre</dt><dd>{!signals.reliable ? "—" : signals.framing === "near" ? "Aléjate un poco" : signals.framing === "far" ? "Acércate un poco" : signals.centered ? "Centrado" : "Busca el centro"}</dd></div><div><dt>Inclinación de hombros</dt><dd>{signals.shoulderTilt === null ? "—" : `${signals.shoulderTilt}°`}</dd></div><div><dt>Manos visibles</dt><dd>{signals.handsVisible === null ? "—" : `${signals.handsVisible} de 2`}</dd></div></dl><VisualFeedback face={faceSignals} torsoTilt={torsoTilt} error={faceError}/></details><button className="room-text-button" disabled={!faceSignals.gaze} onClick={()=>{if(!calibrateGaze())setNotice("Mira a la lente y mantén el rostro quieto durante dos segundos; después vuelve a calibrar.");else setNotice("Referencia de mirada guardada. Ahora prueba mirar hacia un lado o hacia abajo.");}}>{gazeCalibrated?"Recalibrar mirada":"Calibrar mirando a la lente"}</button><button className="room-text-button" disabled={!signals.reliable} onClick={() => {if (!recalibrate()) setNotice("Mantén los hombros visibles unos segundos antes de fijar tu referencia.");}}><RotateCcw size={14}/> Fijar postura de referencia</button>{baseline !== null && signals.shoulderTilt !== null && <p className="room-privacy">Variación respecto a tu referencia: {Math.abs(signals.shoulderTilt-baseline).toFixed(1)}°. Un cambio no implica mala postura.</p>}<AppearanceFeedback compact key={`appearance-v3-${id}`} simulationId={id} videoRef={videoRef} torsoInFrame={torsoFitsFrame(tracking.pose,tracking.aspectRatio??4/3)} onStatus={setAppearance} available={cameraStatus === "ready" && presence === "present" && quality.faces===1}/></section>
      {(recording || transcription) && <section className="room-signal-card"><p className="room-kicker">RESPUESTA ORAL</p><h2>Voz y palabras</h2><div className="room-audio-meter" role="meter" aria-label="Nivel de micrófono" aria-valuemin={0} aria-valuemax={100} aria-valuenow={volume}><i style={{width:`${volume}%`}}/></div><p className="room-privacy">{recording ? volume < 5 ? "Señal baja. Acércate al micrófono." : "Micrófono captando audio" : "Micrófono en espera"}</p>{transcription ? <><dl><div><dt>Palabras transcritas</dt><dd>{speech.wordCount}</dd></div><div><dt>Posibles muletillas</dt><dd>{speech.fillers.length}</dd></div><div><dt>Palabras repetidas</dt><dd>{speech.repetitions.length}</dd></div></dl><details><summary>Última transcripción</summary><p className="room-privacy">{transcription}</p></details><p className="room-privacy">Conteos sobre la última transcripción, sujetos a errores del reconocimiento. No diagnostican fluidez.</p></> : <p className="room-privacy">Las señales de palabras aparecerán después de transcribir una respuesta oral.</p>}</section>}
    </aside></div>}
    {closeDialog && <div ref={closeDialogRef} className="room-dialog-backdrop"><section role="dialog" aria-modal="true" aria-labelledby="close-title" className="room-dialog"><h2 id="close-title">¿Finalizar tu práctica?</h2><p>Se conservarán las respuestas enviadas. Después podrás consultar la evaluación de esta sesión.{recording ? " La respuesta que estás grabando se descartará si finalizas." : ""}</p><div><button autoFocus className="button button-ghost" onClick={() => setCloseDialog(false)}>Seguir practicando</button><button className="button button-primary" onClick={closeSession}>Finalizar práctica</button></div></section></div>}
  </main>;
}
