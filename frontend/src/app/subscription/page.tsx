"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

interface Plan {
  id: string;
  name: string;
  description: string | null;
  price: string;
  max_documents: number;
  max_simulations: number;
  max_storage_mb: number;
  is_active: boolean;
}

interface Subscription {
  id: string;
  user_id: string;
  plan_id: string;
  status: "ACTIVE" | "CANCELLED" | "EXPIRED";
  price_at_subscription: string;
  started_at: string;
  cancelled_at: string | null;
  created_at: string;
}

interface SubscriptionData {
  subscription: Subscription | null;
  plan: Plan | null;
  history: Subscription[];
}

export default function StudentSubscriptionPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subData, setSubData] = useState<SubscriptionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Confirmation Modals
  const [selectedPlanToSubscribe, setSelectedPlanToSubscribe] = useState<Plan | null>(null);
  const [selectedPlanToChange, setSelectedPlanToChange] = useState<Plan | null>(null);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [plansRes, subRes] = await Promise.all([
        apiRequest<Plan[]>("/plans"),
        apiRequest<SubscriptionData>("/subscription"),
      ]);
      setPlans(plansRes);
      setSubData(subRes);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cargar datos de suscripción";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
  }, []);

  const handleSubscribe = async () => {
    if (!selectedPlanToSubscribe) return;
    try {
      setActionLoading(true);
      await apiRequest("/subscription", {
        method: "POST",
        body: JSON.stringify({ plan_id: selectedPlanToSubscribe.id }),
      });
      setSelectedPlanToSubscribe(null);
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al confirmar suscripción";
      alert(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleChangePlan = async () => {
    if (!selectedPlanToChange) return;
    try {
      setActionLoading(true);
      await apiRequest("/subscription", {
        method: "PATCH",
        body: JSON.stringify({ plan_id: selectedPlanToChange.id }),
      });
      setSelectedPlanToChange(null);
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cambiar de plan";
      alert(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    try {
      setActionLoading(true);
      await apiRequest("/subscription/cancel", {
        method: "POST",
      });
      setShowCancelConfirm(false);
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cancelar suscripción";
      alert(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const currentPlanId = subData?.subscription?.status === "ACTIVE" ? subData.subscription.plan_id : null;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Mi Suscripción</h1>
        <p className="text-gray-600 mt-1">
          Gestiona el plan académico para tus defensas y simulaciones.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Cargando suscripción...</p>
      ) : (
        <div className="space-y-8">
          {/* Tarjeta de Plan Actual */}
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h2 className="text-xl font-bold mb-4 text-gray-800">Estado de tu Plan Actual</h2>
            {subData?.subscription && subData.subscription.status === "ACTIVE" ? (
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-bold text-gray-900">
                      {subData.plan?.name || "Plan Activo"}
                    </span>
                    <span className="bg-green-100 text-green-800 text-xs font-semibold px-2.5 py-0.5 rounded-full">
                      Activo
                    </span>
                  </div>
                  <p className="text-gray-600 mt-1 text-sm">
                    {subData.plan?.description || "Acceso académico habilitado"}
                  </p>
                  <div className="flex gap-6 mt-3 text-xs text-gray-500">
                    <div>
                      Precio contratado:{" "}
                      <strong className="text-gray-800 font-semibold">
                        ${Number(subData.subscription.price_at_subscription).toFixed(2)}/mes
                      </strong>
                    </div>
                    <div>
                      Inicio:{" "}
                      <strong className="text-gray-800">
                        {new Date(subData.subscription.started_at).toLocaleDateString()}
                      </strong>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setShowCancelConfirm(true)}
                    className="text-sm text-red-600 hover:text-red-700 border border-red-200 hover:bg-red-50 font-medium px-4 py-2 rounded-lg transition-colors"
                  >
                    Cancelar Suscripción
                  </button>
                </div>
              </div>
            ) : (
              <div className="py-4">
                <p className="text-gray-600">
                  Actualmente no tienes ninguna suscripción activa. Elige uno de los planes disponibles a continuación para activar tus defensas académicas.
                </p>
              </div>
            )}
          </div>

          {/* Catálogo de Planes Disponibles */}
          <div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Planes Académicos Disponibles</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {plans.map((plan) => {
                const isCurrent = plan.id === currentPlanId;
                return (
                  <div
                    key={plan.id}
                    className={`bg-white rounded-xl border p-6 flex flex-col justify-between shadow-sm transition-all ${
                      isCurrent ? "ring-2 ring-blue-600 border-transparent" : "hover:border-gray-300"
                    }`}
                  >
                    <div>
                      {isCurrent && (
                        <span className="inline-block bg-blue-100 text-blue-800 text-xs font-bold px-2 py-0.5 rounded mb-2">
                          Plan Actual
                        </span>
                      )}
                      <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
                      <p className="text-gray-500 text-sm mt-1 h-10 line-clamp-2">
                        {plan.description || "Plan estándar para estudiantes"}
                      </p>
                      <div className="mt-4">
                        <span className="text-3xl font-extrabold text-gray-900">
                          ${Number(plan.price).toFixed(2)}
                        </span>
                        <span className="text-gray-500 text-sm"> / mes</span>
                      </div>
                      <ul className="mt-6 space-y-2 text-xs text-gray-600 border-t pt-4">
                        <li className="flex items-center gap-2">
                          <span className="text-green-500 font-bold">✓</span> Hasta {plan.max_documents} documentos
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="text-green-500 font-bold">✓</span> {plan.max_simulations} simulaciones activas
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="text-green-500 font-bold">✓</span> {plan.max_storage_mb} MB de almacenamiento
                        </li>
                      </ul>
                    </div>

                    <div className="mt-6 pt-4 border-t">
                      {isCurrent ? (
                        <button
                          disabled
                          className="w-full bg-gray-100 text-gray-400 font-semibold py-2 px-4 rounded-lg text-sm cursor-not-allowed"
                        >
                          Plan Actual
                        </button>
                      ) : currentPlanId ? (
                        <button
                          onClick={() => setSelectedPlanToChange(plan)}
                          className="w-full bg-blue-50 text-blue-600 hover:bg-blue-100 font-semibold py-2 px-4 rounded-lg text-sm transition-colors"
                        >
                          Cambiar a este plan
                        </button>
                      ) : (
                        <button
                          onClick={() => setSelectedPlanToSubscribe(plan)}
                          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg text-sm transition-colors"
                        >
                          Confirmar suscripción
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Historial de Suscripciones */}
          {subData?.history && subData.history.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="text-lg font-bold text-gray-800 mb-4">Historial de Suscripciones</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Fecha de Inicio</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Estado</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Precio Contratado</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Fecha Cancelación</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {subData.history.map((hist) => (
                      <tr key={hist.id}>
                        <td className="px-4 py-3">{new Date(hist.started_at).toLocaleDateString()}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded-full font-medium ${
                              hist.status === "ACTIVE"
                                ? "bg-green-100 text-green-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {hist.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-medium">
                          ${Number(hist.price_at_subscription).toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-gray-500">
                          {hist.cancelled_at ? new Date(hist.cancelled_at).toLocaleDateString() : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal Confirmar Nueva Suscripción */}
      {selectedPlanToSubscribe && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-sm w-full p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Confirmar Suscripción</h3>
            <p className="text-sm text-gray-600 mb-4">
              ¿Deseas activar el plan <strong>{selectedPlanToSubscribe.name}</strong> por{" "}
              <strong>${Number(selectedPlanToSubscribe.price).toFixed(2)}/mes</strong>?
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => setSelectedPlanToSubscribe(null)}
                className="px-4 py-2 border rounded-md text-sm text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={handleSubscribe}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-semibold"
              >
                {actionLoading ? "Confirmando..." : "Confirmar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Cambiar Plan */}
      {selectedPlanToChange && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-sm w-full p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Cambiar de Plan</h3>
            <p className="text-sm text-gray-600 mb-4">
              ¿Deseas cambiar tu suscripción al plan <strong>{selectedPlanToChange.name}</strong> por{" "}
              <strong>${Number(selectedPlanToChange.price).toFixed(2)}/mes</strong>? Tu plan anterior quedará finalizado y tu historial permanecerá guardado.
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => setSelectedPlanToChange(null)}
                className="px-4 py-2 border rounded-md text-sm text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={handleChangePlan}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-semibold"
              >
                {actionLoading ? "Actualizando..." : "Cambiar Plan"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Cancelar Suscripción */}
      {showCancelConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-sm w-full p-6">
            <h3 className="text-lg font-bold text-red-600 mb-2">Cancelar Suscripción</h3>
            <p className="text-sm text-gray-600 mb-4">
              ¿Estás seguro de que deseas cancelar tu suscripción activa? No podrás realizar nuevas simulaciones hasta que vuelvas a suscribirte. Tu historial no se perderá.
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => setShowCancelConfirm(false)}
                className="px-4 py-2 border rounded-md text-sm text-gray-700 hover:bg-gray-50"
              >
                Volver
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={handleCancelSubscription}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-semibold"
              >
                {actionLoading ? "Cancelando..." : "Sí, Cancelar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
