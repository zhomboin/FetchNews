import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import {
  ArticleDraftRecord,
  IngestRunRecord,
  PublishJobRecord,
  SourceSpec,
  StoryRecord,
  fetchArticleDrafts,
  fetchIngestRuns,
  fetchOpsSummary,
  fetchPublishJobs,
  fetchSourceSpecs,
  fetchStories,
  formatSectionLabel,
} from "../../lib/api";

const REFRESH_INTERVAL_MS = 30_000;
const OPS_SUMMARY_QUERY_KEY = ["opsSummary", "detail"] as const;
const STORIES_QUERY_KEY = ["stories", "detail"] as const;
const PUBLISH_JOBS_QUERY_KEY = ["publishJobs", "detail"] as const;
const ARTICLES_QUERY_KEY = ["articles", "detail"] as const;
const SOURCE_SPECS_QUERY_KEY = ["sourceSpecs", "detail"] as const;
const INGEST_RUNS_QUERY_KEY = ["ingestRuns", "detail"] as const;

type OpsDetailPageProps = {
  health: string;
};

type DetailKind = "section" | "platform" | "source";

function isDetailKind(value: string | null): value is DetailKind {
  return value === "section" || value === "platform" || value === "source";
}

function formatDateTime(value: string | null): string {
  if (value === null) {
    return "Running";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatPublishStatus(status: string): string {
  if (status === "scheduled") {
    return "Scheduled";
  }
  if (status === "published") {
    return "Published";
  }
  if (status === "failed") {
    return "Failed";
  }
  return status;
}

function formatArticleStatus(status: string): string {
  if (status === "ready") {
    return "Ready";
  }
  if (status === "scheduled") {
    return "Scheduled";
  }
  if (status === "published") {
    return "Published";
  }
  if (status === "failed") {
    return "Failed";
  }
  return "Draft";
}

function formatStoryStatus(status: StoryRecord["status"]): string {
  return status === "approved" ? "Approved" : "Pending";
}

function formatPlatform(platform: string): string {
  if (platform === "wechat") {
    return "WeChat";
  }
  if (platform === "telegram") {
    return "Telegram";
  }
  return platform.toUpperCase();
}

function formatMomentumTier(momentumTier: string): string {
  if (momentumTier === "hot") {
    return "Hot";
  }
  if (momentumTier === "rising") {
    return "Rising";
  }
  if (momentumTier === "cooling") {
    return "Cooling";
  }
  return "Steady";
}

function formatPeriodType(periodType: ArticleDraftRecord["periodType"]): string {
  if (periodType === "weekly") {
    return "Weekly";
  }
  if (periodType === "monthly") {
    return "Monthly";
  }
  return "Daily";
}

function buildDetailPath(kind: DetailKind, target: string, failedOnly = false): string {
  const searchParams = new URLSearchParams({ kind });
  if (kind === "section") {
    searchParams.set("section", target);
  }
  if (kind === "platform") {
    searchParams.set("platform", target);
  }
  if (kind === "source") {
    searchParams.set("source", target);
  }
  if (failedOnly) {
    searchParams.set("failedOnly", "1");
  }
  return `/ops/details?${searchParams.toString()}`;
}

function readConfigNumber(source: SourceSpec, key: string): number | null {
  const value = source.config[key];
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function countSourceFailures(run: IngestRunRecord, sourceSlug: string): number {
  return run.errors.filter((error) => error.sourceSlug === sourceSlug).length;
}

function pickTarget(searchParams: URLSearchParams, kind: DetailKind | null): string | null {
  if (kind === "section") {
    return searchParams.get("section");
  }
  if (kind === "platform") {
    return searchParams.get("platform");
  }
  if (kind === "source") {
    return searchParams.get("source");
  }
  return null;
}

function getWorkbenchLink(kind: DetailKind | null): string {
  if (kind === "section") {
    return "/stories";
  }
  if (kind === "platform") {
    return "/articles";
  }
  if (kind === "source") {
    return "/ingestion";
  }
  return "/";
}

/**
 * Drill-down detail page for section, platform, and failed source diagnostics.
 */
export function OpsDetailPage({ health }: OpsDetailPageProps): React.JSX.Element {
  const [searchParams] = useSearchParams();
  const kind = isDetailKind(searchParams.get("kind")) ? searchParams.get("kind") : null;
  const detailKind = kind as DetailKind | null;
  const target = pickTarget(searchParams, detailKind);
  const failedOnly = searchParams.get("failedOnly") === "1";

  const opsSummaryQuery = useQuery({
    queryKey: OPS_SUMMARY_QUERY_KEY,
    queryFn: fetchOpsSummary,
    enabled: detailKind === "section" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const storiesQuery = useQuery({
    queryKey: STORIES_QUERY_KEY,
    queryFn: fetchStories,
    enabled: detailKind === "section" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const publishJobsQuery = useQuery({
    queryKey: PUBLISH_JOBS_QUERY_KEY,
    queryFn: fetchPublishJobs,
    enabled: detailKind === "platform" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const articlesQuery = useQuery({
    queryKey: ARTICLES_QUERY_KEY,
    queryFn: fetchArticleDrafts,
    enabled: detailKind === "platform" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const sourceSpecsQuery = useQuery({
    queryKey: SOURCE_SPECS_QUERY_KEY,
    queryFn: fetchSourceSpecs,
    enabled: detailKind === "source" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const ingestRunsQuery = useQuery({
    queryKey: INGEST_RUNS_QUERY_KEY,
    queryFn: fetchIngestRuns,
    enabled: detailKind === "source" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  const opsSummary = opsSummaryQuery.data;
  const stories = storiesQuery.data ?? [];
  const publishJobs = publishJobsQuery.data ?? [];
  const articles = articlesQuery.data ?? [];
  const sourceSpecs = sourceSpecsQuery.data ?? [];
  const ingestRuns = ingestRunsQuery.data ?? [];

  const sectionMetric =
    detailKind === "section" && target !== null
      ? opsSummary?.sectionReviewMetrics.find((metric) => metric.section === target) ?? null
      : null;
  const sectionStories =
    detailKind === "section" && target !== null
      ? stories
          .filter((story) => story.sections.includes(target))
          .sort((left, right) => right.score - left.score)
      : [];
  const platformJobs =
    detailKind === "platform" && target !== null
      ? publishJobs
          .filter((job) => job.platform === target)
          .filter((job) => (failedOnly ? job.status === "failed" : true))
          .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
      : [];
  const platformEngagement = platformJobs.reduce(
    (totals, job) => ({
      impressions: totals.impressions + (job.performanceMetrics.impressions ?? 0),
      opens: totals.opens + (job.performanceMetrics.opens ?? 0),
      clicks: totals.clicks + (job.performanceMetrics.clicks ?? 0),
      interactions: totals.interactions + (job.performanceMetrics.interactions ?? 0),
    }),
    { impressions: 0, opens: 0, clicks: 0, interactions: 0 },
  );
  const relatedArticleIds = new Set(platformJobs.map((job) => job.articleId));
  const platformArticles =
    detailKind === "platform" && target !== null
      ? articles
          .filter((article) => relatedArticleIds.has(article.id))
          .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
      : [];
  const sourceSpec =
    detailKind === "source" && target !== null ? sourceSpecs.find((source) => source.slug === target) ?? null : null;
  const sourceRuns =
    detailKind === "source" && target !== null
      ? ingestRuns
          .filter((run) => run.sourceSlugs.includes(target))
          .filter((run) => (failedOnly ? countSourceFailures(run, target) > 0 : true))
          .sort((left, right) => new Date(right.startedAt).getTime() - new Date(left.startedAt).getTime())
      : [];
  const sourceFailureRows =
    detailKind === "source" && target !== null
      ? sourceRuns.flatMap((run) =>
          run.errors
            .filter((error) => error.sourceSlug === target)
            .map((error) => ({ runId: run.id, message: error.message, startedAt: run.startedAt })),
        )
      : [];

  const isLoading =
    opsSummaryQuery.isLoading ||
    storiesQuery.isLoading ||
    publishJobsQuery.isLoading ||
    articlesQuery.isLoading ||
    sourceSpecsQuery.isLoading ||
    ingestRunsQuery.isLoading;
  const isError =
    opsSummaryQuery.isError ||
    storiesQuery.isError ||
    publishJobsQuery.isError ||
    articlesQuery.isError ||
    sourceSpecsQuery.isError ||
    ingestRunsQuery.isError;

  const headingTitle =
    detailKind === "section"
      ? `${target ? formatSectionLabel(target) : "Section"} detail`
      : detailKind === "platform"
        ? `${target ? formatPlatform(target) : "Platform"} detail`
        : detailKind === "source"
          ? `${target ?? "Source"} detail`
          : "Ops detail";
  const headingLead =
    detailKind === "section"
      ? "Inspect the stories currently grouped into this editorial section, their review state, and the risk signals that affect inclusion in digests."
      : detailKind === "platform"
        ? "Inspect publish jobs for a single platform, review recent failures, and see which digests are currently associated with that channel."
        : detailKind === "source"
          ? "Inspect governance posture, ingestion failures, and recent source runs before adjusting trust or re-triggering collection."
          : "Choose a section, platform, or source from the operations dashboard to open its drill-down detail page.";

  return (
    <div className="page-stack detail-page">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Ops Drill-down</p>
          <h1>{headingTitle}</h1>
          <p className="lede">{headingLead}</p>
          <div className="detail-breadcrumb-row">
            <Link className="detail-link" to={detailKind === "platform" ? "/publishing" : "/"}>
              Back to ops
            </Link>
            <Link className="detail-link detail-link-soft" to={getWorkbenchLink(detailKind)}>
              Open full workbench
            </Link>
            {detailKind === "platform" && target !== null ? (
              <Link className="detail-link detail-link-soft" to={buildDetailPath("platform", target, !failedOnly)}>
                {failedOnly ? "Show all jobs" : "Show failed only"}
              </Link>
            ) : null}
            {detailKind === "source" && target !== null ? (
              <Link className="detail-link detail-link-soft" to={buildDetailPath("source", target, !failedOnly)}>
                {failedOnly ? "Show all runs" : "Show failed only"}
              </Link>
            ) : null}
          </div>
        </div>

        <div className="hero-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>Current target</span>
            <strong>{target ?? "No target selected"}</strong>
          </div>
        </div>
      </section>

      {!detailKind || target === null ? (
        <section className="panel">
          <div className="empty-state">This detail page needs a section, platform, or source target from the ops dashboard.</div>
        </section>
      ) : null}

      {detailKind === "section" && target !== null ? (
        <>
          <section className="stats-grid" aria-label="Section detail metrics">
            <article className="metric-cell">
              <p>Stories</p>
              <strong>{sectionStories.length}</strong>
              <span>Total stories currently mapped into this section.</span>
            </article>
            <article className="metric-cell">
              <p>Approved</p>
              <strong>{sectionStories.filter((story) => story.status === "approved").length}</strong>
              <span>Stories already approved for digest generation.</span>
            </article>
            <article className="metric-cell">
              <p>Pending</p>
              <strong>{sectionStories.filter((story) => story.status !== "approved").length}</strong>
              <span>Stories still waiting for editorial review.</span>
            </article>
            <article className="metric-cell">
              <p>Flagged</p>
              <strong>{sectionStories.filter((story) => story.riskFlags.length > 0).length}</strong>
              <span>Stories carrying at least one risk flag.</span>
            </article>
            <article className="metric-cell">
              <p>Momentum</p>
              <strong>{formatMomentumTier(sectionMetric?.momentumTier ?? "steady")}</strong>
              <span>
                {sectionMetric
                  ? `${sectionMetric.engagementClicks} clicks from ${sectionMetric.engagementImpressions} impressions.`
                  : "No post-publication engagement captured for this section yet."}
              </span>
            </article>
            <article className="metric-cell">
              <p>CTR</p>
              <strong>{sectionMetric ? `${Math.round(sectionMetric.clickThroughRate * 100)}%` : "--"}</strong>
              <span>
                {sectionMetric
                  ? `${sectionMetric.engagementInteractions} interactions and ${sectionMetric.engagementOpens} opens.`
                  : "Awaiting publish feedback to compute section conversion."}
              </span>
            </article>
          </section>

          <section className="panel detail-panel">
            <header className="section-title">
              <div>
                <p>Section Stories</p>
                <h2>{formatSectionLabel(target)}</h2>
              </div>
              <span>{storiesQuery.isFetching ? "Refreshing" : "Live section slice"}</span>
            </header>

            {isLoading ? <div className="empty-state">Loading section detail...</div> : null}
            {isError ? <div className="empty-state">Section detail failed to load. Check the stories endpoint and try again.</div> : null}
            {!isLoading && !isError && sectionStories.length === 0 ? (
              <div className="empty-state">No stories currently match this section.</div>
            ) : null}

            {!isLoading && !isError && sectionStories.length > 0 ? (
              <div className="detail-card-list">
                {sectionStories.map((story) => (
                  <article key={story.id} className="detail-card" data-tone={story.riskFlags.length > 0 ? "watch" : "calm"}>
                    <div className="detail-card-header">
                      <div>
                        <p className="detail-kicker">{story.storyKey}</p>
                        <h3>{story.clusterTitle}</h3>
                      </div>
                      <div className="detail-card-meta">
                        <span className={`status-pill status-${story.status}`}>{formatStoryStatus(story.status)}</span>
                        <strong>{story.score.toFixed(1)}</strong>
                      </div>
                    </div>
                    <p className="detail-copy">{story.summary}</p>
                    <div className="detail-chip-row">
                      {story.sections.map((section) => (
                        <span key={`${story.id}-${section}`} className="section-badge section-badge-soft">
                          {formatSectionLabel(section)}
                        </span>
                      ))}
                    </div>
                    {story.riskFlags.length > 0 ? (
                      <div className="detail-chip-row">
                        {story.riskFlags.map((flag) => (
                          <span key={`${story.id}-${flag}`} className="failure-target-chip">
                            {flag}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    <div className="detail-inline-grid">
                      <div>
                        <span>Items</span>
                        <strong>{story.itemCount}</strong>
                      </div>
                      <div>
                        <span>Window</span>
                        <strong>{formatDateTime(story.lastSeenAt)}</strong>
                      </div>
                    </div>
                    {story.highlights.length > 0 ? (
                      <div className="detail-note-stack">
                        {story.highlights.slice(0, 3).map((highlight) => (
                          <p key={`${story.id}-${highlight}`} className="detail-note">
                            {highlight}
                          </p>
                        ))}
                      </div>
                    ) : null}
                    {story.sourceLinks.length > 0 ? (
                      <div className="detail-chip-row">
                        {story.sourceLinks.slice(0, 3).map((link) => (
                          <a key={link} className="detail-link detail-link-soft" href={link} target="_blank" rel="noreferrer">
                            Source link
                          </a>
                        ))}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : null}
          </section>
        </>
      ) : null}

      {detailKind === "platform" && target !== null ? (
        <>
          <section className="stats-grid" aria-label="Platform detail metrics">
            <article className="metric-cell">
              <p>Jobs</p>
              <strong>{platformJobs.length}</strong>
              <span>Publish jobs currently visible for this platform.</span>
            </article>
            <article className="metric-cell">
              <p>Published</p>
              <strong>{platformJobs.filter((job) => job.status === "published").length}</strong>
              <span>Jobs that reached a terminal published state.</span>
            </article>
            <article className="metric-cell">
              <p>Clicks</p>
              <strong>{platformEngagement.clicks}</strong>
              <span>{platformEngagement.interactions} interactions from visible jobs.</span>
            </article>
            <article className="metric-cell">
              <p>Drafts</p>
              <strong>{platformArticles.length}</strong>
              <span>{platformEngagement.impressions} impressions recorded for this platform.</span>
            </article>
          </section>

          <section className="ops-grid detail-grid">
            <article className="panel">
              <header className="section-title">
                <div>
                  <p>Platform Jobs</p>
                  <h2>{formatPlatform(target)}</h2>
                </div>
                <span>{failedOnly ? "Failed only" : "All jobs"}</span>
              </header>

              {isLoading ? <div className="empty-state">Loading platform detail...</div> : null}
              {isError ? <div className="empty-state">Platform detail failed to load. Check publish jobs and article endpoints.</div> : null}
              {!isLoading && !isError && platformJobs.length === 0 ? (
                <div className="empty-state">No publish jobs match this platform filter yet.</div>
              ) : null}

              {!isLoading && !isError && platformJobs.length > 0 ? (
                <div className="publish-job-list">
                  {platformJobs.map((job) => (
                    <article key={job.id} className="publish-job-row">
                      <div className="publish-job-copy">
                        <div>
                          <strong>Article #{job.articleId}</strong>
                          <p>{formatDateTime(job.scheduledFor)}</p>
                        </div>
                        <div className="publish-job-meta">
                          <span className={`status-pill status-${job.status}`}>{formatPublishStatus(job.status)}</span>
                          <span>Retries {job.retries}</span>
                        </div>
                      </div>
                      <div className="publish-job-note-stack">
                        <span className="publish-job-note">Updated {formatDateTime(job.updatedAt)}</span>
                        {job.providerJobId ? <span className="publish-job-note">Provider job: {job.providerJobId}</span> : null}
                        {job.externalId ? <span className="publish-job-note">External id: {job.externalId}</span> : null}
                        {job.metricsRecordedAt ? (
                          <span className="publish-job-note">
                            Metrics: {job.performanceMetrics.impressions ?? 0} impressions · {job.performanceMetrics.clicks ?? 0} clicks · {job.performanceMetrics.interactions ?? 0} interactions
                          </span>
                        ) : null}
                        {job.errorMessage ? <span className="publish-job-error">{job.errorMessage}</span> : null}
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}
            </article>

            <article className="panel">
              <header className="section-title">
                <div>
                  <p>Related Drafts</p>
                  <h2>Drafts routed to {formatPlatform(target)}</h2>
                </div>
                <span>{platformArticles.length} drafts</span>
              </header>

              {isLoading ? <div className="empty-state">Loading related drafts...</div> : null}
              {!isLoading && !isError && platformArticles.length === 0 ? (
                <div className="empty-state">No drafts are currently associated with the selected platform filter.</div>
              ) : null}

              {!isLoading && !isError && platformArticles.length > 0 ? (
                <div className="ops-article-list">
                  {platformArticles.map((article) => {
                    const matchingJobs = platformJobs.filter((job) => job.articleId === article.id);
                    return (
                      <article key={article.id} className="ops-article-row">
                        <div>
                          <strong>{article.title}</strong>
                          <p>
                            {formatPeriodType(article.periodType)} · {article.storyCount} stories · updated {formatDateTime(article.updatedAt)}
                          </p>
                        </div>
                        <div className="ops-article-meta">
                          <span className={`status-pill status-${article.status}`}>{formatArticleStatus(article.status)}</span>
                          <span>{matchingJobs.length} matching jobs</span>
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : null}
            </article>
          </section>
        </>
      ) : null}

      {detailKind === "source" && target !== null ? (
        <>
          <section className="stats-grid" aria-label="Source detail metrics">
            <article className="metric-cell">
              <p>Runs</p>
              <strong>{sourceRuns.length}</strong>
              <span>Recent runs where this source was included.</span>
            </article>
            <article className="metric-cell">
              <p>Failures</p>
              <strong>{sourceFailureRows.length}</strong>
              <span>Error rows recorded for this source across visible runs.</span>
            </article>
            <article className="metric-cell">
              <p>Trust</p>
              <strong>{sourceSpec?.effectiveTrustScore?.toFixed(1) ?? "--"}</strong>
              <span>Effective trust score after governance feedback.</span>
            </article>
            <article className="metric-cell">
              <p>Ranking</p>
              <strong>{sourceSpec?.effectiveScoreMultiplier?.toFixed(2) ?? "--"}x</strong>
              <span>Effective ranking multiplier used by story scoring.</span>
            </article>
          </section>

          <section className="ops-grid detail-grid">
            <article className="panel">
              <header className="section-title">
                <div>
                  <p>Source Governance</p>
                  <h2>{sourceSpec?.label ?? target}</h2>
                </div>
                <span>{sourceSpec?.priority ?? "Unknown priority"}</span>
              </header>

              {isLoading ? <div className="empty-state">Loading source detail...</div> : null}
              {isError ? <div className="empty-state">Source detail failed to load. Check source catalog and ingest runs.</div> : null}
              {!isLoading && !isError && sourceSpec === null ? (
                <div className="empty-state">No source catalog entry matches this slug.</div>
              ) : null}

              {!isLoading && !isError && sourceSpec !== null ? (
                <article className="source-governance-card" data-tone={sourceSpec.governanceFlags.length > 0 ? "watch" : "calm"}>
                  <div className="source-governance-head">
                    <div>
                      <p>{sourceSpec.platform}</p>
                      <strong>{sourceSpec.label}</strong>
                    </div>
                    <span className="source-chip">{sourceSpec.priority}</span>
                  </div>
                  <div className="platform-metric-grid compact-gap">
                    <div>
                      <span>Base trust</span>
                      <strong>{readConfigNumber(sourceSpec, "trust_score")?.toFixed(1) ?? "--"}</strong>
                    </div>
                    <div>
                      <span>Effective trust</span>
                      <strong>{sourceSpec.effectiveTrustScore?.toFixed(1) ?? "--"}</strong>
                    </div>
                    <div>
                      <span>Base ranking</span>
                      <strong>{readConfigNumber(sourceSpec, "score_multiplier")?.toFixed(2) ?? "--"}x</strong>
                    </div>
                    <div>
                      <span>Effective ranking</span>
                      <strong>{sourceSpec.effectiveScoreMultiplier?.toFixed(2) ?? "--"}x</strong>
                    </div>
                  </div>
                  <p className="source-governance-note">
                    Failures {sourceSpec.feedbackSignals.failed_ingest_runs ?? 0} · Pending {sourceSpec.feedbackSignals.pending_stories ?? 0} · Flagged {sourceSpec.feedbackSignals.flagged_stories ?? 0}
                  </p>
                  {sourceSpec.governanceFlags.length > 0 ? (
                    <div className="failure-chip-list">
                      {sourceSpec.governanceFlags.map((flag) => (
                        <span key={`${sourceSpec.slug}-${flag}`} className="failure-target-chip">
                          {flag}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </article>
              ) : null}
            </article>

            <article className="panel">
              <header className="section-title">
                <div>
                  <p>Run History</p>
                  <h2>{failedOnly ? "Failed runs" : "Recent runs"}</h2>
                </div>
                <span>{sourceRuns.length} runs</span>
              </header>

              {isLoading ? <div className="empty-state">Loading source runs...</div> : null}
              {!isLoading && !isError && sourceRuns.length === 0 ? (
                <div className="empty-state">No runs match the selected source filter.</div>
              ) : null}

              {!isLoading && !isError && sourceRuns.length > 0 ? (
                <div className="ingest-run-list">
                  {sourceRuns.map((run) => {
                    const sourceErrors = run.errors.filter((error) => error.sourceSlug === target);
                    return (
                      <article key={run.id} className="ingest-run-row">
                        <div className="run-main">
                          <div className="run-head">
                            <h3>Run #{run.id}</h3>
                            <span className={`status-pill status-${run.status}`}>{run.status}</span>
                          </div>
                          <div className="source-chip-list">
                            {run.sourceSlugs.map((slug) => (
                              <span key={`${run.id}-${slug}`} className="source-chip">
                                {slug}
                              </span>
                            ))}
                          </div>
                          {sourceErrors.length > 0 ? (
                            <div className="run-errors">
                              {sourceErrors.map((error) => (
                                <p key={`${run.id}-${error.message}`}>{error.message}</p>
                              ))}
                            </div>
                          ) : (
                            <p className="run-note">This run completed without a source-specific error for the current slug.</p>
                          )}
                        </div>
                        <div className="run-metrics">
                          <div>
                            <span>Status</span>
                            <strong>{run.status}</strong>
                          </div>
                          <div>
                            <span>Items</span>
                            <strong>{run.itemsIngested}</strong>
                          </div>
                          <div>
                            <span>Started</span>
                            <strong>{formatDateTime(run.startedAt)}</strong>
                          </div>
                          <div>
                            <span>Finished</span>
                            <strong>{formatDateTime(run.finishedAt)}</strong>
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : null}
            </article>
          </section>
        </>
      ) : null}
    </div>
  );
}