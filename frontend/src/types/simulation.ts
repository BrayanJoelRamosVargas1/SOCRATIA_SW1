export type JuryProfile = {
  id: string;
  name: string;
  description: string;
  focus_type: "METHODOLOGICAL" | "TECHNICAL" | "CRITICAL";
  strictness: number;
  interruption_level: "LOW" | "MEDIUM" | "HIGH";
};

export type SimulationStatus = "DRAFT" | "READY" | "ACTIVE" | "COMPLETED" | "ABORTED" | "ERROR";
export type SimulationTurnState = "JURY_TURN" | "WAITING_STUDENT" | "PROCESSING";
export type SimulationSpeaker = "JURY" | "STUDENT" | "SYSTEM";
export type SimulationTurnType = "QUESTION" | "ANSWER" | "FOLLOW_UP" | "EVENT";

export type Simulation = {
  id: string;
  status: SimulationStatus;
  planned_duration_minutes: number;
  camera_ready: boolean;
  microphone_ready: boolean;
  vision_ready: boolean;
  question_count: number;
  document: { id: string; name: string };
  jury_profile: JuryProfile;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SessionQuestion = {
  id: string;
  position: number;
  text: string;
  source: "BANK" | "FOLLOW_UP";
};

export type SessionTurn = {
  id: string;
  sequence: number;
  speaker: SimulationSpeaker;
  turn_type: SimulationTurnType;
  simulation_question_id: string | null;
  question_source: "BANK" | "FOLLOW_UP" | null;
  content: string;
  created_at: string;
};

export type SessionSnapshot = {
  simulation_id: string;
  status: SimulationStatus;
  turn_state: SimulationTurnState;
  current_question: SessionQuestion | null;
  answered_questions: number;
  total_questions: number;
  last_sequence: number;
  questions_exhausted: boolean;
  started_at: string;
  transcript: SessionTurn[];
};
