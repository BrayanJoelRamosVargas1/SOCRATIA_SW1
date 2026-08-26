"use client";

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { DocumentIcon } from "@/components/ui/icons";
import { getCurrentUser } from "@/features/auth/api";
import { deleteDocument, listDocuments, uploadDocument } from "@/features/documents/api";
import { ApiError } from "@/lib/api";
import type { Document } from "@/types/document";
import type { User } from "@/types/user";

const MAX_FILE_SIZE = 20 * 1024 * 1024;

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-BO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function DocumentsPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [user, setUser] = useState<User | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getCurrentUser(), listDocuments()])
      .then(([currentUser, items]) => {
        setUser(currentUser);
        setDocuments(items);
      })
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setError("");
    const extension = file.name.toLowerCase().split(".").pop();
    if (!extension || !["pdf", "docx"].includes(extension)) {
      setError("Selecciona un archivo PDF o DOCX.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("El archivo supera el límite de 20 MB.");
      return;
    }
    setUploading(true);
    try {
      const document = await uploadDocument(file);
      setDocuments((current) => [document, ...current]);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No pudimos cargar el documento.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function onInput(event: ChangeEvent<HTMLInputElement>) {
    void handleFile(event.target.files?.[0]);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    void handleFile(event.dataTransfer.files?.[0]);
  }

  async function remove(document: Document) {
    if (!window.confirm(`¿Eliminar “${document.original_name}”? Esta acción no se puede deshacer.`)) return;
    setError("");
    try {
      await deleteDocument(document.id);
      setDocuments((current) => current.filter((item) => item.id !== document.id));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No pudimos eliminar el documento.");
    }
  }

  if (loading || !user) {
    return <main className="loading-screen"><div className="loading-orbit" /><p>Cargando documentos…</p></main>;
  }

  return (
    <main className="dashboard-layout">
      <AppSidebar user={user} active="documents" />
      <section className="dashboard-content documents-content">
        <header className="dashboard-header documents-header">
          <div>
            <p className="eyebrow">P2 · Preparación</p>
            <h1>Mis documentos</h1>
            <p>Tu investigación empieza aquí. Sube el material que Socratia utilizará para prepararte.</p>
          </div>
          <span className="document-counter">{documents.length} {documents.length === 1 ? "documento" : "documentos"}</span>
        </header>

        <div
          className={`upload-zone ${dragging ? "dragging" : ""} ${uploading ? "uploading" : ""}`}
          onDragEnter={() => setDragging(true)}
          onDragLeave={() => setDragging(false)}
          onDragOver={(event) => event.preventDefault()}
          onDrop={onDrop}
        >
          <div className="upload-icon"><DocumentIcon /></div>
          <div>
            <h2>{uploading ? "Guardando tu documento…" : "Arrastra tu PDF o DOCX"}</h2>
            <p>Validamos el tipo y guardamos el archivo de forma persistente. Máximo 20 MB.</p>
          </div>
          <label className="button button-primary upload-button">
            {uploading ? "Cargando…" : "Seleccionar archivo"}
            <input ref={inputRef} type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={onInput} disabled={uploading} />
          </label>
        </div>

        {error && <p className="form-error document-error" role="alert">{error}</p>}

        <section className="documents-section">
          <div className="section-heading documents-section-heading">
            <div><p className="eyebrow">Biblioteca de preparación</p><h2>Archivos cargados</h2></div>
            <p>Los archivos pertenecen exclusivamente a tu cuenta.</p>
          </div>

          {documents.length === 0 ? (
            <div className="documents-empty">
              <span>01</span>
              <h3>Aún no hay documentos</h3>
              <p>Sube tu tesis, artículo o proyecto para construir tu futura base de preguntas.</p>
            </div>
          ) : (
            <div className="document-list">
              {documents.map((document) => (
                <article className="document-row" key={document.id}>
                  <Link className="document-main" href={`/documents/${document.id}`}>
                    <span className={`file-mark ${document.file_type.toLowerCase()}`}>{document.file_type}</span>
                    <span className="document-name"><strong>{document.original_name}</strong><small>{formatBytes(document.file_size)} · {formatDate(document.created_at)}</small></span>
                  </Link>
                  <span className={`document-status status-${document.status.toLowerCase()}`}><i />{document.status === "UPLOADED" ? "Cargado" : document.status}</span>
                  <Link className="row-action" href={`/documents/${document.id}`}>Ver detalle →</Link>
                  <button className="row-delete" type="button" onClick={() => void remove(document)} aria-label={`Eliminar ${document.original_name}`}>Eliminar</button>
                </article>
              ))}
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
