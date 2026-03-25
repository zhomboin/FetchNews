const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function fetchHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch(`${API_BASE}/healthz`);
  if (!response.ok) {
    throw new Error("Failed to fetch health status");
  }
  return response.json();
}
