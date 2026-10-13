"use client";

import React, { useEffect, useState } from "react";

export interface TalkingJuryAvatarProps {
  juryName?: string;
  focusType?: string;
  strictness?: number;
  isSpeaking: boolean;
  isListening: boolean;
  isThinking: boolean;
  micVolume?: number;
  activeSpeakerIndex?: number; // 0 = Dr. Méndez, 1 = Dra. Rostova, 2 = Ing. Mendoza
  observation?: {
    type: "posture" | "dress" | "praise" | "oratory";
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
  micVolume = 0,
  activeSpeakerIndex = 0,
  observation,
  onSpeakQuestion,
  canSpeakQuestion = false,
}: TalkingJuryAvatarProps) {
  // Speech pulse for synchronized mouth/jaw cadence
  const [speechPulse, setSpeechPulse] = useState<number>(0);
  // Interactive click speech bubble for jurors
  const [clickedJurorQuote, setClickedJurorQuote] = useState<{ id: number; text: string } | null>(null);
  // Micro-gesture cycle (simulates living autonomous behavior: adjusting glasses, writing notes, coffee sip)
  const [gesturePhase, setGesturePhase] = useState<number>(0);

  useEffect(() => {
    if (!isSpeaking) return;
    const interval = setInterval(() => {
      setSpeechPulse((prev) => (prev + 1) % 4);
    }, 130);
    return () => clearInterval(interval);
  }, [isSpeaking]);

  const speechCadence = isSpeaking ? speechPulse : 0;

  // Autonomous life engine (switches random living actions every 7 seconds)
  useEffect(() => {
    const lifeTimer = setInterval(() => {
      setGesturePhase((prev) => (prev + 1) % 6);
    }, 6500);
    return () => clearInterval(lifeTimer);
  }, []);

  const activeIndex = activeSpeakerIndex % 3;

  // Real academic jury roster with authentic photographic portraits and unique personal reactions
  const jurors = [
    {
      id: 0,
      name: juryName || "Dr. Roberto Méndez",
      role: "Presidente del Tribunal",
      specialty: focusType || "Fundamentos Epistemológicos & Rigor",
      shortName: "Dr. R. Méndez",
      imageSrc: "/avatars/juror_mendez.jpg",
      accentColor: "#2dd4bf",
      badgeText: "PRESIDENTE DOCTORAL",
      interactiveQuote: "«Postulante, argumente con serenidad y sustente el rigor epistemológico de su propuesta.»",
      deskProp: "⚖️ Mazo de Grado & Expediente Oficial",
      idleStateText: gesturePhase % 3 === 0 ? "Acomodando sus anteojos..." : "Observando atentamente tu postura",
    },
    {
      id: 1,
      name: "Dra. Elena Rostova",
      role: "Vocal Metodológico",
      specialty: "Metodología, Hipótesis & Validación Empírica",
      shortName: "Dra. E. Rostova",
      imageSrc: "/avatars/juror_rostova.jpg",
      accentColor: "#c084fc",
      badgeText: "VOCAL METODOLÓGICO",
      interactiveQuote: "«Coteje sus hipótesis y variables dependientes con los datos empíricos de su tesis.»",
      deskProp: "📓 Cuaderno de Rúbrica & Pluma Estilográfica",
      idleStateText: gesturePhase % 2 === 0 ? "Anotando observaciones en libreta..." : "Revisando metodología del PDF",
    },
    {
      id: 2,
      name: "Ing. Carlos Mendoza",
      role: "Vocal Técnico",
      specialty: "Arquitectura de Software & Viabilidad Técnica",
      shortName: "Ing. C. Mendoza",
      imageSrc: "/avatars/juror_mendoza.jpg",
      accentColor: "#38bdf8",
      badgeText: "VOCAL TÉCNICO",
      interactiveQuote: "«Queremos evaluar los patrones de diseño, complejidad asintótica y viabilidad en producción.»",
      deskProp: "☕ Taza de Café & Especificación Técnica",
      idleStateText: gesturePhase % 3 === 1 ? "Bebiendo un sorbo de café..." : "Analizando arquitectura de software",
    },
  ];

  const activeJuror = jurors[activeIndex] || jurors[0];

  function handleJurorClick(juror: typeof jurors[0]) {
    setClickedJurorQuote({ id: juror.id, text: juror.interactiveQuote });
    setTimeout(() => {
      setClickedJurorQuote((curr) => (curr?.id === juror.id ? null : curr));
    }, 5500);
  }

  return (
    <div
      className="jury-stage-container"
      style={{
        background: "radial-gradient(ellipse at 50% 0%, #0c2738 0%, #071722 55%, #02090e 100%)",
        border: "1px solid rgba(45, 212, 191, 0.3)",
        borderRadius: "20px",
        padding: "1rem 1.25rem",
        marginBottom: "0.85rem",
        boxShadow: "0 18px 45px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.12)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Ambient Moving Spotlight following the active speaker */}
      <div
        style={{
          position: "absolute",
          top: "-70px",
          left: activeIndex === 0 ? "50%" : activeIndex === 1 ? "18%" : "82%",
          transform: "translateX(-50%)",
          width: "440px",
          height: "240px",
          background: isSpeaking
            ? `radial-gradient(ellipse, ${activeJuror.accentColor}35 0%, transparent 70%)`
            : isListening
            ? "radial-gradient(ellipse, rgba(56, 189, 248, 0.22) 0%, transparent 70%)"
            : "radial-gradient(ellipse, rgba(255, 255, 255, 0.08) 0%, transparent 70%)",
          pointerEvents: "none",
          transition: "left 0.65s cubic-bezier(0.4, 0, 0.2, 1), background 0.4s ease",
        }}
      />

      {/* Header bar: Tribunal de Grado */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "0.85rem",
          paddingBottom: "0.6rem",
          borderBottom: "1px solid rgba(255, 255, 255, 0.09)",
          flexWrap: "wrap",
          gap: "0.4rem",
          position: "relative",
          zIndex: 2,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <span
            style={{
              background: "linear-gradient(135deg, rgba(45, 212, 191, 0.22), rgba(13, 148, 136, 0.12))",
              color: "#2dd4bf",
              padding: "3px 10px",
              borderRadius: "12px",
              fontSize: "0.72rem",
              fontWeight: 800,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              border: "1px solid rgba(45, 212, 191, 0.4)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            🏛️ TRIBUNAL EXAMINADOR VIRTUAL
          </span>
          <span style={{ color: "#94a3b8", fontSize: "0.7rem", fontWeight: 600 }}>
            • Interacción Viva 360° (Haz clic en un jurado para interactuar)
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              fontSize: "0.7rem",
              color: strictness >= 4 ? "#f87171" : "#fbbf24",
              background: "rgba(15, 23, 42, 0.8)",
              padding: "2px 8px",
              borderRadius: "8px",
              border: "1px solid rgba(255,255,255,0.1)",
              fontWeight: 700,
            }}
          >
            ⚖️ Rigor: {strictness}/5
          </span>
          {canSpeakQuestion && onSpeakQuestion && (
            <button
              type="button"
              onClick={onSpeakQuestion}
              disabled={isSpeaking}
              style={{
                background: "rgba(13, 148, 136, 0.28)",
                border: "1px solid rgba(45, 212, 191, 0.45)",
                color: "#2dd4bf",
                borderRadius: "10px",
                padding: "2px 9px",
                fontSize: "0.7rem",
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

      {/* Main 3D Courtroom Bench with Autonomous Living Humans */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1.25fr 1fr",
          gap: "1rem",
          alignItems: "end",
          position: "relative",
          zIndex: 2,
          paddingBottom: "0.85rem",
        }}
      >
        {jurors.map((juror) => {
          const isCurrentActive = activeIndex === juror.id;
          const isSide = juror.id !== 0;
          const isNoteTaking = isListening && micVolume > 15 && isSide;
          const hasSpeechBubble = clickedJurorQuote?.id === juror.id;

          // Natural lifelike idle micro-animation selection
          let avatarAnimation = "livingBreathing 4s ease-in-out infinite";
          if (isCurrentActive && isSpeaking) {
            avatarAnimation = "speakingCadence 0.8s ease-in-out infinite";
          } else if (isNoteTaking) {
            avatarAnimation = "noteTakingGaze 2.2s ease-in-out infinite";
          } else if (isListening && micVolume > 12) {
            avatarAnimation = "attentiveNod 2.5s ease-in-out infinite";
          } else if (gesturePhase % 4 === juror.id) {
            avatarAnimation = "livingGazeShift 5s ease-in-out infinite";
          }

          return (
            <div
              key={juror.id}
              onClick={() => handleJurorClick(juror)}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                transform: isCurrentActive ? "scale(1.04)" : "scale(0.96)",
                opacity: isCurrentActive ? 1 : isSpeaking ? 0.72 : 0.94,
                transition: "all 0.35s cubic-bezier(0.4, 0, 0.2, 1)",
                cursor: "pointer",
                position: "relative",
              }}
              title="Haz clic para interactuar con este miembro del jurado"
            >
              {/* Dynamic Interactive Speech Balloon (Mascota de escritorio style) */}
              {(hasSpeechBubble || (isCurrentActive && isSpeaking)) && (
                <div
                  style={{
                    position: "absolute",
                    top: isSide ? "-64px" : "-74px",
                    background: "rgba(10, 23, 38, 0.96)",
                    border: `1.5px solid ${juror.accentColor}`,
                    borderRadius: "14px",
                    padding: "6px 12px",
                    color: "#f8fafc",
                    fontSize: "0.72rem",
                    fontWeight: 600,
                    lineHeight: 1.35,
                    boxShadow: "0 6px 20px rgba(0,0,0,0.6)",
                    zIndex: 10,
                    width: "210px",
                    textAlign: "center",
                    animation: "balloonPop 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275)",
                    pointerEvents: "none",
                  }}
                >
                  <span style={{ color: juror.accentColor, fontWeight: 800, display: "block", fontSize: "0.66rem", marginBottom: "2px" }}>
                    💬 {juror.shortName} dice:
                  </span>
                  {hasSpeechBubble ? clickedJurorQuote?.text : "«Formulando pregunta a la defensa académica...»"}
                  <div
                    style={{
                      position: "absolute",
                      bottom: "-7px",
                      left: "50%",
                      transform: "translateX(-50%)",
                      width: 0,
                      height: 0,
                      borderLeft: "7px solid transparent",
                      borderRight: "7px solid transparent",
                      borderTop: `7px solid ${juror.accentColor}`,
                    }}
                  />
                </div>
              )}

              {/* Realistic Living Human Frame */}
              <div
                style={{
                  position: "relative",
                  width: isSide ? "90px" : "112px",
                  height: isSide ? "90px" : "112px",
                  borderRadius: "50%",
                  border: isCurrentActive && isSpeaking
                    ? `3.5px solid ${juror.accentColor}`
                    : `2.5px solid ${isCurrentActive ? juror.accentColor : "rgba(148, 163, 184, 0.4)"}`,
                  boxShadow: isCurrentActive && isSpeaking
                    ? `0 0 28px ${juror.accentColor}75, 0 8px 24px rgba(0,0,0,0.6)`
                    : isListening
                    ? "0 0 16px rgba(56, 189, 248, 0.3)"
                    : "0 8px 18px rgba(0,0,0,0.5)",
                  overflow: "hidden",
                  background: "#0f172a",
                  animation: avatarAnimation,
                  transformOrigin: "bottom center",
                }}
              >
                {/* Photographic portrait */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={juror.imageSrc}
                  alt={juror.name}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    objectPosition: "top center",
                    transform: isCurrentActive && isSpeaking
                      ? speechCadence % 2 === 1 ? "scale(1.04) translateY(-1px)" : "scale(1.01)"
                      : isNoteTaking
                      ? "scale(0.98) translateY(2px)"
                      : "scale(1)",
                    transition: "transform 0.15s ease",
                  }}
                />

                {/* Sub-chin conference microphone status LED */}
                <div
                  style={{
                    position: "absolute",
                    bottom: "4px",
                    right: "4px",
                    width: "14px",
                    height: "14px",
                    borderRadius: "50%",
                    background: isCurrentActive && isSpeaking ? juror.accentColor : isNoteTaking ? "#eab308" : "#1e293b",
                    border: "2px solid #091724",
                    boxShadow: isCurrentActive && isSpeaking ? `0 0 10px ${juror.accentColor}` : "none",
                    transition: "all 0.2s",
                  }}
                />
              </div>

              {/* Status Pill & Golden Nameplate */}
              <div
                style={{
                  marginTop: "6px",
                  padding: "3px 6px",
                  background: isCurrentActive
                    ? "linear-gradient(180deg, #2b2112 0%, #151008 100%)"
                    : "linear-gradient(180deg, #1e293b 0%, #0f172a 100%)",
                  border: isCurrentActive ? "1px solid #eab308" : "1px solid rgba(255,255,255,0.12)",
                  borderRadius: "6px",
                  boxShadow: "0 3px 8px rgba(0,0,0,0.5)",
                  textAlign: "center",
                  width: "100%",
                  maxWidth: isSide ? "112px" : "136px",
                }}
              >
                <div
                  style={{
                    color: isCurrentActive ? "#fef08a" : "#f1f5f9",
                    fontSize: isSide ? "0.68rem" : "0.76rem",
                    fontWeight: 800,
                    letterSpacing: "0.02em",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {juror.shortName}
                </div>
                <div
                  style={{
                    color: isCurrentActive ? juror.accentColor : "#94a3b8",
                    fontSize: "0.56rem",
                    fontWeight: 700,
                  }}
                >
                  {juror.role}
                </div>
              </div>

              {/* Live Autonomous Activity Caption */}
              <div
                style={{
                  marginTop: "3px",
                  fontSize: "0.55rem",
                  color: isCurrentActive && isSpeaking ? juror.accentColor : "#64748b",
                  fontWeight: 600,
                  textAlign: "center",
                  maxWidth: "116px",
                  lineHeight: 1.2,
                }}
              >
                {isCurrentActive && isSpeaking ? "🎙️ Hablando en sala" : isNoteTaking ? "✍️ Tomando apuntes" : juror.idleStateText}
              </div>
            </div>
          );
        })}
      </div>

      {/* Realistic Polished Mahogany Courtroom Desk with Props */}
      <div
        style={{
          position: "relative",
          margin: "0 -1.25rem -1rem -1.25rem",
          padding: "0.75rem 1.25rem 0.9rem",
          background: "linear-gradient(180deg, #382012 0%, #221208 40%, #120904 100%)",
          borderTop: "3px solid #854d0e",
          boxShadow: "inset 0 4px 14px rgba(0,0,0,0.7)",
        }}
      >
        {/* Active Speaker Dialog Capsule */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(10, 20, 32, 0.9)",
            border: `1px solid ${activeJuror.accentColor}50`,
            borderRadius: "12px",
            padding: "0.5rem 1rem",
            boxShadow: "0 4px 16px rgba(0,0,0,0.45)",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                background: isSpeaking ? activeJuror.accentColor : isListening ? "#38bdf8" : "#f59e0b",
                boxShadow: isSpeaking ? `0 0 12px ${activeJuror.accentColor}` : "none",
                display: "inline-block",
              }}
            />
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <strong style={{ color: "#ffffff", fontSize: "0.84rem" }}>
                  {activeJuror.name}
                </strong>
                <span
                  style={{
                    color: activeJuror.accentColor,
                    fontSize: "0.66rem",
                    fontWeight: 800,
                    background: `${activeJuror.accentColor}25`,
                    padding: "1px 6px",
                    borderRadius: "5px",
                    border: `1px solid ${activeJuror.accentColor}40`,
                  }}
                >
                  {activeJuror.role}
                </span>
                <span style={{ color: "#94a3b8", fontSize: "0.65rem" }}>
                  {activeJuror.deskProp}
                </span>
              </div>
              <p style={{ margin: "1px 0 0", color: "#cbd5e1", fontSize: "0.7rem" }}>
                {activeJuror.specialty}
              </p>
            </div>
          </div>

          {/* Equalizer Waveform during speech */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            {isSpeaking ? (
              <div style={{ display: "flex", gap: "3px", alignItems: "flex-end", height: "16px" }}>
                <span style={{ width: "3.5px", height: "9px", background: activeJuror.accentColor, borderRadius: "2px", animation: "audioWave 0.5s infinite 0.1s" }} />
                <span style={{ width: "3.5px", height: "16px", background: activeJuror.accentColor, borderRadius: "2px", animation: "audioWave 0.5s infinite 0.25s" }} />
                <span style={{ width: "3.5px", height: "13px", background: activeJuror.accentColor, borderRadius: "2px", animation: "audioWave 0.5s infinite 0.4s" }} />
                <span style={{ width: "3.5px", height: "7px", background: activeJuror.accentColor, borderRadius: "2px", animation: "audioWave 0.5s infinite 0.15s" }} />
              </div>
            ) : isListening ? (
              <span style={{ fontSize: "0.72rem", color: "#38bdf8", fontWeight: 700, display: "flex", alignItems: "center", gap: "4px" }}>
                👂 Evaluando tu intervención ({micVolume}%)
              </span>
            ) : isThinking ? (
              <span style={{ fontSize: "0.72rem", color: "#f59e0b", fontWeight: 700 }}>
                🤔 Deliberando rigor...
              </span>
            ) : (
              <span style={{ fontSize: "0.7rem", color: "#94a3b8" }}>
                En sesión formal
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Reactive Biomechanics & Protocol Alert Banner */}
      {observation && (
        <div
          style={{
            marginTop: "0.85rem",
            padding: "0.65rem 0.9rem",
            borderRadius: "10px",
            background:
              observation.type === "praise"
                ? "rgba(16, 185, 129, 0.18)"
                : observation.type === "dress"
                ? "rgba(244, 63, 94, 0.18)"
                : observation.type === "oratory"
                ? "rgba(245, 158, 11, 0.2)"
                : "rgba(239, 68, 68, 0.18)",
            border:
              observation.type === "praise"
                ? "1px solid rgba(16, 185, 129, 0.5)"
                : observation.type === "dress"
                ? "1px solid rgba(244, 63, 94, 0.5)"
                : observation.type === "oratory"
                ? "1px solid rgba(245, 158, 11, 0.5)"
                : "1px solid rgba(239, 68, 68, 0.5)",
            color:
              observation.type === "praise"
                ? "#6ee7b7"
                : observation.type === "dress"
                ? "#fda4af"
                : observation.type === "oratory"
                ? "#fde68a"
                : "#fca5a5",
            fontSize: "0.78rem",
            lineHeight: 1.4,
            display: "flex",
            alignItems: "center",
            gap: "8px",
            animation: "bannerFadeIn 0.3s ease-out",
            position: "relative",
            zIndex: 3,
          }}
        >
          <span style={{ fontSize: "1.1rem", flexShrink: 0 }}>
            {observation.type === "praise" ? "👏" : observation.type === "dress" ? "👔" : observation.type === "oratory" ? "🎙️" : "⚠️"}
          </span>
          <div>
            <strong style={{ color: "#ffffff" }}>
              {observation.type === "praise"
                ? "Aprobación del Tribunal: "
                : observation.type === "dress"
                ? "Protocolo de Grado: "
                : observation.type === "oratory"
                ? "Observación de Oratoria: "
                : "Observación de Postura: "}
            </strong>
            {observation.message}
          </div>
        </div>
      )}

      {/* Living Desktop Companion Keyframe Animations */}
      <style jsx>{`
        @keyframes livingBreathing {
          0%, 100% { transform: translateY(0px) scale(1); }
          50% { transform: translateY(-1.2px) scale(1.008); }
        }
        @keyframes speakingCadence {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          30% { transform: translateY(-1.6px) rotate(0.4deg); }
          70% { transform: translateY(0.8px) rotate(-0.3deg); }
        }
        @keyframes attentiveNod {
          0%, 100% { transform: translateY(0px); }
          40% { transform: translateY(2.2px); }
          70% { transform: translateY(0px); }
        }
        @keyframes noteTakingGaze {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          25% { transform: translateY(2px) rotate(0.6deg); }
          50% { transform: translateY(0.8px) rotate(-0.3deg); }
          75% { transform: translateY(1.8px) rotate(0.4deg); }
        }
        @keyframes livingGazeShift {
          0%, 100% { transform: rotate(0deg); }
          30% { transform: rotate(0.6deg) translateX(0.5px); }
          70% { transform: rotate(-0.5deg) translateX(-0.5px); }
        }
        @keyframes balloonPop {
          from { opacity: 0; transform: scale(0.8) translateY(10px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
        @keyframes audioWave {
          0%, 100% { height: 4px; }
          50% { height: 16px; }
        }
        @keyframes bannerFadeIn {
          from { opacity: 0; transform: translateY(-6px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
