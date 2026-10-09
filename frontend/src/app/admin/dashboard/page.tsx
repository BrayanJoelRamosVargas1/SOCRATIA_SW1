"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

interface DashboardMetrics {
  total_users: number;
  documents_by_status: Record<string, number>;
  simulations_by_status: Record<string, number>;
  evaluations_by_status: Record<string, number>;
  average_overall_score: number | null;
  integration_metrics: string | Record<string, unknown>;
}

export default function AdminDashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const data = await apiRequest<DashboardMetrics>("/admin/dashboard");
        setMetrics(data);
        setError(null);
      } catch (err: unknown) {
        setError((err as Error).message || "Error al cargar las métricas.");
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (loading) {
    return <div className="p-8"><p>Cargando métricas...</p></div>;
  }

  if (error) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-red-600 mb-4">Error</h1>
        <p>{error}</p>
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Supervisión de Plataforma</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Usuarios */}
        <div className="bg-white p-6 rounded-lg shadow border">
          <h2 className="text-xl font-semibold mb-2 text-gray-700">Usuarios Totales</h2>
          <p className="text-4xl font-bold text-blue-600">{metrics.total_users}</p>
        </div>

        {/* Evaluaciones (Promedio) */}
        <div className="bg-white p-6 rounded-lg shadow border">
          <h2 className="text-xl font-semibold mb-2 text-gray-700">Promedio Evaluaciones</h2>
          <p className="text-4xl font-bold text-green-600">
            {metrics.average_overall_score !== null 
              ? metrics.average_overall_score.toFixed(2) 
              : "N/A"}
          </p>
        </div>

        {/* Métricas de Integración */}
        <div className="bg-white p-6 rounded-lg shadow border">
          <h2 className="text-xl font-semibold mb-2 text-gray-700">Telemetría (Integraciones)</h2>
          <p className="text-xl font-bold text-gray-500">
            {typeof metrics.integration_metrics === 'string' 
              ? metrics.integration_metrics 
              : JSON.stringify(metrics.integration_metrics)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        {/* Documentos */}
        <div className="bg-white p-6 rounded-lg shadow border">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">Documentos por Estado</h2>
          {Object.keys(metrics.documents_by_status).length > 0 ? (
            <ul className="space-y-2">
              {Object.entries(metrics.documents_by_status).map(([status, count]) => (
                <li key={status} className="flex justify-between border-b pb-1">
                  <span className="text-gray-600">{status}</span>
                  <span className="font-semibold">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500">Sin datos</p>
          )}
        </div>

        {/* Simulaciones */}
        <div className="bg-white p-6 rounded-lg shadow border">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">Simulaciones por Estado</h2>
          {Object.keys(metrics.simulations_by_status).length > 0 ? (
            <ul className="space-y-2">
              {Object.entries(metrics.simulations_by_status).map(([status, count]) => (
                <li key={status} className="flex justify-between border-b pb-1">
                  <span className="text-gray-600">{status}</span>
                  <span className="font-semibold">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500">Sin datos</p>
          )}
        </div>

        {/* Evaluaciones por estado */}
        <div className="bg-white p-6 rounded-lg shadow border">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">Evaluaciones por Estado</h2>
          {Object.keys(metrics.evaluations_by_status).length > 0 ? (
            <ul className="space-y-2">
              {Object.entries(metrics.evaluations_by_status).map(([status, count]) => (
                <li key={status} className="flex justify-between border-b pb-1">
                  <span className="text-gray-600">{status}</span>
                  <span className="font-semibold">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500">Sin datos</p>
          )}
        </div>
      </div>
    </div>
  );
}
