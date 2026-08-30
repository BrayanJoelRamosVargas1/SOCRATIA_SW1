"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { getCurrentUser } from "@/features/auth/api";
import { getQuestionBank, listDocuments } from "@/features/documents/api";
import { createSimulation, listJuryProfiles } from "@/features/simulations/api";
import { ApiError } from "@/lib/api";
import type { Document } from "@/types/document";
import type { JuryProfile } from "@/types/simulation";
import type { User } from "@/types/user";

const JURY_ICON = { METHODOLOGICAL: "🔬", TECHNICAL: "💻", CRITICAL: "⚠" };

export function NewSimulationPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [juries, setJuries] = useState<JuryProfile[]>([]);
  const [documentId, setDocumentId] = useState("");
  const [juryId, setJuryId] = useState("");
  const [duration, setDuration] = useState(15);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getCurrentUser(), listDocuments(), listJuryProfiles()])
      .then(async ([current, allDocuments, profiles]) => {
        const processed = allDocuments.filter((item) => item.status === "PROCESSED");
        const eligibility = await Promise.all(processed.map(async (item) => { try { await getQuestionBank(item.id); return item; } catch { return null; } }));
        const ready = eligibility.filter((item): item is Document => item !== null);
        setUser(current); setDocuments(ready); setJuries(profiles);
        setDocumentId(ready[0]?.id ?? ""); setJuryId(profiles[0]?.id ?? "");
      })
      .catch(() => router.replace("/login"));
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

  if (!user) return <main className="loading-screen"><div className="loading-orbit" /><p>Preparando configuración…</p></main>;
  return <main className="dashboard-layout"><AppSidebar user={user} active="simulations" /><section className="dashboard-content simulations-content"><Link className="detail-back" href="/simulations">← Simulaciones</Link><header className="dashboard-header"><div><p className="eyebrow">CU12 · CU13</p><h1>Nueva simulación</h1><p>Elige el trabajo, el estilo del tribunal y tu tiempo disponible.</p></div></header>{error && <p className="form-error">{error}</p>}<section className="simulation-form-card"><label className="simulation-field">Documento<select value={documentId} onChange={(event) => setDocumentId(event.target.value)}><option value="">Selecciona un documento listo</option>{documents.map((item) => <option value={item.id} key={item.id}>{item.original_name}</option>)}</select></label>{documents.length === 0 && <p className="form-hint">Primero procesa un documento y genera su banco de 12 preguntas.</p>}<div className="simulation-field"><span>Perfil del jurado</span><div className="jury-grid">{juries.map((jury) => <button type="button" key={jury.id} className={`jury-option ${juryId === jury.id ? "selected" : ""}`} onClick={() => setJuryId(jury.id)}><b>{JURY_ICON[jury.focus_type]}</b><strong>{jury.name}</strong><p>{jury.description}</p><small>Exigencia {jury.strictness}/5 · Interrupción {jury.interruption_level.toLowerCase()}</small></button>)}</div></div><label className="simulation-field duration-field">Duración planificada<span><input type="range" min="5" max="30" step="5" value={duration} onChange={(event) => setDuration(Number(event.target.value))} /><b>{duration} minutos</b></span></label><button className="button button-primary simulation-submit" type="button" disabled={!documentId || !juryId || saving} onClick={() => void submit()}>{saving ? "Creando…" : "Continuar a calibración"}</button></section></section></main>;
}
