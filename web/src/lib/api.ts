const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export type HealthResponse = {
  status: string;
  service: string;
};

export type SourceSpec = {
  slug: string;
  label: string;
  platform: string;
  priority: string;
  kind: string;
  enabled: boolean;
  config: Record<string, unknown>;
};

export type IngestRunError = {
  source_slug: string;
  message: string;
};

export type IngestRunRecord = {
  id: number;
  source_slugs: string[];
  status: string;
  sources_total: number;
  sources_succeeded: number;
  sources_failed: number;
  items_ingested: number;
  errors: IngestRunError[];
  started_at: string;
  finished_at: string | null;
};

export type IngestRunRequest = {
  source_slugs?: string[];
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/healthz");
}

export function fetchSourceSpecs(): Promise<SourceSpec[]> {
  return requestJson<SourceSpec[]>("/sources");
}

export function fetchIngestRuns(): Promise<IngestRunRecord[]> {
  return requestJson<IngestRunRecord[]>("/ingest/runs");
}

export function triggerIngestRun(payload: IngestRunRequest): Promise<IngestRunRecord> {
  return requestJson<IngestRunRecord>("/ingest/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
