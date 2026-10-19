"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

interface Plan {
  id: string;
  name: string;
  price: string;
  is_active: boolean;
}

interface UserOption { id: string; full_name: string; email: string; }

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

export default function AdminSubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter
  const [statusFilter, setStatusFilter] = useState<string>("");

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createUserId, setCreateUserId] = useState("");
  const [createPlanId, setCreatePlanId] = useState("");
  const [userSearch,setUserSearch] = useState("");
  const [userOptions,setUserOptions] = useState<UserOption[]>([]);
  const [searchingUsers,setSearchingUsers] = useState(false);
  const [userSearchError,setUserSearchError] = useState("");
  useEffect(() => {
    if (!showCreateModal) return;
    let active = true;
    const timer = setTimeout(async () => {
      setSearchingUsers(true); setUserSearchError("");
      try {
        const response = await apiRequest<{items:UserOption[]}>(`/admin/users?size=20&is_active=true&search=${encodeURIComponent(userSearch)}`);
        if (active) setUserOptions(response.items);
      } catch {if (active) {setUserOptions([]); setUserSearchError("No pudimos consultar usuarios. Vuelve a buscar.");}}
      finally {if (active) setSearchingUsers(false);}
    },250);
    return () => {active=false; clearTimeout(timer);};
  },[showCreateModal,userSearch]);

  const [showChangeModal, setShowChangeModal] = useState(false);
  const [selectedSub, setSelectedSub] = useState<Subscription | null>(null);
  const [changePlanId, setChangePlanId] = useState("");

  const fetchData = async () => {
    try {
      setLoading(true);
      const [subsData, plansData] = await Promise.all([
        apiRequest<Subscription[]>("/admin/subscriptions"),
        apiRequest<Plan[]>("/admin/plans"),
      ]);
      setSubscriptions(subsData);
      setPlans(plansData);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cargar suscripciones";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData();
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiRequest("/admin/subscriptions", {
        method: "POST",
        body: JSON.stringify({
          user_id: createUserId.trim(),
          plan_id: createPlanId,
        }),
      });
      setShowCreateModal(false);
      setCreateUserId("");
      setCreatePlanId("");
      fetchData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al asignar plan";
      alert(msg);
    }
  };

  const handleChangePlanSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSub) return;
    try {
      await apiRequest(`/admin/subscriptions/${selectedSub.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          plan_id: changePlanId,
        }),
      });
      setShowChangeModal(false);
      setSelectedSub(null);
      fetchData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cambiar de plan";
      alert(msg);
    }
  };

  const handleCancelSub = async (sub: Subscription) => {
    if (!confirm("¿Seguro que deseas cancelar esta suscripción?")) return;
    try {
      await apiRequest(`/admin/subscriptions/${sub.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: "CANCELLED",
        }),
      });
      fetchData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cancelar suscripción";
      alert(msg);
    }
  };

  const getPlanName = (planId: string) => {
    const p = plans.find((item) => item.id === planId);
    return p ? p.name : planId.slice(0, 8) + "...";
  };

  const filteredSubs = subscriptions.filter((sub) => {
    if (!statusFilter) return true;
    return sub.status === statusFilter;
  });

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Gestión de Suscripciones</h1>
          <p className="text-gray-600 mt-1">Supervisión y asignación administrativa de suscripciones.</p>
        </div>
        <button
          onClick={() => {
            const firstActive = plans.find((p) => p.is_active);
            setCreatePlanId(firstActive ? firstActive.id : "");
            setShowCreateModal(true);
          }}
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg"
        >
          + Asignar Suscripción
        </button>
      </div>

      <div className="mb-6 flex gap-4 items-center">
        <label className="text-sm font-medium text-gray-700">Filtrar por estado:</label>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border rounded-md px-3 py-1.5 text-sm"
        >
          <option value="">Todos los estados</option>
          <option value="ACTIVE">Activas</option>
          <option value="CANCELLED">Canceladas</option>
          <option value="EXPIRED">Expiradas</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Cargando suscripciones...</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto border">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Usuario</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plan</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Precio</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Inicio / Cancelación</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredSubs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    No hay suscripciones registradas.
                  </td>
                </tr>
              ) : (
                filteredSubs.map((sub) => (
                  <tr key={sub.id}>
                    <td className="px-6 py-4">
                      <div className="font-mono text-xs text-gray-700">{sub.user_id}</div>
                    </td>
                    <td className="px-6 py-4 text-sm font-semibold text-gray-900">
                      {getPlanName(sub.plan_id)}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      ${Number(sub.price_at_subscription).toFixed(2)}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          sub.status === "ACTIVE"
                            ? "bg-green-100 text-green-800"
                            : sub.status === "CANCELLED"
                            ? "bg-gray-100 text-gray-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {sub.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-600">
                      <div>Inicio: {new Date(sub.started_at).toLocaleDateString()}</div>
                      {sub.cancelled_at && (
                        <div className="text-red-600">
                          Cancelado: {new Date(sub.cancelled_at).toLocaleDateString()}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right text-sm font-medium space-x-2">
                      {sub.status === "ACTIVE" && (
                        <>
                          <button
                            onClick={() => {
                              setSelectedSub(sub);
                              setChangePlanId(sub.plan_id);
                              setShowChangeModal(true);
                            }}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            Cambiar Plan
                          </button>
                          <button
                            onClick={() => handleCancelSub(sub)}
                            className="text-red-600 hover:text-red-900"
                          >
                            Cancelar
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal Asignar Suscripción */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4">Asignar Suscripción a Usuario</h2>
            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label htmlFor="subscription-user-search" className="block text-sm font-medium text-gray-700">Buscar usuario</label>
                <input id="subscription-user-search" type="search" placeholder="Nombre o correo electrónico" value={userSearch} onChange={event => {setUserSearch(event.target.value); setCreateUserId("");}} className="mt-1 block w-full border rounded-md px-3 py-2 text-sm" />
                <label htmlFor="subscription-user" className="block text-sm font-medium text-gray-700 mt-3">Usuario</label>
                <select id="subscription-user" required value={createUserId} disabled={searchingUsers} onChange={event => setCreateUserId(event.target.value)} className="mt-1 block w-full border rounded-md px-3 py-2 text-sm">
                  <option value="">{searchingUsers ? "Buscando…" : "Selecciona un usuario"}</option>
                  {userOptions.map(user => <option key={user.id} value={user.id}>{user.full_name} · {user.email}</option>)}
                </select>
                {userSearchError && <p role="alert" className="form-error">{userSearchError}</p>}
                {!searchingUsers && !userSearchError && userOptions.length === 0 && <p className="text-sm text-gray-500 mt-2">No hay usuarios activos para esta búsqueda.</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Plan</label>
                <select
                  required
                  value={createPlanId}
                  onChange={(e) => setCreatePlanId(e.target.value)}
                  className="mt-1 block w-full border rounded-md px-3 py-2 text-sm"
                >
                  <option value="">Selecciona un plan activo</option>
                  {plans
                    .filter((p) => p.is_active)
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} (${Number(p.price).toFixed(2)})
                      </option>
                    ))}
                </select>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border rounded-md text-sm text-gray-700 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium"
                >
                  Asignar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Cambiar Plan */}
      {showChangeModal && selectedSub && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4">Cambiar Plan de Suscripción</h2>
            <form onSubmit={handleChangePlanSubmit} className="space-y-4">
              <p className="text-sm text-gray-600">
                Usuario: <span className="font-mono">{selectedSub.user_id}</span>
              </p>
              <div>
                <label className="block text-sm font-medium text-gray-700">Nuevo Plan</label>
                <select
                  required
                  value={changePlanId}
                  onChange={(e) => setChangePlanId(e.target.value)}
                  className="mt-1 block w-full border rounded-md px-3 py-2 text-sm"
                >
                  {plans
                    .filter((p) => p.is_active)
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} (${Number(p.price).toFixed(2)})
                      </option>
                    ))}
                </select>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowChangeModal(false)}
                  className="px-4 py-2 border rounded-md text-sm text-gray-700 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium"
                >
                  Actualizar Plan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
