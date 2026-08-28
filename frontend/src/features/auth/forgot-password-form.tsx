"use client";

import { FormEvent, useState } from "react";

import { forgotPassword } from "@/features/auth/api";
import { ApiError } from "@/lib/api";

export function ForgotPasswordForm() {
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    const data = new FormData(event.currentTarget);
    try {
      setMessage(await forgotPassword(String(data.get("email"))));
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No pudimos procesar la solicitud. Inténtalo de nuevo.",
      );
    } finally {
      setLoading(false);
    }
  }

  if (message) {
    return (
      <div className="notice-card" role="status">
        <strong>Revisa tu correo</strong>
        <p>{message}</p>
        <p>El enlace caduca en 15 minutos y solo puede utilizarse una vez.</p>
      </div>
    );
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      <label>
        Correo electrónico
        <input
          name="email"
          type="email"
          autoComplete="email"
          placeholder="tu@universidad.edu"
          required
        />
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-primary button-wide" type="submit" disabled={loading}>
        {loading ? "Enviando…" : "Enviar enlace de recuperación"}
      </button>
      <p className="terms">
        Por seguridad, mostraremos la misma respuesta aunque el correo no esté registrado.
      </p>
    </form>
  );
}
