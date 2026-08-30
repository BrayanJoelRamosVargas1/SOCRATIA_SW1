"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { getCurrentUser } from "@/features/auth/api";
import {
  deleteDocument,
  generatePresentationMaterial,
  generateQuestionBank,
  getDocument,
  getDocumentStatus,
  getPresentationMaterial,
  getQuestionBank,
  processDocument,
  regeneratePresentationMaterial,
} from "@/features/documents/api";
import { ApiError } from "@/lib/api";
import type {
  Document,
  ProcessingStatus,
  PresentationMaterial,
  QuestionBank,
  QuestionCategory,
} from "@/types/document";
import type { User } from "@/types/user";

function formatBytes(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1048576).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-BO", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

const STAGE_NAMES: Record<string, string> = {
  UPLOAD: "Documento recibido",
  EXTRACTION: "Texto extraído",
  CHUNKING: "Contenido fragmentado",
  EMBEDDING: "Embeddings generados",
  VECTOR_STORE: "Vectores indexados",
  COMPLETE: "Documento listo",
};

const CATEGORY_ORDER: QuestionCategory[] = [
  "CONCEPTUAL",
  "METHODOLOGICAL",
  "TECHNICAL",
  "CRITICAL",
];

const CATEGORY_LABELS: Record<QuestionCategory, string> = {
  CONCEPTUAL: "Conceptuales",
  METHODOLOGICAL: "Metodológicas",
  TECHNICAL: "Técnicas",
  CRITICAL: "Críticas",
};

const ANALYSIS_MESSAGES = [
  "Recuperando objetivos y metodología",
  "Analizando arquitectura y decisiones técnicas",
  "Contrastando resultados y evidencia",
  "Detectando limitaciones, riesgos y supuestos",
  "Construyendo preguntas de tribunal",
];

export function DocumentDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [user, setUser] = useState<User | null>(null);
  const [document, setDocument] = useState<Document | null>(null);
  const [processing, setProcessing] = useState<ProcessingStatus | null>(null);
  const [questionBank, setQuestionBank] = useState<QuestionBank | null>(null);
  const [presentation, setPresentation] = useState<PresentationMaterial | null>(null);
  const [durationMinutes, setDurationMinutes] = useState(15);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGeneratingPresentation, setIsGeneratingPresentation] = useState(false);
  const [analysisMessage, setAnalysisMessage] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getCurrentUser(), getDocument(params.id), getDocumentStatus(params.id)])
      .then(async ([currentUser, currentDocument, currentStatus]) => {
        setUser(currentUser);
        setDocument(currentDocument);
        setProcessing(currentStatus);
        if (currentDocument.status === "PROCESSED") {
          try {
            setQuestionBank(await getQuestionBank(params.id));
          } catch (caught) {
            if (!(caught instanceof ApiError && caught.status === 404)) throw caught;
          }
          try {
            const material = await getPresentationMaterial(params.id);
            setPresentation(material);
            setDurationMinutes(material.duration_minutes);
          } catch (caught) {
            if (!(caught instanceof ApiError && caught.status === 404)) throw caught;
          }
        }
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 404) {
          setError("El documento no existe o no pertenece a tu cuenta.");
        } else {
          router.replace("/login");
        }
      });
  }, [params.id, router]);

  useEffect(() => {
    if (!isGenerating) return;
    const interval = window.setInterval(() => {
      setAnalysisMessage((current) => (current + 1) % ANALYSIS_MESSAGES.length);
    }, 1800);
    return () => window.clearInterval(interval);
  }, [isGenerating]);

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
    setDocument((current) => (current ? { ...current, status: "PROCESSING" } : current));
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

  async function runQuestionGeneration() {
    if (!document || isGenerating) return;
    if (
      questionBank &&
      !window.confirm("Esto reemplazará el banco de preguntas actual. ¿Quieres regenerarlo?")
    ) {
      return;
    }
    setError("");
    setAnalysisMessage(0);
    setIsGenerating(true);
    try {
      setQuestionBank(await generateQuestionBank(document.id));
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No pudimos generar el banco de preguntas.",
      );
    } finally {
      setIsGenerating(false);
    }
  }

  async function runPresentationGeneration() {
    if (!document || isGeneratingPresentation) return;
    if (
      presentation &&
      !window.confirm("Esto reemplazará el material de exposición actual. ¿Quieres continuar?")
    ) return;
    setError("");
    setIsGeneratingPresentation(true);
    try {
      const action = presentation
        ? regeneratePresentationMaterial
        : generatePresentationMaterial;
      setPresentation(await action(document.id, durationMinutes));
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No pudimos generar el material de exposición.",
      );
    } finally {
      setIsGeneratingPresentation(false);
    }
  }

  if (error && !user) {
    return (
      <main className="loading-screen detail-error">
        <h1>Documento no disponible</h1>
        <p>{error}</p>
        <Link className="button button-primary" href="/documents">
          Volver a mis documentos
        </Link>
      </main>
    );
  }
  if (!user || !document || !processing) {
    return (
      <main className="loading-screen">
        <div className="loading-orbit" />
        <p>Abriendo documento…</p>
      </main>
    );
  }

  return (
    <main className="dashboard-layout">
      <AppSidebar user={user} active="documents" />
      <section className="dashboard-content document-detail-content">
        <Link className="detail-back" href="/documents">← Mis documentos</Link>
        <header className="detail-header">
          <div className={`file-mark detail-file-mark ${document.file_type.toLowerCase()}`}>
            {document.file_type}
          </div>
          <div>
            <p className="eyebrow">Documento de preparación</p>
            <h1>{document.original_name}</h1>
            <p>Cargado el {formatDate(document.created_at)}</p>
          </div>
          <div className="detail-actions">
            {document.status !== "PROCESSED" && (
              <button
                className="button button-primary"
                type="button"
                disabled={isProcessing}
                onClick={() => void runProcessing()}
              >
                {isProcessing
                  ? "Procesando…"
                  : document.status === "ERROR"
                    ? "Reintentar procesamiento"
                    : "Procesar documento"}
              </button>
            )}
            <button
              className="danger-button"
              type="button"
              disabled={isProcessing || isGenerating}
              onClick={() => void remove()}
            >
              Eliminar documento
            </button>
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

        {document.status !== "PROCESSED" ? (
          <section className="next-stage-card">
            <span>RAG</span>
            <div><p className="eyebrow">Siguiente capacidad</p><h2>Este documento alimentará tu banco de preguntas.</h2><p>Primero procésalo para dejar sus chunks disponibles en Pinecone.</p></div>
          </section>
        ) : (
          <>
          <section className="question-bank-workspace">
            <header className="question-bank-header">
              <div>
                <p className="eyebrow">CU10 · RAG documental</p>
                <h2>{questionBank ? "Banco de preguntas" : "Documento listo para el tribunal"}</h2>
                <p>{questionBank ? "Doce preguntas sustentadas exclusivamente en los fragmentos de este documento." : `${processing.chunk_count} chunks están indexados y listos para recuperar evidencia.`}</p>
              </div>
              <button className="button button-primary" type="button" disabled={isGenerating} onClick={() => void runQuestionGeneration()}>
                {isGenerating ? "Generando…" : questionBank ? "Regenerar preguntas" : "Generar banco de preguntas"}
              </button>
            </header>

            {isGenerating && (
              <div className="question-analysis" aria-live="polite">
                <div className="loading-orbit" />
                <div><strong>Generando preguntas críticas…</strong><span>{ANALYSIS_MESSAGES[analysisMessage]}</span></div>
              </div>
            )}

            {questionBank && !isGenerating && (
              <>
                <div className="question-bank-meta">
                  <span><b>12</b> preguntas</span>
                  <span><b>{questionBank.provider_used}</b> proveedor</span>
                  <span><b>{questionBank.fallback_used ? "Sí" : "No"}</b> fallback</span>
                  {questionBank.latency_ms !== null && <span><b>{(questionBank.latency_ms / 1000).toFixed(1)} s</b> generación</span>}
                </div>
                <div className="question-category-grid">
                  {CATEGORY_ORDER.map((category) => {
                    const questions = questionBank.questions.filter((question) => question.category === category);
                    return (
                      <section className={`question-category category-${category.toLowerCase()}`} key={category}>
                        <div className="question-category-heading"><h3>{CATEGORY_LABELS[category]}</h3><span>{questions.length}</span></div>
                        <ol>
                          {questions.map((question) => (
                            <li key={question.id}>
                              <p>{question.question}</p>
                              <div>
                                <span className={`difficulty difficulty-${question.difficulty.toLowerCase()}`}>{question.difficulty === "HARD" ? "Difícil" : "Media"}</span>
                                <small>Sustentada en evidencia del documento</small>
                              </div>
                            </li>
                          ))}
                        </ol>
                      </section>
                    );
                  })}
                </div>
              </>
            )}
          </section>
          <section className="presentation-workspace">
            <header className="question-bank-header presentation-header">
              <div>
                <p className="eyebrow">CU11 · Preparación de exposición</p>
                <h2>{presentation ? presentation.title : "Convierte tu documento en una defensa"}</h2>
                <p>Indica cuánto tiempo tienes y Socratia distribuirá la evidencia en una estructura presentable.</p>
              </div>
              <div className="presentation-controls">
                <label>
                  Tiempo disponible
                  <span><input type="number" min="5" max="30" value={durationMinutes} onChange={(event) => setDurationMinutes(Number(event.target.value))} /> minutos</span>
                </label>
                <button className="button button-primary" type="button" disabled={isGeneratingPresentation || durationMinutes < 5 || durationMinutes > 30} onClick={() => void runPresentationGeneration()}>
                  {isGeneratingPresentation ? "Preparando…" : presentation ? "Regenerar estructura" : "Generar estructura"}
                </button>
              </div>
            </header>

            {isGeneratingPresentation && (
              <div className="question-analysis" aria-live="polite">
                <div className="loading-orbit" />
                <div><strong>Diseñando tu exposición…</strong><span>Distribuyendo evidencia, guion y tiempos</span></div>
              </div>
            )}

            {presentation && !isGeneratingPresentation && (
              <>
                <div className="question-bank-meta presentation-meta">
                  <span><b>{presentation.duration_minutes} min</b> exposición</span>
                  <span><b>{presentation.slides.length}</b> diapositivas</span>
                  <span><b>~{presentation.target_word_count}</b> palabras objetivo</span>
                  <span><b>{presentation.provider_used}</b> {presentation.fallback_used ? "fallback" : "primario"}</span>
                </div>
                <div className="slide-list">
                  {presentation.slides.map((slide) => (
                    <details key={slide.id} className="slide-card">
                      <summary><b>{String(slide.position).padStart(2, "0")}</b><span>{slide.title}</span><time>{formatDuration(slide.estimated_seconds)}</time></summary>
                      <div className="slide-content">
                        <p className="slide-objective"><strong>Objetivo:</strong> {slide.objective}</p>
                        <ul>{slide.bullet_points.map((bullet) => <li key={bullet}>{bullet}</li>)}</ul>
                        <div className="speaker-notes"><strong>Qué explicar</strong><p>{slide.speaker_notes}</p></div>
                      </div>
                    </details>
                  ))}
                </div>
              </>
            )}
          </section>
          </>
        )}
      </section>
    </main>
  );
}
