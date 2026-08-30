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

export type QuestionCategory = "CONCEPTUAL" | "METHODOLOGICAL" | "TECHNICAL" | "CRITICAL";
export type QuestionDifficulty = "MEDIUM" | "HARD";

export type Question = {
  id: string;
  question: string;
  category: QuestionCategory;
  difficulty: QuestionDifficulty;
};

export type QuestionBank = {
  id: string;
  document_id: string;
  status: "READY";
  provider_used: string;
  model_used: string;
  fallback_used: boolean;
  latency_ms: number | null;
  created_at: string;
  updated_at: string;
  questions: Question[];
};

export type PresentationSlide = {
  id: string;
  position: number;
  title: string;
  objective: string;
  bullet_points: string[];
  speaker_notes: string;
  estimated_seconds: number;
};

export type PresentationMaterial = {
  id: string;
  document_id: string;
  title: string;
  duration_minutes: number;
  target_word_count: number;
  status: "READY";
  provider_used: string;
  model_used: string;
  fallback_used: boolean;
  latency_ms: number | null;
  created_at: string;
  updated_at: string;
  slides: PresentationSlide[];
};

