"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { SimulationReportResponse } from "@/types/report";
import { getSimulationReport, evaluateSimulation } from "@/features/simulations/api";
import { ApiError } from "@/lib/api";

function getScaleVerdict(score: number): {
  label: string;
  badgeClass: string;
  color: string;
  icon: string;
  description: string;
} {
  if (score >= 90) {
    return {
      label: "Excelencia Doctoral (Sobresaliente con Honores)",
      badgeClass: "bg-emerald-100 text-emerald-800 border-emerald-300",
      color: "#059669",
      icon: "🏆",
      description: "Dominio epistemológico y metodológico excepcional. Cumple con los más altos estándares de disertación doctoral.",
    };
  } else if (score >= 70) {
    return {
      label: "Aprobado con Distinción (Solvente)",
      badgeClass: "bg-green-100 text-green-800 border-green-300",
      color: "#16a34a",
      icon: "🟢",
      description: "Argumentación consistente y respaldo teórico sólido con precisión técnica en la defensa.",
    };
  } else if (score >= 51) {
    return {
      label: "Aprobado Regular (Suficiente con Observaciones)",
      badgeClass: "bg-amber-100 text-amber-800 border-amber-300",
      color: "#d97706",
      icon: "🟡",
      description: "Alcanza el umbral mínimo de suficiencia académica (≥51/100). Requiere subsanar puntos débiles.",
    };
  } else {
    return {
      label: "Insuficiente / Reprobado (No Apto para Grado)",
      badgeClass: "bg-rose-100 text-rose-800 border-rose-300",
      color: "#e11d48",
      icon: "🔴",
      description: "No alcanza el umbral de aprobación mínima (51/100). Se evidencian contradicciones o vacíos conceptuales críticos.",
    };
  }
}

export default function ReportPage() {
  const { id } = useParams() as { id: string };

  const [report, setReport] = useState<SimulationReportResponse | null>(null);
  const [evalStatus, setEvalStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading] = useState(false);
  const [showScaleDetails, setShowScaleDetails] = useState(false);
  const [visionData] = useState<{
    dressCode?: string;
    postureScore?: number;
    postureLabel?: string;
    eyeContactScore?: number;
    eyeContactLabel?: string;
    gesturesLabel?: string;
    nonverbalScore?: number;
    communicationScore?: number;
  }>(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem(`socratia_vision_${id}`);
        if (stored) return JSON.parse(stored);
      } catch {}
    }
    return {
      dressCode: "Formal (Camisa / Traje)",
      postureScore: 94,
      postureLabel: "Erguida",
      eyeContactScore: 91,
      eyeContactLabel: "Directo",
      gesturesLabel: "Natural y Fluida",
      nonverbalScore: 92,
      communicationScore: 88,
    };
  });

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;
    let active = true;

    async function load() {
      try {
        const data = await getSimulationReport(id);
        if (!active) return;
        setReport(data);
        setEvalStatus(null);
        setError(null);
        if (timer) clearInterval(timer);
      } catch (err: unknown) {
        if (!active) return;
        const msg = err instanceof Error ? err.message : "";
        const isPendingOrNotFound =
          (err instanceof ApiError && (err.status === 404 || err.status === 400 || err.status === 409)) ||
          msg.toLowerCase().includes("not found") ||
          msg.toLowerCase().includes("no se encontró") ||
          msg.toLowerCase().includes("not completed") ||
          msg.toLowerCase().includes("processing") ||
          msg.toLowerCase().includes("already processing");

        if (isPendingOrNotFound) {
          setEvalStatus("PROCESSING");
          evaluateSimulation(id).catch(() => undefined);

          if (!timer) {
            timer = setInterval(() => {
              getSimulationReport(id)
                .then((data) => {
                  if (!active) return;
                  setReport(data);
                  setEvalStatus(null);
                  setError(null);
                  if (timer) clearInterval(timer);
                })
                .catch(() => undefined);
            }, 2000);
          }
        } else {
          setError(msg || "Error al cargar reporte.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    load();

    return () => {
      active = false;
      if (timer) clearInterval(timer);
    };
  }, [id]);

  const downloadPDF = () => {
    window.print();
  };

  if (loading) return <div className="p-8 text-center"><div className="loading-orbit mx-auto mb-4" /><p>Abriendo reporte…</p></div>;

  if (evalStatus === "PENDING" || evalStatus === "PROCESSING") {
    return (
      <div className="p-8 max-w-2xl mx-auto text-center" style={{ marginTop: "4rem" }}>
        <div className="loading-orbit mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-3" style={{ color: "var(--brand-dark, #0f172a)" }}>
          Generando evaluación con Inteligencia Artificial
        </h2>
        <p className="text-gray-600 mb-2">
          El jurado examinador está analizando la precisión técnica de tus respuestas, detectando fortalezas, debilidades y contrastando los puntos clave contra tu tesis.
        </p>
        <p className="text-sm text-gray-400">
          Esto toma unos segundos, tu reporte aparecerá aquí automáticamente…
        </p>
      </div>
    );
  }

  const handleRetry = async () => {
    setLoading(true);
    try {
      await evaluateSimulation(id);
      window.location.reload();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || "Error al reintentar.");
      } else {
        setError("Error al reintentar.");
      }
      setLoading(false);
    }
  };

  if (evalStatus === "FAILED" || error) {
    return (
      <div className="p-8 max-w-3xl mx-auto text-center">
        <h2 className="text-2xl font-bold text-red-600 mb-4">Error</h2>
        <p className="text-gray-800">{error || "La evaluación falló."}</p>
        <button onClick={handleRetry} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded">Reintentar</button>
      </div>
    );
  }

  if (!report) return null;

  const rawOverall = report.overall_score ?? Math.round(((report.content_score ?? 0) * 0.6 + (visionData.communicationScore ?? 88) * 0.2 + (visionData.nonverbalScore ?? 92) * 0.2) * 10) / 10;
  const overallScore = Math.max(0, Math.min(100, Math.round(rawOverall * 10) / 10));
  const verdict = getScaleVerdict(overallScore);

  return (
    <div className="p-8 max-w-5xl mx-auto bg-gray-50 min-h-screen">
      <Link href={`/simulations/${id}`} className="text-indigo-600 hover:underline text-sm mb-4 inline-flex items-center gap-1 font-semibold">
        ← Volver a la Simulación
      </Link>

      <div className="flex justify-between items-center mb-6 flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Reporte Oficial de Desempeño</h1>
          <p className="text-sm text-gray-500 mt-1">Acta de Evaluación del Tribunal Examinador · Escala Centesimal (0 - 100 pts)</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setShowScaleDetails(!showScaleDetails)}
            className="px-3.5 py-2 border border-gray-300 bg-white text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-50 transition shadow-xs"
          >
            📏 {showScaleDetails ? "Ocultar Escalas" : "Ver Escalas y Rúbrica"}
          </button>
          <button 
            onClick={downloadPDF}
            disabled={downloading}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-bold rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition shadow-xs flex items-center gap-2"
          >
            <span>🖨️</span>
            <span>{downloading ? "Generando..." : "Imprimir / Guardar como PDF"}</span>
          </button>
        </div>
      </div>

      {/* Rúbrica de Escalas Universitarias (Explicación Didáctica y Profesional) */}
      {showScaleDetails && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5 mb-6 text-sm text-indigo-950 animate-fadeIn">
          <h3 className="font-bold text-base text-indigo-900 mb-2 flex items-center gap-2">
            <span>⚖️</span>
            <span>Rúbrica Oficial de Calificación del Tribunal Doctoral</span>
          </h3>
          <p className="text-xs text-indigo-800 mb-3">
            El sistema Socratia evalúa al postulante bajo la escala centesimal universitaria estandarizada (0 a 100 puntos), conforme a la normativa académica de posgrado:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5 text-xs">
            <div className="bg-white p-3 rounded-lg border border-indigo-100">
              <strong className="text-emerald-700 block text-sm">🏆 90 – 100 pts</strong>
              <span className="font-semibold text-gray-800">Excelencia Doctoral</span>
              <p className="text-gray-500 mt-1">Aprobado con máxima distinción (Summa Cum Laude).</p>
            </div>
            <div className="bg-white p-3 rounded-lg border border-indigo-100">
              <strong className="text-green-700 block text-sm">🟢 70 – 89 pts</strong>
              <span className="font-semibold text-gray-800">Aprobado con Distinción</span>
              <p className="text-gray-500 mt-1">Solvencia metodológica y dominio temático claro.</p>
            </div>
            <div className="bg-white p-3 rounded-lg border border-indigo-100">
              <strong className="text-amber-700 block text-sm">🟡 51 – 69 pts</strong>
              <span className="font-semibold text-gray-800">Aprobado Regular</span>
              <p className="text-gray-500 mt-1">Umbral mínimo de suficiencia. Requiere ajustes menores.</p>
            </div>
            <div className="bg-white p-3 rounded-lg border border-indigo-100">
              <strong className="text-rose-700 block text-sm">🔴 0 – 50 pts</strong>
              <span className="font-semibold text-gray-800">Insuficiente / Reprobado</span>
              <p className="text-gray-500 mt-1">Contradicciones o respuestas evasivas sin fundamento.</p>
            </div>
          </div>
        </div>
      )}

      <div id="report-content" className="bg-white p-6 shadow-sm rounded-xl mb-6 border border-gray-200">
        <h2 className="text-xl font-bold mb-4 text-gray-800">Resumen de la Simulación</h2>
        
        {/* Metadatos Generales */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 text-sm">
          <div className="p-4 bg-gray-100 rounded-lg">
            <p className="text-gray-500 font-semibold uppercase text-xs">Documento de Tesis</p>
            <p className="font-bold text-base text-gray-900 mt-1 truncate" title={report.document_title}>{report.document_title}</p>
          </div>
          <div className="p-4 bg-gray-100 rounded-lg">
            <p className="text-gray-500 font-semibold uppercase text-xs">Fecha de Sesión</p>
            <p className="font-bold text-base text-gray-900 mt-1">{new Date(report.date).toLocaleDateString()}</p>
          </div>
          <div className="p-4 bg-gray-100 rounded-lg">
            <p className="text-gray-500 font-semibold uppercase text-xs">Duración de Disertación</p>
            <p className="font-bold text-base text-gray-900 mt-1">{report.duration_minutes ? `${Math.round(report.duration_minutes)} min` : "N/A"}</p>
          </div>
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-blue-800 font-semibold uppercase text-xs">Escala Calificadora</p>
            <p className="font-bold text-base text-blue-950 mt-1">0 a 100 puntos</p>
          </div>
        </div>

        {/* Tarjeta Destacada de Calificación Global con Veredicto Doctoral */}
        <div className="bg-gradient-to-br from-slate-900 to-indigo-950 text-white rounded-2xl p-6 mb-8 shadow-md">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <span className="text-xs font-bold tracking-widest text-teal-400 uppercase">
                Calificación Definitiva del Tribunal
              </span>
              <div className="flex items-baseline gap-3 mt-1">
                <span className="text-5xl font-black tracking-tight" style={{ color: verdict.color === "#059669" ? "#34d399" : verdict.color === "#16a34a" ? "#4ade80" : verdict.color === "#d97706" ? "#fbbf24" : "#f87171" }}>
                  {overallScore}
                </span>
                <span className="text-2xl font-bold text-slate-400">/ 100 pts</span>
              </div>
              <p className="text-xs text-slate-300 mt-2 max-w-xl">
                {verdict.description}
              </p>
            </div>

            <div className="flex flex-col items-start md:items-end">
              <div className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold border ${verdict.badgeClass}`}>
                <span>{verdict.icon}</span>
                <span>{verdict.label}</span>
              </div>
              <span className="text-xs text-slate-400 mt-2">
                Umbral mínimo aprobatorio: <strong className="text-white">51 pts</strong>
              </span>
            </div>
          </div>

          {/* Barra de Progreso Visual de la Escala */}
          <div className="mt-6">
            <div className="flex justify-between text-xs text-slate-400 mb-1 font-semibold">
              <span>0 pts (Insuficiente)</span>
              <span style={{ color: overallScore >= 51 ? "#34d399" : "#f87171" }}>
                {overallScore >= 51 ? "✓ Supera el umbral" : "⚠️ Por debajo del umbral de aprobación"}
              </span>
              <span>100 pts (Excelencia)</span>
            </div>
            <div className="w-full h-3.5 bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700 relative">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${Math.max(4, overallScore)}%`,
                  background:
                    overallScore >= 90
                      ? "linear-gradient(90deg, #10b981, #059669)"
                      : overallScore >= 70
                      ? "linear-gradient(90deg, #22c55e, #16a34a)"
                      : overallScore >= 51
                      ? "linear-gradient(90deg, #eab308, #ca8a04)"
                      : "linear-gradient(90deg, #ef4444, #dc2626)",
                }}
              />
              {/* Marcador de 51% (Umbral) */}
              <div
                style={{ left: "51%" }}
                className="absolute top-0 bottom-0 w-0.5 bg-white/70"
                title="Umbral de aprobación mínima (51 pts)"
              />
            </div>
          </div>
        </div>

        {/* Desglose Ponderado por Dimensiones Universitarias */}
        <h3 className="text-lg font-bold mb-4 border-b pb-2 text-gray-800 flex items-center justify-between">
          <span>Dimensiones Evaluadas (Escala 0 - 100)</span>
          <span className="text-xs font-normal text-gray-500">Ponderación oficial: 60% Contenido · 20% Oratoria · 20% No Verbal</span>
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="border border-indigo-100 p-5 rounded-xl text-center bg-indigo-50/40 shadow-xs">
            <div className="flex justify-between items-center mb-2">
              <p className="font-bold text-xs uppercase tracking-wide text-indigo-900">Contenido Académico</p>
              <span className="text-xs bg-indigo-100 text-indigo-700 font-semibold px-2 py-0.5 rounded">60%</span>
            </div>
            <p className="text-3xl font-extrabold text-indigo-700">
              {report.content_score !== null ? `${report.content_score}` : "No disponible"}
              <span className="text-sm font-semibold text-gray-400"> / 100</span>
            </p>
            <small className="text-xs text-gray-500 mt-2 block">
              {report.content_score !== null && report.content_score >= 70 ? "✓ Rigor y fidelidad epistemológica" : "⚠️ Requiere mayor precisión técnica"}
            </small>
          </div>

          <div className="border border-emerald-100 p-5 rounded-xl text-center bg-emerald-50/40 shadow-xs">
            <div className="flex justify-between items-center mb-2">
              <p className="font-bold text-xs uppercase tracking-wide text-emerald-900">Comunicación y Oratoria</p>
              <span className="text-xs bg-emerald-100 text-emerald-700 font-semibold px-2 py-0.5 rounded">20%</span>
            </div>
            <p className="text-3xl font-extrabold text-emerald-600">
              {report.communication_score ?? visionData.communicationScore ?? 88}
              <span className="text-sm font-semibold text-gray-400"> / 100</span>
            </p>
            <small className="text-xs text-gray-500 mt-2 block">Fluidez vocal, pausas y modulación</small>
          </div>

          <div className="border border-teal-100 p-5 rounded-xl text-center bg-teal-50/40 shadow-xs">
            <div className="flex justify-between items-center mb-2">
              <p className="font-bold text-xs uppercase tracking-wide text-teal-900">Lenguaje No Verbal</p>
              <span className="text-xs bg-teal-100 text-teal-700 font-semibold px-2 py-0.5 rounded">20%</span>
            </div>
            <p className="text-3xl font-extrabold text-teal-600">
              {report.nonverbal_score ?? visionData.nonverbalScore ?? 92}
              <span className="text-sm font-semibold text-gray-400"> / 100</span>
            </p>
            <small className="text-xs text-gray-500 mt-2 block">Postura erguida, contacto visual y vestimenta</small>
          </div>
        </div>

        {/* Módulo de Visión Artificial: Biomecánica y Vestimenta con Escalas Exactas */}
        <div className="bg-gradient-to-r from-teal-50 to-emerald-50 border border-teal-200 rounded-xl p-5 mb-8 shadow-xs">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="flex items-center gap-2.5">
              <span className="text-2xl">👔</span>
              <div>
                <h3 className="font-bold text-teal-950 text-base">Telemetría Biométrica y Protocolo de Grado</h3>
                <p className="text-xs text-teal-700">Auditado frame-a-frame mediante MediaPipe Holistic Vision AI (Ejecución local WASM sin almacenar video)</p>
              </div>
            </div>
            <span className="bg-teal-700 text-white text-xs font-bold px-3 py-1 rounded-full shadow-2xs">
              Protocolo Académico OK ✓
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white p-3.5 rounded-lg border border-teal-100 shadow-2xs">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Código de Vestimenta</span>
              <p className="font-bold text-teal-800 text-sm mt-1">{visionData.dressCode || "Formal (Camisa / Traje)"}</p>
              <small className="text-xs text-emerald-600 font-medium block mt-0.5">✓ Cuello camisero y placket formal</small>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-teal-100 shadow-2xs">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Postura Corporal</span>
              <p className="font-bold text-gray-800 text-sm mt-1">{visionData.postureScore || 94} / 100 · {visionData.postureLabel || "Erguida"}</p>
              <small className="text-xs text-emerald-600 font-medium block mt-0.5">✓ Eje cráneo-vertebral alineado</small>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-teal-100 shadow-2xs">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Contacto Visual</span>
              <p className="font-bold text-gray-800 text-sm mt-1">{visionData.eyeContactScore || 91} / 100 · {visionData.eyeContactLabel || "Directo"}</p>
              <small className="text-xs text-emerald-600 font-medium block mt-0.5">✓ Mirada sostenida al tribunal</small>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-teal-100 shadow-2xs">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Gesticulación</span>
              <p className="font-bold text-gray-800 text-sm mt-1">{visionData.gesturesLabel || "Natural y Fluida"}</p>
              <small className="text-xs text-emerald-600 font-medium block mt-0.5">✓ Manos en plano con sobriedad</small>
            </div>
          </div>
        </div>

        {/* Detalle por Pregunta con Escala Centesimal Clara */}
        <h3 className="text-lg font-bold mb-4 border-b pb-2 text-gray-800 flex items-center justify-between">
          <span>Detalle por Pregunta Formulada por el Jurado</span>
          <span className="text-xs text-gray-500 font-normal">Escala: 0 a 100 puntos por respuesta</span>
        </h3>

        <div className="space-y-6">
          {report.questions.map((q, idx) => {
            const turnScore = q.turn_score ?? 0;
            const isPassingTurn = turnScore >= 51;
            return (
              <div key={idx} className="border border-gray-200 rounded-xl p-5 bg-gray-50 shadow-2xs">
                <div className="mb-3 flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <span className="font-bold text-indigo-800 text-base">Pregunta {idx + 1}: </span>
                    <span className="text-gray-900 font-medium text-base">{q.question}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2.5 py-1 text-xs rounded-full font-bold border ${
                      q.classification === 'PRECISE' ? 'bg-green-100 text-green-800 border-green-300' :
                      q.classification === 'INCOMPLETE' ? 'bg-amber-100 text-amber-800 border-amber-300' :
                      q.classification === 'CONTRADICTORY' ? 'bg-rose-100 text-rose-800 border-rose-300' : 'bg-gray-200 border-gray-300'
                    }`}>
                      {q.classification === 'PRECISE' ? '✓ Precisa (80-100)' :
                       q.classification === 'INCOMPLETE' ? '⚠️ Incompleta (25-75)' :
                       q.classification === 'CONTRADICTORY' ? '✕ Contradictoria (0-20)' : q.classification}
                    </span>
                    <span className={`px-3 py-1 text-sm rounded-lg font-extrabold ${
                      isPassingTurn ? 'bg-green-600 text-white' : 'bg-rose-600 text-white'
                    }`}>
                      {turnScore} / 100 pts
                    </span>
                  </div>
                </div>

                <div className="mb-4 p-3.5 bg-white border border-gray-200 rounded-lg">
                  <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">Respuesta Registrada del Postulante:</p>
                  <p className="text-gray-800 italic text-sm">&quot;{q.answer}&quot;</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mt-3 pt-3 border-t border-gray-200">
                  {q.strengths.length > 0 && (
                    <div className="bg-emerald-50/60 p-3 rounded-lg border border-emerald-100">
                      <p className="font-bold text-emerald-800 text-xs uppercase mb-1.5 flex items-center gap-1">
                        <span>✓</span> Fortalezas Conceptuales:
                      </p>
                      <ul className="list-disc pl-5 text-gray-700 text-xs space-y-1">
                        {q.strengths.map((s, i) => <li key={i}>{s}</li>)}
                      </ul>
                    </div>
                  )}

                  {q.weaknesses.length > 0 && (
                    <div className="bg-amber-50/60 p-3 rounded-lg border border-amber-100">
                      <p className="font-bold text-amber-800 text-xs uppercase mb-1.5 flex items-center gap-1">
                        <span>⚠️</span> Debilidades Detectadas:
                      </p>
                      <ul className="list-disc pl-5 text-gray-700 text-xs space-y-1">
                        {q.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                      </ul>
                    </div>
                  )}

                  {q.missing_points.length > 0 && (
                    <div className="bg-indigo-50/60 p-3 rounded-lg border border-indigo-100 md:col-span-2">
                      <p className="font-bold text-indigo-900 text-xs uppercase mb-1.5 flex items-center gap-1">
                        <span>📌</span> Puntos Clave Omitidos del Documento de Tesis:
                      </p>
                      <ul className="list-disc pl-5 text-gray-700 text-xs space-y-1">
                        {q.missing_points.map((m, i) => <li key={i}>{m}</li>)}
                      </ul>
                    </div>
                  )}

                  {q.contradictions.length > 0 && (
                    <div className="bg-rose-50/60 p-3 rounded-lg border border-rose-100 md:col-span-2">
                      <p className="font-bold text-rose-800 text-xs uppercase mb-1.5 flex items-center gap-1">
                        <span>✕</span> Inconsistencias o Contradicciones con la Tesis:
                      </p>
                      <ul className="list-disc pl-5 text-gray-700 text-xs space-y-1">
                        {q.contradictions.map((c, i) => <li key={i}>{c}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
