"use client";

import { useRef, useState, type FormEvent } from "react";
import { apiRequest, ApiError } from "@/lib/api";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";

type SearchResult = {
  engine: string; model: string | null; degraded: boolean;
  matches: { fragment: number; excerpt: string }[];
};

export function DocumentSemanticSearch({ documentId }: { documentId: string }) {
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const locked = useRef(false);

  async function search(event: FormEvent) {
    event.preventDefault();
    if (locked.current || query.trim().length < 3) return;
    locked.current = true; setBusy(true); setError(""); setResult(null);
    try {
      setResult(await apiRequest<SearchResult>(`/documents/${documentId}/search`, {
        method: "POST", body: JSON.stringify({ query: query.trim() }),
      }));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "No pudimos realizar la búsqueda. Inténtalo nuevamente.");
    } finally { locked.current = false; setBusy(false); }
  }

  return <section className="question-bank-workspace" aria-labelledby="document-search-title">
    <header className="question-bank-header"><div>
      <p className="eyebrow">EXPLORA TU INVESTIGACIÓN</p>
      <h2 id="document-search-title">Encuentra ideas en tu documento</h2>
      <p>Escribe lo que necesitas encontrar, aunque no recuerdes las palabras exactas. Verás fragmentos del texto original.</p>
    </div></header>
    <form onSubmit={search} style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
      <label style={{ flex: "1 1 260px" }}>¿Qué quieres encontrar?
        <input value={query} onChange={e => setQuery(e.target.value)} minLength={3} maxLength={400}
          required placeholder="Por ejemplo: ¿cómo se comprobó que la propuesta funciona?"
          style={{ width: "100%", padding: "0.85rem", border: "1px solid #8aaba5", borderRadius: "12px", color: "#163239", background: "#fff" }} />
      </label>
      <button type="submit" className="button button-primary" disabled={busy || query.trim().length < 3}
        style={{ alignSelf: "end" }}>{busy ? "Buscando en el contenido…" : "Buscar ideas"}</button>
    </form>
    {busy && <LoadingSkeleton label="Buscando fragmentos relacionados" rows={2} />}
    {error && <p role="alert">{error}</p>}
    <div aria-live="polite">
      {result && <>
        <p>{result.engine === "qwen_local" ? "Qwen · IA propia en el servidor" : result.degraded ? "Búsqueda por palabras · modo alternativo" : "Búsqueda por significado"}</p>
        {result.degraded && <p>La búsqueda por significado no está disponible ahora. Estos resultados se basan en palabras coincidentes.</p>}
        {result.matches.length === 0 && <p>No encontramos fragmentos. Prueba una idea más específica de tu investigación.</p>}
        {result.matches.map(match => <article key={match.fragment} style={{ background: "#f1f8f6", color: "#163239", padding: "1rem", borderRadius: "12px", marginTop: "0.75rem" }}>
          <strong>Fragmento {match.fragment}</strong><p style={{ whiteSpace: "pre-wrap" }}>{match.excerpt}</p>
        </article>)}
      </>}
    </div>
  </section>;
}
