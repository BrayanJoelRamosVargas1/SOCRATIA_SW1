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
  // Multi-phoneme viseme phase generator for realistic lip sync
  const [visemeStep, setVisemeStep] = useState<number>(0);

  useEffect(() => {
    if (!isSpeaking) return;
    const interval = setInterval(() => {
      setVisemeStep((prev) => (prev + 1) % 6);
    }, 110);
    return () => {
      clearInterval(interval);
    };
  }, [isSpeaking]);

  const visemePhase = isSpeaking ? visemeStep : 0;

  const activeIndex = activeSpeakerIndex % 3;

  // Jury roster definition
  const jurors = [
    {
      id: 0,
      name: juryName || "Dr. Roberto Méndez",
      role: "Presidente del Tribunal",
      specialty: focusType || "Fundamentos Epistemológicos & Rigor",
      shortName: "Dr. R. Méndez",
      badgeColor: "#2dd4bf",
    },
    {
      id: 1,
      name: "Dra. Elena Rostova",
      role: "Vocal Metodológico",
      specialty: "Metodología, Hipótesis y Validación Empírica",
      shortName: "Dra. E. Rostova",
      badgeColor: "#c084fc",
    },
    {
      id: 2,
      name: "Ing. Carlos Mendoza",
      role: "Vocal Técnico",
      specialty: "Arquitectura de Software & Viabilidad Técnica",
      shortName: "Ing. C. Mendoza",
      badgeColor: "#38bdf8",
    },
  ];

  const activeJuror = jurors[activeIndex] || jurors[0];

  return (
    <div
      className="jury-stage-container"
      style={{
        background: "radial-gradient(ellipse at 50% 0%, #0d283e 0%, #071522 60%, #030a10 100%)",
        border: "1px solid rgba(45, 212, 191, 0.25)",
        borderRadius: "22px",
        padding: "1.25rem 1.5rem",
        marginBottom: "1.25rem",
        boxShadow: "0 18px 45px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.12)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Dynamic Ambient Spotlight focused on the active speaker */}
      <div
        style={{
          position: "absolute",
          top: "-60px",
          left: activeIndex === 0 ? "50%" : activeIndex === 1 ? "20%" : "80%",
          transform: "translateX(-50%)",
          width: "420px",
          height: "240px",
          background: isSpeaking
            ? `radial-gradient(ellipse, ${activeJuror.badgeColor}35 0%, transparent 70%)`
            : isListening
            ? "radial-gradient(ellipse, rgba(2, 132, 199, 0.22) 0%, transparent 70%)"
            : "radial-gradient(ellipse, rgba(255, 255, 255, 0.06) 0%, transparent 70%)",
          pointerEvents: "none",
          transition: "left 0.6s cubic-bezier(0.4, 0, 0.2, 1), background 0.4s ease",
        }}
      />

      {/* Header bar: Sala de Defensa y Tribunal Examinador */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
          paddingBottom: "0.65rem",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          flexWrap: "wrap",
          gap: "0.5rem",
          position: "relative",
          zIndex: 2,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <span
            style={{
              background: "linear-gradient(135deg, rgba(45, 212, 191, 0.2), rgba(13, 148, 136, 0.1))",
              color: "#2dd4bf",
              padding: "4px 11px",
              borderRadius: "14px",
              fontSize: "0.72rem",
              fontWeight: 800,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              border: "1px solid rgba(45, 212, 191, 0.35)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              boxShadow: "0 2px 8px rgba(45, 212, 191, 0.15)",
            }}
          >
            🏛️ SALA DE DEFENSA VIRTUAL · TRIBUNAL EXAMINADOR DE GRADO
          </span>
          <span style={{ color: "#94a3b8", fontSize: "0.72rem", fontWeight: 600 }}>
            • Deliberación Socrática 360°
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              fontSize: "0.72rem",
              color: strictness >= 4 ? "#f87171" : "#fbbf24",
              background: "rgba(15, 23, 42, 0.75)",
              padding: "3px 9px",
              borderRadius: "10px",
              border: "1px solid rgba(255,255,255,0.1)",
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
                gap: "5px",
                transition: "all 0.2s",
              }}
            >
              🔊 {isSpeaking ? "Reproduciendo..." : "Repetir Pregunta"}
            </button>
          )}
        </div>
      </div>

      {/* Main 3D Courtroom Bench (Estrado de los 3 Jurados) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1.35fr 1fr",
          gap: "1rem",
          alignItems: "end",
          position: "relative",
          zIndex: 2,
          paddingBottom: "1.25rem",
        }}
      >
        {/* ========================================================
            JUROR 1 (Izquierda): Dra. Elena Rostova - Vocal Metodológico
           ======================================================== */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            transform: activeIndex === 1 ? "scale(1.04)" : "scale(0.96)",
            opacity: activeIndex === 1 ? 1 : isSpeaking ? 0.65 : 0.9,
            transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        >
          {/* Avatar Container with spotlight ring */}
          <div
            style={{
              position: "relative",
              width: "82px",
              height: "82px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #1e1b4b, #0f172a)",
              border: activeIndex === 1 && isSpeaking
                ? "3px solid #c084fc"
                : "2px solid rgba(192, 132, 252, 0.35)",
              boxShadow: activeIndex === 1 && isSpeaking
                ? "0 0 25px rgba(192, 132, 252, 0.55)"
                : "0 6px 14px rgba(0,0,0,0.4)",
              overflow: "hidden",
            }}
          >
            <svg
              viewBox="0 0 100 100"
              style={{
                width: "100%",
                height: "100%",
                animation: activeIndex === 1 && isSpeaking
                  ? "speakerHeadBob 0.85s ease-in-out infinite"
                  : isListening && micVolume > 15
                  ? "sideJurorNoteTaking 1.8s ease-in-out infinite"
                  : "sideJurorNod 6s ease-in-out infinite",
                transformOrigin: "bottom center",
              }}
            >
              <circle cx="50" cy="50" r="48" fill="#08182b" />
              {/* Blusa formal púrpura académica */}
              <path d="M12 100 Q50 68 88 100 Z" fill="#2e1065" />
              <polygon points="42,70 50,88 58,70" fill="#f1f5f9" />
              {/* Pin académico plateado */}
              <circle cx="28" cy="88" r="2.2" fill="#e2e8f0" />
              {/* Cuello */}
              <rect x="43" y="58" width="14" height="16" rx="2" fill="#fed7aa" />
              {/* Cabeza */}
              <ellipse cx="50" cy="45" rx="21" ry="25" fill="#fed7aa" />
              {/* Cabello castaño peinado formal */}
              <path d="M26 40 Q50 14 74 40 Q78 68 73 78 Q68 50 64 43 Q50 22 36 43 Q32 50 27 78 Z" fill="#78350f" />
              {/* Gafas académicas */}
              <rect x="35" y="40" width="12" height="9" rx="2" fill="rgba(255,255,255,0.25)" stroke="#0f172a" strokeWidth="1.4" />
              <rect x="53" y="40" width="12" height="9" rx="2" fill="rgba(255,255,255,0.25)" stroke="#0f172a" strokeWidth="1.4" />
              <line x1="47" y1="44" x2="53" y2="44" stroke="#0f172a" strokeWidth="1.4" />
              {/* Ojos con parpadeo desfasado */}
              <g style={{ animation: "naturalEyeBlink 4.5s infinite 1.2s", transformOrigin: "50px 44px" }}>
                <circle cx="41" cy="44.5" r="2" fill="#0f172a" />
                <circle cx="41.7" cy="43.8" r="0.6" fill="#ffffff" />
                <circle cx="59" cy="44.5" r="2" fill="#0f172a" />
                <circle cx="59.7" cy="43.8" r="0.6" fill="#ffffff" />
              </g>
              {/* Nariz */}
              <path d="M50 46 L48 53 L52 53" stroke="#ea580c" strokeWidth="1.1" strokeLinecap="round" fill="none" opacity="0.6" />
              {/* Boca con Lip-Sync dinámico si es la oradora activa */}
              {activeIndex === 1 && isSpeaking ? (
                visemePhase === 0 ? (
                  <path d="M45 61 Q50 63 55 61" stroke="#991b1b" strokeWidth="2" strokeLinecap="round" fill="none" />
                ) : visemePhase === 1 ? (
                  <g>
                    <ellipse cx="50" cy="63" rx="5" ry="4" fill="#450a0a" />
                    <rect x="46" y="60.5" width="8" height="1.5" rx="0.5" fill="#ffffff" />
                    <path d="M44 60.5 Q50 59 56 60.5" stroke="#991b1b" strokeWidth="1.5" fill="none" />
                  </g>
                ) : visemePhase === 2 ? (
                  <ellipse cx="50" cy="62.5" rx="3.5" ry="4" fill="#450a0a" stroke="#991b1b" strokeWidth="1.3" />
                ) : (
                  <g>
                    <ellipse cx="50" cy="62" rx="5.5" ry="2.5" fill="#450a0a" />
                    <rect x="46" y="61" width="8" height="1" fill="#ffffff" />
                    <path d="M44 61.5 Q50 60 56 61.5" stroke="#991b1b" strokeWidth="1.4" fill="none" />
                  </g>
                )
              ) : isThinking ? (
                <path d="M46 62 Q50 60 54 62" stroke="#991b1b" strokeWidth="1.8" strokeLinecap="round" fill="none" />
              ) : (
                <path d="M46 62 Q50 64 54 62" stroke="#991b1b" strokeWidth="1.6" strokeLinecap="round" fill="none" />
              )}
            </svg>
            {/* Mic LED indicator */}
            <div
              style={{
                position: "absolute",
                bottom: "2px",
                right: "2px",
                width: "14px",
                height: "14px",
                borderRadius: "50%",
                background: activeIndex === 1 && isSpeaking ? "#c084fc" : "#1e1b4b",
                border: "2px solid #091724",
                boxShadow: activeIndex === 1 && isSpeaking ? "0 0 8px #c084fc" : "none",
              }}
            />
          </div>

          {/* Placa Dorada de Jurado */}
          <div
            style={{
              marginTop: "6px",
              padding: "3px 8px",
              background: "linear-gradient(180deg, #33261a, #1a130b)",
              border: "1px solid #ca8a04",
              borderRadius: "6px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.5)",
              textAlign: "center",
              width: "100%",
              maxWidth: "110px",
            }}
          >
            <div style={{ color: "#fef08a", fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.02em" }}>
              Dra. E. Rostova
            </div>
            <div style={{ color: "#a1a1aa", fontSize: "0.55rem", fontWeight: 600 }}>
              Vocal Metodológico
            </div>
          </div>
        </div>

        {/* ========================================================
            JUROR 0 (Centro): Dr. Roberto Méndez - Presidente del Tribunal
           ======================================================== */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            transform: activeIndex === 0 ? "scale(1.06)" : "scale(0.98)",
            opacity: activeIndex === 0 ? 1 : isSpeaking ? 0.75 : 0.95,
            transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        >
          {/* Main Avatar Frame */}
          <div
            style={{
              position: "relative",
              width: "110px",
              height: "110px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #1e293b, #0f172a)",
              border: activeIndex === 0 && isSpeaking
                ? "3.5px solid #2dd4bf"
                : "2.5px solid rgba(45, 212, 191, 0.4)",
              boxShadow: activeIndex === 0 && isSpeaking
                ? "0 0 32px rgba(45, 212, 191, 0.55)"
                : isListening
                ? "0 0 16px rgba(56, 189, 248, 0.3)"
                : "0 8px 20px rgba(0,0,0,0.5)",
              overflow: "hidden",
            }}
          >
            <svg
              viewBox="0 0 120 120"
              style={{
                width: "100%",
                height: "100%",
                animation: activeIndex === 0 && isSpeaking
                  ? "speakerHeadBob 0.8s ease-in-out infinite"
                  : isListening && micVolume > 15
                  ? "listeningHeadNod 2.2s ease-in-out infinite"
                  : isListening
                  ? "listeningHeadNod 4.5s ease-in-out infinite"
                  : "none",
                transformOrigin: "bottom center",
              }}
            >
              <defs>
                <linearGradient id="mainSuitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#1e293b" />
                  <stop offset="100%" stopColor="#091422" />
                </linearGradient>
                <linearGradient id="mainSkinGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#fed7aa" />
                  <stop offset="100%" stopColor="#fba668" />
                </linearGradient>
              </defs>

              <circle cx="60" cy="60" r="58" fill="#081e2b" />
              {/* Traje formal con solapa */}
              <path d="M12 120 Q60 84 108 120 Z" fill="url(#mainSuitGrad)" />
              {/* Pin dorado de Presidente */}
              <circle cx="34" cy="100" r="2.4" fill="#eab308" />
              <polygon points="50,85 60,105 70,85" fill="#f8fafc" />
              {/* Corbata vino de grado académico */}
              <polygon points="57,90 63,90 62,118 58,118" fill="#881337" />
              <polygon points="57,90 63,90 61,96 59,96" fill="#4c0519" />
              {/* Cuello */}
              <rect x="52" y="68" width="16" height="22" rx="3" fill="#fed7aa" />
              {/* Cabeza */}
              <ellipse cx="60" cy="51" rx="25" ry="29" fill="url(#mainSkinGrad)" />
              {/* Cabello canoso distinguido */}
              <path d="M35 44 Q60 18 85 44 Q79 28 60 26 Q41 28 35 44 Z" fill="#475569" />
              <path d="M34 44 Q37 32 45 28 Q32 36 34 47 Z" fill="#334155" />
              <path d="M86 44 Q83 32 75 28 Q88 36 86 47 Z" fill="#334155" />

              {/* Cejas expresivas */}
              <path d="M43 42 Q50 39 54 42" stroke="#334155" strokeWidth="2.4" strokeLinecap="round" fill="none" />
              <path d="M66 42 Q70 39 77 42" stroke="#334155" strokeWidth="2.4" strokeLinecap="round" fill="none" />

              {/* Gafas metálicas */}
              <rect x="41" y="43" width="15" height="11" rx="2" fill="rgba(255,255,255,0.2)" stroke="#0f172a" strokeWidth="1.8" />
              <rect x="64" y="43" width="15" height="11" rx="2" fill="rgba(255,255,255,0.2)" stroke="#0f172a" strokeWidth="1.8" />
              <line x1="56" y1="47" x2="64" y2="47" stroke="#0f172a" strokeWidth="1.8" />

              {/* Ojos con parpadeo */}
              <g style={{ animation: "naturalEyeBlink 3.8s infinite", transformOrigin: "60px 48px" }}>
                <circle cx="48.5" cy="48.5" r="2.6" fill="#0f172a" />
                <circle cx="49.5" cy="47.5" r="0.8" fill="#ffffff" />
                <circle cx="71.5" cy="48.5" r="2.6" fill="#0f172a" />
                <circle cx="72.5" cy="47.5" r="0.8" fill="#ffffff" />
              </g>

              {/* Nariz */}
              <path d="M60 50 L58 58 L62 58" stroke="#ea580c" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.65" />

              {/* Boca con Lip-Sync realista */}
              {activeIndex === 0 && isSpeaking ? (
                visemePhase === 0 ? (
                  <g>
                    <path d="M54 67 Q60 69 66 67" stroke="#991b1b" strokeWidth="2.2" strokeLinecap="round" fill="none" />
                    <line x1="56" y1="67" x2="64" y2="67" stroke="#4c0519" strokeWidth="1" />
                  </g>
                ) : visemePhase === 1 ? (
                  <g style={{ animation: "subtleJawDrop 0.15s ease-out" }}>
                    <ellipse cx="60" cy="69" rx="7.5" ry="5.5" fill="#450a0a" />
                    <path d="M54 66 Q60 64 66 66 L65 67 Q60 66 55 67 Z" fill="#ffffff" />
                    <ellipse cx="60" cy="72" rx="4" ry="2" fill="#ef4444" opacity="0.6" />
                    <path d="M53 66 Q60 62 67 66" stroke="#991b1b" strokeWidth="1.8" fill="none" />
                  </g>
                ) : visemePhase === 2 ? (
                  <g>
                    <ellipse cx="60" cy="68" rx="5" ry="6" fill="#450a0a" stroke="#991b1b" strokeWidth="1.5" />
                    <ellipse cx="60" cy="69" rx="3" ry="3.5" fill="#7f1d1d" />
                  </g>
                ) : visemePhase === 3 ? (
                  <g>
                    <ellipse cx="60" cy="67.5" rx="8" ry="3" fill="#450a0a" />
                    <rect x="54" y="66" width="12" height="2" rx="0.5" fill="#ffffff" />
                    <path d="M52 67 Q60 65 68 67" stroke="#991b1b" strokeWidth="1.8" fill="none" />
                  </g>
                ) : (
                  <g>
                    <ellipse cx="60" cy="67.5" rx="6" ry="2.5" fill="#450a0a" />
                    <path d="M54 67 Q60 66 66 67" stroke="#991b1b" strokeWidth="1.8" fill="none" />
                  </g>
                )
              ) : isThinking ? (
                <path d="M55 67 Q60 65 65 67" stroke="#991b1b" strokeWidth="2" strokeLinecap="round" fill="none" />
              ) : (
                <path d="M54 67.5 Q60 69.5 66 67.5" stroke="#991b1b" strokeWidth="2" strokeLinecap="round" fill="none" />
              )}
            </svg>
            {/* Speaking mic indicator */}
            <div
              style={{
                position: "absolute",
                bottom: "3px",
                right: "3px",
                width: "16px",
                height: "16px",
                borderRadius: "50%",
                background: activeIndex === 0 && isSpeaking ? "#2dd4bf" : "#0f172a",
                border: "2px solid #091724",
                boxShadow: activeIndex === 0 && isSpeaking ? "0 0 10px #2dd4bf" : "none",
              }}
            />
          </div>

          {/* Placa Dorada de Presidente */}
          <div
            style={{
              marginTop: "6px",
              padding: "4px 10px",
              background: "linear-gradient(180deg, #3d2d1d, #20170e)",
              border: "1.5px solid #eab308",
              borderRadius: "7px",
              boxShadow: "0 3px 8px rgba(0,0,0,0.6)",
              textAlign: "center",
              width: "100%",
              maxWidth: "140px",
            }}
          >
            <div style={{ color: "#fef08a", fontSize: "0.74rem", fontWeight: 900, letterSpacing: "0.03em" }}>
              {jurors[0].name}
            </div>
            <div style={{ color: "#2dd4bf", fontSize: "0.6rem", fontWeight: 700 }}>
              Presidente del Tribunal
            </div>
          </div>
        </div>

        {/* ========================================================
            JUROR 2 (Derecha): Ing. Carlos Mendoza - Vocal Técnico
           ======================================================== */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            transform: activeIndex === 2 ? "scale(1.04)" : "scale(0.96)",
            opacity: activeIndex === 2 ? 1 : isSpeaking ? 0.65 : 0.9,
            transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        >
          {/* Avatar Container */}
          <div
            style={{
              position: "relative",
              width: "82px",
              height: "82px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #1e293b, #0f172a)",
              border: activeIndex === 2 && isSpeaking
                ? "3px solid #38bdf8"
                : "2px solid rgba(56, 189, 248, 0.35)",
              boxShadow: activeIndex === 2 && isSpeaking
                ? "0 0 25px rgba(56, 189, 248, 0.55)"
                : "0 6px 14px rgba(0,0,0,0.4)",
              overflow: "hidden",
            }}
          >
            <svg
              viewBox="0 0 100 100"
              style={{
                width: "100%",
                height: "100%",
                animation: activeIndex === 2 && isSpeaking
                  ? "speakerHeadBob 0.85s ease-in-out infinite"
                  : isListening && micVolume > 15
                  ? "sideJurorNoteTaking 1.8s ease-in-out infinite 0.4s"
                  : "sideJurorNod 5.5s ease-in-out infinite 1s",
                transformOrigin: "bottom center",
              }}
            >
              <circle cx="50" cy="50" r="48" fill="#08182b" />
              {/* Traje oscuro formal */}
              <path d="M12 100 Q50 68 88 100 Z" fill="#0f172a" />
              <polygon points="43,72 50,88 57,72" fill="#f8fafc" />
              {/* Corbata azul */}
              <polygon points="48,76 52,76 51,96 49,96" fill="#1e3a8a" />
              {/* Cuello */}
              <rect x="43" y="58" width="14" height="16" rx="2" fill="#fdba74" />
              {/* Cabeza */}
              <ellipse cx="50" cy="45" rx="21" ry="25" fill="#fdba74" />
              {/* Cabello corto formal */}
              <path d="M28 38 Q50 18 72 38 Q67 24 50 22 Q33 24 28 38 Z" fill="#1e293b" />
              {/* Barba académica bien delineada */}
              <path d="M41 55 Q50 68 59 55 Q59 64 50 67 Q41 64 41 55 Z" fill="#334155" />
              {/* Ojos con parpadeo */}
              <g style={{ animation: "naturalEyeBlink 4.2s infinite 2.2s", transformOrigin: "50px 44px" }}>
                <circle cx="42" cy="44" r="2" fill="#0f172a" />
                <circle cx="42.7" cy="43.3" r="0.6" fill="#ffffff" />
                <circle cx="58" cy="44" r="2" fill="#0f172a" />
                <circle cx="58.7" cy="43.3" r="0.6" fill="#ffffff" />
              </g>
              {/* Boca con Lip-Sync */}
              {activeIndex === 2 && isSpeaking ? (
                visemePhase === 0 ? (
                  <path d="M45 60 Q50 62 55 60" stroke="#7f1d1d" strokeWidth="2" strokeLinecap="round" fill="none" />
                ) : visemePhase === 1 ? (
                  <g>
                    <ellipse cx="50" cy="62" rx="5" ry="4" fill="#450a0a" />
                    <rect x="46" y="59.5" width="8" height="1.5" rx="0.5" fill="#ffffff" />
                  </g>
                ) : visemePhase === 2 ? (
                  <ellipse cx="50" cy="61.5" rx="3.5" ry="4" fill="#450a0a" stroke="#7f1d1d" strokeWidth="1.3" />
                ) : (
                  <g>
                    <ellipse cx="50" cy="61" rx="5.5" ry="2.5" fill="#450a0a" />
                    <rect x="46" y="60" width="8" height="1" fill="#ffffff" />
                  </g>
                )
              ) : isThinking ? (
                <path d="M46 61 Q50 59 54 61" stroke="#7f1d1d" strokeWidth="1.8" strokeLinecap="round" fill="none" />
              ) : (
                <path d="M46 61 Q50 62 54 61" stroke="#7f1d1d" strokeWidth="1.6" strokeLinecap="round" fill="none" />
              )}
            </svg>
            {/* Mic LED indicator */}
            <div
              style={{
                position: "absolute",
                bottom: "2px",
                right: "2px",
                width: "14px",
                height: "14px",
                borderRadius: "50%",
                background: activeIndex === 2 && isSpeaking ? "#38bdf8" : "#0f172a",
                border: "2px solid #091724",
                boxShadow: activeIndex === 2 && isSpeaking ? "0 0 8px #38bdf8" : "none",
              }}
            />
          </div>

          {/* Placa Dorada de Jurado */}
          <div
            style={{
              marginTop: "6px",
              padding: "3px 8px",
              background: "linear-gradient(180deg, #33261a, #1a130b)",
              border: "1px solid #ca8a04",
              borderRadius: "6px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.5)",
              textAlign: "center",
              width: "100%",
              maxWidth: "110px",
            }}
          >
            <div style={{ color: "#fef08a", fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.02em" }}>
              Ing. C. Mendoza
            </div>
            <div style={{ color: "#a1a1aa", fontSize: "0.55rem", fontWeight: 600 }}>
              Vocal Técnico
            </div>
          </div>
        </div>
      </div>

      {/* Realistic Mahogany Bench / Estrado de Madera Caoba con Micrófonos de Conferencia */}
      <div
        style={{
          position: "relative",
          margin: "0 -1.5rem -1.25rem -1.5rem",
          padding: "0.75rem 1.5rem 1rem",
          background: "linear-gradient(180deg, #382012 0%, #24140a 40%, #150b05 100%)",
          borderTop: "3px solid #78350f",
          boxShadow: "inset 0 4px 12px rgba(0,0,0,0.6)",
        }}
      >
        {/* Active Speaker Dialog Capsule */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(10, 19, 30, 0.85)",
            border: `1px solid ${activeJuror.badgeColor}40`,
            borderRadius: "14px",
            padding: "0.5rem 1rem",
            boxShadow: "0 4px 15px rgba(0,0,0,0.4)",
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
                background: isSpeaking ? activeJuror.badgeColor : isListening ? "#38bdf8" : "#f59e0b",
                boxShadow: isSpeaking ? `0 0 10px ${activeJuror.badgeColor}` : "none",
                display: "inline-block",
              }}
            />
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <strong style={{ color: "#ffffff", fontSize: "0.82rem" }}>
                  {activeJuror.name}
                </strong>
                <span
                  style={{
                    color: activeJuror.badgeColor,
                    fontSize: "0.68rem",
                    fontWeight: 700,
                    background: `${activeJuror.badgeColor}20`,
                    padding: "1px 6px",
                    borderRadius: "6px",
                  }}
                >
                  {activeJuror.role}
                </span>
              </div>
              <p style={{ margin: "1px 0 0", color: "#94a3b8", fontSize: "0.7rem" }}>
                {activeJuror.specialty}
              </p>
            </div>
          </div>

          {/* Equalizer Waveform during speech */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            {isSpeaking ? (
              <div style={{ display: "flex", gap: "3px", alignItems: "flex-end", height: "16px" }}>
                <span style={{ width: "3px", height: "10px", background: activeJuror.badgeColor, borderRadius: "1px", animation: "audioWave 0.5s infinite 0.1s" }} />
                <span style={{ width: "3px", height: "16px", background: activeJuror.badgeColor, borderRadius: "1px", animation: "audioWave 0.5s infinite 0.25s" }} />
                <span style={{ width: "3px", height: "12px", background: activeJuror.badgeColor, borderRadius: "1px", animation: "audioWave 0.5s infinite 0.4s" }} />
                <span style={{ width: "3px", height: "7px", background: activeJuror.badgeColor, borderRadius: "1px", animation: "audioWave 0.5s infinite 0.15s" }} />
              </div>
            ) : isListening ? (
              <span style={{ fontSize: "0.72rem", color: "#38bdf8", fontWeight: 600 }}>
                👂 Evaluando disertación ({micVolume}%)
              </span>
            ) : isThinking ? (
              <span style={{ fontSize: "0.72rem", color: "#f59e0b", fontWeight: 600 }}>
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
            marginTop: "1rem",
            padding: "0.65rem 1rem",
            borderRadius: "12px",
            background:
              observation.type === "praise"
                ? "rgba(16, 185, 129, 0.16)"
                : observation.type === "dress"
                ? "rgba(244, 63, 94, 0.16)"
                : observation.type === "oratory"
                ? "rgba(245, 158, 11, 0.18)"
                : "rgba(239, 68, 68, 0.16)",
            border:
              observation.type === "praise"
                ? "1px solid rgba(16, 185, 129, 0.45)"
                : observation.type === "dress"
                ? "1px solid rgba(244, 63, 94, 0.45)"
                : observation.type === "oratory"
                ? "1px solid rgba(245, 158, 11, 0.45)"
                : "1px solid rgba(239, 68, 68, 0.45)",
            color:
              observation.type === "praise"
                ? "#6ee7b7"
                : observation.type === "dress"
                ? "#fda4af"
                : observation.type === "oratory"
                ? "#fde68a"
                : "#fca5a5",
            fontSize: "0.8rem",
            lineHeight: 1.45,
            display: "flex",
            alignItems: "center",
            gap: "10px",
            animation: "bannerFadeIn 0.3s ease-out",
            position: "relative",
            zIndex: 3,
          }}
        >
          <span style={{ fontSize: "1.15rem", flexShrink: 0 }}>
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
        @keyframes naturalEyeBlink {
          0%, 94%, 100% { transform: scaleY(1); }
          96% { transform: scaleY(0.06); }
        }
        @keyframes speakerHeadBob {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          30% { transform: translateY(-1.8px) rotate(0.5deg); }
          70% { transform: translateY(0.9px) rotate(-0.4deg); }
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
        @keyframes sideJurorNoteTaking {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          25% { transform: translateY(2.8px) rotate(0.8deg); }
          50% { transform: translateY(1.2px) rotate(-0.4deg); }
          75% { transform: translateY(2.4px) rotate(0.5deg); }
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
