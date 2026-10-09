"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { getCurrentUser } from "@/features/auth/api";
import { updateProfile } from "@/features/users/api";
import type { User } from "@/types/user";

export function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [fullName, setFullName] = useState("");
  const [bio, setBio] = useState("");

  useEffect(() => {
    getCurrentUser()
      .then((u) => {
        setUser(u);
        setFullName(u.full_name);
        setBio(u.bio || "");
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const updatedUser = await updateProfile({ full_name: fullName, bio });
      setUser(updatedUser);
      setMessage({ type: "success", text: "Perfil actualizado correctamente." });
    } catch (err: unknown) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Error al actualizar el perfil. Revisa los datos.",
      });
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <main className="loading-screen">
        <div className="loading-orbit" />
        <p>Cargando perfil...</p>
      </main>
    );
  }

  return (
    <main className="dashboard-layout">
      <AppSidebar user={user} active="profile" />
      <section className="dashboard-content">
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">Gestión de Perfil</p>
            <h1>Tu Perfil</h1>
            <p>Actualiza tu información personal aquí.</p>
          </div>
        </header>

        <section className="card p-6 mt-6 max-w-2xl">
          {message && (
            <div className={`p-4 mb-4 rounded ${message.type === "error" ? "bg-red-900 text-red-100" : "bg-green-900 text-green-100"}`}>
              {message.text}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-300">
                Correo Electrónico (No editable)
              </label>
              <input
                id="email"
                type="email"
                value={user.email}
                disabled
                className="mt-1 block w-full rounded-md border-gray-700 bg-gray-800 text-gray-400 shadow-sm sm:text-sm px-3 py-2 cursor-not-allowed"
              />
            </div>

            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-100">
                Nombre Completo
              </label>
              <input
                id="fullName"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                minLength={2}
                maxLength={120}
                className="mt-1 block w-full rounded-md border-gray-600 bg-gray-800 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 outline-none"
              />
            </div>

            <div>
              <label htmlFor="bio" className="block text-sm font-medium text-gray-100">
                Biografía
              </label>
              <textarea
                id="bio"
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                maxLength={500}
                rows={4}
                className="mt-1 block w-full rounded-md border-gray-600 bg-gray-800 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 outline-none"
                placeholder="Cuéntanos un poco sobre ti..."
              />
            </div>

            <div className="pt-4">
              <button
                type="submit"
                disabled={loading}
                className="inline-flex justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50"
              >
                {loading ? "Guardando..." : "Guardar Cambios"}
              </button>
            </div>
          </form>
        </section>
      </section>
    </main>
  );
}
