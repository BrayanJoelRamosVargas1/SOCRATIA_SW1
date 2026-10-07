"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type FocusType = "METHODOLOGICAL" | "TECHNICAL" | "CRITICAL";
type InterruptionLevel = "LOW" | "MEDIUM" | "HIGH";

interface JuryProfile {
  id: string;
  name: string;
  description: string;
  focus_type: FocusType;
  strictness: number;
  interruption_level: InterruptionLevel;
  is_active: boolean;
}

export default function AdminJuryProfilesPage() {
  const [profiles, setProfiles] = useState<JuryProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [formState, setFormState] = useState<Partial<JuryProfile>>({});
  const [isEditing, setIsEditing] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const fetchProfiles = async () => {
    try {
      setLoading(true);
      const data = await apiRequest<JuryProfile[]>("/admin/jury-profiles");
      setProfiles(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load jury profiles";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchProfiles();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEditing && formState.id) {
        await apiRequest(`/admin/jury-profiles/${formState.id}`, {
          method: "PATCH",
          body: JSON.stringify(formState),
        });
      } else {
        await apiRequest("/admin/jury-profiles", {
          method: "POST",
          body: JSON.stringify({ ...formState, is_active: formState.is_active ?? true }),
        });
      }
      setShowForm(false);
      setFormState({});
      setIsEditing(false);
      fetchProfiles();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save profile";
      alert(message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this profile?")) return;
    try {
      await apiRequest(`/admin/jury-profiles/${id}`, { method: "DELETE" });
      fetchProfiles();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Cannot delete profile";
      alert(message);
    }
  };

  const handleToggleActive = async (profile: JuryProfile) => {
    try {
      await apiRequest(`/admin/jury-profiles/${profile.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !profile.is_active }),
      });
      fetchProfiles();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to toggle profile";
      alert(message);
    }
  };

  const openEditForm = (profile: JuryProfile) => {
    setFormState(profile);
    setIsEditing(true);
    setShowForm(true);
  };

  const openCreateForm = () => {
    setFormState({ strictness: 3, focus_type: "TECHNICAL", interruption_level: "MEDIUM", is_active: true });
    setIsEditing(false);
    setShowForm(true);
  };

  if (loading) return <div className="p-8 text-center">Cargando...</div>;
  if (error) return <div className="p-8 text-red-500">{error}</div>;

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Administrar Perfiles de Jurado</h1>
        <button
          onClick={openCreateForm}
          className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700"
        >
          Crear Perfil
        </button>
      </div>

      {showForm && (
        <div className="mb-8 bg-gray-50 p-6 rounded-lg border border-gray-200">
          <h2 className="text-xl font-semibold mb-4">{isEditing ? "Editar Perfil" : "Nuevo Perfil"}</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nombre</label>
              <input
                type="text"
                required
                value={formState.name || ""}
                onChange={(e) => setFormState({ ...formState, name: e.target.value })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Descripción</label>
              <textarea
                required
                value={formState.description || ""}
                onChange={(e) => setFormState({ ...formState, description: e.target.value })}
                className="w-full border rounded px-3 py-2"
                rows={3}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Enfoque</label>
                <select
                  value={formState.focus_type}
                  onChange={(e) => setFormState({ ...formState, focus_type: e.target.value as FocusType })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="METHODOLOGICAL">Metodológico</option>
                  <option value="TECHNICAL">Técnico</option>
                  <option value="CRITICAL">Crítico</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Severidad (1-5)</label>
                <input
                  type="number"
                  required
                  min="1"
                  max="5"
                  value={formState.strictness || 3}
                  onChange={(e) => setFormState({ ...formState, strictness: parseInt(e.target.value) })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Nivel de Interrupción</label>
                <select
                  value={formState.interruption_level}
                  onChange={(e) => setFormState({ ...formState, interruption_level: e.target.value as InterruptionLevel })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="LOW">Bajo</option>
                  <option value="MEDIUM">Medio</option>
                  <option value="HIGH">Alto</option>
                </select>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="is_active"
                checked={formState.is_active ?? true}
                onChange={(e) => setFormState({ ...formState, is_active: e.target.checked })}
              />
              <label htmlFor="is_active" className="text-sm font-medium">Activo</label>
            </div>
            <div className="flex space-x-3 pt-4">
              <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                Guardar
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="bg-gray-300 text-gray-800 px-4 py-2 rounded hover:bg-gray-400"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-x-auto bg-white rounded shadow">
        <table className="min-w-full text-sm text-left">
          <thead className="bg-gray-100 text-gray-600 border-b">
            <tr>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Enfoque</th>
              <th className="px-4 py-3">Severidad</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {profiles.map((profile) => (
              <tr key={profile.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{profile.name}</td>
                <td className="px-4 py-3">{profile.focus_type}</td>
                <td className="px-4 py-3">{profile.strictness}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${profile.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {profile.is_active ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => handleToggleActive(profile)} className="text-gray-600 hover:text-gray-900">
                    {profile.is_active ? "Desactivar" : "Activar"}
                  </button>
                  <button onClick={() => openEditForm(profile)} className="text-blue-600 hover:text-blue-900">
                    Editar
                  </button>
                  <button onClick={() => handleDelete(profile.id)} className="text-red-600 hover:text-red-900">
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
            {profiles.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                  No hay perfiles de jurado registrados.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
