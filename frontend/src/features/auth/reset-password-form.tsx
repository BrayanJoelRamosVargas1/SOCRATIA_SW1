"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";

import { resetPassword } from "@/features/auth/api";
import { PasswordField } from "@/features/auth/password-field";
import {
  analyzePassword,
  countPasswordCharacters,
  PASSWORD_MIN_LENGTH,
} from "@/features/auth/password-strength";
import { ApiError } from "@/lib/api";

export function ResetPasswordForm({ token }: { token: string }) {
  const [error, setError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [confirmationError, setConfirmationError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const strength = analyzePassword(password);
  const passwordLength = countPasswordCharacters(password);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPasswordError("");
    setConfirmationError("");
    if (passwordLength < PASSWORD_MIN_LENGTH || !strength.acceptable) {
      setPasswordError(
        passwordLength < PASSWORD_MIN_LENGTH
          ? `Usa al menos ${PASSWORD_MIN_LENGTH} caracteres.`
          : "Esta contraseña es demasiado predecible. Prueba una frase más larga.",
      );
      return;
    }
    if (password !== confirmation) {
      setConfirmationError("Las contraseñas no coinciden.");
      return;
    }

    setLoading(true);
    try {
      setMessage(await resetPassword({ token, password }));
      setPassword("");
      setConfirmation("");
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "weak_password") {
        setPasswordError(caught.message);
      } else {
        setError(
          caught instanceof ApiError
            ? caught.message
            : "No pudimos restablecer la contraseña.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="notice-card notice-error" role="alert">
        <strong>Enlace incompleto</strong>
        <p>Solicita un nuevo correo de recuperación para continuar.</p>
      </div>
    );
  }

  if (message) {
    return (
      <div className="notice-card" role="status">
        <strong>Contraseña actualizada</strong>
        <p>{message}</p>
        <Link className="button button-primary button-wide" href="/login">
          Iniciar sesión
        </Link>
      </div>
    );
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      <PasswordField
        id="reset-password"
        name="password"
        label="Nueva contraseña"
        value={password}
        onChange={(value) => {
          setPassword(value);
          setPasswordError("");
        }}
        autoComplete="new-password"
        placeholder="Una frase de al menos 15 caracteres"
        boundarySpaceMessage="La contraseña comienza o termina con un espacio. Ese espacio se guardará como parte de la contraseña."
        fieldError={passwordError}
      >
        <div className="password-guidance" aria-live="polite">
          <div className="strength-heading">
            <span>Fortaleza estimada</span>
            <strong>{strength.label}</strong>
          </div>
          <div className="strength-track" aria-hidden="true">
            <span className={`strength-value strength-${strength.score}`} />
          </div>
          <ul>
            <li className={passwordLength >= PASSWORD_MIN_LENGTH ? "is-valid" : ""}>
              {passwordLength >= PASSWORD_MIN_LENGTH ? "✓" : "○"} Al menos 15 caracteres
            </li>
            <li className={password && !strength.predictable ? "is-valid" : ""}>
              {password && !strength.predictable ? "✓" : "○"} Evita claves comunes o repetitivas
            </li>
          </ul>
        </div>
      </PasswordField>
      <PasswordField
        id="reset-confirmation"
        name="confirmation"
        label="Confirmar nueva contraseña"
        value={confirmation}
        onChange={(value) => {
          setConfirmation(value);
          setConfirmationError("");
        }}
        autoComplete="new-password"
        placeholder="Escríbela exactamente igual"
        boundarySpaceMessage="La confirmación comienza o termina con un espacio y debe coincidir exactamente."
        fieldError={confirmationError}
      />
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-primary button-wide" type="submit" disabled={loading}>
        {loading ? "Actualizando…" : "Guardar nueva contraseña"}
      </button>
    </form>
  );
}
