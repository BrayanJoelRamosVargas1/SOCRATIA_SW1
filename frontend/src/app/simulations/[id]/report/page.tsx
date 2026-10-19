"use client";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";
import {useEffect, useState} from "react";
import Link from "next/link";
import {useParams} from "next/navigation";
import {ArrowLeft, Download, ArrowUpRight, CheckCircle2, CircleAlert, FileText} from "lucide-react";
import {getSimulationReport, getEvaluation, evaluateSimulation, getSimulation} from "@/features/simulations/api";
import {ApiError} from "@/lib/api";
import type {SimulationReportResponse} from "@/types/report";
const scoreLabel = (score: number | null) => score === null ? "Sin puntuación" : score >= 85 ? "Una base sólida" : score >= 65 ? "Sigue fortaleciendo tu defensa" : "Una oportunidad para mejorar";
export default function ReportPage() {
  const {id} = useParams<{id:string}>();
  const [report,setReport] = useState<SimulationReportResponse | null>(null);
  const [error,setError] = useState("");
  const [loading,setLoading] = useState(true);
  const [attempt,setAttempt] = useState(0);
  useEffect(() => {
    let active = true, timer: ReturnType<typeof setTimeout> | undefined, polls = 0;
    async function load() {
      try {
        const data = await getSimulationReport(id);
        if (active) {setReport(data); setError(""); setLoading(false);}
      } catch (err) {
        if (!active) return;
        if (err instanceof ApiError && [400,404,409].includes(err.status)) {
          try {
            const simulation = await getSimulation(id);
            if (simulation.status !== "COMPLETED") throw new Error("Finaliza esta simulación antes de consultar su reporte.");
            const evaluation = await getEvaluation(id);
            if (evaluation.status === "FAILED") throw new Error("La evaluación falló. Vuelve a la sesión para revisar su estado.");
          } catch (statusError) {
            if (!(statusError instanceof ApiError && statusError.status === 404)) {if (active) {setError(statusError instanceof Error ? statusError.message : "No se pudo consultar la evaluación."); setLoading(false);} return;}
          }
          if (!active) return;
          if (polls === 0) {
            try {await evaluateSimulation(id);} catch (evaluationError) {
              if (!(evaluationError instanceof ApiError && evaluationError.status === 409)) {if (active) {setError(evaluationError instanceof Error ? evaluationError.message : "No se pudo iniciar la evaluación."); setLoading(false);} return;}
            }
          }
          if (++polls >= 30) {setError("La evaluación está tardando más de lo habitual. Puedes volver a consultar en unos momentos."); setLoading(false); return;}
          timer = setTimeout(() => void load(),2000);
        } else {setError(err instanceof Error ? err.message : "No pudimos cargar tu evaluación."); setLoading(false);}
      }
    }
    void load();
    return () => {active = false; if (timer) clearTimeout(timer);};
  },[id,attempt]);
  const retry = async () => {
    setError(""); setLoading(true);
    try {await evaluateSimulation(id); setAttempt(value => value+1);}
    catch(err) {
      if (err instanceof ApiError && err.status === 409) setAttempt(value => value+1);
      else {setError(err instanceof Error ? err.message : "No se pudo reintentar la evaluación."); setLoading(false);}
    }
  };
  useEffect(() => {
    const closed: HTMLDetailsElement[] = [];
    const beforePrint = () => {document.querySelectorAll<HTMLDetailsElement>(".report-answers details:not([open])").forEach(item => {closed.push(item); item.open = true;});};
    const afterPrint = () => {closed.splice(0).forEach(item => {item.open = false;});};
    window.addEventListener("beforeprint",beforePrint); window.addEventListener("afterprint",afterPrint);
    return () => {window.removeEventListener("beforeprint",beforePrint); window.removeEventListener("afterprint",afterPrint);};
  },[]);
  const strengths = [...new Set(report?.questions.flatMap(question => question.strengths) ?? [])].slice(0,5);
  const improvements = [...new Set(report?.questions.flatMap(question => [...question.weaknesses,...question.missing_points]) ?? [])].slice(0,5);
  return <main className="report-page"><nav className="report-nav"><Link href="/history"><ArrowLeft size={16}/> Mis resultados</Link>{report && <button className="button button-ghost" onClick={() => window.print()}><Download size={16}/> Imprimir / guardar PDF</button>}</nav>
    {loading ? <section className="report-loading"><LoadingSkeleton label="Preparando tu retroalimentación…" rows={3}/></section> : error ? <section className="report-loading" role="alert"><CircleAlert size={30}/><h1>No pudimos abrir el reporte</h1><p>{error}</p><button className="button button-primary" onClick={() => void retry()}>Volver a consultar</button></section> : report && <>
      <header className="report-heading"><p className="eyebrow">TU PRÁCTICA, EN PERSPECTIVA</p><h1>{scoreLabel(report.overall_score)}</h1><p>{report.document_title}</p><div><span>{new Intl.DateTimeFormat("es-BO",{dateStyle:"medium",timeStyle:"short"}).format(new Date(report.date))}</span><span>{report.duration_minutes === null ? "Duración no disponible" : `${report.duration_minutes.toFixed(1)} minutos`}</span><span>{report.questions.length} {report.questions.length === 1 ? "pregunta" : "preguntas"}</span></div></header>
      <div className="report-score-grid">{[{label:"Resultado general",score:report.overall_score,available:report.overall_score !== null},{label:"Contenido",score:report.content_score,available:report.availability.content},{label:"Comunicación",score:report.communication_score,available:report.availability.communication},{label:"Lenguaje corporal",score:report.nonverbal_score,available:report.availability.nonverbal}].map(metric => <article className="report-score" key={metric.label}><span>{metric.label}</span><strong>{metric.available && metric.score !== null ? metric.score.toFixed(1) : "—"}<small>{metric.available && metric.score !== null ? "/100" : ""}</small></strong><p>{metric.available && metric.score !== null ? "Evaluación de esta sesión" : "Sin evidencia suficiente"}</p></article>)}</div>
      <p className="report-evidence-note">Esta retroalimentación sirve para practicar; no es una calificación oficial de tu universidad. Las dimensiones sin evidencia no se completan con estimaciones locales.</p>
      <section className="report-feedback-grid"><article><CheckCircle2 size={22}/><h2>Lo que hiciste bien</h2>{strengths.length ? <ul>{strengths.map(item => <li key={item}>{item}</li>)}</ul> : <p>No se registraron fortalezas específicas.</p>}</article><article><ArrowUpRight size={22}/><h2>Tu próxima mejora</h2>{improvements.length ? <ul>{improvements.map(item => <li key={item}>{item}</li>)}</ul> : <p>Revisa el detalle de tus respuestas para preparar tu siguiente práctica.</p>}</article></section>
      <section className="report-answers"><div className="report-section-heading"><div><p className="eyebrow">EVIDENCIA DE TU DEFENSA</p><h2>Pregunta por pregunta</h2></div><FileText size={22}/></div>{report.questions.map((question,index) => <details key={index} open={index === 0}><summary><span>{String(index+1).padStart(2,"0")}</span><strong>{question.question}</strong><small>{question.turn_score === null ? "Sin nota" : `${question.turn_score.toFixed(1)}/100`}</small></summary><div className="report-answer-detail"><h3>Tu respuesta</h3><p>{question.answer || "Sin respuesta registrada."}</p>{[{label:"Fortalezas",items:question.strengths},{label:"Por reforzar",items:question.weaknesses},{label:"Puntos pendientes",items:question.missing_points},{label:"Contradicciones",items:question.contradictions},{label:"Evidencia",items:question.evidence}].filter(group => group.items.length).map(group => <div key={group.label}><h3>{group.label}</h3><ul>{group.items.map((item,itemIndex) => <li key={itemIndex}>{item}</li>)}</ul></div>)}</div></details>)}</section><footer className="report-next-step"><div><h2>Lleva esta mejora a tu próxima defensa.</h2><p>Revisa tus argumentos, vuelve a practicar y compara tus resultados.</p></div><Link href="/simulations/new" className="button button-primary">Nueva práctica <ArrowUpRight size={16}/></Link></footer>
    </>}
  </main>;
}
