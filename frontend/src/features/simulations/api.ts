import { apiRequest } from "@/lib/api";
import type { JuryProfile, SessionSnapshot, Simulation } from "@/types/simulation";

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

export function startSimulation(id: string): Promise<SessionSnapshot> {
  return apiRequest<SessionSnapshot>(`/simulations/${id}/start`, { method: "POST" });
}

export function getSimulationSession(id: string): Promise<SessionSnapshot> {
  return apiRequest<SessionSnapshot>(`/simulations/${id}/session`);
}

import { SimulationReportResponse } from "@/types/report";

export function evaluateSimulation(id: string): Promise<unknown> {
  return apiRequest<unknown>(`/simulations/${id}/evaluate`, { method: 'POST' });
}

export function getSimulationReport(id: string): Promise<SimulationReportResponse> {
  return apiRequest<SimulationReportResponse>(`/simulations/${id}/report`);
}

export function getEvaluation(id: string): Promise<{status: string}> {
  return apiRequest<{status: string}>(`/simulations/${id}/evaluation`);
}

