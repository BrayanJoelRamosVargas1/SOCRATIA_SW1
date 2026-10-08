export type TurnClassification = "PRECISE" | "INCOMPLETE" | "CONTRADICTORY";

export type ReportQuestionDetail = {
  question: string;
  answer: string;
  classification: TurnClassification | null;
  turn_score: number | null;
  strengths: string[];
  weaknesses: string[];
  missing_points: string[];
  contradictions: string[];
  evidence: string[];
  time_taken_seconds: number | null;
  filler_words_count: number | null;
  eye_contact_score: number | null;
};

export type ScoreAvailability = {
  content: boolean;
  communication: boolean;
  nonverbal: boolean;
};

export type SimulationReportResponse = {
  simulation_id: string;
  document_title: string;
  date: string;
  duration_minutes: number | null;
  overall_score: number | null;
  content_score: number | null;
  communication_score: number | null;
  nonverbal_score: number | null;
  evaluation_version: string | null;
  availability: ScoreAvailability;
  questions: ReportQuestionDetail[];
};
