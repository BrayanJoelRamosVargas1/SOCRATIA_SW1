"use client";

import { useEffect, useState, useTransition } from "react";
import {
  Users,
  Search,
  Shield,
  GraduationCap,
  CheckCircle2,
  Edit3,
  X,
  AlertCircle,
  ShieldCheck,
  UserCheck,
  UserX,
  ChevronLeft,
  ChevronRight,
  RefreshCw
} from "lucide-react";
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
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState<string>("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Edit Modal State
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editForm, setEditForm] = useState<{
    full_name: string;
    email: string;
    is_active: boolean;
    roles: string[];
  }>({
    full_name: "",
    email: "",
    is_active: true,
    roles: [],
  });
  const [savingUser, setSavingUser] = useState(false);
  const [, startTransition] = useTransition();

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const query = new URLSearchParams();
      query.append("page", page.toString());
      query.append("size", "20");
      if (search.trim()) query.append("search", search.trim());
      if (roleFilter) query.append("role", roleFilter);
      if (activeFilter !== "") query.append("is_active", activeFilter);

      const data = await apiRequest<PaginatedResponse>(`/admin/users?${query.toString()}`);
      setUsers(data.items);
      setTotal(data.total);
      setPages(data.pages || 1);
      setError(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error al cargar la lista de usuarios";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, roleFilter, activeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleClearFilters = () => {
    setSearch("");
    setRoleFilter("");
    setActiveFilter("");
    setPage(1);
    startTransition(() => {
      fetchUsers();
    });
  };

  const openEdit = (user: User) => {
    setEditingUser(user);
    setEditForm({
      full_name: user.full_name,
      email: user.email,
      is_active: user.is_active,
      roles: [...user.roles],
    });
    setFeedbackMessage(null);
  };

  const closeEdit = () => {
    setEditingUser(null);
    setSavingUser(false);
  };

  const toggleRole = (roleToToggle: string) => {
    setEditForm((prev) => {
      let updatedRoles = prev.roles.includes(roleToToggle)
        ? prev.roles.filter((r) => r !== roleToToggle)
        : [...prev.roles, roleToToggle];

      // Ensure at least one role remains (default to student)
      if (updatedRoles.length === 0) {
        updatedRoles = ["student"];
      }
      return { ...prev, roles: updatedRoles };
    });
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    try {
      setSavingUser(true);
      await apiRequest(`/admin/users/${editingUser.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          full_name: editForm.full_name.trim(),
          email: editForm.email.trim(),
          is_active: editForm.is_active,
          roles: editForm.roles,
        }),
      });

      setFeedbackMessage({
        type: "success",
        text: `Usuario "${editForm.full_name}" actualizado exitosamente.`,
      });
      closeEdit();
      fetchUsers();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "No se pudo actualizar el usuario.";
      setFeedbackMessage({ type: "error", text: message });
    } finally {
      setSavingUser(false);
    }
  };

  // Quick stats calculation
  const adminCount = users.filter((u) => u.roles.some((r) => r.toLowerCase().includes("admin"))).length;
  const activeCount = users.filter((u) => u.is_active).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
              <ShieldCheck className="w-3.5 h-3.5" />
              Gobierno de Identidades
            </span>
            <span className="text-xs text-slate-500">· RBAC & Seguridad</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Administración de Usuarios</h1>
          <p className="text-sm text-slate-600">
            Control de acceso basado en roles, auditoría de sesiones y activación/baja de cuentas institucionales.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchUsers()}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 rounded-xl shadow-xs transition-colors disabled:opacity-60"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-teal-600" : ""}`} />
            <span>Refrescar</span>
          </button>
        </div>
      </div>

      {/* Global Feedback Alert */}
      {(feedbackMessage || error) && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between text-sm ${
            feedbackMessage?.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-rose-50 border-rose-200 text-rose-800"
          }`}
        >
          <div className="flex items-center gap-2">
            {feedbackMessage?.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            )}
            <span>{feedbackMessage?.text || error}</span>
          </div>
          <button
            onClick={() => {
              setFeedbackMessage(null);
              setError(null);
            }}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Quick Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-medium">Total Registrados</span>
            <p className="text-xl font-bold text-slate-900">{total}</p>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-medium">Administradores en esta vista</span>
            <p className="text-xl font-bold text-purple-700">{adminCount}</p>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <UserCheck className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-medium">En Vista Activos</span>
            <p className="text-xl font-bold text-emerald-700">{activeCount}</p>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center shrink-0">
            <GraduationCap className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-medium">Página Actual</span>
            <p className="text-xl font-bold text-slate-900">{page} / {pages}</p>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-grow">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar por nombre o correo electrónico..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white transition-all text-slate-800"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-700"
            >
              <option value="">Todos los roles</option>
              <option value="Administrator">Administrator (Gobierno)</option>
              <option value="student">student (Estudiante)</option>
            </select>

            <select
              value={activeFilter}
              onChange={(e) => {
                setActiveFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-700"
            >
              <option value="">Todos los estados</option>
              <option value="true">Activos</option>
              <option value="false">Inactivos (Suspendidos)</option>
            </select>

            <button
              type="submit"
              className="px-4 py-2 text-sm font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded-xl transition-colors shrink-0 shadow-xs"
            >
              Buscar
            </button>

            {(search || roleFilter || activeFilter) && (
              <button
                type="button"
                onClick={handleClearFilters}
                className="px-3 py-2 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors shrink-0"
                title="Limpiar filtros"
              >
                Limpiar
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm text-left">
            <thead className="bg-slate-50/80 text-slate-600 border-b border-slate-200 text-xs uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-6 py-4">Usuario</th>
                <th className="px-6 py-4">Correo Institucional</th>
                <th className="px-6 py-4">Roles de Acceso</th>
                <th className="px-6 py-4">Estado</th>
                <th className="px-6 py-4">Fecha Registro</th>
                <th className="px-6 py-4 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((u) => {
                const isAdmin = u.roles.some((r) => r.toLowerCase().includes("admin"));
                const initials = u.full_name
                  ? u.full_name
                      .split(" ")
                      .map((n) => n[0])
                      .slice(0, 2)
                      .join("")
                      .toUpperCase()
                  : "U";

                return (
                  <tr key={u.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs shrink-0 ${
                            isAdmin
                              ? "bg-purple-100 text-purple-800 border border-purple-200"
                              : "bg-teal-100 text-teal-800 border border-teal-200"
                          }`}
                        >
                          {initials}
                        </div>
                        <div>
                          <p className="font-bold text-slate-900">{u.full_name}</p>
                          <p className="text-[11px] text-slate-400 font-mono truncate max-w-[120px]">{u.id}</p>
                        </div>
                      </div>
                    </td>

                    <td className="px-6 py-4 whitespace-nowrap text-slate-600 font-medium font-mono text-xs">
                      {u.email}
                    </td>

                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-wrap gap-1">
                        {u.roles.map((r) => {
                          const isRoleAdmin = r.toLowerCase().includes("admin");
                          return (
                            <span
                              key={r}
                              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                                isRoleAdmin
                                  ? "bg-purple-50 text-purple-700 border border-purple-200"
                                  : "bg-slate-100 text-slate-700 border border-slate-200"
                              }`}
                            >
                              {isRoleAdmin ? <Shield className="w-3 h-3 text-purple-600" /> : <GraduationCap className="w-3 h-3 text-teal-600" />}
                              <span>{r}</span>
                            </span>
                          );
                        })}
                      </div>
                    </td>

                    <td className="px-6 py-4 whitespace-nowrap">
                      {u.is_active ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                          Activo
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                          Inactivo
                        </span>
                      )}
                    </td>

                    <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-500">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                    </td>

                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <button
                        onClick={() => openEdit(u)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:text-teal-700 bg-white hover:bg-teal-50 border border-slate-200 hover:border-teal-300 rounded-lg shadow-2xs transition-colors"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Editar</span>
                      </button>
                    </td>
                  </tr>
                );
              })}

              {users.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500 space-y-2">
                    <UserX className="w-8 h-8 text-slate-400 mx-auto" />
                    <p className="font-semibold text-slate-700">No se encontraron usuarios</p>
                    <p className="text-xs text-slate-400">Intenta ajustar los filtros de búsqueda o el rol seleccionado.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {pages > 1 && (
          <div className="p-4 bg-slate-50/60 border-t border-slate-200 flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">
              Página {page} de {pages} ({total} usuarios en total)
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 disabled:opacity-50 disabled:pointer-events-none transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Anterior
              </button>
              <button
                disabled={page === pages}
                onClick={() => setPage(page + 1)}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 disabled:opacity-50 disabled:pointer-events-none transition-colors"
              >
                Siguiente <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Edit User Modal Dialog */}
      {editingUser && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div>
                <h3 className="font-bold text-slate-900 text-lg">Modificar Perfil y Accesos</h3>
                <p className="text-xs text-slate-500">ID: {editingUser.id}</p>
              </div>
              <button
                onClick={closeEdit}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleEditSubmit} className="p-6 space-y-5">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Nombre Completo
                </label>
                <input
                  type="text"
                  required
                  value={editForm.full_name}
                  onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                  className="w-full px-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white text-slate-800"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Correo Electrónico
                </label>
                <input
                  type="email"
                  required
                  value={editForm.email}
                  onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                  className="w-full px-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white text-slate-800 font-mono"
                />
              </div>

              {/* Roles Toggle */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Roles Asignados
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {/* Administrator Role Option */}
                  <button
                    type="button"
                    onClick={() => toggleRole("Administrator")}
                    className={`p-3 rounded-xl border text-left flex items-start gap-2.5 transition-all ${
                      editForm.roles.includes("Administrator")
                        ? "bg-purple-50/80 border-purple-300 ring-2 ring-purple-500/20"
                        : "bg-slate-50 border-slate-200 opacity-60 hover:opacity-100"
                    }`}
                  >
                    <Shield className={`w-4 h-4 mt-0.5 ${editForm.roles.includes("Administrator") ? "text-purple-600" : "text-slate-400"}`} />
                    <div>
                      <p className="font-bold text-xs text-slate-900">Administrator</p>
                      <p className="text-[10px] text-slate-500">Acceso a consola de gobierno</p>
                    </div>
                  </button>

                  {/* Student Role Option */}
                  <button
                    type="button"
                    onClick={() => toggleRole("student")}
                    className={`p-3 rounded-xl border text-left flex items-start gap-2.5 transition-all ${
                      editForm.roles.includes("student")
                        ? "bg-teal-50/80 border-teal-300 ring-2 ring-teal-500/20"
                        : "bg-slate-50 border-slate-200 opacity-60 hover:opacity-100"
                    }`}
                  >
                    <GraduationCap className={`w-4 h-4 mt-0.5 ${editForm.roles.includes("student") ? "text-teal-600" : "text-slate-400"}`} />
                    <div>
                      <p className="font-bold text-xs text-slate-900">Estudiante</p>
                      <p className="text-[10px] text-slate-500">Simulación y documentos</p>
                    </div>
                  </button>
                </div>
              </div>

              {/* Status Toggle Switch */}
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
                <div>
                  <span className="font-bold text-xs text-slate-900 block">Estado de la Cuenta</span>
                  <span className="text-xs text-slate-500">
                    {editForm.is_active ? "Usuario activo con acceso al sistema" : "Usuario suspendido (revoca sesiones)"}
                  </span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editForm.is_active}
                    onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                </label>
              </div>

              {/* Modal Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={closeEdit}
                  disabled={savingUser}
                  className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={savingUser}
                  className="inline-flex items-center gap-2 px-5 py-2 text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded-xl transition-colors shadow-sm disabled:opacity-60"
                >
                  {savingUser && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{savingUser ? "Guardando..." : "Guardar Cambios"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
