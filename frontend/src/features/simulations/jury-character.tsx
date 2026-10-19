"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import type { TalkingHead } from "@/vendor/talkinghead.mjs";

export type SpeechMotion = {
  analyser: AnalyserNode | null;
  speaking: boolean;
  text: string;
  charIndex: number;
  startedAt: number;
  audioBuffer?: AudioBuffer;
};

const models = [
  { url: "/avatars/alex.glb", body: "M", baseline: { headRotateX: -.04, eyeBlinkLeft: .05, eyeBlinkRight: .05 }, retarget: { Neck: { z: -.01, rx: -.15 }, Neck1: { z: -.01, rx: -.15 }, Neck2: { z: -.01, rx: -.15 }, LeftShoulder: { rz: -.3 }, RightShoulder: { rz: .3 }, scaleToEyesLevel: 1, origin: { y: -.1 } } },
  { url: "/avatars/daniel.glb", body: "F", baseline: { headRotateX: -.05, eyeBlinkLeft: .15, eyeBlinkRight: .15 }, retarget: { Hips: { y: .03 }, Spine: { y: .02 }, Spine1: { y: .02, z: .01 }, Spine2: { y: .02, z: .01 }, Neck: { z: .02, y: .01 }, Head: { z: .02 }, LeftShoulder: { rx: -.5 }, RightShoulder: { rx: -.5 }, scaleToHipsLevel: 1 } },
  { url: "/avatars/academic-base.glb", body: "F", baseline: { headRotateX: -.01, eyeBlinkLeft: .05, eyeBlinkRight: .05 } },
];
const visemes = ["viseme_aa", "viseme_E", "viseme_I", "viseme_O", "viseme_U", "viseme_PP"];

export function JuryCharacter({ index, speaking, listening, thinking, animated, motion }: {
  index: number; speaking: boolean; listening: boolean; thinking: boolean;
  animated: boolean; motion?: RefObject<SpeechMotion>;
}) {
  const container = useRef<HTMLDivElement>(null);
  const head = useRef<TalkingHead | null>(null);
  const state = useRef({ speaking, listening, thinking, animated, motion });
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    state.current = { speaking, listening, thinking, animated, motion };
    if (!head.current) return;
    head.current.isSpeaking = speaking;
    if (animated) head.current.start();
    else head.current.stop();
    if (speaking) { head.current.lookAtCamera(1500); head.current.speakWithHands(0, 1); }
    else if (listening) head.current.makeEyeContact(2000);
    if (!speaking) {
      for (const key of visemes) {
        const target = head.current.mtAvatar[key];
        if (target) Object.assign(target, { newvalue: 0, needsUpdate: true });
      }
    }
  }, [speaking, listening, thinking, animated, motion, ready]);

  useEffect(() => {
    let cancelled = false;
    let instance: TalkingHead | undefined;
    let settled = false, disposed = false;
    const dispose = () => {
      if (!instance || disposed) return;
      disposed = true;
      instance.dispose();
      void instance.audioCtx.close().catch(() => undefined);
    };
    const data = new Uint8Array(256);
    let mouth = 0;
    async function load() {
      setReady(false); setError(""); setProgress(0);
      try {
        const { TalkingHead } = await import("@/vendor/talkinghead.mjs");
        if (cancelled || !container.current) return;
        instance = new TalkingHead(container.current, {
          lipsyncModules: [], cameraView: "head", cameraRotateEnable: false,
          // TalkingHead multiplies this factor by devicePixelRatio internally.
          // Cap the final render density instead of applying the screen ratio twice.
          cameraZoomEnable: false, modelFPS: 24, modelPixelRatio: Math.min(window.devicePixelRatio || 1, 1.25) / (window.devicePixelRatio || 1),
          modelMovementFactor: .35, avatarIdleEyeContact: .65, avatarIdleHeadMove: .25,
          avatarSpeakingEyeContact: .85, avatarSpeakingHeadMove: .4,
          lightAmbientIntensity: 1.5, lightDirectIntensity: 3,
          update: () => {
            if (!instance) return;
            const current = state.current;
            const speech = current.motion?.current;
            let energy = 0;
            if (current.speaking && current.animated) {
              if (speech?.analyser) {
                speech.analyser.getByteTimeDomainData(data);
                energy = Math.min(.95, Math.sqrt(data.reduce((sum, value) => sum + ((value - 128) / 128) ** 2, 0) / data.length) * 5);
              } else {
                // Browser synthesis cannot expose its PCM. Boundaries keep the
                // estimated articulation tied to the current spoken word.
                const t = (performance.now() - (speech?.startedAt ?? 0)) / 1000;
                energy = .12 + .42 * Math.abs(Math.sin(t * 11)) * Math.abs(Math.sin(t * 6.3));
              }
            }
            mouth += (energy - mouth) * .6;
            if (container.current) container.current.dataset.mouth = mouth.toFixed(3);
            const offset = speech?.analyser ? Math.floor((performance.now() - speech.startedAt) / 70) : speech?.charIndex ?? 0;
            const letter = speech?.text[(offset + Math.floor(performance.now() / 130) % 5) % Math.max(1, speech.text.length)]?.toLowerCase();
            const key = ({ a: "viseme_aa", e: "viseme_E", i: "viseme_I", o: "viseme_O", u: "viseme_U", m: "viseme_PP", b: "viseme_PP", p: "viseme_PP" } as Record<string, string>)[letter ?? ""] ?? "viseme_aa";
            for (const name of visemes) {
              const target = instance.mtAvatar[name];
              if (target) Object.assign(target, { newvalue: name === key ? mouth : 0, needsUpdate: true });
            }
          },
        });
        await instance.showAvatar({ ...models[index], avatarMood: "neutral" }, (event: ProgressEvent) => {
          if (!cancelled && event.total) setProgress(Math.round(event.loaded / event.total * 100));
        });
        settled = true;
        if (cancelled) { dispose(); return; }
        head.current = instance;
        instance.makeEyeContact(2000);
        setReady(true);
      } catch {
        settled = true; dispose();
        if (!cancelled) setError("No se pudo iniciar el personaje 3D.");
      }
    }
    void load();
    return () => { cancelled = true; head.current = null; if (settled) dispose(); };
  }, [index, attempt]);

  return <div className="jury-character" data-ready={ready} data-speaking={speaking}>
    <div ref={container} className="jury-character-canvas" role="img" aria-label={`Jurado 3D ${speaking ? "hablando" : listening ? "escuchando" : "en espera"}`} />
    {!ready && <div className="jury-character-loading" role="status">{error || `Preparando personaje 3D · ${progress}%`}{error && <button className="room-text-button" onClick={() => setAttempt(value => value + 1)}>Reintentar</button>}</div>}
  </div>;
}
