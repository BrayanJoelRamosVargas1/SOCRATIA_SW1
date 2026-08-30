import { apiRequest } from "@/lib/api";
import type {
  Document,
  DocumentProcessingResult,
  ProcessingStatus,
  PresentationMaterial,
  QuestionBank,
} from "@/types/document";

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

export function getQuestionBank(documentId: string): Promise<QuestionBank> {
  return apiRequest<QuestionBank>(`/documents/${documentId}/questions`);
}

export function generateQuestionBank(documentId: string): Promise<QuestionBank> {
  return apiRequest<QuestionBank>(`/documents/${documentId}/questions/generate`, {
    method: "POST",
  });
}

export function getPresentationMaterial(documentId: string): Promise<PresentationMaterial> {
  return apiRequest<PresentationMaterial>(`/documents/${documentId}/presentation`);
}

export function generatePresentationMaterial(
  documentId: string,
  durationMinutes: number,
): Promise<PresentationMaterial> {
  return apiRequest<PresentationMaterial>(`/documents/${documentId}/presentation/generate`, {
    method: "POST",
    body: JSON.stringify({ duration_minutes: durationMinutes }),
  });
}

export function regeneratePresentationMaterial(
  documentId: string,
  durationMinutes: number,
): Promise<PresentationMaterial> {
  return apiRequest<PresentationMaterial>(`/documents/${documentId}/presentation/regenerate`, {
    method: "POST",
    body: JSON.stringify({ duration_minutes: durationMinutes }),
  });
}

export function deleteDocument(documentId: string): Promise<void> {
  return apiRequest<void>(`/documents/${documentId}`, { method: "DELETE" });
}

