"use client";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { getCurrentUser } from "@/features/auth/api";
import { updateProfile } from "@/features/users/api";
import { apiRequest } from "@/lib/api";
import type { User } from "@/types/user";

interface SubscriptionInfo {
  subscription: {
    id: string;
    status: string;
    price_at_subscription: string;
    started_at: string;
  } | null;
  plan: {
    id: string;
    name: string;
    description: string | null;
    price: string;
    max_documents: number;
    max_simulations: number;
    max_storage_mb: number;
  } | null;
}

export function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [subData, setSubData] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [fullName, setFullName] = useState("");
  const [bio, setBio] = useState("");

  useEffect(() => {
    Promise.all([
      getCurrentUser(),
      apiRequest<SubscriptionInfo>("/subscription").catch(() => null),
    ])
      .then(([u, sub]) => {
        setUser(u);
        setFullName(u.full_name);
        setBio(u.bio || "");
        setSubData(sub);
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

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "US";

  const isAdmin = Boolean(user?.roles?.includes("Administrator"));

  return (
    <main className="dashboard-layout">
      <AppSidebar user={user} active="profile" />
      <section className="dashboard-content">
        {!user ? (
          <LoadingSkeleton label="Cargando perfil…"/>
        ) : (
          <>
            <header className="dashboard-header">
              <div>
                <p className="eyebrow">TU CUENTA</p>
                <h1>Perfil Académico</h1>
                <p>Gestiona tu información personal y verifica el estado de tu suscripción para defensas.</p>
              </div>
            </header>

        {/* Profile Identity Card */}
        <div className="bg-white rounded-2xl border p-6 mt-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6 max-w-4xl">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white font-extrabold text-2xl flex items-center justify-center shadow-md">
              {initials}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-xl font-bold text-gray-900">{user.full_name}</h2>
                <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
                  isAdmin ? "bg-purple-100 text-purple-800" : "bg-blue-100 text-blue-800"
                }`}>
                  {isAdmin ? "🛡️ Administrador" : "🎓 Postulante Académico"}
                </span>
                <span className="bg-green-100 text-green-800 text-xs font-semibold px-2 py-0.5 rounded-full">
                  ✓ Cuenta activa
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-0.5">{user.email}</p>
              <p className="text-xs text-gray-400 mt-1">
                Registrado desde: {user.created_at ? new Date(user.created_at).toLocaleDateString() : "2026"}
              </p>
            </div>
          </div>
          <Link
            href="/subscription"
            className="text-xs font-semibold bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 px-3.5 py-2 rounded-lg transition-colors flex items-center gap-1.5"
          >
            💳 Administrar Suscripción →
          </Link>
        </div>

        {/* Subscription Snapshot Card */}
        <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-2xl p-6 mt-6 max-w-4xl shadow-md border border-slate-700">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">🛡️</span>
                <h3 className="text-base font-bold text-slate-100">
                  {subData?.subscription?.status === "ACTIVE"
                    ? `Plan Activo: ${subData.plan?.name || "Plan Académico"}`
                    : "Sin Plan Activo"}
                </h3>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  subData?.subscription?.status === "ACTIVE"
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                    : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                }`}>
                  {subData?.subscription?.status === "ACTIVE" ? "Activo" : "Inactivo"}
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1 max-w-xl">
                {subData?.plan?.description || "Activa un plan para procesar tesis ilimitadas y habilitar jurados virtuales con telemetría biomecánica."}
              </p>
              {subData?.plan && (
                <div className="flex items-center gap-4 mt-3 text-xs text-slate-300">
                  <span>📄 <strong>{subData.plan.max_documents}</strong> Documentos</span>
                  <span>🎯 <strong>{subData.plan.max_simulations}</strong> Simulaciones</span>
                  <span>💾 <strong>{subData.plan.max_storage_mb} MB</strong> Almacenamiento</span>
                  <span>💵 <strong>${Number(subData.plan.price).toFixed(2)}/mes</strong></span>
                </div>
              )}
            </div>
            <Link
              href="/subscription"
              className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-all shadow-sm"
            >
              {subData?.subscription?.status === "ACTIVE" ? "Cambiar Plan →" : "Ver Planes Disponibles →"}
            </Link>
          </div>
        </div>

        {/* Edit Profile Form */}
        <section className="bg-white rounded-2xl border p-6 mt-6 max-w-4xl shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Información Personal y Académica</h3>
          {message && (
            <div className={`p-4 mb-4 rounded-xl text-sm font-medium ${
              message.type === "error" ? "bg-red-50 text-red-700 border border-red-200" : "bg-emerald-50 text-emerald-700 border border-emerald-200"
            }`}>
              {message.text}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-semibold text-gray-700">
                Correo Electrónico (No editable · Identidad Académica)
              </label>
              <input
                id="email"
                type="email"
                value={user.email}
                disabled
                className="mt-1 block w-full rounded-lg border border-gray-200 bg-gray-100 text-gray-500 shadow-sm sm:text-sm px-3.5 py-2.5 cursor-not-allowed"
              />
            </div>

            <div>
              <label htmlFor="fullName" className="block text-sm font-semibold text-gray-700">
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
                className="mt-1 block w-full rounded-lg border border-gray-300 bg-white text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 sm:text-sm px-3.5 py-2.5 outline-none"
              />
            </div>

            <div>
              <label htmlFor="bio" className="block text-sm font-semibold text-gray-700">
                Biografía Académica / Resumen de Investigación
              </label>
              <textarea
                id="bio"
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                maxLength={500}
                rows={4}
                className="mt-1 block w-full rounded-lg border border-gray-300 bg-white text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 sm:text-sm px-3.5 py-2.5 outline-none"
                placeholder="Escribe tu área de investigación, carrera o enfoque de tu tesis doctoral..."
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
        </>
        )}
      </section>
    </main>
  );
}
