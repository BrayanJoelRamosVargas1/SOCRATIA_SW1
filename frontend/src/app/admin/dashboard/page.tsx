"use client";
import {useCallback,useEffect,useState} from "react";
import Link from "next/link";
import {Users,Files,Mic,ChartNoAxesCombined,RefreshCw,ArrowUpRight,TriangleAlert,ShieldCheck,SlidersHorizontal,Layers,Scale} from "lucide-react";
import {apiRequest} from "@/lib/api";
type Metrics = {total_users:number; documents_by_status:Record<string,number>; simulations_by_status:Record<string,number>; evaluations_by_status:Record<string,number>; average_overall_score:number|null; integration_metrics:unknown};
const labels:Record<string,string> = {UPLOADED:"Cargados",QUEUED:"En cola",EXTRACTING:"Extrayendo",CHUNKING:"Preparando contenido",EMBEDDING:"Analizando",RETRYING:"Reintentando",SWITCHING_PROVIDER:"Cambiando servicio",INDEXING:"Indexando",DEGRADED:"Requieren revisión",PROCESSING:"Procesando",PROCESSED:"Procesados",ERROR:"Con error",FAILED:"Fallidas",DRAFT:"Borradores",READY:"Listas",ACTIVE:"Activas",COMPLETED:"Completadas",ABORTED:"Interrumpidas",PENDING:"Pendientes"};
const total = (values:Record<string,number>) => Object.values(values).reduce((a,b) => a+b,0);
const percent = (value:number,denominator:number) => denominator ? `${Math.round(value/denominator*100)}%` : "—";
export default function AdminDashboardPage() {
  const [metrics,setMetrics] = useState<Metrics|null>(null);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState("");
  const [updated,setUpdated] = useState<Date|null>(null);
  const load = useCallback(async () => {
    try {const data = await apiRequest<Metrics>("/admin/dashboard"); setMetrics(data); setError(""); setUpdated(new Date());}
    catch(err) {setError(err instanceof Error ? err.message : "No se pudo cargar el panel.");}
    finally {setLoading(false);}
  },[]);
  useEffect(() => {
    // Initial remote fetch reuses the manual refresh loader.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  },[load]);
  const docs = metrics?.documents_by_status ?? {}, sims = metrics?.simulations_by_status ?? {}, evaluations = metrics?.evaluations_by_status ?? {};
  const allDocs = total(docs), allSims = total(sims), allEvals = total(evaluations);
  const failed = (docs.ERROR ?? 0)+(docs.FAILED ?? 0)+(sims.ERROR ?? 0)+(evaluations.FAILED ?? 0);
  const pending = ["PROCESSING","QUEUED","EXTRACTING","CHUNKING","EMBEDDING","RETRYING","SWITCHING_PROVIDER","INDEXING"].reduce((sum,status) => sum+(docs[status] ?? 0),0)+(evaluations.PENDING ?? 0)+(evaluations.PROCESSING ?? 0);
  const cards = [
    {label:"Usuarios registrados",value:metrics?.total_users,detail:"Cuentas de la plataforma",icon:Users,href:"/admin/users"},
    {label:"Documentos",value:metrics ? allDocs : undefined,detail:`${docs.PROCESSED ?? 0} procesados`,icon:Files,href:"/admin/ai-settings"},
    {label:"Simulaciones",value:metrics ? allSims : undefined,detail:`${sims.ACTIVE ?? 0} en curso`,icon:Mic,href:"/admin/jury-profiles"},
    {label:"Evaluaciones",value:metrics ? allEvals : undefined,detail:`${evaluations.COMPLETED ?? 0} completadas`,icon:ChartNoAxesCombined,href:"/admin/dashboard"},
  ];
  return <div className="admin-overview"><header className="admin-page-heading"><div><p className="eyebrow">VISIÓN GENERAL</p><h1>El pulso de Socratia.</h1><p>Usuarios, actividad y procesos que necesitan tu atención.</p></div><div className="admin-update"><small>{updated ? `Consultado a las ${updated.toLocaleTimeString("es-BO",{hour:"2-digit",minute:"2-digit"})}` : "Datos del sistema"}</small><button className="button button-ghost" disabled={loading} onClick={() => {setLoading(true); void load();}}><RefreshCw size={16} className={loading ? "spin-icon" : ""}/>{loading ? "Consultando…" : "Actualizar"}</button></div></header>
    {error && <div className="workspace-notice" role="alert">{error}{metrics && " Se muestran los datos de la última consulta correcta."}</div>}
    <div className="admin-kpi-grid">{cards.map(({icon:Icon,...card}) => <article className="admin-kpi" key={card.label}><div><span>{card.label}</span><Icon size={20}/></div><strong>{card.value ?? "—"}</strong><small>{metrics ? card.detail : "Esperando datos"}</small></article>)}</div>
    <div className="admin-summary-grid"><section className="admin-health-card"><div className="admin-card-heading"><span className="admin-section-icon"><TriangleAlert size={20}/></span><h2>Centro de atención</h2></div>{metrics ? <><div className="admin-attention-counts"><div><strong>{failed}</strong><span>procesos con error</span></div><div><strong>{pending}</strong><span>procesos pendientes o en curso</span></div></div><p>{failed ? "Revisa la configuración de IA y los estados de procesamiento. El conteo agrupa documentos, simulaciones y evaluaciones." : "No hay estados de error registrados en la consulta actual."}</p><Link className="admin-inline-link" href="/admin/ai-settings">Revisar configuración <ArrowUpRight size={15}/></Link></> : <p>La información aparecerá al completar la consulta.</p>}</section>
      <section className="admin-quality-card"><div className="admin-card-heading"><span className="admin-section-icon"><ChartNoAxesCombined size={20}/></span><h2>Resultados y conversión</h2></div><dl><div><dt>Simulaciones completadas</dt><dd>{metrics ? percent(sims.COMPLETED ?? 0,allSims) : "—"}</dd></div><div><dt>Documentos procesados</dt><dd>{metrics ? percent(docs.PROCESSED ?? 0,allDocs) : "—"}</dd></div><div><dt>Promedio de evaluaciones</dt><dd>{metrics?.average_overall_score == null ? "—" : `${metrics.average_overall_score.toFixed(1)} / 100`}</dd></div></dl><p>Acumulados de toda la plataforma. Sin datos suficientes, la métrica aparece como “—”.</p></section></div>
    <section className="admin-distribution"><div className="admin-section-title"><div><p className="eyebrow">OPERACIÓN</p><h2>De documento a defensa</h2></div><span>Distribución acumulada por estado</span></div><div className="admin-pipeline-grid">{[{title:"Documentos",values:docs,total:allDocs,icon:Files},{title:"Simulaciones",values:sims,total:allSims,icon:Mic},{title:"Evaluaciones",values:evaluations,total:allEvals,icon:ChartNoAxesCombined}].map(({icon:Icon,...group}) => <article key={group.title}><header><Icon size={18}/><h3>{group.title}</h3><span>{metrics ? group.total : "—"}</span></header>{Object.entries(group.values).length ? Object.entries(group.values).map(([status,count]) => <div className="admin-status-row" key={status}><div><span>{labels[status] ?? status}</span><strong>{count}</strong></div><div className="admin-status-track"><i className={["FAILED","ERROR","ABORTED"].includes(status) ? "status-failure" : ""} style={{width:`${group.total ? count/group.total*100 : 0}%`}}/></div></div>) : <p className="admin-empty">{metrics ? "Sin actividad registrada" : "Consultando actividad…"}</p>}</article>)}</div></section>
    <section className="admin-bottom-grid"><article className="admin-integrations"><ShieldCheck size={22}/><h2>Integraciones externas</h2><p>La API aún no publica disponibilidad ni latencia verificadas por proveedor. Este panel no declara servicios conectados a partir de su configuración.</p><Link href="/admin/ai-settings" className="admin-inline-link">Ver configuración <ArrowUpRight size={15}/></Link></article><article className="admin-quick-links"><h2>Herramientas de gestión</h2>{[{href:"/admin/users",label:"Usuarios y permisos",icon:Users},{href:"/admin/plans",label:"Catálogo de planes",icon:Layers},{href:"/admin/jury-profiles",label:"Perfiles de jurado",icon:Scale},{href:"/admin/ai-settings",label:"Parámetros de IA",icon:SlidersHorizontal}].map(({icon:Icon,...link}) => <Link href={link.href} key={link.href}><Icon size={16}/>{link.label}<ArrowUpRight size={15}/></Link>)}</article></section>
  </div>;
}
