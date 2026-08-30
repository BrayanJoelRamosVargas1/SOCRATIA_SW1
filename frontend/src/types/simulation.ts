export type JuryProfile = {
  id: string;
  name: string;
  description: string;
  focus_type: "METHODOLOGICAL" | "TECHNICAL" | "CRITICAL";
  strictness: number;
  interruption_level: "LOW" | "MEDIUM" | "HIGH";
};

export type SimulationStatus = "DRAFT" | "READY" | "ACTIVE" | "COMPLETED" | "ABORTED" | "ERROR";

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
