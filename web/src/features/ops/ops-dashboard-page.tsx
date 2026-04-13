import React from "react";
import { useQuery } from "@tanstack/react-query";

import { DetailLink, EmptyState, MetricGrid, PageHeader, PanelHeader, StatusPill } from "../../components/console";
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
    return "待发布";
  }
  if (status === "published") {
    return "已发布";
  }
  if (status === "failed") {
    return "失败";
  }
  return status;
}

function formatArticleStatus(status: string): string {
  if (status === "ready") {
    return "就绪";
  }
  if (status === "scheduled") {
    return "已排程";
  }
  if (status === "published") {
    return "已发布";
  }
  if (status === "failed") {
    return "失败";
  }
  return "草稿";
}

function formatFailureCategory(category: string): string {
  if (category === "ingest") {
    return "采集";
  }
  if (category === "publish") {
    return "发布";
  }
  return category;
}

function formatRecommendationCategory(category: string): string {
  if (category === "section") {
    return "栏目";
  }
  if (category === "platform") {
    return "平台";
  }
  if (category === "source") {
    return "来源";
  }
  return category;
}

function buildMetrics(summary: Awaited<ReturnType<typeof fetchOpsSummary>> | undefined): OpsMetric[] {
  if (summary === undefined) {
    return [
      { label: "采集条目", value: "--", note: "等待后端指标" },
      { label: "已审核故事", value: "--", note: "等待后端指标" },
      { label: "发布成功率", value: "--", note: "等待后端指标" },
      { label: "互动点击", value: "--", note: "等待后端指标" },
    ];
  }

  return [
    {
      label: "采集条目",
      value: `${summary.itemsIngestedTotal}`,
      note: `${summary.ingestRunsTotal} 次运行，失败 ${summary.ingestRunsFailed} 次`,
    },
    {
      label: "已审核故事",
      value: `${summary.storiesApproved}`,
      note: `待审核 ${summary.storiesPending} 条`,
    },
    {
      label: "发布成功率",
      value: `${Math.round(summary.publishSuccessRate * 100)}%`,
      note: `已发布 ${summary.publishJobsPublished} 条，失败 ${summary.publishJobsFailed} 条`,
    },
    {
      label: "互动点击",
      value: `${summary.engagementClicksTotal}`,
      note: `${summary.engagementInteractionsTotal} 次互动，${summary.engagementOpensTotal} 次打开`,
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
    return "高热";
  }
  if (momentumTier === "rising") {
    return "上升";
  }
  if (momentumTier === "cooling") {
    return "降温";
  }
  return "平稳";
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
  const title = mode === "publishing" ? "发布运营总览" : "运营总览";
  const lead =
    mode === "publishing"
      ? "跟踪分发质量、平台健康度、审核积压和下一步处置动作，在重试前快速定位风险。"
      : "在同一个暖白金属控制台里查看采集、审核、草稿生成与多平台分发状态。";

  return (
    <div className="preview-page ops-dashboard-page">
      <PageHeader
        className="intro-band"
        eyebrow="运营控制台"
        title={title}
        lead={lead}
        health={health}
        metaLabel="刷新间隔"
        metaValue="30 秒"
      />

      <MetricGrid ariaLabel="运营快照" items={metrics} variant="strip" />


      <section className="ops-alert-strip" aria-label="运营告警">
        {alerts.length === 0 ? (
          <article className="ops-alert-card" data-tone="calm">
            <div>
              <p>告警</p>
              <strong>当前没有活跃告警</strong>
            </div>
            <span>当前采集、审核和发布信号整体稳定。</span>
          </article>
        ) : (
          alerts.map((alert) => (
            <article key={`${alert.category}-${alert.title}`} className="ops-alert-card" data-tone={getAlertTone(alert)}>
              <div className="ops-alert-head">
                <div>
                  <p>{alert.category}</p>
                  <strong>{alert.title}</strong>
                </div>
                <StatusPill status={alert.severity === "critical" ? "failed" : alert.severity === "warning" ? "pending" : "approved"}>
                  {alert.count}
                </StatusPill>
              </div>
              <span>{alert.summary}</span>
              <p className="failure-suggestion">{alert.suggestion}</p>
            </article>
          ))
        )}
      </section>

      <section className="ops-grid">
        <article className="panel ops-health-panel">
          <PanelHeader kicker="流程健康度" title="核心工作流状态" meta={summaryQuery.isFetching ? "刷新中" : "实时快照"} />

          <div className="runway ops-runway">
            <div className="runway-step">
              <div className="runway-node">
                <span>1</span>
              </div>
              <div className="runway-copy">
                <strong>采集</strong>
                <p>{summary?.ingestRunsTotal ?? 0}</p>
                <span>{summary?.ingestRunsFailed ?? 0} 次运行带错误</span>
              </div>
            </div>
            <div className="runway-step">
              <div className="runway-node">
                <span>2</span>
              </div>
              <div className="runway-copy">
                <strong>审核</strong>
                <p>{summary?.storiesApproved ?? 0}</p>
                <span>{summary?.storiesPending ?? 0} 条待审核</span>
              </div>
            </div>
            <div className="runway-step">
              <div className="runway-node">
                <span>3</span>
              </div>
              <div className="runway-copy">
                <strong>发布</strong>
                <p>{summary?.publishJobsPublished ?? 0}</p>
                <span>{summary?.publishJobsScheduled ?? 0} 条仍待执行</span>
              </div>
            </div>
          </div>

          <div className="risk-overview-grid ops-risk-grid">
            <div className="risk-stat" data-tone={(summary?.articlesFailed ?? 0) > 0 ? "watch" : "calm"}>
              <p>失败草稿</p>
              <strong>{summary?.articlesFailed ?? 0}</strong>
              <span>发布回写后失败、需要人工介入的草稿。</span>
            </div>
            <div className="risk-stat" data-tone={(summary?.duePublishJobs ?? 0) > 0 ? "watch" : "calm"}>
              <p>到期未完成</p>
              <strong>{summary?.duePublishJobs ?? 0}</strong>
              <span>已经到期但仍等待分发或轮询收敛的任务。</span>
            </div>
            <div
              className="risk-stat"
              data-tone={(summary?.feedbackRecommendations.length ?? 0) > 0 ? "watch" : "calm"}
            >
              <p>行动队列</p>
              <strong>{summary?.feedbackRecommendations.length ?? 0}</strong>
              <span>根据审核积压、失败情况和平台信号生成的建议动作。</span>
            </div>
          </div>
        </article>

        <div className="ops-side-stack">
          <article className="panel ops-section-panel">
            <PanelHeader kicker="栏目审核" title="按栏目查看编辑负载" meta={`${sectionMetrics.length} 个栏目`} />

            {sectionMetrics.length === 0 ? (
              <EmptyState>当前还没有已审核或待审核的 story。先执行采集并审核几条内容。</EmptyState>
            ) : (
              <div className="source-governance-grid section-metric-list">
                {sectionMetrics.map((metric) => (
                  <article key={metric.section} className="source-governance-card" data-tone={getSectionTone(metric)}>
                    <div className="source-governance-head">
                      <div>
                        <p>{metric.section.replace(/_/g, " ")}</p>
                        <strong>{metric.label}</strong>
                      </div>
                      <StatusPill status="pending">{metric.totalStories}</StatusPill>
                    </div>
                    <div className="platform-metric-grid compact-gap">
                      <div>
                        <span>已审核</span>
                        <strong>{metric.approvedStories}</strong>
                      </div>
                      <div>
                        <span>待审核</span>
                        <strong>{metric.pendingStories}</strong>
                      </div>
                      <div>
                        <span>需复核</span>
                        <strong>{metric.flaggedStories}</strong>
                      </div>
                      <div>
                        <span>总数</span>
                        <strong>{metric.totalStories}</strong>
                      </div>
                    </div>
                    <p className="platform-metric-note">
                      {metric.engagementImpressions > 0
                        ? `${formatMomentumTier(metric.momentumTier)} · CTR ${Math.round(metric.clickThroughRate * 100)}% · ${metric.engagementClicks} 次点击`
                        : "当前栏目还没有沉淀发布后的互动数据。"}
                    </p>
                    <div className="panel-link-row">
                      <DetailLink to={buildDetailPath("section", metric.section)}>
                        打开栏目详情
                      </DetailLink>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </article>

          <article className="panel ops-momentum-panel">
            <PanelHeader kicker="栏目势能" title="表现较强的栏目" meta={`${momentumSections.length} 个已跟踪栏目`} />

            {momentumSections.length === 0 ? (
              <EmptyState>当前还没有栏目互动信号。先记录发布反馈，才能看出哪些栏目真正有效。</EmptyState>
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
                        <span>点击</span>
                        <strong>{metric.engagementClicks}</strong>
                      </div>
                      <div>
                        <span>CTR</span>
                        <strong>{Math.round(metric.clickThroughRate * 100)}%</strong>
                      </div>
                      <div>
                        <span>互动</span>
                        <strong>{metric.engagementInteractions}</strong>
                      </div>
                      <div>
                        <span>曝光</span>
                        <strong>{metric.engagementImpressions}</strong>
                      </div>
                    </div>
                    <div className="panel-link-row">
                      <DetailLink to={buildDetailPath("section", metric.section)}>
                        打开栏目详情
                      </DetailLink>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </article>

          <article className="panel ops-recommendation-panel">
            <PanelHeader kicker="反馈闭环" title="建议的下一步动作" meta={`${feedbackRecommendations.length} 条建议`} />

            {feedbackRecommendations.length === 0 ? (
              <EmptyState>当前没有额外建议动作，审核和发布信号整体稳定。</EmptyState>
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
                        <StatusPill status="pending">{recommendation.signalCount}</StatusPill>
                      </div>
                      <p className="source-governance-note">{recommendation.summary}</p>
                      <p className="failure-suggestion">{recommendation.suggestion}</p>
                      {detailPath ? (
                        <div className="panel-link-row">
                          <DetailLink to={detailPath}>
                            打开建议详情
                          </DetailLink>
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
          <PanelHeader kicker="失败诊断" title="最近的失败分组" meta={`${failureGroups.length} 个分组`} />

          {failureGroups.length === 0 ? (
            <EmptyState>最近没有失败分组，当前流程快照较为干净。</EmptyState>
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
                      <StatusPill status="failed">{group.count}</StatusPill>
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
                        <DetailLink to={detailPath}>
                          打开失败详情
                        </DetailLink>
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          )}
        </article>

        <article className="panel ops-platform-panel">
          <PanelHeader kicker="平台表现" title="按渠道查看发布表现" meta={`${platformMetrics.length} 个平台`} />

          {platformMetrics.length === 0 ? (
            <EmptyState>当前还没有平台指标。先创建并执行几条发布任务。</EmptyState>
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
                        <span>任务总数</span>
                        <strong>{metric.totalJobs}</strong>
                      </div>
                      <div>
                        <span>已发布</span>
                        <strong>{metric.publishedJobs}</strong>
                      </div>
                      <div>
                        <span>失败</span>
                        <strong>{metric.failedJobs}</strong>
                      </div>
                      <div>
                        <span>待执行</span>
                        <strong>{metric.scheduledJobs}</strong>
                      </div>
                    </div>
                    <p className="platform-metric-note">
                      {metric.engagementImpressions > 0
                      ? `CTR ${Math.round(metric.clickThroughRate * 100)}% · ${metric.engagementClicks} 次点击 · ${metric.engagementInteractions} 次互动`
                      : metric.lastError
                        ? `最近一次${metric.lastFailureCategory ?? "平台"}问题：${metric.lastError}`
                        : "当前还没有最近的平台错误或互动数据。"}
                    </p>
                    <div className="panel-link-row">
                      <DetailLink to={buildDetailPath("platform", metric.platform, metric.failedJobs > 0)}>
                      {metric.failedJobs > 0 ? "打开失败任务" : "打开平台详情"}
                      </DetailLink>
                    </div>
                  </article>
              ))}
            </div>
          )}
        </article>
      </section>

      <section className="ops-grid">
        <article className="panel ops-jobs-panel">
          <PanelHeader kicker="最近任务" title="最近的发布活动" meta={`${recentJobs.length} 条任务`} />

          {recentJobs.length === 0 ? (
            <EmptyState>当前还没有发布任务。先创建草稿并排程分发。</EmptyState>
          ) : (
            <div className="ops-article-list">
              {recentJobs.map((job) => (
                <article key={job.id} className="ops-article-row">
                  <div>
                    <strong>{formatPlatform(job.platform)}</strong>
                    <p>
                      稿件 #{job.articleId} · {formatDateTime(job.updatedAt)}
                    </p>
                  </div>
                  <div className="ops-article-meta">
                    <StatusPill status={job.status}>{formatPublishStatus(job.status)}</StatusPill>
                    <span>
                      {job.failureCategory
                        ? `${job.failureCategory} · ${job.errorMessage ?? "提供方失败"}`
                        : job.lastProviderStatus
                          ? `${job.lastProviderStatus} · 重试 ${job.retries} 次`
                          : job.errorMessage ?? `已重试 ${job.retries} 次`}
                    </span>
                    <DetailLink soft to={buildDetailPath("platform", job.platform, job.status === "failed")}>
                      详情
                    </DetailLink>
                  </div>
                </article>
              ))}
            </div>
          )}
        </article>

        <article className="panel ops-articles-panel">
          <PanelHeader kicker="最近草稿" title="最近的稿件更新" meta={`${recentArticles.length} 篇草稿`} />

          {recentArticles.length === 0 ? (
            <EmptyState>当前还没有文章草稿。先生成一篇摘要稿件。</EmptyState>
          ) : (
            <div className="ops-article-list">
              {recentArticles.map((article) => (
                <article key={article.id} className="ops-article-row">
                  <div>
                    <strong>{article.title}</strong>
                    <p>
                      {article.periodType.toUpperCase()} · {article.storyCount} 条 story · 更新于 {formatDateTime(article.updatedAt)}
                    </p>
                  </div>
                  <div className="ops-article-meta">
                    <StatusPill status={article.status}>{formatArticleStatus(article.status)}</StatusPill>
                    <span>{article.variantCount} 个变体</span>
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
