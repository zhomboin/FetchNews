const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

type ApiIngestRunError = {
  source_slug: string;
  message: string;
};

type ApiIngestRunRecord = {
  id: number;
  source_slugs: string[];
  status: string;
  sources_total: number;
  sources_succeeded: number;
  sources_failed: number;
  items_ingested: number;
  errors: ApiIngestRunError[];
  started_at: string;
  finished_at: string | null;
};

type ApiIngestRunRequest = {
  source_slugs?: string[];
};

/**
 * Minimal health payload returned by the backend.
 */
export type HealthResponse = {
  status: string;
  service: string;
};

/**
 * Enabled source definition shown in the ingestion console.
 */
export type SourceSpec = {
  slug: string;
  label: string;
  platform: string;
  priority: string;
  kind: string;
  enabled: boolean;
  config: Record<string, unknown>;
};

/**
 * Frontend-friendly representation of a single source failure.
 */
export type IngestRunError = {
  sourceSlug: string;
  message: string;
};

/**
 * Normalized ingest run model consumed by React views.
 */
export type IngestRunRecord = {
  id: number;
  sourceSlugs: string[];
  status: string;
  sourcesTotal: number;
  sourcesSucceeded: number;
  sourcesFailed: number;
  itemsIngested: number;
  errors: IngestRunError[];
  startedAt: string;
  finishedAt: string | null;
};

/**
 * Request payload used by the frontend when manually starting ingestion.
 */
export type IngestRunRequest = {
  sourceSlugs?: string[];
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function mapIngestRunError(apiError: ApiIngestRunError): IngestRunError {
  return {
    sourceSlug: apiError.source_slug,
    message: apiError.message,
  };
}

function mapIngestRunRecord(apiRun: ApiIngestRunRecord): IngestRunRecord {
  return {
    id: apiRun.id,
    sourceSlugs: apiRun.source_slugs,
    status: apiRun.status,
    sourcesTotal: apiRun.sources_total,
    sourcesSucceeded: apiRun.sources_succeeded,
    sourcesFailed: apiRun.sources_failed,
    itemsIngested: apiRun.items_ingested,
    errors: apiRun.errors.map(mapIngestRunError),
    startedAt: apiRun.started_at,
    finishedAt: apiRun.finished_at,
  };
}

/**
 * Returns the backend health marker used by the shell status pill.
 */
export function fetchHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/healthz");
}

/**
 * Loads the enabled source catalog for manual ingestion.
 */
export function fetchSourceSpecs(): Promise<SourceSpec[]> {
  return requestJson<SourceSpec[]>("/sources");
}

/**
 * Loads recent ingest runs and maps backend snake_case fields to camelCase.
 */
export async function fetchIngestRuns(): Promise<IngestRunRecord[]> {
  const apiRuns = await requestJson<ApiIngestRunRecord[]>("/ingest/runs");
  return apiRuns.map(mapIngestRunRecord);
}

/**
 * Starts a new ingest run for the selected sources.
 */
export async function triggerIngestRun(payload: IngestRunRequest): Promise<IngestRunRecord> {
  const apiPayload: ApiIngestRunRequest = {
    source_slugs: payload.sourceSlugs,
  };
  const apiRun = await requestJson<ApiIngestRunRecord>("/ingest/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(apiPayload),
  });

  return mapIngestRunRecord(apiRun);
}