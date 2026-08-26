"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ChartIcon, DocumentIcon, MicIcon } from "@/components/ui/icons";
import { Logo } from "@/components/ui/logo";
import { getCurrentUser } from "@/features/auth/api";
import { LogoutButton } from "@/features/auth/logout-button";
import type { User } from "@/types/user";

export function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => router.replace("/login"));
  }, [router]);

  if (!user) {
    return (
      <main className="loading-screen">
        <div className="loading-orbit" />
        <p>Preparando tu espacio…</p>
      </main>
    );
  }

  const firstName = user.full_name.split(" ")[0];
  return (
    <main className="dashboard-layout">
      <aside className="dashboard-sidebar">
        <Logo />
        <nav aria-label="Navegación principal">
          <a className="nav-item active" href="/dashboard">Resumen</a>
          <span className="nav-item disabled">Documentos <small>Próximo</small></span>
          <span className="nav-item disabled">Simulaciones <small>Próximo</small></span>
          <span className="nav-item disabled">Reportes <small>Próximo</small></span>
        </nav>
        <div className="sidebar-user">
          <span className="avatar">{firstName.slice(0, 1).toUpperCase()}</span>
          <div><strong>{user.full_name}</strong><small>{user.email}</small></div>
        </div>
        <LogoutButton />
      </aside>

      <section className="dashboard-content">
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">Tu espacio de preparación</p>
            <h1>Hola, {firstName}.</h1>
            <p>Ya tienes la base lista. Tu primera práctica empieza en el siguiente sprint.</p>
          </div>
          <span className="status-pill"><i /> Sistema operativo</span>
        </header>

        <section className="dashboard-hero">
          <div>
            <span className="phase-tag">Sprint 1 completado</span>
            <h2>Tu sala de entrenamiento está lista.</h2>
            <p>La cuenta, las sesiones seguras y tu perfil ya funcionan sobre la arquitectura real de Socratia.</p>
          </div>
          <div className="score-ring"><strong>01</strong><span>incremento</span></div>
        </section>

        <div className="metric-grid">
          <article className="metric-card">
            <DocumentIcon className="metric-icon" />
            <span>Documentos</span><strong>0</strong><small>Carga disponible en Sprint 2</small>
          </article>
          <article className="metric-card">
            <MicIcon className="metric-icon" />
            <span>Simulaciones</span><strong>0</strong><small>Voz disponible en Sprint 3</small>
          </article>
          <article className="metric-card">
            <ChartIcon className="metric-icon" />
            <span>Reportes</span><strong>0</strong><small>Evaluación disponible en Sprint 4</small>
          </article>
        </div>

        <section className="roadmap-card">
          <div className="section-heading">
            <div><p className="eyebrow">Ruta del producto</p><h2>Lo que viene ahora</h2></div>
            <span>Arquitectura modular</span>
          </div>
          <ol className="roadmap">
            <li className="done"><b>1</b><div><strong>Identidad y plataforma base</strong><span>Auth, users, roles, Docker y PostgreSQL</span></div></li>
            <li><b>2</b><div><strong>Preparación inteligente</strong><span>Documentos, RAG y preguntas</span></div></li>
            <li><b>3</b><div><strong>Simulación oral</strong><span>WebSocket, STT y TTS</span></div></li>
            <li><b>4</b><div><strong>Evaluación multimodal</strong><span>MediaPipe, criterios y reportes</span></div></li>
          </ol>
        </section>
      </section>
    </main>
  );
}

