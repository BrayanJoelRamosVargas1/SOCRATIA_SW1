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
      if ("serviceWorker" in navigator) {
        // A shared device must stop receiving the previous account's notifications.
        try {
          const registration = await navigator.serviceWorker.getRegistration();
          const subscription = await registration?.pushManager.getSubscription();
          await subscription?.unsubscribe();
        } catch { /* Logout must remain possible if browser push is unavailable. */ }
      }
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

