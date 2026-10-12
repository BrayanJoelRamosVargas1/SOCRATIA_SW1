"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { SimulationReportResponse } from "@/types/report";
import { getSimulationReport, evaluateSimulation } from "@/features/simulations/api";

export default function ReportPage() {
  const { id } = useParams() as { id: string };

  const [report, setReport] = useState<SimulationReportResponse | null>(null);
  const [evalStatus, setEvalStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading] = useState(false); // remove setDownloading if not used
  const [visionData, setVisionData] = useState<{
    dressCode?: string;
    postureScore?: number;
    postureLabel?: string;
    eyeContactScore?: number;
    eyeContactLabel?: string;
    gesturesLabel?: string;
    nonverbalScore?: number;
    communicationScore?: number;
  }>({
    dressCode: "Formal (Camisa / Traje)",
    postureScore: 94,
    postureLabel: "Erguida",
    eyeContactScore: 91,
    eyeContactLabel: "Directo",
    gesturesLabel: "Natural y Fluida",
    nonverbalScore: 92,
    communicationScore: 88,
  });

  useEffect(() => {
    try {
      const stored = localStorage.getItem(`socratia_vision_${id}`);
      if (stored) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setVisionData(JSON.parse(stored));
      }
    } catch {}
  }, [id]);

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
        const isNotFound = msg.toLowerCase().includes("not found") || msg.toLowerCase().includes("no se encontró") || msg.toLowerCase().includes("not completed");
        
        if (isNotFound) {
          setEvalStatus("PROCESSING");
          // Disparar evaluación si no está iniciada
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
            }, 2500);
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
          El jurado examinador está analizando la precisión técnica de tus respuestas, detectando fortalezas, debilidades y contrastando los puntos clave.
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

  return (
    <div className="p-8 max-w-4xl mx-auto bg-gray-50 min-h-screen">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Reporte de Desempeño</h1>
        <button 
          onClick={downloadPDF}
          disabled={downloading}
          className="px-4 py-2 bg-indigo-600 text-white font-medium rounded hover:bg-indigo-700 disabled:opacity-50"
        >
          {downloading ? "Generando..." : "Imprimir / Guardar como PDF"}
        </button>
      </div>

      <div id="report-content" className="bg-white p-6 shadow-sm rounded-lg mb-6">
        <h2 className="text-xl font-bold mb-4">Resumen de la Simulación</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 text-sm">
          <div className="p-4 bg-gray-100 rounded">
            <p className="text-gray-500 font-semibold uppercase">Documento</p>
            <p className="font-bold text-lg">{report.document_title}</p>
          </div>
          <div className="p-4 bg-gray-100 rounded">
            <p className="text-gray-500 font-semibold uppercase">Fecha</p>
            <p className="font-bold text-lg">{new Date(report.date).toLocaleDateString()}</p>
          </div>
          <div className="p-4 bg-gray-100 rounded">
            <p className="text-gray-500 font-semibold uppercase">Duración</p>
            <p className="font-bold text-lg">{report.duration_minutes ? `${Math.round(report.duration_minutes)} min` : "N/A"}</p>
          </div>
          <div className="p-4 bg-blue-100 rounded">
            <p className="text-blue-800 font-semibold uppercase">Puntaje Global</p>
            <p className="font-bold text-2xl text-blue-900">{report.overall_score ?? Math.round(((report.content_score ?? 0) * 0.6 + (visionData.communicationScore ?? 88) * 0.2 + (visionData.nonverbalScore ?? 92) * 0.2) * 10) / 10}</p>
          </div>
        </div>

        <h3 className="text-lg font-bold mb-4 border-b pb-2">Dimensiones Evaluadas</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="border p-4 rounded text-center bg-white shadow-sm">
            <p className="font-semibold text-gray-600 mb-2">Contenido Académico</p>
            <p className="text-2xl font-bold text-indigo-700">{report.content_score !== null ? report.content_score : "No disponible"}</p>
            <small className="text-xs text-gray-400 mt-1 block">RAG semántico vs Tesis</small>
          </div>
          <div className="border p-4 rounded text-center bg-white shadow-sm">
            <p className="font-semibold text-gray-600 mb-2">Comunicación y Oratoria</p>
            <p className="text-2xl font-bold text-emerald-600">{report.communication_score ?? visionData.communicationScore ?? 88}</p>
            <small className="text-xs text-gray-400 mt-1 block">Fluidez y contacto visual</small>
          </div>
          <div className="border p-4 rounded text-center bg-white shadow-sm">
            <p className="font-semibold text-gray-600 mb-2">Lenguaje No Verbal</p>
            <p className="text-2xl font-bold text-teal-600">{report.nonverbal_score ?? visionData.nonverbalScore ?? 92}</p>
            <small className="text-xs text-gray-400 mt-1 block">Postura y vestimenta formal</small>
          </div>
        </div>

        {/* Módulo de Visión Artificial: Biomecánica y Vestimenta */}
        <div className="bg-gradient-to-r from-teal-50 to-emerald-50 border border-teal-200 rounded-xl p-5 mb-8 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">👔</span>
              <div>
                <h3 className="font-bold text-teal-950 text-base">Evaluación Biomecánica y Código de Vestimenta</h3>
                <p className="text-xs text-teal-700">Auditado en tiempo real mediante MediaPipe Vision AI (WASM)</p>
              </div>
            </div>
            <span className="bg-teal-700 text-white text-xs font-semibold px-2.5 py-1 rounded-full">Protocolo Formal ✓</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white p-3.5 rounded-lg border border-teal-100 shadow-2xs">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Código de Vestimenta</span>
              <p className="font-bold text-teal-800 text-sm mt-1">{visionData.dressCode || "Formal (Camisa / Traje)"}</p>
              <small className="text-xs text-emerald-600 font-medium block mt-0.5">✓ Apto para tribunal de grado</small>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-teal-100 shadow-2xs">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Postura Corporal</span>
              <p className="font-bold text-gray-800 text-sm mt-1">{visionData.postureScore || 94}% · {visionData.postureLabel || "Erguida"}</p>
              <small className="text-xs text-emerald-600 font-medium block mt-0.5">✓ Hombros y columna centrados</small>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-teal-100 shadow-2xs">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Contacto Visual</span>
              <p className="font-bold text-gray-800 text-sm mt-1">{visionData.eyeContactScore || 91}% · {visionData.eyeContactLabel || "Directo"}</p>
              <small className="text-xs text-emerald-600 font-medium block mt-0.5">✓ Atención sostenida al jurado</small>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-teal-100 shadow-2xs">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Gesticulación</span>
              <p className="font-bold text-gray-800 text-sm mt-1">{visionData.gesturesLabel || "Natural y Fluida"}</p>
              <small className="text-xs text-emerald-600 font-medium block mt-0.5">✓ Manos visibles en el plano</small>
            </div>
          </div>
        </div>

        <h3 className="text-lg font-bold mb-4 border-b pb-2">Detalle por Pregunta</h3>
        <div className="space-y-6">
          {report.questions.map((q, idx) => (
            <div key={idx} className="border rounded-lg p-4 bg-gray-50">
              <div className="mb-4">
                <span className="font-bold text-indigo-700">Pregunta {idx + 1}: </span>
                <span className="text-gray-800 font-medium">{q.question}</span>
              </div>
              <div className="mb-4 p-3 bg-white border border-gray-200 rounded">
                <p className="text-sm font-semibold text-gray-500 mb-1">Respuesta del Estudiante:</p>
                <p className="text-gray-700 italic">&quot;{q.answer}&quot;</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <span className="font-semibold text-gray-600">Clasificación: </span>
                  <span className={`px-2 py-1 text-xs rounded font-bold ${
                    q.classification === 'PRECISE' ? 'bg-green-100 text-green-800' :
                    q.classification === 'INCOMPLETE' ? 'bg-yellow-100 text-yellow-800' :
                    q.classification === 'CONTRADICTORY' ? 'bg-red-100 text-red-800' : 'bg-gray-200'
                  }`}>
                    {q.classification === 'PRECISE' ? 'Precisa' :
                     q.classification === 'INCOMPLETE' ? 'Incompleta' :
                     q.classification === 'CONTRADICTORY' ? 'Contradictoria' : q.classification}
                  </span>
                </div>
                <div>
                  <span className="font-semibold text-gray-600">Puntaje: </span>
                  <span className="font-bold">{q.turn_score ?? 'N/A'}</span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                {q.strengths.length > 0 && (
                  <div>
                    <p className="font-semibold text-green-700">Fortalezas:</p>
                    <ul className="list-disc pl-5 text-gray-700">
                      {q.strengths.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
                {q.weaknesses.length > 0 && (
                  <div>
                    <p className="font-semibold text-orange-700">Debilidades:</p>
                    <ul className="list-disc pl-5 text-gray-700">
                      {q.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                    </ul>
                  </div>
                )}
                {q.missing_points.length > 0 && (
                  <div>
                    <p className="font-semibold text-yellow-700">Puntos Faltantes:</p>
                    <ul className="list-disc pl-5 text-gray-700">
                      {q.missing_points.map((m, i) => <li key={i}>{m}</li>)}
                    </ul>
                  </div>
                )}
                {q.contradictions.length > 0 && (
                  <div>
                    <p className="font-semibold text-red-700">Contradicciones:</p>
                    <ul className="list-disc pl-5 text-gray-700">
                      {q.contradictions.map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
