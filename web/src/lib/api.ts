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
  primary_section: string;
  sections: string[];
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
  period_type: string;
  target_date: string;
  title: string;
  summary: string;
  body: string;
  story_ids: number[];
  story_keys: string[];
  sections: string[];
  generation_note: string | null;
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

type ApiPublishJob = {
  id: number;
  article_id: number;
  platform: string;
  scheduled_for: string;
  status: string;
  retries: number;
  external_id: string | null;
  error_message: string | null;
  provider_job_id: string | null;
  updated_at: string;
};

type ApiPublishDispatchResult = {
  jobs_dispatched: number;
  jobs_failed: number;
};

type ApiPublishPollResult = {
  jobs_polled: number;
  jobs_completed: number;
  jobs_failed: number;
};

type ApiFailureGroup = {
  category: string;
  reason: string;
  count: number;
  targets: string[];
  suggestion: string;
};

type ApiPublishPlatformMetric = {
  platform: string;
  total_jobs: number;
  scheduled_jobs: number;
  published_jobs: number;
  failed_jobs: number;
  success_rate: number;
  last_error: string | null;
};

type ApiOpsSummary = {
  ingest_runs_total: number;
  ingest_runs_failed: number;
  items_ingested_total: number;
  stories_total: number;
  stories_approved: number;
  stories_pending: number;
  articles_total: number;
  articles_ready: number;
  articles_published: number;
  articles_failed: number;
  publish_jobs_total: number;
  publish_jobs_scheduled: number;
  publish_jobs_published: number;
  publish_jobs_failed: number;
  publish_success_rate: number;
  due_publish_jobs: number;
  recent_failure_groups: ApiFailureGroup[];
  publish_platform_metrics: ApiPublishPlatformMetric[];
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
  primarySection: string;
  sections: string[];
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
 * Supported digest periods in the review console.
 */
export type ArticlePeriodType = "daily" | "weekly" | "monthly";

/**
 * Generated article draft persisted for review and publishing.
 */
export type ArticleDraftRecord = {
  id: number;
  periodType: ArticlePeriodType;
  targetDate: string;
  title: string;
  summary: string;
  body: string;
  storyIds: number[];
  storyKeys: string[];
  sections: string[];
  generationNote: string | null;
  status: string;
  storyCount: number;
  variantCount: number;
  createdAt: string;
  updatedAt: string;
};

/**
 * Platform-specific post variant derived from a digest.
 */
export type PostVariantRecord = {
  id: number;
  articleId: number;
  platform: string;
  content: string;
  updatedAt: string;
};

/**
 * Request payload for article generation.
 */
export type GenerateArticlePayload = {
  targetDate: string;
  storyIds?: number[];
  generationNote?: string;
};

/**
 * Publish job model used by the draft center.
 */
export type PublishJobRecord = {
  id: number;
  articleId: number;
  platform: string;
  scheduledFor: string;
  status: string;
  retries: number;
  externalId: string | null;
  errorMessage: string | null;
  providerJobId: string | null;
  updatedAt: string;
};

/**
 * Request payload for creating publish jobs.
 */
export type PublishArticlePayload = {
  platforms: string[];
  scheduledFor: string;
};

/**
 * Manual writeback payload used to record publish results from the draft center.
 */
export type PublishJobResultPayload = {
  status: "published" | "failed";
  externalId?: string;
  errorMessage?: string;
};

/**
 * Summary returned by the due publish dispatcher.
 */
export type PublishDispatchResult = {
  jobsDispatched: number;
  jobsFailed: number;
};

/**
 * Summary returned by the publish polling endpoint.
 */
export type PublishPollResult = {
  jobsPolled: number;
  jobsCompleted: number;
  jobsFailed: number;
};

/**
 * Aggregated recent failure causes used in the operations dashboard.
 */
export type FailureGroupRecord = {
  category: string;
  reason: string;
  count: number;
  targets: string[];
  suggestion: string;
};

/**
 * Per-platform publishing metrics used by the ops dashboard.
 */
export type PublishPlatformMetricRecord = {
  platform: string;
  totalJobs: number;
  scheduledJobs: number;
  publishedJobs: number;
  failedJobs: number;
  successRate: number;
  lastError: string | null;
};

/**
 * Aggregated operations metrics used by the real dashboard.
 */
export type OpsSummaryRecord = {
  ingestRunsTotal: number;
  ingestRunsFailed: number;
  itemsIngestedTotal: number;
  storiesTotal: number;
  storiesApproved: number;
  storiesPending: number;
  articlesTotal: number;
  articlesReady: number;
  articlesPublished: number;
  articlesFailed: number;
  publishJobsTotal: number;
  publishJobsScheduled: number;
  publishJobsPublished: number;
  publishJobsFailed: number;
  publishSuccessRate: number;
  duePublishJobs: number;
  recentFailureGroups: FailureGroupRecord[];
  publishPlatformMetrics: PublishPlatformMetricRecord[];
};

/**
 * Canonical section labels used across stories and digests.
 */
export const SECTION_LABELS: Record<string, string> = {
  model_release: "模型发布",
  open_source: "开源项目",
  research: "论文精选",
  agents: "Agent 工作流",
  infrastructure: "基础设施",
  product_updates: "产品动态",
  community: "社区热议",
};

/**
 * Maps backend section slugs into human-readable labels.
 */
export function formatSectionLabel(sectionSlug: string): string {
  return SECTION_LABELS[sectionSlug] ?? sectionSlug.replace(/_/g, " ");
}

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
    primarySection: apiStory.primary_section,
    sections: apiStory.sections,
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
    periodType: apiArticle.period_type as ArticlePeriodType,
    targetDate: apiArticle.target_date,
    title: apiArticle.title,
    summary: apiArticle.summary,
    body: apiArticle.body,
    storyIds: apiArticle.story_ids,
    storyKeys: apiArticle.story_keys,
    sections: apiArticle.sections,
    generationNote: apiArticle.generation_note,
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

function mapPublishJob(apiJob: ApiPublishJob): PublishJobRecord {
  return {
    id: apiJob.id,
    articleId: apiJob.article_id,
    platform: apiJob.platform,
    scheduledFor: apiJob.scheduled_for,
    status: apiJob.status,
    retries: apiJob.retries,
    externalId: apiJob.external_id,
    errorMessage: apiJob.error_message,
    providerJobId: apiJob.provider_job_id,
    updatedAt: apiJob.updated_at,
  };
}

function mapPublishDispatchResult(apiResult: ApiPublishDispatchResult): PublishDispatchResult {
  return {
    jobsDispatched: apiResult.jobs_dispatched,
    jobsFailed: apiResult.jobs_failed,
  };
}

function mapPublishPollResult(apiResult: ApiPublishPollResult): PublishPollResult {
  return {
    jobsPolled: apiResult.jobs_polled,
    jobsCompleted: apiResult.jobs_completed,
    jobsFailed: apiResult.jobs_failed,
  };
}

function mapFailureGroup(apiGroup: ApiFailureGroup): FailureGroupRecord {
  return {
    category: apiGroup.category,
    reason: apiGroup.reason,
    count: apiGroup.count,
    targets: apiGroup.targets,
    suggestion: apiGroup.suggestion,
  };
}

function mapPublishPlatformMetric(apiMetric: ApiPublishPlatformMetric): PublishPlatformMetricRecord {
  return {
    platform: apiMetric.platform,
    totalJobs: apiMetric.total_jobs,
    scheduledJobs: apiMetric.scheduled_jobs,
    publishedJobs: apiMetric.published_jobs,
    failedJobs: apiMetric.failed_jobs,
    successRate: apiMetric.success_rate,
    lastError: apiMetric.last_error,
  };
}

function mapOpsSummary(apiSummary: ApiOpsSummary): OpsSummaryRecord {
  return {
    ingestRunsTotal: apiSummary.ingest_runs_total,
    ingestRunsFailed: apiSummary.ingest_runs_failed,
    itemsIngestedTotal: apiSummary.items_ingested_total,
    storiesTotal: apiSummary.stories_total,
    storiesApproved: apiSummary.stories_approved,
    storiesPending: apiSummary.stories_pending,
    articlesTotal: apiSummary.articles_total,
    articlesReady: apiSummary.articles_ready,
    articlesPublished: apiSummary.articles_published,
    articlesFailed: apiSummary.articles_failed,
    publishJobsTotal: apiSummary.publish_jobs_total,
    publishJobsScheduled: apiSummary.publish_jobs_scheduled,
    publishJobsPublished: apiSummary.publish_jobs_published,
    publishJobsFailed: apiSummary.publish_jobs_failed,
    publishSuccessRate: apiSummary.publish_success_rate,
    duePublishJobs: apiSummary.due_publish_jobs,
    recentFailureGroups: apiSummary.recent_failure_groups.map(mapFailureGroup),
    publishPlatformMetrics: apiSummary.publish_platform_metrics.map(mapPublishPlatformMetric),
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
 * Loads generated article drafts for the draft center.
 */
export async function fetchArticleDrafts(): Promise<ArticleDraftRecord[]> {
  const apiArticles = await requestJson<ApiArticleDraft[]>("/articles");
  return apiArticles.map(mapArticleDraft);
}

async function generateArticle(path: string, payload: GenerateArticlePayload): Promise<ArticleDraftRecord> {
  const apiArticle = await requestJson<ApiArticleDraft>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      target_date: payload.targetDate,
      story_ids: payload.storyIds,
      generation_note: payload.generationNote,
    }),
  });
  return mapArticleDraft(apiArticle);
}

/**
 * Generates or refreshes the daily digest for a given date and story scope.
 */
export function generateDailyArticle(payload: GenerateArticlePayload): Promise<ArticleDraftRecord> {
  return generateArticle("/articles/generate/daily", payload);
}

/**
 * Generates or refreshes the weekly digest for a given date and story scope.
 */
export function generateWeeklyArticle(payload: GenerateArticlePayload): Promise<ArticleDraftRecord> {
  return generateArticle("/articles/generate/weekly", payload);
}

/**
 * Generates or refreshes the monthly digest for a given date and story scope.
 */
export function generateMonthlyArticle(payload: GenerateArticlePayload): Promise<ArticleDraftRecord> {
  return generateArticle("/articles/generate/monthly", payload);
}

/**
 * Loads platform-specific post variants for a generated article.
 */
export async function fetchArticleVariants(articleId: number): Promise<PostVariantRecord[]> {
  const apiVariants = await requestJson<ApiPostVariant[]>(`/articles/${articleId}/variants`);
  return apiVariants.map(mapPostVariant);
}

/**
 * Loads publish jobs created for article review and scheduling.
 */
export async function fetchPublishJobs(): Promise<PublishJobRecord[]> {
  const apiJobs = await requestJson<ApiPublishJob[]>("/publish-jobs");
  return apiJobs.map(mapPublishJob);
}

/**
 * Creates publish jobs for the selected article and platforms.
 */
export async function publishArticle(articleId: number, payload: PublishArticlePayload): Promise<PublishJobRecord[]> {
  const response = await requestJson<{ jobs: ApiPublishJob[] }>(`/articles/${articleId}/publish`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      platforms: payload.platforms,
      scheduled_for: payload.scheduledFor,
    }),
  });
  return response.jobs.map(mapPublishJob);
}

/**
 * Writes a publish result back to the backend so article status can be recalculated.
 */
export async function writePublishJobResult(
  jobId: number,
  payload: PublishJobResultPayload,
): Promise<PublishJobRecord> {
  const apiJob = await requestJson<ApiPublishJob>(`/publish-jobs/${jobId}/result`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      status: payload.status,
      external_id: payload.externalId,
      error_message: payload.errorMessage,
    }),
  });
  return mapPublishJob(apiJob);
}

/**
 * Re-queues a failed publish job and clears its previous result payload.
 */
export async function retryPublishJob(jobId: number): Promise<PublishJobRecord> {
  const apiJob = await requestJson<ApiPublishJob>(`/publish-jobs/${jobId}/retry`, {
    method: "POST",
  });
  return mapPublishJob(apiJob);
}

/**
 * Dispatches all due jobs to the configured publisher connectors.
 */
export async function dispatchDuePublishJobs(): Promise<PublishDispatchResult> {
  const apiResult = await requestJson<ApiPublishDispatchResult>("/publish-jobs/dispatch-due", {
    method: "POST",
  });
  return mapPublishDispatchResult(apiResult);
}

/**
 * Polls scheduled jobs that already have a provider job id and writes back terminal results.
 */
export async function pollPublishJobs(): Promise<PublishPollResult> {
  const apiResult = await requestJson<ApiPublishPollResult>("/publish-jobs/poll", {
    method: "POST",
  });
  return mapPublishPollResult(apiResult);
}

/**
 * Loads aggregated ingestion and publishing metrics for the ops dashboard.
 */
export async function fetchOpsSummary(): Promise<OpsSummaryRecord> {
  const apiSummary = await requestJson<ApiOpsSummary>("/ops/summary");
  return mapOpsSummary(apiSummary);
}