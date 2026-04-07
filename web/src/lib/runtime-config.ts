export const DEFAULT_API_BASE = "http://localhost:8000";

export function getApiBase(): string {
  return import.meta.env.VITE_API_BASE ?? DEFAULT_API_BASE;
}
