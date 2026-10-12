"use client";

import React, { useEffect, useState } from "react";

interface TalkingJuryAvatarProps {
  juryName?: string;
  focusType?: string;
  strictness?: number;
  isSpeaking: boolean;
  isListening: boolean;
  isThinking: boolean;
  observation?: {
    type: "posture" | "dress" | "praise";
    message: string;
  } | null;
  onSpeakQuestion?: () => void;
  canSpeakQuestion?: boolean;
}

export function TalkingJuryAvatar({
  juryName = "Dr. Roberto Méndez",
  focusType = "Técnico y Metodológico",
  strictness = 4,
  isSpeaking,
  isListening,
  isThinking,
  observation,
  onSpeakQuestion,
  canSpeakQuestion = false,
}: TalkingJuryAvatarProps) {
  // Viseme phase generator for realistic lip sync
  const [visemePhase, setVisemePhase] = useState<number>(0);

  useEffect(() => {
    if (!isSpeaking) return;
    const interval = setInterval(() => {
      setVisemePhase((prev) => (prev + 1) % 6);
    }, 110);
    return () => {
      clearInterval(interval);
      setVisemePhase(0);
    };
  }, [isSpeaking]);

  return (
    <div
      className="jury-stage-container"
      style={{
        background: "linear-gradient(145deg, #091724 0%, #0d2332 50%, #07131d 100%)",
        border: "1px solid rgba(45, 212, 191, 0.2)",
        borderRadius: "20px",
        padding: "1.25rem 1.5rem",
        marginBottom: "1.25rem",
        boxShadow: "0 14px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Ambient Lighting & Tribunal Stage Spotlight */}
      <div
        style={{
          position: "absolute",
          top: "-50px",
          left: "20%",
          width: "350px",
          height: "220px",
          background: isSpeaking
            ? "radial-gradient(ellipse, rgba(13, 148, 136, 0.35) 0%, transparent 70%)"
            : isListening
            ? "radial-gradient(ellipse, rgba(2, 132, 199, 0.22) 0%, transparent 70%)"
            : "radial-gradient(ellipse, rgba(255, 255, 255, 0.05) 0%, transparent 70%)",
          pointerEvents: "none",
          transition: "background 0.5s ease",
        }}
      />

      {/* Header bar: Tribunal de Grado Académico */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
          paddingBottom: "0.6rem",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              background: "rgba(45, 212, 191, 0.15)",
              color: "#2dd4bf",
              padding: "3px 10px",
              borderRadius: "12px",
              fontSize: "0.72rem",
              fontWeight: 800,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              border: "1px solid rgba(45, 212, 191, 0.3)",
              display: "flex",
              alignItems: "center",
              gap: "5px",
            }}
          >
            🏛️ SALA DE DEFENSA · TRIBUNAL EXAMINADOR DE GRADO
          </span>
          <span style={{ color: "#94a3b8", fontSize: "0.75rem", fontWeight: 600 }}>
            • Examen Oral Socrático
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              fontSize: "0.72rem",
              color: strictness >= 4 ? "#f87171" : "#fbbf24",
              background: "rgba(15, 23, 42, 0.6)",
              padding: "2px 8px",
              borderRadius: "10px",
              border: "1px solid rgba(255,255,255,0.08)",
              fontWeight: 600,
            }}
          >
            Rigor: {strictness}/5 ({strictness >= 4 ? "Tribunal Doctoral" : "Estándar"})
          </span>
          {canSpeakQuestion && onSpeakQuestion && (
            <button
              type="button"
              onClick={onSpeakQuestion}
              disabled={isSpeaking}
              style={{
                background: "rgba(13, 148, 136, 0.25)",
                border: "1px solid rgba(45, 212, 191, 0.4)",
                color: "#2dd4bf",
                borderRadius: "12px",
                padding: "3px 10px",
                fontSize: "0.72rem",
                fontWeight: 700,
                cursor: isSpeaking ? "not-allowed" : "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                transition: "all 0.2s",
              }}
            >
              🔊 {isSpeaking ? "Reproduciendo..." : "Repetir Pregunta"}
            </button>
          )}
        </div>
      </div>

      {/* Main Committee Area (President & 2 Evaluators) */}
      <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", flexWrap: "wrap" }}>
        {/* Left Side: Secondary Juror 1 (Dra. Elena Rostova - Metodología) */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            opacity: isSpeaking ? 0.65 : 0.9,
            transition: "opacity 0.3s",
            width: "72px",
          }}
        >
          <div
            style={{
              width: "60px",
              height: "60px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #1e293b, #0f172a)",
              border: "2px solid rgba(148, 163, 184, 0.3)",
              overflow: "hidden",
              boxShadow: "0 4px 10px rgba(0,0,0,0.3)",
              position: "relative",
            }}
          >
            <svg
              viewBox="0 0 100 100"
              style={{
                width: "100%",
                height: "100%",
                animation: isListening ? "sideJurorNod 6s ease-in-out infinite" : "none",
              }}
            >
              {/* Background */}
              <circle cx="50" cy="50" r="48" fill="#0c1f2e" />
              {/* Suit / Blusa formal */}
              <path d="M15 100 Q50 72 85 100 Z" fill="#1e293b" />
              <polygon points="44,72 50,88 56,72" fill="#e2e8f0" />
              {/* Neck */}
              <rect x="44" y="60" width="12" height="15" rx="2" fill="#fed7aa" />
              {/* Head */}
              <ellipse cx="50" cy="46" rx="20" ry="24" fill="#fed7aa" />
              {/* Hair */}
              <path d="M28 42 Q50 16 72 42 Q76 65 72 75 Q68 50 64 45 Q50 25 36 45 Q32 50 28 75 Z" fill="#78350f" />
              {/* Glasses */}
              <rect x="36" y="42" width="11" height="8" rx="2" fill="rgba(255,255,255,0.2)" stroke="#0f172a" strokeWidth="1.2" />
              <rect x="53" y="42" width="11" height="8" rx="2" fill="rgba(255,255,255,0.2)" stroke="#0f172a" strokeWidth="1.2" />
              <line x1="47" y1="45" x2="53" y2="45" stroke="#0f172a" strokeWidth="1.2" />
              {/* Eyes */}
              <circle cx="41.5" cy="46" r="1.8" fill="#0f172a" />
              <circle cx="58.5" cy="46" r="1.8" fill="#0f172a" />
              {/* Mouth listening */}
              <path d="M46 62 Q50 64 54 62" stroke="#991b1b" strokeWidth="1.5" fill="none" />
            </svg>
          </div>
          <span style={{ color: "#94a3b8", fontSize: "0.62rem", marginTop: "4px", fontWeight: 700, textAlign: "center" }}>
            Dra. Rostova
          </span>
          <span style={{ color: "#64748b", fontSize: "0.55rem", textAlign: "center" }}>
            Vocal Metodológico
          </span>
        </div>

        {/* Center: PRIMARY ACTIVE JUROR (Dr. Roberto Méndez / Selected Profile) with Full Lip Sync */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flex: 1, minWidth: "260px" }}>
          {/* Main Avatar Frame */}
          <div style={{ position: "relative", width: "105px", height: "105px", flexShrink: 0 }}>
            <div
              style={{
                width: "105px",
                height: "105px",
                borderRadius: "50%",
                background: "linear-gradient(135deg, #1e293b, #0f172a)",
                border: isSpeaking
                  ? "3px solid #2dd4bf"
                  : isListening
                  ? "3px solid #38bdf8"
                  : "2px solid rgba(255, 255, 255, 0.2)",
                boxShadow: isSpeaking
                  ? "0 0 25px rgba(45, 212, 191, 0.45)"
                  : isListening
                  ? "0 0 15px rgba(56, 189, 248, 0.3)"
                  : "0 6px 16px rgba(0,0,0,0.5)",
                overflow: "hidden",
                position: "relative",
                transition: "all 0.3s ease",
              }}
            >
              <svg
                viewBox="0 0 120 120"
                style={{
                  width: "100%",
                  height: "100%",
                  animation: isSpeaking
                    ? "speakerHeadBob 0.8s ease-in-out infinite"
                    : isListening
                    ? "listeningHeadNod 4s ease-in-out infinite"
                    : "none",
                  transformOrigin: "bottom center",
                }}
              >
                <defs>
                  <linearGradient id="primarySuit" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#1e293b" />
                    <stop offset="100%" stopColor="#091422" />
                  </linearGradient>
                  <linearGradient id="primarySkin" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#fed7aa" />
                    <stop offset="100%" stopColor="#fba668" />
                  </linearGradient>
                </defs>

                {/* Academic Aura */}
                <circle cx="60" cy="60" r="58" fill="#081e2b" />

                {/* Formal Suit & Shoulders */}
                <path d="M12 120 Q60 84 108 120 Z" fill="url(#primarySuit)" />

                {/* Gold Academic Lapel Pin */}
                <circle cx="34" cy="100" r="2.2" fill="#eab308" />

                {/* White Collar Shirt */}
                <polygon points="50,85 60,105 70,85" fill="#f8fafc" />
                {/* Formal Maroon Tie with realistic knot */}
                <polygon points="57,90 63,90 62,118 58,118" fill="#881337" />
                <polygon points="57,90 63,90 61,96 59,96" fill="#4c0519" />

                {/* Neck */}
                <rect x="52" y="68" width="16" height="22" rx="3" fill="#fed7aa" />

                {/* Head / Face */}
                <ellipse cx="60" cy="51" rx="25" ry="29" fill="url(#primarySkin)" />

                {/* Academic Hair (Distinguished Gray / Dark) */}
                <path d="M35 44 Q60 18 85 44 Q79 28 60 26 Q41 28 35 44 Z" fill="#475569" />
                <path d="M34 44 Q37 32 45 28 Q32 36 34 47 Z" fill="#334155" />
                <path d="M86 44 Q83 32 75 28 Q88 36 86 47 Z" fill="#334155" />

                {/* Eyebrows */}
                <path
                  d="M43 42 Q50 39 54 42"
                  stroke="#334155"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  fill="none"
                  style={{
                    transform: isSpeaking && (visemePhase === 1 || visemePhase === 4) ? "translateY(-1.2px)" : "none",
                    transition: "transform 0.1s",
                  }}
                />
                <path
                  d="M66 42 Q70 39 77 42"
                  stroke="#334155"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  fill="none"
                  style={{
                    transform: isSpeaking && (visemePhase === 1 || visemePhase === 4) ? "translateY(-1.2px)" : "none",
                    transition: "transform 0.1s",
                  }}
                />

                {/* Academic Glasses */}
                <rect x="41" y="43" width="15" height="11" rx="2" fill="rgba(255,255,255,0.18)" stroke="#0f172a" strokeWidth="1.8" />
                <rect x="64" y="43" width="15" height="11" rx="2" fill="rgba(255,255,255,0.18)" stroke="#0f172a" strokeWidth="1.8" />
                <line x1="56" y1="47" x2="64" y2="47" stroke="#0f172a" strokeWidth="1.8" />

                {/* Eyes with Blinking */}
                <g style={{ animation: "naturalEyeBlink 4s infinite", transformOrigin: "60px 48px" }}>
                  <circle cx="48.5" cy="48.5" r="2.6" fill="#0f172a" />
                  <circle cx="49.5" cy="47.5" r="0.8" fill="#ffffff" />
                  <circle cx="71.5" cy="48.5" r="2.6" fill="#0f172a" />
                  <circle cx="72.5" cy="47.5" r="0.8" fill="#ffffff" />
                </g>

                {/* Nose */}
                <path d="M60 50 L58 58 L62 58" stroke="#ea580c" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.65" />

                {/* REALISTIC MULTI-PHONEME LIP-SYNC MOUTH */}
                {isSpeaking ? (
                  visemePhase === 0 ? (
                    // Closed mouth / M, P, B consonant
                    <g>
                      <path d="M54 67 Q60 69 66 67" stroke="#991b1b" strokeWidth="2.2" strokeLinecap="round" fill="none" />
                      <line x1="56" y1="67" x2="64" y2="67" stroke="#4c0519" strokeWidth="1" />
                    </g>
                  ) : visemePhase === 1 ? (
                    // Wide Open "A / Ah" - Jaw drops, teeth visible
                    <g style={{ animation: "subtleJawDrop 0.15s ease-out" }}>
                      <ellipse cx="60" cy="69" rx="7.5" ry="5.5" fill="#450a0a" />
                      <path d="M54 66 Q60 64 66 66 L65 67 Q60 66 55 67 Z" fill="#ffffff" />
                      <ellipse cx="60" cy="72" rx="4" ry="2" fill="#ef4444" opacity="0.6" />
                      <path d="M53 66 Q60 62 67 66" stroke="#991b1b" strokeWidth="1.8" fill="none" />
                    </g>
                  ) : visemePhase === 2 ? (
                    // Round "O / U" - Puckered vowel
                    <g>
                      <ellipse cx="60" cy="68" rx="5" ry="6" fill="#450a0a" stroke="#991b1b" strokeWidth="1.5" />
                      <ellipse cx="60" cy="69" rx="3" ry="3.5" fill="#7f1d1d" />
                    </g>
                  ) : visemePhase === 3 ? (
                    // Moderate "E / I" - Stretched wide with teeth
                    <g>
                      <ellipse cx="60" cy="67.5" rx="8" ry="3" fill="#450a0a" />
                      <rect x="54" y="66" width="12" height="2" rx="0.5" fill="#ffffff" />
                      <path d="M52 67 Q60 65 68 67" stroke="#991b1b" strokeWidth="1.8" fill="none" />
                    </g>
                  ) : visemePhase === 4 ? (
                    // Open Socratic questioning
                    <g>
                      <ellipse cx="60" cy="68.5" rx="7" ry="4.5" fill="#450a0a" />
                      <path d="M55 66 Q60 65 65 66" stroke="#ffffff" strokeWidth="1.2" fill="none" />
                      <path d="M53 66 Q60 63 67 66" stroke="#991b1b" strokeWidth="1.6" fill="none" />
                    </g>
                  ) : (
                    // Soft closing
                    <g>
                      <ellipse cx="60" cy="67.5" rx="6" ry="2.5" fill="#450a0a" />
                      <path d="M54 67 Q60 66 66 67" stroke="#991b1b" strokeWidth="1.8" fill="none" />
                    </g>
                  )
                ) : isThinking ? (
                  // Thinking / Pensive mouth
                  <path d="M55 67 Q60 65 65 67" stroke="#991b1b" strokeWidth="2" strokeLinecap="round" fill="none" />
                ) : (
                  // Neutral Academic listening expression
                  <path d="M54 67.5 Q60 69.5 66 67.5" stroke="#991b1b" strokeWidth="2" strokeLinecap="round" fill="none" />
                )}
              </svg>
            </div>

            {/* Speaking / Transmitting Badge */}
            <div
              style={{
                position: "absolute",
                bottom: "-3px",
                right: "-3px",
                background: isSpeaking ? "#0d9488" : isListening ? "#0284c7" : "#334155",
                color: "#ffffff",
                borderRadius: "50%",
                width: "28px",
                height: "28px",
                display: "grid",
                placeItems: "center",
                fontSize: "13px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.5)",
                border: "2px solid #091724",
              }}
            >
              {isSpeaking ? "🔊" : isListening ? "👂" : isThinking ? "🤔" : "👔"}
            </div>
          </div>

          {/* Details of President Juror */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "2px" }}>
              <span style={{ color: "#2dd4bf", fontSize: "0.68rem", fontWeight: 700, textTransform: "uppercase" }}>
                Presidente del Tribunal
              </span>
              <span style={{ color: "#64748b", fontSize: "0.7rem" }}>• {focusType}</span>
            </div>

            <h2
              style={{
                margin: 0,
                fontSize: "1.25rem",
                fontWeight: 700,
                color: "#f8fafc",
                fontFamily: "Georgia, serif",
                letterSpacing: "-0.01em",
              }}
            >
              {juryName}
            </h2>

            <p style={{ margin: "2px 0 6px", fontSize: "0.76rem", color: "#94a3b8" }}>
              Examinador Titular · Evaluación Socrática en Tiempo Real
            </p>

            {/* Live State Capsule with Audio Equalizer */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "7px",
                  padding: "4px 10px",
                  borderRadius: "20px",
                  background: isSpeaking
                    ? "rgba(13, 148, 136, 0.25)"
                    : isListening
                    ? "rgba(2, 132, 199, 0.18)"
                    : "rgba(255, 255, 255, 0.05)",
                  border: isSpeaking
                    ? "1px solid rgba(45, 212, 191, 0.4)"
                    : isListening
                    ? "1px solid rgba(56, 189, 248, 0.3)"
                    : "1px solid rgba(255, 255, 255, 0.08)",
                  fontSize: "0.74rem",
                  fontWeight: 600,
                  color: isSpeaking ? "#2dd4bf" : isListening ? "#38bdf8" : "#cbd5e1",
                }}
              >
                {isSpeaking ? (
                  <>
                    <span style={{ display: "flex", gap: "2px", alignItems: "flex-end", height: "13px" }}>
                      <span style={{ width: "3px", height: "8px", background: "#2dd4bf", borderRadius: "1px", animation: "audioWave 0.5s infinite 0.1s" }} />
                      <span style={{ width: "3px", height: "14px", background: "#2dd4bf", borderRadius: "1px", animation: "audioWave 0.5s infinite 0.25s" }} />
                      <span style={{ width: "3px", height: "10px", background: "#2dd4bf", borderRadius: "1px", animation: "audioWave 0.5s infinite 0.4s" }} />
                    </span>
                    El Tribunal está hablando con voz activa
                  </>
                ) : isListening ? (
                  <>
                    <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#38bdf8", boxShadow: "0 0 8px #38bdf8" }} />
                    El Tribunal escucha su defensa
                  </>
                ) : isThinking ? (
                  <>
                    <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#f59e0b" }} />
                    Analizando argumentación con IA...
                  </>
                ) : (
                  <>
                    <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#64748b" }} />
                    Tribunal en sesión
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Secondary Juror 2 (Ing. Carlos Mendoza - Especialista Técnico) */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            opacity: isSpeaking ? 0.65 : 0.9,
            transition: "opacity 0.3s",
            width: "72px",
          }}
        >
          <div
            style={{
              width: "60px",
              height: "60px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #1e293b, #0f172a)",
              border: "2px solid rgba(148, 163, 184, 0.3)",
              overflow: "hidden",
              boxShadow: "0 4px 10px rgba(0,0,0,0.3)",
              position: "relative",
            }}
          >
            <svg
              viewBox="0 0 100 100"
              style={{
                width: "100%",
                height: "100%",
                animation: isListening ? "sideJurorNod 5.5s ease-in-out infinite 1s" : "none",
              }}
            >
              {/* Background */}
              <circle cx="50" cy="50" r="48" fill="#0c1f2e" />
              {/* Dark suit */}
              <path d="M15 100 Q50 72 85 100 Z" fill="#0f172a" />
              <polygon points="44,72 50,88 56,72" fill="#f8fafc" />
              <polygon points="48,76 52,76 51,96 49,96" fill="#1e3a8a" />
              {/* Neck */}
              <rect x="44" y="60" width="12" height="15" rx="2" fill="#fdba74" />
              {/* Head */}
              <ellipse cx="50" cy="46" rx="20" ry="24" fill="#fdba74" />
              {/* Short dark hair */}
              <path d="M30 40 Q50 20 70 40 Q65 26 50 24 Q35 26 30 40 Z" fill="#1e293b" />
              {/* Beard / Barbita académica */}
              <path d="M42 56 Q50 68 58 56 Q58 64 50 67 Q42 64 42 56 Z" fill="#334155" />
              {/* Eyes */}
              <circle cx="43" cy="45" r="1.8" fill="#0f172a" />
              <circle cx="57" cy="45" r="1.8" fill="#0f172a" />
              {/* Mouth */}
              <path d="M46 60 Q50 61 54 60" stroke="#7f1d1d" strokeWidth="1.5" fill="none" />
            </svg>
          </div>
          <span style={{ color: "#94a3b8", fontSize: "0.62rem", marginTop: "4px", fontWeight: 700, textAlign: "center" }}>
            Ing. Mendoza
          </span>
          <span style={{ color: "#64748b", fontSize: "0.55rem", textAlign: "center" }}>
            Vocal Técnico
          </span>
        </div>
      </div>

      {/* Reactive Biomechanics / Protocol Observation Banner */}
      {observation && (
        <div
          style={{
            marginTop: "1rem",
            padding: "0.65rem 1rem",
            borderRadius: "12px",
            background:
              observation.type === "praise"
                ? "rgba(16, 185, 129, 0.16)"
                : observation.type === "dress"
                ? "rgba(244, 63, 94, 0.16)"
                : "rgba(239, 68, 68, 0.16)",
            border:
              observation.type === "praise"
                ? "1px solid rgba(16, 185, 129, 0.45)"
                : observation.type === "dress"
                ? "1px solid rgba(244, 63, 94, 0.45)"
                : "1px solid rgba(239, 68, 68, 0.45)",
            color:
              observation.type === "praise"
                ? "#6ee7b7"
                : observation.type === "dress"
                ? "#fda4af"
                : "#fca5a5",
            fontSize: "0.8rem",
            lineHeight: 1.45,
            display: "flex",
            alignItems: "center",
            gap: "10px",
            animation: "bannerFadeIn 0.3s ease-out",
          }}
        >
          <span style={{ fontSize: "1.15rem", flexShrink: 0 }}>
            {observation.type === "praise" ? "👏" : observation.type === "dress" ? "👔" : "⚠️"}
          </span>
          <div>
            <strong style={{ color: "#ffffff" }}>
              {observation.type === "praise"
                ? "Aprobación del Tribunal: "
                : observation.type === "dress"
                ? "Protocolo de Grado: "
                : "Observación de Postura: "}
            </strong>
            {observation.message}
          </div>
        </div>
      )}

      {/* Styles & Keyframe Animations */}
      <style jsx>{`
        @keyframes naturalEyeBlink {
          0%, 94%, 100% { transform: scaleY(1); }
          96% { transform: scaleY(0.06); }
        }
        @keyframes speakerHeadBob {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          30% { transform: translateY(-1.5px) rotate(0.4deg); }
          70% { transform: translateY(0.8px) rotate(-0.3deg); }
        }
        @keyframes listeningHeadNod {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          25% { transform: translateY(2.5px) rotate(0.6deg); }
          40% { transform: translateY(0px) rotate(0deg); }
          65% { transform: translateY(2px) rotate(-0.4deg); }
        }
        @keyframes sideJurorNod {
          0%, 100% { transform: translateY(0px); }
          30% { transform: translateY(2px); }
          60% { transform: translateY(0px); }
        }
        @keyframes audioWave {
          0%, 100% { height: 4px; }
          50% { height: 14px; }
        }
        @keyframes bannerFadeIn {
          from { opacity: 0; transform: translateY(-6px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
