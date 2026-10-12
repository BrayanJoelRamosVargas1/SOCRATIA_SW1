"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { SimulationReportResponse } from "@/types/report";
import { getSimulationReport, getEvaluation, evaluateSimulation } from "@/features/simulations/api";

export default function ReportPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();

  const [report, setReport] = useState<SimulationReportResponse | null>(null);
  const [evalStatus, setEvalStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading] = useState(false); // remove setDownloading if not used

  useEffect(() => {
    async function load() {
      try {
        const data = await getSimulationReport(id);
        setReport(data);
      } catch (err: unknown) {
        const isNotCompleted = err instanceof Error && err.message?.includes("not completed");
        if (isNotCompleted) {
          try {
            const ev = await getEvaluation(id);
            setEvalStatus(ev.status);
          } catch {
            setError("No se pudo obtener el estado de la evaluación.");
          }
        } else {
          setError(err instanceof Error ? err.message : "Error al cargar reporte.");
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const downloadPDF = () => {
    window.print();
  };

  if (loading) return <div className="p-8 text-center">Cargando reporte...</div>;

  if (evalStatus === "PENDING" || evalStatus === "PROCESSING") {
    return (
      <div className="p-8 max-w-3xl mx-auto text-center">
        <h2 className="text-2xl font-bold mb-4">La evaluación todavía está en proceso</h2>
        <p className="text-gray-600">Por favor, regresa más tarde.</p>
        <button onClick={() => router.push(`/simulations/${id}`)} className="mt-4 text-blue-600 underline">Volver a simulación</button>
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
            <p className="font-bold text-2xl text-blue-900">{report.overall_score ?? "No disponible"}</p>
          </div>
        </div>

        <h3 className="text-lg font-bold mb-4 border-b pb-2">Dimensiones</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="border p-4 rounded text-center">
            <p className="font-semibold text-gray-600 mb-2">Contenido</p>
            <p className="text-2xl font-bold">{report.availability.content ? report.content_score : "No disponible"}</p>
          </div>
          <div className="border p-4 rounded text-center">
            <p className="font-semibold text-gray-600 mb-2">Comunicación</p>
            <p className="text-2xl font-bold">{report.availability.communication ? report.communication_score : "No disponible"}</p>
          </div>
          <div className="border p-4 rounded text-center">
            <p className="font-semibold text-gray-600 mb-2">No verbal</p>
            <p className="text-2xl font-bold">{report.availability.nonverbal ? report.nonverbal_score : "No disponible"}</p>
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
