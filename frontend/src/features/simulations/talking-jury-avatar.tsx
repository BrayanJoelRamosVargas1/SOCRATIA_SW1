"use client";
import { useState, type RefObject } from "react";
import { AudioLines, Volume2, Sparkles, Pause, Play } from "lucide-react";
import { JuryCharacter, type SpeechMotion } from "./jury-character";
import { VideoJuryCharacter } from "./video-jury-character";
export interface TalkingJuryAvatarProps {
  juryName?: string; focusType?: string; strictness?: number;
  isSpeaking: boolean; isListening: boolean; isThinking: boolean;
  isPreparingVoice?: boolean;
  speechMotion?: RefObject<SpeechMotion>; micVolume?: number; activeSpeakerIndex?: number;
  observation?: { type: "posture" | "dress" | "praise" | "oratory"; message: string } | null;
  onInterrupt?: () => void; onSpeakQuestion?: () => void; canSpeakQuestion?: boolean;
}
const roster = [
  { name: "Alex", role: "Presidencia", color: "#88d8c0", skin: "#bf8868", hair: "#25373d", jacket: "#294f60" },
  { name: "Elena", role: "Metodología", color: "#c6bbf1", skin: "#e0ad88", hair: "#493432", jacket: "#584e72" },
  { name: "Valeria", role: "Análisis crítico", color: "#9cc9ec", skin: "#98664e", hair: "#242a31", jacket: "#34516d" },
];
export function TalkingJuryAvatar({juryName, focusType, strictness = 3, isSpeaking, isListening, isThinking, activeSpeakerIndex = 0, observation, onSpeakQuestion, canSpeakQuestion, speechMotion, onInterrupt, isPreparingVoice}: TalkingJuryAvatarProps) {
  const [animated, setAnimated] = useState(true);
  const [video, setVideo] = useState(true);
  const Character = video ? VideoJuryCharacter : JuryCharacter;
  const active = ((activeSpeakerIndex % 3) + 3) % 3;
  return <section className="tribunal-stage" aria-label="Tribunal virtual">
    <header className="tribunal-heading"><div><span className="room-kicker"><Sparkles size={13}/> SALA DE DEFENSA · JURADO VIRTUAL</span><h2>{juryName || "Tu tribunal de práctica"}</h2></div><button type="button" className="room-icon-button" aria-label={animated ? "Pausar animaciones" : "Activar animaciones"} aria-pressed={!animated} onClick={() => setAnimated(!animated)}>{animated ? <Pause size={16}/> : <Play size={16}/>}</button></header>
    <div className="tribunal-footer"><label>Personajes <select aria-label="Motor del jurado" value={video ? "video" : "3d"} onChange={event => setVideo(event.target.value === "video")}><option value="video">Video humano · experimental</option><option value="3d">Personajes 3D</option></select></label></div><div className="tribunal-members">{roster.map((person,index) => <article key={person.name} className={`tribunal-member ${active === index ? "selected" : ""}`} style={{"--juror-accent": person.color} as React.CSSProperties}><div className="juror-status">{active === index && isPreparingVoice ? "Preparando voz" : active === index && isSpeaking ? <><AudioLines size={12}/> Hablando</> : isThinking && active === index ? "Pensando" : (isListening || isSpeaking) && !isThinking ? "Escuchando" : "En espera"}</div><Character index={index} speaking={active === index && isSpeaking && !isPreparingVoice} listening={(isListening || isSpeaking) && !(active === index && isSpeaking) && !isThinking} thinking={isThinking} preparing={active === index && Boolean(isPreparingVoice)} animated={animated} motion={speechMotion}/><div className="juror-caption"><strong>{video && index === 2 ? "Daniel" : person.name}</strong><span>{person.role}</span></div></article>)}</div>
    <footer className="tribunal-footer">{isSpeaking && onInterrupt && <button type="button" className="room-text-button" onClick={onInterrupt}>Interrumpir y tomar la palabra</button>}<span>{focusType || "Preguntas basadas en tu investigación"} · Exigencia {strictness}/5</span>{canSpeakQuestion && onSpeakQuestion && <button type="button" onClick={onSpeakQuestion} disabled={isSpeaking} className="room-text-button"><Volume2 size={15}/> Repetir pregunta</button>}</footer>
    {observation && <p className="tribunal-observation" role="status">{observation.message}</p>}
  </section>;
}
