"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";
import { API_URL } from "@/lib/config";
import { getCurrentUser } from "@/features/auth/api";
import {
  deleteDocument,
  getDocument,
  getDocumentStatus,
  getPresentationMaterial,
  getQuestionBank,
} from "@/features/documents/api";
import { listPreparationTasks, submitPreparationTask, taskIsActive, type PreparationTask } from "./preparation-tasks";
import { ApiError } from "@/lib/api";
import { documentStatusLabels } from "@/types/document";
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

export function DocumentDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [user, setUser] = useState<User | null>(null);
  const [document, setDocument] = useState<Document | null>(null);
  const [processing, setProcessing] = useState<ProcessingStatus | null>(null);
  const [questionBank, setQuestionBank] = useState<QuestionBank | null>(null);
  const [presentation, setPresentation] = useState<PresentationMaterial | null>(null);
  const [durationMinutes, setDurationMinutes] = useState(15);
  const [tasks,setTasks]=useState<PreparationTask[]>([]);
  const [submitting,setSubmitting]=useState(false);
  const [taskNotice,setTaskNotice]=useState("");
  const handledTasks=useRef(new Set<string>());
  const activeTask=tasks.find(taskIsActive);
  const activeTaskId=activeTask?.id;
  const busy=submitting || Boolean(activeTask);
  const isProcessing=busy && (activeTask?.kind==="process" || document?.status!=="PROCESSED");
  const isGenerating=busy && activeTask?.kind==="questions";
  const isGeneratingPresentation=busy && activeTask?.kind==="presentation";
  const [error, setError] = useState("");

  useEffect(() => {
    let disposed=false;
    void listPreparationTasks(params.id).then(value=>{
      if(disposed)return;
      setTasks(value);
      if(value[0] && ["FAILED","INTERRUPTED"].includes(value[0].status))setTaskNotice("La última preparación se interrumpió. Revisa los materiales guardados antes de iniciar otra solicitud.");
    }).catch(()=>undefined);
    Promise.all([getCurrentUser(), getDocument(params.id), getDocumentStatus(params.id)])
      .then(async ([currentUser, currentDocument, currentStatus]) => {
        setUser(currentUser);
        setDocument(currentDocument);
        setProcessing(currentStatus);
        if (currentDocument.status === "PROCESSED") {
          await Promise.all([
            getQuestionBank(params.id).then(setQuestionBank).catch(caught => {
              if (!(caught instanceof ApiError && caught.status === 404)) throw caught;
            }),
            getPresentationMaterial(params.id).then(material => {
            setPresentation(material);
            setDurationMinutes(material.duration_minutes);
            }).catch(caught => {
              if (!(caught instanceof ApiError && caught.status === 404)) throw caught;
            }),
          ]);
        }
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 404) {
          setError("El documento no existe o no pertenece a tu cuenta.");
        } else if (caught instanceof ApiError && caught.status === 401) {
          router.replace("/login");
        } else setError("No pudimos completar la consulta. Revisa tu conexión e inténtalo de nuevo.");
      });
    return ()=>{disposed=true;};
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

  useEffect(()=>{
    if(!activeTaskId)return;
    let stopped=false;
    let timer:ReturnType<typeof setTimeout>;
    async function poll(){
      try {
        const rows=await listPreparationTasks(params.id);
        if(stopped)return;
        const finished=rows.find(row=>row.id===activeTaskId && !taskIsActive(row));
        if(finished && !handledTasks.current.has(finished.id)){
          const [doc,status]=await Promise.all([getDocument(params.id),getDocumentStatus(params.id)]);
          if(stopped)return;
          setDocument(doc);setProcessing(status);
          if(finished.status==="SUCCEEDED"){
            setTaskNotice("Preparación completada. El resultado quedó guardado.");
            if(finished.kind==="questions")setQuestionBank(await getQuestionBank(params.id));
            if(finished.kind==="presentation")setPresentation(await getPresentationMaterial(params.id));
          } else setTaskNotice(finished.status==="INTERRUPTED"
            ? "El servidor se reinició durante la preparación. Revisa los materiales antes de reintentar: no repetimos llamadas automáticamente."
            : "La preparación no terminó. Puede deberse a cuota o disponibilidad del proveedor. Revisa tu conexión y los materiales antes de reintentar.");
          handledTasks.current.add(finished.id);
          if(!stopped)setTasks(rows);
        } else if(!finished && !stopped){setTasks(rows);timer=setTimeout(()=>void poll(),2000);}
      } catch {
        if(!stopped){setTaskNotice("Se perdió la conexión. La tarea sigue guardada; volveremos a consultar su estado.");timer=setTimeout(()=>void poll(),5000);}
      }
    }
    timer=setTimeout(()=>void poll(),1000);
    return ()=>{stopped=true;clearTimeout(timer);};
  },[activeTaskId,params.id]);

  async function enqueue(kind:PreparationTask["kind"],regenerate=false){
    if(!document || busy)return;
    setError("");setSubmitting(true);
    try {
      const task=await submitPreparationTask(document.id,kind,durationMinutes,regenerate);
      setTasks(current=>[task,...current.filter(row=>row.id!==task.id)]);
      setTaskNotice("Solicitud guardada. Puedes salir de esta página y volver para consultar el resultado.");
    } catch(caught){
      setError(caught instanceof ApiError?caught.message:"No pudimos confirmar la solicitud. Consultaremos si quedó guardada.");
      try{setTasks(await listPreparationTasks(document.id));}catch{/* Never resubmit an uncertain request automatically. */}
    } finally {setSubmitting(false);}
  }
  async function runProcessing(){await enqueue("process");}
  async function runQuestionGeneration(){
    if(questionBank && !window.confirm("Esto reemplazará el banco de preguntas actual. ¿Quieres regenerarlo?"))return;
    await enqueue("questions",Boolean(questionBank));
  }
  async function runPresentationGeneration(){
    if(presentation && !window.confirm("Esto reemplazará el material de exposición actual. ¿Quieres continuar?"))return;
    await enqueue("presentation",Boolean(presentation));
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
  return (
    <main className="dashboard-layout">
      <AppSidebar user={user} active="documents" />
      <section className="dashboard-content document-detail-content">
        {!user || !document || !processing ? (
          <LoadingSkeleton label="Abriendo tu documento y materiales…" rows={2}/>
        ) : (
          <>
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
                disabled={busy}
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
              disabled={busy}
              onClick={() => void remove()}
            >
              Eliminar documento
            </button>
          </div>
        </header>

        {error && <p className="form-error document-error">{error}</p>}
        {(activeTask || taskNotice) && <section className="workspace-notice" role="status" aria-live="polite"><div><strong>{activeTask?.status==="QUEUED"?"En cola":activeTask?"Preparación en curso":"Estado de preparación"}</strong><p>{taskNotice || "La preparación continúa en el servidor. Puedes volver a esta página más tarde."}</p></div></section>}

        <div className="detail-grid">
          <section className="detail-card metadata-card">
            <p className="eyebrow">Información del documento</p>
            <dl>
              <div><dt>Tipo</dt><dd>{document.file_type}</dd></div>
              <div><dt>Tamaño</dt><dd>{formatBytes(document.file_size)}</dd></div>
              <div><dt>Estado</dt><dd><span className={`document-status status-${document.status.toLowerCase()}`}><i />{documentStatusLabels[document.status]}</span></dd></div>
              <div><dt>Fragmentos preparados</dt><dd>{processing.chunk_count}</dd></div>
              <div><dt>Identificador</dt><dd className="document-id">{document.id}</dd></div>
            </dl>
          </section>

          <section className="detail-card processing-card">
            <div className="section-heading"><div><p className="eyebrow">Trazabilidad</p><h2>Estado de procesamiento</h2></div><span className="phase-tag light">Procesamiento</span></div>
            <ol className="processing-timeline">
              {processing.history.map((step) => (
                <li key={step.id} className={step.status === "ERROR" ? "failed" : "complete"}>
                  <b>{step.status === "ERROR" ? "!" : "✓"}</b>
                  <div><strong>{STAGE_NAMES[step.stage] ?? step.stage}</strong><span>{formatDate(step.started_at)}</span>{step.error_message && <p>{step.error_message}</p>}</div>
                </li>
              ))}
              {document.status !== "PROCESSED" && (
                <li className="pending"><b>→</b><div><strong>Extracción y vectorización</strong><span>{isProcessing ? "Preparación en el servidor; el estado se guarda automáticamente…" : "Inicia el procesamiento para preparar este documento"}</span></div></li>
              )}
            </ol>
          </section>
        </div>

        {document.status !== "PROCESSED" ? (
          <section className="next-stage-card">
            <span>01</span>
            <div><p className="eyebrow">Siguiente capacidad</p><h2>Este documento alimentará tu banco de preguntas.</h2><p>Procesa el documento para preparar preguntas basadas en su contenido.</p></div>
          </section>
        ) : (
          <>
          <section className="question-bank-workspace">
            <header className="question-bank-header">
              <div>
                <p className="eyebrow">PREGUNTAS DE TU INVESTIGACIÓN</p>
                <h2>{questionBank ? "Banco de preguntas" : "Documento listo para el tribunal"}</h2>
                <p>{questionBank ? "Doce preguntas sustentadas exclusivamente en los fragmentos de este documento." : `${processing.chunk_count} fragmentos preparados para generar preguntas sobre tu investigación.`}</p>
              </div>
              <button className="button button-primary" type="button" disabled={busy} onClick={() => void runQuestionGeneration()}>
                {isGenerating ? "Generando…" : questionBank ? "Regenerar preguntas" : "Generar banco de preguntas"}
              </button>
            </header>

            {isGenerating && (
              <div className="question-analysis" aria-live="polite">
                <LoadingSkeleton label="Generando preguntas basadas en tu documento…" rows={1}/>
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
                <p className="eyebrow">PREPARA TU EXPOSICIÓN</p>
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
                <LoadingSkeleton label="Preparando el contenido, guion y tiempos de tu exposición…" rows={1}/>
              </div>
            )}

            {presentation && !isGeneratingPresentation && (
              <>
                <p><a className="button button-primary" href={`${API_URL}/documents/${document.id}/presentation/export`} download>Descargar PowerPoint</a></p>
                <p>Diapositivas editables y notas del expositor. Las imágenes extraíbles del PDF aparecen como anexo con su página de origen.</p>
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
        </>
        )}
      </section>
    </main>
  );
}
