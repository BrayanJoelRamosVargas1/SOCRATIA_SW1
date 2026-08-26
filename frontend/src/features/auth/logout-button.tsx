"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { logout } from "@/features/auth/api";

export function LogoutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleLogout() {
    setLoading(true);
    try {
      await logout();
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  return (
    <button className="logout-button" onClick={handleLogout} disabled={loading}>
      {loading ? "Saliendo…" : "Cerrar sesión"}
    </button>
  );
}

