"use client";

import type { KeyboardEvent, ReactNode } from "react";
import { useState } from "react";

import { PasswordVisibilityIcon } from "@/components/ui/icons";
import { hasBoundarySpace, PASSWORD_MAX_LENGTH } from "@/features/auth/password-strength";

type PasswordFieldProps = {
  id: string;
  name: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: "current-password" | "new-password";
  placeholder: string;
  labelAction?: ReactNode;
  boundarySpaceMessage: string;
  fieldError?: string;
  children?: ReactNode;
};

export function PasswordField({
  id,
  name,
  label,
  value,
  onChange,
  autoComplete,
  placeholder,
  labelAction,
  boundarySpaceMessage,
  fieldError,
  children,
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const boundarySpace = hasBoundarySpace(value);
  const messageIds = [
    capsLock ? `${id}-caps-lock` : "",
    boundarySpace ? `${id}-boundary-space` : "",
    fieldError ? `${id}-error` : "",
  ].filter(Boolean);

  function updateCapsLock(event: KeyboardEvent<HTMLInputElement>) {
    setCapsLock(event.getModifierState("CapsLock"));
  }

  return (
    <div className="field-group">
      <div className="label-row">
        <label htmlFor={id}>{label}</label>
        {labelAction}
      </div>
      <div className="password-input-shell">
        <input
          id={id}
          name={name}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={updateCapsLock}
          onKeyUp={updateCapsLock}
          onBlur={() => setCapsLock(false)}
          autoComplete={autoComplete}
          autoCapitalize="none"
          spellCheck={false}
          maxLength={PASSWORD_MAX_LENGTH}
          placeholder={placeholder}
          aria-describedby={messageIds.length ? messageIds.join(" ") : undefined}
          aria-invalid={Boolean(fieldError)}
          required
        />
        <button
          className="password-toggle"
          type="button"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
          aria-pressed={visible}
        >
          <PasswordVisibilityIcon visible={visible} />
        </button>
      </div>
      {capsLock && (
        <p className="field-message field-warning" id={`${id}-caps-lock`} role="status">
          Bloq Mayús está activado.
        </p>
      )}
      {boundarySpace && (
        <p className="field-message field-warning" id={`${id}-boundary-space`} role="status">
          {boundarySpaceMessage}
        </p>
      )}
      {fieldError && (
        <p className="field-message field-invalid" id={`${id}-error`} role="alert">
          {fieldError}
        </p>
      )}
      {children}
    </div>
  );
}
