"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import { type SpeechMotion } from "./jury-character";

// DH_live consumes mono signed PCM16 WAV at 16 kHz. Keep playback in the parent
// so this renderer cannot double the voice or acquire the microphone.
function encodeAudio(buffer: AudioBuffer, offset: number) {
  const rate = 16000;
  const length = Math.max(0, Math.floor((buffer.duration - offset) * rate));
  const wav = new ArrayBuffer(44 + length * 2);
  const view = new DataView(wav);
  const label = (at: number, text: string) => [...text].forEach((c, i) => view.setUint8(at + i, c.charCodeAt(0)));
  label(0, "RIFF"); view.setUint32(4, wav.byteLength - 8, true); label(8, "WAVE"); label(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  label(36, "data"); view.setUint32(40, length * 2, true);
  const channels = Array.from({length: buffer.numberOfChannels}, (_, i) => buffer.getChannelData(i));
  for (let i = 0; i < length; i++) {
    const position = (offset + i / rate) * buffer.sampleRate;
    const a = Math.min(buffer.length - 1, Math.floor(position)), b = Math.min(buffer.length - 1, a + 1);
    const sample = channels.reduce((sum, channel) => sum + channel[a] + (channel[b] - channel[a]) * (position - a), 0) / channels.length;
    view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, sample)) * 32767, true);
  }
  return wav;
}

export function VideoJuryCharacter(props: {
  index: number; speaking: boolean; listening: boolean; thinking: boolean;
  animated: boolean; motion?: RefObject<SpeechMotion>;
}) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [needsLipSync, setNeedsLipSync] = useState(false);
  const sent = useRef<AudioBuffer | null>(null);
  const initialized = useRef(false);
  const latest = useRef(props);
  useEffect(() => { latest.current = props; });
  useEffect(() => {
    const receive = (event: MessageEvent) => {
      if (event.origin !== location.origin || event.source !== frame.current?.contentWindow) return;
      if (event.data?.type === "socratia.ready") { initialized.current = true; setReady(true); }
      if (event.data?.type === "socratia.error") setFailed(true);
    };
    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
  }, []);
  useEffect(() => {
    if (!needsLipSync) return;
    const timeout = setTimeout(() => { if (!initialized.current) setFailed(true); }, 30000);
    return () => clearTimeout(timeout);
  }, [needsLipSync]);
  useEffect(() => {
    // Initialization completed: the startup deadline no longer applies.
    const timer = setInterval(() => {
      const current = latest.current;
      const speech = current.motion?.current;
      if (current.speaking && speech?.audioBuffer && !failed) setNeedsLipSync(true);
      if (!ready) return;
      if (current.speaking && speech?.audioBuffer && speech.audioBuffer !== sent.current) {
        const wav = encodeAudio(speech.audioBuffer, Math.max(0, (performance.now() - speech.startedAt) / 1000));
        frame.current?.contentWindow?.postMessage({type:"socratia.audio", wav}, location.origin, [wav]);
        sent.current = speech.audioBuffer;
      } else if (!current.speaking && sent.current) {
        frame.current?.contentWindow?.postMessage({type:"socratia.stop"},location.origin);
        sent.current = null;
      }
    }, 100);
    return () => clearInterval(timer);
  }, [ready, failed]);
  useEffect(() => {
    frame.current?.contentWindow?.postMessage({type:"socratia.pause",paused:!props.animated},location.origin);
  }, [ready, props.animated]);
  useEffect(() => {
    if (ready) frame.current?.contentWindow?.postMessage({type:"socratia.listen",listening:props.listening},location.origin);
  }, [ready, props.listening]);
  const engine = needsLipSync && !failed;
  return <div className="jury-character" data-ready={ready} data-renderer="dh-live">
    <iframe ref={frame} src={`/vendor/dh-live/${engine ? "player" : "portrait"}.html?index=${props.index}`} onLoad={() => frame.current?.contentWindow?.postMessage({type:"socratia.pause",paused:!props.animated},location.origin)} title={`Jurado de video ${props.index + 1}`} style={{width:"100%",height:"100%",border:0}} />
    {engine && !ready && <div className="jury-character-loading" role="status">Preparando sincronización de labios…</div>}
  </div>;
}
