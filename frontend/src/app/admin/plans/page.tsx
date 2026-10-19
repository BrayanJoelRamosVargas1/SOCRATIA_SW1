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
  created_at: string;
}

export default function AdminPlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showModal, setShowModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<Plan | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    price: "0.00",
    max_documents: 10,
    max_simulations: 10,
    max_storage_mb: 100,
    is_active: true,
  });

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const data = await apiRequest<Plan[]>("/admin/plans");
      setPlans(data);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cargar planes";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchPlans();
  }, []);

  const openCreateModal = () => {
    setEditingPlan(null);
    setForm({
      name: "",
      description: "",
      price: "0.00",
      max_documents: 10,
      max_simulations: 10,
      max_storage_mb: 100,
      is_active: true,
    });
    setShowModal(true);
  };

  const openEditModal = (plan: Plan) => {
    setEditingPlan(plan);
    setForm({
      name: plan.name,
      description: plan.description || "",
      price: plan.price,
      max_documents: plan.max_documents,
      max_simulations: plan.max_simulations,
      max_storage_mb: plan.max_storage_mb,
      is_active: plan.is_active,
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingPlan) {
        await apiRequest(`/admin/plans/${editingPlan.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            name: form.name,
            description: form.description || null,
            price: form.price,
            max_documents: Number(form.max_documents),
            max_simulations: Number(form.max_simulations),
            max_storage_mb: Number(form.max_storage_mb),
            is_active: form.is_active,
          }),
        });
      } else {
        await apiRequest("/admin/plans", {
          method: "POST",
          body: JSON.stringify({
            name: form.name,
            description: form.description || null,
            price: form.price,
            max_documents: Number(form.max_documents),
            max_simulations: Number(form.max_simulations),
            max_storage_mb: Number(form.max_storage_mb),
            is_active: form.is_active,
          }),
        });
      }
      setShowModal(false);
      fetchPlans();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al guardar el plan";
      alert(msg);
    }
  };

  const toggleActive = async (plan: Plan) => {
    try {
      await apiRequest(`/admin/plans/${plan.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !plan.is_active }),
      });
      fetchPlans();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al actualizar estado del plan";
      alert(msg);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Gestión de Planes</h1>
          <p className="text-gray-600 mt-1">Configuración del catálogo de planes de suscripción.</p>
        </div>
        <button
          onClick={openCreateModal}
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg"
        >
          + Crear Plan
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Cargando planes...</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto border">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Precio</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Límites</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {plans.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                    No hay planes registrados.
                  </td>
                </tr>
              ) : (
                plans.map((plan) => (
                  <tr key={plan.id}>
                    <td className="px-6 py-4">
                      <div className="font-semibold text-gray-900">{plan.name}</div>
                      <div className="text-sm text-gray-500">{plan.description || "Sin descripción"}</div>
                    </td>
                    <td className="px-6 py-4 text-sm font-semibold text-gray-900">
                      ${Number(plan.price).toFixed(2)}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-600">
                      <div>Docs: {plan.max_documents}</div>
                      <div>Sims: {plan.max_simulations}</div>
                      <div>Storage: {plan.max_storage_mb} MB</div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          plan.is_active
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {plan.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right text-sm font-medium space-x-2">
                      <button
                        onClick={() => openEditModal(plan)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => toggleActive(plan)}
                        className={plan.is_active ? "text-amber-600 hover:text-amber-900" : "text-green-600 hover:text-green-900"}
                      >
                        {plan.is_active ? "Desactivar" : "Activar"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4">
              {editingPlan ? "Editar Plan" : "Nuevo Plan"}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Nombre</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="mt-1 block w-full border rounded-md px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Descripción</label>
                <textarea
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="mt-1 block w-full border rounded-md px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Precio ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={form.price}
                  onChange={(e) => setForm({ ...form, price: e.target.value })}
                  className="mt-1 block w-full border rounded-md px-3 py-2 text-sm"
                />
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-xs font-medium text-gray-700">Max Docs</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={form.max_documents}
                    onChange={(e) => setForm({ ...form, max_documents: Number(e.target.value) })}
                    className="mt-1 block w-full border rounded-md px-2 py-1 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700">Max Sims</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={form.max_simulations}
                    onChange={(e) => setForm({ ...form, max_simulations: Number(e.target.value) })}
                    className="mt-1 block w-full border rounded-md px-2 py-1 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700">Storage (MB)</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={form.max_storage_mb}
                    onChange={(e) => setForm({ ...form, max_storage_mb: Number(e.target.value) })}
                    className="mt-1 block w-full border rounded-md px-2 py-1 text-sm"
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  className="h-4 w-4 text-blue-600 rounded"
                />
                <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                  Plan Activo
                </label>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border rounded-md text-sm text-gray-700 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium"
                >
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
