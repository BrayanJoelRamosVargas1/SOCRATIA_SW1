"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { logout } from "@/features/auth/api";

type LogoutButtonProps = {
  className?: string;
};

export function LogoutButton({ className = "" }: LogoutButtonProps = {}) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  async function handleLogout() {
    setLoading(true);
    setError(false);
    try {
      await logout();
      router.replace("/login");
      router.refresh();
    } catch {
      setError(true);
      setLoading(false);
    }
  }

  return (
    <>
    <button type="button" className={`logout-button ${className}`.trim()} onClick={handleLogout} disabled={loading}>
      {loading ? "Saliendo…" : "Cerrar sesión"}
    </button>
    {error && <p className="form-error" role="alert">No se pudo cerrar la sesión. Intenta nuevamente.</p>}
    </>
  );
}

