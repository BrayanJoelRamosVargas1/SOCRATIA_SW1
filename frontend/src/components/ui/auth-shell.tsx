import type { ReactNode } from "react";
import Link from "next/link";

import { Logo } from "@/components/ui/logo";

type AuthShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  footer: ReactNode;
};

export function AuthShell({ eyebrow, title, description, children, footer }: AuthShellProps) {
  return (
    <main className="auth-layout">
      <section className="auth-aside">
        <Logo />
        <div className="auth-aside-copy">
          <p className="eyebrow">Practica con intención</p>
          <h2>Las mejores defensas se construyen antes de entrar a la sala.</h2>
          <p>
            Convierte tu investigación en preguntas exigentes, ensaya bajo presión y detecta dónde mejorar.
          </p>
        </div>
        <p className="auth-quote">“La confianza no se improvisa; se entrena.”</p>
      </section>
      <section className="auth-main">
        <Link className="auth-back" href="/">
          ← Volver al inicio
        </Link>
        <div className="auth-card">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p className="auth-description">{description}</p>
          {children}
          <div className="auth-footer">{footer}</div>
        </div>
      </section>
    </main>
  );
}

