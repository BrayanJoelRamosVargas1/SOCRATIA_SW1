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
  const [confirmedPolicy, setConfirmedPolicy] = useState(false);
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

      {/* Banner de Política de Suscripción Única */}
      {subData?.subscription && subData.subscription.status === "ACTIVE" && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <div className="text-2xl">🛡️</div>
          <div>
            <h3 className="text-sm font-bold text-blue-900">
              Política de Suscripción Única Activa ({subData.plan?.name || "Plan Actual"})
            </h3>
            <p className="text-xs text-blue-800 mt-1 leading-relaxed">
              De acuerdo con las reglas de negocio de Socratia, cada cuenta puede mantener <strong>únicamente un plan activo a la vez</strong>.
              Si seleccionas un plan diferente, tu suscripción actual quedará finalizada de inmediato y será sustituida por el nuevo plan contratado. Todo tu historial de documentos y evaluaciones previas se conservará intacto.
            </p>
          </div>
        </div>
      )}

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
                const currentPrice = subData?.subscription?.price_at_subscription
                  ? Number(subData.subscription.price_at_subscription)
                  : 0;
                const thisPrice = Number(plan.price);
                const isUpgrade = currentPlanId && thisPrice > currentPrice;
                const isDowngrade = currentPlanId && thisPrice < currentPrice;

                return (
                  <div
                    key={plan.id}
                    className={`bg-white rounded-xl border p-6 flex flex-col justify-between shadow-sm transition-all ${
                      isCurrent
                        ? "ring-2 ring-emerald-500 border-transparent bg-emerald-50/15"
                        : "hover:border-gray-300 hover:shadow-md"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        {isCurrent ? (
                          <span className="inline-block bg-emerald-100 text-emerald-800 text-xs font-bold px-2.5 py-0.5 rounded-full">
                            🔒 Plan Actual Activo
                          </span>
                        ) : isUpgrade ? (
                          <span className="inline-block bg-indigo-100 text-indigo-800 text-xs font-bold px-2.5 py-0.5 rounded-full">
                            🚀 Mejora de Plan (Upgrade)
                          </span>
                        ) : isDowngrade ? (
                          <span className="inline-block bg-amber-100 text-amber-800 text-xs font-bold px-2.5 py-0.5 rounded-full">
                            ⬇️ Cambio de Plan (Downgrade)
                          </span>
                        ) : (
                          <span className="inline-block bg-gray-100 text-gray-700 text-xs font-medium px-2 py-0.5 rounded">
                            Nivel Académico
                          </span>
                        )}
                      </div>
                      <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
                      <p className="text-gray-500 text-sm mt-1 h-12 line-clamp-2">
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
                          <span className="text-emerald-600 font-bold">✓</span> Hasta {plan.max_documents} documentos y tesis
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="text-emerald-600 font-bold">✓</span> {plan.max_simulations} simulaciones de defensa
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="text-emerald-600 font-bold">✓</span> {plan.max_storage_mb} MB almacenamiento seguro
                        </li>
                      </ul>
                    </div>

                    <div className="mt-6 pt-4 border-t">
                      {isCurrent ? (
                        <div className="text-center">
                          <button
                            disabled
                            className="w-full bg-emerald-50 text-emerald-700 font-bold py-2.5 px-4 rounded-lg text-xs cursor-not-allowed border border-emerald-200"
                          >
                            ✓ Plan en uso en tu cuenta
                          </button>
                          <span className="text-[10px] text-gray-500 mt-1 block">
                            Tu suscripción vigente está asignada a este plan
                          </span>
                        </div>
                      ) : currentPlanId ? (
                        <div>
                          <button
                            onClick={() => {
                              setConfirmedPolicy(false);
                              setSelectedPlanToChange(plan);
                            }}
                            className={`w-full font-semibold py-2 px-4 rounded-lg text-sm transition-colors border ${
                              isUpgrade
                                ? "bg-indigo-600 hover:bg-indigo-700 text-white border-transparent"
                                : "bg-gray-50 text-gray-700 hover:bg-gray-100 border-gray-300"
                            }`}
                          >
                            {isUpgrade ? `🚀 Subir a ${plan.name}` : `⬇️ Cambiar a ${plan.name}`}
                          </button>
                          <span className="text-[10px] text-amber-700 mt-1 block text-center font-medium">
                            ⚠️ Sustituirá a tu plan actual
                          </span>
                        </div>
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
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Solicitud de Cambio de Plan</h3>
            <div className="bg-amber-50 border border-amber-200 text-amber-900 p-3 rounded-lg text-xs mb-4">
              <strong>🛡️ Restricción de Suscripción Única:</strong> Tu cuenta mantiene activo actualmente el plan{" "}
              <strong>{subData?.plan?.name || "Actual"}</strong>. Por arquitectura de seguridad académica, el sistema no permite múltiples suscripciones concurrentes.
              Al procesar este cambio, tu plan anterior <strong>finalizará de inmediato</strong> y comenzará la vigencia de{" "}
              <strong>{selectedPlanToChange.name}</strong> (${Number(selectedPlanToChange.price).toFixed(2)}/mes). Todo tu trabajo previo permanece asegurado.
            </div>

            <label className="flex items-start gap-2.5 p-3 bg-gray-50 rounded-lg border border-gray-200 mb-4 cursor-pointer">
              <input
                type="checkbox"
                checked={confirmedPolicy}
                onChange={(e) => setConfirmedPolicy(e.target.checked)}
                className="mt-0.5 rounded text-blue-600 focus:ring-blue-500"
              />
              <span className="text-xs text-gray-700 leading-snug">
                He leído y acepto la política de sustitución inmediata: mi plan activo actual será reemplazado por <strong>{selectedPlanToChange.name}</strong>.
              </span>
            </label>

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
                disabled={actionLoading || !confirmedPolicy}
                onClick={handleChangePlan}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {actionLoading ? "Actualizando..." : "Confirmar Cambio de Plan"}
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
