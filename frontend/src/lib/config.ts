export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export function simulationWebSocketUrl(simulationId: string): string {
  const url = new URL(API_URL, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `${url.pathname.replace(/\/$/, "")}/ws/simulations/${simulationId}`;
  url.search = "";
  return url.toString();
}
