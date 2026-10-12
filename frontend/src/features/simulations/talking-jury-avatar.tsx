"use client";

import React from "react";

interface TalkingJuryAvatarProps {
  juryName?: string;
  focusType?: string;
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
  isSpeaking,
  isListening,
  isThinking,
  observation,
  onSpeakQuestion,
  canSpeakQuestion = false,
}: TalkingJuryAvatarProps) {
  return (
    <div className="jury-stage-container" style={{
      background: "linear-gradient(145deg, rgba(16, 47, 58, 0.95), rgba(11, 32, 42, 0.98))",
      border: "1px solid rgba(255, 255, 255, 0.12)",
      borderRadius: "20px",
      padding: "1.25rem",
      marginBottom: "1.25rem",
      boxShadow: "0 12px 36px rgba(0, 0, 0, 0.25)",
      position: "relative",
      overflow: "hidden"
    }}>
      {/* Decorative ambient lighting */}
      <div style={{
        position: "absolute",
        top: "-40px",
        left: "60px",
        width: "160px",
        height: "160px",
        background: isSpeaking ? "radial-gradient(circle, rgba(13, 148, 136, 0.35), transparent 70%)" : "radial-gradient(circle, rgba(56, 128, 135, 0.15), transparent 70%)",
        pointerEvents: "none",
        transition: "all 0.5s ease"
      }} />

      <div style={{ display: "flex", alignItems: "center", gap: "1.5rem", flexWrap: "wrap" }}>
        {/* Animated Avatar Portrait */}
        <div style={{ position: "relative", width: "110px", height: "110px", flexShrink: 0 }}>
          <div style={{
            width: "110px",
            height: "110px",
            borderRadius: "50%",
            background: "linear-gradient(135deg, #1e293b, #0f172a)",
            border: isSpeaking ? "3px solid #2dd4bf" : isListening ? "3px solid #38bdf8" : "2px solid rgba(255, 255, 255, 0.2)",
            boxShadow: isSpeaking ? "0 0 20px rgba(45, 212, 191, 0.4)" : "0 4px 14px rgba(0,0,0,0.4)",
            overflow: "hidden",
            position: "relative",
            transition: "all 0.3s ease"
          }}>
            <svg
              viewBox="0 0 120 120"
              style={{
                width: "100%",
                height: "100%",
                animation: isListening ? "headNod 4s ease-in-out infinite" : isSpeaking ? "headBob 0.6s ease-in-out infinite" : "none",
                transformOrigin: "bottom center"
              }}
            >
              <defs>
                <linearGradient id="suitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#1e293b" />
                  <stop offset="100%" stopColor="#0f172a" />
                </linearGradient>
                <linearGradient id="skinGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#fed7aa" />
                  <stop offset="100%" stopColor="#fdba74" />
                </linearGradient>
              </defs>

              {/* Background Aura */}
              <circle cx="60" cy="60" r="58" fill="#0f2633" />

              {/* Shoulders / Formal Academic Suit */}
              <path d="M15 120 Q60 85 105 120 Z" fill="url(#suitGrad)" />
              
              {/* White Formal Collar & Tie */}
              <polygon points="52,86 60,105 68,86" fill="#f8fafc" />
              <polygon points="57,92 63,92 61,118 59,118" fill="#991b1b" />

              {/* Neck */}
              <rect x="52" y="70" width="16" height="20" rx="3" fill="#fed7aa" />

              {/* Head / Face */}
              <ellipse cx="60" cy="52" rx="24" ry="29" fill="url(#skinGrad)" />

              {/* Academic Hair */}
              <path d="M36 45 Q60 20 84 45 Q78 30 60 28 Q42 30 36 45 Z" fill="#475569" />
              <path d="M35 45 Q38 33 46 30 Q33 38 35 48 Z" fill="#334155" />
              <path d="M85 45 Q82 33 74 30 Q87 38 85 48 Z" fill="#334155" />

              {/* Eyebrows */}
              <path d="M43 43 Q50 40 54 43" stroke="#334155" strokeWidth="2.5" strokeLinecap="round" fill="none" />
              <path d="M66 43 Q70 40 77 43" stroke="#334155" strokeWidth="2.5" strokeLinecap="round" fill="none" />

              {/* Academic Glasses */}
              <rect x="42" y="44" width="14" height="10" rx="2" fill="rgba(255,255,255,0.15)" stroke="#0f172a" strokeWidth="1.8" />
              <rect x="64" y="44" width="14" height="10" rx="2" fill="rgba(255,255,255,0.15)" stroke="#0f172a" strokeWidth="1.8" />
              <line x1="56" y1="48" x2="64" y2="48" stroke="#0f172a" strokeWidth="1.8" />

              {/* Eyes with blinking */}
              <g style={{ animation: "eyeBlink 3.8s infinite", transformOrigin: "60px 49px" }}>
                <circle cx="49" cy="49" r="2.6" fill="#0f172a" />
                <circle cx="50" cy="48" r="0.8" fill="#ffffff" />
                <circle cx="71" cy="49" r="2.6" fill="#0f172a" />
                <circle cx="72" cy="48" r="0.8" fill="#ffffff" />
              </g>

              {/* Nose */}
              <path d="M60 51 L58 59 L62 59" stroke="#ea580c" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.6" />

              {/* Dynamic Lip-Sync Mouth */}
              {isSpeaking ? (
                <g style={{ transformOrigin: "60px 68px", animation: "lipSync 0.22s ease-in-out infinite alternate" }}>
                  <ellipse cx="60" cy="68" rx="6.5" ry="4.5" fill="#7f1d1d" />
                  <rect x="56" y="65" width="8" height="2" rx="1" fill="#ffffff" />
                  <path d="M53 66 Q60 63 67 66" stroke="#991b1b" strokeWidth="1.5" fill="none" />
                </g>
              ) : isThinking ? (
                <path d="M56 68 Q60 66 64 68" stroke="#991b1b" strokeWidth="2" strokeLinecap="round" fill="none" />
              ) : (
                <path d="M54 68 Q60 70 66 68" stroke="#991b1b" strokeWidth="2" strokeLinecap="round" fill="none" />
              )}
            </svg>
          </div>

          {/* Active status pill on avatar badge */}
          <div style={{
            position: "absolute",
            bottom: "-3px",
            right: "-3px",
            background: isSpeaking ? "#0d9488" : isListening ? "#0284c7" : "#475569",
            color: "#ffffff",
            borderRadius: "50%",
            width: "26px",
            height: "26px",
            display: "grid",
            placeItems: "center",
            fontSize: "12px",
            boxShadow: "0 2px 6px rgba(0,0,0,0.4)",
            border: "2px solid #0f172a"
          }}>
            {isSpeaking ? "🔊" : isListening ? "👂" : isThinking ? "🤔" : "👔"}
          </div>
        </div>

        {/* Jury Details & Speaking State */}
        <div style={{ flex: 1, minWidth: "220px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginBottom: "4px" }}>
            <span style={{
              background: "rgba(45, 212, 191, 0.12)",
              color: "#2dd4bf",
              padding: "2px 8px",
              borderRadius: "12px",
              fontSize: "0.68rem",
              fontWeight: 700,
              letterSpacing: "0.05em",
              textTransform: "uppercase"
            }}>
              Tribunal Examinador Oficial
            </span>
            <span style={{ color: "#94a3b8", fontSize: "0.72rem" }}>
              • {focusType}
            </span>
          </div>

          <h2 style={{
            margin: 0,
            fontSize: "1.25rem",
            fontWeight: 700,
            color: "#f8fafc",
            fontFamily: "Georgia, serif",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}>
            {juryName}
          </h2>

          <p style={{ margin: "2px 0 8px", fontSize: "0.78rem", color: "#94a3b8" }}>
            Presidente del Tribunal Académico de Defensa Doctoral
          </p>

          {/* Live Action Status with Equalizer */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              borderRadius: "20px",
              background: isSpeaking ? "rgba(13, 148, 136, 0.2)" : isListening ? "rgba(2, 132, 199, 0.15)" : "rgba(255, 255, 255, 0.05)",
              border: isSpeaking ? "1px solid rgba(45, 212, 191, 0.3)" : "1px solid rgba(255, 255, 255, 0.08)",
              fontSize: "0.72rem",
              fontWeight: 600,
              color: isSpeaking ? "#2dd4bf" : isListening ? "#38bdf8" : "#cbd5e1"
            }}>
              {isSpeaking ? (
                <>
                  <span style={{ display: "flex", gap: "2px", alignItems: "flex-end", height: "12px" }}>
                    <span style={{ width: "3px", height: "8px", background: "#2dd4bf", borderRadius: "1px", animation: "audioWave 0.6s infinite 0.1s" }} />
                    <span style={{ width: "3px", height: "14px", background: "#2dd4bf", borderRadius: "1px", animation: "audioWave 0.6s infinite 0.25s" }} />
                    <span style={{ width: "3px", height: "10px", background: "#2dd4bf", borderRadius: "1px", animation: "audioWave 0.6s infinite 0.4s" }} />
                  </span>
                  El Tribunal está hablando con voz en vivo
                </>
              ) : isListening ? (
                <>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#38bdf8", boxShadow: "0 0 8px #38bdf8" }} />
                  El Tribunal escucha atentamente su respuesta
                </>
              ) : isThinking ? (
                <>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#f59e0b" }} />
                  Evaluando argumentación técnica con IA...
                </>
              ) : (
                <>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#64748b" }} />
                  Tribunal en sesión
                </>
              )}
            </div>

            {canSpeakQuestion && onSpeakQuestion && (
              <button
                type="button"
                onClick={onSpeakQuestion}
                disabled={isSpeaking}
                style={{
                  background: "rgba(255, 255, 255, 0.08)",
                  border: "1px solid rgba(255, 255, 255, 0.18)",
                  color: "#f8fafc",
                  borderRadius: "16px",
                  padding: "4px 10px",
                  fontSize: "0.72rem",
                  cursor: isSpeaking ? "not-allowed" : "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  transition: "background 0.2s"
                }}
              >
                🔊 {isSpeaking ? "Reproduciendo..." : "Escuchar voz"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Reactive Biomechanics / Protocol Observation Bubble */}
      {observation && (
        <div
          style={{
            marginTop: "0.85rem",
            padding: "0.6rem 0.9rem",
            borderRadius: "10px",
            background: observation.type === "praise" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
            border: observation.type === "praise" ? "1px solid rgba(16, 185, 129, 0.4)" : "1px solid rgba(239, 68, 68, 0.4)",
            color: observation.type === "praise" ? "#6ee7b7" : "#fca5a5",
            fontSize: "0.78rem",
            lineHeight: 1.4,
            display: "flex",
            alignItems: "center",
            gap: "8px",
            animation: "fadeIn 0.3s ease"
          }}
        >
          <span style={{ fontSize: "1rem" }}>
            {observation.type === "praise" ? "👏" : "⚠️"}
          </span>
          <div>
            <strong>Intervención del Tribunal:</strong> {observation.message}
          </div>
        </div>
      )}

      {/* Keyframe Styles for Avatar Lip-Sync and Gestures */}
      <style jsx>{`
        @keyframes lipSync {
          0% { transform: scaleY(0.2) scaleX(0.85); }
          30% { transform: scaleY(1.1) scaleX(1.15); }
          60% { transform: scaleY(0.5) scaleX(0.95); }
          100% { transform: scaleY(1.3) scaleX(1.2); }
        }
        @keyframes eyeBlink {
          0%, 92%, 100% { transform: scaleY(1); }
          95% { transform: scaleY(0.08); }
        }
        @keyframes headNod {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          35% { transform: translateY(2.5px) rotate(0.6deg); }
          50% { transform: translateY(0px) rotate(0deg); }
          75% { transform: translateY(2.5px) rotate(-0.5deg); }
        }
        @keyframes headBob {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-1.5px); }
        }
        @keyframes audioWave {
          0%, 100% { height: 4px; }
          50% { height: 14px; }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
