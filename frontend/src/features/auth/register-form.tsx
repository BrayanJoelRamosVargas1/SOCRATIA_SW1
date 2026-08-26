"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { register } from "@/features/auth/api";
import { ApiError } from "@/lib/api";

export function RegisterForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password"));
    const confirmation = String(data.get("confirmation"));
    if (password !== confirmation) {
      setError("Las contraseñas no coinciden.");
      setLoading(false);
      return;
    }
    try {
      await register({
        full_name: String(data.get("full_name")),
        email: String(data.get("email")),
        password,
      });
      router.replace("/dashboard");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No pudimos crear tu cuenta.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      <label>
        Nombre completo
        <input name="full_name" autoComplete="name" placeholder="Cómo quieres que te llamemos" minLength={2} required />
      </label>
      <label>
        Correo electrónico
        <input name="email" type="email" autoComplete="email" placeholder="tu@universidad.edu" required />
      </label>
      <div className="form-grid">
        <label>
          Contraseña
          <input name="password" type="password" autoComplete="new-password" minLength={8} placeholder="Mínimo 8 caracteres" required />
        </label>
        <label>
          Confirmar
          <input name="confirmation" type="password" autoComplete="new-password" minLength={8} placeholder="Repítela" required />
        </label>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-primary button-wide" type="submit" disabled={loading}>
        {loading ? "Creando cuenta…" : "Crear mi cuenta"}
      </button>
      <p className="terms">Al continuar aceptas los términos de uso y la política de privacidad.</p>
    </form>
  );
}

