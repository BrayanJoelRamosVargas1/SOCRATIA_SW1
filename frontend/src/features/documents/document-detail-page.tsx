"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { getCurrentUser } from "@/features/auth/api";
import {
  deleteDocument,
  getDocument,
  getDocumentStatus,
  processDocument,
} from "@/features/documents/api";
import { ApiError } from "@/lib/api";
import type { Document, ProcessingStatus } from "@/types/document";
import type { User } from "@/types/user";

function formatBytes(bytes: number): string {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1048576).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-BO", { dateStyle: "long", timeStyle: "short" }).format(new Date(value));
}

const STAGE_NAMES: Record<string, string> = {
  UPLOAD: "Documento recibido",
  EXTRACTION: "Texto extraído",
  CHUNKING: "Contenido fragmentado",
  EMBEDDING: "Embeddings generados",
  VECTOR_STORE: "Vectores indexados",
  COMPLETE: "Documento listo",
};

export function DocumentDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [user, setUser] = useState<User | null>(null);
  const [document, setDocument] = useState<Document | null>(null);
  const [processing, setProcessing] = useState<ProcessingStatus | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getCurrentUser(), getDocument(params.id), getDocumentStatus(params.id)])
      .then(([currentUser, currentDocument, currentStatus]) => {
        setUser(currentUser);
        setDocument(currentDocument);
        setProcessing(currentStatus);
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 404) setError("El documento no existe o no pertenece a tu cuenta.");
        else router.replace("/login");
      });
  }, [params.id, router]);

  async function remove() {
    if (!document || !window.confirm(`¿Eliminar “${document.original_name}”?`)) return;
    try {
      await deleteDocument(document.id);
      router.replace("/documents");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No pudimos eliminar el documento.");
    }
  }

  async function runProcessing() {
    if (!document || isProcessing) return;
    setError("");
    setIsProcessing(true);
    setDocument((current) => current ? { ...current, status: "PROCESSING" } : current);
    try {
      await processDocument(document.id);
      const [updatedDocument, updatedStatus] = await Promise.all([
        getDocument(document.id),
        getDocumentStatus(document.id),
      ]);
      setDocument(updatedDocument);
      setProcessing(updatedStatus);
    } catch (caught) {
      const [updatedDocument, updatedStatus] = await Promise.all([
        getDocument(document.id),
        getDocumentStatus(document.id),
      ]);
      setDocument(updatedDocument);
      setProcessing(updatedStatus);
      setError(caught instanceof ApiError ? caught.message : "No pudimos procesar el documento.");
    } finally {
      setIsProcessing(false);
    }
  }

  if (error && !user) {
    return <main className="loading-screen detail-error"><h1>Documento no disponible</h1><p>{error}</p><Link className="button button-primary" href="/documents">Volver a mis documentos</Link></main>;
  }
  if (!user || !document || !processing) {
    return <main className="loading-screen"><div className="loading-orbit" /><p>Abriendo documento…</p></main>;
  }

  return (
    <main className="dashboard-layout">
      <AppSidebar user={user} active="documents" />
      <section className="dashboard-content document-detail-content">
        <Link className="detail-back" href="/documents">← Mis documentos</Link>
        <header className="detail-header">
          <div className={`file-mark detail-file-mark ${document.file_type.toLowerCase()}`}>{document.file_type}</div>
          <div><p className="eyebrow">Documento de preparación</p><h1>{document.original_name}</h1><p>Cargado el {formatDate(document.created_at)}</p></div>
          <div className="detail-actions">
            {document.status !== "PROCESSED" && (
              <button className="button button-primary" type="button" disabled={isProcessing} onClick={() => void runProcessing()}>
                {isProcessing ? "Procesando…" : document.status === "ERROR" ? "Reintentar procesamiento" : "Procesar documento"}
              </button>
            )}
            <button className="danger-button" type="button" disabled={isProcessing} onClick={() => void remove()}>Eliminar documento</button>
          </div>
        </header>

        {error && <p className="form-error document-error">{error}</p>}

        <div className="detail-grid">
          <section className="detail-card metadata-card">
            <p className="eyebrow">Metadata</p>
            <dl>
              <div><dt>Tipo</dt><dd>{document.file_type}</dd></div>
              <div><dt>Tamaño</dt><dd>{formatBytes(document.file_size)}</dd></div>
              <div><dt>Estado</dt><dd><span className={`document-status status-${document.status.toLowerCase()}`}><i />{document.status === "UPLOADED" ? "Cargado" : document.status}</span></dd></div>
              <div><dt>Chunks</dt><dd>{processing.chunk_count}</dd></div>
              <div><dt>Identificador</dt><dd className="document-id">{document.id}</dd></div>
            </dl>
          </section>

          <section className="detail-card processing-card">
            <div className="section-heading"><div><p className="eyebrow">Trazabilidad</p><h2>Estado de procesamiento</h2></div><span className="phase-tag light">CU09</span></div>
            <ol className="processing-timeline">
              {processing.history.map((step) => (
                <li key={step.id} className={step.status === "ERROR" ? "failed" : "complete"}>
                  <b>{step.status === "ERROR" ? "!" : "✓"}</b>
                  <div><strong>{STAGE_NAMES[step.stage] ?? step.stage}</strong><span>{formatDate(step.started_at)}</span>{step.error_message && <p>{step.error_message}</p>}</div>
                </li>
              ))}
              {document.status !== "PROCESSED" && (
                <li className="pending"><b>→</b><div><strong>Extracción y vectorización</strong><span>{isProcessing ? "Gemini y Pinecone están trabajando…" : "Inicia el procesamiento para preparar este documento"}</span></div></li>
              )}
            </ol>
          </section>
        </div>

        <section className="next-stage-card"><span>RAG</span><div><p className="eyebrow">Siguiente capacidad</p><h2>Este documento alimentará tu banco de preguntas.</h2><p>{document.status === "PROCESSED" ? `Ya hay ${processing.chunk_count} chunks indexados y listos para retrieval.` : "Primero procesa el documento para dejar sus chunks disponibles en Pinecone."}</p></div></section>
      </section>
    </main>
  );
}
