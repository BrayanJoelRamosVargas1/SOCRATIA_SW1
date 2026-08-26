"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { login } from "@/features/auth/api";
import { ApiError } from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await login({ email: String(data.get("email")), password: String(data.get("password")) });
      router.replace("/dashboard");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No pudimos iniciar sesión.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      <label>
        Correo electrónico
        <input name="email" type="email" autoComplete="email" placeholder="tu@universidad.edu" required />
      </label>
      <label>
        <span className="label-row">
          Contraseña
          <a href="/forgot-password">¿La olvidaste?</a>
        </span>
        <input name="password" type="password" autoComplete="current-password" placeholder="Tu contraseña" required />
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-primary button-wide" type="submit" disabled={loading}>
        {loading ? "Ingresando…" : "Iniciar sesión"}
      </button>
    </form>
  );
}

