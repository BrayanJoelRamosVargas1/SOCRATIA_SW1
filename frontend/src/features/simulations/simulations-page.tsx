"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { getCurrentUser } from "@/features/auth/api";
import { deleteSimulation, listSimulations } from "@/features/simulations/api";
import { ApiError } from "@/lib/api";
import type { Simulation } from "@/types/simulation";
import type { User } from "@/types/user";

const STATUS_LABEL = { DRAFT: "Configurando", READY: "Lista", ACTIVE: "Activa", COMPLETED: "Completada", ABORTED: "Abortada", ERROR: "Error" };

export function SimulationsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getCurrentUser(), listSimulations()])
      .then(([current, items]) => { setUser(current); setSimulations(items); })
      .catch(() => router.replace("/login"));
  }, [router]);

  async function remove(item: Simulation) {
    if (!window.confirm(`¿Eliminar la simulación de “${item.document.name}”?`)) return;
    try {
      await deleteSimulation(item.id);
      setSimulations((current) => current.filter((simulation) => simulation.id !== item.id));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No pudimos eliminar la simulación.");
    }
  }

  if (!user) return <main className="loading-screen"><div className="loading-orbit" /><p>Cargando simulaciones…</p></main>;
  return (
    <main className="dashboard-layout">
      <AppSidebar user={user} active="simulations" />
      <section className="dashboard-content simulations-content">
        <header className="dashboard-header"><div><p className="eyebrow">P3 · Simulación</p><h1>Mis simulaciones</h1><p>Configura tu tribunal y comprueba tus dispositivos antes de comenzar.</p></div><Link className="button button-primary" href="/simulations/new">Nueva simulación</Link></header>
        {error && <p className="form-error">{error}</p>}
        {simulations.length === 0 ? <section className="simulation-empty"><b>03</b><h2>Tu primera defensa empieza aquí</h2><p>Necesitas un documento procesado con su banco de preguntas listo.</p><Link className="button button-primary" href="/simulations/new">Configurar simulación</Link></section> : <div className="simulation-grid">{simulations.map((item) => <article className="simulation-card" key={item.id}><div className="simulation-card-top"><span className={`simulation-state state-${item.status.toLowerCase()}`}>{STATUS_LABEL[item.status]}</span><small>{item.planned_duration_minutes} min</small></div><h2>{item.document.name}</h2><p>{item.jury_profile.name} · {item.question_count} preguntas</p><div className="simulation-card-actions"><Link className="button button-primary" href={item.status === "DRAFT" ? `/simulations/${item.id}/calibration` : `/simulations/${item.id}`}>{item.status === "DRAFT" ? "Calibrar" : "Ver preparación"}</Link>{["DRAFT", "READY"].includes(item.status) && <button className="danger-button" type="button" onClick={() => void remove(item)}>Eliminar</button>}</div></article>)}</div>}
      </section>
    </main>
  );
}
