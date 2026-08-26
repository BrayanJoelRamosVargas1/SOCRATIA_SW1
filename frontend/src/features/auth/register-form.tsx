"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { register } from "@/features/auth/api";
import { PasswordField } from "@/features/auth/password-field";
import {
  analyzePassword,
  countPasswordCharacters,
  PASSWORD_MIN_LENGTH,
} from "@/features/auth/password-strength";
import { ApiError } from "@/lib/api";

export function RegisterForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [confirmationError, setConfirmationError] = useState("");
  const [loading, setLoading] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const strength = analyzePassword(password);
  const passwordLength = countPasswordCharacters(password);
  const passwordsMatch = confirmation.length > 0 && password === confirmation;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPasswordError("");
    setConfirmationError("");
    if (passwordLength < PASSWORD_MIN_LENGTH) {
      setPasswordError(`Usa al menos ${PASSWORD_MIN_LENGTH} caracteres.`);
      return;
    }
    if (!strength.acceptable) {
      setPasswordError("Esta contraseña es demasiado predecible. Prueba con una frase más larga.");
      return;
    }
    if (password !== confirmation) {
      setConfirmationError("Las contraseñas no coinciden.");
      return;
    }

    setLoading(true);
    const data = new FormData(event.currentTarget);
    try {
      await register({
        full_name: String(data.get("full_name")),
        email: String(data.get("email")),
        password,
      });
      router.replace("/dashboard");
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "weak_password") {
        setPasswordError(caught.message);
      } else {
        setError(caught instanceof ApiError ? caught.message : "No pudimos crear tu cuenta.");
      }
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
      <PasswordField
        id="register-password"
        name="password"
        label="Contraseña"
        value={password}
        onChange={(value) => {
          setPassword(value);
          setPasswordError("");
        }}
        autoComplete="new-password"
        placeholder="Una frase de al menos 15 caracteres"
        boundarySpaceMessage="Tu contraseña comienza o termina con un espacio. Verifica que sea intencional: ese espacio se guardará como parte de la contraseña."
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
              {password && !strength.predictable ? "✓" : "○"} No usar una clave común o repetitiva
            </li>
            <li>Los espacios internos, iniciales y finales sí forman parte de la contraseña.</li>
          </ul>
        </div>
      </PasswordField>
      <PasswordField
        id="register-confirmation"
        name="confirmation"
        label="Confirmar contraseña"
        value={confirmation}
        onChange={(value) => {
          setConfirmation(value);
          setConfirmationError("");
        }}
        autoComplete="new-password"
        placeholder="Escríbela exactamente igual"
        boundarySpaceMessage="La confirmación comienza o termina con un espacio. Debe coincidir exactamente con la contraseña."
        fieldError={confirmationError}
      >
        {confirmation && !confirmationError && (
          <p
            className={`field-message ${passwordsMatch ? "field-valid" : "field-invalid"}`}
            role="status"
          >
            {passwordsMatch ? "✓ Las contraseñas coinciden." : "Las contraseñas no coinciden."}
          </p>
        )}
      </PasswordField>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-primary button-wide" type="submit" disabled={loading}>
        {loading ? "Creando cuenta…" : "Crear mi cuenta"}
      </button>
      <p className="terms">Puedes pegar una contraseña generada por tu gestor. Nunca la modificamos silenciosamente.</p>
    </form>
  );
}
