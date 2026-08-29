import { apiRequest } from "@/lib/api";
import type { Document, DocumentProcessingResult, ProcessingStatus } from "@/types/document";

export function listDocuments(): Promise<Document[]> {
  return apiRequest<Document[]>("/documents");
}

export function getDocument(documentId: string): Promise<Document> {
  return apiRequest<Document>(`/documents/${documentId}`);
}

export function getDocumentStatus(documentId: string): Promise<ProcessingStatus> {
  return apiRequest<ProcessingStatus>(`/documents/${documentId}/status`);
}

export function uploadDocument(file: File): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<Document>("/documents", { method: "POST", body: form });
}

export function processDocument(documentId: string): Promise<DocumentProcessingResult> {
  return apiRequest<DocumentProcessingResult>(`/documents/${documentId}/process`, {
    method: "POST",
  });
}

export function deleteDocument(documentId: string): Promise<void> {
  return apiRequest<void>(`/documents/${documentId}`, { method: "DELETE" });
}

