import { apiRequest } from "@/lib/api";
import type { JuryProfile, Simulation } from "@/types/simulation";

export function listJuryProfiles(): Promise<JuryProfile[]> {
  return apiRequest<JuryProfile[]>("/jury-profiles");
}

export function listSimulations(): Promise<Simulation[]> {
  return apiRequest<Simulation[]>("/simulations");
}

export function getSimulation(id: string): Promise<Simulation> {
  return apiRequest<Simulation>(`/simulations/${id}`);
}

export function createSimulation(input: {
  document_id: string;
  jury_profile_id: string;
  planned_duration_minutes: number;
}): Promise<Simulation> {
  return apiRequest<Simulation>("/simulations", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function saveCalibration(
  id: string,
  readiness: { camera_ready: boolean; microphone_ready: boolean; vision_ready: boolean },
): Promise<Simulation> {
  return apiRequest<Simulation>(`/simulations/${id}/calibration`, {
    method: "PUT",
    body: JSON.stringify(readiness),
  });
}

export function deleteSimulation(id: string): Promise<void> {
  return apiRequest<void>(`/simulations/${id}`, { method: "DELETE" });
}
