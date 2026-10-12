"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

interface AISettings {
  jury_provider: string;
  jury_model: string;
  jury_temperature: number;
  jury_max_tokens: number;
  max_followups: number;
  retrieval_top_k: number;
  evaluation_provider: string;
  evaluation_model: string;
  evaluation_temperature: number;
  fallback_enabled: boolean;
  config_version: number;
  updated_at: string | null;
  updated_by: string | null;
}

interface AIProviderOption {
  id: string;
  name: string;
  models: string[];
  is_configured: boolean;
}

interface AIRangeLimit {
  min: number;
  max: number;
  step?: number;
}

interface AIOptionsResponse {
  providers: AIProviderOption[];
  limits: Record<string, AIRangeLimit>;
}

export default function AdminAISettingsPage() {
  const [settings, setSettings] = useState<AISettings | null>(null);
  const [options, setOptions] = useState<AIOptionsResponse | null>(null);
  const [form, setForm] = useState<AISettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [settingsData, optionsData] = await Promise.all([
        apiRequest<AISettings>("/admin/ai-settings"),
        apiRequest<AIOptionsResponse>("/admin/ai-settings/options"),
      ]);
      setSettings(settingsData);
      setForm(settingsData);
      setOptions(optionsData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cargar la configuración de IA";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData();
  }, []);

  const handleJuryProviderChange = (providerId: string) => {
    if (!form || !options) return;
    const provider = options.providers.find((p) => p.id === providerId);
    const defaultModel = provider && provider.models.length > 0 ? provider.models[0] : "";
    setForm({
      ...form,
      jury_provider: providerId,
      jury_model: defaultModel,
    });
  };

  const handleEvaluationProviderChange = (providerId: string) => {
    if (!form || !options) return;
    const provider = options.providers.find((p) => p.id === providerId);
    const defaultModel = provider && provider.models.length > 0 ? provider.models[0] : "";
    setForm({
      ...form,
      evaluation_provider: providerId,
      evaluation_model: defaultModel,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;

    if (form.retrieval_top_k < 1 || form.retrieval_top_k > 20) {
      setError("Top-K de recuperación debe estar entre 1 y 20");
      return;
    }
    if (form.jury_temperature < 0.0 || form.jury_temperature > 1.0) {
      setError("La temperatura del jurado debe estar entre 0.0 y 1.0");
      return;
    }
    if (form.evaluation_temperature < 0.0 || form.evaluation_temperature > 1.0) {
      setError("La temperatura de evaluación debe estar entre 0.0 y 1.0");
      return;
    }
    if (form.jury_max_tokens < 256 || form.jury_max_tokens > 4096) {
      setError("Los tokens máximos del jurado deben estar entre 256 y 4096");
      return;
    }
    if (form.max_followups < 0 || form.max_followups > 5) {
      setError("El límite de preguntas de seguimiento debe estar entre 0 y 5");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      const payload = {
        jury_provider: form.jury_provider,
        jury_model: form.jury_model,
        jury_temperature: Number(form.jury_temperature),
        jury_max_tokens: Number(form.jury_max_tokens),
        max_followups: Number(form.max_followups),
        retrieval_top_k: Number(form.retrieval_top_k),
        evaluation_provider: form.evaluation_provider,
        evaluation_model: form.evaluation_model,
        evaluation_temperature: Number(form.evaluation_temperature),
        fallback_enabled: Boolean(form.fallback_enabled),
      };

      const updated = await apiRequest<AISettings>("/admin/ai-settings", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });

      setSettings(updated);
      setForm(updated);
      setSuccessMessage(`Configuración guardada exitosamente. Versión activa: v${updated.config_version}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al actualizar la configuración";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const getModelsForProvider = (providerId: string): string[] => {
    if (!options) return [];
    const found = options.providers.find((p) => p.id === providerId);
    return found ? found.models : [];
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-8 text-center text-gray-500">
        <p className="text-lg">Cargando parámetros de Inteligencia Artificial...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Navigation Links */}
      <nav className="flex flex-wrap gap-4 text-sm font-medium mb-6 pb-4 border-b">
        <Link href="/admin/dashboard" className="text-gray-600 hover:text-blue-600">
          Supervisión
        </Link>
        <Link href="/admin/users" className="text-gray-600 hover:text-blue-600">
          Usuarios
        </Link>
        <Link href="/admin/jury-profiles" className="text-gray-600 hover:text-blue-600">
          Perfiles de Jurado
        </Link>
        <Link href="/admin/plans" className="text-gray-600 hover:text-blue-600">
          Planes SaaS
        </Link>
        <Link href="/admin/subscriptions" className="text-gray-600 hover:text-blue-600">
          Suscripciones
        </Link>
        <span className="text-blue-600 font-bold">Parámetros de IA</span>
      </nav>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Parámetros de Inteligencia Artificial</h1>
          <p className="text-gray-600 mt-1">
            Gestión en tiempo de ejecución de proveedores de lenguaje, jurado socrático, recuperación RAG y evaluación.
          </p>
        </div>
        {settings && (
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
              Versión Activa: v{settings.config_version}
            </span>
            {settings.updated_at && (
              <span className="text-xs text-gray-500">
                Última mod: {new Date(settings.updated_at).toLocaleString()}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Status Cards: Providers */}
      {options && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {options.providers.map((prov) => (
            <div
              key={prov.id}
              className="bg-white border rounded-lg p-4 flex items-center justify-between shadow-sm"
            >
              <div>
                <h3 className="font-semibold text-gray-800">{prov.name}</h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Modelos compatibles: {prov.models.length}
                </p>
              </div>
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                  prov.is_configured
                    ? "bg-green-100 text-green-800 border border-green-200"
                    : "bg-amber-100 text-amber-800 border border-amber-200"
                }`}
              >
                {prov.is_configured ? "API Key Configurada" : "Sin Clave Configurada"}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Notifications */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-6 text-sm">
          {successMessage}
        </div>
      )}

      {/* Main Settings Form */}
      {form && (
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section 1: Jurado Virtual */}
          <div className="bg-white border rounded-xl p-6 shadow-sm">
            <div className="border-b pb-3 mb-6">
              <h2 className="text-xl font-semibold text-gray-800">1. Jurado Virtual (Live Socratic Jury)</h2>
              <p className="text-xs text-gray-500 mt-1">
                Controla la inferencia en tiempo real para el enrutamiento de preguntas y réplicas del jurado.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Proveedor Principal del Jurado
                </label>
                <select
                  value={form.jury_provider}
                  onChange={(e) => handleJuryProviderChange(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-blue-500"
                >
                  {options?.providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Modelo del Jurado
                </label>
                <select
                  value={form.jury_model}
                  onChange={(e) => setForm({ ...form, jury_model: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-blue-500"
                >
                  {getModelsForProvider(form.jury_provider).map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-sm font-medium text-gray-700">
                    Temperatura del Jurado
                  </label>
                  <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                    {Number(form.jury_temperature).toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={form.jury_temperature}
                  onChange={(e) =>
                    setForm({ ...form, jury_temperature: parseFloat(e.target.value) })
                  }
                  className="w-full cursor-pointer accent-blue-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>0.0 (Determinista)</span>
                  <span>1.0 (Creativo)</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tokens Máximos de Salida (Max Tokens)
                </label>
                <input
                  type="number"
                  min="256"
                  max="4096"
                  step="128"
                  value={form.jury_max_tokens}
                  onChange={(e) =>
                    setForm({ ...form, jury_max_tokens: parseInt(e.target.value) || 2048 })
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-xs text-gray-400 mt-1 block">Rango permitido: 256 a 4096 tokens</span>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Máximo de Preguntas de Seguimiento (Follow-ups)
                </label>
                <input
                  type="number"
                  min="0"
                  max="5"
                  value={form.max_followups}
                  onChange={(e) =>
                    setForm({ ...form, max_followups: parseInt(e.target.value) || 0 })
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-xs text-gray-400 mt-1 block">
                  Límite estricto de réplicas consecutivas por pregunta (0 a 5).
                </span>
              </div>
            </div>
          </div>

          {/* Section 2: Recuperación & RAG */}
          <div className="bg-white border rounded-xl p-6 shadow-sm">
            <div className="border-b pb-3 mb-6">
              <h2 className="text-xl font-semibold text-gray-800">2. Recuperación & RAG (Retrieval-Augmented Generation)</h2>
              <p className="text-xs text-gray-500 mt-1">
                Ajuste del volumen de contexto recuperado desde la base vectorial para bancos de preguntas y presentaciones.
              </p>
            </div>

            <div className="max-w-md">
              <div className="flex justify-between items-center mb-1">
                <label className="text-sm font-medium text-gray-700">
                  Top-K Chunks Recuperados
                </label>
                <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                  {form.retrieval_top_k} fragmentos
                </span>
              </div>
              <input
                type="number"
                min="1"
                max="20"
                value={form.retrieval_top_k}
                onChange={(e) =>
                  setForm({ ...form, retrieval_top_k: parseInt(e.target.value) || 1 })
                }
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-xs text-gray-400 mt-1 block">
                Valores típicos: 3 a 6 fragmentos. Un valor muy alto puede saturar la ventana de contexto.
              </span>
            </div>
          </div>

          {/* Section 3: Evaluación */}
          <div className="bg-white border rounded-xl p-6 shadow-sm">
            <div className="border-b pb-3 mb-6">
              <h2 className="text-xl font-semibold text-gray-800">3. Motor Evaluador (Post-Simulation Evaluator)</h2>
              <p className="text-xs text-gray-500 mt-1">
                Configuración del modelo estructurado encargado de evaluar las intervenciones y clasificar el desempeño.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Proveedor de Evaluación
                </label>
                <select
                  value={form.evaluation_provider}
                  onChange={(e) => handleEvaluationProviderChange(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-blue-500"
                >
                  {options?.providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Modelo de Evaluación
                </label>
                <select
                  value={form.evaluation_model}
                  onChange={(e) => setForm({ ...form, evaluation_model: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-blue-500"
                >
                  {getModelsForProvider(form.evaluation_provider).map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-sm font-medium text-gray-700">
                    Temperatura de Evaluación
                  </label>
                  <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                    {Number(form.evaluation_temperature).toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={form.evaluation_temperature}
                  onChange={(e) =>
                    setForm({ ...form, evaluation_temperature: parseFloat(e.target.value) })
                  }
                  className="w-full cursor-pointer accent-blue-600"
                />
                <span className="text-xs text-gray-400 mt-1 block">
                  Recomendado 0.0 para garantizar reproducibilidad en las calificaciones.
                </span>
              </div>
            </div>
          </div>

          {/* Section 4: Resiliencia y Fallback */}
          <div className="bg-white border rounded-xl p-6 shadow-sm">
            <div className="border-b pb-3 mb-6">
              <h2 className="text-xl font-semibold text-gray-800">4. Resiliencia y Conmutación por Error (Fallback)</h2>
              <p className="text-xs text-gray-500 mt-1">
                Políticas de continuidad del servicio ante fallos transitorios o límites de tasa de los proveedores.
              </p>
            </div>

            <div className="flex items-start gap-4">
              <input
                id="fallback_toggle"
                type="checkbox"
                checked={form.fallback_enabled}
                onChange={(e) => setForm({ ...form, fallback_enabled: e.target.checked })}
                className="mt-1 h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
              />
              <label htmlFor="fallback_toggle" className="cursor-pointer">
                <span className="text-sm font-semibold text-gray-800 block">
                  Habilitar Proveedor de Respaldo Secundario (Fallback Activo)
                </span>
                <span className="text-xs text-gray-500 block mt-1">
                  Si ocurre un error de red o timeout en el proveedor principal (o si el Circuit Breaker se abre),
                  la solicitud se derivará automáticamente al proveedor secundario sin interrumpir la simulación del estudiante.
                </span>
              </label>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-4 pt-4">
            <button
              type="button"
              onClick={fetchData}
              disabled={saving}
              className="px-5 py-2.5 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
            >
              Descartar Cambios
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium shadow-sm transition disabled:opacity-50 flex items-center gap-2"
            >
              {saving ? (
                <>
                  <span className="inline-block animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  Guardando en tiempo real...
                </>
              ) : (
                "Guardar Parámetros de IA"
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
