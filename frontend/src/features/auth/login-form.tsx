"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { login } from "@/features/auth/api";
import { PasswordField } from "@/features/auth/password-field";
import { ApiError } from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [password, setPassword] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await login({ email: String(data.get("email")), password });
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
      <PasswordField
        id="login-password"
        name="password"
        label="Contraseña"
        value={password}
        onChange={(value) => {
          setPassword(value);
          setError("");
        }}
        autoComplete="current-password"
        placeholder="Tu contraseña"
        boundarySpaceMessage="La contraseña comienza o termina con un espacio. Asegúrate de escribirla exactamente como la registraste."
        labelAction={<Link href="/forgot-password">¿La olvidaste?</Link>}
      />
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-primary button-wide" type="submit" disabled={loading}>
        {loading ? "Ingresando…" : "Iniciar sesión"}
      </button>
    </form>
  );
}
