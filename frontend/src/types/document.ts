export type DocumentStatus = "UPLOADED" | "PROCESSING" | "PROCESSED" | "ERROR";

export type Document = {
  id: string;
  original_name: string;
  file_type: "PDF" | "DOCX";
  file_size: number;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
};

export type ProcessingStep = {
  id: string;
  status: DocumentStatus;
  stage: string;
  started_at: string;
  finished_at: string | null;
  error_message: string | null;
};

export type ProcessingStatus = {
  document_id: string;
  status: DocumentStatus;
  chunk_count: number;
  history: ProcessingStep[];
};

export type DocumentProcessingResult = {
  document_id: string;
  status: DocumentStatus;
  chunk_count: number;
  embedding_model: string;
  embedding_dimensions: number;
};

