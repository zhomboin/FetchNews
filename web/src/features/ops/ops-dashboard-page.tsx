import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import {
  AlertRecord,
  ArticleDraftRecord,
  FailureGroupRecord,
  FeedbackRecommendationRecord,
  PublishJobRecord,
  PublishPlatformMetricRecord,
  SectionReviewMetricRecord,
  fetchArticleDrafts,
  fetchOpsSummary,
  fetchPublishJobs,
} from "../../lib/api";

const OPS_SUMMARY_QUERY_KEY = ["opsSummary"] as const;
const PUBLISH_JOBS_QUERY_KEY = ["publishJobs"] as const;
const ARTICLES_QUERY_KEY = ["articles"] as const;
const REFRESH_INTERVAL_MS = 30_000;

type OpsDashboardPageProps = {
  health: string;
  mode: "overview" | "publishing";
};

type OpsMetric = {
  label: string;
  value: string;
  note: string;
};

type DetailKind = "section" | "platform" | "source";

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
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

function formatFailureCategory(category: string): string {
  if (category === "ingest") {
    return "Ingest";
  }
  if (category === "publish") {
    return "Publish";
  }
  return category;
}

function formatRecommendationCategory(category: string): string {
  if (category === "section") {
    return "Section";
  }
  if (category === "platform") {
    return "Platform";
  }
  if (category === "source") {
    return "Source";
  }
  return category;
}

function buildMetrics(summary: Awaited<ReturnType<typeof fetchOpsSummary>> | undefined): OpsMetric[] {
  if (summary === undefined) {
    return [
      { label: "Items ingested", value: "--", note: "Waiting for backend metrics" },
      { label: "Approved stories", value: "--", note: "Waiting for backend metrics" },
      { label: "Publish success", value: "--", note: "Waiting for backend metrics" },
      { label: "Engagement clicks", value: "--", note: "Waiting for backend metrics" },
    ];
  }

  return [
    {
      label: "Items ingested",
      value: `${summary.itemsIngestedTotal}`,
      note: `${summary.ingestRunsTotal} runs, ${summary.ingestRunsFailed} failed`,
    },
    {
      label: "Approved stories",
      value: `${summary.storiesApproved}`,
      note: `${summary.storiesPending} pending review`,
    },
    {
      label: "Publish success",
      value: `${Math.round(summary.publishSuccessRate * 100)}%`,
      note: `${summary.publishJobsPublished} published, ${summary.publishJobsFailed} failed`,
    },
    {
      label: "Engagement clicks",
      value: `${summary.engagementClicksTotal}`,
      note: `${summary.engagementInteractionsTotal} interactions, ${summary.engagementOpensTotal} opens`,
    },
  ];
}

function pickRecentJobs(jobs: PublishJobRecord[]): PublishJobRecord[] {
  return [...jobs]
    .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
    .slice(0, 6);
}

function pickRecentArticles(articles: ArticleDraftRecord[]): ArticleDraftRecord[] {
  return [...articles]
    .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
    .slice(0, 5);
}

function pickAlerts(alerts: AlertRecord[]): AlertRecord[] {
  return alerts.slice(0, 6);
}

function pickFailureGroups(groups: FailureGroupRecord[]): FailureGroupRecord[] {
  return groups.slice(0, 6);
}

function pickPlatformMetrics(metrics: PublishPlatformMetricRecord[]): PublishPlatformMetricRecord[] {
  return metrics.slice(0, 6);
}

function pickSectionMetrics(metrics: SectionReviewMetricRecord[]): SectionReviewMetricRecord[] {
  return metrics.slice(0, 6);
}

function getMomentumPriority(momentumTier: string): number {
  if (momentumTier === "hot") {
    return 0;
  }
  if (momentumTier === "rising") {
    return 1;
  }
  if (momentumTier === "steady") {
    return 2;
  }
  return 3;
}

function pickMomentumSections(metrics: SectionReviewMetricRecord[]): SectionReviewMetricRecord[] {
  return [...metrics]
    .filter((metric) => metric.engagementImpressions > 0 || metric.totalStories > 0)
    .sort((left, right) => {
      const momentumDiff = getMomentumPriority(left.momentumTier) - getMomentumPriority(right.momentumTier);
      if (momentumDiff !== 0) {
        return momentumDiff;
      }
      if (right.engagementClicks !== left.engagementClicks) {
        return right.engagementClicks - left.engagementClicks;
      }
      return right.totalStories - left.totalStories;
    })
    .slice(0, 4);
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

function pickRecommendations(recommendations: FeedbackRecommendationRecord[]): FeedbackRecommendationRecord[] {
  return recommendations.slice(0, 6);
}

function getAlertTone(alert: AlertRecord): "watch" | "calm" {
  return alert.severity === "info" ? "calm" : "watch";
}

function getFailureTone(group: FailureGroupRecord): "watch" | "calm" {
  if (group.category === "publish") {
    return "watch";
  }
  return "calm";
}

function getPlatformTone(metric: PublishPlatformMetricRecord): "watch" | "calm" {
  if (metric.failedJobs > 0 && metric.successRate < 0.5) {
    return "watch";
  }
  return "calm";
}

function getSectionTone(metric: SectionReviewMetricRecord): "watch" | "calm" {
  if (metric.flaggedStories > 0 || metric.pendingStories > 0 || metric.momentumTier === "cooling") {
    return "watch";
  }
  return "calm";
}

function getRecommendationTone(recommendation: FeedbackRecommendationRecord): "watch" | "calm" {
  if (recommendation.category === "platform" || recommendation.category === "section") {
    return "watch";
  }
  return "calm";
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

function buildRecommendationDetailPath(recommendation: FeedbackRecommendationRecord): string | null {
  if (recommendation.category === "section") {
    return buildDetailPath("section", recommendation.target);
  }
  if (recommendation.category === "platform") {
    return buildDetailPath("platform", recommendation.target, true);
  }
  if (recommendation.category === "source") {
    return buildDetailPath("source", recommendation.target, true);
  }
  return null;
}

function buildFailureDetailPath(group: FailureGroupRecord): string | null {
  const target = group.targets[0];
  if (!target) {
    return null;
  }
  if (group.category === "publish") {
    return buildDetailPath("platform", target, true);
  }
  if (group.category === "ingest") {
    return buildDetailPath("source", target, true);
  }
  return null;
}

/**
 * Real operations dashboard for ingestion, diagnostics, publishing health, and drill-down navigation.
 */
export function OpsDashboardPage({ health, mode }: OpsDashboardPageProps): React.JSX.Element {
  const summaryQuery = useQuery({
    queryKey: OPS_SUMMARY_QUERY_KEY,
    queryFn: fetchOpsSummary,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const publishJobsQuery = useQuery({
    queryKey: PUBLISH_JOBS_QUERY_KEY,
    queryFn: fetchPublishJobs,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const articlesQuery = useQuery({
    queryKey: ARTICLES_QUERY_KEY,
    queryFn: fetchArticleDrafts,
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  const summary = summaryQuery.data;
  const metrics = buildMetrics(summary);
  const recentJobs = pickRecentJobs(publishJobsQuery.data ?? []);
  const recentArticles = pickRecentArticles(articlesQuery.data ?? []);
  const alerts = pickAlerts(summary?.alerts ?? []);
  const failureGroups = pickFailureGroups(summary?.recentFailureGroups ?? []);
  const platformMetrics = pickPlatformMetrics(summary?.publishPlatformMetrics ?? []);
  const sectionMetrics = pickSectionMetrics(summary?.sectionReviewMetrics ?? []);
  const momentumSections = pickMomentumSections(summary?.sectionReviewMetrics ?? []);
  const feedbackRecommendations = pickRecommendations(summary?.feedbackRecommendations ?? []);
  const title = mode === "publishing" ? "Publishing Operations" : "Operations Overview";
  const lead =
    mode === "publishing"
      ? "Track delivery quality, platform health, review backlog, and the next actions the team should take before retrying distribution."
      : "Watch ingestion, editorial review, draft generation, and multi-platform delivery from one warm-metal control room.";

  return (
    <div className="preview-page ops-dashboard-page">
      <section className="intro-band">
        <div className="intro-copy">
          <p className="eyebrow">Operations Console</p>
          <h1>{title}</h1>
          <p className="lede">{lead}</p>
        </div>

        <div className="intro-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>Refresh interval</span>
            <strong>30s</strong>
          </div>
        </div>
      </section>

      <section className="metric-strip" aria-label="Operations snapshot">
        {metrics.map((metric) => (
          <article key={metric.label} className="metric-cell">
            <p>{metric.label}</p>
            <strong>{metric.value}</strong>
            <span>{metric.note}</span>
          </article>
        ))}
      </section>


      <section className="ops-alert-strip" aria-label="Operations alerts">
        {alerts.length === 0 ? (
          <article className="ops-alert-card" data-tone="calm">
            <div>
              <p>Alerts</p>
              <strong>No active alerts</strong>
            </div>
            <span>Current ingestion, review, and publishing signals look stable.</span>
          </article>
        ) : (
          alerts.map((alert) => (
            <article key={`${alert.category}-${alert.title}`} className="ops-alert-card" data-tone={getAlertTone(alert)}>
              <div className="ops-alert-head">
                <div>
                  <p>{alert.category}</p>
                  <strong>{alert.title}</strong>
                </div>
                <span className={`status-pill status-${alert.severity === "critical" ? "failed" : alert.severity === "warning" ? "pending" : "approved"}`}>
                  {alert.count}
                </span>
              </div>
              <span>{alert.summary}</span>
              <p className="failure-suggestion">{alert.suggestion}</p>
            </article>
          ))
        )}
      </section>

      <section className="ops-grid">
        <article className="panel ops-health-panel">
          <header className="section-title">
            <div>
              <p>Pipeline Health</p>
              <h2>Core workflow health</h2>
            </div>
            <span>{summaryQuery.isFetching ? "Refreshing" : "Live snapshot"}</span>
          </header>

          <div className="runway ops-runway">
            <div className="runway-step">
              <div className="runway-node">
                <span>1</span>
              </div>
              <div className="runway-copy">
                <strong>Ingest</strong>
                <p>{summary?.ingestRunsTotal ?? 0}</p>
                <span>{summary?.ingestRunsFailed ?? 0} runs with errors</span>
              </div>
            </div>
            <div className="runway-step">
              <div className="runway-node">
                <span>2</span>
              </div>
              <div className="runway-copy">
                <strong>Review</strong>
                <p>{summary?.storiesApproved ?? 0}</p>
                <span>{summary?.storiesPending ?? 0} waiting for review</span>
              </div>
            </div>
            <div className="runway-step">
              <div className="runway-node">
                <span>3</span>
              </div>
              <div className="runway-copy">
                <strong>Publish</strong>
                <p>{summary?.publishJobsPublished ?? 0}</p>
                <span>{summary?.publishJobsScheduled ?? 0} still scheduled</span>
              </div>
            </div>
          </div>

          <div className="risk-overview-grid ops-risk-grid">
            <div className="risk-stat" data-tone={(summary?.articlesFailed ?? 0) > 0 ? "watch" : "calm"}>
              <p>Failed drafts</p>
              <strong>{summary?.articlesFailed ?? 0}</strong>
              <span>Drafts that failed after publish writeback and need operator attention.</span>
            </div>
            <div className="risk-stat" data-tone={(summary?.duePublishJobs ?? 0) > 0 ? "watch" : "calm"}>
              <p>Due but not completed</p>
              <strong>{summary?.duePublishJobs ?? 0}</strong>
              <span>Jobs already due but still waiting for dispatch or poll completion.</span>
            </div>
            <div
              className="risk-stat"
              data-tone={(summary?.feedbackRecommendations.length ?? 0) > 0 ? "watch" : "calm"}
            >
              <p>Action queue</p>
              <strong>{summary?.feedbackRecommendations.length ?? 0}</strong>
              <span>Recommendations generated from review backlog, failures, and platform signals.</span>
            </div>
          </div>
        </article>

        <div className="ops-side-stack">
          <article className="panel ops-section-panel">
            <header className="section-title">
              <div>
                <p>Section Review</p>
                <h2>Editorial load by section</h2>
              </div>
              <span>{sectionMetrics.length} sections</span>
            </header>

            {sectionMetrics.length === 0 ? (
              <div className="empty-state">No reviewed or pending stories yet. Run ingestion and approve a few stories first.</div>
            ) : (
              <div className="source-governance-grid section-metric-list">
                {sectionMetrics.map((metric) => (
                  <article key={metric.section} className="source-governance-card" data-tone={getSectionTone(metric)}>
                    <div className="source-governance-head">
                      <div>
                        <p>{metric.section.replace(/_/g, " ")}</p>
                        <strong>{metric.label}</strong>
                      </div>
                      <span className="status-pill status-pending">{metric.totalStories}</span>
                    </div>
                    <div className="platform-metric-grid compact-gap">
                      <div>
                        <span>Approved</span>
                        <strong>{metric.approvedStories}</strong>
                      </div>
                      <div>
                        <span>Pending</span>
                        <strong>{metric.pendingStories}</strong>
                      </div>
                      <div>
                        <span>Flagged</span>
                        <strong>{metric.flaggedStories}</strong>
                      </div>
                      <div>
                        <span>Total</span>
                        <strong>{metric.totalStories}</strong>
                      </div>
                    </div>
                    <p className="platform-metric-note">
                      {metric.engagementImpressions > 0
                        ? `${formatMomentumTier(metric.momentumTier)} · CTR ${Math.round(metric.clickThroughRate * 100)}% · ${metric.engagementClicks} clicks`
                        : "No post-publication engagement captured for this section yet."}
                    </p>
                    <div className="panel-link-row">
                      <Link className="detail-link" to={buildDetailPath("section", metric.section)}>
                        Open section detail
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </article>

          <article className="panel ops-momentum-panel">
            <header className="section-title">
              <div>
                <p>Section Momentum</p>
                <h2>High-performing sections</h2>
              </div>
              <span>{momentumSections.length} tracked</span>
            </header>

            {momentumSections.length === 0 ? (
              <div className="empty-state">No section engagement signals yet. Record publish feedback to reveal what is actually landing.</div>
            ) : (
              <div className="source-governance-grid momentum-section-list">
                {momentumSections.map((metric) => (
                  <article
                    key={`momentum-${metric.section}`}
                    className="source-governance-card"
                    data-tone={metric.momentumTier === "cooling" ? "watch" : "calm"}
                  >
                    <div className="source-governance-head">
                      <div>
                        <p>{metric.section.replace(/_/g, " ")}</p>
                        <strong>{metric.label}</strong>
                      </div>
                      <span className="momentum-chip" data-tier={metric.momentumTier}>{formatMomentumTier(metric.momentumTier)}</span>
                    </div>
                    <div className="platform-metric-grid compact-gap">
                      <div>
                        <span>Clicks</span>
                        <strong>{metric.engagementClicks}</strong>
                      </div>
                      <div>
                        <span>CTR</span>
                        <strong>{Math.round(metric.clickThroughRate * 100)}%</strong>
                      </div>
                      <div>
                        <span>Interactions</span>
                        <strong>{metric.engagementInteractions}</strong>
                      </div>
                      <div>
                        <span>Impressions</span>
                        <strong>{metric.engagementImpressions}</strong>
                      </div>
                    </div>
                    <div className="panel-link-row">
                      <Link className="detail-link" to={buildDetailPath("section", metric.section)}>
                        Open section detail
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </article>

          <article className="panel ops-recommendation-panel">
            <header className="section-title">
              <div>
                <p>Feedback Loop</p>
                <h2>Recommended next actions</h2>
              </div>
              <span>{feedbackRecommendations.length} suggestions</span>
            </header>

            {feedbackRecommendations.length === 0 ? (
              <div className="empty-state">No actions recommended right now. Current review and publish signals look stable.</div>
            ) : (
              <div className="failure-group-list recommendation-list">
                {feedbackRecommendations.map((recommendation) => {
                  const detailPath = buildRecommendationDetailPath(recommendation);
                  return (
                    <article
                      key={`${recommendation.category}-${recommendation.target}`}
                      className="failure-group-card recommendation-card"
                      data-tone={getRecommendationTone(recommendation)}
                    >
                      <div className="failure-group-head">
                        <div>
                          <p>{formatRecommendationCategory(recommendation.category)}</p>
                          <strong>{recommendation.title}</strong>
                        </div>
                        <span className="status-pill status-pending">{recommendation.signalCount}</span>
                      </div>
                      <p className="source-governance-note">{recommendation.summary}</p>
                      <p className="failure-suggestion">{recommendation.suggestion}</p>
                      {detailPath ? (
                        <div className="panel-link-row">
                          <Link className="detail-link" to={detailPath}>
                            Open recommendation detail
                          </Link>
                        </div>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            )}
          </article>
        </div>
      </section>

      <section className="ops-grid">
        <article className="panel ops-diagnostics-panel">
          <header className="section-title">
            <div>
              <p>Failure Diagnostics</p>
              <h2>Recent grouped failures</h2>
            </div>
            <span>{failureGroups.length} groups</span>
          </header>

          {failureGroups.length === 0 ? (
            <div className="empty-state">No recent grouped failures. The current pipeline snapshot looks clean.</div>
          ) : (
            <div className="failure-group-list">
              {failureGroups.map((group) => {
                const detailPath = buildFailureDetailPath(group);
                return (
                  <article key={`${group.category}-${group.reason}`} className="failure-group-card" data-tone={getFailureTone(group)}>
                    <div className="failure-group-head">
                      <div>
                        <p>{formatFailureCategory(group.category)}</p>
                        <strong>{group.reason}</strong>
                      </div>
                      <span className="status-pill status-failed">{group.count}</span>
                    </div>
                    <div className="failure-chip-list">
                      {group.targets.map((target) => (
                        <span key={`${group.reason}-${target}`} className="failure-target-chip">
                          {target}
                        </span>
                      ))}
                    </div>
                    <p className="failure-suggestion">{group.suggestion}</p>
                    {detailPath ? (
                      <div className="panel-link-row">
                        <Link className="detail-link" to={detailPath}>
                          Open failure detail
                        </Link>
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          )}
        </article>

        <article className="panel ops-platform-panel">
          <header className="section-title">
            <div>
              <p>Platform Performance</p>
              <h2>Publishing by channel</h2>
            </div>
            <span>{platformMetrics.length} platforms</span>
          </header>

          {platformMetrics.length === 0 ? (
            <div className="empty-state">No platform metrics yet. Create and execute a few publish jobs first.</div>
          ) : (
            <div className="platform-metric-list">
              {platformMetrics.map((metric) => (
                <article key={metric.platform} className="platform-metric-card" data-tone={getPlatformTone(metric)}>
                  <div className="platform-metric-head">
                    <strong>{formatPlatform(metric.platform)}</strong>
                    <span>{Math.round(metric.successRate * 100)}%</span>
                  </div>
                  <div className="platform-metric-grid">
                    <div>
                      <span>Total jobs</span>
                      <strong>{metric.totalJobs}</strong>
                    </div>
                    <div>
                      <span>Published</span>
                      <strong>{metric.publishedJobs}</strong>
                    </div>
                    <div>
                      <span>Failed</span>
                      <strong>{metric.failedJobs}</strong>
                    </div>
                    <div>
                      <span>Scheduled</span>
                      <strong>{metric.scheduledJobs}</strong>
                    </div>
                  </div>
                  <p className="platform-metric-note">
                    {metric.engagementImpressions > 0
                      ? `CTR ${Math.round(metric.clickThroughRate * 100)}% · ${metric.engagementClicks} clicks · ${metric.engagementInteractions} interactions`
                      : metric.lastError
                        ? `Latest ${metric.lastFailureCategory ?? "platform"} issue: ${metric.lastError}`
                        : "No recent platform errors or engagement data yet."}
                  </p>
                  <div className="panel-link-row">
                    <Link className="detail-link" to={buildDetailPath("platform", metric.platform, metric.failedJobs > 0)}>
                      {metric.failedJobs > 0 ? "Open failed jobs" : "Open platform detail"}
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </article>
      </section>

      <section className="ops-grid">
        <article className="panel ops-jobs-panel">
          <header className="section-title">
            <div>
              <p>Recent Jobs</p>
              <h2>Latest publish activity</h2>
            </div>
            <span>{recentJobs.length} jobs</span>
          </header>

          {recentJobs.length === 0 ? (
            <div className="empty-state">No publish jobs yet. Create a draft and schedule distribution to populate this feed.</div>
          ) : (
            <div className="ops-article-list">
              {recentJobs.map((job) => (
                <article key={job.id} className="ops-article-row">
                  <div>
                    <strong>{formatPlatform(job.platform)}</strong>
                    <p>
                      Article #{job.articleId} · {formatDateTime(job.updatedAt)}
                    </p>
                  </div>
                  <div className="ops-article-meta">
                    <span className={`status-pill status-${job.status}`}>{formatPublishStatus(job.status)}</span>
                    <span>
                      {job.failureCategory
                        ? `${job.failureCategory} · ${job.errorMessage ?? "provider failure"}`
                        : job.lastProviderStatus
                          ? `${job.lastProviderStatus} · retries ${job.retries}`
                          : job.errorMessage ?? `Retries: ${job.retries}`}
                    </span>
                    <Link className="detail-link detail-link-soft" to={buildDetailPath("platform", job.platform, job.status === "failed")}>
                      Detail
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </article>

        <article className="panel ops-articles-panel">
          <header className="section-title">
            <div>
              <p>Recent Drafts</p>
              <h2>Latest digest updates</h2>
            </div>
            <span>{recentArticles.length} drafts</span>
          </header>

          {recentArticles.length === 0 ? (
            <div className="empty-state">No article drafts yet. Generate a digest to start tracking draft health here.</div>
          ) : (
            <div className="ops-article-list">
              {recentArticles.map((article) => (
                <article key={article.id} className="ops-article-row">
                  <div>
                    <strong>{article.title}</strong>
                    <p>
                      {article.periodType.toUpperCase()} · {article.storyCount} stories · updated {formatDateTime(article.updatedAt)}
                    </p>
                  </div>
                  <div className="ops-article-meta">
                    <span className={`status-pill status-${article.status}`}>{formatArticleStatus(article.status)}</span>
                    <span>{article.variantCount} variants</span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </article>
      </section>
    </div>
  );
}
