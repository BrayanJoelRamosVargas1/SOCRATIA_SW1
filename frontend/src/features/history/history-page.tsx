"use client";

import { useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { BarChart3, Clock, FileText, ChevronLeft, ChevronRight, Activity } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/api";

type SimulationStatus = "DRAFT" | "READY" | "ACTIVE" | "COMPLETED" | "ABORTED" | "ERROR";
type EvaluationStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

interface PerformanceHistoryItem {
  simulation_id: string;
  document_title: string;
  created_at: string;
  duration_minutes: number;
  simulation_status: SimulationStatus;
  evaluation_status: EvaluationStatus | null;
  overall_score: number | null;
  content_score: number | null;
  communication_score: number | null;
  nonverbal_score: number | null;
  delta_score: number | null;
  report_url: string;
}

interface PerformanceHistorySummary {
  total_simulations: number;
  evaluated_simulations: number;
  latest_score: number | null;
  best_score: number | null;
}

interface PerformanceHistoryResponse {
  summary: PerformanceHistorySummary;
  items: PerformanceHistoryItem[];
  total_items: number;
  page: number;
  page_size: number;
  total_pages: number;
}

const statusColor = (status: string) => {
  if (status === "COMPLETED") return "bg-green-100 text-green-800";
  if (status === "PENDING" || status === "PROCESSING") return "bg-yellow-100 text-yellow-800";
  if (status === "FAILED" || status === "ERROR" || status === "ABORTED") return "bg-red-100 text-red-800";
  return "bg-gray-100 text-gray-800";
};

const statusLabel = (status: string | null) => {
  if (status === "COMPLETED") return "Completado";
  if (status === "PENDING" || status === "PROCESSING") return "En Proceso";
  if (status === "FAILED") return "Fallido";
  if (status === "ERROR") return "Error";
  if (status === "ABORTED") return "Abortado";
  if (status === "READY") return "Listo";
  if (status === "ACTIVE") return "Activo";
  return status || "Desconocido";
};

export function HistoryPage() {
  const [data, setData] = useState<PerformanceHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    setLoading(true);
    apiRequest<PerformanceHistoryResponse>(`/performance-history?page=${page}&page_size=10`)
      .then((res) => {
        setData(res);
      })
      .catch((err) => {
        console.error("Error fetching history", err);
      })
      .finally(() => setLoading(false));
  }, [page]);

  if (loading && !data) {
    return <div className="p-8 text-center">Cargando historial...</div>;
  }

  if (!data) {
    return <div className="p-8 text-center text-red-500">Error al cargar historial</div>;
  }

  const { summary, items, total_pages } = data;
  
  // Extract completed evaluations in chronological order for the chart
  const evaluatedItems = [...items]
    .filter(item => item.evaluation_status === "COMPLETED" && item.overall_score !== null)
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Historial de Desempeño</h1>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Simulaciones</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.total_simulations}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Simulaciones Evaluadas</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.evaluated_simulations}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Último Puntaje</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.latest_score !== null ? `${summary.latest_score.toFixed(1)}/100` : "-"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mejor Puntaje</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {summary.best_score !== null ? `${summary.best_score.toFixed(1)}/100` : "-"}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Evolución de Desempeño</CardTitle>
          <CardDescription>Tu progreso general a lo largo de las simulaciones evaluadas</CardDescription>
        </CardHeader>
        <CardContent>
          {evaluatedItems.length < 2 ? (
            <div className="p-4 text-center text-muted-foreground bg-muted rounded-md">
              Necesitas al menos dos simulaciones evaluadas para visualizar tu evolución.
            </div>
          ) : (
            <div className="h-64 flex items-end gap-2 p-4 border rounded-md">
              {/* Very simple visual chart using DOM elements, no external libs needed per reqs */}
              {evaluatedItems.map((item, i) => (
                <div key={item.simulation_id} className="flex flex-col items-center flex-1 h-full justify-end group relative">
                   <div className="text-xs font-semibold mb-1 opacity-0 group-hover:opacity-100 transition-opacity absolute -top-6">
                      {item.overall_score?.toFixed(1)}
                   </div>
                   <div 
                     className="w-full bg-primary/80 rounded-t-sm transition-all group-hover:bg-primary"
                     style={{ height: `${Math.max(10, (item.overall_score || 0))}%` }}
                   ></div>
                   <div className="text-[10px] mt-2 text-muted-foreground truncate w-full text-center">
                     {format(parseISO(item.created_at), "dd/MM", { locale: es })}
                   </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Registro de Simulaciones</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No se encontraron simulaciones.
            </div>
          ) : (
            <div className="space-y-4">
              {items.map((item) => (
                <div key={item.simulation_id} className="flex flex-col md:flex-row items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors gap-4">
                  <div className="flex-1 space-y-1">
                    <h3 className="font-medium text-lg">{item.document_title}</h3>
                    <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {format(parseISO(item.created_at), "dd MMM yyyy, HH:mm", { locale: es })}
                      </span>
                      <span>•</span>
                      <span>{item.duration_minutes} min</span>
                      <span>•</span>
                      <Badge variant="secondary" className={statusColor(item.simulation_status)}>
                        Sim: {statusLabel(item.simulation_status)}
                      </Badge>
                      {item.evaluation_status && (
                        <Badge variant="secondary" className={statusColor(item.evaluation_status)}>
                          Eval: {statusLabel(item.evaluation_status)}
                        </Badge>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      {item.overall_score !== null ? (
                        <>
                          <div className="text-2xl font-bold">{item.overall_score.toFixed(1)}</div>
                          {item.delta_score !== null && (
                            <div className={`text-xs font-medium ${item.delta_score > 0 ? "text-green-600" : item.delta_score < 0 ? "text-red-600" : "text-gray-500"}`}>
                              {item.delta_score > 0 ? "+" : ""}{item.delta_score > 0 || item.delta_score < 0 ? item.delta_score.toFixed(1) + " puntos" : "Sin cambio"}
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="text-sm text-muted-foreground italic">
                          {item.simulation_status !== "COMPLETED" ? "Incompleta" : 
                           item.evaluation_status === "FAILED" ? "Evaluación fallida" : "En evaluación"}
                        </div>
                      )}
                    </div>
                    <Button asChild variant="outline" disabled={item.evaluation_status !== "COMPLETED"}>
                      {item.evaluation_status === "COMPLETED" ? (
                         <Link href={item.report_url}>Ver Reporte</Link>
                      ) : (
                         <span>Ver Reporte</span>
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {total_pages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                Página {page} de {total_pages}
              </p>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setPage(p => Math.min(total_pages, p + 1))}
                  disabled={page === total_pages}
                >
                  Siguiente <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
