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

type ApiStoryRecord = {
  id: number;
  status: string;
  story_key: string;
  cluster_title: string;
  summary: string;
  highlights: string[];
  source_links: string[];
  tags: string[];
  risk_flags: string[];
  score: number;
  item_count: number;
  first_seen_at: string;
  last_seen_at: string;
};

type ApiNormalizedItem = {
  raw_item_id: number | null;
  source_slug: string;
  source_priority: string;
  external_id: string;
  canonical_url: string;
  title: string;
  normalized_title: string;
  author: string | null;
  published_at: string;
  summary: string;
  content: string;
  language: string;
  tags: string[];
  keywords: string[];
  metadata: Record<string, unknown>;
};

type ApiArticleDraft = {
  id: number;
  target_date: string;
  title: string;
  summary: string;
  body: string;
  story_keys: string[];
  status: string;
  story_count: number;
  variant_count: number;
  created_at: string;
  updated_at: string;
};

type ApiPostVariant = {
  id: number;
  article_id: number;
  platform: string;
  content: string;
  updated_at: string;
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

/**
 * Story model consumed by the review console.
 */
export type StoryRecord = {
  id: number;
  status: string;
  storyKey: string;
  clusterTitle: string;
  summary: string;
  highlights: string[];
  sourceLinks: string[];
  tags: string[];
  riskFlags: string[];
  score: number;
  itemCount: number;
  firstSeenAt: string;
  lastSeenAt: string;
};

/**
 * Standardized item used to inspect normalization quality.
 */
export type NormalizedItemRecord = {
  rawItemId: number | null;
  sourceSlug: string;
  sourcePriority: string;
  externalId: string;
  canonicalUrl: string;
  title: string;
  normalizedTitle: string;
  author: string | null;
  publishedAt: string;
  summary: string;
  content: string;
  language: string;
  tags: string[];
  keywords: string[];
  metadata: Record<string, unknown>;
};

/**
 * Result returned by manual story pipeline rebuilds.
 */
export type PipelineRebuildResult = {
  normalizedItems: number;
  stories: number;
};

/**
 * Generated article draft persisted for review and publishing.
 */
export type ArticleDraftRecord = {
  id: number;
  targetDate: string;
  title: string;
  summary: string;
  body: string;
  storyKeys: string[];
  status: string;
  storyCount: number;
  variantCount: number;
  createdAt: string;
  updatedAt: string;
};

/**
 * Platform-specific post variant derived from a daily digest.
 */
export type PostVariantRecord = {
  id: number;
  articleId: number;
  platform: string;
  content: string;
  updatedAt: string;
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

function mapStoryRecord(apiStory: ApiStoryRecord): StoryRecord {
  return {
    id: apiStory.id,
    status: apiStory.status,
    storyKey: apiStory.story_key,
    clusterTitle: apiStory.cluster_title,
    summary: apiStory.summary,
    highlights: apiStory.highlights,
    sourceLinks: apiStory.source_links,
    tags: apiStory.tags,
    riskFlags: apiStory.risk_flags,
    score: apiStory.score,
    itemCount: apiStory.item_count,
    firstSeenAt: apiStory.first_seen_at,
    lastSeenAt: apiStory.last_seen_at,
  };
}

function mapNormalizedItem(apiItem: ApiNormalizedItem): NormalizedItemRecord {
  return {
    rawItemId: apiItem.raw_item_id,
    sourceSlug: apiItem.source_slug,
    sourcePriority: apiItem.source_priority,
    externalId: apiItem.external_id,
    canonicalUrl: apiItem.canonical_url,
    title: apiItem.title,
    normalizedTitle: apiItem.normalized_title,
    author: apiItem.author,
    publishedAt: apiItem.published_at,
    summary: apiItem.summary,
    content: apiItem.content,
    language: apiItem.language,
    tags: apiItem.tags,
    keywords: apiItem.keywords,
    metadata: apiItem.metadata,
  };
}

function mapArticleDraft(apiArticle: ApiArticleDraft): ArticleDraftRecord {
  return {
    id: apiArticle.id,
    targetDate: apiArticle.target_date,
    title: apiArticle.title,
    summary: apiArticle.summary,
    body: apiArticle.body,
    storyKeys: apiArticle.story_keys,
    status: apiArticle.status,
    storyCount: apiArticle.story_count,
    variantCount: apiArticle.variant_count,
    createdAt: apiArticle.created_at,
    updatedAt: apiArticle.updated_at,
  };
}

function mapPostVariant(apiVariant: ApiPostVariant): PostVariantRecord {
  return {
    id: apiVariant.id,
    articleId: apiVariant.article_id,
    platform: apiVariant.platform,
    content: apiVariant.content,
    updatedAt: apiVariant.updated_at,
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

/**
 * Loads clustered stories produced by the Phase 03 pipeline.
 */
export async function fetchStories(): Promise<StoryRecord[]> {
  const apiStories = await requestJson<ApiStoryRecord[]>("/stories");
  return apiStories.map(mapStoryRecord);
}

/**
 * Loads normalized items for inspecting URL cleanup and title normalization.
 */
export async function fetchNormalizedItems(limit = 12): Promise<NormalizedItemRecord[]> {
  const apiItems = await requestJson<ApiNormalizedItem[]>(`/normalized-items?limit=${limit}`);
  return apiItems.map(mapNormalizedItem);
}

/**
 * Re-runs the story pipeline against the current raw item set.
 */
export async function rebuildStoriesPipeline(): Promise<PipelineRebuildResult> {
  const payload = await requestJson<{ normalized_items: number; stories: number }>("/pipeline/stories/rebuild", {
    method: "POST",
  });
  return {
    normalizedItems: payload.normalized_items,
    stories: payload.stories,
  };
}

/**
 * Marks a story as approved for downstream digest generation.
 */
export function approveStory(storyId: number): Promise<{ id: number; status: string }> {
  return requestJson<{ id: number; status: string }>(`/stories/${storyId}/approve`, {
    method: "POST",
  });
}

/**
 * Loads generated article drafts for the Phase 04 draft center.
 */
export async function fetchArticleDrafts(): Promise<ArticleDraftRecord[]> {
  const apiArticles = await requestJson<ApiArticleDraft[]>("/articles");
  return apiArticles.map(mapArticleDraft);
}

/**
 * Generates or refreshes the daily digest for a given date.
 */
export async function generateDailyArticle(targetDate: string): Promise<ArticleDraftRecord> {
  const apiArticle = await requestJson<ApiArticleDraft>(`/articles/generate/daily?target_date=${targetDate}`, {
    method: "POST",
  });
  return mapArticleDraft(apiArticle);
}

/**
 * Loads platform-specific post variants for a generated article.
 */
export async function fetchArticleVariants(articleId: number): Promise<PostVariantRecord[]> {
  const apiVariants = await requestJson<ApiPostVariant[]>(`/articles/${articleId}/variants`);
  return apiVariants.map(mapPostVariant);
}