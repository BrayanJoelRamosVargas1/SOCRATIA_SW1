"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

interface User {
  id: string;
  email: string;
  full_name: string;
  bio: string | null;
  is_active: boolean;
  roles: string[];
  created_at: string;
}

interface PaginatedResponse {
  items: User[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState<string>(""); // "" | "true" | "false"

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editForm, setEditForm] = useState<{ is_active: boolean; roles: string[] }>({ is_active: true, roles: [] });

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const query = new URLSearchParams();
      query.append("page", page.toString());
      query.append("size", "20");
      if (search) query.append("search", search);
      if (roleFilter) query.append("role", roleFilter);
      if (activeFilter !== "") query.append("is_active", activeFilter);

      const data = await apiRequest<PaginatedResponse>(`/admin/users?${query.toString()}`);
      setUsers(data.items);
      setPages(data.pages);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load users";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchUsers();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, search, roleFilter, activeFilter]);

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    try {
      await apiRequest(`/admin/users/${editingUser.id}`, {
        method: "PATCH",
        body: JSON.stringify(editForm),
      });
      setEditingUser(null);
      fetchUsers();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update user";
      alert(message);
    }
  };

  const openEdit = (user: User) => {
    setEditingUser(user);
    setEditForm({ is_active: user.is_active, roles: [...user.roles] });
  };

  const toggleRole = (role: string) => {
    setEditForm((prev) => ({
      ...prev,
      roles: prev.roles.includes(role) 
        ? prev.roles.filter((r) => r !== role)
        : [...prev.roles, role]
    }));
  };

  if (loading && users.length === 0) return <div className="p-8 text-center">Cargando...</div>;
  if (error) return <div className="p-8 text-red-500">{error}</div>;

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Administrar Usuarios</h1>
      </div>

      <div className="flex space-x-4 mb-6">
        <input 
          type="text" 
          placeholder="Buscar por nombre o email..." 
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2 flex-grow"
        />
        <select 
          value={roleFilter} 
          onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="">Todos los roles</option>
          <option value="Administrator">Administrator</option>
          <option value="Student">Student</option>
        </select>
        <select 
          value={activeFilter} 
          onChange={(e) => { setActiveFilter(e.target.value); setPage(1); }}
          className="border rounded px-3 py-2"
        >
          <option value="">Todos los estados</option>
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
        </select>
      </div>

      {editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-full max-w-md shadow-xl">
            <h2 className="text-xl font-bold mb-4">Editar Usuario: {editingUser.email}</h2>
            <form onSubmit={handleEditSubmit}>
              <div className="mb-4">
                <label className="flex items-center space-x-2">
                  <input 
                    type="checkbox" 
                    checked={editForm.is_active} 
                    onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                  />
                  <span>Usuario Activo</span>
                </label>
              </div>
              <div className="mb-6">
                <p className="font-semibold mb-2">Roles:</p>
                <label className="flex items-center space-x-2 mb-1">
                  <input 
                    type="checkbox" 
                    checked={editForm.roles.includes("Administrator")} 
                    onChange={() => toggleRole("Administrator")}
                  />
                  <span>Administrator</span>
                </label>
              </div>
              <div className="flex justify-end space-x-3">
                <button type="button" onClick={() => setEditingUser(null)} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">
                  Cancelar
                </button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="overflow-x-auto bg-white rounded shadow">
        <table className="min-w-full text-sm text-left">
          <thead className="bg-gray-100 text-gray-600 border-b">
            <tr>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Roles</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{u.full_name}</td>
                <td className="px-4 py-3">{u.email}</td>
                <td className="px-4 py-3">{u.roles.join(", ")}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${u.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {u.is_active ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => openEdit(u)} className="text-blue-600 hover:text-blue-900">
                    Editar
                  </button>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                  No se encontraron usuarios.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {pages > 1 && (
        <div className="flex justify-between items-center mt-4">
          <button 
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            className="px-4 py-2 border rounded disabled:opacity-50"
          >
            Anterior
          </button>
          <span>Página {page} de {pages}</span>
          <button 
            disabled={page === pages}
            onClick={() => setPage(page + 1)}
            className="px-4 py-2 border rounded disabled:opacity-50"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  );
}
