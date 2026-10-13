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
  // Speech pulse for synchronized mouth and jaw micro-movement
  const [speechPulse, setSpeechPulse] = useState<number>(0);

  useEffect(() => {
    if (!isSpeaking) return;
    const interval = setInterval(() => {
      setSpeechPulse((prev) => (prev + 1) % 4);
    }, 130);
    return () => {
      clearInterval(interval);
    };
  }, [isSpeaking]);

  const activeIndex = activeSpeakerIndex % 3;

  // Real academic jury roster with authentic photographic portraits
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
    },
  ];

  const activeJuror = jurors[activeIndex] || jurors[0];

  return (
    <div
      className="jury-stage-container"
      style={{
        background: "radial-gradient(ellipse at 50% 0%, #0c2738 0%, #071722 55%, #02090e 100%)",
        border: "1px solid rgba(45, 212, 191, 0.3)",
        borderRadius: "22px",
        padding: "1.25rem 1.5rem",
        marginBottom: "1.25rem",
        boxShadow: "0 22px 55px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.12)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Dynamic Ambient Spotlight directed at the active juror */}
      <div
        style={{
          position: "absolute",
          top: "-70px",
          left: activeIndex === 0 ? "50%" : activeIndex === 1 ? "18%" : "82%",
          transform: "translateX(-50%)",
          width: "480px",
          height: "260px",
          background: isSpeaking
            ? `radial-gradient(ellipse, ${activeJuror.accentColor}40 0%, transparent 70%)`
            : isListening
            ? "radial-gradient(ellipse, rgba(56, 189, 248, 0.25) 0%, transparent 70%)"
            : "radial-gradient(ellipse, rgba(255, 255, 255, 0.08) 0%, transparent 70%)",
          pointerEvents: "none",
          transition: "left 0.7s cubic-bezier(0.4, 0, 0.2, 1), background 0.4s ease",
        }}
      />

      {/* Header bar: Tribunal de Grado */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.1rem",
          paddingBottom: "0.75rem",
          borderBottom: "1px solid rgba(255, 255, 255, 0.09)",
          flexWrap: "wrap",
          gap: "0.5rem",
          position: "relative",
          zIndex: 2,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <span
            style={{
              background: "linear-gradient(135deg, rgba(45, 212, 191, 0.22), rgba(13, 148, 136, 0.12))",
              color: "#2dd4bf",
              padding: "4px 12px",
              borderRadius: "14px",
              fontSize: "0.74rem",
              fontWeight: 800,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              border: "1px solid rgba(45, 212, 191, 0.4)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              boxShadow: "0 2px 8px rgba(45, 212, 191, 0.15)",
            }}
          >
            🏛️ TRIBUNAL EXAMINADOR DE GRADO ACADÉMICO
          </span>
          <span style={{ color: "#94a3b8", fontSize: "0.72rem", fontWeight: 600 }}>
            • Sustentación Formal en Vivo
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              fontSize: "0.72rem",
              color: strictness >= 4 ? "#f87171" : "#fbbf24",
              background: "rgba(15, 23, 42, 0.8)",
              padding: "3px 10px",
              borderRadius: "10px",
              border: "1px solid rgba(255,255,255,0.12)",
              fontWeight: 700,
            }}
          >
            ⚖️ Rigor: {strictness}/5 ({strictness >= 4 ? "Doctoral Estricto" : "Estándar"})
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
                borderRadius: "12px",
                padding: "3px 11px",
                fontSize: "0.72rem",
                fontWeight: 700,
                cursor: isSpeaking ? "not-allowed" : "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                transition: "all 0.2s",
              }}
            >
              🔊 {isSpeaking ? "Reproduciendo..." : "Repetir Pregunta"}
            </button>
          )}
        </div>
      </div>

      {/* Main 3D Courtroom Bench (Estrado de los 3 Jurados con Retratos Reales) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1.3fr 1fr",
          gap: "1.25rem",
          alignItems: "end",
          position: "relative",
          zIndex: 2,
          paddingBottom: "1.25rem",
        }}
      >
        {jurors.map((juror) => {
          const isCurrentActive = activeIndex === juror.id;
          const isSide = juror.id !== 0;

          return (
            <div
              key={juror.id}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                transform: isCurrentActive ? "scale(1.05)" : "scale(0.96)",
                opacity: isCurrentActive ? 1 : isSpeaking ? 0.7 : 0.92,
                transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
              }}
            >
              {/* Realistic Portrait Frame */}
              <div
                style={{
                  position: "relative",
                  width: isSide ? "94px" : "118px",
                  height: isSide ? "94px" : "118px",
                  borderRadius: "50%",
                  border: isCurrentActive && isSpeaking
                    ? `3.5px solid ${juror.accentColor}`
                    : `2.5px solid ${isCurrentActive ? juror.accentColor : "rgba(148, 163, 184, 0.35)"}`,
                  boxShadow: isCurrentActive && isSpeaking
                    ? `0 0 32px ${juror.accentColor}70, 0 8px 24px rgba(0,0,0,0.6)`
                    : isListening
                    ? "0 0 16px rgba(56, 189, 248, 0.25)"
                    : "0 8px 20px rgba(0,0,0,0.5)",
                  overflow: "hidden",
                  background: "#0f172a",
                }}
              >
                {/* Real photographic image */}
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
                      ? speechPulse % 2 === 1 ? "scale(1.03) translateY(-1px)" : "scale(1.01)"
                      : isListening && micVolume > 15
                      ? "scale(0.99) translateY(1.5px)"
                      : "scale(1)",
                    transition: "transform 0.15s ease",
                  }}
                />

                {/* Sub-chin microphone LED on portrait */}
                <div
                  style={{
                    position: "absolute",
                    bottom: "4px",
                    right: "4px",
                    width: "14px",
                    height: "14px",
                    borderRadius: "50%",
                    background: isCurrentActive && isSpeaking ? juror.accentColor : "#1e293b",
                    border: "2px solid #091724",
                    boxShadow: isCurrentActive && isSpeaking ? `0 0 10px ${juror.accentColor}` : "none",
                    transition: "all 0.2s",
                  }}
                />
              </div>

              {/* Placa Dorada de Jurado */}
              <div
                style={{
                  marginTop: "8px",
                  padding: "4px 8px",
                  background: isCurrentActive
                    ? "linear-gradient(180deg, #2a2012 0%, #150f07 100%)"
                    : "linear-gradient(180deg, #1e293b 0%, #0f172a 100%)",
                  border: isCurrentActive ? "1px solid #eab308" : "1px solid rgba(255,255,255,0.12)",
                  borderRadius: "7px",
                  boxShadow: "0 3px 8px rgba(0,0,0,0.5)",
                  textAlign: "center",
                  width: "100%",
                  maxWidth: isSide ? "116px" : "140px",
                }}
              >
                <div
                  style={{
                    color: isCurrentActive ? "#fef08a" : "#f1f5f9",
                    fontSize: isSide ? "0.7rem" : "0.78rem",
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
                    fontSize: "0.58rem",
                    fontWeight: 700,
                    marginTop: "1px",
                  }}
                >
                  {juror.role}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Realistic Mahogany Bench / Estrado de Madera Caoba con Micrófonos de Conferencia */}
      <div
        style={{
          position: "relative",
          margin: "0 -1.5rem -1.25rem -1.5rem",
          padding: "0.85rem 1.5rem 1.1rem",
          background: "linear-gradient(180deg, #3d2212 0%, #241308 40%, #120904 100%)",
          borderTop: "3px solid #92400e",
          boxShadow: "inset 0 4px 14px rgba(0,0,0,0.7)",
        }}
      >
        {/* Active Speaker Dialog Capsule */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(10, 20, 32, 0.88)",
            border: `1px solid ${activeJuror.accentColor}50`,
            borderRadius: "14px",
            padding: "0.6rem 1.1rem",
            boxShadow: "0 4px 18px rgba(0,0,0,0.45)",
            flexWrap: "wrap",
            gap: "0.6rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                background: isSpeaking ? activeJuror.accentColor : isListening ? "#38bdf8" : "#f59e0b",
                boxShadow: isSpeaking ? `0 0 12px ${activeJuror.accentColor}` : "none",
                display: "inline-block",
              }}
            />
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <strong style={{ color: "#ffffff", fontSize: "0.86rem" }}>
                  {activeJuror.name}
                </strong>
                <span
                  style={{
                    color: activeJuror.accentColor,
                    fontSize: "0.68rem",
                    fontWeight: 800,
                    background: `${activeJuror.accentColor}25`,
                    padding: "2px 7px",
                    borderRadius: "6px",
                    border: `1px solid ${activeJuror.accentColor}40`,
                  }}
                >
                  {activeJuror.role}
                </span>
              </div>
              <p style={{ margin: "2px 0 0", color: "#cbd5e1", fontSize: "0.72rem" }}>
                {activeJuror.specialty}
              </p>
            </div>
          </div>

          {/* Equalizer Waveform during speech */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {isSpeaking ? (
              <div style={{ display: "flex", gap: "3px", alignItems: "flex-end", height: "18px" }}>
                <span style={{ width: "3.5px", height: "10px", background: activeJuror.accentColor, borderRadius: "2px", animation: "audioWave 0.5s infinite 0.1s" }} />
                <span style={{ width: "3.5px", height: "18px", background: activeJuror.accentColor, borderRadius: "2px", animation: "audioWave 0.5s infinite 0.25s" }} />
                <span style={{ width: "3.5px", height: "14px", background: activeJuror.accentColor, borderRadius: "2px", animation: "audioWave 0.5s infinite 0.4s" }} />
                <span style={{ width: "3.5px", height: "8px", background: activeJuror.accentColor, borderRadius: "2px", animation: "audioWave 0.5s infinite 0.15s" }} />
              </div>
            ) : isListening ? (
              <span style={{ fontSize: "0.74rem", color: "#38bdf8", fontWeight: 700, display: "flex", alignItems: "center", gap: "5px" }}>
                👂 Evaluando tu intervención verbal ({micVolume}%)
              </span>
            ) : isThinking ? (
              <span style={{ fontSize: "0.74rem", color: "#f59e0b", fontWeight: 700 }}>
                🤔 Deliberando rigor...
              </span>
            ) : (
              <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                En sesión formal
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Reactive Biomechanics, Protocol & Oratory Observation Banner */}
      {observation && (
        <div
          style={{
            marginTop: "1.1rem",
            padding: "0.75rem 1rem",
            borderRadius: "12px",
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
            fontSize: "0.82rem",
            lineHeight: 1.45,
            display: "flex",
            alignItems: "center",
            gap: "10px",
            animation: "bannerFadeIn 0.3s ease-out",
            position: "relative",
            zIndex: 3,
          }}
        >
          <span style={{ fontSize: "1.2rem", flexShrink: 0 }}>
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

      {/* Keyframe Animations */}
      <style jsx>{`
        @keyframes audioWave {
          0%, 100% { height: 4px; }
          50% { height: 18px; }
        }
        @keyframes bannerFadeIn {
          from { opacity: 0; transform: translateY(-6px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
