"use client";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";

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

  const active = simulation?.status === "ACTIVE";
  const completed = simulation?.status === "COMPLETED";
  const checks = simulation ? [
    ["Documento", simulation.document.name, true],
    ["Banco de preguntas", `${simulation.question_count} preguntas disponibles`, simulation.question_count > 0],
    ["Jurado", simulation.jury_profile.name, true],
    ["Cámara", simulation.camera_ready ? "Lista" : "Pendiente", simulation.camera_ready],
    ["Micrófono", simulation.microphone_ready ? "Listo" : "Pendiente", simulation.microphone_ready],
    ["Visión", simulation.vision_ready ? "Persona detectada" : "Pendiente", simulation.vision_ready],
  ] as const : [];

  return (
    <main className="dashboard-layout">
      <AppSidebar user={user} active="simulations" />
      <section className="dashboard-content simulations-content">
        {!user || !simulation ? (
          <LoadingSkeleton label="Abriendo preparación…"/>
        ) : (
          <>
            <Link className="detail-back" href="/simulations">
              ← Simulaciones
            </Link>
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">Preparación de simulación</p>
            <h1>{simulation.document.name}</h1>
            <p>{simulation.jury_profile.name} · {simulation.planned_duration_minutes} minutos</p>
          </div>
          <span className={`simulation-state state-${simulation.status.toLowerCase()}`}>
            {simulation.status}
          </span>
        </header>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <section className="readiness-card">
          <h2>
            {completed
              ? "Defensa completada"
              : active
              ? "Tu defensa está en curso"
              : simulation.status === "READY"
              ? "¡Todo listo para defender tu tesis!"
              : "Completa la calibración de hardware"}
          </h2>

          <div className="readiness-list">
            {checks.map(([label, value, ready]) => (
              <div key={label}>
                <b className={ready ? "ready" : "pending"}>{ready ? "✓" : "○"}</b>
                <span>
                  <strong>{label}</strong>
                  <small>{value}</small>
                </span>
              </div>
            ))}
          </div>

          <div className="readiness-actions">
            {completed ? (
              <>
                <Link className="button button-primary" href={`/simulations/${simulation.id}/report`}>
                  📊 Ver reporte de desempeño
                </Link>
                <Link className="button" href="/simulations/new">
                  Nueva simulación
                </Link>
              </>
            ) : active ? (
              <Link className="button button-primary" href={`/simulations/${simulation.id}/live`}>
                Volver a la sala
              </Link>
            ) : simulation.status === "READY" ? (
              <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
                <button
                  className="button button-primary"
                  type="button"
                  style={{ fontWeight: 700, padding: "0.75rem 1.75rem", fontSize: "1rem" }}
                  disabled={starting}
                  onClick={() => void start()}
                >
                  {starting ? "Iniciando sala…" : "🚀 Iniciar Simulación Ahora →"}
                </button>
                <Link className="button button-secondary" href={`/simulations/${simulation.id}/calibration`}>
                  Repetir calibración
                </Link>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", width: "100%" }}>
                <div style={{ padding: "0.75rem 1rem", background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", borderRadius: "8px", fontSize: "0.85rem", color: "#b45309" }}>
                  ⚠️ <strong>Paso Requerido:</strong> Para habilitar el inicio de la defensa, debes calibrar la cámara y el micrófono primero.
                </div>
                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
                  <Link className="button button-primary" href={`/simulations/${simulation.id}/calibration`}>
                    🎙️ Calibrar Dispositivos Ahora →
                  </Link>
                  <button
                    className="button"
                    type="button"
                    disabled
                    title="Debes calibrar tus dispositivos primero"
                    style={{ opacity: 0.6, cursor: "not-allowed" }}
                  >
                    🔒 Iniciar simulación (Bloqueado hasta calibrar)
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>
        </>
        )}
      </section>
    </main>
  );
}
