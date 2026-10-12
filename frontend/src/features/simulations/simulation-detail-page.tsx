"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { getCurrentUser } from "@/features/auth/api";
import { getSimulation, startSimulation } from "@/features/simulations/api";
import type { Simulation } from "@/types/simulation";
import type { User } from "@/types/user";

export function SimulationDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getCurrentUser(), getSimulation(params.id)])
      .then(([current, item]) => { setUser(current); setSimulation(item); })
      .catch(() => router.replace("/simulations"));
  }, [params.id, router]);

  async function start() {
    setStarting(true); setError("");
    try {
      await startSimulation(params.id);
      router.push(`/simulations/${params.id}/live`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo iniciar la simulación.");
      setStarting(false);
    }
  }

  if (!user || !simulation) return <main className="loading-screen"><div className="loading-orbit" /><p>Abriendo preparación…</p></main>;
  const checks = [["Documento", simulation.document.name, true], ["Banco de preguntas", `${simulation.question_count} preguntas disponibles`, simulation.question_count === 12], ["Jurado", simulation.jury_profile.name, true], ["Cámara", simulation.camera_ready ? "Lista" : "Pendiente", simulation.camera_ready], ["Micrófono", simulation.microphone_ready ? "Listo" : "Pendiente", simulation.microphone_ready], ["Visión", simulation.vision_ready ? "Persona detectada" : "Pendiente", simulation.vision_ready]] as const;
  const active = simulation.status === "ACTIVE";
  const completed = simulation.status === "COMPLETED";
  return <main className="dashboard-layout"><AppSidebar user={user} active="simulations" /><section className="dashboard-content simulations-content"><Link className="detail-back" href="/simulations">← Simulaciones</Link><header className="dashboard-header"><div><p className="eyebrow">Preparación de simulación</p><h1>{simulation.document.name}</h1><p>{simulation.jury_profile.name} · {simulation.planned_duration_minutes} minutos</p></div><span className={`simulation-state state-${simulation.status.toLowerCase()}`}>{simulation.status}</span></header>{error && <p className="form-error" role="alert">{error}</p>}<section className="readiness-card"><h2>{completed ? "Defensa completada" : active ? "Tu defensa está en curso" : simulation.status === "READY" ? "Todo está preparado" : "Completa la calibración"}</h2><div className="readiness-list">{checks.map(([label, value, ready]) => <div key={label}><b className={ready ? "ready" : "pending"}>{ready ? "✓" : "○"}</b><span><strong>{label}</strong><small>{value}</small></span></div>)}</div><div className="readiness-actions">{completed ? (<><Link className="button button-primary" href={`/simulations/${simulation.id}/report`}>Ver reporte de desempeño</Link><Link className="button" href="/simulations/new">Nueva simulación</Link></>) : active ? (<Link className="button button-primary" href={`/simulations/${simulation.id}/live`}>Volver a la sala</Link>) : (<><Link className="button button-primary" href={`/simulations/${simulation.id}/calibration`}>{simulation.status === "READY" ? "Repetir calibración" : "Calibrar dispositivos"}</Link><button className="button" type="button" disabled={simulation.status !== "READY" || starting} onClick={() => void start()}>{starting ? "Iniciando…" : "Iniciar simulación"}</button></>)}</div></section></section></main>;
}
