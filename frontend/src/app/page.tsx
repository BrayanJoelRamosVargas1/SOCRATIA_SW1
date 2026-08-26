import Link from "next/link";

import { ArrowIcon, ChartIcon, DocumentIcon, MicIcon, ShieldIcon } from "@/components/ui/icons";
import { Logo } from "@/components/ui/logo";

const capabilities = [
  { icon: DocumentIcon, title: "Entiende tu investigación", text: "Convierte tus documentos en una base de conocimiento lista para cuestionarte." },
  { icon: MicIcon, title: "Ensaya como si fuera real", text: "Practica frente a un jurado virtual con voz, ritmo e interrupciones naturales." },
  { icon: ChartIcon, title: "Mejora con evidencia", text: "Recibe retroalimentación sobre contenido, voz, tiempos y lenguaje corporal." },
];

export default function Home() {
  return (
    <main>
      <nav className="landing-nav">
        <Logo />
        <div className="landing-links">
          <a href="#metodo">Método</a>
          <a href="#arquitectura">Arquitectura</a>
          <Link className="button button-ghost" href="/login">Ingresar</Link>
          <Link className="button button-primary" href="/register">Crear cuenta</Link>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-glow" />
        <div className="hero-copy">
          <p className="eyebrow">Tu investigación merece una gran defensa</p>
          <h1>No memorices tu defensa. <em>Entrénala.</em></h1>
          <p className="hero-lead">Socratia convierte tu trabajo académico en una experiencia de práctica exigente, medible y diseñada para darte confianza.</p>
          <div className="hero-actions">
            <Link className="button button-primary button-large" href="/register">Empezar a practicar <ArrowIcon /></Link>
            <a className="text-link" href="#metodo">Conocer el método <span>↓</span></a>
          </div>
          <div className="trust-row"><ShieldIcon /><span>Sesiones revocables</span><i /><span>Tus claves nunca se almacenan</span></div>
        </div>

        <div className="hero-visual" aria-label="Vista previa de una sesión de Socratia">
          <div className="visual-top"><span><i /> Sesión de práctica</span><small>12:48</small></div>
          <div className="jury-panel">
            <div className="jury-avatar">SC</div>
            <p>“¿Cuál es el aporte principal de tu investigación frente a trabajos anteriores?”</p>
            <span>Jurado metodológico</span>
          </div>
          <div className="waveform" aria-hidden="true">
            {Array.from({ length: 34 }, (_, index) => <i key={index} style={{ height: `${18 + ((index * 17) % 46)}px` }} />)}
          </div>
          <div className="visual-metrics">
            <span><b>82%</b> contacto visual</span><span><b>01:14</b> respuesta</span><span><b>Claro</b> argumento</span>
          </div>
        </div>
      </section>

      <section className="method-section" id="metodo">
        <div className="section-heading centered">
          <p className="eyebrow">Un sistema, no otro chatbot</p>
          <h2>Preparación en tres movimientos</h2>
          <p>Cada capacidad aporta una señal distinta para ayudarte a defender ideas, no sólo a repetirlas.</p>
        </div>
        <div className="capability-grid">
          {capabilities.map(({ icon: Icon, title, text }, index) => (
            <article className="capability-card" key={title}>
              <span className="capability-number">0{index + 1}</span>
              <Icon className="capability-icon" />
              <h3>{title}</h3><p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="architecture-strip" id="arquitectura">
        <div><p className="eyebrow">Construido sobre una base seria</p><h2>Una arquitectura que puede crecer con el producto.</h2></div>
        <div className="tech-list"><span>Next.js</span><span>FastAPI</span><span>PostgreSQL</span><span>Docker</span><span>AWS</span></div>
      </section>

      <footer className="landing-footer"><Logo /><p>Entrena el criterio. Defiende con confianza.</p><span>© 2026 Socratia</span></footer>
    </main>
  );
}

