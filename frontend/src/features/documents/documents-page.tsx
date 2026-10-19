"use client";

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { DocumentIcon } from "@/components/ui/icons";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";
import { getCurrentUser } from "@/features/auth/api";
import { deleteDocument, listDocuments, uploadDocument } from "@/features/documents/api";
import { ApiError } from "@/lib/api";
import { documentStatusLabels } from "@/types/document";
import type { Document } from "@/types/document";
import type { User } from "@/types/user";


const MAX_FILE_SIZE = 10 * 1024 * 1024;

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
  const [uploadProgress,setUploadProgress]=useState(0);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getCurrentUser(), listDocuments()])
      .then(([currentUser, items]) => {
        setUser(currentUser);
        setDocuments(items);
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 401) router.replace("/login");
        else setError("No pudimos cargar esta sección. Revisa tu conexión e inténtalo de nuevo.");
      })
      .finally(() => setLoading(false));
  }, [router]);

  async function handleFile(file: File | undefined) {
    if (!file || uploading) return;
    setError("");
    const extension = file.name.toLowerCase().split(".").pop();
    if (!extension || !["pdf", "docx"].includes(extension)) {
      setError("Selecciona un archivo PDF o DOCX.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("El archivo supera el límite de 10 MB del piloto.");
      return;
    }
    setUploading(true);
    setUploadProgress(0);
    try {
      const document = await uploadDocument(file,setUploadProgress);
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

  return (
    <main className="dashboard-layout">
      <AppSidebar user={user} active="documents" />
      <section className="dashboard-content documents-content">
        {!user && error && <div className="workspace-notice" role="alert">{error} <button type="button" onClick={() => window.location.reload()}>Reintentar</button></div>}
        {(loading || !user) && !error ? (
          <LoadingSkeleton label="Preparando tus documentos…"/>
        ) : !user ? null : (
          <>
            <header className="dashboard-header documents-header">
          <div>
            <p className="eyebrow">TU INVESTIGACIÓN</p>
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
            <h2>{uploading ? uploadProgress<100 ? `Subiendo documento · ${uploadProgress}%` : "Transferencia completa · validando y guardando…" : "Arrastra tu PDF o DOCX"}</h2>
            <p>Validamos el tipo y guardamos el archivo de forma persistente. Máximo 10 MB en este piloto.</p>
            {uploading && <progress aria-label="Transferencia del documento" max={100} value={uploadProgress} style={{width:"100%"}}/>}
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
                  <span className={`document-status status-${document.status.toLowerCase()}`}><i />{documentStatusLabels[document.status]}</span>
                  <Link className="row-action" href={`/documents/${document.id}`}>Ver detalle →</Link>
                  <button className="row-delete" type="button" onClick={() => void remove(document)} aria-label={`Eliminar ${document.original_name}`}>Eliminar</button>
                </article>
              ))}
            </div>
          )}
        </section>
        </>
        )}
      </section>
    </main>
  );
}
