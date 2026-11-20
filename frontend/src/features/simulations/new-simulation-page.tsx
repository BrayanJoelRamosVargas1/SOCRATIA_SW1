"use client";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { getCurrentUser } from "@/features/auth/api";
import { listDocuments } from "@/features/documents/api";
import { createSimulation, listJuryProfiles } from "@/features/simulations/api";
import { apiRequest, ApiError } from "@/lib/api";
import type { Document } from "@/types/document";
import type { JuryProfile } from "@/types/simulation";
import type { User } from "@/types/user";

const JURY_ICON = { METHODOLOGICAL: "01", TECHNICAL: "02", CRITICAL: "03" };

export function NewSimulationPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [juries, setJuries] = useState<JuryProfile[]>([]);
  const [readyIds, setReadyIds] = useState<string[]>([]);
  const [documentId, setDocumentId] = useState("");
  const [juryId, setJuryId] = useState("");
  const [duration, setDuration] = useState(15);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getCurrentUser(), listDocuments(), listJuryProfiles(), apiRequest<{ready_document_ids:string[]}>("/documents/readiness")])
      .then(([current, allDocuments, profiles, readiness]) => {
        setUser(current); setDocuments(allDocuments); setJuries(profiles);
        const ready = allDocuments.filter(item=>readiness.ready_document_ids.includes(item.id));
        setReadyIds(readiness.ready_document_ids);
        setDocumentId(ready[0]?.id ?? allDocuments[0]?.id ?? ""); setJuryId(profiles[0]?.id ?? "");
      })
      .catch((caught) => { if (caught instanceof ApiError && caught.status === 401) router.replace("/login"); else setError("No se pudo cargar la configuración. Revisa la conexión y actualiza la página."); });
  }, [router]);

  async function submit() {
    if (!documentId || !juryId || saving) return;
    setSaving(true); setError("");
    try {
      const simulation = await createSimulation({ document_id: documentId, jury_profile_id: juryId, planned_duration_minutes: duration });
      router.push(`/simulations/${simulation.id}/calibration`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No pudimos crear la simulación.");
      setSaving(false);
    }
  }

  function getDifficultyBadge(strictness: number) {
    if (strictness <= 2) {
      return { label: "Formativo", color: "#166534", bg: "#dcfce7" };
    }
    if (strictness === 3) {
      return { label: "Intermedio", color: "#854d0e", bg: "#fef9c3" };
    }
    return { label: "Exigente", color: "#991b1b", bg: "#fee2e2" };
  }

  return (
    <main className="dashboard-layout">
      <AppSidebar user={user} active="simulations" />
      <section className="dashboard-content simulations-content">
        {!user && error ? <div role="alert"><p>{error}</p><Link href="/documents">Volver a documentos</Link></div> : !user ? (
          <LoadingSkeleton label="Preparando configuración…"/>
        ) : (
          <>
            <Link className="detail-back" href="/simulations">
              ← Simulaciones
            </Link>
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">PREPARA TU PRÁCTICA</p>
            <h1>Nueva Simulación de Defensa</h1>
            <p>Selecciona tu tesis de grado, el tribunal evaluador y la rigurosidad socrática.</p>
          </div>
        </header>
        {error && <p className="form-error">{error}</p>}
        <section className="simulation-form-card">
          <label className="simulation-field">
            Documento de Tesis
            <select value={documentId} onChange={(event) => setDocumentId(event.target.value)}>
              <option value="">Selecciona un documento procesado</option>
              {documents.map((item) => (
                <option value={item.id} key={item.id}>

                  {item.original_name}{readyIds.includes(item.id) ? " · listo para practicar" : item.status === "PROCESSED" ? " · falta preparar preguntas" : " · pendiente de procesamiento"}
                </option>
              ))}
            </select>
          </label>
          {documentId && !readyIds.includes(documentId) && <p className="form-hint" role="status">Tu documento está guardado. {documents.find(item=>item.id===documentId)?.status === "PROCESSED" ? "Genera su banco de preguntas para usarlo en la defensa." : "Primero procesa el archivo y después genera sus preguntas."} <Link href={`/documents/${documentId}`}>Preparar este documento →</Link></p>}
          {documents.length === 0 && (
            <p className="form-hint">
              Primero sube y procesa un documento académico para generar su banco de preguntas socráticas.
            </p>
          )}

          <div className="simulation-field">
            <span>Tribunal Jurado Evaluador</span>
            <div className="jury-grid">
              {juries.map((jury) => {
                const diff = getDifficultyBadge(jury.strictness);
                const isSelected = juryId === jury.id;
                return (
                  <button
                    type="button"
                    key={jury.id}
                    className={`jury-option ${isSelected ? "selected" : ""}`}
                    aria-pressed={isSelected}
                    onClick={() => setJuryId(jury.id)}
                    style={{ position: "relative" }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                      <b>{JURY_ICON[jury.focus_type]}</b>
                      <span
                        style={{
                          fontSize: "0.68rem",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "12px",
                          background: diff.bg,
                          color: diff.color,
                        }}
                      >
                        {diff.label}
                      </span>
                    </div>
                    <strong>{jury.name}</strong>
                    <p>{jury.description}</p>
                    <small>
                      Rigurosidad: {jury.strictness}/5 · Interrupción: {{LOW:"baja",MEDIUM:"media",HIGH:"alta"}[jury.interruption_level]} · Enfoque: {{METHODOLOGICAL:"metodológico",TECHNICAL:"técnico",CRITICAL:"crítico"}[jury.focus_type]}
                    </small>
                  </button>
                );
              })}
            </div>
          </div>

          <label className="simulation-field duration-field">
            Duración Planificada
            <span>
              <input
                type="range"
                min="5"
                max="30"
                step="5"
                value={duration}
                onChange={(event) => setDuration(Number(event.target.value))}
              />
              <b>{duration} minutos</b>
            </span>
          </label>

          <button
            className="button button-primary simulation-submit"
            type="button"
            disabled={!documentId || !readyIds.includes(documentId) || !juryId || saving}
            onClick={() => void submit()}
          >
            {saving ? "Creando sala…" : "Continuar a Calibración de Hardware →"}
          </button>
        </section>
        </>
        )}
      </section>
    </main>
  );
}
