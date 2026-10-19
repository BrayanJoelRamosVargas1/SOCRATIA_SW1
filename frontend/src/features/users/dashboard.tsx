"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Files, Mic, ChartNoAxesCombined } from "lucide-react";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { getCurrentUser } from "@/features/auth/api";
import { listDocuments } from "@/features/documents/api";
import { listSimulations } from "@/features/simulations/api";
import { apiRequest, ApiError } from "@/lib/api";
import type { User } from "@/types/user";
type Counts = { documents: number | null; simulations: number | null; evaluations: number | null };
export function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [counts, setCounts] = useState<Counts>({documents: null, simulations: null, evaluations: null});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    try {
      const [profile, docs, sims, history] = await Promise.allSettled([
        getCurrentUser(),
        listDocuments(), listSimulations(),
        apiRequest<{summary: {evaluated_simulations: number}}>("/performance-history?page=1&page_size=1"),
      ]);
      if(profile.status==="rejected")throw profile.reason;
      setUser(profile.value);
      setCounts({documents: docs.status === "fulfilled" ? docs.value.length : null, simulations: sims.status === "fulfilled" ? sims.value.length : null, evaluations: history.status === "fulfilled" ? history.value.summary.evaluated_simulations : null});
      if ([docs, sims, history].some(result => result.status === "rejected")) setError("No pudimos cargar todas tus estadísticas. Puedes seguir accediendo a tus documentos y simulaciones.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) router.replace("/login");
      else setError("No pudimos conectar con tu cuenta. Intenta nuevamente.");
    } finally { setLoading(false); }
  }, [router]);
  useEffect(() => {
    // Initial remote data fetch shares the same loader as the retry action.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);
  const metrics = [
    {label: "Documentos", value: counts.documents, href: "/documents", icon: Files, detail: "Tu material de defensa"},
    {label: "Simulaciones", value: counts.simulations, href: "/simulations", icon: Mic, detail: "Cada práctica cuenta"},
    {label: "Evaluaciones", value: counts.evaluations, href: "/history", icon: ChartNoAxesCombined, detail: "Revisa tu progreso"},
  ];
  return <main className="dashboard-layout"><AppSidebar user={user} active="dashboard" /><section className="dashboard-content" aria-busy={loading}>
    <header className="dashboard-header"><div><p className="eyebrow">TU PRÓXIMA DEFENSA EMPIEZA AQUÍ</p><h1>{user ? `Hola, ${user.full_name.split(" ")[0]}.` : "Tu espacio de preparación"}</h1><p>Un paso más cerca de defender tus ideas con confianza.</p></div><Link href="/simulations/new" className="button button-primary"><Mic size={17} /> Nueva práctica</Link></header>
    {error && <div className="workspace-notice" role="alert">{error}<button type="button" disabled={loading} onClick={() => { setLoading(true); setError(""); void load(); }}>Reintentar</button></div>}
    <section className="dashboard-hero"><div><span className="phase-tag">TU TRIBUNAL VIRTUAL</span><h2>Grandes ideas. Una defensa segura.</h2><p>Prepara tu documento, ensaya las preguntas del jurado y descubre qué puedes mejorar antes del gran día.</p><div className="hero-workspace-actions"><Link href={counts.documents ? "/simulations/new" : "/documents"} className="button button-primary">{counts.documents ? "Preparar una simulación" : "Subir mi documento"}<ArrowRight size={17} /></Link><Link href="/history" className="button button-ghost">Ver mis resultados</Link></div></div></section>
    <div className="metric-grid">{metrics.map(({icon: Icon, ...metric}) => <Link href={metric.href} key={metric.label}><article className="metric-card"><Icon className="metric-icon" size={22} /><span>{metric.label}</span><strong>{metric.value ?? "—"}</strong><small>{metric.detail} →</small></article></Link>)}</div>
    <section className="roadmap-card"><div className="section-heading"><div><p className="eyebrow">PASO A PASO</p><h2>Tu ruta hacia una mejor defensa</h2></div><span>Avanza a tu ritmo</span></div><ol className="roadmap">
      <li className={counts.documents ? "done" : ""}><b>1</b><div><strong><Link href="/documents">Prepara tu documento →</Link></strong><span>Sube tu tesis en PDF o Word y prepara las preguntas de tu tema.</span></div></li>
      <li className={counts.simulations ? "done" : ""}><b>2</b><div><strong><Link href="/simulations">Ensaya con tu jurado →</Link></strong><span>Configura tu simulación y practica tus respuestas.</span></div></li>
      <li className={counts.evaluations ? "done" : ""}><b>3</b><div><strong><Link href="/history">Aprende de cada intento →</Link></strong><span>Consulta las evaluaciones y enfoca tu próxima práctica.</span></div></li>
    </ol></section>
  </section></main>;
}
